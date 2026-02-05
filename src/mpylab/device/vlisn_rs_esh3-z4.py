# -*- coding: utf-8 -*-
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from mpylab.device.vlisn import VLISN as VL
from mpylab.tools.util import case_insensitive_string_compare
from mpylab.tools.configuration import Configuration

class VLISN(VL):
    """
    T-Type LISN device R&S esh3-z4
    """
    conftmpl = VL.conftmpl

    def __init__(self, **kw):
        VL.__init__(self, **kw)



    def Init(self, ini=None, channel=None, ignore_bus=True):
        self.path = None
        self.filter = None
        super().Init(ini=ini, channel=channel, ignore_bus=ignore_bus)

        sec = 'channel_%d' % self.channel

        return self.error

    def SetPath(self, path):
        return path

    def SetFilter(self, state):
        raise NotImplementedError

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
                         DESCRIPTION = R&S ENV216 V-Type LISN
                         TYPE = VLISN
                         VENDOR = Rohde&Schwarz
                         SERIALNR = 
                         DEVICEID = 
                         DRIVER = vlisn_rs_env216.py

                         [INIT_VALUE]
                         FSTART = 9e3
                         FSTOP = 30e6
                         FSTEP = 0.0
                         NR_OF_CHANNELS =  1
                         IP = 192.168.88.6
                         FILTER = 0
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

    while(True):
        ans = input('L, N, F, f, Q > ')
        if ans in 'Qq':
            break
        if ans in 'F':
            lisn.SetFilter(True)
        if ans in 'f':
            lisn.SetFilter(False)
        if ans in 'Ll':
            lisn.SetPath('L')
        if ans in 'Nn':
            lisn.SetPath('N')


if __name__ == '__main__':
    main()
