try:
    import msvcrt
    kbhit = msvcrt.kbhit
except ImportError:
    import select, sys
    def _KBHit_Unix():
        """kbhit() - returns 1 if a key is ready, 0 othewise.
           kbhit always returns immediately.
        """
        (read_ready, write_ready, except_ready) = \
            select.select( [sys.stdin], [], [], 0.0)
        if read_ready:
            return 1
        else:
            return 0
    kbhit = _KBHit_Unix


if __name__ == "__main__":
    while True:
        ready = kbhit()
        if ready:
            break
        else:
            print('.', end=' ')
