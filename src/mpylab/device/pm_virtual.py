# -*- coding: utf-8 -*-
#
import io
import sys

import mpylab.tools.spacing
from mpylab.device.powermeter import POWERMETER as PMMTR
from scuq.quantities import Quantity
from scuq.ucomponents import UncertainInput
from scuq.si import WATT

class POWERMETER(PMMTR):
    conftmpl = PMMTR.conftmpl
    conftmpl['init_value']['visa'] = str
    conftmpl['channel_%d']['value'] = float
    conftmpl['channel_%d']['uncertainty'] = float

    def __init__(self, **kw):
        PMMTR.__init__(self, **kw)
        self._internal_unit = 'dBm'
        self.freq = None

        self._cmds = {'Zero': [],
                      'ZeroOn': [],
                      'ZeroOff': [],
                      'Trigger': [],
                      'Quit': []}
        self.error = None


    def Init(self, ini=None, channel=None):
        if channel is None:
            self.channel = 1
        else:
            self.channel = channel
        self.error = PMMTR.Init(self, ini, self.channel, ignore_bus=True)  # run init from parent class
        sec = 'channel_%d' % self.channel
        try:
            self.levelunit = self.conf[sec]['unit']
        except KeyError:
            self.levelunit = 'dBm'
        try:
            self.value = self.conf[sec]['value']
        except KeyError:
            self.value = 42
        try:
            self.uncertainty = self.conf[sec]['uncertainty']
        except KeyError:
            self.uncertainty = 0.42
        return self.error

    def GetDescription(self):
        return 0, "Virtual Powermeter"

    def SetFreq(self, freq):
        self.freq = freq
        return 0, self.freq

    def GetDataNB(self):
        return self.GetData()

    def GetData(self):
        mpower = self.value
        mpower_watt = 10**(mpower*0.1)*0.001
        unc = self.uncertainty
        unc_watt = 10**((mpower+unc)*0.1)*0.001
        power = Quantity(WATT, UncertainInput(mpower_watt ,unc_watt))
        return 0, power

def main():
    from mpylab.tools.util import format_block

    try:
        ini = sys.argv[1]
    except IndexError:
        ini = format_block("""
                        [DESCRIPTION]
                        description: 'Virtual Powermeter'
                        type:        'POWERMETER'
                        vendor:      'TUD'
                        serialnr:
                        deviceid:
                        driver:

                        [Init_Value]
                        fstart: 0
                        fstop: 100e9
                        fstep: 1
                        gpib: 20
                        virtual: 1

                        [Channel_1]
                        unit: 'dBm'
                        value: 0
                        uncertainty: 0.1

                        [Channel_2]
                        unit: 'dBm'
                        value: -10
                        uncertainty: 0.1
                        """)
        ini = io.StringIO(ini)

    pm = POWERMETER()

    err = pm.Init(ini, channel=2)

    freqs = mpylab.tools.spacing.logspace(30e6, 1e9, 1.1, endpoint=True)
    for f in freqs:
        pm.SetFreq(f)
        err, lv = pm.GetData()
        print(f"{f=}, {lv=}")
    pm.Quit()

if __name__ == '__main__':
    main()
