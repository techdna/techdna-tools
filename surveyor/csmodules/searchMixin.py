#=============================================================================
'''
    Search Mix-in Functionality for csmodules

    Provides shared implementation for Surveyor modules to manage
    searches defined by extra prarameters in config files
'''
#=============================================================================
# Copyright 2004-2010, Matt Peloquin and Construx. This file is part of Code
# Surveyor, covered under GNU GPL v3 and is distributed WITHOUT ANY WARRANTY.
#=============================================================================
import re
from framework import trace
from framework import basemodule

class _searchMixin( object ):

    # Config file prefixes, used in the search expressing list to identify
    # whether an expression is intended as a postive or negative match
    POS_CONFIG_PREFIX = "POSITIVE__"
    NEG_CONFIG_PREFIX = "NEGATIVE__"

    # We truncate string hits we report to avoid problems from
    # scanning files with really long "lines"
    MAX_STR_LEN = 255

    ConfigOptions_Search = {
        'SEARCH_CASE_SENSITIVE': (
            'self._searchReFlags &= ~re.IGNORECASE',
            'Will make search regular expressions case insensitive'),
        }

    @classmethod
    def _cs_config_options(cls):
        return cls.ConfigOptions_Search


    #-------------------------------------------------------------------------
    # Overloadable functions we need to provide super calls for to
    # ensure we don't break MRO chain

    def __init__(self, options):
        super(_searchMixin, self).__init__(options)

    def _measure_line(self, line, onCommentLine):
        super(_searchMixin, self)._measure_line(line, onCommentLine)


    #-------------------------------------------------------------------------
    # Overrides used in search behavior

    def _cs_init_config_options(self):
        super(_searchMixin, self)._cs_init_config_options()

        # Default RE compile options for search REs loaded from config files
        self._searchReFlags = re.IGNORECASE | re.VERBOSE


    def add_param(self, param, rawParam):
        '''
        Default implementation for config params assumes a regular expression that
        may have positive or negative prfeix.
        Return a tuple of (pos/neg, rawParamStr, compiledRE)
        '''
        positiveSearch = True
        param = param.strip()
        if param.startswith(self.NEG_CONFIG_PREFIX):
            positiveSearch = False
            param = param[len(self.NEG_CONFIG_PREFIX):]
        elif param.startswith(self.POS_CONFIG_PREFIX):
            param = param[len(self.POS_CONFIG_PREFIX):]
        regEx = re.compile(param, self._searchReFlags)
        trace.search(2, "Adding {0} Search: {1} ({2})".format(bool(positiveSearch), param, self._searchReFlags))
        return (positiveSearch, ' '.join(rawParam.split()), regEx)


    #-------------------------------------------------------------------------
    # Methods used by

    def _setup_search_strings(self, configParams):
        '''
        Setup the positive and negative regex counting dictionary
        for all our search expressions created in add_param
        '''
        positiveSearches = {}
        negativeSearches = {}
        for positiveSearch, rawParam, regEx in configParams:
            if positiveSearch:
                positiveSearches[rawParam] = [regEx, 0]
            else:
                negativeSearches[rawParam] = [regEx, 0]
        return positiveSearches, negativeSearches


    def _first_match(self, searchTarget, positiveSearches, negativeSearches, negativeFirst=False):
        '''
        Match object for the first positive match that has no negative matches,
        with option on which to check first
        If no positive match (including a negative hit), returns None
        Otherwise returns keyName of match and the match object
        Searches dicts have count that is incremented in place
        '''
        if trace.level(): trace.search(4, "Searching: {0}".format(searchTarget))
        matchTuple = None
        if negativeFirst:
            if not self._is_negative_match(searchTarget, negativeSearches):
                matchTuple = self._find_positive_match(searchTarget, positiveSearches)
        else:
            matchTuple = self._find_positive_match(searchTarget, positiveSearches)
            if matchTuple:
                if self._is_negative_match(searchTarget, negativeSearches):
                    matchTuple = None
        return matchTuple


    #-------------------------------------------------------------------------
    # Internal implementation

    def _find_positive_match(self, searchTarget, positiveSearches):
        for posString, (posRegExp, posCount) in positiveSearches.iteritems():
            if trace.level(): trace.search(3, "  PositiveCheck: {0} > {1}".format(
                                           searchTarget, posRegExp.pattern))

            match = posRegExp.search(searchTarget)

            if match:
                positiveSearches[posString][1] = posCount + 1
                if trace.level(): trace.search(1, "PositveHit: {0} > {1}".format(
                                            str(match.group()), posRegExp.pattern))
                return posString, match

        return None


    def _is_negative_match(self, searchTarget, negativeSearches):
        for negString, (negRegExp, negCount) in negativeSearches.iteritems():
            if trace.level(): trace.search(2, "  NegativeCheck: {0} > {1}".format(
                                            negRegExp.pattern, searchTarget))

            negMatch = negRegExp.search(searchTarget)

            if negMatch:
                negativeSearches[negString][1] = negCount + 1
                if trace.level(): trace.search(1, "  NegativeHit: {0} > {1}".format(
                                            str(negMatch.group()), negRegExp.pattern))
                return True

        return False