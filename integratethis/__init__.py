#!/usr/bin/env python3
# -*- coding: utf-8 -*-
PROG_VERSION = "Time-stamp: <2018-05-07 16:57:42 karl.voit>"

PROG_VERSION_DATE = PROG_VERSION[13:23]

DESCRIPTION = "This program integrates arbitrary commands to various tools.\n\
For example, you can add a program named \"filetags\" to the \"Send to\"\n\
folder of the context menu of the Windows File explorer via\n\
    integratethis filetags\n\
\n\
The integration method used differs from tool to tool. For the Windows Explorer,\n\
a batch file is placed within the AppData\\Roaming folder in case of additional\n\
parameters have to be added to the command and a lnk file to it is created in\n\
the \"Send to\" folder so that you can use the command from the context menu of\n\
the Windows Exporer. If no additional parameters are required, a lnk file to the\n\
command itself is placed in the \"Send to\" folder. For details, please look at\n\
the source code or read the help info for the --into parameter.\n\
\n\
You can overwrite pre-configured parameters using the command line options.\n\n"

EPILOG = u"\n\
:copyright: (c) by Karl Voit <tools@Karl-Voit.at>\n\
:license: GPL v3 or any later version\n\
:URL: https://github.com/novoid/integratethis\n\
:bugreports: via github or <tools@Karl-Voit.at>\n\
:version: " + PROG_VERSION_DATE + "\n·\n"

import sys
import os
import platform
import subprocess
import codecs

from importlib import import_module

def save_import(library):
    try:
        globals()[library] = import_module(library)
    except ImportError:
        print("Could not find Python module \"" + library +
              "\".\nPlease install it, e.g., with \"sudo pip install " + library + "\".")
        sys.exit(2)

save_import('logging')
save_import('argparse')   # for handling command line arguments

IS_WINDOWS = platform.system() == 'Windows'

if IS_WINDOWS:
    try:
        import win32com.client
    except ImportError:
        print("Could not find Python module \"win32com.client\".\nPlease install it, e.g., " +
              "with \"sudo pip install pypiwin32\".")
        sys.exit(3)

HOME = os.path.expanduser("~")

parser = argparse.ArgumentParser(prog=sys.argv[0],
                                 # keep line breaks in EPILOG and such
                                 formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog=EPILOG,
                                 description=DESCRIPTION)

parser.add_argument(dest="command", metavar='command', nargs=1, help='The command to integrate. ' +
                    "For a defined set of tools which can be installed via \"pip3 install\", parameters are pre-configured: \n" +
                    "filetags, " +
                    "appendfilename, " +
                    "date2name, " +
                    "time2name (date2name but with time-stamp), " +
                    "and more to come in the future. The path for the command is looked up " +
                    "using \"where\" (Windows) or \"which\" (all other operating systems) so that " +
                    "the command has to be found in the path of the current environment.")

parser.add_argument("--overwrite",
                    dest="overwrite", action="store_true",
                    help="Do not warn when a previous batch- or lnk-file for integration get overwritten.")

parser.add_argument("--parameter",
                    dest="parameter", nargs=1, metavar='PARAMETERS',
                    help='Optional parameter string which gets appended after the command ' +
                    'when being invoked. For example, \'filetags\' as this pre-configured ' +
                    'to "--interactive *" (on non-Windows) in order to use the interactive mode and operate ' +
                    'on all selected files.')

parser.add_argument("--confirm",
                    dest="ask_before_close_window", action="store_true",
                    help="Ask the user to confirm by pressing RETURN/ENTER before closing the " +
                    "dialog window of the batch file to run the command.")

parser.add_argument("--into",
                    dest="into", nargs=1, metavar='PROGRAM',
                    help="Explicitely define, where to integrate the program to. Valid values (according " +
                    "to your operating system) are: " +
                    "windowsexplorer (same as File Explorer; default for Windows), " +
                    "and more to come in future.")

parser.add_argument("--displayname",
                    dest="displayname", nargs=1,
                    help='Optional name that should be used instead of the command name ' +
                    'when being linked.')

parser.add_argument("--delete",
                    dest="delete", action="store_true",
                    help='Instead of integrate the program, remove its integration. ' +
                    'Command or displayname has to match the existing integration point.')

parser.add_argument("-v", "--verbose",
                    dest="verbose", action="store_true",
                    help="enable verbose mode")

parser.add_argument("-q", "--quiet",
                    dest="quiet", action="store_true",
                    help="enable quiet mode")

options = parser.parse_args()


def handle_logging():
    """Log handling and configuration"""

    if options.verbose:
        FORMAT = "%(levelname)-8s %(asctime)-15s %(message)s"
        logging.basicConfig(level=logging.DEBUG, format=FORMAT)
    elif options.quiet:
        FORMAT = "%(levelname)-8s %(message)s"
        logging.basicConfig(level=logging.ERROR, format=FORMAT)
    else:
        FORMAT = "%(levelname)-8s %(message)s"
        logging.basicConfig(level=logging.INFO, format=FORMAT)


def error_exit(errorcode, text):
    """exits with return value of errorcode and prints to stderr"""

    sys.stdout.flush()
    logging.error(text)

    sys.exit(errorcode)


def check_for_file_existence_and_exit_if_found_with_no_overwrite_parameter(filename):
    """checks if the filename (which includes its path) does exist.
    If the file is found, exit the program in case of options.overwrite is not set."""

    if os.path.isfile(filename):
        if options.overwrite:
            logging.warn('I am deleting "' + filename + '" before it gets re-generated.')
            os.remove(filename)
        else:
            error_exit(4, 'The file "' + filename +
                       '" already exists (from a prior run?). Please remove file manually and ' +
                       're-run this script or choose the --overwrite parameter.')
    else:
        logging.debug('File ' + filename +
                      ' is not found -> I can continue generating it.')


def locate_command_in_path(command):
    """Locate an executable command in the current environment.
    Return its path when found or exit otherwise."""

    if IS_WINDOWS:
        result = subprocess.run(["where", command], stdout=subprocess.PIPE)
        # e.g.: b'C:\\Python36\\Scripts\\filetags.exe'
    else:
        result = subprocess.run(["which", command], stdout=subprocess.PIPE)
        # e.g.: b'C:\\Python36\\Scripts\\filetags.exe'

    cmd_path = result.stdout[:-2]
    cmd_path_str = result.stdout.decode('ascii').strip()
    if len(cmd_path) < 1:
        error_exit(5, 'I could not find any command "' + command + '" in the path of the current environment.')
    logging.debug('command was found at: ' + cmd_path_str)
    return cmd_path_str


def determine_default_parameters_for_known_commands(command, user_command_parameters, user_into, displayname):
    """A simple look-up function that returns command, parameters and
    tool to integrate to for known, pre-defined commands."""

    command_in_path, command_parameters, batchfile, linkfile, integrate_to = False, False, False, False, False

    # the default destination paths for batchfile and linkfile
    if IS_WINDOWS:
        if os.path.isdir(os.path.join(HOME, "bin")):
            batchfile_path = os.path.join(HOME, "bin")  # I personally do maintain "~\bin\", so let's use it if it is found
        else:
            batchfile_path = os.path.join(HOME, "AppData", "Roaming")
        linkfile_path = os.path.join(HOME, "AppData", "Roaming", "Microsoft", "Windows", "SendTo")
    else:
        batchfile_path = os.path.join(HOME, ".config")
        linkfile_path = os.path.join(HOME, "bin")  # FIXXME: has to be created if not already found

    # the hard-coded/pre-configured settings for known tools:
    if command == 'filetags':
        if IS_WINDOWS:
            command_parameters = '--interactive %*'
            integrate_to = 'windowsexplorer'
            if displayname:
                batchfile = os.path.join(batchfile_path, displayname + '.bat')
                linkfile = os.path.join(linkfile_path, displayname + '.lnk')
            else:
                batchfile = os.path.join(batchfile_path, command + '.bat')
                linkfile = os.path.join(linkfile_path, command + '.lnk')
        else:
            command_parameters = '--interactive "${*}"'
            integrate_to = 'thunar'

    elif command == 'time2name':
        command = 'date2name'
        if IS_WINDOWS:
            command_parameters = '--withtime %*'
            integrate_to = 'windowsexplorer'
            if displayname:
                linkfile = os.path.join(linkfile_path, displayname + '.lnk')
                batchfile = os.path.join(batchfile_path, displayname + '.bat')
            else:
                linkfile = os.path.join(linkfile_path, 'time2name.lnk')
                batchfile = os.path.join(batchfile_path, 'time2name.bat')
        else:
            command_parameters = '--withtime "${*}"'
            integrate_to = 'thunar'

    elif command in ['appendfilename', 'date2name']:
        if IS_WINDOWS:
            command_parameters = '%*'
            integrate_to = 'windowsexplorer'
            if displayname:
                linkfile = os.path.join(linkfile_path, displayname + '.lnk')
                batchfile = os.path.join(batchfile_path, displayname + '.bat')
            else:
                linkfile = os.path.join(linkfile_path, command + '.lnk')
                batchfile = os.path.join(batchfile_path, command + '.bat')
        else:
            command_parameters = '"${*}"'
            integrate_to = 'thunar'

    # overwrite values if found in command line parameters:
    if user_command_parameters:
        command_parameters = user_command_parameters
    if user_into:
        integrate_to = user_into

    if not command_parameters:
        batchfile = False  # just to make sure; this is not needed when there are no parameters

    return locate_command_in_path(command), command_parameters, batchfile, linkfile, integrate_to


def write_batchfile(batchfile, command_in_path, parameters, ask_for_confirmation):
    """Write a batchfile that calls the command with the given parameters."""

    assert(os.path.isfile(command_in_path))
    logging.debug('called: write_batchfile(' + str(batchfile) + ', ' + str(command_in_path) +
                  ', ' + str(parameters) + ', ' + str(ask_for_confirmation) + ')')
    logging.debug('writing file ' + batchfile + ' ...')
    with codecs.open(batchfile, 'w', encoding='utf-8') as outputhandle:
        outputhandle.write('@ECHO OFF\n' +
                           'REM change drive, e.g., D:\n' +
                           '%~d1\n' +
                           'REM change directory, e.g., D:\\data processing\\subdir\\\n' +
                           'cd %~dp1\n\n\n')
        if parameters:
            outputhandle.write(command_in_path + ' ' + parameters + '\n\n')
        else:
            outputhandle.write(command_in_path + '\n\n')
        if options.ask_before_close_window:
            logging.debug('options.ask_before_close_window is active: let\'s ask the user before closing command window')
            if IS_WINDOWS:
                outputhandle.write("set /p DUMMY=Hit ENTER to continue...\n\n")
            else:
                outputhandle.write('echo "Hit ENTER to continue...\nread DUMMYVARIABLE\n\n')
        else:
            logging.debug('options.ask_before_close_window is NOT active: do not ask the user before closing command window')
            if IS_WINDOWS:
                outputhandle.write("REM set /p DUMMY=Hit ENTER to continue...\n\n")
            else:
                outputhandle.write('echo "Hit ENTER to continue...\nread DUMMYVARIABLE\n\n')
    logging.debug('file ' + batchfile + ' written')


def create_link(source, destination):
    """
    On non-Windows systems, a symbolic link is created that links
    source (existing file) to destination (the new symlink). On
    Windows systems a lnk-file is created instead.

    The reason why we have to use really poor performing error-prone
    "lnk"-files instead of symlinks on Windows is that you're required
    to have administration permission so that "SeCreateSymbolicLinkPrivilege"
    is granted. Sorry for this lousy operating system.
    See: https://docs.python.org/3/library/os.html#os.symlink for details about that.

    This is the reason why the "--tagrees" option does perform really bad
    on Windows. And "really bad" means factor 10 to 1000. I measured it.

    @param source: a file name of the source, an existing file
    @param destination: a file name for the link which is about to be created
    """

    logging.debug('create_link(' + source + ', ' + destination + ') called')
    if IS_WINDOWS:
        # do lnk-files instead of symlinks:
        shell = win32com.client.Dispatch('WScript.Shell')
        if destination.endswith('.lnk'):
            shortcut = shell.CreateShortCut(destination)
        else:
            shortcut = shell.CreateShortCut(destination + '.lnk')
        shortcut.Targetpath = source
        shortcut.WorkingDirectory = os.path.dirname(destination)
        # shortcut.IconLocation: is derived from the source file
        shortcut.save()

    else:
        # for normal operating systems, use good old high-performing symbolic links:
        os.symlink(source, destination)


def main():
    """Main function"""

    handle_logging()

    # FIXXME: implement configurations for GNU/Linux and macOS
    if not IS_WINDOWS:
        error_exit(999, 'Sorry, this tool is only configured for Windows systems. More to come in the future.')

    command_in_path = None       # command located within the current environment path
    if options.parameter:
        command_parameters = options.parameter[0]    # optional parameters for the command
    else:
        command_parameters = False
    batchfile = None             # False if not required; a file if command_parameters is not empty
    linkfile = None              # name of the link if it is required
    if options.into:
        integrate_to = options.into[0]
    else:
        integrate_to = None      # the tool to integrate the command to
    if options.displayname:
        displayname = options.displayname[0]
    else:
        displayname = None

    assert(len(options.command) == 1)

    # FIXXME: this only holds for file-based integration: add more complex integrations in future: append config files, ...
    command_in_path, command_parameters, batchfile, linkfile, integrate_to = \
        determine_default_parameters_for_known_commands(
            options.command[0].lower(),
            command_parameters,
            integrate_to,
            displayname)

    if options.delete:
        if os.path.isfile(linkfile):
            os.remove(linkfile)
            logging.info('The file "' + linkfile + '" has been removed.')
        else:
            logging.warn('The file "' + linkfile + '" could not be found to be removed.')
        if batchfile and os.path.isfile(batchfile):
            os.remove(batchfile)
            logging.info('The file "' + batchfile + '" has been removed.')
        elif os.path.isfile(batchfile):
            logging.warn('The file "' + batchfile + '" was found but was not removed because I would not even have created it for the current settings.')
        else:
            logging.debug('The file "' + batchfile + '" was not necessary to be removed.')
        sys.exit(0)

    assert(os.path.isfile(command_in_path))

    if batchfile:
        check_for_file_existence_and_exit_if_found_with_no_overwrite_parameter(batchfile)
    if linkfile:
        check_for_file_existence_and_exit_if_found_with_no_overwrite_parameter(linkfile)

    if batchfile:
        write_batchfile(batchfile,
                        command_in_path,
                        command_parameters,
                        options.ask_before_close_window)

    if integrate_to == 'windowsexplorer':
        if batchfile and linkfile:
            create_link(batchfile, linkfile)
        elif linkfile:
            create_link(command_in_path, linkfile)
    else:
        error_exit(998, 'Sorry, this tool is only configured to integrate to Windows Explorer. More to come in the future.')

    if command_parameters:
        parameter_info = ' with parameters "' + command_parameters + '"'
    else:
        parameter_info = ''
    if displayname:
        displayname_info = ' as "' + displayname + '"'
    else:
        displayname_info = ''
    logging.info('Everything went fine, you can now use ' + command_in_path +
                 parameter_info + displayname_info + ' within ' + integrate_to + '.')

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:

        logging.info("Received KeyboardInterrupt")

# END OF FILE #################################################################
