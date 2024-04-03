import io
import sys
import logging


logger = logging.getLogger("pyterm")


class ProxyStdin(io.TextIOWrapper):
    """Object representing a proxy/fake text stdin stream."""

    def __init__(self, lines_queue, name):
        super().__init__(ProxyStdinBuffer(lines_queue, name))

    def readline(self, size=-1):
        return self.buffer.readline(size).decode()


class ProxyStdout(io.TextIOWrapper):
    """Object representing a proxy/fake text stdout stream."""

    def __init__(self, prompt, original, name):
        super().__init__(
            ProxyStdoutBuffer(prompt, original.buffer, name), encoding=original.encoding
        )

    def write(self, text):
        self.buffer.write(text.encode(self.encoding))


class ProxyStdinBuffer:
    """Object representing a proxy/fake binary stdin stream."""

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


class ProxyStdoutBuffer:
    """Object representing a proxy/fake binary stdout stream."""

    def __init__(self, prompt, original, name, isatty=True):
        self._name = name
        self._closed = False
        self._isatty = isatty
        self._prompt = prompt
        self._original_file = original

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
        self._original_file.close()
        self._closed = True
        return

    def detach(self):
        raise io.UnsupportedOperation("Stream does not support detach.")

    def readable(self):
        return False

    def writable(self):
        return True

    def seekable(self):
        return False

    def flush(self):
        self._original_file.flush()

    def isatty(self):
        return self._isatty

    # def fileno(self) -> if we implement it to raise an error, TextIOWrapper(..) fails

    def write(self, bb):
        logger.info(f"stdout buffer write {id(self._original_file)}: {bb}")
        self._prompt.clear()
        self._original_file.write(bb)
        self._original_file.flush()  # because this *can* be stderr
        self._prompt.write_prompt()
        return len(bb)

    def writelines(self, lines):
        logger.info("stdout buffer write lines")
        self._prompt.clear()
        for line in lines:
            self._original_file.write(line)
        self._original_file.flush()
        self._prompt.write_prompt()
