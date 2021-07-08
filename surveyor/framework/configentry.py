#=============================================================================
'''
    ConfigEntry
    Encapsulation of config file line
'''
#=============================================================================
# Copyright 2004-2010, Matt Peloquin and Construx. This file is part of Code
# Surveyor, covered under GNU GPL v3 and is distributed WITHOUT ANY WARRANTY.
#=============================================================================

from framework import trace

CONFIG_ITEM_SEPARATOR = ';'
CONFIG_DELIM_CHAR = ':'
CONFIG_DELIM_OPTION = 'OPT' + CONFIG_DELIM_CHAR
CONFIG_DELIM_OUTFILE = 'OUT' + CONFIG_DELIM_CHAR
CONFIG_TAG_PREFIX = 'tag'

#-----------------------------------------------------------------------------
# Encoding output filenames in measurement tags (used by output writer)

def is_tag_name(strValue):
    return strValue.startswith(CONFIG_TAG_PREFIX)

def filename_from_tag(tag):
    outFileName = None
    if tag.startswith(CONFIG_DELIM_OUTFILE):
        outFileName = tag[len(CONFIG_DELIM_OUTFILE):]
    return outFileName


class ConfigEntry( object ):
    '''
    A single configuration entry, defined by line/section in a config file:

        verb  moduleName  measures  files  tag1  tag2  tagN
           extraParam1
           extraParam2
           ...
        verb_end

    Tags may contain options to be passed to the csmodule, which have the
    form OPT:optName:optValue, which the module will decode
    '''
    # Position of config items on a verb line
    POS_VERB         = 0
    POS_MODULE       = 1
    POS_MEASURE_MASK = 2
    POS_FILE_MASK    = 3
    POS_TAG_START    = 4

    def __init__(self, line, extraLineContent='', configFilePath=''):
        # These items must be set later, when module is loaded and called
        self.module = None
        self.paramsRaw = []
        self.paramsProcessed = []
        self.measureFilter = ''
        self.measureFilters = []
        self.fileFilters = []

        # Used for caching optimization
        self.configFilePath = configFilePath

        # Process line as list
        configValues = line.split() + extraLineContent.split()

        # Load the information on this line up to the tags
        self.verb = configValues[self.POS_VERB].lower()
        self.moduleName = configValues[self.POS_MODULE]
        self.new_measure_filter(configValues[self.POS_MEASURE_MASK])
        self.new_file_filter(configValues[self.POS_FILE_MASK])

        self.tags = []
        self.options = []
        self.add_tags_and_options(configValues[self.POS_TAG_START:])

    def __str__(self):
        return self.fileFilter + " " + self.config_str_no_fileext()

    def add_tags_and_options(self, tagItems):
        # Parse the "tag" values into tags and options
        for item in tagItems:
            if item.startswith(CONFIG_DELIM_OPTION):
                opt = item[len(CONFIG_DELIM_OPTION):].split(CONFIG_DELIM_CHAR)
                # There are two types of options, with and without values
                if len(opt) > 1:
                    # Everything after OPT tag is value string, we joing back together
                    # in case the string had delim chars in it
                    optionStr = CONFIG_DELIM_CHAR.join(opt[1:])
                    self.options.append((str(opt[0]), optionStr))
                    trace.config(2, "Option Load: {0} -> {1}".format(str(opt[0]), optionStr))
                elif opt:
                    self.options.append((str(opt[0]), None))
                    trace.config(2, "Option Selected: {0}".format(str(opt[0])))
            else:
                self.tags.append(item)

    def is_empty(self):
        return self.verb != ''

    def is_complete(self):
        return self.module is not None

    def config_str_no_fileext(self):
        configStr = [self.verb, self.moduleName, self.measureFilter,
                    " ".join([str(t) for t in self.tags]),
                    " ".join([str(optN) + ":" + str(optV) for optN, optV in self.options])]
        return " ".join(configStr)

    def new_measure_filter(self, filterStr):
        self.measureFilter = filterStr
        self.measureFilters = self.measureFilter.split(CONFIG_ITEM_SEPARATOR)

    def new_file_filter(self, filterStr):
        self.fileFilter = filterStr
        self.fileFilters = [filterItem for filterItem in
                self.fileFilter.split(CONFIG_ITEM_SEPARATOR) if filterItem]
