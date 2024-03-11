import os
import sys

# Enable importing also if not installed
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


import pyterm


# Special hooks exit early
if __name__ == "__main__" and len(sys.argv) >= 2:
    if sys.argv[1] in ("--version", "version"):
        print("pyterm", pyterm.__version__)
        sys.exit(0)


if __name__ == "__main__":

    # Delete stuff we do not want
    for name in [
        "os",
        "sys",
        "__file__",  # __main__ does not have a corresponding file
        "__loader__",  # prevent lines from this file to be shown in tb
    ]:
        globals().pop(name, None)
    del name

    pyterm.main()
