from ._base import BaseLoop, LoopManager, loop_manager
from ._raw import RawLoop
from ._asyncio import enable_asyncio_loop_support


def enable_all_loop_support():
    """Enable support for all loops (that pyterm implements)."""
    enable_asyncio_loop_support()
