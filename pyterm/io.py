"""
Handling reading from stdin.
"""

import io
import sys
import queue
import logging
import threading


logger = logging.getLogger("pyterm")


class StdinBuffer:
    def __init__(self, lines_queue, name="<stdin>", isatty=True):
        self._name = name
        self._closed = False
        self._isatty = isatty
        self.lines_queue = lines_queue

    def __del__(self):
        self.close()

    @property
    def name(self):
        return self._name

    @property
    def newlines(self):
        return None

    @property
    def closed(self):
        return self._closed

    def close(self):
        """Close the file object."""
        sys.__stdin__.close()
        self._closed = True
        return

    def detach(self):
        raise io.UnsupportedOperation("Stream does not support detach.")

    def readable(self):
        return True

    def writable(self):
        return False

    def seekable(self):
        return False

    def flush(self):
        pass

    def isatty(self):
        return self._isatty

    # def fileno(self) -> if we implement it to raise an error, TextIOWrapper(..) fails

    def read(self, size=-1):
        raise io.UnsupportedOperation(
            "If your application reads from stdin, you should probably not boot it via pyterm! Note that readline is supported though."
        )

    def readline(self, size=-1):
        return self.lines_queue.get()


class Stdin(io.TextIOWrapper):

    def readline(self, size=-1):
        return self.buffer.readline(size).decode()


class InputThread(threading.Thread):
    """To read from stdin and feed the result into the main thread's event loop."""

    def __init__(self, lines_queue, line_callback):
        super().__init__()
        self.lines_queue = lines_queue
        self.line_callback = line_callback
        self.daemon = True

    def run(self):
        logger.info("input thread started")
        rfile = sys.__stdin__.buffer  # binary file io
        try:
            while True:
                line = rfile.readline()
                if not line:  # stdin is closed
                    break
                elif line.startswith(b"%pyterm{"):
                    pass  # todo: special command
                else:
                    self.lines_queue.put(line)
                    try:
                        self.line_callback()
                    except Exception as err:
                        logger.error(f"Error in line callback: {err}")
        except Exception as err:
            logger.error(f"io thread errored: {str(err)}")
        else:
            logger.info("io thread stopped")


class StdoutWithPrompt(io.TextIOWrapper):

    def __init__(self, buffer):
        super().__init__(buffer)
        self._last_prompt = ""

    def write(self, text):
        if self._last_prompt:
            super().write("\r")
        super().write(text)


# # A ref to the current input thread to prevent it from being deleted
# input_thread = None


# def patch_stdin(line_callback, line):
#     global input_thread
#
#     if input_thread and input_thread.is_alive():
#         raise RuntimeError("Input thread is already running.")
#
#     lines_queue = queue.Queue()
#     sys.stdin = Stdin(StdinBuffer(lines_queue))
#     input_thread = InputThread(lines_queue, line_callback)
#     input_thread.start()
#
#     # todo: also patch stdout and stderr?
#     # Set fileno on both outputs
#     # sys.stdout.fileno = sys.__stdout__.fileno
#     # sys.stderr.fileno = sys.__stderr__.fileno
