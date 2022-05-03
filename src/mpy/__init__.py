version='unknown'
try:
    from . import __version__
    version=__version__.version
except ImportError:
    pass
