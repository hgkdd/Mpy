# -*- coding: utf-8 -*-
#
import io
import sys
from copy import deepcopy

import mpylab.tools.spacing
from mpylab.device.powermeter import POWERMETER as PMMTR
from scuq.quantities import Quantity
from scuq.ucomponents import UncertainInput
from scuq.si import WATT

class POWERMETER(PMMTR):
    conftmpl = deepcopy(PMMTR.conftmpl)
    conftmpl['init_value']['visa'] = str

    def __init__(self, **kw):
        PMMTR.__init__(self, **kw)
        self._internal_unit = 'dBm'
        self.trace = 1

        self.freq = None

        self._cmds = {'Zero': [],
                      'ZeroOn': [],
                      'ZeroOff': [],
                      'Trigger': [],
                      'Quit': [],
                      'GetDescription': [('*IDN?', r'(?P<IDN>.*)')]}
        self.term_chars = '\r\n'
        self.error = None


    def Init(self, ini=None, channel=None):
        if channel is None:
            channel = 1
        self.channel = channel
        self.error = PMMTR.Init(self, ini, self.channel)  # run init from parent class
        sec = f'channel_{channel}'
        try:
            self.levelunit = self.conf[sec]['unit']
        except KeyError:
            self.levelunit = self._internal_unit

        return self.error

    def SetFreq(self, freq):
        self.freq = freq
        return 0, self.freq

    def GetDataNB(self):
        return self.GetData()

    def GetData(self):
        # set marker 1 to peak
        self.write('INIT1:IMM')
        self.write('CALC:MARK1:MAX')
        self.write('CALC:MARK1:X?')
        mfreq = float(self.dev.read())
        self.write('CALC:MARK1:Y?')
        mpower = float(self.dev.read())
        mpower_watt = 10**(mpower*0.1)*0.001
        power = Quantity(WATT, UncertainInput(mpower_watt ,0.05*mpower_watt))
        return 0, power

def main():
    from mpylab.tools.util import format_block

    try:
        ini = sys.argv[1]
    except IndexError:
        ini = format_block("""
                        [DESCRIPTION]
                        description: 'ZLV-6-K1'
                        type:        'POWERMETER'
                        vendor:      'Rohde&Schwarz'
                        serialnr:
                        deviceid:
                        driver:

                        [Init_Value]
                        fstart: 9e3
                        fstop: 6e9
                        fstep: 1
                        gpib: 20
                        virtual: 0

                        [Channel_1]
                        unit: 'dBm'
                        """)
        ini = io.StringIO(ini)

    zvl = POWERMETER()

    err = zvl.Init(ini)

    freqs = mpylab.tools.spacing.logspace(30e6, 1e9, 1.1, endpoint=True)
    for f in freqs:
        zvl.SetFreq(f)
        err, lv = zvl.GetData()
        print(f"{f=}, {lv=}")
    zvl.Quit()

if __name__ == '__main__':
    main()
