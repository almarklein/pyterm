"""
Handling reading from stdin.
"""

import os
import io
import sys
import queue
import logging
import threading
from codecs import getincrementaldecoder

from .escape_code_decoder import EscapeCodeDecoder


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

    def __init__(self, fd, callback):
        super().__init__()
        self._fd = fd
        self._callback = callback
        self.daemon = True

    def run(self):
        logger.info("input thread started")
        fd = self._fd
        callback = self._callback
        read = os.read
        decode_utf8 = getincrementaldecoder("utf-8")().decode
        decode_escapes = EscapeCodeDecoder().decode

        try:
            while True:
                bb = read(fd, 1024)
                raw_text = decode_utf8(bb)
                texts = decode_escapes(raw_text)

                if not bb:  # stdin is closed
                    break  # todo: signal main thread to close
                for text in texts:
                    try:
                        callback(text)
                    except Exception as err:
                        logger.error(f"Error in handling input: {err}")
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


# %%
