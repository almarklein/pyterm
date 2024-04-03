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
    """Object to manage the active loops.

    Basically it keeps track of a collection of loops. When a request is made to
    call a function (via ``call_in_loops()``) it will schedule a call in all loops,
    so that if any becomes active, it works.
    """

    def __init__(self):
        self._loops = []

    def clean(self):
        """Purge closed loops."""
        # todo: allow an asyncio loop to be run multiple times, it does not close in between, does it?
        self._loops = [loop for loop in self._loops if not loop.is_closed()]

    def add_loop(self, loop):
        """Add a loop to the collection."""
        self.clean()
        assert isinstance(loop, BaseLoop)
        self._loops.append(loop)

    def call_in_loops(self, func):
        """Call the given function in the active loop.

        The function *can* be called multiple times, possibly at a much later
        time (e.g. when an event-loop is closed and the outer loop becomes
        active again).
        """
        self.clean()
        for loop in self._loops:
            if loop.is_running:
                loop.call_soon(func)


# Create global instance
loop_manager = LoopManager()
