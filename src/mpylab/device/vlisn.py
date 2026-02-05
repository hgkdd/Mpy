# -*- coding: utf-8 -*-

from mpylab.device.driver import DRIVER
from mpylab.tools.configuration import strbool, fstrcmp
from mpylab.tools.dataparser import DatFile
from mpylab.tools.interpol import UQ_interpol
from mpylab.tools.util import case_insensitive_string_compare


class VLISN(DRIVER):
    """
    Child class for all py-drivers for V-Type LISN
    The parent class is DRIVER
    """
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
                     'visa': str,
                     'nr_of_channels': int,
                     'path': str,
                     'unit': str,
                     'filter': strbool,
                     'virtual': strbool},
                'channel_%d':
                    {'name': str,
                     'unit': str,
                     'interpolation': str,
                     'file': str}}

    def __init__(self, **kw):
        super().__init__(self, **kw)
        self.kw = kw
        self.error = 0
        self.path = None
        self.conf = {'init_value': {'virtual': False}}
        self.data = {}

    def Init(self, ini=None, channel=None, ignore_bus=False):
        super().Init(ini=ini, channel=channel, ignore_bus=ignore_bus)
        self.path = self.conf['init_value']['path'].upper()
        for ch in self.Configuration.channel_list:
            thename = self._get('channel_%d' % ch, 'name')
            thefile = self._get('channel_%d' % ch, 'file')
            theinterpol = self._get('channel_%d' % ch, 'interpolation')
            theunit = self._get('channel_%d' % ch, 'unit')
            self.data[thename] = {}
            self.data[thename]['unit'] = theunit
            self.data[thename]['datafile'] = DatFile(filename=thefile,
                                                     interpolation=theinterpol, **self.kw)
            # print(self.data[thename]['datafile'])
            self.data[thename]['data'] = self.data[thename]['datafile'].run()
            # print self.data[thename]['data']
            self.data[thename]['interpol'] = UQ_interpol(self.data[thename]['data'])
        # self.SetPath(path)
        return self.error

    def _get(self, sec, key):
        sectok = fstrcmp(sec, self.conftmpl, n=1, cutoff=0, ignorecase=True)[0]
        keytok = fstrcmp(key, self.conftmpl[sectok], n=1, cutoff=0, ignorecase=True)[0]
        if '%' in sectok:
            pos = sectok.index('%')
            sectok = sectok[:pos] + sec[pos:]
        # print sectok, keytok
        # print self.conf.keys()
        return self.conf[sectok][keytok]

    def Quit(self):
        self.error = 0
        return self.error

    def SetVirtual(self, virtual):
        self.error = 0
        self.conf['init_value']['virtual'] = virtual
        return self.error

    def GetVirtual(self):
        self.error = 0
        return self.error, self.conf['init_value']['virtual']

    def GetDescription(self):
        self.error = 0
        return self.error, self.conf['description']['description']

    def SetFreq(self, freq):
        self.error = 0
        self.freq = freq
        return self.error, freq

    def GetData(self, what):
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

    def GetPath(self):
        self.error = 0
        return self.error, self.path

    def SetPath(self, path):
        self.error = 0
        self.path = None
        for _path in ('L', 'L1', 'L2', 'L3', 'N'):
            if case_insensitive_string_compare(path, _path):
                ans = input(f"Switch to {_path} and press enter.")
                self.path = _path
                break
        if self.path is None:
            raise RuntimeError("V-LISN: Path has to be in ('L', 'L1', 'L2', 'L3', 'N')")
        return self.GetPath()

    def SetFilter(self, state):
        self.error = 0
        self.filter = state

    def GetFilter(self):
        self.error = 0
        return self.error, bool(self.filter)

def main():
    import sys
    import io
    from mpylab.tools.util import format_block
    from mpylab.tools.spacing import linspaceN
    import scuq

    try:
        ini = sys.argv[1]
    except IndexError:
        ini = format_block("""
                         [description]
                         DESCRIPTION = A Dummy V-LISN
                         TYPE = VLISN
                         VENDOR = TUD
                         SERIALNR = 
                         DEVICEID = 
                         DRIVER =

                         [INIT_VALUE]
                         FSTART = 9e3
                         FSTOP = 30e6
                         FSTEP = 0.0
                         NR_OF_CHANNELS =  1
                         PATH = L
                         VIRTUAL = 0

                         [CHANNEL_1]
                         NAME = S21
                         UNIT = dB
                         INTERPOLATION = LIN
                         FILE = io.StringIO(format_block('''
                                                                FUNIT: Hz
                                                                UNIT: dB
                                                                RELERROR: 0
                                                                9e3 -10
                                                                30e6 -10
                                            '''))
                         """)
        ini = io.StringIO(ini)

    lisn = VLISN()
    err = lisn.Init(ini)
    ctx = scuq.ucomponents.Context()
    for path in ('L', 'N'):
        err, p = lisn.SetPath(path)
        print(f"Path set to {p}")
        for freq in linspaceN(9e3, 30e6, 10, endpoint=True):
            lisn.SetFreq(freq)
            err, uq = lisn.GetData(what='S21')
            val, unc, unit = ctx.value_uncertainty_unit(uq)
            print(freq, uq, abs(val), abs(unc), unit)


if __name__ == '__main__':
    main()
