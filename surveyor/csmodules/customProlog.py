#=============================================================================
'''
    Prolog Module
'''
#=============================================================================
# Copyright 2004-2010, Matt Peloquin and Construx. This file is part of Code
# Surveyor, covered under GNU GPL v3 and is distributed WITHOUT ANY WARRANTY.
#=============================================================================
import re
from Code import Code

class customProlog( Code ):
    '''
    Prolog example of overriding the default NBNC Code class to work
    with comment syntax that is in conflict with the Surveyor defaults
    '''
    def __init__(self, options):
        super(customProlog, self).__init__(options)

    @classmethod
    def _cs_config_options(cls):
        return {}

    def _cs_init_config_options(self):
        super(customProlog, self)._cs_init_config_options()

        self.singleLineComments = [ re.compile(r"^\s*%") ]
        self.multiLineCommentsOpen = [
            re.compile( r"/\*" ),
            re.compile( r"\"" ),
            ]
        self.multiLineCommentsClose = [
            re.compile( r"\*/" ),
            re.compile( r"\"" ),
            ]
        self.multiLineCommentsCloseSameLine = [
            re.compile( r"\*/" ),
            re.compile( r"\"" ),
            ]

