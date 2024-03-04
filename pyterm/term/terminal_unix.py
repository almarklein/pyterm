import os
import tty  # Unix
import signal
import termios  # Unix

from .terminal import Terminal



def patch_lflag(attrs: int) -> int:
    return attrs & ~(termios.ECHO | termios.ICANON | termios.IEXTEN | termios.ISIG)


def patch_iflag(attrs: int) -> int:
    return attrs & ~(
        # Disable XON/XOFF flow control on output and input.
        # (Don't capture Ctrl-S and Ctrl-Q.)
        # Like executing: "stty -ixon."
        termios.IXON
        | termios.IXOFF
        |
        # Don't translate carriage return into newline on input.
        termios.ICRNL
        | termios.INLCR
        | termios.IGNCR
    )


class UnixTerminal(Terminal):

    def __init__(self, **kwargs):
        self._ori_term_attr = None
        super().__init__(**kwargs)

    def _ok_to_init(self):

        # This was from Textual's start_application_mode()
        def _stop_again(*_) -> None:
            """Signal handler that will put the application back to sleep."""
            os.kill(os.getpid(), signal.SIGSTOP)

        # If we're working with an actual tty...
        # https://github.com/Textualize/textual/issues/4104
        if os.isatty(self.fd_in):
            # Set up handlers to ensure that, if there's a SIGTTOU or a SIGTTIN,
            # we go back to sleep.
            signal.signal(signal.SIGTTOU, _stop_again)
            signal.signal(signal.SIGTTIN, _stop_again)
            try:
                # Here we perform a NOP tcsetattr. The reason for this is
                # that, if we're suspended and the user has performed a `bg`
                # in the shell, we'll SIGCONT *but* we won't be allowed to
                # do terminal output; so rather than get into the business
                # of spinning up application mode again and then finding
                # out, we perform a no-consequence change and detect the
                # problem right away.
                termios.tcsetattr(
                    self.fd_in, termios.TCSANOW, termios.tcgetattr(self.fd_in)
                )
            except termios.error:
                # There was an error doing the tcsetattr; there is no sense
                # in carrying on because we'll be doing a SIGSTOP (see
                # above).
                return
            finally:
                # We don't need to be hooking SIGTTOU or SIGTTIN any more.
                signal.signal(signal.SIGTTOU, signal.SIG_DFL)
                signal.signal(signal.SIGTTIN, signal.SIG_DFL)

        return True

        # todo: start writer thread

        # We can use a signal handler to keep notified of size changes.
        # But for now we don't care about size, so we don't.
        # signal.signal(signal.SIGWINCH, on_terminal_resize)
        # We can also use


    def _set_terminal_mode(self):
        try:
            self._ori_term_attr = termios.tcgetattr(self.fd_in)
        except termios.error:
            # Ignore attribute errors.
            self._ori_term_attr = None

        try:
            newattr = termios.tcgetattr(self.fd_in)
        except termios.error:
            pass
        else:
            newattr[tty.LFLAG] = patch_lflag(newattr[tty.LFLAG])
            newattr[tty.IFLAG] = patch_iflag(newattr[tty.IFLAG])

            # VMIN defines the number of characters read at a time in
            # non-canonical mode. It seems to default to 1 on Linux, but on
            # Solaris and derived operating systems it defaults to 4. (This is
            # because the VMIN slot is the same as the VEOF slot, which
            # defaults to ASCII EOT = Ctrl-D = 4.)
            newattr[tty.CC][termios.VMIN] = 1

            termios.tcsetattr(self.fd_in, termios.TCSANOW, newattr)

    def _reset(self):
        # Reset terminal
        if self._ori_term_attr is not None:
            try:
                termios.tcsetattr(self.fd_in, termios.TCSANOW, self._ori_term_attr)
            except Exception:
                pass
            self_ori_term_attr = None

