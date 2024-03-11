"""
pyterm - an interative Python terminal.
"""

from ._main import main
from ._cli import cli

__version__ = "0.1.0"
version_info = tuple(map(int, __version__.split(".")))
