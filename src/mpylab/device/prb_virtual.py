# -*- coding: utf-8 -*-
"""Virtual field probe driver for UI and workflow tests."""

from copy import deepcopy
import re

from scuq import si, quantities, ucomponents

from mpylab.device.fieldprobe import FIELDPROBE as FIELDPROBE_BASE
from mpylab.tools.numeric_eval import safe_numeric_eval


class FIELDPROBE(FIELDPROBE_BASE):
    """Virtual field probe backend with expression-based component synthesis."""

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
        self._last_response = ""

    def Init(self, ini=None, channel=None):
        """Initialize virtual channel expressions and enable virtual mode."""
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
        """Return virtual instrument identification."""
        return 0, self.IDN

    def SetFreq(self, freq):
        """Set virtual operating frequency in Hz."""
        self.freq = float(freq)
        return 0, self.freq

    def GetFreq(self):
        """Return virtual operating frequency in Hz."""
        return 0, self.freq

    def Trigger(self):
        """Trigger acquisition (no-op in virtual mode)."""
        return 0, 0

    def Zero(self, state):
        """Set virtual zero state flag to ``on`` or ``off``."""
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
        """Return synthetic three-axis field data as quantities."""
        return 0, [
            self._component(self.x_expr),
            self._component(self.y_expr),
            self._component(self.z_expr),
        ]

    def GetDataNB(self, retrigger=False):
        """Return data and optionally emulate retrigger behavior."""
        if retrigger:
            self.Trigger()
        return self.GetData()

    def GetBatteryState(self):
        """Return virtual battery state."""
        return 0, self.battery

    def GetWaveform(self):
        """Return unsupported marker for waveform access."""
        return -1, None, None, None, None

    def Quit(self):
        """Close virtual driver and return success."""
        return 0

    def write(self, cmd):
        """Handle a small SCPI-like command subset without a hardware bus."""
        cmd = str(cmd).strip()
        upper = cmd.upper()
        self._last_response = ""
        if upper == "*IDN?":
            self._last_response = self.IDN
        elif upper == "FREQ?":
            self._last_response = str(self.freq)
        elif upper.startswith("FREQ "):
            self.SetFreq(float(cmd.split()[1]))
        elif upper == "BATTERY?":
            self._last_response = str(self.battery)
        elif upper == "DATA?":
            _err, data = self.GetData()
            self._last_response = ",".join(str(item) for item in data)
        elif upper in {"ZERO ON", "ZERO:ON"}:
            self.Zero("on")
        elif upper in {"ZERO OFF", "ZERO:OFF"}:
            self.Zero("off")
        elif upper in {"QUIT", "*CLS"}:
            self.Quit()
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
