"""mpylab.limits.limit module."""
from numpy import array, full_like, nan, log10

def log_linear(f1,v1,f2,v2):
    """log_linear function."""
    return lambda f: (v2-v1) * log10(f/f1) / log10(f2/f1) + v1

class Limit:
    """Limit class."""
    def __init__(self):
        pass

    def no_limit(self, f):
        """no_limit method."""
        if not isinstance(f, type(array)):
            f = array(f, dtype=float)
        return full_like(f, nan)

