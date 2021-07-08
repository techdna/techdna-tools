#=============================================================================
'''
    Surveyor file extension support

    Adds behaviors to default fnmatch matching

        1) Multile filters separated with ';'
        2) NO_EXT for specifying files with no extension
        3) EX: option for excluding the given extension
        4) RE: option for a custom regex filter (not using fnmatch.translate)

    We implement our own fnmatch.match because some recent Python
    versions have cache of compiled re that is set to 100, which is too low
    for many Surveyor scenarios, causing LOTS of overhead because re.compile
    is called frequently during initial folderwalk in main process.
    This can massively slow down a job because the folderwalk can't fill
    the job queue fast enough.
'''
#=============================================================================
# Copyright 2004-2012, Matt Peloquin and Construx. This file is part of Code
# Surveyor, covered under GNU GPL v3 and is distributed WITHOUT ANY WARRANTY.
#=============================================================================
import os
import re
import fnmatch

# Special tokens we allow in filter patterns
BLANK_FILE_EXT = 'NO_EXT'
EXCLUDE_FILE_EXT = 'EX:'
EX_DELIM_CHAR = ':'
CUSTOM_FILE_REGEX = 'RE:'

# Dictionary of compiled re objects for file filters
_FilterCache = {}

# We handle file system case sensitivity in the RE we build for each
# each file mask. Note that our check could potentially fail if Surveyor
# is being run on windows and pointed at a posix file system -- but
# Python lib fnmatch which uses os.path.normcase has same issue.
RE_OPTIONS = 0
if os.name in ['nt', 'os2', 'posix']:
    RE_OPTIONS = re.IGNORECASE


def file_ext_match(fileName, fileFilter):
    '''
    Implement fnmatch with no-extension and exlcude extension capability
    '''
    if not fileFilter:
        return True

    # Exclusion filters allow for groups of excluded file types
    if fileFilter.startswith(EXCLUDE_FILE_EXT):
        negativeFilters = fileFilter.replace(EXCLUDE_FILE_EXT, '').split(EX_DELIM_CHAR)
        negMatch = False
        for negFilter in negativeFilters:
            if _file_match(fileName, negFilter):
                negMatch = True
                break
        return not negMatch
    else:
        return _file_match(fileName, fileFilter)


def file_matches_filters(fileName, fileFilters):
    '''
    Provide capability similar to fnmatch.filter
    Returns the matching filter if found, None otherwise
    An empty filter list matches anything
    '''
    if not fileFilters:
        return True
    for fileFilter in fileFilters:
        if file_ext_match(fileName, fileFilter):
            return fileFilter
    return None


def _file_match(fileName, fileFilter):
    '''
    Performs the match check of filename to filter
    In the case of blank detection, look for no extension
    Otherwise use regex comparison using cached version of either the
    re from fnmatch.translate or custom RE string provided in filter
    '''
    if BLANK_FILE_EXT == fileFilter:
        root, ext = os.path.splitext(fileName)
        return '' == ext and not root.startswith('.')
    else:
        filterRe = None
        try:
            filterRe = _FilterCache[fileFilter]
        except KeyError:
            if fileFilter.startswith(CUSTOM_FILE_REGEX):
                filterRe = re.compile(fileFilter.replace(CUSTOM_FILE_REGEX, ''), RE_OPTIONS)
            else:
                filterRe = re.compile(fnmatch.translate(fileFilter), RE_OPTIONS)
            _FilterCache[fileFilter] = filterRe

        return filterRe.match(fileName) is not None
