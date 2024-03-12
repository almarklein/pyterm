import msvcrt
import ctypes
from ctypes import wintypes

from .terminal import Terminal


KERNEL32 = ctypes.WinDLL("kernel32", use_last_error=True)  # type: ignore

ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
ENABLE_VIRTUAL_TERMINAL_INPUT = 0x0200


def get_console_mode(fd) -> int:
    """Get the console mode for a given file descriptor (for stdout or stdin)"""
    windows_filehandle = msvcrt.get_osfhandle(fd)  # type: ignore
    mode = wintypes.DWORD()
    KERNEL32.GetConsoleMode(windows_filehandle, ctypes.byref(mode))
    return mode.value


def set_console_mode(fd, mode: int) -> bool:
    """Set the console mode for a given file descriptor (for stdout or stdin)."""
    windows_filehandle = msvcrt.get_osfhandle(fd)  # type: ignore
    success = KERNEL32.SetConsoleMode(windows_filehandle, mode)
    return success


class WindowsTerminal(Terminal):

    def __init__(self, **kwargs):
        self._ori_mode_in = None
        self._ori_mode_out = None
        super().__init__(**kwargs)

    def _set_terminal_mode(self):
        # Get current mode
        mode_in = get_console_mode(self.fd_in)
        mode_out = get_console_mode(self.fd_out)
        # Store for reset
        self._ori_mode_in = mode_in
        self._ori_mode_out = mode_out
        # Update
        set_console_mode(self.fd_in, ENABLE_VIRTUAL_TERMINAL_INPUT)
        set_console_mode(self.fd_out, mode_out | ENABLE_VIRTUAL_TERMINAL_PROCESSING)

    def _reset(self):
        if self._ori_mode_in is not None:
            set_console_mode(self.fd_in, self._ori_mode_in)
            set_console_mode(self.fd_out, self._ori_mode_out)
            self._ori_mode_in = self._ori_mode_out = None
