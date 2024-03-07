import sys


class Prompt:
    """ A terminal prompt.
    """

    def __init__(self):
        self._pre = "pyterm> "
        self._in1 = ""
        self._in2 = ""

        self._history = []
        self._history_index = None
        self._in2_alt = ""

        self._write_prompt()


    def on_key(self, key):

        if key not in ["up", "down"]:
            self._history_index = None
            if self._in2_alt:
                self._in2 = self._in2_alt
                self._in2_alt = ""

        if len(key) == 1:
            # A regular character
            self._in1 += key
        elif key == "backspace":
            if self._in1:
                self._in1 = self._in1[:-1]
        elif key == "enter":
            command = self._in1 + self._in2
            if command:
                if command in self._history:
                    self._history.remove(command)
                self._history.append(command)
                if len(self._history) > 11:
                    self._history[10:] = []
                self._in1 = self._in2 = ""
        elif key == "left":
            if self._in1:
                self._in2 = self._in1[-1] + self._in2
                self._in1 = self._in1[:-1]
        elif key == "right":
            if self._in2:
                self._in1 += self._in2[0]
                self._in2 = self._in2[1:]
        elif key == "up":
            self._search_history(-1)
        elif key == "down":
            self._search_history(+1)
        else:
            pass  # ignore
        self._write_prompt()

    def _search_history(self, step):
        # Prep
        # i being len(self._history), i.e. out of scope means clear, i.e. start point
        i = self._history_index
        if i is None:
            i = len(self._history)
        i = min(i + step, len(self._history))
        if i < 0:
            i = len(self._history)
        # Perform a search
        needle = self._in1
        foundit = False
        while 0 <= i < len(self._history):
            if self._history[i].startswith(needle):
                foundit = True
                break
            i += step
        # Process result.
        if foundit:
            self._history_index = i
            command = self._history[i]
            self._in2_alt = command[len(self._in1):]
        else:
            self._history_index = None
            self._in2_alt = ""
            return

    def _write_prompt(self):
        write = sys.stdout.write

        write("\r")
        write("\x1b[0K")

        write("\x1b[1m")  # bold
        write(self._pre)
        write("\x1b[0m")  # reset style
        write(self._in1)

        if self._in2_alt:
            write("\x1b[2m")  # faint
            write(self._in2_alt)
            write("\x1b[0m")  # reset style
            n =  - len(self._in2_alt)
        else:
            write(self._in2)
            n =  - len(self._in2)

        if n > 0:
            write(f"\x1b[{n}C")
        elif n < 0:
            write(f"\x1b[{-n}D")

        sys.stdout.flush()

    def _write(self, s):
        sys.std.flush()


p = Prompt()
##
p._history = ["foo", "fie", "bar"]
p._history_index = -1

p._in1 = "f"

p._search_history(-1)

print(p._in2)
