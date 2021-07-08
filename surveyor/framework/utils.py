#=============================================================================
'''
    Utility classes and routines shared by Surveyor components
'''
#=============================================================================
# Copyright 2004-2010, Matt Peloquin and Construx. This file is part of Code
# Surveyor, covered under GNU GPL v3 and is distributed WITHOUT ANY WARRANTY.
#=============================================================================
import os
import sys
import time
import chardet
import magic

#-----------------------------------------------------------------------------
#  OS Defaults we may want to make dynamic some day

CURRENT_FOLDER = '.'
CONSOLE_CR = "\r"

# Confidence from chardet that we'll accept on detecting an encoding
# see open_chardet
ENCODING_DETECTION_THRESHHOLD = 0.50

#-----------------------------------------------------------------------------
#  Exceptions

class SurveyorException(Exception):
    pass

class JobException(SurveyorException):
    pass

class InputException(SurveyorException):
    pass

class OutputException(SurveyorException):
    pass

class ConfigError(SurveyorException):
    pass

class CsModuleException(SurveyorException):
    pass

class FileMeasureError(SurveyorException):
    pass

class AbstractMethod(SurveyorException):
    def __init__(self, obj):
        self.methodName = sys._getframe(1).f_code.co_name
        self.className = obj.__class__.__name__
    def __str__(self):
        return "Abstract method called: {0}.{1}()".format(
            self.className, self.methodName)


#-----------------------------------------------------------------------------
#  Timing Utils

_timings = {}

def timing_start():
    timing_set('START_RUN')

def timing_elapsed():
    return timing_get('START_RUN')

def timing_set(checkpointName='DEFAULT'):
    _timings[checkpointName] = time.time()

def timing_get(checkpointName='DEFAULT'):
    return time.time() - _timings[checkpointName]


#-----------------------------------------------------------------------------
# General utils

def safe_dict_get(dictionary, keyName):
    value = None
    if dictionary is not None:
        value = dictionary.get(keyName, None)
    return value

def safe_dict_get_float(dictionary, keyName):
    try:
        return float(safe_dict_get(dictionary, keyName))
    except Exception:
        return 0.0

# In Python3 we have to implement our own magic autodetection
# of binary/text and charsets
def open_chardet(fpath):
    my_magic = magic.Magic(mime=True, uncompress=True)
    if not my_magic.from_file(fpath).startswith('text/'):
        return open(fpath, 'rb')

    # looks like text, use chardet to figure out encoding
    fh = open(fpath, 'rb')
    buf = fh.read(16 * 1024)
    res = chardet.detect(buf)
    # DEBUG - print(res)
    fh.close()

    # Search through detected encodings - they could be a single encoding or
    # a list of dictionaries in
    # this form: {'encoding': 'ascii', 'confidence': 1.0, 'language': ''}
    # and find if any is detected with better than 90% confidence.  if not,
    # open the file as binary
    encoding_found = None
    encoding_confidence = 0
    if isinstance(res, list):
        for encoding in res:
            # Work through the encoding list,
            # pick the one with the highest confidence score
            # DEBUG print('Considering {0}'.format(encoding))
            if encoding.get('confidence') >= encoding_confidence:
                encoding_found = encoding.get('encoding')
                encoding_confidence = encoding.get('confidence')
    else:
        encoding_found = res.get('encoding')
        encoding_confidence = res.get('confidence')

    # DEBUG print('Using {0}'.format(use_encoding))
    if encoding_found is None or encoding_confidence < ENCODING_DETECTION_THRESHHOLD:
        # chardet could not figure out encoding, or has very low confidence
        # DEBUG - print('No encoding detected with confidence >= {0} - using binary'.format(ENCODING_DETECTION_THRESHHOLD))
        fh = open(fpath, 'rb')
    else:  # use encoding detected
        # DEBUG - print('Encoding detected {0}'.format(enc))
        fh = open(fpath, 'r', encoding=encoding_found, errors="surrogateescape")
    return fh

#-----------------------------------------------------------------------------
# String and RE utils

def get_match_string(match):
    '''
    Returns the first match string with something in it
    '''
    for matchStr in match.groups():
        if matchStr:
            return str(matchStr).strip()
    return ""

def get_match_pattern(match):
    return str(match.re.pattern)


def check_bytes_below_threshold(byteStr, chars, minWin, startPos, threshold):
    '''
    If the ratio of bytes not in chars is above the given threshold
    (within the startPos and minWin window size) return false
    '''
    #DEBUG print "Bytes: {0}".format(byteStr)
    isBelowThreshold = True
    bytePos = 0
    badChars = 0
    # One byte at a time, bailing if we exceed threshold
    for char in byteStr:
        bytePos += 1
        if bytePos < startPos:
            continue
        if isinstance(char, int):
            try:
                char = chr(char)
            except ValueError:
                badChars += 1
                break
        if not char in chars:
            badChars += 1
            #DEBUG print("check_bytes_below_threshold - binary char at {0}: {1}".format(bytePos, char))
        if bytePos >= minWin or bytePos == len(byteStr):
            badCharRatio = float(badChars)/float(bytePos)
            if badCharRatio > threshold:
                #DEBUG print("check_bytes_below_threshold - badCharRatio {0} exceeds threshold of {1} - file is suspected as binary".format(badCharRatio,threshold))
                isBelowThreshold = False
                break
    return isBelowThreshold


def check_start_phrases(searchString, phrases):
    '''
    Do any of the provided phrases match the start of searchString?
    '''
    phraseFound = None
    for phrase in phrases:
        if searchString.startswith(phrase):
            phraseFound = phrase
            break
    return phraseFound


def strip_null_chars(rawString):
    '''
    In 2 or 4 byte (UTF-16, UTF32) unicode conversion, null chars may be
    inserted into an Ascii string
    TBD -- make search UTF/Unicode aware
    '''
    if isinstance(rawString, str):
        return rawString.replace('\00', '')
    else:
        return rawString.replace(b'\00', b'')


AnnoyingChars = ''.join([chr(byte) for byte in range(0, 31)])
AnnoyingCharsTable=str.maketrans(AnnoyingChars, '_' * len(AnnoyingChars))
def strip_annoying_chars(rawStr):
    '''
    Get rid of annoying characters that can mess up display
    '''
    newStr = rawStr.rstrip()
    newStr = newStr.expandtabs(2)                   # Make tabs consistent and small
    newStr = newStr.replace('\n', ' <\n> ')         # Avoid embedded newlines
    newStr = newStr.translate(AnnoyingCharsTable)   # Beeps, linefeeds, etc.
    return  newStr


ExtendedChars = ''.join([chr(byte) for byte in range(127, 255)])
def strip_extended_chars(rawStr):
    '''
    Get rid of binary characters
    '''
    return rawStr.translate(None, ExtendedChars)


def safe_ascii_string(byteStr):
    '''
    If the standard ASCII conversion has a Unicode error, attempt a
    unicode escaped encoding converted back to ASCII
    '''
    if byteStr is None:
        return ""
    try:
        return str(byteStr)
    except UnicodeEncodeError:
        return str(str(byteStr).encode('unicode_escape'))


def safe_utf8_string(byteStr):
    '''
    Convert a given string into a UTF8 string; if not possible,
    do an escapted convert to ASCII and then to UTF
    '''
    if byteStr is None:
        return ""
    try:
        return str(byteStr, 'utf8', 'replace')
    except UnicodeEncodeError:
        ascii = str(byteStr).encode('string_escape')
        return str(ascii)


def fit_string(fullString, maxLen, replacement="...", tailLen=None):
    '''
    Shorten strings to fit into maxlen, e.g,  "The quick brown...azy dog"
    '''
    newString = fullString
    if not maxLen <= 0 and len(newString) > maxLen:
        if not tailLen:
            tailLen = int(maxLen/2)
        replacementPos = maxLen - len(replacement) - tailLen
        shortendString = newString[:replacementPos] + replacement
        if tailLen > 0:
            shortendString += newString[-tailLen:]
        newString = shortendString
    return newString


MAX_RANK = sys.maxsize
def match_ranking_label(rankingMap, value):
    '''
    Match a ranking label to a value, based on list a of rankValue/name pairs
    where the rankValue defines the top end of the rank
    '''
    label = ""
    if not (value == ""):
        for (threshold, rank) in rankingMap:
            if float(value) <= float(threshold):
                label = rank
                break
    return label

#-----------------------------------------------------------------------------
#  File utils

def get_file_mod_time_str(filePath, dateFormat):
    # We want the content modification time, which st_mtime should give
    # across all OS
    fileStats = os.stat(filePath)
    return time.strftime(dateFormat, time.localtime(fileStats.st_mtime))

def get_file_size(filePath):
    fileStats = os.stat(filePath)
    return int(fileStats.st_size)

def get_file_start(fileObject, maxWin):
    '''
    Get maxWin bytes and put the file back the way we found it
    '''
    fileObject.seek(0)
    fileStart = fileObject.read(maxWin)
    fileObject.seek(0)
    return fileStart


class SurveyorPathParser( object ):
    '''
    Provide common parsing of file paths as an object
    Upon instantiation, fill members with parsed path info
    '''
    def __init__(self, rawFilePath):

        # Remove leading slash, if any, such that the first folder position
        # will be a sub-folder. If this is a root path of a search, it is
        # represented by having an empty dirlist
        filePath = rawFilePath[1:] if rawFilePath[0] == os.sep else rawFilePath
        splitFilePath = filePath.split(os.sep)

        # Pop file name off the end of our path list
        fileName = splitFilePath.pop()
        (fileNameNoExt, fileExt) = os.path.splitext(fileName)

        # Initialize file name variations
        self.filePath = rawFilePath
        self.folder = os.path.dirname(rawFilePath)
        self.dirList = [safe_ascii_string(dirItem) for dirItem in splitFilePath]
        self.dirLength = len(self.dirList)
        self.fileName = safe_ascii_string(fileName)
        self.fileNameNoExt = safe_ascii_string(fileNameNoExt)
        self.fileExt = safe_ascii_string(fileExt)

    def __repr__(self):
        return self.dirList
    def __str__(self):
        return self.filePath


#-----------------------------------------------------------------------------
#  System utils

def running_as_exe():
    '''
    If the frozen attribute is present, we're in py2exe
    otherwise we're in script
    '''
    return hasattr(sys, "frozen")

def runtime_ext():
    return "" if running_as_exe() else ".py"

def runtime_dir():
    '''
    Return the directory that the job is being run from
    Surveyor does not manipulate CWD, so we assume it is accurate
    '''
    return os.path.abspath(os.getcwd())


'''
    Surveyor Dir

    In a Py2Exe compiled program, sys.argv[0] will not always return
    the fully qualified path of the running program, but
    sys.executable will in that case

    Also, to support testing, we don't want to rely on setting of
    sys.argv, so we initialize it at run time
'''
StartupPath = None

def surveyor_dir():
    '''
    Return the directory that the surveyor script was loaded from
    '''
    assert StartupPath is not None
    return StartupPath

def init_surveyor_dir(arg0):
    '''
    This must be called before calling surveyor_dir
    '''
    global StartupPath
    if running_as_exe():
        StartupPath = sys.executable
    else:
        StartupPath = arg0
    StartupPath = os.path.abspath(os.path.dirname(StartupPath))
