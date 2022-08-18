class _Getch(object):
    """Gets a single character from standard input.  
    Does not echo to the screen."""

    def __init__(self):
        try:
            self.impl = _GetchWindows()
        except (ModuleNotFoundError, ImportError):
            try:
                self.impl = _GetchMacOS()
            except (ModuleNotFoundError, AttributeError):
                self.impl = _GetchUnix()

    def __call__(self):
        return self.impl()


class _GetchUnix(object):
    def __init__(self):
        import getch
    def __call__(self):
        import getch
        return getch.getch()


class _GetchWindows(object):
    def __init__(self):
        import msvcrt

    def __call__(self):
        import msvcrt
        return msvcrt.getch()


class _GetchMacOS(object):
    def __init__(self):
        import getch

    def __call__(self):
        import getch
        return getch.getch()


getch = _Getch()

if __name__ == '__main__':  # a little test
    while True:
        print('Press a key (q=quit)')
        k = getch()
        print(k)
        if k == 'q':
            break
