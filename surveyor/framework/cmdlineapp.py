#=============================================================================
'''
    Code Surveyor command line application

    See README, framework\__init__.py, and csmodule\__init__.py for system
    overview and design
'''
#=============================================================================
# Copyright 2004-2011, Matt Peloquin and Construx. This file is part of Code
# Surveyor, covered under GNU GPL v3 and is distributed WITHOUT ANY WARRANTY.
#=============================================================================
import os
import sys
import locale
import multiprocessing
from numbers import Number

from framework import job
from framework import writer
from framework import filetype
from framework import basemodule
from framework import configstack
from framework import cmdlineargs
from framework import utils
from framework import trace
from framework.uistrings import *

# Debugging support
#import code; code.interact(local=locals())
#import pdb; pdb.set_trace()


# Factory method for running a Surveyor job
def run_job(cmdArgs, outputStream, printWidth=None):
    return SurveyorCmdLine().run(cmdArgs, outputStream, printWidth)


# Default values for application display
MIN_DISPLAY_INTERVAL = 0.2
LONG_PROCESSING_THRESHOLD = 5
CONSOLE_OUT_WIDTH = 78
MAX_ERRORS_TO_DISPLAY = 15
MAX_ERRORS_DEBUG = 200


class SurveyorCmdLine( object ):
    '''
    Implements user interface, manages output file creation, and application
    behavior for dupes and aggregate processing.
    Each instantiation equals one measurement run, with the main file scanning
    and processing delegated to the Job
    '''

    # The following lists have dependencies on csmodule defined names, to provide
    # convienence for display and writing of key output
    ItemColumnOrder = [
            'dir1', 'dir2', 'dir3', 'dir4', 'dir5', 'dir6', 'dir7',
            'fileName',
            'fileType',
            'tag1', 'tag2', 'tag3',
            'file.nbnc',
            'file.comment',
            'file.dead',
            'file.machine',
            'file.content',
            'file.blank',
            'file.nbncRank',
            'file.commentRank',
            'dupe.nbnc',
            'routine.line',
            'routine.nbnc',
            'routine.nbncRank',
            'routine.complexity',
            'routine.complexityRank',
            'routine.nesting',
            'routine.nestingRank',
            'routine.name',
            'routine.linenum',
            'routine.regex',
            'search.line',
            'search.linenum',
            'search.regex',
            'search.match',
            'file.fullName',
            'fileAbsPath',
            ]
    SummaryPrefixToExclude = set(['dir', 'fileName'])
    SummaryToInclude = set([
            'fileType', 'file.nbnc', 'file.comment', 'file.machine', 'dupe.nbnc', 'file.bytes',
            'file.content', 'file.dead', 'routine.complexity', 'search.total'])
    DupeMeasureOutput = set([
            'fileType', 'fileName', 'fileAbsPath', 'dir', 'tag', 'nbnc.crc',
            'dupe.nbnc', 'dupe.fileName', 'dupe.firstPath', 'dupe.dir' ])


    def __init__(self):
        utils.timing_start()
        utils.timing_set('LAST_DISPLAY_TIME')

        locale.setlocale(locale.LC_ALL, '')
        self._outLock = multiprocessing.Lock()

        self.set_tracing(0)
        #self.set_tracing(2, modes=[])

        # Objects we will create and delegate to
        self._args = None
        self._job = None
        self._writer = None
        self._out = None

        # Options (stay constant for life of a job)
        # Can be modified at start from command line arguments

        self._jobOpt = job.Options()

        self._outType = CMDARG_OUTPUT_TYPE_CSV
        self._outFileName = DEFAULT_OUT_FILE
        self._outFileDir = utils.CURRENT_FOLDER
        self._outFileOverride = False

        self._dupeTracking = False
        self._dupeThreshold = 0
        self._aggregateNames = {}
        self._aggregateThresholdKey = None
        self._aggregateThreshold = 1

        self._summaryOnly = False
        self._printMaxWidth = CONSOLE_OUT_WIDTH
        self._detailed = False
        self._detailedPrintSummaryMax = 0
        self._progress = False
        self._quiet = False

        self._profiling = False
        self._profileCalls = 16
        self._profileCalledBy = 4
        self._profileCalled = 4
        self._profileThreadFilter = 'all'
        self._profileNameFilter = ''

        # Other internal state
        self._aggregates = {}
        self._dupeFileSurveys = {}

        self._totals = {}
        self._lastDisplayLen = 0
        self._numFilesMeasured = 0
        self._numFilesProcessed = 0
        self._numMeasures = 0

        self._errorList = []
        self._maxErrorDisplay = MAX_ERRORS_TO_DISPLAY
        self._longProcessingThreshold = LONG_PROCESSING_THRESHOLD
        self._keyboardInterrupt = None
        self._finalException = None


    def run(self, cmdArgs, outputStream, printWidth):
        '''
        Run a single session of the Surveyor command line UI
        The return value (for cmd shell) will be false if any errors occurred.
        '''
        self._out = outputStream
        if printWidth:
            self._printMaxWidth = printWidth
        self._display_heading()
        success = False
        if self._parse_command_line(cmdArgs):
            self._display_start()
            try:
                if self._profiling:
                    self._print("\n=== RUNNING WITH PROFILER ===\n")
                    self._jobOpt.profileName = PROFILE_FILE
                    import cProfile;
                    cProfile.runctx('self._execute_job()', globals(),
                            {'self': self}, PROFILE_FILE + "Main")
                else:
                    self._execute_job()
                success = not self._errorList
            except KeyboardInterrupt as e:
                self._keyboardInterrupt = e
            except Exception as e:
                self._finalException = sys.exc_info()
            finally:
                self._display_summary()
                self._cleanup()
        return success


    def set_tracing(self, level, **kwargs):
        '''
        Set tracing parameters, always supplying our lock
        '''
        if level > 0:
            self._maxErrorDisplay = MAX_ERRORS_DEBUG
            kwargs['lock'] = self._outLock
        trace.init_context(level, **kwargs)


    #-------------------------------------------------------------------------
    #  Job exceution and error handling

    def _execute_job(self):
        self._setup_job()
        self._initialize_output()
        self._job.run()
        self._write_aggregates()


    def _parse_command_line(self, cmdArgs):
        utils.init_surveyor_dir(cmdArgs[0])
        self._args = cmdlineargs.SurveyorCmdLineArgs(cmdArgs, self)
        helpText = None
        try:
            helpText = self._args.parse_args()
        except KeyboardInterrupt:
            self._keyboardInterrupt()
        except Exception as e:
            trace.traceback()
            helpText = STR_HelpText_Usage
            if len(e.args):
                helpText += STR_ErrorCmdLineText.format(str(self._args.args), str(e))
            else:
                helpText += STR_ErrorParsingCommandLine
        finally:
            if helpText is None:
                return True
            else:
                self._display_help(helpText)
                return False


    def _setup_job(self):
        '''
        Creates the ConfigStack and Job objects for this job
        Assummes internal state already set by command line parsing
        '''
        configStack = configstack.ConfigStack(
                self._args.configCustom,
                self._args.configOverrides,
                self._args.config_option_list()
                )
        self._job = job.Job(
                configStack,
                self._jobOpt,
                self.file_measured_callback,
                self.status_callback)


    def _initialize_output(self):
        # Do not run display meter if we are doing heavy debug output
        self._quiet = self._quiet or (
                        trace.out() == sys.stdout and trace.level() > 2)

        # Init the meter so it shows up right away (really big dirs can
        # cause a delay in feedback
        if not self._quiet:
            self._write_display_feedback_line()

        # Initialize the writer and note default outfile path
        # (there may be other output files open based on config file settings)
        # If we are sending measure to stdout, make sure quiet mode is on
        typeLookup = {
            CMDARG_OUTPUT_TYPE_CSV:  ',',
            CMDARG_OUTPUT_TYPE_TAB:  '\t',
            CMDARG_OUTPUT_TYPE_PARA: '\xB6',
            CMDARG_OUTPUT_TYPE_XML:  'xml',
            }
        self._writer = writer.get_writer(
                typeLookup[self._outType], self.status_callback,
                self._outFileDir, self._outFileName, self._outFileOverride,
                self.ItemColumnOrder)
        if self._writer.using_console():
            self._quiet = True


    def _cleanup(self):
        if self._writer is not None:
            self._writer.close_files()
        self._display_profile_info()
        if self._keyboardInterrupt is not None:
            self._print(STR_UserInterrupt)
        if self._finalException is not None:
            import traceback
            # We don't use our tracing or print output here
            self._out.write(STR_Error)
            self._out.write(''.join(traceback.format_exception(*self._finalException)))



    #-----------------------------------------------------------------------------
    #   Callbacks from Job

    def file_measured_callback(self, filePath, outputList, errorList):
        '''
        Job output thread callback to provide file measurements.
        A list of output and potential errors is provided for each file.
        Called ONCE for each file in the job; if there were multiple
        config entries for the file, outputList will have multiple items.
        '''
        self._numFilesProcessed += 1
        self._errorList.extend(errorList)

        fileTime = 0
        fileMeasured = False
        for measures, analysisResults in outputList:
            trace.file(2, "Callback: {0} -- {1}".format(filePath, measures))
            if list(measures.items()):
                # Zero out dupe measures in place
                if self._dupeTracking:
                    self._filter_dupes(filePath, measures, analysisResults)

                # Send results to metrics writer
                fileMeasured = True
                self._numMeasures += max(1, len(analysisResults))
                if not self._summaryOnly:
                    self._writer.write_items(measures, analysisResults)

                # Capture summary metrics and aggregates
                self._stash_summary_metrics(filePath, measures, analysisResults)
                self._stash_aggregates(filePath, analysisResults)

                fileTime += utils.safe_dict_get_float(measures, basemodule.METADATA_TIMING)

        self._numFilesMeasured += (1 if fileMeasured else 0)
        self._display_file_progress(filePath, fileTime)
        self._display_feedback()


    def status_callback(self, outputText = None):
        '''
        General callback for updating UI of the application
        '''
        self._display_feedback()
        if outputText and not self._quiet:
            outputLines = outputText.split("\n")
            for line in outputLines:
                self._print_clear(self._format_progress_message(line + "\n"))


    #-------------------------------------------------------------------------
    #  Metrics Results

    def _stash_summary_metrics(self, filePath, measures, analysisItems):
        '''
        Keep summary metrics on the measures for command-line display
        Use a dictionary of dictionaries to capture each measure along with
        the break-down on per-file type
        '''
        itemsToStash = []
        itemsToStash.extend(list(measures.items()))
        # For detailed or higher trace levels, show everything we collected except exclusions
        # Otherwise show only key summary items
        if self._detailed or trace.level() > 1:
            for analysis in analysisItems:
                itemsToStash.extend(list(analysis.items()))
            itemsToStash = [(n, v) for n, v in itemsToStash if
                    True not in [n.startswith(prefix) for prefix in self.SummaryPrefixToExclude]]
        else:
            itemsToStash = [(n, v) for n, v in itemsToStash if n in self.SummaryToInclude]

        for itemName, itemValue in itemsToStash:
            self._add_metric_to_summary(filePath, itemName, itemValue)


    def _add_metric_to_summary(self, filePath, metricName, metric):
        if metricName not in self._totals:
            self._totals[metricName] = {}

        # If scalar value, add it to total, otherise increment count
        MEASURE_TOTAL_KEY = ''
        increment = 1
        if isinstance(metric, Number):
            increment = metric
        newValue = self._totals[metricName].get(MEASURE_TOTAL_KEY, 0) + increment
        self._totals[metricName][MEASURE_TOTAL_KEY] = newValue

        # For detailed measures stash metrics on per-file basis, according to exclusions
        if self._detailed and (
                metricName in self.SummaryToInclude or trace.level() >= 2) and (
                True not in [metricName.startswith(prefix) for prefix in self.SummaryPrefixToExclude]):
            (_not_used_, fileType) = os.path.splitext(filePath)
            fileType = fileType.lower() if fileType else NO_EXTENSION_NAME
            self._totals[metricName][fileType] = (
                self._totals[metricName].get(fileType, 0) + increment)


    #-------------------------------------------------------------------------
    #  Duplicate Filter

    def _filter_dupes(self, filePath, measures, analysisResults):
        '''
        If filePath qualifies as a duplicate of a previous file, blank out
        all analysisResults, some measures, and add dupe measures
        '''
        firstDupeFilePath = self._is_file_survey_dupe(filePath, measures)
        if firstDupeFilePath:
            analysisResults[:] = []

            # We special case grabbingthe NBNC size, to have easy measure of
            # how many LOC are duplicate for a given file
            try:
                measures[basemodule.METADATA_DUPE_NBNC] = measures['file.nbnc']
            except KeyError:
                pass

            # Add duplicate measure info
            measures[basemodule.METADATA_DUPE_PATH] = firstDupeFilePath
            measures[basemodule.METADATA_DUPE_FILE] = measures[basemodule.METADATA_FULLNAME]
            basemodule.add_dir_list_to_measures(
                    utils.SurveyorPathParser(firstDupeFilePath),
                    basemodule.METADATA_DUPE_DIR,
                    cmdlineargs.METADATA_MAXDEPTH_DEFAULT,
                    measures)

            # Delete in place measures not defined in DupeMeasureOutput
            # The numbers are stripped as convienence for Dir1, Dir2, etc.
            dupeMeasures = dict(
                    (k, v) for k, v in measures.items()
                        if k.rstrip('0123456789') in self.DupeMeasureOutput)
            measures.clear()
            measures.update(dupeMeasures)



    def _is_file_survey_dupe(self, filePath, measures):
        '''
        Simple mechanism to identify duplicate and near-dupicate code by tracking
        a dictionary of files we see as measures.  There are two modes:

        1) File Size: Build a dictionary in memory based on a hash of fileName
        and config info. In the hash buckets we store a dict of file sizes for
        the first of each size we see that is not within the dupe threshold.
        If we see a file size within the threshold of one of our existing
        hashed sizes, we treat it as a dupe and increment count for reporting.

        2) NBNC CRC: We use the nbnc.crc measure to identify duplicates

        Note that we ASSUME the necessary file metadata will be present in the
        measures dicitonary, as basemodule.py puts it there for the Dupe option.
        '''
        firstDupeFilePath = None

        # 1) File name and Size check
        if isinstance(self._dupeThreshold, int):
            fileSize = int(measures[basemodule.METADATA_FILESIZE])
            dupeKey = (measures[basemodule.METADATA_FULLNAME] +
                        measures[basemodule.METADATA_CONFIG].replace(' ', ''))
            if dupeKey in self._dupeFileSurveys:
                for dupeFileSize, (fileCount, firstFilePath) in self._dupeFileSurveys[dupeKey].items():
                    if (dupeFileSize - self._dupeThreshold) <= fileSize and (
                            fileSize <= (dupeFileSize + self._dupeThreshold)):
                        firstDupeFilePath = firstFilePath
                        self._dupeFileSurveys[dupeKey][dupeFileSize] = (fileCount + 1, firstFilePath)
                        trace.msg(1, "Dupe {0} by {1} of {2} bytes: {3}".format(
                                    fileCount, fileSize - dupeFileSize, fileSize, filePath))
                        break
            else:
                self._dupeFileSurveys[dupeKey] = {}

            if firstDupeFilePath is None:
                self._dupeFileSurveys[dupeKey][fileSize] = (1, filePath)
                trace.file(2, "Added {0} -- {1} to dupe dictionary".format(dupeKey, fileSize))

        # 2) Code CRC check
        # Our relying on the nbnc.crc is brittle, because it is both a code and runtime
        # dependency on the Code csmodule being used. And there are valid scenarios
        # where nbnc.crc may not be present (e.g., skipping dupe file). Thus if the
        # measure isn't present, we fail silently
        else:
            fileCrc = None
            try:
                fileCrc = measures['nbnc.crc']
            except:
                trace.file(2, "CRC Dupe - nbnc.crc missing: {0}".format(filePath))
            if fileCrc in self._dupeFileSurveys:
                fileCount, firstDupeFilePath = self._dupeFileSurveys[fileCrc]
                self._dupeFileSurveys[fileCrc] = (fileCount + 1, firstDupeFilePath)
                trace.msg(1, "Dupe {0}: {1} DUPE_OF {2}".format(fileCount, filePath, firstDupeFilePath))
            elif fileCrc is not None:
                self._dupeFileSurveys[fileCrc] = (1, filePath)
                trace.file(2, "Added {0} -- {1} to dupe dictionary".format(filePath, fileCrc))

        return firstDupeFilePath


    #-------------------------------------------------------------------------
    #  Aggregates

    def _stash_aggregates(self, filePath, analysisResults):
        '''
        As we receive results for files, if we have requests to aggregate
        results, store away aggregate information.
        The aggreate functionality is based on names of items generated
        by specific csmodules; we consider it a fatal error if what is
        requested for aggregation and what is present in analysisResults
        are out of sync
        '''
        # For each set of aggregates we go through results and add
        # them to the appropriate aggregate set
        for aggKey, aggNames in self._aggregateNames.items():
            aggregateDict = self._aggregates.setdefault(aggKey, {})
            trace.file(2, "Aggregating {0} items in {1}".format(len(analysisResults), aggKey))
            for result in analysisResults:
                # aggKey has the name for the value from results that we
                # will be keying the aggreate dictionary on
                try:
                    newKey = result[aggKey]
                except KeyError as e:
                    raise utils.InputException(STR_AggregateKeyError.format(str(e)))
                else:
                    aggregate = aggregateDict.setdefault(newKey, {'aggregate.count':0})

                    # Sepcific names can be provided to aggregate, or can do all
                    namesToAggregate = aggNames
                    if isinstance(aggNames, str):
                        if aggNames == 'all':
                            namesToAggregate = list(result.keys())

                    # Take each value from the result and aggregate according to type
                    for itemName in namesToAggregate:
                        self._aggregate_update(itemName, result[itemName], aggregate)

                    # Count the item
                    aggregate['aggregate.count'] += 1

                    # Update the aggregate
                    aggregateDict[newKey] = aggregate

            # The dictionary for this aggKey has been updated, so stash it
            self._aggregates[aggKey] = aggregateDict


    def _aggregate_update(self, itemName, item, aggregate):
        '''
        Updates an aggreate dictionary in place, based on type of newItem
        '''
        # Numbers are added
        if isinstance(item, Number):
            currentValue = aggregate.get(itemName, 0)
            try:
                aggregate[itemName] = currentValue + item
            except TypeError:
                # If a number and string are confused, treat as a string
                aggregate[itemName] = str(item)

        # Lists are extended
        elif isinstance(item, list):
            currentList = aggregate.get(itemName, [])
            currentList.extend(item)
            aggregate[itemName] = currentList

        # Dicts are opened and updated recursively
        elif isinstance(item, dict):
            currentDict = aggregate.get(itemName, {})
            for key, value in item.items():
                self._aggregate_update(key, value, currentDict)
            aggregate[itemName] = currentDict

        # Otherwise we overwrite as string
        else:
            aggregate[itemName] = str(item)


    def _write_aggregates(self):
        '''
        For each set of aggregates, we create an output file with aggregates
        that exceed threshold.
        HACK - We use the output writer by creating a dummy OUT file tag
        '''
        for keyName in list(self._aggregateNames.keys()):
            fileName = str(keyName).replace('.', '')
            hackOutTagMeasure = {'tag_write_aggregates': 'OUT:' + fileName}
            analysisRows = []
            for valueRow in list(self._aggregates[keyName].values()):
                writeRow = self._aggregateThresholdKey is None
                if not writeRow:
                    try:
                        writeRow = valueRow[self._aggregateThresholdKey] > self._aggregateThreshold
                    except KeyError as e:
                        raise utils.InputException(STR_AggregateThresholdKeyError.format(str(e)))
                if writeRow:
                    analysisRows.append(valueRow)
            trace.msg(1, "Aggregate: {0}".format(analysisRows))
            self._writer.write_items(hackOutTagMeasure, analysisRows)


    #-------------------------------------------------------------------------
    #   UI Display

    def _print(self, message, forceClear=None):
        '''
        All output to console should use this print function, which
        handles locking. Child worker processes never call this directly, but
        it is possible for us to be called from multiple threads via job
        callbacks. And we may need to share output with debug stream.
        '''
        try:
            self._outLock.acquire()
            self._write_message(message, forceClear)
            self._out.flush()
        finally:
            self._outLock.release()

    def _print_clear(self, message):
        self._print(message, True)

    def _print_no_clear(self, message):
        self._print(message, False)

    def _write_message(self, message, forceClear=None):
        '''
        Used to create the in-place updating on the console by resetting
        the cursor each time, and blanking the text if requested
        '''
        if not isinstance(message, str):
            message = str(message)

        clearCurrentLine = False
        if forceClear is None:
            clearCurrentLine = len(message) < self._lastDisplayLen
        elif forceClear:
            clearCurrentLine = True
        self._lastDisplayLen = len(message)

        if clearCurrentLine:
            self._out.write("{0:<{width}}".format('', width=self._printMaxWidth))
            self._out.write(utils.CONSOLE_CR)

        self._out.write("{0:<{width}}".format(message, width=self._printMaxWidth))
        self._out.write(utils.CONSOLE_CR)


    def _format_progress_message(self, message):
        return utils.fit_string(message, self._printMaxWidth, "...")

    def _display_heading(self):
        self._print(STR_Intro)

    def _display_help(self, text):
        folderSeperator = '/' if os.name == 'posix' else '\\'
        self._print(text.format(utils.runtime_ext(), folderSeperator))

    def _display_start(self):
        '''
        Called once before job is started
        '''
        if self._quiet:
           return
        self._print(STR_Divider)
        self._print(STR_FolderMeasured.format(", ".join(
                    [os.path.abspath(path) for path in self._jobOpt.pathsToMeasure])))
        if self._jobOpt.deltaPath is not None:
            self._print(STR_DeltaFolder.format(os.path.abspath(self._jobOpt.deltaPath)))
        if self._jobOpt.fileFilters:
            self._print(STR_FileFilter.format(self._jobOpt.fileFilters))
        if self._jobOpt.skipFolders:
            self._print(STR_DirFilter.format(self._jobOpt.skipFolders))
        if self._jobOpt.includeFolders:
            self._print(STR_IncludeFolders.format(self._jobOpt.includeFolders))
        if not self._summaryOnly:
            if (len(self._jobOpt.pathsToMeasure) > 1 or
                    self._jobOpt.pathsToMeasure[0] != self._outFileDir):
                self._print(STR_LocationOfMeasurements.format(
                                os.path.abspath(self._outFileDir)))
        if self._detailed:
            self._print(STR_CmdArgs.format(self._args.args))
        self._print(STR_Divider)
        if trace.level():
            self._print(" ==> Debug Trace <==\n")
            self._print(" Level: {0}  Modes: {1}\n".format(
                    trace.level(), trace.modes()))
            self._print(" Debug output:    {0}\n".format(str(trace.out()).split(',')[0]))
            self._print(" Surveyor folder: {0}\n".format(utils.surveyor_dir()))
            self._print(" CWD for job:     {0}\n\n".format(utils.runtime_dir()))


    def _display_feedback(self):
        '''
        Called during run to display total at bottom of shell screen
        '''
        if self._quiet or self._progress:
            return
        timeSinceLastDisplay = utils.timing_get('LAST_DISPLAY_TIME')
        if timeSinceLastDisplay > MIN_DISPLAY_INTERVAL:
            self._write_display_feedback_line()
            utils.timing_set('LAST_DISPLAY_TIME')


    def _write_display_feedback_line(self):
        displayFeedbackLine = STR_UpdateDisplay.format(
                utils.timing_elapsed(),
                self._job.numUnfilteredFiles,
                self._job.numFilesToProcess - self._numFilesProcessed,
                self._numFilesMeasured)
        self._print(displayFeedbackLine)


    def _display_file_progress(self, filePath, measureTime):
        '''
        We provide some per-file screen feedback
        '''
        if self._progress:
            progressStr = None
            if measureTime is None:
                progressStr = STR_UpdatePath.format(filePath)
            else:
                progressStr = STR_UpdatePathDetailed.format(float(measureTime), filePath)
            self._print_no_clear(self._format_progress_message(progressStr))

        if not self._quiet:
            # Shout out compressed files because they are a pain if not detected
            if filetype.is_compressed_ext(filePath):
                self._print(STR_CompressedFile.format(filePath))

            # A long processing time may indicate a large file that shouldn't be measured
            if measureTime > self._longProcessingThreshold:
                self._print(STR_LongProcessingFile.format(measureTime, os.path.basename(filePath)))


    def _display_summary(self):
        '''
        End of run display to console
        '''
        # Make sure the progress counter is blanked out
        self._print_clear('')
        # Any errors we swallowed during the run
        if self._errorList:
            self._print(STR_ErrorList.format(
                    len(self._errorList), self._maxErrorDisplay,
                    "\n".join(self._errorList[:self._maxErrorDisplay])))
        # Data on files/folders
        if self._job is not None:
            self._print(STR_SummaryTotalFiles.format(
                    self._job.numFolders,
                    self._job.numUnfilteredFiles))
            if self._job.numUnfilteredFiles > self._numFilesMeasured:
                self._print(STR_SummaryFiltered.format(
                        self._job.numUnfilteredFiles - self._numFilesProcessed,
                        self._numFilesProcessed,
                        self._numFilesProcessed - self._numFilesMeasured))
            self._print(STR_SummaryMeasured.format(
                    self._job.numFoldersMeasured,
                    self._numFilesMeasured,
                    self._numMeasures))
        # Key optional information related to measurement content
        if 0 < self._args.ignoreSize:
            self._print(STR_SummaryLargeFile.format(self._args.ignoreSize))
        if self._args.ignoreBinary:
            self._print(STR_SummaryBinaryFile)
        if self._jobOpt.deltaPath is not None:
            self._print(STR_SummaryDeltaFile)
        # Display sorted measurement results
        # We display the measurements in alphabetical order
        # In verbose mode we may break out each measure by file type,
        # in which case we sort by size
        measureNames = list(self._totals.keys())
        if measureNames:
            if self._detailed:
                self._print(STR_SummaryDetailedFileTitle.format(
                        self._detailedPrintSummaryMax))
            else:
                self._print(STR_SummaryDetailedTitle)
            self._display_detailed_summary(measureNames)
        # Note total number of dupes if present
        if self._dupeFileSurveys:
            self._print(STR_TotalDupes.format(*self._get_dupe_counts()))
        # Job run time
        if not self._quiet:
            self._print(STR_SummaryRunTime.format(utils.timing_elapsed()))


    def _get_dupe_counts(self):
        dupeFiles = 0
        totalDupes = 0
        for _k, v in self._dupeFileSurveys.items():
            if isinstance(v, dict):
                for _sizeBucket, (fileCount, _firstFile) in v.items():
                    if fileCount > 1:
                        dupeFiles += 1
                        totalDupes += fileCount
            else:
                (fileCount, _firstFile) = v
                if fileCount > 1:
                    dupeFiles += 1
                    totalDupes += fileCount
        return dupeFiles, totalDupes


    def _display_detailed_summary(self, measureNames):
        measureNames.sort()
        for measureName in measureNames:
            # Create new dict for this measure, keyed on size
            sizeMeasures = {}
            for (fileType, measureTotal) in self._totals[measureName].items():
                sizeMeasures[measureTotal] = STR_SummaryDetailedMeasureValue.format(
                        str(measureName), str(fileType), measureTotal)
            # Display the measurement totals, in descending order
            sortedSizes = list(sizeMeasures.keys())
            sortedSizes.sort(reverse=True)
            for size in sortedSizes[:(self._detailedPrintSummaryMax + 1)]:
                self._print(str(sizeMeasures[size]))


    def _display_profile_info(self):
        '''
        Bring the profile files from each process togehter and display stats
        '''
        if self._profiling:
            try:
                import pstats
            except ImportError:
                print("\nError importing pstats, profile info cannot be displayed\n")
            else:
                try:
                    # Load either data for all threads, or only for one if filtered
                    p = None
                    if self._profileThreadFilter == 'all':
                        p = pstats.Stats(PROFILE_FILE + "Main")
                        p.add(PROFILE_FILE + "Out")
                        if self._job is not None:
                            for jobNum in range(self._job._workers.num_started()):
                                p.add(PROFILE_FILE + "Job" + str(jobNum+1))
                    else:
                        p = pstats.Stats(PROFILE_FILE + self._profileThreadFilter)

                    p.strip_dirs()
                    p.sort_stats('time')
                    print(self._profileNameFilter)

                    # Display output for stats, callers, callees
                    p.print_stats(self._profileCalls, self._profileNameFilter)
                    p.print_callers(self._profileCalledBy, self._profileNameFilter)
                    p.print_callees(self._profileCalled, self._profileNameFilter)
                except Exception as e:
                    print("\nError displaying profile data: \n", e)


