# -*- coding: utf-8 -*-
import requests

from mpylab.device.vlisn import VLISN as VL
from mpylab.tools.util import case_insensitive_string_compare
from mpylab.tools.configuration import Configuration

class VLISN(VL):
    """
    V-Type LISN device R&S ENV216
    """
    conftmpl = VL.conftmpl
    conftmpl['init_value']['ip'] = str

    ip = '192.168.88.6'
    _FLT_ = 19
    _L_ = 18
    _N_ = 16

    def __init__(self):
        super().__init__()

    def _set_as_digital_out(self, pin):
        request = f"http://{self.ip}/mode/{pin}/o"
        ans = requests.get(request)
        return ans

    def _set_as_digital_in(self, pin):
        request = f"http://{self.ip}/mode/{pin}/i"
        ans = requests.get(request)
        return ans

    def _set_pin_state(self, pin, state):
        request = f"http://{self.ip}/digital/{pin}/{state}"
        ans = requests.get(request)
        return ans

    def _set_L(self):
        self._set_pin_state(self._N_, 1)
        self._set_pin_state(self._L_, 0)    # low for L

    def _set_N(self):
        self._set_pin_state(self._L_, 1)    # low for L
        self._set_pin_state(self._N_, 0)   # low for N

    def _set_filter(self, state):
        if state:
            state = 0
        else:
            state = 1
        self._set_pin_state(self._FLT_, state)   # low Filter ON


    def Init(self, ini=None, channel=None):
        self.path = None
        self.ip = None
        self.filter = None
        super().Init(ini=ini, channel=channel, ignore_bus=True)

        sec = 'channel_%d' % self.channel
        self.ip = self.conf['init_value']['ip']
        self.filter = bool(self.conf['init_value']['filter'])

        self._set_as_digital_out(self._FLT_)
        self._set_as_digital_out(self._L_)
        self._set_as_digital_out(self._N_)
        self.SetPath(self.path)
        self._set_filter(self.filter)
        return self.error

    def SetPath(self, path):
        self.error = 0
        self.path = None
        for _path in ('L', 'N'):
            if case_insensitive_string_compare(path, _path):
                if _path == 'N':
                    self._set_N()
                else:
                    self._set_L()
                self.path = _path
                break
        if self.path is None:
            raise RuntimeError("V-LISN: Path has to be in ('L', 'N')")
        return self.GetPath()

    def SetFilter(self, state):
        self._set_filter(state)
        self.filter = bool(state)

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
