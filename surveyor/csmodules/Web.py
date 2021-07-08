#=============================================================================
'''
    Web Module -- Used to separate code from content/layout in web
    or similar file types.
'''
#=============================================================================
# Copyright 2004-2011, Matt Peloquin and Construx. This file is part of Code
# Surveyor, covered under GNU GPL v3 and is distributed WITHOUT ANY WARRANTY.
#=============================================================================
import re
from Code import Code

class Web( Code ):
    '''
    Adds a new block type called "content"
    Extends Code module by using the block detection mechanism to separate
    script/code blocks from content blocks
    Records the content metrics

    See NBNC.py and Machine.py for description of block detection.
    '''

    ConfigOptions_Web = {
        'SCRIPT_ADD_DETECTOR': ('''self.blockDetectors[self._measureBlock].append(eval(optValue))''',
            'Adds a script detection regex'),
        'SCRIPT_DETECTORS': ('''self.blockDetectors[self._measureBlock] = eval(optValue)''',
            'Completely replaces script detection regexs'),
        }

    def __init__(self, options):
        super(Web, self).__init__(options)

    @classmethod
    def _cs_config_options(cls):
        return cls.ConfigOptions_Web

    def _cs_init_config_options(self):
        super(Web, self)._cs_init_config_options()
        self._configOptionDict.update(self.ConfigOptions_Web)

        # We want to capture lines before the first routine as a dummy routine
        self.routineInclFileLines = True

        # We override the default measurement block to be whatever is inside
        # our block detection - anything outside block detection (position 0)
        # is now "content"
        self.CONTENT = 0
        self.HUMAN_CODE = 2
        self._measureBlock = self.HUMAN_CODE

        # Add block detections for web script
        # The set of items below should work well for most common web file
        # types like HTML, PHP, ASP, JSP, etc.
        self.blockDetectors[self.HUMAN_CODE] = [
            # Common script tags
            [   re.compile( r"[<{]%", self._reFlags),
                re.compile( r"%[>}]", self._reFlags),
                ],
            [   re.compile( r"<script", self._reFlags),
                re.compile( r"</script>", self._reFlags),
                ],

            # PHP
            [   re.compile( r"<\?php", self._reFlags),
                re.compile( r"\?>", self._reFlags),
                ],

            # Flex
            [   re.compile( r"<[fm]x:script", self._reFlags),
                re.compile( r"</[fm]x:script>", self._reFlags),
                ],

            # Sometimes code will be consistenly placed in CDATA tags
            #[   re.compile( r"<\!\[CDATA\[", self._reFlags),
            #    re.compile( r"\]\]>", self._reFlags),
            #    ],
        ]


    def _trace_block_level(self):
        # We want to trace out all lines (not just code/content) at Debug level 3
        return 3



