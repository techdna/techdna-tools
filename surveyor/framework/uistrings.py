#-*- coding: latin-1 -*-
#=============================================================================
'''
    Surveyor Application UI Strings

    All non-debug strings used by the framework are placed here, to provide
    for easy update, potential translation, and compactness in code
'''
#=============================================================================
# Copyright 2004-2012, Matt Peloquin. This file is part of Code Surveyor,
# covered under GNU GPL v3 and is distributed WITHOUT ANY WARRANTY.
#=============================================================================

#-------------------------------------------------------------------------
#   Visible File Name and system values

CONFIG_FILE_DEFAULT_NAME = "surveyor.code"
DEFAULT_OUT_FILE = "surveyor"               # Writer will add type extension
NO_EXTENSION_NAME = ".(NoExt)"              # Appears where we need fileExt
PROFILE_FILE = "SurveyorProfile"            # For profiler output files


#-------------------------------------------------------------------------
#   Framework UI Strings

STR_OpenedOutput = " Output file: {0}\n"
STR_ErrorProcessingOutput = " Error processing output for: {0}\n"
STR_ErrorOpeningOutputAccess = """
    Cannot open output file...

       {0}

    ...due to exclusive lock or lack of permission.

    If the the file is open in an application that may have it locked
    (such as Excel), try closing the file.

"""
STR_ErrorOpeningOutput = """
    Cannot open output file: {0}
      {1}
"""
STR_ErrorMeasuringFile = """
    Error measururing: {0}
       {1}
"""
STR_ErrorOpeningMeasureFile_Except = """
    Error opening file for measurement: {0}
       {1}
"""
STR_ErrorOpeningMeasureFile_Access = """
    Exclusive lock or lack permissions: {0}
"""
STR_ErrorFindingModule = """
    Could not find Surveyor module: {0}
"""
STR_ErrorLoadingModule = """
    Python error while loading Surveyor module: {0}
"""
STR_ErrorNoDefaultConfig = """
    To execute this job a config file named "{0}" is needed in one of:

       1) Root of the tree being measured:  {1}
       2) Current working folder:  {2}
       3) Surveyor folder:  {3}

    If no config files are obtainable, use the "-a" option.
"""
STR_ErrorConfigFile = """
    Error processing configuration file:
      {0}

      {1}
"""
STR_ErrorConfigEntry = """
    Error processing config entry...
      {0}
      {1}
"""
STR_ErrorConfigParam = """
    Error processing config entry parameter...
      Config Entry: {0}
      Parameter:    {1}
      {2}
"""
STR_ErrorConfigConstantsTooDeep = """
    Constant recursuion depth of {0} exceeded:
        {1}
"""
STR_ErrorConfigValidate = """
    Validation problem with configuration file

        {0}
"""
STR_ErrorConfigInvalidMeasure = """
    Config file requested measure that module cannot perform:

        {0}, {1}
"""
STR_ErrorConfigDupeMeasures = """
    Duplicate measures:

        {0} {1} {3} {4} {6} {8}
        {0} {2} {3} {5} {7} {9}
"""


#-------------------------------------------------------------------------
#   Command Line App UI Strings

STR_Intro = """
Code Surveyor 6
Copyright 2012, GPL (-? for help)
"""
STR_Divider = "\n"
STR_FolderMeasured = " Measuring: {0}\n"
STR_DeltaFolder = " Delta comparison folder: {0}\n"
STR_FileFilter = " File filter: {0}\n"
STR_DirFilter = " Skiping folders: {0}\n"
STR_IncludeFolders = " Including folders: {0}\n"
STR_LocationOfMeasurements = " Output location: {0}\n"
STR_CmdArgs = " Cmdline: {0}\n"

STR_UpdateDisplay = "({0:.0f}) Files found : in queue : measured -- {1:n} : {2:n} : {3:n}"
STR_UpdatePath = " {0:75}\n"
STR_UpdatePathDetailed = " ({0:0.3f}) {1:60}\n"

STR_CompressedFile = " Compressed file: {0:58}\n\n"
STR_LongProcessingFile = " Long processing ({0:0.1f}): {1:50}\n\n"

STR_UserInterrupt = """

 ===  Measurement aborted by user  ===

"""
STR_Error = """

 ===  Error occurred, measurement aborted  ===

"""
STR_ErrorList = """

 ===  MEASUREMENTS ABORTED FOR {0} FILES  (first {1} displayed below)  ===
    {2}


"""
STR_SummaryTotalFiles = """ Total files:   {1:n}
 Total folders: {0:n}
 """
STR_SummaryFiltered = """
 Files filtered: {0:n}
      processed: {1:n}
        skipped: {2:n}
 """
STR_SummaryMeasured = """
 Folders measured: {0:n}
 Files measured:   {1:n}
 Measure rows:     {2:n}
"""
STR_SummaryLargeFile = """
 Files larger than {0:n} bytes will have empty measures
 """
STR_SummaryBinaryFile = """
 Probable binary files will have empty measures
 """
STR_SummaryDeltaFile = """
 Unchanged files (relative to delta) will have empty measures
 """
STR_SummaryDetailedTitle = """
 Summary of key measurements:
"""
STR_SummaryDetailedFileTitle = """
 Summary metrics sorted for top {0} file types:
"""
STR_TotalDupes = """
 There were {0} files with duplicates and {1} duplicates in total
 See output results for details, duplicate files are not included in measures
"""
STR_AggregateKeyError = """
 There was a problem aggregating the measure name: {0}
 Check that the measure name exists in the measure results
"""
STR_AggregateThresholdKeyError = """
 The aggregate threshold key is not in the aggregates: {0}
"""
STR_SummaryDetailedMeasureValue = "   {0}{1}  {2:n}\n"
STR_SummaryDetailedMeasure =      "   {0}{1}\n"
STR_SummaryRunTime = "\nRun time: {0:.1f} seconds\n"


#-------------------------------------------------------------------------
#   Help Text and Command Line Parsing

STR_HelpText_Intro = (
"""
 Configurable and extensible code measuring and searching. Non-Blank,
 Non-Comment (NBNC) lines of code and other measures for code and text:
 (see "surveyor.code" for broad list)

    C/C++ Java C# SQL Lua JS Py Ruby Perl VB PHP JSP ASP HTML TCL etc.

 Per-file measures are placed into a csv file for analysis. Customized
 config files can (should) be placed in your folders to override
 "surveyor.code" ("-? config" for more info). Also see README.
 Code Surveyor is free to use and extend, see LICENSE.
 """)

CMDARG_LEADS = '-'
CMDLINE_SEPARATOR = ';'
CMDARG_HELP = 'h?'

# Primary commands
CMDARG_SCAN_ALL = 'a'
CMDARG_BREAK_ERROR = 'b'
CMDARG_CONFIG_CUSTOM = 'c'
CMDARG_DELTA = 'd'
CMDARG_DUPE_PROCESSING = 'e'
CMDARG_OUTPUT_FILTER = 'f'
CMDARG_AGGREGATES = 'g'
CMDARG_INCLUDE_ONLY = 'i'
CMDARG_METADATA = 'm'
CMDARG_RECURSION = 'n'
CMDARG_OUTPUT_FILE = 'o'
CMDARG_PROGRESS = 'p'
CMDARG_QUIET = 'q'
CMDARG_OUTPUT_TYPE = 'r'
CMDARG_SKIP = 's'
CMDARG_SUMMARY_ONLY = 't'
CMDARG_DETAILED = 'v'
CMDARG_NUM_WORKERS = 'w'
CMDARG_PROFILE = 'y'
CMDARG_DEBUG = 'z'

STR_HelpText_Usage = """
 Usage:

    surveyor{0} [options] [pathToMeasure]{1}[fileFilters]...
    """
STR_HelpText_Options = """
    [pathToMeasure]   Measure path(s) other than the current one
    [fileFilters]     File type filters (documented in surveyor.examples)
    -delta <path>     Measure diffs and additions relative to <path> (+)
    -config <name>    Look for config files called <name> (+)

    -a[mode]          Scan all files, ignoring config file settings (+)
    -s<mode> <filt>   Skip files due to binary, size, name, locaiton, etc. (+)
    -inclPath <filt>  Include only files in paths that match filter (+)
    -nonRecursive     Only scan <pathToMeasure>, do not scan sub-folders
    -breakOnError     Stop scanning if file error is encountered

    -exDupe [thresh]  Exclude duplicate files from measure totals (+)
    -m <metadata>     Modify metadata output (e.g., folder reporting depth) (+)
    -filter <name>    Filter measurement output by <name> (+)
    -g <key> <value>  Track aggregates of measures (+)
    -results <type>   Change results output from csv to XML, etc. (+)
    -out <filePath>   Place measurement results in <filePath> (+)

    -totalsOnly       No measure file output, just display summary on console
    -progress [len]   Per-file progress on console, max width of [len]
    -verbose [len]    Additional summary information on console, up to [len]
    -z[level][modes]  Debug tracing to console (+)
    -workers <num>    Use <num> worker processes (default is NumCores-1)
    -quiet            Don't update console status, useful for piping output

    -? [name]         Additional help on [name] for items above ending in (+)

 Examples:
    surveyor{0}               (measure files as per surveyor.code config files)
    surveyor{0} -ad -t              (scan all likely code files, no csv output)
    surveyor{0} -c myConfigFile         (run using "myConfigFile" config files)
    surveyor{0} -e 100 -o dupes.csv         (same files within 100 bytes duped)
    surveyor{0} -i *test* A{1}*.cs B{1}*.c           (test folders in path A and B)
    """

CMDARG_CONFIG_CUSTOM = 'c'
CMDARG_CONFIG_INFO = 'i'
STR_HelpText_Config = """
 Custom config file(s):

    By default Surveyor looks for 'surveyor.code' files in each folder.
    When found they are read as config files for that folder and all folders
    below (unless overridden farther down).
    If no config file is present in the root folder of a measurement job,
    Surveyor looks in the folder it is being run from.

    -c <name>   Files that EXACTLY match <name> will be used as config files.
                NOTE - this is NOT a file at a particular location, but
                rather a name that is scanned for in the folder tree.

    For documentation see 'surveyor.code' and 'surveyor.examples' in:

        {0}

 Config information:

    -ci [name]  Instead of measuring, this option displays all folders and
                file types that would be measured, along with the options
                from the config file that apply to each location.

 Command-line config:

    -cc <config>    Allows a one line config entry in <config>, overriding
                    any config files, e.g., -cc "measure DupeLines * *"

 Config file options:

    csmodules support options that can be used in config files to modify
    behavior by file type. A complete list of the options for each csmodule
    is below. Look inside each module for more detail:
"""
STR_HelpText_Config_OptionModName = """
  {0}
"""
STR_HelpText_Config_OptionItemHelp = "   {0:<20} {1}\n"


CMDARG_DELTA_DELETE = 'd'
STR_HelpText_Delta = """
 Delta Measure:

    Measures what has changed between two versions of the same folder tree.
    Normally you would make <pathToMeasure> your current version of a folder
    tree and <deltaPath> the older version.

    Unchanged files and lines (per Python difflib) will have 0 values.

    Works on path names to individual files, so any folder changes will
    be seen as new files in <pathToMeasure>.
    Files in <deltaPath> that are not in <pathToMeasure> are not considered;
    in other words deleted files in <pathToMeasure> are ignored.

    -d <deltaPath>  Measures added or modified lines in new files and files that
                    exist in both <pathToMeasure> and <deltaPath>. 
                    Deleted lines are not measured.

    -dd <deltaPath> Incldues lines that have been deleted. Note that modified
                    lines will be double counted.
                    Lines from DELETED FILES ARE NOT MEASURED.

    Delta measurement only works well for the measure and search
    verbs; behavior with the routines verb is undedefined.

    If you need different delta semantics, you can also create a diff
    output with your tool of choice and run surveyor on that.
    """

CMDARG_SCAN_ALL_METADATA = 'm'
CMDARG_SCAN_ALL_CODE = 'nd'
CMDARG_SCAN_ALL_DEEP_CODE = 'd'
STR_HelpText_Scan_All = """
 Scan All, ignoring config files:

    Normal Surveyor measurement is dictated by config files -- only file
    extensions that have been explicity configured are measured.
    Scanning is useful to ensure that all file types you want to consider
    are included when tuning config files.

    -a      Attempt to measure all files in folder tree. Files that start with
            binary characters will not have per-line measurements produced.
            Can be very slow if there are many huge text files (e.g., XML).

    -am     Fastest way to get a list of all files in a folder tree. This does
            does not open files so only provides metadata (e.g., byte size).

    -an     Quick scan using the NBNC module to measure likely code files.
            To determine likely code files, a number of filters are used:
                + Folders and files starting with "." and "cvs" are skipped
                + Common non-code file extensions are skipped (-sn)
                + Files detected as binary are skipped (-sb)
                + Large files are skipped (the -sl option)
            Does not provide generated-code detection like -ad, but can be
            significantly faster than -ad for large code bases.

    -ad     Deep code scan of all likely code files. This applies the same file
            criteria as "-an", but uses the Code module to do a full analysis
            of the file, including detecting generated machine code.

    Scanning also turns on the ignore errors option, to ensure the scan will
    continue through all files.

    MAY PRODUCE GARBAGE MEASURES FOR NON-CODE FILES
"""

CMDARG_SKIP_DIR = 'd'
CMDARG_SKIP_FILE = 'f'
CMDARG_SKIP_SIZE = 's'
CMDARG_SKIP_BINARY = 'b'
CMDARG_SKIP_NONCODE = 'n'
STR_HelpText_Skip = """
 Skip folders and/or files that match the given criteria:

    -sn             Do not measure files with common non-code extensions
    -sd <folders>   Skip folders that match <folders>
    -sf <files>     Skip files that match filters in <files>
    -sbinary        Attempt to identify and skip binary files
    -ssize [bytes]  Do not measure files larger than [bytes]

    Run with the -z2f debug option to see which files are being skipped.
    See framework\\filetype.py for details on the file detection logic.

"""

STR_HelpText_InlcudeOnly = """
 Only include files in paths that match the filter

    For each file matches against the entire relative path using fnmatch.
    This allows excluding/including specific folders and branches.
    Usually filters should start (and often end) with '*' to ensure the
    desired match is captured out of the full path.

 Examples:

    -i *test*;*unit*
    -i *\\test\\fixtures

"""

STR_HelpText_Dupe_Processing = """
 Exclude duplicate file measures:

    Zeros out measure and analysis information for duplicate files.

    NOTE ABOUT DUPLICATE PROCESSING
    Since duplicates are checked and processed by Surveyor as results are received, 
    and since Surveyor jobs are likely using multiple cores to process groups of 
    files, it is possible that different runs against the same folder tree will
    produce slightly different dupe results -- not in the totals, but in which
    dupe file instance gets credit for being "first". This can change the roll-ups
    of folder trees the duplicate each other's files. 

    -excludeDupes [byteThreshold]

    Will keep track of file names and sizes (in bytes). If files with the same
    name are encountered whose size is within [byteThreshold] of a previously
    measured file, metadata for the file will be written in output, but no
    measures will be recorded.

    This allows both detection of duplicates or near-dupes, as well as
    aggregate measures that do not include the duplicate files.
    [byteThreshold] defaults to 0, or an exact match in size

    -excludeDupes crc

    Uses the Code csmodule's per-file CRC calculation to detect duplicates. This
    works similarly to above, except file name is ignored and only the nbnc.crc
    measure is compared.
    This CRC is NOT a simple file CRC -- nbnc.crc is calculated based on considering
    only the non-whitespace content of NBNC lines of human-written code. This updates
    in comments or minor whitespace changes will not change the CRC and thus be
    considered duplicates.
    Note that the Code csmodule must be used for this to work.
"""

CMDARG_OUTPUT_TYPE_CSV = 'csv'
CMDARG_OUTPUT_TYPE_TAB = 'tab'
CMDARG_OUTPUT_TYPE_XML = 'xml'
CMDARG_OUTPUT_TYPE_PARA = 'paragraph'
STR_HelpText_Output = """
 Place measurement results into specific output file:

    -o <filePath>   Send default measurement results to file, will override and
                    config file output settings

    -o stdout       Send all measurement results to console

    -o <folder>     Open all output files in the given folder, both the default
                    output file as well as any output files designated in the
                    config files
"""

STR_HelpText_Results = """
 Change the output stream from the standard comma-delimited to:

    -r csv          Comma-delimited output columns (default)
    -r tab          Tab-delimited output columns
    -r paragraph    Uses paragraph symbol to separarte*
    -r xml          XML output for values

    *on windows hold down "Alt" and type "0182" for \\xB6 paragraph symbol "¶"
"""

CMDARG_METADATA_RESET = 'r'
CMDARG_METADATA_MAXDEPTH = 'p'
CMDARG_METADATA_DATE = 'd'
CMDARG_METADATA_ABSPATH = 'a'
CMDARG_METADATA_SIZE = 's'
CMDARG_METADATA_FOLDER = 'f'
CMDARG_METADATA_DEBUG = 'y'
CMDARG_METADATA_ALL = 'z'
STR_HelpText_Metadata = ("""
 File Metadata
 
 Various metadata related to each file can be recorded by Surveyor. By default
 Surveyor captures file name and path information (fileType, dir1, dir2, etc.)

 The metadata placed into output can be adjusted through config file options
 (see the config help) and the command line options below: 

    -m path <depth> Depth of folder structure reported in output 

    -m date <frmt>  File modified date in output, using strftime <frmt>.
                    Defaults to year last modified.
                    May be specified multiple times to put date values into
                    separate output columns. For instance:
                      -m d %Y -m d %m  separates year and month

    -m size     File byte size in output
    -m absPath  Include fully qualified path and file name into one column
    -m folder   Ranking of file to folder ratio
    -m yDebug   csmodule, config line, timing info
    -m zAll     Incude all the metadata options with default values

    -m reset    Removes all metadata; new options can be added after this
                argument to build up customized metadata. 
    """)


CMDARG_OUTPUT_FILTER_METADATA = 'metadata'
STR_HelpText_Filter = """
 Override the output filter:

    -f <filters>    Overrides config file settings for the filters provided in
                    the output file.

    -f metadata     When 'metadata' is the filter, all measures that require
                    opening the file will be skipped, but metadata output will
                    still be collected on path, date, etc. Allos for very
                    fast scanning of all files in a tree.
"""

STR_HelpText_Aggregates = """
 Aggregate mapping:

    -g <keyValue> <keyList> [thresholdKey] [thresholdValue]
    
    
    
    -g search.line "['search.line','search.match']"

"""


CMDARG_DEBUG_FILE = 'f'
CMDARG_DEBUG_SEARCH = 's'
CMDARG_DEBUG_CODE = 'c'
CMDARG_DEBUG_NOT_CODE = 'n'
CMDARG_DEBUG_CONFIG = 'q'
CMDARG_DEBUG_CONCURRENCY = 'm'
CMDARG_DEBUG_TRACE = 't'
CMDARG_DEBUG_TEMP = 'z'
STR_HelpText_Debug = """
 Debug Tracing:

    Used to support regular expression tuning, new module development,
    and debugging Surveyor issues.

    -z<level>[mode][mode]... [outFile] [maxLineLen]

    <level> controls the detail of debug tracing:
        1 - Low:     Key information and Python traceback on major errors
        2 - Med:     Important events, traceback at every exception level
        3 - High:    Per-file feedback, significant events in file lines
        4 - Extreme: Per-line feedback, use for single file debugging

    [mode] provides detail in different areas; multiple modes may be used:
        f - Messages related to Surveyor file processing
        s - Search info on config file regex matches
        c - Lines of code information (levels 3+ shows lines)
        n - Opposite of c, info on lines that are not code (level 3+)
        q - Processing of configuration files
        m - Multiprocessing and concurrency tracing
        t - Turns on python call tracing

    NORMALLY YOU WILL WANT TO USE FILE TRACING WITH "-w 1"
    This will ensure 1 worker process, so output won't be interleaved

    [outFile]   Defines an optional file or stream to send debug output to.
                Defaults to stdout

    [maxLineLen]  Defines how wide the maximum debug report string will be.
                  Defaults to 80.

    Debug Examples:
        surveyor -z
        surveyor -z1sfq
        surveyor -z4c debugOut.txt 999 -w 1


    Profiling

    -y [calls] [calledBy] [called] [threadName] [nameFilter]
    Runs the surveyor job with the profiler. Options specify how many items
    are included for each category, whether to isolate 'Main', 'Out', or 'JobX'
    threads (default is 'all'), and whether to filter output is used.

"""

detailedHelpMap = {
    CMDARG_DELTA: STR_HelpText_Delta,
    CMDARG_CONFIG_CUSTOM: STR_HelpText_Config,
    CMDARG_SCAN_ALL: STR_HelpText_Scan_All,
    CMDARG_SKIP: STR_HelpText_Skip,
    CMDARG_INCLUDE_ONLY: STR_HelpText_InlcudeOnly,
    CMDARG_OUTPUT_FILE: STR_HelpText_Output,
    CMDARG_OUTPUT_TYPE: STR_HelpText_Results,
    CMDARG_METADATA: STR_HelpText_Metadata,
    CMDARG_AGGREGATES: STR_HelpText_Aggregates,
    CMDARG_OUTPUT_FILTER: STR_HelpText_Filter,
    CMDARG_DEBUG: STR_HelpText_Debug,
    CMDARG_DUPE_PROCESSING: STR_HelpText_Dupe_Processing
    }

STR_ErrorInvalidParameter = """
 Invalid parameter: {0}
"""
STR_ErrorParsingCommandLine = """
 Fatal error parsing command line, use -? for help
"""
STR_ErrorCmdLineText = """
 There is a problem with the command line:

    {0}
    {1}
 Use -? for option descriptions
"""
STR_ErrorParsingEnd = """
    The command line arguments ended unexpectedly at: {0}
"""
STR_ErrorParsingValidValue = """
    {0} is not a valid value for {1}
"""
STR_ErrorParsingInt = """
    Expecting integer value folowing: {0}
"""
STR_ErrorParsingValueRequired = """
    Error parsing: {0}
    A value was required for the parameter.
"""
STR_ErrorBadPath = """
    Unable to process path and/or file filter:

        {0}

    The path must exist, and the file filter must be a valid name or wildcard.
"""
STR_ErrorConfigFileNameHasPath = """
    Configuration file name cannot include a path

    Surveyor searches for a file with the config file name in each folder
    being measured; not a specific config in a specific location.

    Normally you will place a single config file in the root of your
    project, but behavior may be changed in subfolders by additional config
    files with the same name.
"""
