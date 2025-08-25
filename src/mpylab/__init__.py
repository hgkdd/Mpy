__version__ = 'unknown'
try:
    from ._version import version

    __version__ = version
except ImportError:
    pass
