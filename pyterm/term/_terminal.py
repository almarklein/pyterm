import sys
import shutil


class Terminal:
    """Base class for a simple terminal.

    Instantiating this class produces a class corresponding with the
    current platform.
    """

    def __new__(cls, **kwargs):
        # Select terminal class
        if sys.platform.startswith("win"):
            from ._terminal_windows import WindowsTerminal as Terminal
        else:
            from ._terminal_unix import UnixTerminal as Terminal
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

    def reset(self):
        # todo: replace this with a context manager?
        self._reset()

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
