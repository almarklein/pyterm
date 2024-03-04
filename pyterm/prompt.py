import sys



class Prompt:

    def __init__(self):
        self._pre = "pyterm> "
        self._in1 = ""
        self._in2 = ""

        self._write_prompt()

    def on_key(self, key):

        if len(key) == 1:
            # A regular character
            self._in1 += key
        elif key == "backspace":
            if self._in1:
                self._in1 = self._in1[:-1]
        elif key == "left":
            if self._in1:
                self._in2 = self._in1[-1] + self._in2
                self._in1 = self._in1[:-1]
        elif key == "right":
            if self._in2:
                self._in1 += self._in2[0]
                self._in2 = self._in2[1:]
        else:
            pass  # ignore
        self._write_prompt()

    def _write_prompt(self):
        write = sys.stdout.write

        write("\r")
        write("\x1b[0K")

        write("\x1b[1m")  # bold
        write(self._pre)
        write("\x1b[0m")  # reset style
        write(self._in1)
        write(self._in2)

        n =  - len(self._in2)
        if n > 0:
            write(f"\x1b[{n}C")
        elif n < 0:
            write(f"\x1b[{-n}D")

        sys.stdout.flush()

    def _write(self, s):
        sys.std.flush()


