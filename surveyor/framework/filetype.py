#=============================================================================
'''
    Support for determining file type
'''
#=============================================================================
# Copyright 2004-2010, Matt Peloquin and Construx. This file is part of Code
# Surveyor, covered under GNU GPL v3 and is distributed WITHOUT ANY WARRANTY.
#=============================================================================
import os
import string

from framework import utils
from framework import trace

#-------------------------------------------------------------------------
#  File Extentions Detection

# Compressed file Extentsions
CompressedFileExtensions = set([
    'zip', 'tgz' 'tar', 'gz', 'rar',
    ])
def is_compressed_ext(filePath):
    rv = False
    if _has_ext(filePath, CompressedFileExtensions):
        rv = True
    return rv

# Common file extentsions highly unlikely to contain code-related files
# We don't cast too wide a net with these extensions, since even popular file
# types may be used for code/config/data in some systems.
NonCodeFileExtensions = set([
    'svn', 'svn-base', 'scc', 'cvs',
    'exe', 'com', 'bin', 'dll', 'dylib', 'lib', 'mo', 'so', 'ko', 'a', 'o', 'obj',
    'jar', 'war', 'ear', 'pyc', 'class', 'pdb', 'pch', 'tlb', 'ocx',
    'cab', 'msi', '7z', 'iso', 'bak', 'rpm', 'lha', 'lhz',
    'csv', 'tsv', 'old', 'rc', 'resx',
    'doc', 'docx', 'dot', 'dotx', 'xls', 'xlsx', 'xlsm', 'ppt', 'pptx',
    'pdf', 'rtf', 'vsd', 'vsx', 'mdb',
    'png', 'jpg', 'jp2', 'gif', 'bmp', 'tif', 'tiff', 'tga', 'raw', 'ico',
    'avi', 'mpg', 'mpeg', 'm1v', 'm2v', 'm4v', 'wmv', 'dat', 'flv', 'avchd', 'mov',
    'wav', 'm4a', 'wma', 'mp2', 'mp3', 'aac', 'swa',
    'vhd', 'vmdk', 'vmem', 'vmss', 'vmx', 'vm',
    'er1','ai', 'eps','dxf', 'svg', 'wmf', 'ps','chm', 'hlp',
    ])

# Used to avoid detecting PDF as text
PdfExtensions = set(['pdf'])

def is_noncode_ext(filePath):
    rv = False
    if is_compressed_ext(filePath) or _has_ext(filePath, NonCodeFileExtensions):
        rv = True
        trace.file(3, "   NonCodeExt:  {0}".format(os.path.basename(filePath)))
    return rv

#-------------------------------------------------------------------------
#  File Start Detection

# Magic numbers and phrases
# Look for known magic numbers and phrases in file start
# We only include items that may not be consistently picked up by file extension
# because extension works well in most cases, and this is a more expensive
# operation since we need to open the file
NonCodeFileStart = [
    '\x7ELF',           # Linux/Unif ELF exe (often don't have file extensions)
    'PK\x03\x04',       # Many types of zipped file structure
    '\x1F\x8B\x08',     # Gzip
    ]
def is_noncode_file(fileObject):
    maxWindowSize = 30
    fileStart = utils.get_file_start(fileObject, maxWindowSize)
    phraseFound = utils.check_start_phrases(fileStart, NonCodeFileStart)
    trace.file(3, "   NonCodeFileStart({0}): {1} ==> {2}".format(
            phraseFound, fileStart, os.path.basename(fileObject.name)))
    return phraseFound is not None


# Text to non-text ratio
# Do an approximate check for a text file by looking at how many non-text
# bytes are at the start of the file
# This is our most expensive operation, so should be saved for last
# TBD -- expose tuning parameters to config?
def is_text_file(fileObject):

    textChars = string.letters + string.digits + string.punctuation + string.whitespace
    bytesToCheck = 128          # Big enough window to grab, but small for speed
    startPoint = 4              # Skip start of file, for hidden text codes
    minWindowSize = 32          # Get a big enough min window to be feasible
    nonTextThreshold = 0.2      # Have some tolerance to avoid false positives

    # Grab the first bytes of the file, STRIPPING NULLS (for unicode text files)
    fileBytes = utils.strip_null_chars(utils.get_file_start(fileObject, bytesToCheck))

    # Special case for PDF that looks like text but isn't
    if is_pdf_file(fileObject):
        isBelowThreshold = False
        trace.file(3,"   IsTextFile({0}): {1} ==> PDF File detected".format(
            isBelowThreshold, os.path.basename(fileObject.name)))
    else:
        isBelowThreshold = utils.check_bytes_below_threshold(
            fileBytes, textChars, minWindowSize, startPoint, nonTextThreshold)
        trace.file(3,"   IsTextFile({0}): {1} ==> {2}".format(
            isBelowThreshold, os.path.basename(fileObject.name), fileBytes))

    return isBelowThreshold


# TBD -- may use in future for more robust unicode support
TextFileType = [
    '\xEF\xBB\xBF',     # UTF-8
    '\xFF\xFE',         # UTF-16 LE or UTF-32 LE
    '\xFE\xFF',         # UTF-16 BE
    '\x00\x00\xFE\xFF', # UTF-32 BE
    ]

def is_pdf_file(fileObject):
    return _has_ext(fileObject.name, PdfExtensions)

#-------------------------------------------------------------------------

def _has_ext(filePath, extensions):
    '''
    Does file have an extension, stripping off any numeric only extensions
    '''
    fileExt = None
    while True:
        (base, extension) = os.path.splitext(filePath)
        fileExt = str(extension).strip('.')
        if fileExt.isdigit():
            filePath = base
        else:
            break
    trace.file(3, "   File Extension:  {0}".format(fileExt))
    return fileExt.lower() in extensions


