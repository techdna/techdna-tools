#=============================================================================
'''
    Logic for walking folders, selecting files to be processed,
    and providing the configEntry information for the files.
'''
#=============================================================================
# Copyright 2004-2011, Matt Peloquin and Construx. This file is part of Code
# Surveyor, covered under GNU GPL v3 and is distributed WITHOUT ANY WARRANTY.
#=============================================================================
import os
import fnmatch

from framework import configstack
from framework import fileext
from framework import utils
from framework import trace

class FolderWalker( object ):
    '''
    One instance is created for each job
    A callback is used to allow us to update caller on progress on
    a per-folder basis.
    Errors are not caught here
    '''
    def __init__(self, deltaPath, configStack,
                expandSubdirs, includeFolders, skipFolders, fileFilters, skipFiles,
                add_files_callback):
        self._add_files_to_job = add_files_callback
        self._deltaPath = deltaPath
        self._configStack = configStack
        self._expandSubdirs = expandSubdirs
        self._includeFolders = includeFolders
        self._skipFolders = skipFolders
        self._fileExtFilters = fileFilters
        self._skipFiles = skipFiles

        # Cache both the set of possible file filters for a config file, and config
        # entries for config file extensions. This avoids much redundant looping to
        # match config items to files
        self._configFilterCache = {}
        self._configEntryCache = {}


    def walk(self, pathToMeasure):
        '''
        Walk folders while filtering sending updates via callback
        We may be asked to terminate in our callback
        '''
        self._configStack.set_measure_root(pathToMeasure)

        for folderName, childFolders, fileNames in os.walk(pathToMeasure, topdown=True):
            trace.file(2, "Scanning: {0}".format(folderName))

            numUnfilteredFiles = len(fileNames)
            if numUnfilteredFiles == 0:
                trace.file(1, "WARNING - No files in: {0}".format(folderName))

            filesAndConfigs = []

            if fileNames and self._valid_folder(folderName):

                # Get the current set of active config filters
                fileFilters, activeConfigs, configPath = self._configStack.get_configuration(folderName)

                # Filter out files by options and config items
                filesToProcess = self._get_files_to_process(folderName, fileNames, fileFilters, configPath)

                # Create list of tuples with fileName and configEntrys for each file
                for fileName, fileFilter in filesToProcess:
                    configEntrys = self._get_configs_for_file(fileName, fileFilter, activeConfigs, configPath)
                    filesAndConfigs.append((fileName, configEntrys))

            # For delta measure create a fully qualified delta path name
            # Note when we split on path to measure, it will start with seperator
            deltaFolder = None
            if self._deltaPath is not None:
                deltaFolder = self._deltaPath + folderName[len(pathToMeasure):]

            # Call back to job with files and configs
            continueProcessing = self._add_files_to_job(
                        folderName,
                        deltaFolder,
                        filesAndConfigs,
                        numUnfilteredFiles)

            if not continueProcessing or not self._expandSubdirs:
                break

            # Remove any folders, and sort remaining to ensure consistent walk
            # order across file systems (for our testing if nothing else)
            self._remove_skip_dirs(folderName, childFolders)
            childFolders.sort()


    def _valid_folder(self, folderName):
        '''
        Is this folder one we should process?
        '''
        if not self._skipFolders and not self._includeFolders:
            return True

        validFolder = True

        # First verfiy this folder is not to be skipped
        if self._skipFolders:
            _root, currentFolder = os.path.split(folderName)
            for folderPattern in self._skipFolders:
                if fnmatch.fnmatch(currentFolder, folderPattern):
                    trace.file(1, "Skipping folder: {0}".format(folderName))
                    validFolder = False
                    break

        # Next verify if it is on the include list
        if validFolder and self._includeFolders:
            includeMatch = False
            for folderPattern in self._includeFolders:
                if fnmatch.fnmatch(folderName, folderPattern):
                    includeMatch = True
                    break
            if not includeMatch:
                trace.file(1, "Excluding folder: {0}".format(folderName))
                validFolder = False

        return validFolder


    def _get_files_to_process(self, folderName, fileNames, fileFilters, configPath):
        '''
        Filter the list of files based on command line options and active
        config file filters
        '''
        # if fileFilters is empty it means an empty config file, so skip all files
        if not fileFilters:
            return []

        # Optimize the most common matching of extensions by creating cache of
        # simple '*.xxx' extensions from config filters for each config file
        filterExts = []
        try:
            filterExts = self._configFilterCache[configPath]
        except KeyError:
            filterSplits = [os.path.splitext(fileFilter) for fileFilter in fileFilters if
                                os.path.splitext(fileFilter)[0] == '*']
            filterExts = [ext for _root, ext in filterSplits]
            self._configFilterCache[configPath] = filterExts

        # Select files based on matching filters
        filesToProcess = []
        for fileName in fileNames:

            # Filter file list by command-line postive filter, if provided
            if fileext.file_matches_filters(fileName, self._fileExtFilters):

                # Optimize most common case of direct match of file extension, then
                # fall back to doing a full filter match on config file filter
                _root, fileExt = os.path.splitext(fileName)
                fileFilter = None
                if fileExt in filterExts:
                    fileFilter = '*' + fileExt
                else:
                    fileFilter = fileext.file_matches_filters(fileName, fileFilters)
                if fileFilter is not None:
                    filesToProcess.append((fileName, fileFilter))

        # Remove files that should be skipped
        if self._skipFiles:
            filesToProcess = [(fileName, fileFilter) for fileName, fileFilter in filesToProcess if
                                not fileext.file_matches_filters(fileName, self._skipFiles)]
        return filesToProcess


    def _get_configs_for_file(self, fileName, fileFilter, activeConfigs, configPath):
        '''
        Return only the needed config items for the given file
        We use a cache based on file filter. This optimizes for the single
        config file case.
        '''
        configEntrys = None
        keyName = str(configPath) + str(fileFilter)
        try:
            configEntrys = self._configEntryCache[keyName]
        except KeyError:
            configEntrys = configstack.config_items_for_file(activeConfigs, fileName)
            self._configEntryCache[keyName] = configEntrys
        return configEntrys


    def _remove_skip_dirs(self, root, dirs):
        '''
        Decide what children dirs should be skipped
        Filter out dirs in place (vs a copy), so os.walk will skip
        '''
        dirsToRemove = []
        for folderPattern in self._skipFolders:
            dirsToRemove += fnmatch.filter(dirs, folderPattern)
        dirsToRemove = set(dirsToRemove)

        for folder in dirsToRemove:
            trace.file(1, "Skipping over: {0}\\{1}".format(root, folder))
            dirs.remove(folder)


