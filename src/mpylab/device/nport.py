# -*- coding: utf-8 -*-
"""Base driver for passive n-port style data models."""

from mpylab.device.driver import DRIVER
from mpylab.tools.configuration import strbool, fstrcmp
from mpylab.tools.dataparser import DatFile
from mpylab.tools.interpol import UQ_interpol
from mpylab.tools.regular_expressions import FP


def _file_source(value):
    """Keep inline file-like data sources intact while accepting path strings."""
    return value


class NPORT(DRIVER):
    """
    Child class for all py-drivers for n-ports (like antennas, cables, hybrids, ...)
    The parent class is DRIVER
    """

    _FP = FP

    conftmpl = {'description':
                    {'description': str,
                     'type': str,
                     'vendor': str,
                     'serialnr': str,
                     'deviceid': str,
                     'driver': str},
                'init_value':
                    {'fstart': float,
                     'fstop': float,
                     'fstep': float,
                     'nr_of_channels': int,
                     'virtual': strbool},
                'channel_%d':
                    {'name': str,
                     'unit': str,
                     'interpolation': str,
                     'file': _file_source}}

    def __init__(self, SearchPaths=None):
        DRIVER.__init__(self, SearchPaths=SearchPaths)
        # self.kw = kw
        self.error = 0
        self.conf = {'init_value': {'virtual': False}}
        self.data = {}
        self.freq = None

    def Init(self, ini=None, channel=None, ignore_bus=True):
        """Initialize channel datasets and interpolation helpers from config."""
        super().Init(ini=ini, channel=channel, ignore_bus=ignore_bus)
        # self.error=0
        # self.Configuration=Configuration(ini, self.conftmpl)
        # print self.Configuration.conf
        # self.conf.update(self.Configuration.conf)
        for ch in self.Configuration.channel_list:
            thech = f'channel_{ch}'
            thename = self._get(thech, 'name')
            thefile = self._get(thech, 'file')
            theinterpol = self._get(thech, 'interpolation')
            theunit = self._get(thech, 'unit')
            self.data[thename] = {}
            self.data[thename]['unit'] = theunit
            self.data[thename]['datafile'] = DatFile(filename=thefile,
                                                     interpolation=theinterpol, SearchPaths=self.SearchPaths)
            # print(self.data[thename]['datafile'])
            self.data[thename]['data'] = self.data[thename]['datafile'].run()
            # print self.data[thename]['data']
            self.data[thename]['interpol'] = UQ_interpol(self.data[thename]['data'])
        return self.error

    def _get(self, sec, key):
        sectok = fstrcmp(sec, self.conftmpl, cutoff=0, ignorecase=True)[0]
        keytok = fstrcmp(key, self.conftmpl[sectok], cutoff=0, ignorecase=True)[0]
        if '%' in sectok:
            pos = sectok.index('%')
            sectok = sectok[:pos] + sec[pos:]
        # print sectok, keytok
        # print self.conf.keys()
        return self.conf[sectok][keytok]

    def Quit(self):
        """Close driver state and return status."""
        self.error = 0
        return self.error

    def SetVirtual(self, virtual):
        """Enable or disable virtual mode in runtime configuration."""
        self.error = 0
        self.conf['init_value']['virtual'] = virtual
        return self.error

    def GetVirtual(self):
        """Return whether virtual mode is enabled."""
        self.error = 0
        return self.error, self.conf['init_value']['virtual']

    def GetDescription(self):
        """Return the configured description string."""
        self.error = 0
        return self.error, self.conf['description']['description']

    def SetFreq(self, freq):
        """Set current interpolation frequency in Hz."""
        self.error = 0
        self.freq = freq
        return self.error, freq

    def GetFreq(self):
        """Return current interpolation frequency in Hz."""
        self.error = 0
        return self.error, self.freq

    def GetChannels(self):
        """Return available channel names."""
        self.error = 0
        return self.error, tuple(self.data.keys())

    def GetData(self, what):
        """Return interpolated data for a requested channel name."""
        self.error = 0
        allwhat = list(self.data.keys())
        whatguess = None
        for w in allwhat:
            if what.lower().replace(' ', '') == w.lower().replace(' ', ''):
                whatguess = w
        # print what, whatguess
        if not whatguess:
            self.error = -1
            obj = None
        else:
            obj = self.data[whatguess]['interpol'](self.freq)
        return self.error, obj


class CABLE(NPORT):
    """Passive cable model based on interpolated n-port data."""


class ANTENNA(NPORT):
    """Passive antenna model based on interpolated n-port data."""


def main():
    """Run a simple manual test for NPORT interpolation behavior."""
    import sys
    import io
    from mpylab.tools.util import format_block
    import scuq

    try:
        ini = sys.argv[1]
    except IndexError:
        ini = format_block("""
                         [description]
                         DESCRIPTION = Just a Cable
                         TYPE = CABLE
                         VENDOR =UMD
                         SERIALNR = 
                         DEVICEID = 
                         DRIVER =

                         [INIT_VALUE]
                         FSTART = 0
                         FSTOP = 8e9
                         FSTEP = 0.0
                         NR_OF_CHANNELS =  1
                         VIRTUAL = 0

                         [CHANNEL_1]
                         NAME = S21
                         UNIT = dB
                         INTERPOLATION = LOG
                         FILE = io.StringIO(format_block('''
                                                                FUNIT: Hz
                                                                UNIT: dB
                                                                ABSERROR: [0.1, 1]
                                                                10 [-40, 0]
                                                                90 [-40, 0]
                                                                #30 [0.8, 70]
                                                                #40 [0.7, 120]
                                                                #50 [0.6, 180]
                                                                #60 [0.5, 260]
                                                                #70 [0.4, 310]
                                                                #80 [0.3, 10]
                                                                #90 [0.2, 50]
                                            '''))
                         """)
        ini = io.StringIO(ini)

    cbl = NPORT(SearchPaths=['testpfad'])
    err = cbl.Init(ini)
    ctx = scuq.ucomponents.Context()
    for freq in range(10, 100, 10):
        cbl.SetFreq(freq)
        err, uq = cbl.GetData(what='S21')
        val, unc, unit = ctx.value_uncertainty_unit(uq)
        print((freq, uq, abs(val), abs(unc), unit))


if __name__ == '__main__':
    main()
