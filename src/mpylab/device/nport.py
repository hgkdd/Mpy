# -*- coding: utf-8 -*-

from mpylab.device.driver import DRIVER
from mpylab.tools.Configuration import strbool, fstrcmp
from mpylab.tools.dataparser import DatFile
from mpylab.tools.interpol import UQ_interpol


class NPORT(DRIVER):
    """
    Child class for all py-drivers for n-ports (like antennas, cables, hybrids, ...)
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
                     'nr_of_channels': int,
                     'virtual': strbool},
                'channel_%d':
                    {'name': str,
                     'unit': str,
                     'interpolation': str,
                     'file': str}}

    def __init__(self, **kw):
        DRIVER.__init__(self, **kw)
        self.kw = kw
        self.error = 0
        self.conf = {'init_value': {'virtual': False}}
        self.data = {}

    def Init(self, ininame, channel=None):
        DRIVER.Init(self, ininame, channel=channel)
        # self.error=0
        # self.Configuration=Configuration(ininame, self.conftmpl)
        # print self.Configuration.conf
        # self.conf.update(self.Configuration.conf)
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


ANTENNA = CABLE = NPORT


def main():
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

    cbl = NPORT()
    err = cbl.Init(ini)
    ctx = scuq.ucomponents.Context()
    for freq in range(10, 100, 10):
        cbl.SetFreq(freq)
        err, uq = cbl.GetData(what='S21')
        val, unc, unit = ctx.value_uncertainty_unit(uq)
        print((freq, uq, abs(val), abs(unc), unit))


if __name__ == '__main__':
    main()
