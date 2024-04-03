"""
Utilities to work with the terminal and escape sequences.

This is inspired / borrows code from the heart of e.g. prompt_toolkit and
Textual. Since it's 2024 I'm ok with supporting only win10 and up. This means we
can use a sensible subset of vt100. I also want this to work on VSCode, so we
also limit to what xterm.js supports.

We don't use curses, because that's Unix only, and would require a whole
separate implementation for Windows. Using vt100-ish escape sequences allows us
to target a broad audience, with nearly the same code.

There are a few parts where the code for Unix and Windows needs to differ. This
is why we have a base Terminal class, with implementations for Unix and Windows.
"""

from ._context import TerminalContext  # noqa
from ._input_reader import InputReader  # noqa
from ._io_proxies import ProxyStdin, ProxyStdout  # noqa
