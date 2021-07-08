#=============================================================================
'''
    Ecapsulates Management of Surveyor measurement modules
'''
#=============================================================================
# Copyright 2004-2010, Matt Peloquin and Construx. This file is part of Code
# Surveyor, covered under GNU GPL v3 and is distributed WITHOUT ANY WARRANTY.
#=============================================================================
from framework import uistrings
from framework import utils
from framework import trace


class CodeSurveyorModules( object ):
    '''
    Manages csmodules for the ConfigStack
    Note the "csmodules" are actually instances of the class inside each python
    module. The modules are loaded lazily and the classes are cached.
    Since csmodule classes may have different initialization states set by
    options, we include the option strings as part of the cache name.
    '''
    PACKAGE_PREFIX = 'csmodules.'
    RequiredMethods = [ 'open_file', 'process_file',
            'match_measure', 'can_do_verb', 'can_do_measure',
            'add_param', 'verb_end_marker']

    def __init__(self):
        self.moduleList = {}


    def get_csmodule(self, csmoduleName, options=[]):
        '''
        Return the csmodule class with the given name, if it exists
        '''
        csmodule = None
        trace.config(2, "Loading csmodule: {0}".format(csmoduleName))
        mod_hash = self._csmod_hash(csmoduleName, options)
        if mod_hash in self.moduleList:
            csmodule = self.moduleList[mod_hash]
        csmodule = self._load_csmodule(csmoduleName, options)
        if csmodule is not None:
            self.moduleList[self._csmod_hash(csmoduleName, options)] = csmodule
        return csmodule


    def _csmod_hash(self, moduleName, options):
        if options is None:
            return moduleName
        else:
            optHash = ""
            for name, value in options:
                if value is None:
                    optHash += name
                else:
                    optHash += name + str(value)
            return moduleName + optHash


    def _load_csmodule(self, modName, options):
        '''
        Import a module given its name, and return the object.
        If there are any problems finding or loading the module we return None.
        If the module has python errors in it we treat as catastrophic
        failure and allow caller to handle.
        '''
        csmoduleClassInstance = None
        try:
            # Load the module called modName, and then get class inside the
            # module with the same name
            moduleFile = __import__(self.PACKAGE_PREFIX + modName)
            module = getattr(moduleFile, modName)
            moduleClass = getattr(module, modName)

            # Instantiate the module
            csmoduleClassInstance = moduleClass(options)

            # Make sure required methods are in the class; fatal error if not
            for method in self.RequiredMethods:
                getattr(csmoduleClassInstance, method)

        except (ImportError, AttributeError):
            trace.traceback()
            raise utils.SurveyorException(uistrings.STR_ErrorLoadingModule.format(modName))
        return csmoduleClassInstance

