#=============================================================================
'''
    csmodules -- Code Surveyor Modules

    The csmodule package is where Surveyor looks for measurement modules
    that are loaded by modules.py and referenced in config files. These
    modules provide different behaviors; implementation inheritance allows
    for minimal modification of code in each specialization

                 framework\basemodule.py____
                 /                    |     \
           NBNC.py    searchMixin.py  |     Document.py
               |      /           \   |
               |     /          Search.py
             Code.py_____________________________
              |       |             |            |
          Web.py  DupeLines.py  customXYZ.py    ...

    Design
    information for individual csmodules is the files. NBNC.py is a good
    place to start. Some general design notes for all csmodules:

      - The csmodules are intended to be easily accessible script
        plug-ins that may be frequently modified or extended

      - The csmodules are NOT intended as generally callable Python
        modules; they are design to be used in the Surveyor framework

      - All current csmodules inherit basic file handling implementation
        from framework.basemodule. This isn't strictly necessary, as long
        as a csmodule replicates the appropriate interface.

      - Unlike the Surveyor framework, error and measure output strings are
        hard-coded in the modules vs. in string resources.

      - The csmodules intentionally do not follow Python's style guidelines
        for lowercase naming to help differentiate them from generally
        callable Python modules
'''
#=============================================================================
# Copyright 2009-2011 Matt Peloquin This file is part of Code Surveyor,
# covered under GNU GPL v3 and is distributed WITHOUT ANY WARRANTY.
#=============================================================================
__version__ = '6'

__all__ = [
    'NBNC',
    'Code',
    'Web',
    'Search',
    'Document',
    'DupeLines',
    'Depends',
    'customCobol',
    'customDelphi',
    'customPowerBuilder',
    'customProlog',
    ]


