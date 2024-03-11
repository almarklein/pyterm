from collections import deque

# %% Decoder


class EscapeCodeDecoder:
    """A streaming ASCII input key decoder."""

    def __init__(self):

        # We remove the double-escape, because it captures cases where
        # an escape is followed by another escape code, causing the
        # remainder of that escape code to be interpreted as characters.
        # At the end of decode() we dedupe.
        map = KEY_MAP.copy()
        map.pop("\x1b\x1b")
        self._key_tree = build_tree(map)
        self._branch = self._key_tree
        self._chars = deque()

    def decode(self, text, flush=False):
        """Decode the given string.

        Escape codes can be split between multiple calls to decode.
        When flush is True, this is not the case, and any partial escape
        code is ignored. But without a flush, a lonely escape char will
        not be decoded until new chars are decoded.
        """

        self._chars.extend(text)
        result = []

        while True:

            # Get a char
            try:
                c = self._chars.popleft()
            except IndexError:
                break  # empty

            if c in self._branch:
                # Walk the tree, can be result or new branch
                tree_result = self._branch[c]
                if isinstance(tree_result, dict):
                    self._branch = tree_result
                else:  # == isinstance(tree_result, tuple):
                    self._branch = self._key_tree
                    result.extend(tree_result)
            elif self._branch is self._key_tree:
                # A normal character
                result.append(c)
            else:
                # We were traversing the tree, perhaps it still resolves to a value?
                if "" in self._branch:
                    result.extend(self._branch[""])
                else:
                    pass  # Ignore an incomplete escape
                # Reset tree and put character back for next iter.
                self._branch = self._key_tree
                self._chars.appendleft(c)

        # Flush the tree
        if flush and self._branch is not self._key_tree:
            if "" in self._branch:
                result.extend(self._branch[""])
            self._branch = self._key_tree

        # Consolidate double-escapes
        to_pop = []
        may_be_double_esc = False
        for i in range(len(result)):
            is_esc = result[i] == "escape"
            if is_esc and may_be_double_esc:
                to_pop.append(i)
                may_be_double_esc = False
            else:
                may_be_double_esc = is_esc
        for i in reversed(to_pop):
            result.pop(i)

        return result


def build_tree(map):
    """Build a tree from a flat map, so it can be traversed while decoding incoming chars."""
    trunk = {}
    for text, keys in map.items():
        branch = trunk
        while len(text) > 1:
            char, text = text[0], text[1:]
            new_branch = branch.setdefault(char, {})
            if not isinstance(new_branch, dict):
                branch[char] = new_branch = {"": new_branch}
            branch = new_branch
        branch[text] = keys
    assert "" not in trunk  # Sanity check
    return trunk


# %% A flat mapping of vt100 escape codes to keys

# This code is taken withs gratitude from the Textual project. A
# very similar map in in the prompt_toolkit codebase. We closely follow
# the Textual version, except we replaced its key enum with plain
# strings. On the bottom of this file there is some code that tests the below
# map with the version from Textual.

KEY_MAP = {
    # Control keys.
    " ": (" ",),  # using ' ' instead of Textual's 'space'
    "\r": ("enter",),
    "\x00": ("ctrl+@",),  # Control-At (Also for Ctrl-Space)
    "\x01": ("ctrl+a",),  # Control-A (home)
    "\x02": ("ctrl+b",),  # Control-B (emacs cursor left)
    "\x03": ("ctrl+c",),  # Control-C (interrupt)
    "\x04": ("ctrl+d",),  # Control-D (exit)
    "\x05": ("ctrl+e",),  # Control-E (end)
    "\x06": ("ctrl+f",),  # Control-F (cursor forward)
    "\x07": ("ctrl+g",),  # Control-G
    "\x08": ("backspace",),  # Control-H (8) (Identical to '\b')
    "\x09": ("tab",),  # Control-I (9) (Identical to '\t')
    "\x0a": ("ctrl+j",),  # Control-J (10) (Identical to '\n')
    "\x0b": ("ctrl+k",),  # Control-K (delete until end of line; vertical tab)
    "\x0c": ("ctrl+l",),  # Control-L (clear; form feed)
    # "\x0d": ("ctrl+m",),  # Control-M (13) (Identical to '\r')
    "\x0e": ("ctrl+n",),  # Control-N (14) (history forward)
    "\x0f": ("ctrl+o",),  # Control-O (15)
    "\x10": ("ctrl+p",),  # Control-P (16) (history back)
    "\x11": ("ctrl+q",),  # Control-Q
    "\x12": ("ctrl+r",),  # Control-R (18) (reverse search)
    "\x13": ("ctrl+s",),  # Control-S (19) (forward search)
    "\x14": ("ctrl+t",),  # Control-T
    "\x15": ("ctrl+u",),  # Control-U
    "\x16": ("ctrl+v",),  # Control-V
    "\x17": ("ctrl+w",),  # Control-W
    "\x18": ("ctrl+x",),  # Control-X
    "\x19": ("ctrl+y",),  # Control-Y (25)
    "\x1a": ("ctrl+z",),  # Control-Z
    "\x1b": ("escape",),  # Also Control-[
    # Windows issues esc esc for a single press of escape key
    "\x1b\x1b": ("escape",),
    "\x9b": ("shift+escape",),
    "\x1c": ("ctrl+backslash",),  # Both Control-\ (also Ctrl-| )
    "\x1d": ("ctrl+right_square_bracket",),  # Control-]
    "\x1e": ("ctrl+circumflex_accent",),  # Control-^
    "\x1f": ("ctrl+underscore",),  # Control-underscore (Also for Ctrl-hyphen.)
    # ASCII Delete (0x7f)
    # Vt220 (and Linux terminal) send this when pressing backspace. We map this
    # to ControlH, because that will make it easier to create key bindings that
    # work everywhere, with the trade-off that it's no longer possible to
    # handle backspace and control-h individually for the few terminals that
    # support it. (Most terminals send ControlH when backspace is pressed.)
    # See: http://www.ibb.net/~anne/keyboard.html
    "\x7f": ("backspace",),
    "\x1b\x7f": ("ctrl+w",),
    # Various
    "\x1b[1~": ("home",),  # tmux
    "\x1b[2~": ("insert",),
    "\x1b[3~": ("delete",),
    "\x1b[4~": ("end",),  # tmux
    "\x1b[5~": ("pageup",),
    "\x1b[6~": ("pagedown",),
    "\x1b[7~": ("home",),  # xrvt
    "\x1b[8~": ("end",),  # xrvt
    "\x1b[Z": ("shift+tab",),  # shift + tab
    "\x1b\x09": ("shift+tab",),  # Linux console
    "\x1b[~": ("shift+tab",),  # Windows console
    # --
    # Function keys.
    "\x1bOP": ("f1",),
    "\x1bOQ": ("f2",),
    "\x1bOR": ("f3",),
    "\x1bOS": ("f4",),
    "\x1b[[A": ("f1",),  # Linux console.
    "\x1b[[B": ("f2",),  # Linux console.
    "\x1b[[C": ("f3",),  # Linux console.
    "\x1b[[D": ("f4",),  # Linux console.
    "\x1b[[E": ("f5",),  # Linux console.
    "\x1b[11~": ("f1",),  # rxvt-unicode
    "\x1b[12~": ("f2",),  # rxvt-unicode
    "\x1b[13~": ("f3",),  # rxvt-unicode
    "\x1b[14~": ("f4",),  # rxvt-unicode
    "\x1b[15~": ("f5",),
    "\x1b[17~": ("f6",),
    "\x1b[18~": ("f7",),
    "\x1b[19~": ("f8",),
    "\x1b[20~": ("f9",),
    "\x1b[21~": ("f10",),
    "\x1b[23~": ("f11",),
    "\x1b[24~": ("f12",),
    "\x1b[25~": ("f13",),
    "\x1b[26~": ("f14",),
    "\x1b[28~": ("f15",),
    "\x1b[29~": ("f16",),
    "\x1b[31~": ("f17",),
    "\x1b[32~": ("f18",),
    "\x1b[33~": ("f19",),
    "\x1b[34~": ("f20",),
    # Xterm
    "\x1b[1;2P": ("f13",),
    "\x1b[1;2Q": ("f14",),
    "\x1b[1;2R": (
        "f15",
    ),  # Conflicts with CPR response; enabled after https://github.com/Textualize/textual/issues/3440.
    "\x1b[1;2S": ("f16",),
    "\x1b[15;2~": ("f17",),
    "\x1b[17;2~": ("f18",),
    "\x1b[18;2~": ("f19",),
    "\x1b[19;2~": ("f20",),
    "\x1b[20;2~": ("f21",),
    "\x1b[21;2~": ("f22",),
    "\x1b[23;2~": ("f23",),
    "\x1b[24;2~": ("f24",),
    "\x1b[23$": ("f23",),  # rxvt
    "\x1b[24$": ("f24",),  # rxvt
    # CSI 27 disambiguated modified "other" keys (xterm)
    # Ref: https://invisible-island.net/xterm/modified-keys.html
    # These are currently unsupported, so just re-map some common ones to the
    # unmodified versions
    "\x1b[27;2;13~": ("ctrl+m",),  # Shift + Enter
    "\x1b[27;5;13~": ("ctrl+m",),  # Ctrl + Enter
    "\x1b[27;6;13~": ("ctrl+m",),  # Ctrl + Shift + Enter
    # --
    # Control + function keys.
    "\x1b[1;5P": ("ctrl+f1",),
    "\x1b[1;5Q": ("ctrl+f2",),
    "\x1b[1;5R": (
        "ctrl+f3",
    ),  # Conflicts with CPR response; enabled after https://github.com/Textualize/textual/issues/3440.
    "\x1b[1;5S": ("ctrl+f4",),
    "\x1b[15;5~": ("ctrl+f5",),
    "\x1b[17;5~": ("ctrl+f6",),
    "\x1b[18;5~": ("ctrl+f7",),
    "\x1b[19;5~": ("ctrl+f8",),
    "\x1b[20;5~": ("ctrl+f9",),
    "\x1b[21;5~": ("ctrl+f10",),
    "\x1b[23;5~": ("ctrl+f11",),
    "\x1b[24;5~": ("ctrl+f12",),
    "\x1b[1;6P": ("ctrl+f13",),
    "\x1b[1;6Q": ("ctrl+f14",),
    "\x1b[1;6R": (
        "ctrl+f15",
    ),  # Conflicts with CPR response; enabled after https://github.com/Textualize/textual/issues/3440.
    "\x1b[1;6S": ("ctrl+f16",),
    "\x1b[15;6~": ("ctrl+f17",),
    "\x1b[17;6~": ("ctrl+f18",),
    "\x1b[18;6~": ("ctrl+f19",),
    "\x1b[19;6~": ("ctrl+f20",),
    "\x1b[20;6~": ("ctrl+f21",),
    "\x1b[21;6~": ("ctrl+f22",),
    "\x1b[23;6~": ("ctrl+f23",),
    "\x1b[24;6~": ("ctrl+f24",),
    # rxvt-unicode control function keys:
    "\x1b[11^": ("ctrl+f1",),
    "\x1b[12^": ("ctrl+f2",),
    "\x1b[13^": ("ctrl+f3",),
    "\x1b[14^": ("ctrl+f4",),
    "\x1b[15^": ("ctrl+f5",),
    "\x1b[17^": ("ctrl+f6",),
    "\x1b[18^": ("ctrl+f7",),
    "\x1b[19^": ("ctrl+f8",),
    "\x1b[20^": ("ctrl+f9",),
    "\x1b[21^": ("ctrl+f10",),
    "\x1b[23^": ("ctrl+f11",),
    "\x1b[24^": ("ctrl+f12",),
    # rxvt-unicode control+shift function keys:
    "\x1b[25^": ("ctrl+f13",),
    "\x1b[26^": ("ctrl+f14",),
    "\x1b[28^": ("ctrl+f15",),
    "\x1b[29^": ("ctrl+f16",),
    "\x1b[31^": ("ctrl+f17",),
    "\x1b[32^": ("ctrl+f18",),
    "\x1b[33^": ("ctrl+f19",),
    "\x1b[34^": ("ctrl+f20",),
    "\x1b[23@": ("ctrl+f21",),
    "\x1b[24@": ("ctrl+f22",),
    # --
    # Tmux (Win32 subsystem) sends the following scroll events.
    "\x1b[62~": ("<scroll-up>",),
    "\x1b[63~": ("<scroll-down>",),
    # Meta/control/escape + pageup/pagedown/insert/delete.
    "\x1b[3;2~": ("shift+delete",),  # xterm, gnome-terminal.
    "\x1b[3$": ("shift+delete",),  # rxvt
    "\x1b[5;2~": ("shift+pageup",),
    "\x1b[6;2~": ("shift+pagedown",),
    "\x1b[2;3~": ("escape", "insert"),
    "\x1b[3;3~": ("escape", "delete"),
    "\x1b[5;3~": ("escape", "pageup"),
    "\x1b[6;3~": ("escape", "pagedown"),
    "\x1b[2;4~": ("escape", "shift+insert"),
    "\x1b[3;4~": ("escape", "shift+delete"),
    "\x1b[5;4~": ("escape", "shift+pageup"),
    "\x1b[6;4~": ("escape", "shift+pagedown"),
    "\x1b[3;5~": ("ctrl+delete",),  # xterm, gnome-terminal.
    "\x1b[3^": ("ctrl+delete",),  # rxvt
    "\x1b[5;5~": ("ctrl+pageup",),
    "\x1b[6;5~": ("ctrl+pagedown",),
    "\x1b[5^": ("ctrl+pageup",),  # rxvt
    "\x1b[6^": ("ctrl+pagedown",),  # rxvt
    "\x1b[3;6~": ("ctrl+shift+delete",),
    "\x1b[5;6~": ("ctrl+shift+pageup",),
    "\x1b[6;6~": ("ctrl+shift+pagedown",),
    "\x1b[2;7~": ("escape", "ctrl+insert"),
    "\x1b[5;7~": ("escape", "ctrl+pagedown"),
    "\x1b[6;7~": ("escape", "ctrl+pagedown"),
    "\x1b[2;8~": ("escape", "ctrl+shift+insert"),
    "\x1b[5;8~": ("escape", "ctrl+shift+pagedown"),
    "\x1b[6;8~": ("escape", "ctrl+shift+pagedown"),
    # --
    # Arrows.
    # (Normal cursor mode).
    "\x1b[A": ("up",),
    "\x1b[B": ("down",),
    "\x1b[C": ("right",),
    "\x1b[D": ("left",),
    "\x1b[H": ("home",),
    "\x1b[F": ("end",),
    # Tmux sends following keystrokes when control+arrow is pressed, but for
    # Emacs ansi-term sends the same sequences for normal arrow keys. Consider
    # it a normal arrow press, because that's more important.
    # (Application cursor mode).
    "\x1bOA": ("up",),
    "\x1bOB": ("down",),
    "\x1bOC": ("right",),
    "\x1bOD": ("left",),
    "\x1bOF": ("end",),
    "\x1bOH": ("home",),
    # Shift + arrows.
    "\x1b[1;2A": ("shift+up",),
    "\x1b[1;2B": ("shift+down",),
    "\x1b[1;2C": ("shift+right",),
    "\x1b[1;2D": ("shift+left",),
    "\x1b[1;2F": ("shift+end",),
    "\x1b[1;2H": ("shift+home",),
    # Shift+navigation in rxvt
    "\x1b[a": ("shift+up",),
    "\x1b[b": ("shift+down",),
    "\x1b[c": ("shift+right",),
    "\x1b[d": ("shift+left",),
    "\x1b[7$": ("shift+home",),
    "\x1b[8$": ("shift+end",),
    # Meta + arrow keys. Several terminals handle this differently.
    # The following sequences are for xterm and gnome-terminal.
    #     (Iterm sends ESC followed by the normal arrow_up/down/left/right
    #     sequences, and the OSX Terminal sends ESCb and ESCf for "alt
    #     arrow_left" and "alt arrow_right." We don't handle these
    #     explicitly, in here, because would could not distinguish between
    #     pressing ESC (to go to Vi navigation mode), followed by just the
    #     'b' or 'f' key. These combinations are handled in
    #     the input processor.)
    "\x1b[1;3A": ("escape", "up"),
    "\x1b[1;3B": ("escape", "down"),
    "\x1b[1;3C": ("escape", "right"),
    "\x1b[1;3D": ("escape", "left"),
    "\x1b[1;3F": ("escape", "end"),
    "\x1b[1;3H": ("escape", "home"),
    # Alt+shift+number.
    "\x1b[1;4A": ("escape", "shift+up"),
    "\x1b[1;4B": ("escape", "shift+down"),
    "\x1b[1;4C": ("escape", "shift+right"),
    "\x1b[1;4D": ("escape", "shift+left"),
    "\x1b[1;4F": ("escape", "shift+end"),
    "\x1b[1;4H": ("escape", "shift+home"),
    # Control + arrows.
    "\x1b[1;5A": ("ctrl+up",),  # Cursor Mode
    "\x1b[1;5B": ("ctrl+down",),  # Cursor Mode
    "\x1b[1;5C": ("ctrl+right",),  # Cursor Mode
    "\x1b[1;5D": ("ctrl+left",),  # Cursor Mode
    "\x1bf": ("ctrl+right",),  # iTerm natural editing keys
    "\x1bb": ("ctrl+left",),  # iTerm natural editing keys
    "\x1b[1;5F": ("ctrl+end",),
    "\x1b[1;5H": ("ctrl+home",),
    # rxvt
    "\x1b[7^": ("ctrl+end",),
    "\x1b[8^": ("ctrl+home",),
    # Tmux sends following keystrokes when control+arrow is pressed, but for
    # Emacs ansi-term sends the same sequences for normal arrow keys. Consider
    # it a normal arrow press, because that's more important.
    "\x1b[5A": ("ctrl+up",),
    "\x1b[5B": ("ctrl+down",),
    "\x1b[5C": ("ctrl+right",),
    "\x1b[5D": ("ctrl+left",),
    # Control arrow keys in rxvt
    "\x1bOa": ("ctrl+up",),
    "\x1bOb": ("ctrl+up",),
    "\x1bOc": ("ctrl+right",),
    "\x1bOd": ("ctrl+left",),
    # Control + shift + arrows.
    "\x1b[1;6A": ("ctrl+shift+up",),
    "\x1b[1;6B": ("ctrl+shift+down",),
    "\x1b[1;6C": ("ctrl+shift+right",),
    "\x1b[1;6D": ("ctrl+shift+left",),
    "\x1b[1;6F": ("ctrl+shift+end",),
    "\x1b[1;6H": ("ctrl+shift+home",),
    # Control + Meta + arrows.
    "\x1b[1;7A": ("escape", "ctrl+up"),
    "\x1b[1;7B": ("escape", "ctrl+down"),
    "\x1b[1;7C": ("escape", "ctrl+right"),
    "\x1b[1;7D": ("escape", "ctrl+left"),
    "\x1b[1;7F": ("escape", "ctrl+end"),
    "\x1b[1;7H": ("escape", "ctrl+home"),
    # Meta + Shift + arrows.
    "\x1b[1;8A": ("escape", "ctrl+shift+up"),
    "\x1b[1;8B": ("escape", "ctrl+shift+down"),
    "\x1b[1;8C": ("escape", "ctrl+shift+right"),
    "\x1b[1;8D": ("escape", "ctrl+shift+left"),
    "\x1b[1;8F": ("escape", "ctrl+shift+end"),
    "\x1b[1;8H": ("escape", "ctrl+shift+home"),
    # Meta + arrow on (some?) Macs when using iTerm defaults (see issue #483).
    "\x1b[1;9A": ("escape", "up"),
    "\x1b[1;9B": ("escape", "down"),
    "\x1b[1;9C": ("escape", "right"),
    "\x1b[1;9D": ("escape", "left"),
    # --
    # Control/shift/meta + number in mintty.
    # (c-2 will actually send c-@ and c-6 will send c-^.)
    "\x1b[1;5p": ("ctrl+0",),
    "\x1b[1;5q": ("ctrl+1",),
    "\x1b[1;5r": ("ctrl+2",),
    "\x1b[1;5s": ("ctrl+3",),
    "\x1b[1;5t": ("ctrl+4",),
    "\x1b[1;5u": ("ctrl+5",),
    "\x1b[1;5v": ("ctrl+6",),
    "\x1b[1;5w": ("ctrl+7",),
    "\x1b[1;5x": ("ctrl+8",),
    "\x1b[1;5y": ("ctrl+9",),
    "\x1b[1;6p": ("ctrl+shift+0",),
    "\x1b[1;6q": ("ctrl+shift+1",),
    "\x1b[1;6r": ("ctrl+shift+2",),
    "\x1b[1;6s": ("ctrl+shift+3",),
    "\x1b[1;6t": ("ctrl+shift+4",),
    "\x1b[1;6u": ("ctrl+shift+5",),
    "\x1b[1;6v": ("ctrl+shift+6",),
    "\x1b[1;6w": ("ctrl+shift+7",),
    "\x1b[1;6x": ("ctrl+shift+8",),
    "\x1b[1;6y": ("ctrl+shift+9",),
    "\x1b[1;7p": ("escape", "ctrl+0"),
    "\x1b[1;7q": ("escape", "ctrl+1"),
    "\x1b[1;7r": ("escape", "ctrl+2"),
    "\x1b[1;7s": ("escape", "ctrl+3"),
    "\x1b[1;7t": ("escape", "ctrl+4"),
    "\x1b[1;7u": ("escape", "ctrl+5"),
    "\x1b[1;7v": ("escape", "ctrl+6"),
    "\x1b[1;7w": ("escape", "ctrl+7"),
    "\x1b[1;7x": ("escape", "ctrl+8"),
    "\x1b[1;7y": ("escape", "ctrl+9"),
    "\x1b[1;8p": ("escape", "ctrl+shift+0"),
    "\x1b[1;8q": ("escape", "ctrl+shift+1"),
    "\x1b[1;8r": ("escape", "ctrl+shift+2"),
    "\x1b[1;8s": ("escape", "ctrl+shift+3"),
    "\x1b[1;8t": ("escape", "ctrl+shift+4"),
    "\x1b[1;8u": ("escape", "ctrl+shift+5"),
    "\x1b[1;8v": ("escape", "ctrl+shift+6"),
    "\x1b[1;8w": ("escape", "ctrl+shift+7"),
    "\x1b[1;8x": ("escape", "ctrl+shift+8"),
    "\x1b[1;8y": ("escape", "ctrl+shift+9"),
    # Simplify some sequences that appear to be unique to rxvt; see
    # https://github.com/Textualize/textual/issues/3741 for context.
    "\x1bOj": ("*",),
    "\x1bOk": ("+",),
    "\x1bOm": ("-",),
    "\x1bOn": (".",),
    "\x1bOo": ("/",),
    "\x1bOp": ("0",),
    "\x1bOq": ("1",),
    "\x1bOr": ("2",),
    "\x1bOs": ("3",),
    "\x1bOt": ("4",),
    "\x1bOu": ("5",),
    "\x1bOv": ("6",),
    "\x1bOw": ("7",),
    "\x1bOx": ("8",),
    "\x1bOy": ("9",),
    "\x1bOM": ("enter",),
    # WezTerm on macOS emits sequences for Opt and keys on the top numeric
    # row; whereas other terminals provide various characters. The following
    # swallow up those sequences and turns them into characters the same as
    # the other terminals.
    "\x1b§": ("§",),
    "\x1b1": ("¡",),
    "\x1b2": ("™",),
    "\x1b3": ("£",),
    "\x1b4": ("¢",),
    "\x1b5": ("∞",),
    "\x1b6": ("§",),
    "\x1b7": ("¶",),
    "\x1b8": ("•",),
    "\x1b9": ("ª",),
    "\x1b0": ("º",),
    "\x1b-": ("–",),
    "\x1b=": ("≠",),
    # Ctrl+§ on kitty is different from most other terminals on macOS.
    "\x1b[167;5u": ("0",),
    ############################################################################
    # The ignore section. Only add sequences here if they are going to be
    # ignored. Also, when adding a sequence here, please include a note as
    # to why it is being ignored; ideally citing sources if possible.
    ############################################################################
    # The following 2 are inherited from prompt toolkit. They relate to a
    # press of 5 on the numeric keypad, when *not* in number mode.
    "\x1b[E": (),  # Xterm.
    "\x1b[G": (),  # Linux console.
    # Various ctrl+cmd+ keys under Kitty on macOS.
    "\x1b[3;13~": (),  # ctrl-cmd-del
    "\x1b[1;13H": (),  # ctrl-cmd-home
    "\x1b[1;13F": (),  # ctrl-cmd-end
    "\x1b[5;13~": (),  # ctrl-cmd-pgup
    "\x1b[6;13~": (),  # ctrl-cmd-pgdn
    "\x1b[49;13u": (),  # ctrl-cmd-1
    "\x1b[50;13u": (),  # ctrl-cmd-2
    "\x1b[51;13u": (),  # ctrl-cmd-3
    "\x1b[52;13u": (),  # ctrl-cmd-4
    "\x1b[53;13u": (),  # ctrl-cmd-5
    "\x1b[54;13u": (),  # ctrl-cmd-6
    "\x1b[55;13u": (),  # ctrl-cmd-7
    "\x1b[56;13u": (),  # ctrl-cmd-8
    "\x1b[57;13u": (),  # ctrl-cmd-9
    "\x1b[48;13u": (),  # ctrl-cmd-0
    "\x1b[45;13u": (),  # ctrl-cmd--
    "\x1b[61;13u": (),  # ctrl-cmd-+
    "\x1b[91;13u": (),  # ctrl-cmd-[
    "\x1b[93;13u": (),  # ctrl-cmd-]
    "\x1b[92;13u": (),  # ctrl-cmd-\
    "\x1b[39;13u": (),  # ctrl-cmd-'
    "\x1b[59;13u": (),  # ctrl-cmd-;
    "\x1b[47;13u": (),  # ctrl-cmd-/
    "\x1b[46;13u": (),  # ctrl-cmd-.
}


# https://gist.github.com/christianparpart/d8a62cc1ab659194337d73e399004036
SYNC_START = "\x1b[?2026h"
SYNC_END = "\x1b[?2026l"

BRACKETED_PASTE_START = "\x1b[200~"


# %% Some internal tools so we can keep up if textual / pt add new codes


def compare_with_textual():
    from textual._ansi_sequences import (
        ANSI_SEQUENCES_KEYS as textual_map,
        IGNORE_SEQUENCE as textual_ignore,
    )

    pyterm_map = KEY_MAP
    pyterm_keys = set(pyterm_map)
    textual_keys = set(textual_map)

    print("== Comparing with Textual")
    print("missing keys:", textual_keys - pyterm_keys)
    print("extra keys:", pyterm_keys - textual_keys)

    different_count = 0
    for key in pyterm_keys & textual_keys:
        v1, v2 = pyterm_map[key], textual_map[key]
        v2 = () if v2 is textual_ignore else v2
        v2 = (v2,) if isinstance(v2, str) else v2
        v2 = tuple(x.value if hasattr(x, "value") else x for x in v2)
        if v1 != v2:
            different_count += 1
            print("different key:", repr(key), v1, v2)

    if not different_count:
        print("all keys are equal")


def compare_with_prompt_toolkit():
    from prompt_toolkit.input.ansi_escape_sequences import ANSI_SEQUENCES as pt_map

    pyterm_map = KEY_MAP
    pyterm_keys = set(pyterm_map)
    pt_keys = set(pt_map)

    print("== Comparing with prompt_toolkit")
    print("missing keys:", pt_keys - pyterm_keys)
    print("extra keys:", pyterm_keys - pt_keys)

    different_count = 0
    for key in pyterm_keys & pt_keys:
        v1, v2 = pyterm_map[key], pt_map[key]
        v2 = () if v2 == "<ignore>" else v2
        v2 = (v2,) if isinstance(v2, str) else v2
        v2 = tuple(x.value if hasattr(x, "value") else x for x in v2)
        v2 = tuple(x.replace("c-", "ctrl+").replace("s-", "shift+") for x in v2)
        if v1 != v2:
            different_count += 1
            print("different key:", repr(key), v1, v2)

    if not different_count:
        print("all keys are equal")


if __name__ == "__main__":
    compare_with_textual()
    compare_with_prompt_toolkit()
