#=============================================================================
'''
    Surveyor NBNC Code measurement module

    Implements Non-Blank, Non-Comment (NBNC) Lines Of Code (LOC) metrics
    across a wide range of code file types. Provides base implementation for
    all Surveyor NBNC line-based code analysis.

    NBNC LOC is a strong proxy for size across technologies. NBNC lines
    are calculated by subracting blank and comment lines from total lines
    for a REASONABLY accurate measure of:

        C/C++, Java, C#, VB, SQL, Python, Perl, JS, Lua, LISP, etc...

    ...and languages with similar comment syntax:

        - Single-line comments: // # -- ' rem ; ! %
        - Multi-line: /* */, <!-- -->, --[[ ]], #| |#, {- -}
            (Python multi-line added in config file)

    Surevyor uses the additional assumptions:

        - A 'Blank' line contains only whitepace or symbol
        - Line continuation and multiple statements a line are IGNORED;
          each NBNC line is defined by a newline
        - Nesting of multi-line comments (e.g., /* /* */ */) is ignored
        - The '#' character is treated as a comment. The most common C/C++
          preprocessor statements are excluded
        - Inline comments ignored (the Code csmodule detects them)

    Languages that do not follow these comment conventions will require
    modifcation of the regular expressions (see customXYZ.py csmodules)
'''
#=============================================================================
# Copyright 2004-2012, Matt Peloquin and Construx. This file is part of Code
# Surveyor, covered under GNU GPL v3 and is distributed WITHOUT ANY WARRANTY.
#=============================================================================
import re
import sys

from framework import utils
from framework import trace
from framework import basemodule

class NBNC( basemodule._BaseModule ):
    '''
    Examines files LINE-BY-LINE with regular expressions to:

        1) Detect and track "blocks" (for generated code, see Machine.py)
        2) Identify blank and comment lines
        3) Count lines of NBNC code
        4) Analyze lines (search/complexity metrics, see Code.py)

    Most csmodules base their implementation on this NBNC framework
    '''
    # Optimization for checking debug level in tight loops
    _traceLevel = None
    
    # Special handling for strings in Python files since comments can look like strings
    _pythonFile = False

    # The measure verb supported by NBNC in the config file
    VERB_MEASURE = "measure"

    # Measures this module can proude
    LINES_CODE    = "file.nbnc"
    LINES_COMMENT = "file.comment"
    LINES_TOTAL   = "file.total"

    # Positions of block dection statements in the blockDetector sub-lists
    BLOCK_START = 0
    BLOCK_END = 1

    # Python triple quotes are a pain to handle in python
    PYTHON_TRIPLE = '('+chr(34)+chr(34)+chr(34)+'|'+chr(39)+chr(39)+chr(39)+')'

    # Maximum line length to process
    # The right combination of a goofy long line and regex can cause some very
    # slow recursion from the regex engine. Since we don't care about any lines
    # above a reaonable lenght for counting or searching, we put this in as
    # a safety valve
    MAX_LINE_LENGTH_DEFAULT = 255

    ConfigOptions_NBNC = {
        'ADD_LINE_SEP': (
            '''self.addLineSep = optValue''',
            '''Split file lines using the given character (e.g., ';')'''),
        'BLANK_LINE': (
            '''self.reBlankLine = re.compile(optValue, self._reFlags)''',
            'Replace the regex for blank line detection'),
        'BLANK_LINE_ADD': (
            '''self.reBlankLineAdd = re.compile(optValue, self._reFlags)''',
            'Add a regex to count as blank lines'),
        'BLANK_LINE_XML': (
            '''self.blankXmlLines = True''',
            'Count lines with only an XML style tag as a blank line'),
        'COMMENT_LINE': (
            '''self.reSingleLineComments = re.compile(optValue, self._reFlags)''',
            'Replace the single-line comment regex detector'),
        'COMMENT_OPEN': (
            '''self.reMultiLineCommentsOpen = re.compile(optValue + self.REMAINING_LINE_APPEND, self._reFlags)''',
            'Replace the multi-line comment open detector'),
        'COMMENT_CLOSE': (
            '''self.reMultiLineCommentsClose = re.compile(optValue, self._reFlags)''',
            'Replace the multi-line comment close detector'),
        'COMMENT_CLOSE_CODE': (
            '''self._sameLineMultiCloseAsComment = False''',
            'If multi-line comment closes on same line, treat line as code'),
        'IGNORE_LINE': (
            '''self.reIgnoreLine = re.compile(optValue, self._reFlags)''',
            'Add a regex for lines to completely ignore'),
        'MAX_LINE_LENGTH': (
            '''self.maxLineLength = int(optValue)''',
            'Cutoff for max chars in a line to process, default is: ' + str(MAX_LINE_LENGTH_DEFAULT)),
        'PYTHON': ('''
self._pythonFile = True
self.reSingleLineComments = re.compile('[#]', self._reFlags)
self.reMultiLineCommentsOpen = re.compile(self.PYTHON_TRIPLE + self.REMAINING_LINE_APPEND, self._reFlags)
self.reMultiLineCommentsClose = re.compile(self.PYTHON_TRIPLE, self._reFlags)''',
            'Add Python comment handling, to deal with triple quotes'),
        'STRINGS': (
            '''self.reStringLiteral = re.compile(optValue, self._reFlags)''',
            'Override the regex used to detect strings'),
        'RUBY': ('''
self.reSingleLineComments = re.compile('[#]', self._reFlags)
self.reMultiLineCommentsOpen = re.compile('=begin' + self.REMAINING_LINE_APPEND, self._reFlags)
self.reMultiLineCommentsClose = re.compile('=end', self._reFlags)''',
            'Add Ruby comment handling, to deal with begin/end'),
        }

    def __init__(self, options):
        super(NBNC, self).__init__(options)

        # We optimize a check for trace level inside the core file processing loop, because some
        # trace statements make calls to format even in non-debug mode
        self._traceLevel = trace.level()

        # Identify what measures we can do for config file validation
        self.verbs = [self.VERB_MEASURE]
        self.measures = [self.LINES_CODE, self.LINES_COMMENT, self.LINES_TOTAL]


    @classmethod
    def _cs_config_options(cls):
        return cls.ConfigOptions_NBNC

    def _cs_init_config_options(self):
        super(NBNC, self)._cs_init_config_options()
        self._configOptionDict.update(self.ConfigOptions_NBNC)

        # Block Detector List
        # This is a list of lists containing start/stop RE pairs that can
        # identify different groupings of code lines
        # The default is an empty list, which counts an entire file as one "block"
        # See Code.py for examples of block detection
        self.blockDetectors = [[]]

        # Additional line separators
        # Normally lines are determined by standard line breaks, but you can add additional
        # line breaks here, for use with Python split()
        self.addLineSep = None

        # The maximum characters we'll process in a line
        self.maxLineLength = self.MAX_LINE_LENGTH_DEFAULT

        # String literal detector
        # Used to remove string literal from some types of searches
        # (note need to except Python triple-quote comments)
        self.reStringLiteral = re.compile(r''' (["](?!["]) .+? ["]) | (['](?![']) .+? [']) ''', re.VERBOSE)

        # Blank line detectors
        # Count common open/closure elements on their own line as blank lines
        self.reTrueBlankLine = re.compile(r'^ \s* $', self._reFlags)
        self.reBlankLine = re.compile(r'''
                ^ [ \s \\ \+ \. , ; = \- / \* ' ` " # ! % {} \(\) \[\] <> \| ]* $
                ''', self._reFlags)
        self.reBlankLineAdd = None
        self.blankXmlLines = False
        self.reBlankXmlLine = re.compile(r'''^ \s* <[\w/\\]*?> \s* $''', self._reFlags)

        # Ignore line; don't consider it in processing
        self.reIgnoreLine = None

        #
        # Single-line comments
        #
        self.reSingleLineComments = re.compile( r'''(
                    //              # C/C++, Java, C#, JS, etc.
                |   [#](?! \| |def|inc|if|else|region)  # Python, etc. (exclude Lisp and pre-process)
                |   ;               # Lisp, assembly
                |   --(?! \[ )      # SQL, Ada, Haskell (exclude lua)
                |   ' (?![^']+?')   # Visual Basic, leaving out string defs
                |   rem             # BAT files, .NET Regions, BASIC, some SQL
                |   !               # FORTRAN, Clarion
                |   %               # Matlab, Prolog, Erlang
                )''', self._reFlags)

        #
        # Multi-line comments
        # The match everything group at the end of the Open regex is used to
        # detect multi-line comments that end on the same line
        # We do not attempt to match opens with particular closes, which has
        # the (very small) potential to lead to occasional errors
        #
        self.RE_GROUP_REMAINING_LINE = "remainingLine"
        self.REMAINING_LINE_APPEND = "(?P<" + self.RE_GROUP_REMAINING_LINE + ">.*)"
        self.reMultiLineCommentsOpen = re.compile( r'''(
                    /\*             # C/C++
                |   --\[\[          # Lua
                |   =(begin|head)   # Perl, Ruby
                |   [#]\|           # Lisp
                |   {-              # Haskell
                |   <!--            # HTML, XML
                |   <%--            # HTML server comments
                )''' + self.REMAINING_LINE_APPEND, self._reFlags)

        self.reMultiLineCommentsClose = re.compile( r'''(
                    \*/             # C/C++
                |   \]\]            # Lua
                |   =(cut|end)      # Perl, Ruby
                |   \|[#]           # Lisp
                |   -}              # Haskell
                |   -->             # HTML, XML
                |   --%>            # HTML server comments
                )'''+ self.REMAINING_LINE_APPEND, self._reFlags)

        self._sameLineMultiCloseAsComment = True


    def _survey(self, linesToSurvey, _configEntry, measurements, _analysis):
        '''
        Basemodule delegate to us to survey a collection of lines.
        '''
        self._survey_lines(linesToSurvey, [],  measurements, [])

        # We always write output, to support metadataOnly runs and providing
        # measure rows for empty files, binaries, etc.
        return True


    #-------------------------------------------------------------------------

    def _survey_start(self, _unused_params):
        # Track our block processing
        self._activeBlock = 0
        self._activeBlockEndRe = None
        self._activeBlockIsSingleLine = False

        # We need to keep track of metrics separtely for every possible block
        # detector we have, so all measures are collected as lists
        # that have as many spaces as the block detector
        self.counts = {}
        self.counts['RawLines']      = [0] * len(self.blockDetectors)
        self.counts['IgnoreLines']   = [0] * len(self.blockDetectors)
        self.counts['TotalLines']    = [0] * len(self.blockDetectors)
        self.counts['MeasureLines']  = [0] * len(self.blockDetectors)
        self.counts['CommentLines']  = [0] * len(self.blockDetectors)
        self.counts['BlankLines']    = [0] * len(self.blockDetectors)
        self.counts['TrueBlankLines']= [0] * len(self.blockDetectors)


    def _survey_lines(self, linesToSurvey, params, measurements, analysis):
        '''
        Analyze file line by line. linesToSurvey is an iterable set of lines.
        Processing is driven by the regular expressions in member variables.
        The order of processing each line is:
             - Preprocess line string
             - Detect machine vs. human code
             - Detect blank lines
             - Detect single and multi-line comments
             - Capture line measures
             - Peform line processing (searches, routines, etc.)
        '''
        # Setup dictionary for measures and searches we'll do
        self._survey_start(params)

        # If no lines to process, we may still want to output empty measures
        if linesToSurvey is None:
            linesToSurvey = []

        # Track whether we are inside a multi-line comment - we ignore nesting
        scanningMultiLine = False

        # If we have a line seperator, apply it
        for bufferLine in linesToSurvey:
            self.counts['RawLines'][self._activeBlock] += 1
            if self._traceLevel: trace.file(4, "Raw: {0}".format(bufferLine))

            # Allow specializations to special-case certain lines
            if self._alternate_line_processing(bufferLine):
                continue

            lines = [bufferLine]
            if self.addLineSep is not None:
                lines = bufferLine.split(self.addLineSep)

            #
            # Read through the file lines and process them one at a time
            # This is the main processing loop for all csmodules derived from NBNC
            #
            try:
                for rawLine in lines:
                    self.counts['TotalLines'][self._activeBlock] += 1

                    # Allow for clean up of artifacts or other pre-processing
                    line = self._preprocess_line(rawLine)

                    # Detect true blank lines
                    if self.reTrueBlankLine.match(line):
                        self.counts['TrueBlankLines'][self._activeBlock] += 1
                        self._trace_line(line, "T")
                        continue

                    # Block Detection
                    if len(self.blockDetectors) > 1:
                        if self._detect_block_change(line, analysis):
                            scanningMultiLine = False  # Don't allow multi-line comment to span blocks

                    # Determine comment state
                    # This is done before blank lines to make sure we consider multi-line
                    # comment syntax that will be counted as "blank", e.g., /* on it's own line
                    onCommentLine, scanningMultiLine = self._detect_line_comment(line, scanningMultiLine)

                    # Detect blank lines
                    if self._detect_blank_line(line):
                        continue

                    # Measure and analyze -- overriden in derived classes
                    self._measure_line(line, onCommentLine)
                    self._analyze_line(line, analysis, onCommentLine)

            except Exception, e:
                trace.traceback()
                raise utils.FileMeasureError(
                        "Problem processing line: {0} with module: {1}\n{2}".format(
                        str(sum(self.counts['RawLines'])), self.__class__.__name__, str(e)))

        # Package results
        self._survey_end(measurements, analysis)


    def _survey_end(self, measurements, _unused_analysis):
        '''
        Capture summary metrics for this file
        Will be overridden in specialized modules to add additional measures
        '''
        measurements[self.LINES_TOTAL  ] = sum(self.counts['TotalLines'])
        measurements[self.LINES_CODE   ] = sum(self.counts['MeasureLines'])
        measurements[self.LINES_COMMENT] = sum(self.counts['CommentLines'])


    #-------------------------------------------------------------------------

    def _preprocess_line(self, line):
        '''
        Cut line down to the maximum allowed length
        Remove null characters that can occur with multibyte file formats
        Can be overriden if multibyte needs to be preserved
        '''
        return utils.strip_null_chars(line[:self.maxLineLength])


    def _alternate_line_processing(self, rawLine):
        '''
        This can be overridden to break out of standard NBNC loop for particular lines
        Our default is to implete the ignore line check
        '''
        if self.reIgnoreLine:
            if self.reIgnoreLine.search(rawLine):
                self._trace_line(rawLine, "-")
                self.counts['IgnoreLines'][self._activeBlock] += 1
                return True
        else:
            return False


    def _detect_block_change(self, line, analysis):
        '''
        Check to see if this line is exiting or entering a new block
        Blcoks do not nest; once in a block, we'll stay in that block
        until a matching exit RE match is found.
        None is a valid value for the exit RE, meaning we stay in
        block until the end of file.
        If a block change happens, we call _block_change_event; the
        analysis argument is in case we need to stash any information
        related to the block change
        '''
        oldActiveBlock = self._activeBlock

        # If we're in an active block, check if we are exiting the block
        if self._activeBlock > 0:

            # If the PREVIOUS line was a single-line block, we reset
            # block status and call ourselves again (once, this is not recursive)
            if self._activeBlockIsSingleLine:
                self._activeBlockIsSingleLine = False
                self._activeBlock = 0
                self._activeBlockEndRe = None
                return self._detect_block_change(line, analysis)

            # Otherwise, normal check for end of block
            else:
                endRe = self._activeBlockEndRe
                if endRe is not None and endRe.search(line):
                    self._activeBlock = 0
                    self._activeBlockEndRe = None
                    if self._traceLevel: trace.search(
                            3, "endblock: {0} ==> {1}".format(endRe.pattern, line))

        # Otherwise check to see if new block starts on this line
        else:
            blockNum = 1
            blockFound = False
            while not blockFound and blockNum < len(self.blockDetectors):
                blockDetector = self.blockDetectors[blockNum]
                for detector in blockDetector:
                    startRe = detector[self.BLOCK_START]
                    if startRe.search(line):
                        self._activeBlock = blockNum
                        self._activeBlockEndRe = detector[self.BLOCK_END]
                        if self._traceLevel: trace.search(
                                3, "startblock: {0} ==> {1}".format(startRe.pattern, line))

                        # Note if block closed on the same line
                        if self._activeBlockEndRe is not None and self._activeBlockEndRe.search(line):
                            self._activeBlockIsSingleLine = True
                            if self._traceLevel: trace.search(
                                    3, "endblockSameline: {0} ==> {1}".format(self._activeBlockEndRe.pattern, line))

                        blockFound = True
                        break
                blockNum += 1

        blockChanged = oldActiveBlock != self._activeBlock
        if blockChanged:
            self._block_change_event(line, analysis, oldActiveBlock)

        return blockChanged


    def _block_change_event(self, line, analysis, oldActiveBlock):
        '''
        Placeholder for specializations to know when we've crossed a block boundary
        '''
        trace.code(1, "BlockChange {0}>{1}: {2} -- {3}".format(
                oldActiveBlock, self._activeBlock, line, self._currentPath.filePath))


    def _detect_line_comment(self, line, scanningMultiLine):
        '''
        Check for single and multi-line comment
        '''
        onCommentLine = False

        # Get rid of whitespace for better comment detection
        stripLine = line.strip()
        

        # TBD -- refactor to cache different versions of string for the
        # current line, and process them in self.  Don't do for Python
        # since comments look like strings; sigh.
        if not self._pythonFile:
            stripLine = self._strip_string_literals(stripLine)

        # Single line comments
        if not scanningMultiLine:
            if self.reSingleLineComments.match(stripLine):
                onCommentLine = True

        # Multi-line comments
        if not onCommentLine:
            if scanningMultiLine:
                # We're inside a multi-line comment, check for closure
                onCommentLine = True
                if self.reMultiLineCommentsClose.search(stripLine):
                    scanningMultiLine = False
            else:
                # Check for start of multiline comment
                match = self.reMultiLineCommentsOpen.search(stripLine)
                if match:
                    onCommentLine = True
                    scanningMultiLine = True
                    # Special handling for closure of multi-line comment on same line
                    closeMatch = self.reMultiLineCommentsClose.search(
                                    match.group(self.RE_GROUP_REMAINING_LINE))
                    if closeMatch:
                        scanningMultiLine = False
                        # Special handling of whether we count comments that open
                        # and close on the same line as comments -- need to figure out
                        # if there is anything else on the line
                        if not self._sameLineMultiCloseAsComment:
                            remainingLine = closeMatch.group(self.RE_GROUP_REMAINING_LINE)
                            commentFirst = self.reMultiLineCommentsOpen.match(stripLine)
                            if not commentFirst or remainingLine.strip():
                                onCommentLine = False

        return onCommentLine, scanningMultiLine


    def _detect_blank_line(self, line):
        '''
        Allows for overriding counting of "blank" line
        '''
        if (    self.reBlankLine.match(line) or
                (self.blankXmlLines and self.reBlankXmlLine.match(line)) or
                (self.reBlankLineAdd and self.reBlankLineAdd.match(line))
            ):
            self.counts['BlankLines'][self._activeBlock] += 1
            self._trace_line(line, "B")
            return True
        else:
            return False


    def _measure_line(self, line, onCommentLine):
        '''
        Allow for overriding how comment and NBNC lines are captured
        the default is to just separate comments and NBNC
        '''
        if onCommentLine:
            self._trace_line(line, "C")
            self.counts['CommentLines'][self._activeBlock] += 1
        else:
            self._trace_line(line)
            self.counts['MeasureLines'][self._activeBlock] += 1


    def _analyze_line(self, line, analysis, onCommentLine):
        '''
        Placeholder for specializations to do line by line analysis
        '''
        pass


    def _strip_string_literals(self, line):
        '''
        Remove bodies of strings as per reStringLiteral to allow for re
        measurements that won't be messed up by string content
        '''
        return self.reStringLiteral.sub('', line).strip()



    #-------------------------------------------------------------------------
    #  Prvoide debug output for tuning regular expressions

    def _trace_line(self, line, commentPrefix=None, level=None):
        if self._traceLevel:
            if level is None:
                level = self._trace_block_level()
            if commentPrefix is not None:
                trace.notcode(level, self._trace_line_str(line, commentPrefix))
            else:
                trace.code(level, self._trace_line_str(line))

    def _trace_block_level(self):
        # We care most about the first code block, so trace it at level 3
        if self._activeBlock == 0:
            return 3
        else:
            return 4

    def _trace_line_str(self, line, prefix =""):
        return "{0}{1}: {2}".format(prefix, sum(self.counts["RawLines"]), line)




