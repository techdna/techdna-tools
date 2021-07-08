#=============================================================================
'''
    Surveyor Job Worker Process

    A work package from the input queue is a set of work items. These
    consits of a file name and set of config entries for that file.

    For each workitem, the worker designates the given file as the
    "currentFile". It then goes through all the config entries for
    the file (files are processed more than once if they are tagged
    with different measures by a config file) and delegates the measurement
    call to the appropriate module (the file is opened once and cached).

    The output from each measure call is placed in a list associated with
    that file. When the file processing is done this list is cached as
    part of "currentOutput". Once all workItems in a workPackage are
    processed, the currentOutput is posted and we start over again.
'''
#=============================================================================
# Copyright 2004-2011, Matt Peloquin and Construx. This file is part of Code
# Surveyor, covered under GNU GPL v3 and is distributed WITHOUT ANY WARRANTY.
#=============================================================================
import os
import sys
import time
import multiprocessing
from errno import EACCES
from queue import Empty, Full

from framework import fileext
from framework import uistrings
from framework import trace
from framework import utils

WORKER_PROC_BASENAME = "Job"
INPUT_EMPTY_WAIT = 0.01
CONTROL_QUEUE_TIMEOUT = 0.1
OUT_PUT_TIMEOUT = 0.4


#-------------------------------------------------------------------------
# The following is required to support multi-processing with pyinstaller
try:
    # Python 3.4+
    if sys.platform.startswith('win'):
        import multiprocessing.popen_spawn_win32 as forking
    else:
        import multiprocessing.popen_fork as forking
except ImportError:
    import multiprocessing.forking as forking

class _Popen(forking.Popen):
    def __init__(self, *args, **kw):
        if hasattr(sys, 'frozen'):
            # Have to set _MEIPASS2 to get --onefile and --onedir mode working.
            os.putenv('_MEIPASS2', sys._MEIPASS) # last character is stripped in C-loader
        try:
            super(_Popen, self).__init__(*args, **kw)
        finally:
            if hasattr(sys, 'frozen'):
                os.unsetenv('_MEIPASS2')

class Process(multiprocessing.Process):
    _Popen = _Popen


class Worker( Process ):
    '''
    The worker class executes as separate processes spawned by the Job
    They take items from the input queue, delegate calls to the measurement
    modules, and package measures for the output queue.
    '''
    def __init__(self, inputQueue, outputQueue, controlQueue,
                    context, num, jobName=WORKER_PROC_BASENAME):
        '''
        Init is called in the parent process
        '''
        multiprocessing.Process.__init__(self, name=jobName + str(num))
        self._inputQueue = inputQueue
        self._outputQueue = outputQueue
        self._controlQueue = controlQueue
        self._continueProcessing = True
        self._currentOutput = []
        self._currentFilePath = None
        self._currentFileIterator = None
        self._currentFileOutput = []
        self._currentFileErrors = []
        self._dbgContext, self._profileName = context
        trace.cc(2, "Initialized new process: {0}".format(self.name))

    #-------------------------------------------------------------------------

    def run(self):
        '''
        Process entry point - set up debug/profile context
        '''
        try:
            trace.set_context(self._dbgContext)

            if self._profileName is not None:
                import cProfile;
                cProfile.runctx('self._run()', globals(), {'self': self}, self._profileName + self.name)
            else:
                self._run()

        except Exception as e:
            self._controlQueue.put_nowait(('JOB', 'EXCEPTION', e))
            trace.traceback()
        except KeyboardInterrupt:
            trace.cc(1, "Ctrl-c occurred in job worker loop")
        except Exception as e:
            trace.cc(1, "EXCEPTION occurred in job worker loop")
            self._controlQueue.put_nowait(('JOB', 'EXCEPTION', e))
            trace.traceback()
        finally:
            # We know the input and out queues are empty or that we're bailing
            # on them, so we cancel_join_thread (don't wait for them to clear)
            self._inputQueue.close()
            self._inputQueue.cancel_join_thread()
            self._outputQueue.close()
            self._outputQueue.cancel_join_thread()
            # We may have put items on the control queue, so we join_thread to
            # make sure what we've put in the pipe is flushed
            self._controlQueue.close()
            self._controlQueue.join_thread()
            trace.cc(1, "TERMINATING")


    def _run(self):
        '''
        Process items from input queue until it's empty and app signals all done
        '''
        trace.cc(1, "STARTING: Begining to process input queue...")

        while self._continueProcessing:
            try:
                workPackage = self._inputQueue.get_nowait()
                trace.cc(2, "GOT WorkPackage - files: {0}".format(len(workPackage)))
            except Empty:
                # The input queue can return empty when it really isn't, or
                # we are in mid job and have burned down the empty queue
                # Sleeping after these helps performance with many cores, vs
                # just blocking on inputQueue.get
                trace.cc(3, "EMPTY INPUT")
                time.sleep(INPUT_EMPTY_WAIT)
                self._check_for_stop()
            else:
                for workItem in workPackage:
                    if not self._measure_file(workItem):
                        self._continueProcessing = False
                        break
                self._post_results()
                self._check_for_stop()


    def _check_for_stop(self):
        '''
        Command queue will normally be empty unless we are terminating.
        If there are commands, get all that we can until we find our own or empty
        the queue -- we then put back everything we took off. The command queue
        should never have a lot in it and this guarantees we can't deadlock.
        '''
        otherCommands = []
        myCommand = None
        exitNow = False
        try:
            while True:
                (target, command, payload) = self._controlQueue.get_nowait()
                trace.cc(3, "command - {0}, {1}".format(target, command))
                if target == self.name:
                    myCommand = command
                    break
                else:
                    otherCommands.append((target, command, payload))
        except Empty:
            pass
        finally:
            if 'EXIT' == myCommand:
                trace.cc(1, "COMMAND: EXIT")
                self._continueProcessing = False
                exitNow = True
            elif 'WORK_DONE' == myCommand:
                trace.cc(1, "COMMAND: WORK_DONE")
                self._continueProcessing = False
            for target, command, payload in otherCommands:
                trace.cc(3, "putting {0}, {1}".format(target, command))
                try:
                    self._controlQueue.put((target, command, payload), True, CONTROL_QUEUE_TIMEOUT)
                except Full:
                    raise utils.JobException("FATAL EXCEPTION - Control Queue full, can't put")
        return exitNow

    #-------------------------------------------------------------------------
    #  File measurement

    def file_measured_callback(self, filePath, measures, analysisResults):
        '''
        Callback from the masurement module
        We store up a list of tuples with the work output for a given file
        '''
        assert filePath == self._currentFilePath, "Measure callback out of sync"
        trace.cc(3, "_file_measured_callback: {0}".format(filePath))
        trace.file(3, "  measures: {0}".format(measures))
        trace.file(3, "  analysis: {0}".format(analysisResults))
        self._currentFileOutput.append((measures, analysisResults))


    def _measure_file(self, workItem):
        '''
        Unpack workItem and run all measures requested by the configItems
        for the file
        '''
        (   path,
            deltaPath,
            fileName,
            configItems,
            options,
            numFilesInFolder
            ) = workItem

        self._currentFilePath = os.path.join(path, fileName)
        trace.file(1, "Processing: {0}".format(self._currentFilePath))

        deltaFilePath = None
        if deltaPath is not None:
            deltaFilePath = os.path.join(deltaPath, fileName)

        continueProcessing = True
        try:
            for configItem in configItems:
                if self._check_for_stop():
                    break

                self._open_file(configItem.module, deltaFilePath)

                #
                # Synchronus delegation to the measure module defined in the config file
                #
                configItem.module.process_file(
                        self._currentFilePath,
                        self._currentFileIterator,
                        configItem,
                        numFilesInFolder,
                        self.file_measured_callback)

        except utils.FileMeasureError as e:
            trace.traceback(2)
            self._currentFileErrors.append(
                    uistrings.STR_ErrorMeasuringFile.format(self._currentFilePath, str(e)))
            continueProcessing = not options.breakOnError
        except EnvironmentError as e:
            trace.traceback(2)
            if e.errno == EACCES:
                self._currentFileErrors.append(
                        uistrings.STR_ErrorOpeningMeasureFile_Access.format(self._currentFilePath))
            else:
                self._currentFileErrors.append(
                        uistrings.STR_ErrorOpeningMeasureFile_Except.format(self._currentFilePath, str(e)))
            continueProcessing = not options.breakOnError
        finally:
            self._close_current_file()
            self._file_complete()
        return continueProcessing


    def _open_file(self, module, deltaFilePath):
        '''
        Open can be an expensive operation, so for the nominal case of opening a file,
        we'll cache the current file iterator and use multiple times if there are
        multiple config entries to be processed for the file
        We also cache the originally opening module to make the close symetrical.
        '''
        fileIterator = module.open_file(
                        self._currentFilePath, deltaFilePath, self._currentFileIterator)
        if fileIterator:
            self._currentFileIterator = fileIterator


    def _close_current_file(self):
        '''
        Normally the fileIterator is a file handle that needs to be closed, but it may
        just be an iterator
        '''
        if self._currentFileIterator:
            try:
                self._currentFileIterator.close()
            except AttributeError:
                pass
            self._currentFileIterator = None


    #-------------------------------------------------------------------------

    def _file_complete(self):
        '''
        Cache the output from the measurement callbacks for current file
        '''
        if self._currentFileOutput or self._currentFileErrors:
            self._currentOutput.append(
                    (self._currentFilePath, self._currentFileOutput, self._currentFileErrors))
            trace.cc(3, "Caching results: {0}".format(self._currentFilePath))
        else:
            trace.cc(3, "No measures for: {0}".format(self._currentFilePath))
        self._currentFileOutput = []
        self._currentFileErrors = []


    def _post_results(self):
        '''
        Send any cached results back to main process's out thread
        This is a set of results for config measure of every file
        in the last work package
        '''
        try:
            self._outputQueue.put(self._currentOutput, True, OUT_PUT_TIMEOUT)
            trace.cc(3, "OUT - PUT {0} items".format(len(self._currentOutput)))
        except Full:
            raise utils.JobException("FATAL EXCEPTION - Out Queue full, can't put")
        finally:
            self._currentOutput = []


