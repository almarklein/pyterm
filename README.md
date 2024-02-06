# pyterm

(name may still change.)

## The idea

A Python repl that replicates the interactive behavior of the Pyzo IDE, but even better.
Can be used to run Python scripts (doing `pyterm myscript.py` instead of `python pyscript.py`)
allowing one to interact with the application while its running, and after it's done. But
also as a VSCode extension, to have that nice interactive (Matlab-like) feeling. Might
become a new kernel for Pyzo too.

## Features

Automatically hooks onto a wide variety of event loops. The type of GUI integration does not
have to be chosen beforehand, because pyterm detects when a new loop is entered, and attaches
to it so it remains interactive.

Superb debugging as in Pyzo (postmortem, via breakpoint(), and via breakpoints in the IDE).

A few convenience additional commands, for running code, inspecting variables, etc.

IDE's can communicate with process to e.g. run code, acquire autocompletion lists, workspace variables, etc.

## Status

* Loop detection and hooking works for asyincio, proving the concept.
* REPL is copied from Pyzo, but rather a mess.
* Prompt does not work yet.

Next up should be the prompt, how to detect keystrokes like tab, how it can integrate with VSCode.

