version='unknown'
try:
    import __version__
    version=__version__.version
except ImportError:
    pass
