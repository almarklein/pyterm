import sys
import weakref
import logging
import threading

from .importhook import on_import
from .loop import BaseLoop, loop_manager


logger = logging.getLogger("pyterm")


def patch_asyncio_on_import():
    if "asyncio" in sys.modules:
        logger.warning("Patching asyncio, but it was already imported!")
        patch_asyncio(sys.modules["asyncio"])
    else:
        on_import("asyncio", patch_asyncio)


def patch_asyncio(asyncio):
    """Patch asyncio so we get notified when a new event-loop is set."""

    logger.info("Patching asyncio.")

    # # Patch DefaultEventLoopPolicy.set_event_loop.
    # # This relies on user code to call set_event_loop().
    #
    # def pyterm_set_event_loop(self, loop, *args, **kwargs):
    #     ori_set_event_loop(self, loop, *args, **kwargs)
    #     if threading.current_thread() is threading.main_thread():
    #         main_thread_sets_new_loop(loop)
    #
    # ori_set_event_loop = asyncio.DefaultEventLoopPolicy.set_event_loop
    # if "pyterm" not in ori_set_event_loop.__name__:
    #     asyncio.DefaultEventLoopPolicy.set_event_loop = pyterm_set_event_loop

    # Patch asyncio.events_set_running_loop()

    def pyterm_set_running_loop(loop, *args, **kwargs):
        ori_set_running_loop(loop, *args, **kwargs)
        if threading.current_thread() is threading.main_thread():
            main_thread_sets_new_loop(loop)

    ori_set_running_loop = asyncio.events._set_running_loop
    if "pyterm" not in ori_set_running_loop.__name__:
        asyncio.events._set_running_loop = pyterm_set_running_loop


def main_thread_sets_new_loop(loop):
    logger.info("Detected new asyncio loop.")
    loop_manager.add_loop(AsyncioLoop(loop))


class AsyncioLoop(BaseLoop):

    def __init__(self, loop):
        self._loop_ref = weakref.ref(loop)

    def call_soon(self, func):
        loop = self._loop_ref()
        if loop:
            loop.call_soon_threadsafe(func)

    def is_running(self):
        loop = self._loop_ref()
        return loop and loop.is_running()

    def is_closed(self):
        loop = self._loop_ref()
        return (loop is None) or loop.is_closed()
