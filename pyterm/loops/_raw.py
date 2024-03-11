from ._base import BaseLoop


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
