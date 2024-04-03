import sys

# import argparse

from ._main import main
from .utils import listen_to_logs


def cli(argv=None):
    argv = sys.argv if argv is None else argv
    if "--listen" in argv:
        listen_to_logs()
    else:
        main()
