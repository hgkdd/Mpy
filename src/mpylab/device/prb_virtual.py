# -*- coding: utf-8 -*-
"""Virtual field probe driver for UI and workflow tests."""

from copy import deepcopy

from scuq import si, quantities, ucomponents

from mpylab.device.fieldprobe import FIELDPROBE as FIELDPROBE_BASE
from mpylab.tools.numeric_eval import safe_numeric_eval


class FIELDPROBE(FIELDPROBE_BASE):
    conftmpl = deepcopy(FIELDPROBE_BASE.conftmpl)
    conftmpl["channel_%d"]["x"] = str
    conftmpl["channel_%d"]["y"] = str
    conftmpl["channel_%d"]["z"] = str
    conftmpl["channel_%d"]["uncertainty"] = str

    def __init__(self, **kw):
        super().__init__(**kw)
        self.IDN = "Virtual FieldProbe"
        self._internal_unit = si.VOLT / si.METER
        self.freq = 1e6
        self.channel = 1
        self.error = 0
        self.x_expr = "1 + f/1e9"
        self.y_expr = "2"
        self.z_expr = "3"
        self.uncertainty_expr = "0.1"
        self.battery = 1.0
        self.zero_state = "off"

    def Init(self, ini=None, channel=None):
        self.channel = 1 if channel is None else channel
        self.error = FIELDPROBE_BASE.Init(self, ini, self.channel, ignore_bus=True)
        self.bus_ready = True
        self.conf.setdefault("init_value", {})
        self.conf["init_value"]["virtual"] = True
        sec = f"channel_{self.channel}"
        channel_conf = self.conf.get(sec, {})
        self.unit = channel_conf.get("unit", self._internal_unit)
        self.x_expr = channel_conf.get("x", self.x_expr)
        self.y_expr = channel_conf.get("y", self.y_expr)
        self.z_expr = channel_conf.get("z", self.z_expr)
        self.uncertainty_expr = channel_conf.get("uncertainty", self.uncertainty_expr)
        return self.error

    def GetDescription(self):
        return 0, self.IDN

    def SetFreq(self, freq):
        self.freq = float(freq)
        return 0, self.freq

    def GetFreq(self):
        return 0, self.freq

    def Trigger(self):
        return 0, 0

    def Zero(self, state):
        self.zero_state = "on" if str(state).strip().lower() == "on" else "off"
        return 0, self.zero_state

    def _component(self, expr):
        f = self.freq
        value = float(safe_numeric_eval(str(expr).replace("f", f"({f})")))
        uncertainty = abs(value) * float(
            safe_numeric_eval(str(self.uncertainty_expr).replace("f", f"({f})"))
        )
        return quantities.Quantity(
            self._internal_unit,
            ucomponents.UncertainInput(value, uncertainty),
        )

    def GetData(self):
        return 0, [
            self._component(self.x_expr),
            self._component(self.y_expr),
            self._component(self.z_expr),
        ]

    def GetDataNB(self, retrigger=False):
        if retrigger:
            self.Trigger()
        return self.GetData()

    def GetBatteryState(self):
        return 0, self.battery

    def GetWaveform(self):
        return -1, None, None, None, None

    def Quit(self):
        return 0
