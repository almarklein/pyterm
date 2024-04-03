import os
import logging
import threading
from codecs import getincrementaldecoder

from ._escape_code_decoder import EscapeCodeDecoder


logger = logging.getLogger("pyterm")


class InputReader(threading.Thread):
    """A thread that reads from stdin and feeds the result into the main thread's event loop."""

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
