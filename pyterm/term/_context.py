import sys
import shutil


class TerminalContext:
    """Base class for a simple terminal.

    Instantiating this class produces a class corresponding with the
    current platform.
    """

    def __new__(cls, **kwargs):
        # Select terminal class
        if sys.platform.startswith("win"):
            from ._context_windows import WindowsTerminalContext as TerminalContext
        else:
            from ._context_unix import UnixTerminalContext as TerminalContext
        return super().__new__(TerminalContext, **kwargs)

    def __init__(self, stdin=None, stdout=None):

        self._entered = False

        stdin = stdin or sys.__stdin__
        stdout = stdout or sys.__stdout__
        self.fd_in = stdin.fileno()
        self.fd_out = stdout.fileno()

        # Warn if it looks like this is not a terminal
        if not stdin.isatty():
            sys.stderr.write(f"Warning: Input is not a tty: {stdin}\n")
            sys.stderr.flush()

        # todo: graceful handling of actual signals. In raw input mode, the ctrl-c does
        # not translate to sigint anymore, but via e.g. os.kill() a signal can still be send!
        # signal.signal(signal.SIGINT, self._exit)
        # signal.signal(signal.SIGTERM, self._exit)

    def __enter__(self):
        if self._entered:
            raise RuntimeError("Can only enter the context state once.")
        self._entered = True
        self._store_terminal_mode()
        self._set_terminal_mode()
        return self

    def __exit__(self, *args):
        self._entered = False
        self.reset()

    def reset(self):
        """Reset the terminal to the state it was when the context was entered."""
        self._reset_terminal_mode()

    def get_size(self):
        """Get the (estimate) terminal size."""
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

    # For subclasses to implement

    def _store_terminal_mode(self):
        raise NotImplementedError()

    def _set_terminal_mode(self):
        raise NotImplementedError()

    def _reset_terminal_mode(self):
        raise NotImplementedError()
