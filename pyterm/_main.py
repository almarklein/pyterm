import sys
import time
import queue

from .loops import loop_manager, RawLoop, enable_all_loop_support
from .term import TerminalContext, ProxyStdin, ProxyStdout, InputReader
from .repl import Repl
from .prompt import Prompt


def main():

    # When importing pyterm, nothing should happen just yet.
    # Only when this function is called, is everything put in place.

    # Uncomment to detect error in the interpreter itself.
    # But better not use it by default. For instance errors in qt events
    # are also catched by this function. I think that is because it would
    # allow you to show such exceptions in an error dialog.
    # sys.excepthook = pyterm_excepthook

    with TerminalContext() as terminal_context:

        # Create queue to store lines from stdin, but thread-safe, and being
        # able to tell whether there are lines pending.
        lines_queue = queue.Queue()

        prompt = Prompt(sys.stdout)

        # Replace stdin with a variant that uses the queue.
        sys.stdin = ProxyStdin(lines_queue, "<stdin>")
        sys.stdout = ProxyStdout(sys.stdout, "<stdout>", prompt)
        sys.stderr = ProxyStdout(sys.stderr, "<stderr>", prompt)

        def callback(key):
            if "x" == key:
                print("Quitting!")
                loop.call_soon(sys.exit)
            # print("echo", repr(key))
            prompt.on_key(key)

        # Read from real stdin, into the queue.
        input_thread = InputReader(sys.__stdin__.fileno(), callback)
        input_thread.start()

        # Create a repl, also reads from the queue.
        namespace = {}
        # repl = Repl(namespace, lines_queue)

        # Patching loops
        enable_all_loop_support()

        # Create outer loop
        loop = RawLoop()
        loop_manager.add_loop(loop)

        try:
            loop.run()
        except BaseException as err:
            pass  # print("except from loop", err)
        finally:
            # Restore original streams, so that SystemExit behaves as intended
            prompt.clear(True)
            try:
                sys.stdout, sys.stderr = sys.__stdout__, sys.__stderr__
            except Exception:
                pass
            try:
                # Help InputReader close down
                sys.stdin.close()
            except (Exception, KeyboardInterrupt):
                pass
            # Could do more cleanup here


def pyterm_excepthook(type, value, tb):

    def writeErr(err):
        sys.__stderr__.write(str(err) + "\n")
        sys.__stderr__.flush()

    writeErr("Uncaught exception in pyterm:")
    writeErr(value)
    if not isinstance(value, (OverflowError, SyntaxError, ValueError)):
        while tb:
            writeErr(
                "-> line %i of %s."
                % (tb.tb_frame.f_lineno, tb.tb_frame.f_code.co_filename)
            )
            tb = tb.tb_next

    time.sleep(0.3)  # Give some time for the message to be send
