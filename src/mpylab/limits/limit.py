from numpy import array, full_like, nan, log10

def log_linear(f1,v1,f2,v2):
    return lambda f: (v2-v1) * log10(f/f1) / log10(f2/f1) + v1

class Limit:
    def __init__(self):
        pass

    def no_limit(self, f):
        if not isinstance(f, type(array)):
            f = array(f, dtype=float)
        return full_like(f, nan)

