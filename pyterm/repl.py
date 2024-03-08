import os
import sys
import time
import queue
import logging
import platform
import struct
import shlex
from codeop import CommandCompiler
import traceback
import keyword
import inspect  # noqa - Must be in this namespace
import bdb
import linecache


printDirect = print

# todo: clean this up ...
# todo: prompts and inputs and such.
# todo: Probably some gems here: https://github.com/almarklein/heart_of_prompt_toolit


class PS1:
    """Dynamic prompt for PS1."""

    def __init__(self, repl):
        self._repl = repl

    def __str__(self):
        if self._repl._dbFrames:
            # When debugging, show where we are.
            preamble = "(" + self._repl._dbFrameName + ")"
            return "\n\x1b[0;32m%s>>>\x1b[0m " % preamble
        else:
            # Normal Python prompt
            return "\n\x1b[0;32m>>>\x1b[0m "


class PS2:
    """Dynamic prompt for PS2."""

    def __init__(self, repl):
        self._repl = repl

    def __str__(self):
        if self._repl._dbFrames:
            # When debugging, show where we are.
            preamble = "(" + self._repl._dbFrameName + ")"
            return "\x1b[0;32m%s...\x1b[0m " % preamble
        else:
            # Just dots
            return "\x1b[0;32m...\x1b[0m "


class Repl:

    def __init__(self, locals, lines_queue):
        self.lines_queue = lines_queue

        self._filename = "<console>"

        # Init variables for locals and globals (globals only for debugging)
        self.locals = locals
        self.globals = None

        # Init last traceback information
        sys.last_type = None
        sys.last_value = None
        sys.last_traceback = None

        # Flag to ignore sys exit, to allow running some scripts
        # interactively, even if they call sys.exit.
        self.ignore_sys_exit = False

        # Information for debugging. If self._dbFrames, we're in debug mode
        # _dbFrameIndex starts from 1
        self._dbFrames = []
        self._dbFrameIndex = 0
        self._dbFrameName = ""

        # Init datase to store source code that we execute
        self._codeCollection = ExecutedSourceCollection()

        # Init buffer to deal with multi-line command in the shell
        self._buffer = []

        # Create compiler
        if sys.platform.startswith("java"):
            import compiler

            self._compile = compiler.compile  # or 'exec' does not work
        else:
            self._compile = CommandCompiler()

        # # Instantiate magician and tracer
        # self.magician = Magician()
        # self.debugger = Debugger()

        # To keep track of whether to send a new prompt, and whether more
        # code is expected.
        self.more = 0
        self.newPrompt = True
        self._oldPromptString = None

        # Code and script to run on first iteration
        self._codeToRunOnStartup = None
        self._scriptToRunOnStartup = None

        # Remove "THIS" directory from the PYTHONPATH
        # to prevent unwanted imports. Same for pyzokernel dir
        thisPath = os.getcwd()
        for p in [thisPath, os.path.join(thisPath, "pyzokernel")]:
            while p in sys.path:
                sys.path.remove(p)

        self._prepare()

    def _prepare(self):
        """Prepare for running the main loop."""

        # Reset debug status
        # self.debugger.writestatus()

        # Set startup info (with additional info)
        if sys.platform.startswith("java"):
            import __builtin__ as builtins  # Jython
        else:
            builtins = __builtins__
        if not isinstance(builtins, dict):
            builtins = builtins.__dict__
        startup_info = {}
        startup_info["builtins"] = [builtin for builtin in builtins.keys()]
        startup_info["version"] = tuple(sys.version_info)
        startup_info["keywords"] = keyword.kwlist

        # Prepare the Python environment
        # self._prepare_environment(startup_info)
        # self._run_startup_code(startup_info)

        # Write Python banner (to stdout)
        thename = "Python"
        if "__pypy__" in sys.builtin_module_names:
            thename = "Pypy"
        if sys.platform.startswith("java"):
            thename = "Jython"
            # Jython cannot do struct.calcsize("P")
            import java.lang

            real_plat = java.lang.System.getProperty("os.name").lower()
            plat = "%s/%s" % (sys.platform, real_plat)
        elif sys.platform.startswith("win"):
            NBITS = 8 * struct.calcsize("P")
            plat = "Windows (%i bits)" % NBITS
        else:
            NBITS = 8 * struct.calcsize("P")
            plat = "%s (%i bits)" % (sys.platform, NBITS)
        printDirect(
            "%s %s on %s.\n" % (thename, sys.version.split("[")[0].rstrip(), plat)
        )

        # Write pyterm part of banner (including what GUI loop is integrated)
        printDirect("This is the pyterm.")

        # Set prompts
        sys.ps1 = PS1(self)
        sys.ps2 = PS2(self)

        # # Notify about project path
        # projectPath = startup_info["projectPath"]
        # if projectPath:
        #     printDirect("Prepending the project path %r to sys.path\n" % projectPath)

        printDirect(
            "Type 'help' for help, " + "type '?' for a list of *magic* commands.\n"
        )

        # Notify the running of the script
        if self._scriptToRunOnStartup:
            printDirect(
                '\x1b[0;33mRunning script: "'
                + self._scriptToRunOnStartup
                + '"\x1b[0m\n'
            )

        # Prevent app nap on OSX 9.2 and up
        # The _nope module is taken from MINRK's appnope package
        if sys.platform == "darwin":

            def parse_version_crudely(version_string):
                """extracts the leading number parts of a version string to a tuple
                e.g.: "123.45ew6.7x.dev8" --> (123, 45, 7)
                """
                import re

                return tuple(
                    int(s) for s in re.findall(r"\.(\d+)", "." + version_string)
                )

            parsev = parse_version_crudely
            if parsev(platform.mac_ver()[0]) >= parsev("10.9"):
                from . import _nope

                _nope.nope()

        # Setup post-mortem debugging via appropriately logged exceptions
        class PMHandler(logging.Handler):
            def emit(self, record):
                if record.exc_info:
                    sys.last_type, sys.last_value, sys.last_traceback = record.exc_info
                return record

        # Setup logging
        root_logger = logging.getLogger()
        if not root_logger.handlers:
            root_logger.addHandler(logging.StreamHandler())
        root_logger.addHandler(PMHandler())

        # Warn when logging.basicConfig is used (see issue #645)
        def basicConfigDoesNothing(*args, **kwargs):
            logging.warn(
                "Pyterm already added handlers to the root handler, "
                + "so logging.basicConfig() does nothing."
            )

        try:
            logging.basicConfig = basicConfigDoesNothing
        except Exception:
            pass

    def _prepare_environment(self, startup_info):
        """Prepare the Python environment. There are two possibilities:
        either we run a script or we run interactively.
        """

        # Get whether we should (and can) run as script
        scriptFilename = startup_info["scriptFile"]
        if scriptFilename:
            if not os.path.isfile(scriptFilename):
                printDirect('Invalid script file: "' + scriptFilename + '"\n')
                scriptFilename = None

        # Get project path
        projectPath = startup_info["projectPath"]

        if scriptFilename.endswith(".ipynb"):
            # Run Jupyter notebook
            import notebook.notebookapp

            sys.argv = ["jupyter_notebook", scriptFilename]
            sys.exit(notebook.notebookapp.main())

        elif scriptFilename:
            # RUN AS SCRIPT
            # Set __file__  (note that __name__ is already '__main__')
            self.locals["__file__"] = scriptFilename
            # Set command line arguments
            sys.argv[:] = []
            sys.argv.append(scriptFilename)
            sys.argv.extend(shlex.split(startup_info.get("argv", "")))
            # Insert script directory to path
            theDir = os.path.abspath(os.path.dirname(scriptFilename))
            if theDir not in sys.path:
                sys.path.insert(0, theDir)
            if projectPath is not None:
                sys.path.insert(0, projectPath)
            # Go to script dir
            os.chdir(os.path.dirname(scriptFilename))
            # Run script later
            self._scriptToRunOnStartup = scriptFilename
        else:
            # RUN INTERACTIVELY
            # No __file__ (note that __name__ is already '__main__')
            self.locals.pop("__file__", "")
            # Remove all command line arguments, set first to empty string
            sys.argv[:] = []
            sys.argv.append("")
            sys.argv.extend(shlex.split(startup_info.get("argv", "")))
            # Insert current directory to path
            sys.path.insert(0, "")
            if projectPath:
                sys.path.insert(0, projectPath)
            # Go to start dir
            startDir = startup_info["startDir"]
            if startDir and os.path.isdir(startDir):
                os.chdir(startDir)
            else:
                os.chdir(os.path.expanduser("~"))  # home dir

    def _run_startup_code(self, startup_info):
        """Execute the startup code or script."""

        # Run startup script (if set)
        script = startup_info["startupScript"]
        # Should we use the default startupScript?
        if script == "$PYTHONSTARTUP":
            script = os.environ.get("PYTHONSTARTUP", "")

        if "\n" in script:
            # Run code later or now
            linesBefore = []
            linesAfter = script.splitlines()
            while linesAfter:
                if linesAfter[0].startswith("# AFTER_GUI"):
                    linesAfter.pop(0)
                    break
                linesBefore.append(linesAfter.pop(0))
            scriptBefore = "\n".join(linesBefore)
            self._codeToRunOnStartup = "\n".join(linesAfter)
            if scriptBefore.strip():  # don't trigger when only empty lines
                self.context._stat_interpreter.send("Busy")
                msg = {"source": scriptBefore, "fname": "<startup>", "lineno": 0}
                self.runlargecode(msg, True)
        elif script and os.path.isfile(script):
            # Run script
            self.context._stat_interpreter.send("Busy")
            self.runfile(script)
        else:
            # Nothing to run
            pass

    def iter(self):
        """Do one iteration of processing commands (the REPL)."""
        try:
            self._process_commands()

        except SystemExit:
            # It may be that we should ignore sys exit now...
            if self.ignore_sys_exit:
                self.ignore_sys_exit = False  # Never skip more than once
                return
            # Get and store the exception so we can raise it later
            type, value, tb = sys.exc_info()
            del tb
            self._exitException = value
            # Stop debugger if it is running
            # self.debugger.stopinteraction()

    def _process_commands(self):
        # Run startup code/script inside the loop (only the first time)
        # so that keyboard interrupt will work
        if self._codeToRunOnStartup:
            self.context._stat_interpreter.send("Busy")
            self._codeToRunOnStartup, tmp = None, self._codeToRunOnStartup
            self._runlines(tmp, filename="<startup_after_gui>", symbol="exec")
        if self._scriptToRunOnStartup:
            self.context._stat_interpreter.send("Busy")
            self._scriptToRunOnStartup, tmp = None, self._scriptToRunOnStartup
            self.runfile(tmp)

        # Flush real stdout / stderr
        sys.__stdout__.flush()
        sys.__stderr__.flush()

        # Set status and prompt?
        # Prompt is allowed to be an object with __str__ method
        # We also compare prompt strings because stack frame changes
        # caused by a breakpoint while running the gui event loop
        # would get unnotified otherwise.
        promptString = str(sys.ps2 if self.more else sys.ps1)
        if self.newPrompt or promptString != self._oldPromptString:
            self.newPrompt = False
            self._oldPromptString = promptString

        if True:
            # Determine state. The message is really only send
            # when the state is different. Note that the kernelbroker
            # can also set the state ("Very busy", "Busy", "Dead")
            if self._dbFrames:
                pass  # self.context._stat_interpreter.send("Debug")
            elif self.more:
                pass  # self.context._stat_interpreter.send("More")
            else:
                pass  # self.context._stat_interpreter.send("Ready")
            # self.context._stat_cd.send(os.getcwd())

        # Are we still connected?
        if sys.stdin.closed:
            # Exit from main loop.
            # This will raise SystemExit and will shut us down in the
            # most appropriate way
            sys.exit()

        # Get the queue with lines
        try:
            lines_queue = self.lines_queue
        except Exception:
            return

        # Read a line
        try:
            line1 = lines_queue.get_nowait().decode()
        except queue.Empty:
            return

        if True:
            # Read command
            if line1:
                # Notify what we're doing
                self.newPrompt = True
                # Convert command
                line2 = line1  # self.magician.convert_command(line1.rstrip("\n"))
                # Execute actual code
                if line2 is not None:
                    for line3 in line2.split("\n"):  # not splitlines!
                        self.more = self.pushline(line3)
                else:
                    self.more = False
                    self._resetbuffer()

        elif False:
            # Read larger block of code (dict)
            msg = self.context._ctrl_code.recv(False)
            if msg:
                # Notify what we're doing
                # (runlargecode() sends on stdin-echo)
                self.context._stat_interpreter.send("Busy")
                self.newPrompt = True
                # Execute code
                self.runlargecode(msg)
                # Reset more stuff
                self._resetbuffer()
                self.more = False

    ## Running code in various ways
    # In all cases there is a call for compilecode and a call to execcode

    def _resetbuffer(self):
        """Reset the input buffer."""
        self._buffer = []

    def pushline(self, line):
        """Push a line to the interpreter.

        The line should not have a trailing newline; it may have
        internal newlines.  The line is appended to a buffer and the
        interpreter's _runlines() method is called with the
        concatenated contents of the buffer as source.  If this
        indicates that the command was executed or invalid, the buffer
        is reset; otherwise, the command is incomplete, and the buffer
        is left as it was after the line was appended.  The return
        value is 1 if more input is required, 0 if the line was dealt
        with in some way (this is the same as _runlines()).

        """
        # Get buffer, join to get source
        buffer = self._buffer
        buffer.append(line)
        source = "\n".join(buffer)
        # Clear buffer and run source
        self._resetbuffer()
        more = self._runlines(source, self._filename)
        # Create buffer if needed
        if more:
            self._buffer = buffer
        return more

    def _runlines(self, source, filename="<input>", symbol="single"):
        """Compile and run some source in the interpreter.

        Arguments are as for compile_command().

        One several things can happen:

        1) The input is incorrect; compile_command() raised an
        exception (SyntaxError or OverflowError).  A syntax traceback
        will be printed by calling the showsyntaxerror() method.

        2) The input is incomplete, and more input is required;
        compile_command() returned None.  Nothing happens.

        3) The input is complete; compile_command() returned a code
        object.  The code is executed by calling self.execcode() (which
        also handles run-time exceptions, except for SystemExit).

        The return value is True in case 2, False in the other cases (unless
        an exception is raised).  The return value can be used to
        decide whether to use sys.ps1 or sys.ps2 to prompt the next
        line.

        """

        # Try compiling.
        error = None
        try:
            code = self.compilecode(source, filename, symbol)
        except (OverflowError, SyntaxError, ValueError):
            error = sys.exc_info()[1]
            code = False

        if code is None:
            # Case 2
            return True
        elif not code:
            # Case 1, a bit awkward way to show the error, but we need
            # to call showsyntaxerror in an exception handler.
            try:
                raise error
            except Exception:
                self.showsyntaxerror(filename)
            return False
        else:
            # Case 3
            self.execcode(code)
            return False

    def runlargecode(self, msg, silent=False):
        """To execute larger pieces of code."""

        # Get information
        source, fname, lineno = msg["source"], msg["fname"], msg["lineno"]
        cellName = msg.get("cellName", "")
        source += "\n"

        # Change directory?
        if msg.get("changeDir", False) and os.path.isfile(fname):
            d = os.path.normpath(os.path.normcase(os.path.dirname(fname)))
            if d != os.getcwd():
                os.chdir(d)

        # Construct notification message
        lineno1 = lineno + 1
        lineno2 = lineno + source.count("\n")
        fname_show = fname
        if not fname.startswith("<"):
            fname_show = os.path.split(fname)[1]
        if cellName == fname:
            runtext = '(executing file "%s")\n' % fname_show
        elif cellName:
            runtext = '(executing cell "%s" (line %i of "%s"))\n' % (
                cellName.strip(),
                lineno1,
                fname_show,
            )
            # Try to get the last expression printed in the cell.
            try:
                import ast

                tree = ast.parse(source, fname, "exec")
                if (
                    isinstance(tree.body[-1], ast.Expr)
                    and tree.body[-1].col_offset == 0
                ):
                    e = tree.body[-1]
                    lines = source.splitlines()
                    lines[e.lineno - 1] = "_=\\\n" + lines[e.lineno - 1]
                    source2 = (
                        "\n".join(lines).rstrip()
                        + "\nif _ is not None:\n  print(repr(_))\n"
                    )
                    ast.parse(
                        source2, fname, "exec"
                    )  # This is to make sure it still compiles
                    source = source2
            except Exception:
                pass
        elif lineno1 == lineno2:
            runtext = '(executing line %i of "%s")\n' % (lineno1, fname_show)
        else:
            runtext = '(executing lines %i to %i of "%s")\n' % (
                lineno1,
                lineno2,
                fname_show,
            )
        # Notify IDE
        if not silent:
            self.context._strm_echo.send("\x1b[0;33m%s\x1b[0m" % runtext)

        # Bring fname to the canonical form so that pdb recognizes the breakpoints,
        # otherwise filename r"C:\..." would be different from canonical form r"c:\..."
        fname = self.debugger.canonic(fname)

        # Put the line number in the filename (if necessary)
        # Note that we could store the line offset in the _codeCollection,
        # but then we cannot retrieve it for syntax errors.
        if lineno:
            fname = "%s+%i" % (fname, lineno)

        # Try compiling the source
        code = None
        try:
            # Compile
            code = self.compilecode(source, fname, "exec")

        except (OverflowError, SyntaxError, ValueError):
            self.showsyntaxerror(fname)
            return

        if code:
            # Store the source using the (id of the) code object as a key
            self._codeCollection.store_source(code, source)
            # Execute the code
            self.execcode(code)
        else:
            # Incomplete code
            self.write("Could not run code because it is incomplete.\n")

    def runfile(self, fname):
        """To execute the startup script."""

        # Get text (make sure it ends with a newline)
        try:
            with open(fname, "rb") as fd:
                bb = fd.read()
            encoding = "UTF-8"
            firstline = bb.split(b"\n", 1)[0].decode("ascii", "ignore")
            if firstline.startswith("#") and "coding" in firstline:
                encoding = firstline.split("coding", 1)[-1].strip(" \t\r\n:=-*")
            source = bb.decode(encoding)
        except Exception:
            printDirect(
                "Could not read script (decoding using %s): %r\n" % (encoding, fname)
            )
            return
        try:
            source = source.replace("\r\n", "\n").replace("\r", "\n")
            if source[-1] != "\n":
                source += "\n"
        except Exception:
            printDirect('Could not execute script: "' + fname + '"\n')
            return

        # Try compiling the source
        code = None
        try:
            # Compile
            code = self.compilecode(source, fname, "exec")
        except (OverflowError, SyntaxError, ValueError):
            time.sleep(0.2)  # Give stdout time to be send
            self.showsyntaxerror(fname)
            return

        if code:
            # Store the source using the (id of the) code object as a key
            self._codeCollection.store_source(code, source)
            # Execute the code
            self.execcode(code)
        else:
            # Incomplete code
            self.write("Could not run code because it is incomplete.\n")

    def compilecode(self, source, filename, mode, *args, **kwargs):
        """Compile source code.
        Will mangle coding definitions on first two lines.

        * This method should be called with Unicode sources.
        * Source newlines should consist only of LF characters.
        """

        # This method solves pyzo issue 22

        # Split in first two lines and the rest
        parts = source.split("\n", 2)

        # Replace any coding definitions
        ci = "coding is"
        contained_coding = False
        for i in range(len(parts) - 1):
            tmp = parts[i]
            if tmp and tmp[0] == "#" and "coding" in tmp:
                contained_coding = True
                parts[i] = tmp.replace("coding=", ci).replace("coding:", ci)

        # Combine parts again (if necessary)
        if contained_coding:
            source = "\n".join(parts)

        # Compile
        return self._compile(source, filename, mode, *args, **kwargs)

    def execcode(self, code):
        """Execute a code object.

        When an exception occurs, self.showtraceback() is called to
        display a traceback.  All exceptions are caught except
        SystemExit, which is reraised.

        A note about KeyboardInterrupt: this exception may occur
        elsewhere in this code, and may not always be caught.  The
        caller should be prepared to deal with it.

        The globals variable is used when in debug mode.
        """

        try:
            if self._dbFrames:
                self.apply_breakpoints()
                exec(code, self.globals, self.locals)
            else:
                # Turn debugger on at this point. If there are no breakpoints,
                # the tracing is disabled for better performance.
                self.apply_breakpoints()
                # self.debugger.set_on()
                exec(code, self.locals)
        except bdb.BdbQuit:
            self.dbstop_handler()
        except Exception:
            time.sleep(0.2)  # Give stdout some time to send data
            self.showtraceback()
        except KeyboardInterrupt:  # is a BaseException, not an Exception
            time.sleep(0.2)
            self.showtraceback()

    def apply_breakpoints(self):
        """Breakpoints are updated at each time a command is given,
        including commands like "db continue".
        """
        return
        try:
            breaks = self.context._stat_breakpoints.recv()
            if self.debugger.breaks:
                self.debugger.clear_all_breaks()
            if breaks:  # Can be None
                for fname in breaks:
                    for linenr in breaks[fname]:
                        self.debugger.set_break(fname, linenr)
        except Exception:
            type, value, tb = sys.exc_info()
            del tb
            print("Error while setting breakpoints: %s" % str(value))

    ## Handlers and hooks

    def dbstop_handler(self, *args, **kwargs):
        print("Program execution stopped from debugger.")

    ## Writing and error handling

    def write(self, text):
        """Write errors."""
        sys.stderr.write(text)

    def showsyntaxerror(self, filename=None):
        """Display the syntax error that just occurred.
        This doesn't display a stack trace because there isn't one.
        If a filename is given, it is stuffed in the exception instead
        of what was there before (because Python's parser always uses
        "<string>" when reading from a string).

        Pyzo version: support to display the right line number,
        see doc of showtraceback for details.
        """

        # Get info (do not store)
        type, value, tb = sys.exc_info()
        del tb

        # Work hard to stuff the correct filename in the exception
        if filename and type is SyntaxError:
            try:
                # unpack information
                msg, (dummy_filename, lineno, offset, line) = value
                # correct line-number
                fname, lineno = self.correctfilenameandlineno(filename, lineno)
            except Exception:
                # Not the format we expect; leave it alone
                pass
            else:
                # Stuff in the right filename
                value = SyntaxError(msg, (fname, lineno, offset, line))
                sys.last_value = value

        # Show syntax error
        strList = traceback.format_exception_only(type, value)
        for s in strList:
            self.write(s)

    def showtraceback(self, useLastTraceback=False):
        """Display the exception that just occurred.
        We remove the first stack item because it is our own code.
        The output is written by self.write(), below.

        In the pyzo version, before executing a block of code,
        the filename is modified by appending " [x]". Where x is
        the index in a list that we keep, of tuples
        (sourcecode, filename, lineno).

        Here, showing the traceback, we check if we see such [x],
        and if so, we extract the line of code where it went wrong,
        and correct the lineno, so it will point at the right line
        in the editor if part of a file was executed. When the file
        was modified since the part in question was executed, the
        fileno might deviate, but the line of code shown shall
        always be correct...
        """
        # Traceback info:
        # tb_next -> go down the trace
        # tb_frame -> get the stack frame
        # tb_lineno -> where it went wrong
        #
        # Frame info:
        # f_back -> go up (towards caller)
        # f_code -> code object
        # f_locals -> we can execute code here when PM debugging
        # f_globals
        # f_trace -> (can be None) function for debugging? (
        #
        # The traceback module is used to obtain prints from the
        # traceback.

        try:
            if useLastTraceback:
                # Get traceback info from buffered
                type = sys.last_type
                value = sys.last_value
                tb = sys.last_traceback
            else:
                # Get exception information and remove first, since that's us
                type, value, tb = sys.exc_info()
                tb = tb.tb_next

                # Store for debugging, but only store if not in debug mode
                if not self._dbFrames:
                    sys.last_type = type
                    sys.last_value = value
                    sys.last_traceback = tb

            # Get traceback to correct all the line numbers
            # tblist = list  of (filename, line-number, function-name, text)
            tblist = traceback.extract_tb(tb)

            # Get frames
            frames = []
            while tb:
                frames.append(tb.tb_frame)
                tb = tb.tb_next

            # Walk through the list
            for i in range(len(tblist)):
                tbInfo = tblist[i]
                # Get filename and line number, init example
                fname, lineno = self.correctfilenameandlineno(tbInfo[0], tbInfo[1])
                if not isinstance(fname, str):
                    fname = fname.decode("utf-8")
                example = tbInfo[3]
                # Reset info
                tblist[i] = (fname, lineno, tbInfo[2], example)

            # Format list
            strList = traceback.format_list(tblist)
            if strList:
                strList.insert(0, "Traceback (most recent call last):\n")
            strList.extend(traceback.format_exception_only(type, value))

            # Write traceback
            for s in strList:
                self.write(s)

            # Clean up (we cannot combine except and finally in Python <2.5
            tb = None
            frames = None

        except Exception:
            type, value, tb = sys.exc_info()
            tb = None
            frames = None
            t = "An error occured, but then another one when trying to write the traceback: "
            t += str(value) + "\n"
            self.write(t)

    def correctfilenameandlineno(self, fname, lineno):
        """Given a filename and lineno, this function returns
        a modified (if necessary) version of the two.
        As example:
        "foo.py+7", 22  -> "foo.py", 29
        """
        j = fname.rfind("+")
        if j > 0:
            try:
                lineno += int(fname[j + 1 :])
                fname = fname[:j]
            except ValueError:
                pass
        return fname, lineno


class ExecutedSourceCollection:
    """Stores the source of executed pieces of code, so that the right
    traceback can be reproduced when an error occurs. The filename
    (including the +lineno suffix) is used as a key. We monkey-patch
    the linecache module so that we first try our cache to look up the
    lines. In that way we also allow third party modules
    to get the lines for executed cells.
    """

    def __init__(self):
        self._cache = {}
        self._patch()

    def store_source(self, codeObject, source):
        self._cache[codeObject.co_filename] = source

    def _patch(self):
        def getlines(filename, module_globals=None):
            # !!! do not use "import" inside this function because it can
            # cause an infinite recursion loop with the import override in
            # module shiboken6 (PySide6) !!!

            # Try getting the source from our own cache,
            # otherwise fallback to linecache's own cache
            src = self._cache.get(filename, "")
            if src:
                return [line + "\n" for line in src.splitlines()]
            else:
                if module_globals is None:
                    return linecache._getlines(filename)  # only valid sig in 2.4
                else:
                    return linecache._getlines(filename, module_globals)

        # Monkey patch
        linecache._getlines = linecache.getlines
        linecache.getlines = getlines
