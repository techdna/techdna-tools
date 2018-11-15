#=============================================================================
'''
    Surveyor Job

    Executes a measurement job against a folder tree, using jobworker processes
    to read files and delegate mesurement tasks to Surveyor modules.
'''
#=============================================================================
# Copyright 2004-2011, Matt Peloquin and Construx. This file is part of Code
# Surveyor, covered under GNU GPL v3 and is distributed WITHOUT ANY WARRANTY.
#=============================================================================
import os
import time
import multiprocessing
from Queue import Empty, Full

from framework import jobworker
from framework import jobout
from framework import folderwalk
from framework import fileext
from framework import configstack
from framework import utils
from framework import trace


# Leave a core open for the main app and jobOut threads, which
# are running under the process we execute on
DEFAULT_NUM_WORKERS = max(1, multiprocessing.cpu_count()-1)

# Seconds we wait at various points
MAIN_PROCESSING_SLEEP = 0.1
WORKER_EXIT_TIMEOUT = 0.5
JOBOUT_EXIT_TIMEOUT = 1
TASK_FULL_TIMEOUT = 0.4

# Max number of files and size in bytes that will be sent to a worker
# Smaller values result in more multiprocessing overhead, while larger
# values risk not providing a good distribution of files across cores
# if file/folder sizes vary widely
QUEUE_PACKAGE_MAX_ITEMS = 256
QUEUE_PACKAGE_MAX_BYTES = 256000

# Number of unfiltered files before we send a work package
# This prevents a small work package from not being sent if we are
# searching through a large number of files we're not measuring
MAX_FILES_BEFORE_SEND = 256


class Options( object ):
    '''
    Holds options that define the execution of a job
    '''
    def __init__(self):
        self.pathsToMeasure = []
        self.fileFilters = []
        self.deltaPath = None
        self.includeFolders = []
        self.skipFolders = []
        self.skipFiles = []
        self.recursive = True
        self.numWorkers = DEFAULT_NUM_WORKERS
        self.breakOnError = False
        self.configInfoOnly = False
        self.profileName = None


class Job( object ):
    '''
    One Job object is created and run by the main app.
    The main thread walks the folder tree placing files in task queue.
    The out thread gets output from the output work queue and calls
    back to the application (display update and writing to the output
    file occurs on this output thread)
    '''
    def __init__(self, configStack, options,
                    file_measured_callback, status_callback):

        # Options define the life a job and cannot be modified
        self._options = options

        # All UI output is done through the status callback
        self._status_callback = status_callback

        # Keep track of (and allow access to) raw file metrics
        self.numFolders = 0
        self.numFoldersMeasured = 0
        self.numUnfilteredFiles = 0
        self.numFilteredFiles = 0
        self.numFilesToProcess = 0

        # Queues to communicate with Workers, and the output thread
        self._taskQueue = multiprocessing.Queue()
        self._controlQueue = multiprocessing.Queue()
        self._outQueue = multiprocessing.Queue()
        self._outThread = jobout.OutThread(
                self._outQueue, self._controlQueue,
                self._options.profileName, file_measured_callback)

        # Create max number of workers (they will be started later as needed)
        assert self._options.numWorkers > 0, "Less than 1 worker requested!"
        context = (trace.get_context(), self._options.profileName)
        self._workers = self.Workers(
                self._controlQueue, self._taskQueue, self._outQueue,
                context, self._options.numWorkers)
        trace.msg(1, "Created {0} workers".format(self._workers.num_max()))

        # Create our object for tracking state of folder walking
        self._pathsToMeasure = options.pathsToMeasure
        self._folderWalker = folderwalk.FolderWalker(
                options.deltaPath,
                configStack,
                options.recursive,
                options.includeFolders,
                options.skipFolders,
                options.fileFilters,
                options.skipFiles,
                self.add_folder_files)

        # Utility object for managing work packages; holds the state of the
        # work package that is being prepared for sending to queue
        self._workPackage = self.WorkPackage()

        # Other processing state
        self._continueProcessing = True
        self._taskPackagesSent = 0
        self._filesSinceLastSend = 0


    #-------------------------------------------------------------------------

    def add_folder_files(self, currentDir, deltaPath, filesAndConfigs, numUnfilteredFiles):
        '''
        This is a callback from folderwalk that we use to put a set of filesAndConfigItems
        into one or more WorkPackages to send to jobs. At this point files have already
        been filtered against both job options and the config items.
        '''
        self.numFolders += 1
        self.numUnfilteredFiles += numUnfilteredFiles
        self._filesSinceLastSend += numUnfilteredFiles
        self.numFilteredFiles += len(filesAndConfigs)
        if self._options.configInfoOnly:
            self._config_info_display(currentDir, filesAndConfigs)
        else:
            self._put_files_in_queue(currentDir, deltaPath, filesAndConfigs)
            self._status_callback()
        return self._check_command()

    #-------------------------------------------------------------------------

    def run(self):
        try:
            self._outThread.start()
            self._fill_work_queue()
            self._wait_process_packages()
            self._wait_output_finish()
        except KeyboardInterrupt:
            self._keyboardInterrupt()
        except Exception, e:
            self._exception(e)
        finally:
            self._wait_then_exit()

    def _fill_work_queue(self):
        trace.cc(1, "Starting to fill task queue")
        for pathToMeasure in self._pathsToMeasure:
            if self._check_command():
                self._folderWalker.walk(pathToMeasure)
        if self._check_command() and self._workPackage.size_items() > 0:
            self._send_current_package()

    def _wait_process_packages(self):
        trace.cc(1, "Task queue is complete, processing packages")
        while self._check_command() and self._task_queue_size() > 0:
            time.sleep(MAIN_PROCESSING_SLEEP)
            self._status_callback()
        if self._check_command():
            self._send_workers_command('WORK_DONE')
        else:
            self._send_workers_command('EXIT')

    def _wait_output_finish(self):
        self._send_output_command('WORK_DONE')
        while self._check_command() or self._outThread.is_alive():
            self._outThread.join(JOBOUT_EXIT_TIMEOUT)
            self._status_callback()
            self._continueProcessing = not bool(self._controlQueue.empty())

    def _keyboardInterrupt(self):
        trace.cc(1, "Ctrl-c occurred in MAIN loop")
        self._send_output_command('EXIT')
        raise

    def _exception(self, e):
        trace.cc(1, "EXCEPTION -- EXITING JOB...")
        self._send_workers_command('EXIT')
        self._send_output_command('EXIT')
        trace.traceback()
        raise e

    def _wait_then_exit(self):
        trace.cc(1, "Waiting to exit workers and output thread...")
        for worker in self._workers():
            while worker.is_alive():
                self._status_callback()
                worker.join(WORKER_EXIT_TIMEOUT)
                trace.cc(2, "Worker {0} is_alive: {1}".format(
                        worker.name, worker.is_alive()))
        self._outThread.join(JOBOUT_EXIT_TIMEOUT)
        self._close_queues()
        trace.cc(1, "TERMINATING")


    #-------------------------------------------------------------------------
    #   Work Package Processing

    class WorkPackage( object ):
        '''
        A work package groups a set of files to be sent to a jobworker. The files
        and the config information necessary to process them are workItems.
        '''
        def __init__(self):
            self.reset()
        def reset(self):
            self.itemsToProcess = []
            self.byteSize = 0
        def add(self, workItem, byteSize):
            self.itemsToProcess.append(workItem)
            self.byteSize += byteSize
        def size_items(self):
            return len(self.itemsToProcess)
        def size_bytes(self):
            return self.byteSize
        def items(self):
            return self.itemsToProcess
        def ready_to_send(self):
            return (self.size_items() >= QUEUE_PACKAGE_MAX_ITEMS or
                    self.size_bytes() >= QUEUE_PACKAGE_MAX_BYTES)


    def _task_queue_size(self):
        remainingPackages = self._taskPackagesSent - self._outThread.taskPackagesReceived
        assert remainingPackages >=0, "In/Out Queues out of sync"
        return remainingPackages


    def _put_files_in_queue(self, path, deltaPath, filesAndConfigs):
        '''
        Package files from the given folder into workItems that are then grouped
        into workPackages that are placed into the task queue for jobworkers.
        Packages are broken up if files number or total size exceeds
        thresholds to help evenly distribute load across cores
        '''
        if not filesAndConfigs:
            return
        self.numFoldersMeasured += 1

        for fileName, configEntrys in filesAndConfigs:

            # Expensive to check file size here, but it is worth it for
            # pracelling widely varying file sizes out to cores for CPU intensive
            # jobs. Profiling shows it is not worth caching this
            try:
                fileSize = utils.get_file_size(os.path.join(path, fileName))
            except Exception, e:
                # It is possible (at least in Windows) for a fileName to exist
                # in the file system but be invalid for Windows calls. This is
                # the first place we try to access the file through the file
                # system; if it blows up we don't want the job to fall apart,
                # and this is an unusual case, so unlike more likely errors,
                # we don't bother with a pathway back to the main application
                # to handle the error; we just swallow it and provide debug
                trace.msg(1, str(e))
                continue

            trace.cc(3, "WorkItem: {0}, {1}".format(fileSize, fileName))
            self.numFilesToProcess += 1
            workItem = (path,
                        deltaPath,
                        fileName,
                        configEntrys,
                        self._options,
                        len(filesAndConfigs))
            self._workPackage.add(workItem, fileSize)

            if self._workPackage.ready_to_send() or (
                    self._filesSinceLastSend > MAX_FILES_BEFORE_SEND):
                self._send_current_package()

            if not self._check_command():
                break


    def _send_current_package(self):
        '''
        Place package of work on queue, and start a worker
        '''
        self._workers.start_next()
        trace.cc(2, "PUT WorkPackage - files: {0}, bytes: {1}...".format(
                self._workPackage.size_items(), self._workPackage.size_bytes()))
        trace.cc(4, self._workPackage.items())
        try:
            self._taskQueue.put(self._workPackage.items(), True, TASK_FULL_TIMEOUT)
        except Full:
            raise utils.JobException("FATAL ERROR -- FULL TASK QUEUE")
        else:
            self._taskPackagesSent += 1
            self._filesSinceLastSend = 0
            self._workPackage.reset()


    #-------------------------------------------------------------------------

    def _config_info_display(self, currentDir, filesAndConfigs):
        '''
        Provide support for the configInfo option, that displays in the UI
        what folders would be measured by what configEntries
        '''
        activeConfigs = set([])
        for fileName, configEntrys in filesAndConfigs:
            _root, fileExt = os.path.splitext(fileName)
            # TBD -- this won't work if there are RE or Exclude file types
            for configEntry in configEntrys:
                activeConfigs.add((fileExt, configEntry))

        if activeConfigs:
            displayStr = currentDir + "\n"
            for fileExt, configEntry in activeConfigs:
                displayStr += ("   " + str(fileExt) + " - " +
                        configEntry.config_str_no_fileext() + "\n")
            self._status_callback(displayStr)


    #-------------------------------------------------------------------------
    #   Command Queue management

    def _check_command(self):
        '''
        Check the command queue to see if there have been problems while
        running a job
        Exceptions received from the command queue are thrown
        '''
        myCommand = None
        otherCommands = []
        try:
            while self._continueProcessing:
                (target, command, payload) = self._controlQueue.get_nowait()
                trace.cc(4, "check_command - {0}, {1}".format(target, command))
                if target == 'JOB':
                    if 'ERROR' == command:
                        # Error notifications in the control queue are only used to support
                        # break on error functionality -- the error info itself will be handled
                        # by the output queue. Jobs with lots of errors can clog up the
                        # control queue, so we clear these out as we find them
                        trace.cc(1, "COMMAND: ERROR for file: {0}".format(payload))
                        if self._options.breakOnError:
                            self._continueProcessing = False
                    else:
                        myCommand = command
                        break
                else:
                    otherCommands.append((target, command, payload))
        except Empty:
            pass
        finally:
            if 'EXCEPTION' == myCommand:
                trace.cc(1, "COMMAND: EXCEPTION RECEIVED")
                raise payload

            # If everything is okay, or some other exception happened, we want to
            # make sure we put any queue items we removed back in the queue
            for (target, command, payload) in otherCommands:
                trace.cc(3, "putting {0}, {1}".format(target, command))
                self._controlQueue.put_nowait((target, command, payload))

        return self._continueProcessing


    def _close_queues(self):
        # Make sure queues are flushed and closed to avoid errors in queue code
        queues = [self._taskQueue, self._outQueue, self._controlQueue]
        for queue in queues:
            try:
                while True:
                    _ = queue.get_nowait()
                queue.close()
            except Empty:
                pass


    def _send_workers_command(self, command, payload=None):
        for worker in self._workers():
            if worker.is_alive():
                self._send_command(worker.name, command, payload)

    def _send_output_command(self, command, payload=None):
        self._send_command(self._outThread.name, command, payload)

    def _send_command(self, target, command, payload):
        trace.cc(2, "COMMAND:  {0}, {1} {2}".format(target, command, payload))
        self._controlQueue.put_nowait((target, command, payload))

    #-------------------------------------------------------------------------

    class Workers( object ):
        '''
        Subclass for managing group of workers that makes the construction
        of each Worker a bit cleaner and allows for easy lazy job starting
        and tracking of how many workers are active
        '''
        def __init__(self, controlQueue, inQueue, outQueue,
                    dbgContext, numWorkers):
            self._workers = [
                    jobworker.Worker(inQueue, outQueue, controlQueue,
                            dbgContext, str(num+1))
                    for num in xrange(numWorkers) ]
            self._workerStartIter = self()
            self._workerStartDone = False
            self._startedWorkers = 0
        def __call__(self):
            for worker in self._workers:
                yield worker
        def start_next(self):
            if not self._workerStartDone:
                try:
                    self._workerStartIter.next().start()
                    self._startedWorkers += 1
                    return True
                except StopIteration:
                    self._workerStartDone = True
                    return False
        def num_max(self):
            return len(self._workers)
        def num_started(self):
            return self._startedWorkers


