#=============================================================================
'''
    General searching of files
    See surveyor.examples for examples of setting up searches

    Line-by-Line
    ============
    Provides searches of file lines with NO parsing of code.
    May have both positive and negative search criteria for each line.

    For each line a match is found when:

        - None of the negative expressions are matched
        - At least one positive expression is matched

    The definition in the config file is as follows:

        search Search  [measureFilter] [fileFilter] [tag1] [outFileName]
            posSearch1
            POSITIVE__posSearch2
            NEGATIVE__negSearch1
            NEGATIVE__negSearch2
        search_end

    If no prefix is provided, a positive search is assummed. Other assumptions:

        - Regular Expressions may (should) be used
        - Lines will have leading spaces stripped.
        - The search is CASE INSENSITIVE by default

    Multi-line
    ==========
    In multi-line mode, search REs are matched against the entire file, which
    allows for REs to span lines.

'''
#=============================================================================
# Copyright 2004-2011, Matt Peloquin and Construx. This file is part of Code
# Surveyor, covered under GNU GPL v3 and is distributed WITHOUT ANY WARRANTY.
#=============================================================================
from framework import basemodule
from framework import trace
from framework import utils
from searchMixin import _searchMixin


class Search( _searchMixin, basemodule._BaseModule ):
    '''
    Search functionality similar to, but separate from that provided
    in Code -- every line is searched.
    '''
    VERB_SEARCH       = "search"
    VERB_SEARCH_MULTI = "search_multi"
    VERB_SEARCH_END   = "search_end"

    LINES_TOTAL      = "file.total"
    SEARCH_TOTAL     = "search.total"
    SEARCH_MATCH     = "search.match"
    SEARCH_LINE      = "search.line"
    SEARCH_LINENUM   = "search.linenum"
    SEARCH_CONFIG_RE = "search.regex"
    SEARCH_REGEXP    = "search.regex-full"


    def __init__(self, options):
        super(Search, self).__init__(options)

        self.verbs = [self.VERB_SEARCH, self.VERB_SEARCH_MULTI]
        self.verbEnds = { self.VERB_SEARCH: self.VERB_SEARCH_END,
                self.VERB_SEARCH_MULTI: self.VERB_SEARCH_END }
        self.measures = [ "search.*", self.LINES_TOTAL ]

    @classmethod
    def _cs_config_options(cls):
        return {}

    def _cs_init_config_options(self):
        super(Search, self)._cs_init_config_options()
        self._configOptionDict.update(self.ConfigOptions_Search)


    def _survey(self, linesToSurvey, configEntry, measurements, analysis):
        if linesToSurvey:
            if self.VERB_SEARCH == configEntry.verb:
                self._search(linesToSurvey, configEntry, measurements, analysis)
            elif self.VERB_SEARCH_MULTI == configEntry.verb:
                self._search_multi(linesToSurvey, configEntry, measurements, analysis)
            else:
                utils.CsModuleException("Search csmodule only intended for 'search' or 'search_multi' verb")
        return bool(analysis)


    def _search(self, lines, configEntry, measurements, analysis):
        '''
        Loop through the lines, comparing each aginst
        both the positve and negative list of search strings provided.
        '''
        positiveSearches, negativeSearches = self._setup_search_strings(
                configEntry.paramsProcessed)

        val_TotalHits = 0
        val_TotalLines = 0
        try:
            for rawLine in lines:
                line = utils.strip_null_chars(rawLine)
                val_TotalLines += 1

                matchTuple = self._first_match(line, positiveSearches, negativeSearches)
                if matchTuple:
                    origPatternStr, match = matchTuple
                    val_TotalHits += 1

                    # We may be searching binaries, so take some steps to clean up
                    # the line string we export
                    cleanSearchLine = line.strip()
                    cleanSearchLine = cleanSearchLine[:self.MAX_STR_LEN]
                    cleanSearchLine = utils.safe_ascii_string(cleanSearchLine)
                    cleanSearchLine = utils.strip_annoying_chars(cleanSearchLine)

                    # Export the findings
                    analysisItem = {}
                    analysisItem[ self.SEARCH_LINE       ] = cleanSearchLine[:self.MAX_STR_LEN]
                    analysisItem[ self.SEARCH_LINENUM    ] = val_TotalLines
                    analysisItem[ self.SEARCH_CONFIG_RE  ] = origPatternStr
                    analysisItem[ self.SEARCH_REGEXP     ] = utils.get_match_pattern(match)[:self.MAX_STR_LEN]
                    analysisItem[ self.SEARCH_MATCH      ] = utils.get_match_string(match)[:self.MAX_STR_LEN]
                    analysis.append(analysisItem)

        except Exception, e:
            raise utils.CsModuleException("Error {0}\n...searching line: {1}".format(
                    str(e), str(val_TotalLines)))

        # Populate the measurement results with fixed totals
        if val_TotalHits > 0:
            measurements[self.LINES_TOTAL] = val_TotalLines
            measurements[self.SEARCH_TOTAL] = val_TotalHits


    def _search_multi(self, lines, configEntry, measurements, analysis):
        '''
        Use multi-line searches
        '''
         # Make sure lines represents the text of the file
        try:
            lines = lines.read()
        except AttributeError:
            pass
        lines = utils.strip_null_chars(lines)

        positiveSearches, negativeSearches = self._setup_search_strings(
                configEntry.paramsProcessed)
        matchTuple = self._first_match(lines, positiveSearches, negativeSearches)
        if matchTuple:
            origPatternStr, match = matchTuple
            analysisItem = {}
            analysisItem[self.SEARCH_CONFIG_RE] = origPatternStr
            analysisItem[self.SEARCH_REGEXP] = utils.get_match_pattern(match)[:self.MAX_STR_LEN]
            analysisItem[self.SEARCH_MATCH] = utils.get_match_string(match)
            analysis.append(analysisItem)





