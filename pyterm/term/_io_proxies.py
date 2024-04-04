import io
import sys
import logging
import threading


logger = logging.getLogger("pyterm")


class ProxyStdin(io.TextIOWrapper):
    """Object representing a proxy/fake text stdin stream."""

    def __init__(self, lines_queue, name):
        super().__init__(ProxyStdinBuffer(lines_queue, name))

    def readline(self, size=-1):
        return self.buffer.readline(size).decode()


class ProxyStdout(io.TextIOWrapper):
    """Object representing a proxy/fake text stdout stream."""

    def __init__(self, original_file, name, prompt=None):
        super().__init__(
            ProxyStdoutBuffer(original_file.buffer, name, prompt),
            encoding=original_file.encoding,
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

    def __init__(self, original_file, name, prompt=None, isatty=True):
        self._name = name
        self._closed = False
        self._isatty = isatty
        self._original_file = original_file

        self._prompt = StubPrompt(original_file) if prompt is None else prompt
        assert hasattr(self._prompt, "file")
        assert hasattr(self._prompt, "lock")
        assert hasattr(self._prompt, "clear")
        assert hasattr(self._prompt, "write_prompt")

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
        with self._prompt.lock:
            self._prompt.clear()
            result = self._original_file.write(bb)
            if self._prompt.file is not self._original_file:
                self._original_file.flush()
            self._prompt.write_prompt()
            return result

    def writelines(self, lines):
        logger.info("stdout buffer write lines")
        with self._prompt.lock:
            self._prompt.clear()
            for line in lines:
                self._original_file.write(line)
            if self._prompt.file is not self._original_file:
                self._original_file.flush()
            self._prompt.write_prompt()


class StubPrompt:
    """Dummy prompt

    Used when no promot is given. Also kinda serves as dev-docs on what a prompt needs to work with the ProxyStdout.
    """

    def __init__(self, file):
        self.file = file
        self.lock = threading.RLock()

    def clear(self):
        pass

    def write_prompt(self):
        pass
