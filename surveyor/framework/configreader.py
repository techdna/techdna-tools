#=============================================================================
'''
    ConfigReader
    Encapsulation of reading surveyor config files
'''
#=============================================================================
# Copyright 2004-2010, Matt Peloquin and Construx. This file is part of Code
# Surveyor, covered under GNU GPL v3 and is distributed WITHOUT ANY WARRANTY.
#=============================================================================
import os
import re

from framework import configentry
from framework import fileext
from framework import uistrings
from framework import trace
from framework import utils

# Special identifiers used with the config file
CONFIG_LINE_CONTINUE = r'\\'
CONFIG_DELIM_IGNORE_BEGIN = 'IGNORE_START'
CONFIG_DELIM_IGNORE_END = 'IGNORE_STOP'
CONFIG_DELIM_CONSTANT = 'CONSTANT'
CONFIG_DELIM_INCLUDE = 'INCLUDE'
CONT_LINE_START = "lineStart"
MAX_CONSTANT_REPLACE = 10


class ConfigReader( object ):
    '''
    Responsible for reading lines from config files and loading them
    into ConfigEntry objects
    '''
    def __init__(self, loadModuleCallback, extraLineContent=''):
        self._load_csmodule = loadModuleCallback
        self._extraLineContent = extraLineContent

        # Regular expressions for parsing the config files
        self._reFlags = re.IGNORECASE | re.VERBOSE
        self.blankLine = re.compile(
                r"^ \s* $", self._reFlags)
        self.comment = re.compile(
                r"^ \s* [#]", self._reFlags)
        self.ignoreStart = re.compile(
                r"^ \s*" + CONFIG_DELIM_IGNORE_BEGIN, self._reFlags)
        self.ignoreStop = re.compile(
                r"^ \s*" + CONFIG_DELIM_IGNORE_END, self._reFlags)
        self.continuedLine = re.compile(
                r"^ (?P<"+CONT_LINE_START+">.*)" + CONFIG_LINE_CONTINUE + "$",
                self._reFlags)
        self.constant = re.compile(
                r"^ \s*" + CONFIG_DELIM_CONSTANT + configentry.CONFIG_DELIM_CHAR +
                "(\S+?)" + configentry.CONFIG_DELIM_CHAR + "(.*)", self._reFlags)
        self.include = re.compile(
                r"^ \s*" + CONFIG_DELIM_INCLUDE + configentry.CONFIG_DELIM_CHAR +
                "(\S+?)" + configentry.CONFIG_DELIM_CHAR + "(.*)", self._reFlags)


    def read_file(self, filePath):
        '''
        Read a Surveyor configuration file and return a list of ConfigEntrys
        to be stored on the configuration stack with this folder location.
        '''
        try:
            trace.msg(1, "Config file: {0}".format(filePath))
            configEntries = self._read_file(filePath, [])
            self._validate_file(configEntries)
            trace.config(2, "Finsihed reading config file: {0}".format(filePath))
            trace.config(3, configEntries)
            return configEntries
        except Exception as e:
            raise utils.ConfigError(uistrings.STR_ErrorConfigFile.format(filePath, str(e)))


    def _read_file(self, filePath, configEntries):
        with open(filePath, 'r', errors="surrogateescape") as configFile:
            return self._parse_file(configFile, configEntries)


    def _parse_file(self, configFile, configEntries):
        '''
        Parse config file lines
        '''
        configEntry = configentry.ConfigEntry('_ _ _ _')  # Init to empty object to prevent PyChecker warnings
        constants = {}
        readingVerbs = False
        verbEndMarker = None
        for whiteSpaceRawline in configFile:
            trace.config(3, "Config line: {0}".format(whiteSpaceRawline))
            rawLine = whiteSpaceRawline.strip()
            line = rawLine

            # Skip comments, blank lines
            if self.comment.match(line) or self.blankLine.match(line):
                trace.config(4, "comment/blank")
                continue

            # Skip ignore blocks (or go to end of file if no closing block)
            if self.ignoreStart.match(line):
                trace.config(4, "ignoreBlock")
                try:
                    while not self.ignoreStop.match(line):
                        line = next(configFile)
                        trace.config(4, "Config ignore: {0}".format(line))
                except Exception:
                    trace.config(4, "Exception while seeking end of ignore block")
                    pass
                continue

            # Includes
            # Attempt to load the requested file and add it's entries
            # to our entries, in the form INCLUDE:path: tagInfo
            includeMatch = self.include.match(line)
            if includeMatch:
                includePath = includeMatch.group(1)
                newTags = includeMatch.group(2)
                if not os.path.isabs(includePath):
                    includePath = os.path.join(os.path.dirname(configFile.name), includePath)
                trace.config(1, "Include: {0}".format(includePath))
                newEntries = self._read_file(includePath, [])

                existingFileFilterStrings = [entry.fileFilter for entry in configEntries]
                for entry in newEntries:
                    # If an entry has already been defined with the SAME FILE FILTER STRING,
                    # the INCLUDED ENTRY WILL BE IGNORED
                    if entry.fileFilter in existingFileFilterStrings:
                        continue
                    # If 'tagInfo' is provided, it will be added to ALL entries of the file
                    # that was included
                    # We RELOAD THE MODULE in case new options need processed
                    if newTags:
                        entry.add_tags_and_options(newTags.split())
                        self._load_csmodule(entry)
                    configEntries.append(entry)
                continue

            # If line closes out a verb entry store the config entry
            if readingVerbs and re.match(verbEndMarker, line):
                trace.config(4, "verbend: {0}".format(line))
                readingVerbs = False
                configEntries.append(configEntry)
                continue

            # Handle continued lines
            fullLine = ""
            while True:
                contLineMatch = self.continuedLine.match(line)
                if contLineMatch:
                    fullLine += contLineMatch.group(CONT_LINE_START)
                    line = next(configFile).strip()
                    trace.config(3, "FullLine: {0}".format(line))
                else:
                    fullLine += line
                    break
            assert fullLine
            line = fullLine

            # Is this line defining a constant?
            constantMatch = self.constant.match(line)
            if constantMatch:
                constants[constantMatch.group(1)] = constantMatch.group(2)
                trace.config(4, "constant: {0}".format(constantMatch.group(2)))
                continue

            # Replace any constants used in the line
            line = self._replace_constants(line, constants)
            trace.config(4, "fullline: {0}".format(line))

            # Strip any inline comments
            line = line.split(' #')[0]

            # If the line is a parameter (e.g., search terms), delegate to module
            # to get processed parameters and store for later usage
            # We keep the unprocessed raw version around for consistency checking
            if readingVerbs:
                configEntry.paramsRaw.append(rawLine)
                try:
                    paramTuple = configEntry.module.add_param(line, rawLine)
                    configEntry.paramsProcessed.append(paramTuple)
                    trace.config(2, "LoadedParam: {0} => {1}".format(
                            configEntry.module.__class__.__name__, paramTuple))
                except Exception as e:
                    trace.traceback()
                    raise utils.ConfigError(uistrings.STR_ErrorConfigParam.format(
                            str(configEntry), rawLine, str(e)))

            # Otherwise assume we're at the start of a config entry definition,
            else:
                try:
                    # Load and validate the config line and its module
                    configEntry = configentry.ConfigEntry(line, self._extraLineContent, configFile.name)
                    self._load_csmodule(configEntry)
                    self._validate_line(configEntry)

                    # Check to see if there are parameter lines to read
                    verbEndMarker = configEntry.module.verb_end_marker(configEntry.verb)
                    if verbEndMarker is not None:
                        readingVerbs = True

                    # Add the completed config entry to our list
                    if not readingVerbs:
                        configEntries.append(configEntry)

                except Exception as e:
                    trace.traceback()
                    raise utils.ConfigError(uistrings.STR_ErrorConfigEntry.format(
                            rawLine, str(e)))

            # Loop to next line

        return configEntries


    def _validate_file(self, configEntries):
        if not configEntries:
            trace.config(2, "  EMPTY")
        else:
            try:
                self._validate_entries(configEntries)
            except Exception as e:
                trace.traceback()
                raise utils.ConfigError(uistrings.STR_ErrorConfigValidate.format(str(e)))


    #-------------------------------------------------------------------------

    def _replace_constants(self, line, constants):
        '''
        Allow for constants to be nested within each other, up to a limit
        '''
        lineReplacements = 0
        while True:
            lineReplacements += 1
            if lineReplacements > MAX_CONSTANT_REPLACE:
                raise utils.ConfigError(uistrings.STR_ErrorConfigConstantsTooDeep.format(
                        MAX_CONSTANT_REPLACE, line))

            oldLine = line
            for constantMatch, constantValue in constants.items():
                if not constantValue is None:
                    line = line.replace(
                            constantMatch, constantValue, MAX_CONSTANT_REPLACE)
            if oldLine == line:
                break

        return line


    def _validate_line(self, configEntry):
        '''
        Is the module being asked to do what it was designed to do?
        '''
        measureOk = configEntry.module.can_do_measure(configEntry.measureFilters)
        verbOk = configEntry.module.can_do_verb(configEntry.verb)
        if not (measureOk and verbOk):
            raise utils.ConfigError(uistrings.STR_ErrorConfigInvalidMeasure.format(
                    configEntry.verb, configEntry.measureFilter))


    def _validate_entries(self, configEntries):
        '''
        Are all config file entries consistent with each other, to avoid silent
        double counting? Throws an error exception if not.
        '''
        trace.config(2, "Checking for duplicate config entries")

        # Create list of all possible measure/file combos
        # We ask the module to match each measure, to catch wildcard overlap
        fileFilters = []
        possibleMeasures = []
        for entry in configEntries:
            for fileFilter in entry.fileFilters:
                fileFilters.append(fileFilter)
                possibleMeasures.append((fileFilter, entry.measureFilter,
                        entry.moduleName, entry.verb, entry.tags, entry.paramsRaw))
        trace.config(4, fileFilters)
        trace.config(4, possibleMeasures)

        # Check that no file type would have a measure be double counted
        # If we have a problem, throw an exception based on the first problem item
        if len(fileFilters) > len(set(fileFilters)):
            while possibleMeasures:
                possibleMeasureTuple = possibleMeasures.pop()
                trace.config(2, "possibleMeasure: {0}".format(possibleMeasureTuple))
                (fileFilter, measureFilter, modName, verb, tags, extraParams) = possibleMeasureTuple

                # We don't attempt the do conflict resolution on regex files extensions,
                # both because it doesn't make sense
                if fileFilter.startswith(fileext.CUSTOM_FILE_REGEX):
                    continue

                # Shallow warning check for double counting by creatubg a list of entries
                # based on matching verb and file type
                warningList = [
                        (ff, mf, mn, v, t, ep)
                            for ff, mf, mn, v, t, ep in possibleMeasures if
                                v == verb and
                                fileext.file_ext_match(ff, fileFilter) ]
                if warningList:
                    trace.config(1, "WARNING - Possible double-count: {0}".format(str(warningList)))

                    # For the deep check look at tag values and measure filter
                    dupeList = [
                            (v, modName, mn, mf, fileFilter, ff, t, tags, ep, extraParams)
                                for ff, mf, mn, v, t, ep in warningList if
                                    len(t) == len(tags) and
                                    len(t) == len(set(t) & set(tags)) and
                                    entry.module.match_measure(mf, measureFilter) ]
                    if dupeList:
                        trace.msg(1, "ERROR - Double-count: {0}".format(str(dupeList)))
                        dupe = dupeList[0]
                        raise utils.ConfigError(uistrings.STR_ErrorConfigDupeMeasures.format(
                            dupe[0],
                            dupe[1], dupe[2],
                            dupe[3],
                            dupe[4], dupe[5],
                            dupe[6], dupe[7],
                            dupe[8], dupe[9]))


