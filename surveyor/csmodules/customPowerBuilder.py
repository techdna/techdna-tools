#=============================================================================
'''
    PowerBuilder Module

    This can be run on PBL files directly, or on export files.

    Crude metrics can be generated in a run against PBL files, but it is
    usually better to use the PB_OUTFILES option to create a set of files
    with split contents.
'''
#=============================================================================
# Copyright 2004-2012, Matt Peloquin and Construx. This file is part of Code
# Surveyor, covered under GNU GPL v3 and is distributed WITHOUT ANY WARRANTY.
#=============================================================================
import re
import string
from Code import Code
from framework import utils

class customPowerBuilder( Code ):
    '''
    We override line processing to split out binary parts from the
    various types of code sections
    '''
    ConfigOptions_PowerBuilder = {
        'PB_OUTFILES': (
            'self.createOutFiles = True',
            'Creates output files containing text Code separated from Binary'),
        }

    def __init__(self, options):
        super(customPowerBuilder, self).__init__(options)

        self._outFileSuffix = ".cs"

        self._genLineStarts = [
            re.compile(r'^\s*text\('),
            re.compile(r'^\s*column\('),
            ]

        # Tracking for whether we are in routine
        self._inRoutine = False
        self._currentRoutineEnd = None
        self._routineMatches = [
            (re.compile(r'\s+function\s+.*;'),
                re.compile(r'^end\s+function')),
            (re.compile(r'\s+subroutine\s+.*;'),
                re.compile(r'^end\s+subroutine')),
            (re.compile(r'\bevent\s+.*;'),
                re.compile(r'^end\s+event')),
            ]

        # Tracking for whether we are in table
        self._inTable = False
        self._tableStart = re.compile(r'^\s*table\(')
        self._tableEnd = re.compile(r'^[^\s]+')


    @classmethod
    def _cs_config_options(cls):
        return cls.ConfigOptions_PowerBuilder

    def _cs_init_config_options(self):
        super(customPowerBuilder, self)._cs_init_config_options()
        self._configOptionDict.update(self.ConfigOptions_PowerBuilder)

        self.createOutFiles = False

        # Override comments for PowerBuilder specifics
        self.singleLineComments = [ re.compile(r"^\s*%") ]
        self.multiLineCommentsOpen = [
            re.compile( r"/\*" ),
            re.compile( r"\"" ),
            ]
        self.multiLineCommentsClose = [
            re.compile( r"\*/" ),
            re.compile( r"\"" ),
            ]
        self.multiLineCommentsCloseSameLine = [
            re.compile( r"\*/" ),
            re.compile( r"\"" ),
            ]
        self.reBlankLine = re.compile(r'''
            ^ \s* (end\s+type | end\s+event | end\s+on | // | [ - \* ' #  ; ! % {} \(\) \[\] <> \| ]? ) \s* $
            ''', self._reFlags)


    def _survey_start(self, params):
        Code._survey_start(self, params)
        self.counts['PbBinLines'] = [0] * len(self.blockDetectors)
        self.counts['PbGenLines'] = [0] * len(self.blockDetectors)
        self._isPblFile = self._currentPath.fileExt.lower() == '.pbl'
        self._outFiles = {}


    def _alternate_line_processing(self, line):
        '''
        Check the start of the line to detect a binary part of a PBL file
        Some of this processing is really only for PBL files, but it will be harmless
        for exported files
        Return value to determine whether we do any more survreyor processing on line
        '''
        stopProcessingLine = True
        if super(customPowerBuilder, self)._alternate_line_processing(line):
            return stopProcessingLine

        line = utils.strip_null_chars(line)
        if self.reTrueBlankLine.match(line):
            return False

        isTextLine = True
        if self._isPblFile:
            line = self._clean_PB_tokens(line)

            windowSize = 80
            textChars = string.letters + string.digits + string.whitespace + '~$\\/-_<>=():*|;,\"'
            startPoint = 1
            minWindowSize = 15
            threshold = 0.2
            isTextLine = utils.check_bytes_below_threshold(
                            line.lstrip()[:windowSize], textChars, minWindowSize, startPoint, threshold)

        line = utils.strip_extended_chars(line)

        if isTextLine:
            if self._is_generated_line(line):
                self.counts['PbGenLines'][self._activeBlock] += 1
                self._write_out_line('Gen', line)
            else:
                # At this point, we have a line of code we want to process
                # We separate out routines and tables from generic code
                stopProcessingLine = False
                if not self._process_PB_routine(line):
                    if self._in_PB_table(line):
                        self._write_out_line('Tables', line)
                    else:
                        self._write_out_line('Code', line)
        else:
            self.counts['PbBinLines'][self._activeBlock] += 1
            self._write_out_line('Bin', line)

        return stopProcessingLine


    def _is_generated_line(self, line):
        isGenerated = False
        for genLineRe in self._genLineStarts:
            if genLineRe.match(line):
                isGenerated = True
                break
        return isGenerated


    def _in_PB_table(self, line):
        if self._inTable:
            if self._tableEnd.search(line):
                self._inTable = False
        else:
            if self._tableStart.search(line):
                self._inTable = True
        return self._inTable


    def _process_PB_routine(self, line):
        '''
        Handle writing of routine content to files, and keep track of our
        state of being in a routine
        Return whehter we took care of processing the line
        '''
        processedLine = False
        if self._inRoutine:
            self._write_out_line('Routines', line)
            processedLine = True
            if self._currentRoutineEnd.search(line):
                self._currentRoutineEnd = None
                self._inRoutine = False
        else:
            for routineStart, routineEnd in self._routineMatches:
                if routineStart.search(line):
                    self._inRoutine = True
                    self._currentRoutineEnd = routineEnd
                    self._write_out_line('Routines', '\n')
                    splitLines = line.split(';')
                    for splitLine in splitLines:
                        if not splitLine.endswith('\n'):
                            splitLine += ';\n'
                        self._write_out_line('Routines', splitLine)
                    processedLine = True
                    break
        return processedLine


    def _survey_end(self, measurements, analysis):
        Code._survey_end(self, measurements, analysis)
        measurements["file.pbBinLines"] = sum(self.counts['PbBinLines'])
        measurements["file.pbGenLines"] = sum(self.counts['PbGenLines'])

        if self.createOutFiles:
            for fileObj in self._outFiles.itervalues():
                try:
                    fileObj.close()
                except Exception:
                    pass


    def _write_out_line(self, fileType, line):
        if self.createOutFiles:
            outFile = None
            try:
                outFile = self._outFiles[fileType]
            except KeyError:
                outFile = open(self._currentPath.filePath + self._outFileSuffix + fileType, "w")
                self._outFiles[fileType] = outFile
            outFile.write(line)


    def _clean_PB_tokens(self, line):
        # Clean up the DAT* type tokens, which may be 7-8 chars long
        while True:
            pos = line.find('DAT*')
            if pos < 0:
                break
            length = 8
            if not line[:(pos+length)].isspace():
                length =7
            line = line[:pos] + line[(pos+length):]
        return line