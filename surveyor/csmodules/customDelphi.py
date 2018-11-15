#=============================================================================
'''
    Delphi module
'''
#=============================================================================
# Copyright 2004-2010, Matt Peloquin and Construx. This file is part of Code
# Surveyor, covered under GNU GPL v3 and is distributed WITHOUT ANY WARRANTY.
#=============================================================================
import re
from Code import Code

class customDelphi( Code ):
    '''
    Delphi example of overriding the default NBNC Code class to work
    with comment syntax that is in conflict with the Surveyor defaults
    '''
    def __init__(self, options):
        super(customDelphi, self).__init__(options)

    @classmethod
    def _cs_config_options(cls):
        return {}

    def _cs_init_config_options(self):
        super(customDelphi, self)._cs_init_config_options()

        # Comment structure is different in delphi/pascal
        self.reBlankLine = re.compile(
            r"^ \s* ( \b begin \b | \b end; )? \s* $", self._reFlags)
        self.reSingleLineComments = re.compile(
                r"^ \s* //", self._reFlags)
        self.reMultiLineCommentsOpen = re.compile(
                r"( \(\* | {(?![/$]) )" + self.REMAINING_LINE_APPEND, self._reFlags)
        self.reMultiLineCommentsClose = re.compile(
                r"( \*\) | } )", self._reFlags)

        # We have to remove braces and parans from dead code detection
        self.reDeadCode = re.compile(
                r' [;\[\]]+\s*$ | [A-Za-z]\.[A-Za-z]  | [=&\+\[\]\|]+ ',
                self._reFlags)

