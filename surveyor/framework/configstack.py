#=============================================================================
'''
    ConfigStack
    Encapsulation of config file use and caching
'''
#=============================================================================
# Copyright 2004-2010, Matt Peloquin and Construx. This file is part of Code
# Surveyor, covered under GNU GPL v3 and is distributed WITHOUT ANY WARRANTY.
#=============================================================================
import os

from framework import configentry
from framework import configreader
from framework import fileext
from framework import uistrings
from framework import trace
from framework import utils
from framework.modules import CodeSurveyorModules


def config_items_for_file(configEntrys, fileName):
    '''
    Return a list of config items that match the given fileName
    '''
    neededConfigs = []

    # We don't know how many config entrys could be associated with a given
    # file extension (files could match more than one config file filter),
    # so we check against every config
    # If there are custom RE config filters, we include them no matter what,
    # since we can't just match them against the file extension
    for configFilter in configEntrys.keys():
        if fileext.file_ext_match(fileName, configFilter):
            for config in configEntrys[configFilter]:
                neededConfigs.append(config)

    # Make this a sorted list to ensure repeatble results in terms of
    # order files are processed. This doesn't normally matter, but can
    # be convienent and allows for single-threaded repeatability that
    # allows for comparison against test oracle
    neededConfigs.sort(key=lambda configSort: str(configSort))

    trace.config(3, neededConfigs)
    return neededConfigs


class ConfigStack( object ):
    '''
    Maintains config file information during Surveyor job run
    The stack stores lists of entries from a config file, indexed using the
    full path. On startup we read in any default config files. We're
    then called during tree traversal to load any other config files.
    '''
    def __init__(self, configFileName, configOverrides, defaultConfigOptions=[]):
        trace.config(2, "Creating ConfigStack with {0}".format(configFileName))
        self._modules = CodeSurveyorModules()
        self._reader = configreader.ConfigReader(self.load_csmodule)
        self._measureRootDir = ''

        # Stack of config files, represented as paths and lists of ConfigEntrys
        self._configStack = []

        # Cache of config file information
        # Key is path name, value is list entries that represent the config file
        self._configFileCache = {}

        # List of default config option tags passed by the application
        self._defaultConfigOptions = defaultConfigOptions

        # We either use overrides or try to read config files
        if configOverrides:
            trace.msg(1, "Ignoring config files: {0}".format(configOverrides))
            self._configName = ''
            self._setup_config_overrides(configOverrides)

        else:
            self._configName = configFileName
            # Make sure the config file name does not include a path, as the point is
            # to look for a config file in each folder we visit
            if not os.path.dirname(self._configName) == '':
                raise utils.ConfigError(uistrings.STR_ErrorConfigFileNameHasPath)
            # Load the default config file to use for this job
            # First try in the root of the job folder; then in the surveyor folder
            if not self._push_file(utils.runtime_dir()):
                 if not self._push_file(utils.surveyor_dir()):
                    trace.msg(1, "{0} not present in default locations".format(
                            self._configName))


    def load_csmodule(self, configEntry):
        '''
        Callback for ConfigReader to load modules
        Module loading is delegated to our set of cached modules
        We concatonate and default config options from the application with
        any options defined in the conifig file.
        '''
        trace.config(3, configEntry.__dict__)
        configEntry.module = self._modules.get_csmodule(
                configEntry.moduleName,
                self._defaultConfigOptions + configEntry.options)

        if configEntry.module is None:
            raise utils.ConfigError(uistrings.STR_ErrorFindingModule.format(
                    configEntry.moduleName))


    def set_measure_root(self, measureRootDir):
        '''
        Called before each folder tree is measured to allow path to tbe used
        in error message if no config file is found
        '''
        self._measureRootDir = measureRootDir


    def get_configuration(self, folder):
        '''
        Returns two collections:
         1) A set of all file filters active for folder
         2) A dict by file filter with list of ConfigEntry objects for folder

        The active configuration is the contents of the config file
        closest to the leaf directory passed in as you look back up the
        parent subdirectory tree, ending with the default job config.
        '''
        self._pop_to_active(folder)
        self._push_file(folder)

        path, fileFilters, activeConfigItems = self._active_entry()

        trace.config(4, "Config: {0} -- {1} possible entries".format(path, len(activeConfigItems)))
        return fileFilters, activeConfigItems, path


    def active_path(self):
        '''Returns the fully qualified path of the active config file'''
        return self._active_entry()[0]


    #-------------------------------------------------------------------------

    def _setup_config_overrides(self, configOverrides):
        '''
        If we were pased any overrides, set up config entry objects based on
        the strings instead of from the config file
        '''
        for configName, configStr in configOverrides:
            configEntry = configentry.ConfigEntry(line=configStr)
            self.load_csmodule(configEntry)
            self._push_entries(configName, [configEntry])


    def _active_entry(self):
        activeConfig = None
        try:
            activeConfig = self._configStack[self._active_entry_index()]
        except Exception:
            # If no default config files are available and there is
            # not a config file in the measureRoot we raise an error
            raise utils.ConfigError(uistrings.STR_ErrorNoDefaultConfig.format(
                    self._configName, os.path.abspath(self._measureRootDir),
                    utils.runtime_dir(), utils.surveyor_dir()))
        return activeConfig


    def _push_file(self, dirName):
        '''
        Returns true if a config file was found in dirName and pushed on stack
        '''
        success = False
        configFilePath = os.path.abspath(os.path.join(dirName, self._configName))

        if not configFilePath in self._configFileCache:
            if os.path.isfile(configFilePath):
                self._configFileCache[configFilePath] = self._reader.read_file(configFilePath)

        if configFilePath in self._configFileCache:
            self._push_entries(configFilePath, self._configFileCache[configFilePath])
            trace.config(1, "Config PUSH {0}: {1}".format(
                    len(self._configFileCache[configFilePath]), configFilePath))
            if len(self._configFileCache[configFilePath]) == 0:
                trace.config(1, "EMPTY CONFIG: {0}".format(configFilePath))
            success = True;
        return success


    def _pop_to_active(self, dirToCheck):
        '''
        Removes config entries back up the folder chain, until we get to the
        active one.
        '''
        configIndex = self._active_entry_index()

        # DO NOT EVER pop the first position, as it should be a default file
        while configIndex > 0:
            # Get active config path and remove file name
            configDir, _configItems, _configPath = self._configStack[configIndex]
            configDir = os.path.dirname(configDir)
            currentDir = os.path.abspath(dirToCheck)

            # Is the config file equal to or "above" current position in path?
            # Special case the current folder '.' below because commonprefix
            # returns it, while dirname returns blank for empty path
            currentDirUnderConfigDir = False
            sharedPath = os.path.commonprefix([currentDir, configDir])
            if not sharedPath == '':
                currentDir = os.path.relpath(currentDir, sharedPath)
                configDir = os.path.relpath(configDir, sharedPath)
                while True:
                    if configDir == currentDir:
                        currentDirUnderConfigDir = True
                        break;
                    if '.' == currentDir:
                        break
                    currentDir = os.path.dirname(currentDir)
                    if not currentDir:
                        currentDir = '.'

            # If the current config file does not cover the currentDir, pop it
            if currentDirUnderConfigDir:
                break
            else:
                trace.config(1, "Config POP: {0}".format(self.active_path()))
                del self._configStack[configIndex]
                configIndex -= 1


    def _push_entries(self, path, configEntryList):

        # Create list of items based on file filters
        fileFilters = set([])
        configItems = {}
        for configEntry in configEntryList:
            for fileFilter in configEntry.fileFilters:
                fileFilters.add(fileFilter)
                configObjs = configItems.get(fileFilter, [])
                configObjs.append(configEntry)
                configItems[fileFilter] = configObjs

        self._configStack.append((path, fileFilters, configItems))


    def _active_entry_index(self):
        # The item at the top of the stack is the active one
        return (len(self._configStack) - 1)






