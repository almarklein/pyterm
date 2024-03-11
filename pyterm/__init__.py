"""
pyterm - an interative Python terminal.
"""

import logging

from ._main import main

__version__ = "0.1.0"
version_info = tuple(map(int, __version__.split(".")))


logger = logging.getLogger("pyterm")
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.INFO)
