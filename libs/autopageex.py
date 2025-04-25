import sys
import os
import autopage  
#from autopage import AutoPager

# Extend the AutoPager class
# This class will also handle the stderr redirection
#
# stderr=True       - allow stdedrr without redirction use stderr=True
# stderrdup=True    - redirect stderr to stdout 
# stderr=False and stderrdup=False  - redirect stderr to /dev/null
#
# fixLess=True      - apply fix to the LESS environment variable
# fixLess=False     - do not apply fix to the LESS environment variable

class AutoPagerEx(autopage.AutoPager):
    def __init__(self, stderr=False, stderrdup=False, fixLess=True, **kws):
        self.stderr = stderr
        self.stderrdup = stderrdup
        self.fixLess = fixLess
        self.sysstderr = sys.stderr
        self.sysstdout = sys.stdout
        self.fixLess = fixLess
        if fixLess:
            self.less = os.environ.get('LESS', '')
            os.environ['LESS'] += " -F --quit-if-one-screen"
        super(AutoPagerEx, self).__init__(**kws)

    def __enter__(self):
        #print('AutoPagerEx.__enter__ stderr:', self.stderr, 'stderrdup:', self.stderrdup, 'less:', self.less, 'LESS:', os.environ.get('LESS', ''))
        stdout = super(AutoPagerEx, self).__enter__()
        return stdout, sys.stderr if self.stderr else stdout if self.stderrdup else open(os.devnull, 'w')

    def __exit__(self, exc_type, exc_value, traceback):
        print(f'AutoPagerEx.__exit__ exc_type: {exc_type} exc_value: {exc_value}', file=sys.stderr)
        print(f"AutoPagerEx.__exit__ _exit_code: {self._exit_code}", file=sys.stderr)
        print(f"traceback: {traceback}", file=sys.stderr)
        super(AutoPagerEx, self).__exit__(exc_type, exc_value, traceback)
        if self.fixLess:
            os.environ['LESS'] = self.less
        sys.stderr = self.sysstderr
        sys.stdout = self.sysstdout



if __name__ == "__main__":

    # Cross-platform single-character input
    try:
        import msvcrt  # Windows
        def get_single_char():
            return msvcrt.getch().decode()
    except ImportError:
        import tty, termios  # Unix
        def get_single_char():
            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
            try:
                tty.setraw(fd)
                char = sys.stdin.read(1)
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
            return char

    def wait_for_keypress():
        """Pause execution and allow Ctrl-C to exit."""
        try:
            print("\nPress SPACE to continue, or Ctrl-C to exit... ")
            get_single_char()
        except KeyboardInterrupt:
            print("\nCtrl-C detected. Exiting.", file=sys.stderr)
            sys.exit(1)

    tests = [ 'AAAA', 'BBBB', 'CCCC', 'DDDD' ]

    for test in tests:
        print(f'TEST: {test}', file=sys.stdout)
        with AutoPagerEx(stderr=True, stderrdup=False, fixLess=False) as (sys.stdout, sys.stderr):
            print(f'stdout: 1. {test}', file=sys.stdout)
            print(f'stderr: 2. {test}', file=sys.stderr)
            print(f'stderr: 3. {test}', file=sys.stderr)



