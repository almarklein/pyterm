import sys
import math


class Prompt:
    """A terminal prompt."""

    def __init__(self):
        self._pre = "pyterm> "
        self._in1 = ""
        self._in2 = ""

        self._history = HistoryHelper()

        import builtins

        self._autocomp = AutocompHelper()
        self._autocomp.show(dir(builtins))
        # self._autocomp.show([str(i) for i in range(100)])
        # self._autocomp.show(["aap", "noot", "mies", "spam", "eggs"])

        self._write_prompt()

    def on_key(self, key):

        # Reset helpers, apply if necessary
        if key not in ["up", "down"]:
            self._history.reset()

        if len(key) == 1:
            # A regular character
            self._in1 += key
        elif key == "backspace":
            if self._in1:
                self._in1 = self._in1[:-1]
        elif key == "enter":
            command = self._in1 + self._in2
            self._history.add(command)
            self._history.reset()
            self._in1 = command
            self._in2 = ""
            self._write_prompt()
            sys.stdout.write("\n")
            self._in1 = ""
        elif key == "escape":
            pass
        elif key == "left":
            if self._in1:
                self._in2 = self._in1[-1] + self._in2
                self._in1 = self._in1[:-1]
        elif key == "right":
            if self._in2:
                self._in1 += self._in2[0]
                self._in2 = self._in2[1:]
        elif key == "up":
            if self._autocomp.active:
                self._autocomp.up()
            else:
                if not self._history.active:
                    self._history.activate(self._in1, self._in2)
                    self._in2 = ""
                if self._history.active:
                    self._in1 = self._history.up()
        elif key == "down":
            if self._autocomp.active:
                self._autocomp.down()
            elif self._history.active:
                self._in1 = self._history.down()
        else:
            pass  # ignore
        self._write_prompt()

    def _write_prompt(self):
        write = sys.stdout.write

        # Move to beginning, and clear rest of screen
        write("\r")
        write("\x1b[0J")

        # Make space below
        nlines = 7
        write("\n" * nlines)
        write(f"\x1b[{nlines}A")

        # Write prompt
        write("\x1b[1m")  # bold
        write(self._pre)
        write("\x1b[0m")  # reset style

        # Write input left of the cursor
        write(self._in1)

        # Write input right of the cursor
        write(self._in2)

        # Save cursor pos
        n = -len(self._in2)
        if n > 0:
            write(f"\x1b[{n}C")
        elif n < 0:
            write(f"\x1b[{-n}D")
        write("\x1b7")

        # Autocomp
        self._autocomp.write(sys.stdout)

        # Restore cursor to saved state
        write("\x1b8")

        sys.stdout.flush()

    def _write(self, s):
        sys.std.flush()


class HistoryHelper:

    def __init__(self):
        self._list = []
        self.reset()

    def reset(self):
        self._index = None
        self._in1 = None  # search prefix
        self._in2 = None  # original suffix

    def activate(self, in1, in2):
        self._in1 = in1
        self._in2 = in2

    @property
    def active(self):
        return self._in1 is not None

    def up(self):
        return self._search(-1)

    def down(self):
        return self._search(+1)

    def add(self, command):
        if command:
            if command in self._list:
                self._list.remove(command)
            self._list.append(command)
            if len(self._list) > 110:
                self._list[:-100] = []

    def _search(self, step):
        needle = self._in1
        # Prep
        # i being len(self._list), i.e. out of scope means clear, i.e. start point
        i = self._index
        if i is None:
            i = len(self._list)
        i = min(i + step, len(self._list))
        if i < 0:
            i = len(self._list)
        # Perform a search
        foundit = False
        while 0 <= i < len(self._list):
            if self._list[i].startswith(needle):
                foundit = True
                break
            i += step
        # Process result.
        if foundit:
            self._index = i
            return self._list[i]
        else:
            self._index = None
            return self._in1 + self._in2


class AutocompHelper:
    def __init__(self):
        self._vspace = 7
        self._list = []
        self._index = None
        self._history = []

    def reset(self):
        self._index = None

    def activate(self, in1, in2):
        pass

    @property
    def active(self):
        return True

    def up(self):
        index = (self._index or 0) - 1
        if index < 0:
            index = len(self._list) - 1
        self._index = index

    def down(self):
        index = (self._index or 0) + 1
        if index >= len(self._list):
            index = 0
        self._index = index

    def show(self, names):
        self._list = [str(x) for x in names]

    def write(self, file):
        write = file.write
        ref_index = self._index or 0

        # How much space do we have / need
        vspace = min(self._vspace, len(self._list))
        nbefore = vspace // 2
        nafter = vspace - nbefore - 1

        # Calculate start & end index
        index_first = ref_index - nbefore
        index_last = ref_index + nafter
        highest_index_first = len(self._list) - vspace
        if index_first < 0:
            index_first = 0
            index_last = vspace - 1
        elif index_last >= len(self._list):
            index_last = len(self._list) - 1
            index_first = index_last - vspace + 1

        # Determine scroll params
        scroll_size = len(self._list) / vspace
        scroll_n = max(1, int(vspace / scroll_size))
        if index_first == 0:
            scroll_first = 0
        elif index_first == highest_index_first:
            scroll_first = vspace - scroll_n
        else:
            scroll_first = math.ceil(
                (vspace - scroll_n - 1) * (index_first) / (highest_index_first)
            )

        for i, index in enumerate(range(index_first, index_last + 1)):

            write("\x1b[1E")  # move to beginning of next line
            if i >= scroll_first and i < scroll_first + scroll_n:
                write("\x1b[0m█ \x1b[0m")
            else:
                write("\x1b[2m█ \x1b[0m")
            write("\x1b[2m")
            if index == self._index:
                write("\x1b[4m")
            write(self._list[index])
            # write(f"  {scroll_first} {len(self._list)} {vspace} {scroll_n}")
            write("\x1b[0m")
