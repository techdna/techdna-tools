#!/usr/bin/env python 2.7
#=============================================================================
'''
    Code Surveyor command line application
    See README for detals
'''
#=============================================================================
# Copyright 2004-2010, Matt Peloquin and Construx. This file is part of Code
# Surveyor, covered under GNU GPL v3 and is distributed WITHOUT ANY WARRANTY.
#=============================================================================
import sys
import platform
import traceback
import multiprocessing

from framework import cmdlineapp
from thirdparty import terminalsize

# For Pyinstaller, it is easiest to have fake import of all csmodules
if False:
    from csmodules import *

#-------------------------------------------------------------------------
#  Run surveyor and return status to the shell

if __name__ == '__main__':
    
    # Setup OS sensitive items
    printWidth = None
    try:        
        currentPlatform = platform.system()

        # Try to get console width
        widthHeight = None
        if currentPlatform in ('Windows'):
            widthHeight = terminalsize._get_terminal_size_windows()
        elif currentPlatform in ('Linux') or currentPlatform.startswith('CYGWIN'):
            widthHeight = terminalsize._get_terminal_size_linux()
        if widthHeight:
            printWidth = widthHeight[0] - 1  # Take one off to avoid line overrun

        # This is needed to support multiprocessing for Windows exe
        if currentPlatform in ('Windows'):
            multiprocessing.freeze_support()           

    except Exception:
        # If something falls apart, we'll try to carry on with defaults        
        pass 

    # Run the measurement job, always returning result to the shell
    SUCCESS = 0
    FAILURE = 1
    result = FAILURE
    try:
        if cmdlineapp.run_job(sys.argv, sys.stdout, printWidth):
            result = SUCCESS
    except:
        print "\nA system error occurred while running Surveyor:\n"
        traceback.print_exc()
    finally:
        # We should not have child processes alive at this point, but in
        # case there was a problem, kill them to prevent hangs
        for child in multiprocessing.active_children():
            child.terminate()
            print "BAD EXIT -- {0} active".format(child.name)
        sys.exit(result)




