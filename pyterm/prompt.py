import math
import logging
import platform


logger = logging.getLogger("pyterm")


class Prompt:
    """A terminal prompt, with history, status and autocomp."""

    def __init__(self, file_out):
        self._file_out = file_out

        self._pre = "pyterm> "
        self._in1 = ""
        self._in2 = ""

        self._history = HistoryHelper()
        self._status = StatusHelper()
        self._autocomp = AutocompHelper()
        self._autocomp.show([str(i) for i in range(100)])
        # self._autocomp.show(["aap", "noot", "mies", "spam", "eggs"])

        self.write_prompt()

    def _write(self, text):
        self._file_out.buffer.write(
            text.encode(self._file_out.encoding, errors="ignore")
        )

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
            self.clear()
            self.write_prompt()
            self._write("\n")
            self._in1 = ""
            self.write_prompt()
        elif key == "escape":
            print("escape was hit!")
            return
        elif key == "tab":
            import sys

            sys.stderr.write("Tab was hit!\n")
            sys.stderr.flush()
            return
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

        self.clear()
        self.write_prompt()

    def clear(self):
        write = self._write
        # Move to stored state, and clear rest of screen
        write("\x1b8")
        write("\x1b[0J")

        self._file_out.buffer.flush()

    def write_prompt(self):

        write = self._write

        # Save cursor state, right before doing our thing
        write("\x1b7")

        # Start on a new line, because we don't know whether the last written char was a newline.
        # This results in a bit more vertical space, but I quite like that ...
        write("\n")

        # Print stuff that goes below the prompt
        lines_below = []
        lines_below += self._autocomp.get_lines()
        lines_below += self._status.get_lines()

        for line in lines_below:
            write("\n")
            write(line)

        # Move back up
        write(f"\x1b[{len(lines_below)}F")

        # Write prompt
        write("\x1b[1m")  # bold
        write(self._pre)
        write("\x1b[0m")  # reset style

        # Write input left of the cursor
        if self._in1:
            write(self._in1)

        # Write input right of the cursor, and move cursor back
        if self._in2:
            write(self._in2)
            n = len(self._in2)
            write(f"\x1b[{n}D")

        self._file_out.buffer.flush()


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

    def get_lines(self):
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

        lines = []
        for i, index in enumerate(range(index_first, index_last + 1)):
            line = ""
            if i >= scroll_first and i < scroll_first + scroll_n:
                line += "\x1b[0m█ \x1b[0m"
            else:
                line += "\x1b[2m█ \x1b[0m"
            line += "\x1b[2m"
            if index == self._index:
                line += "\x1b[4m"
            line += self._list[index]
            # line += f"  {scroll_first} {len(self._list)} {vspace} {scroll_n}"
            line += "\x1b[0m"
            lines.append(line)

        while len(lines) < self._vspace:
            lines.append("")

        return lines


class StatusHelper:

    def __init__(self):
        self._pyversion = (
            platform.python_implementation() + " " + platform.python_version()
        )

    @property
    def active(self):
        return True

    def get_lines(self):
        loop_info = "some-loop"
        runner = "o"
        line = ""
        line += "\x1b[0;37;44m"
        line += f" {runner} PyTerm with {self._pyversion} on {loop_info:<10}".ljust(80)
        line += "\x1b[0m"
        return [line]
