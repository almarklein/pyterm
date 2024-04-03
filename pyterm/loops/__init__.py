from ._base import BaseLoop, LoopManager, loop_manager  # noqa
from ._raw import RawLoop  # noqa
from ._asyncio import enable_asyncio_loop_support  # noqa


def enable_all_loop_support():
    """Enable support for all loops (that pyterm implements)."""
    enable_asyncio_loop_support()
