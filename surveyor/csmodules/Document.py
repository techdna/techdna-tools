#=============================================================================
'''
    Document measurement module

    TBD -- this module is experimental

    Provides metrics for various document file types

    1) Allows files to be counted with no measures (so their metadata can
    still be captured if they are defined in a config file)

'''
#=============================================================================
# Copyright 2004-2010, Matt Peloquin and Construx. This file is part of Code
# Surveyor, covered under GNU GPL v3 and is distributed WITHOUT ANY WARRANTY.
#=============================================================================
import os
import re
import sys

from framework import basemodule
from framework import filetype
from framework import utils
from framework import trace


# Since this class gets pickled, we need to put lookup functions that are
# called by reference at the top module level

# PDF files have a fairly consistent marker for page breaks
pdfPageCountRe = re.compile(r"/Type */Page *>", re.MULTILINE|re.DOTALL)
def _measure_pdf(fileObject, measurements):
    if fileObject is None:
        measurements['doc.pages'] = 0
    else:
        measurements['doc.pages'] = len(
                pdfPageCountRe.findall(fileObject.read()))


class Document( basemodule._BaseModule ):
    '''
    Handles document files - limited measures
    '''
    VERB_MEASURE = "measure"
    LINES_TOTAL   = "file.total"
    LINES_BLANK   = "file.blank"
    LINES_CONTENT = "file.content"
    DOC_PAGES =   "doc.pages"
    DOC_CHARS =   "doc.chars"
    NO_MEASURE = "-"
    
    # Optimization for checking debug level in tight loops
    _traceLevel = None

    def __init__(self, options):
        super(Document, self).__init__(options)

        self.verbs = [self.VERB_MEASURE]
        self.measures = [ 'doc.*',
                self.NO_MEASURE,
                self.LINES_TOTAL,
                self.LINES_BLANK,
                self.LINES_CONTENT ]

        self.reBlankLine = re.compile( r"^\s*$" )

        # We optimize a check for trace level inside the core file processing loop, because some
        # trace statements make calls to format even in non-debug mode
        self._traceLevel = trace.level()


        # Lookup to associate file type with counting method
        # We could expose this to the endsuer for configuration as modules
        # or a config option, but documents tend to have much more stable file
        # types so it should be fine to encode them here
        self.filetypeMeasures = {
                '.pdf': _measure_pdf,
                }

    @classmethod
    def _cs_config_options(cls):
        return {}


    #-------------------------------------------------------------------------
    def _survey(self, fileObject, configEntry, measurements, _analysis):
        if not fileObject:
            return

        self.totalLines = 0
        self.blankLines = 0
        self.contentLines = 0
        try:

            measureMethod = self.filetypeMeasures.get(self._currentPath.fileExt, None)
            if measureMethod is not None:
                measureMethod(fileObject, measurements)

            # Otherwise if it is a delta list comparison
            elif isinstance(fileObject, list):
                self._measure_text(fileObject, measurements)

            # Otherwise if it is a text File
            elif filetype.is_text_file(fileObject):
                self._measure_text(fileObject, measurements)

            # TBD -- what to with binary files without handlers

            # Pack up our measurements
            measurements[ self.LINES_TOTAL   ] = self.totalLines
            measurements[ self.LINES_BLANK   ] = self.blankLines
            measurements[ self.LINES_CONTENT ] = self.contentLines

            return True

        except Exception, e:
            trace.traceback()
            raise utils.FileMeasureError(
                    "Problem processing file {0} with module: {1}\n\t{1}".format(
                    self._currentPath.filePath, self.__class__.__name__, str(e)))


    def _measure_text(self, fileObject, measurements):
        '''
        Default handler For text based files, go through each file line
        '''
        if self._traceLevel: trace.file(4, "Document: {0}".format(fileObject))
        for rawLine in fileObject:
            self.totalLines += 1
            line = utils.strip_null_chars(rawLine)

            # Detect blank lines
            if self.reBlankLine.match(line):
                self.blankLines += 1
                continue

            # Content line
            self.contentLines += 1

'''
    TBD --  RTF page signatures
       {\nofpages30}{\nofwords10810}{\nofchars61619}


'''

