# -*- coding: utf-8 -*-
#
import io
import sys
import math
import re
from copy import deepcopy

import mpylab.tools.spacing
from mpylab.device.powermeter import POWERMETER as PMMTR
from scuq.quantities import Quantity
from scuq.ucomponents import UncertainInput
from scuq.si import WATT

from mpylab.tools.numeric_eval import safe_numeric_eval


class POWERMETER(PMMTR):
    conftmpl = deepcopy(PMMTR.conftmpl)
    conftmpl['init_value']['visa'] = str
    conftmpl['channel_%d']['value'] = str
    conftmpl['channel_%d']['uncertainty'] = str

    def __init__(self, **kw):
        PMMTR.__init__(self, **kw)
        self.IDN = "Virtual Powermeter"
        self._internal_unit = 'dBm'
        self.freq = None
        self._last_response = ""

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
        sec = f'channel_{self.channel}'
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
        return 0, self.IDN

    def write(self, cmd):
        """Handle a small SCPI-like command subset without a hardware bus."""
        cmd = str(cmd).strip()
        upper = cmd.upper()
        self._last_response = ""
        if upper == "*IDN?":
            self._last_response = self.IDN
        elif upper == "FREQ?":
            self._last_response = f"FREQ {self.freq if self.freq is not None else 0.0} HZ"
        elif upper.startswith("FREQ "):
            parts = cmd.split()
            if len(parts) >= 2:
                self.freq = float(parts[1])
        elif upper == "POW?":
            err, power = self.GetData()
            value = power.get_expectation_value_as_float()
            self._last_response = f"POW {value} W"
        elif upper in {"TRG", "*TRG"}:
            self.Trigger()
        elif upper.startswith("ZERO"):
            pass
        elif upper in {"QUIT", "SYST:LOC"}:
            pass
        elif upper == "*RST":
            self.freq = None
        else:
            self._last_response = f"OK {cmd}"
        return 0

    def read(self, tmpl=None):
        """Return or parse the last virtual SCPI response."""
        if tmpl is None:
            return self._last_response
        match = re.match(tmpl, self._last_response)
        if match is None:
            return {}
        return match.groupdict()

    def query(self, cmd, tmpl=None):
        """Write a virtual SCPI query and return the raw or parsed response."""
        self.write(cmd)
        return self.read(tmpl)

    def SetFreq(self, freq):
        self.freq = freq
        return 0, self.freq

    def GetDataNB(self):
        return self.GetData()

    def GetData(self):
        f = self.freq
        # Keep the virtual driver deterministic but still allow simple f-dependent formulas.
        value_expr = str(self.value).replace("f", f"({f if f is not None else 0.0})")
        uncertainty_expr = str(self.uncertainty).replace("f", f"({f if f is not None else 0.0})")
        mpower = safe_numeric_eval(value_expr)
        mpower_watt = 10**(mpower*0.1)*0.001
        unc = safe_numeric_eval(uncertainty_expr)
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
                        value: -20 + f/1e10
                        uncertainty: 0.1

                        [Channel_2]
                        unit: 'dBm'
                        value: -10
                        uncertainty: 0.1
                        """)
        ini = io.StringIO(ini)

    pm = POWERMETER()

    err = pm.Init(ini, channel=1)

    freqs = mpylab.tools.spacing.logspace(30e6, 1e9, 1.1, endpoint=True)
    for f in freqs:
        pm.SetFreq(f)
        err, lv = pm.GetData()
        print(f"{f=}, {lv=}")
    pm.Quit()

if __name__ == '__main__':
    main()
