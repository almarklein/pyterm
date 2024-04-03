"""
Loop logic.
"""

import logging


logger = logging.getLogger("pyterm")


class BaseLoop:
    """Base loop class. All methods must be thread-safe."""

    def __init__(self, name):
        pass

    def call_soon(self, func):
        raise NotImplementedError()

    def is_running(self):
        raise NotImplementedError()

    def is_closed(self):
        raise NotImplementedError()


class LoopManager:

    def __init__(self):
        self._loops = []

    def clean(self):
        self._loops = [loop for loop in self._loops if not loop.is_closed()]

    def add_loop(self, loop):
        self.clean()
        assert isinstance(loop, BaseLoop)
        self._loops.append(loop)

    def call_in_loops(self, func):
        self.clean()
        for loop in self._loops:
            if loop.is_running:
                loop.call_soon(func)


loop_manager = LoopManager()
