import sys, os, tty, termios, fcntl


class PosixTerm(object):
    def __init__(self):
        self.peek_buffer = {}

    def _read_blocking(self, fd):
        term_settings = termios.tcgetattr(fd)
        try:
            tty.setcbreak(fd, termios.TCSANOW)
            char = os.read(fd, 1)
        finally:
            termios.tcsetattr(fd, termios.TCSANOW, term_settings)
        return char

    def _read_nonblocking(self, fd):
        term_settings = termios.tcgetattr(fd)
        flags = fcntl.fcntl(fd, fcntl.F_GETFL)
        try:
            fcntl.fcntl(fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)
            tty.setcbreak(fd, termios.TCSANOW)
            char = os.read(fd, 1)
        except OSError:
            char = ""
        finally:
            fcntl.fcntl(fd, fcntl.F_SETFL, flags)
            termios.tcsetattr(fd, termios.TCSANOW, term_settings)
        return char

    def kbhit(self, fd=sys.stdin.fileno()):
        if self.peek_buffer.get(fd):
            return 1
        char = self._read_nonblocking(fd)
        self.peek_buffer[fd] = char
        return int(bool(char))

    def getch(self, fd=sys.stdin.fileno()):
        if self.peek_buffer.get(fd):
            char = self.peek_buffer[fd][0]
            self.peek_buffer[fd] = self.peek_buffer[fd][1:]
            return char
        return self._read_blocking(fd)

    def getwch(self, fd=sys.stdin.fileno(), encoding=sys.stdin.encoding):
        raw_str = ""
        for i in range(4):
            if self.peek_buffer.get(fd):
                raw_str += self.peek_buffer[fd][0]
                self.peek_buffer[fd] = self.peek_buffer[fd][1:]
            else:
                if raw_str:
                    raw_char = self._read_nonblocking(fd)
                    if not raw_char: break
                    raw_str += raw_char
                else:
                    raw_str = self._read_blocking(fd)
            try:
                u_char = str(raw_str, encoding)
                return u_char
            except UnicodeDecodeError:
                continue
        return str(raw_str, encoding)

if __name__ == "__main__":
    import time
    try:
        from msvcrt import getch, getwch, kbhit
    except ImportError:
        _posix_term = PosixTerm()
        getch = _posix_term.getch
        getwch = _posix_term.getwch
        kbhit = _posix_term.kbhit

    for i in range(100):
        print('.', end='', flush=True)
        if kbhit():
            k = getch()
            print(f'you hit a key: {k}')
        time.sleep(1)
