try:
    import msvcrt

    kbhit = msvcrt.kbhit
except ImportError:
    import select
    import sys
    import termios
    import tty


    def _KBHit_Unix():
        """kbhit() - returns 1 if a key is ready, 0 otherwise.
           kbhit always returns immediately.
        """
        #old_settings = termios.tcgetattr(sys.stdin)
        #tty.setcbreak(sys.stdin.fileno())

        try:
            (read_ready, write_ready, except_ready) = \
                select.select([sys.stdin], [], [], 0)
            # print("read_ready: ", read_ready)
            if read_ready != []:
                return 1
            else:
                return 0
        finally:
            pass
            # termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)


    kbhit = _KBHit_Unix

if __name__ == "__main__":
    while True:
        ready = kbhit()
        print(ready)
        if ready:
            break
        else:
            print('.', end=' ')
