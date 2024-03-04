"""
This subpackage implements a simple terminal. This is similar to the
code at the heart of e.g. prompt_toolkit and Textual. Since it's 2024
I'm ok with supporting only win10 and up. This means we can use a
sensible subset of vt100. I also want this to work on VSCode, so we
also limit to what xterm.js supports.

We don't use curses, because that's Unix only, and would require a whole
separate implementation for Windows. Using vt100-ish escape sequences
allows us to target a broad audience, with nearly the same code.

There are a few parts where the code for Unix and Windows needs to
differ. This is why we have a base class, with implementations for Unix
and Windows.
"""

import sys
import signal


class Terminal:
    """ Base class for a simple terminal.

    Instantiating this class produces a class corresponding with the
    current platform.
    """

    def __new__(cls, **kwargs):
        # Select terminal class
        if sys.platform.startswith("win"):
            from .terminal_windows import WindowsTerminal as Terminal
            return windows.WindowsTerminal()
        else:
           from .terminal_unix import UnixTerminal as Terminal
        return super().__new__(Terminal, **kwargs)

    def __init__(self, stdin=None, stdout=None):

        stdin = stdin or sys.__stdin__
        stdout = stdout or sys.__stdout__

        self.fd_in = stdin.fileno()
        self.fd_out = stdout.fileno()

        # Warn if it looks like this is not a terminal
        if not stdin.isatty():
            sys.stderr.write(f"Warning: Input is not a terminal: {stdin}\n")
            sys.stderr.flush()

        # Start
        self._set_terminal_mode()

        # todo: graceful handling of actual signals. In raw input mode, the ctrl-c does
        # not translate to sigint anymore, but via e.g. os.kill() a signal can still be send!
        # signal.signal(signal.SIGINT, self._exit)
        # signal.signal(signal.SIGTERM, self._exit)


    def _set_terminal_mode(self):
        raise NotImplementedError()

    def _reset(self):
        raise NotImplementedError()

    def write(self, w):
        pass

    def cursor_up(self, n):
        pass

    def cursor_down(self, n):
        pass

    def get_size(self):
        # This should work on both Unix and Windows, but the subclasses
        # can nevertheless override this, e.g. if they keep track of
        # resizes already.
        return shutil.get_terminal_size()


    def _enable_mouse_support(self) -> None:
        """Enable reporting of mouse events."""
        write = self.write
        write("\x1b[?1000h")  # SET_VT200_MOUSE
        write("\x1b[?1003h")  # SET_ANY_EVENT_MOUSE
        write("\x1b[?1015h")  # SET_VT200_HIGHLIGHT_MOUSE
        write("\x1b[?1006h")  # SET_SGR_EXT_MODE_MOUSE
        self.flush()

    def _disable_mouse_support(self) -> None:
        """Disable reporting of mouse events."""
        write = self.write
        write("\x1b[?1000l")
        write("\x1b[?1003l")
        write("\x1b[?1015l")
        write("\x1b[?1006l")
        self.flush()

    def _enable_bracketed_paste(self) -> None:
        """Enable bracketed paste mode."""
        self.write("\x1b[?2004h")

    def _disable_bracketed_paste(self) -> None:
        """Disable bracketed paste mode."""
        self.write("\x1b[?2004l")
