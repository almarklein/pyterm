"""
Loop logic.
"""

import time
import logging
import threading


logger = logging.getLogger("pyterm")


class BaseLoop:
    """Base loop class. All methods must be thread-safe.
    """

    def __init__(self, name):
        pass

    def call_soon(self, func):
        raise NotImplementedError()

    def is_running(self):
        raise NotImplementedError()

    def is_closed(self):
        raise NotImplementedError()


class RawLoop(BaseLoop):

    def __init__(self):
        self._func_stack = []
        self._is_running = False
        self._lock = threading.RLock()

    def run(self):
        self._is_running = True
        logger.info("Entering raw loop")

        try:
            while True:
                time.sleep(0.02)
                func = self._get_func_to_call()
                if func is not None:
                    self._call(func)
        finally:
            self._is_running = False
            logger.info("Exiting raw loop")

    def _get_func_to_call(self):
        with self._lock:
            if self._func_stack:
                return self._func_stack.pop(0)

    def _call(self, func):
        try:
            func()
        except Exception as err:
            logger.error(f"Internal pyterm error: {err}")

    def call_soon(self, func):
        with self._lock:
            self._func_stack.append(func)

    def is_running(self):
        return self._is_running

    def is_closed(self):
        return False


class DebugLoop(BaseLoop):
    """ A raw loop during debugging?"""
    pass



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
