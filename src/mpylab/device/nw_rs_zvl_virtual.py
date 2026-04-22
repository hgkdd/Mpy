# -*- coding: utf-8 -*-
#
"""Virtual R&S ZVL driver used for UI and workflow testing without hardware."""

import ast
import io
import math
import re
import sys

from mpylab.device.networkanalyzer import NETWORKANALYZER as NETWORKAN
from mpylab.device.nw_rs_zvl import NETWORKANALYZER as REAL_ZVL
from mpylab.tools.spacing import linspaceN, logspaceN
from mpylab.tools.util import format_block


class NETWORKANALYZER(REAL_ZVL):
    """In-memory simulation of the ZVL driver with synthetic trace generation."""

    def __init__(self, SearchPaths=None):
        super().__init__(SearchPaths=SearchPaths)
        self.IDN = "Rohde&Schwarz,ZVL Virtual,000000,1.0"
        self._nwa_mode = "NWA"
        self._channel_enabled = False
        self._sweep_generation = 0
        self._last_response = ""
        self._virtual_reset()

    def _virtual_reset(self):
        """Reset the simulated instrument state to deterministic defaults."""
        self.center_freq = 3.05e9
        self.span = 5.9e9
        self.start_freq = self.center_freq - self.span / 2.0
        self.stop_freq = self.center_freq + self.span / 2.0
        self.rbw = 10e3
        self.reflevel = 10.0
        self.divivalue = 5.0
        self.sweepType = "LINEAR"
        self.sweepMode = "SINGLE"
        self.sweepCount = 1
        self.spoints = 401
        self.triggerMode = "IMMEDIATE"
        self.tdelay = 0.0
        self.levelunit = self._internal_unit
        self.power = (tuple(), tuple())

    def _conf_value(self, section, *keys, default=None):
        """Return one configuration value while tolerating different key casing."""
        section_dict = self.conf.get(section, {})
        for key in keys:
            if key in section_dict:
                return section_dict[key]
            lowered = key.lower()
            for existing_key, value in section_dict.items():
                if str(existing_key).lower() == lowered:
                    return value
        return default

    def _parse_ini_args(self, arg_value):
        """Parse INI arguments while accepting raw strings and already-converted values."""
        if isinstance(arg_value, tuple):
            return arg_value
        if isinstance(arg_value, list):
            return tuple(arg_value)
        if isinstance(arg_value, str):
            try:
                value = ast.literal_eval(f"({arg_value})")
            except (ValueError, SyntaxError):
                if "," in arg_value:
                    return tuple(part.strip().strip("'\"") for part in arg_value.split(","))
                return (arg_value,)
            if not isinstance(value, tuple):
                value = (value,)
            return value
        return (arg_value,)

    def _set_frequency_range(self, start=None, stop=None, center=None, span=None):
        """Keep start/stop/center/span numerically consistent after one change."""
        if start is not None and stop is not None:
            self.start_freq = float(start)
            self.stop_freq = float(stop)
            self.span = self.stop_freq - self.start_freq
            self.center_freq = self.start_freq + self.span / 2.0
            return

        if center is not None:
            self.center_freq = float(center)
        if span is not None:
            self.span = max(1.0, float(span))
        self.start_freq = self.center_freq - self.span / 2.0
        self.stop_freq = self.center_freq + self.span / 2.0

    def _trace_catalog_string(self):
        """Return the simulated trace catalog in the same format as the real driver."""
        if not self.traces:
            return ""
        entries = []
        for trace in self.traces.values():
            entries.extend([trace.getInternName(), trace.getsparameter()])
        return '"' + ",".join(entries) + '"'

    def _stimulus_values(self):
        """Build the current sweep stimulus axis."""
        if self.spoints <= 1:
            return (self.center_freq,)
        if self.sweepType == "LOGARITHMIC":
            start = max(self.start_freq, 1.0)
            stop = max(self.stop_freq, start * 1.0001)
            return tuple(logspaceN(start, stop, self.spoints, endpoint=1, precision=0))
        if self.sweepType == "SEGMENT":
            p1 = max(3, self.spoints // 4)
            p2 = max(3, self.spoints // 3)
            p3 = max(2, self.spoints - p1 - p2 + 2)
            low = tuple(linspaceN(self.start_freq, self.start_freq + 0.18 * self.span, p1, endpoint=1, precision=0))
            mid = tuple(linspaceN(self.center_freq - 0.04 * self.span, self.center_freq + 0.04 * self.span, p2, endpoint=1, precision=0))
            high = tuple(linspaceN(self.stop_freq - 0.1 * self.span, self.stop_freq, p3, endpoint=1, precision=0))
            values = low[:-1] + mid[:-1] + high
            return values[: self.spoints]
        return tuple(linspaceN(self.start_freq, self.stop_freq, self.spoints, endpoint=1, precision=0))

    def _synthetic_response(self, x_values):
        """Generate a plausible synthetic magnitude trace for the active S-parameter."""
        sparam = "S11"
        if self.activeTrace is not None:
            sparam = self.activeTrace.getsparameter()

        span = max(self.stop_freq - self.start_freq, 1.0)
        center = self.center_freq
        gen_phase = self._sweep_generation * 0.17

        if sparam == "S21":
            base = -2.0
            dip = -18.0
            ripple = 0.7
        elif sparam == "S12":
            base = -35.0
            dip = -8.0
            ripple = 0.5
        elif sparam == "S22":
            base = -11.0
            dip = -14.0
            ripple = 0.9
        else:
            base = -9.0
            dip = -16.0
            ripple = 1.0

        values = []
        for idx, x_value in enumerate(x_values):
            normalized = (x_value - center) / span
            resonance = dip * math.exp(-((normalized - 0.08) / 0.06) ** 2)
            shoulder = -5.0 * math.exp(-((normalized + 0.21) / 0.11) ** 2)
            waviness = ripple * math.sin(2.0 * math.pi * (3.0 * normalized + gen_phase))
            fine = 0.25 * math.cos(2.0 * math.pi * (idx / max(len(x_values), 2)))
            values.append(base + resonance + shoulder + waviness + fine)
        return tuple(values)

    def _run_cmd(self, key, callerdict=None):
        """Execute one simulated low-level command and mirror real-driver semantics."""
        self.error = 0
        params = callerdict or {}
        dct = {}

        if key == "SetCenterFreq":
            self._set_frequency_range(center=params["value"])
        elif key == "GetCenterFreq":
            dct = {"cfreq": self.center_freq}
        elif key == "SetSpan":
            self._set_frequency_range(span=params["value"])
        elif key == "GetSpan":
            dct = {"span": self.span}
        elif key == "SetStartFreq":
            self._set_frequency_range(start=params["value"], stop=self.stop_freq)
        elif key == "GetStartFreq":
            dct = {"stfreq": self.start_freq}
        elif key == "SetStopFreq":
            self._set_frequency_range(start=self.start_freq, stop=params["value"])
        elif key == "GetStopFreq":
            dct = {"spfreq": self.stop_freq}
        elif key == "SetRBW":
            self.rbw = float(params["value"])
        elif key == "GetRBW":
            dct = {"rbw": self.rbw}
        elif key == "SetRefLevel":
            self.reflevel = float(params["value"])
        elif key == "GetRefLevel":
            dct = {"reflevel": self.reflevel}
        elif key == "SetDivisionValue":
            self.divivalue = float(params["value"])
        elif key == "GetDivisionValue":
            dct = {"divivalue": self.divivalue}
        elif key == "SetSweepType":
            self.sweepType = str(params["value"]).upper()
        elif key == "GetSweepType":
            dct = {"sweepType": self.sweepType}
        elif key == "_SetSweepCount":
            self.sweepCount = int(params["value"])
        elif key == "GetSweepCount":
            dct = {"sweepCount": self.sweepCount}
        elif key == "NewSweepCount":
            self._sweep_generation += 1
        elif key == "SetSweepPoints":
            self.spoints = max(2, int(params["value"]))
        elif key == "GetSweepPoints":
            dct = {"spoints": self.spoints}
        elif key == "SetSweepMode":
            self.sweepMode = str(params["value"]).upper()
        elif key == "GetSweepMode":
            dct = {"sweepMode": self.sweepMode}
        elif key == "SetTriggerMode":
            self.triggerMode = str(params["value"]).upper()
        elif key == "GetTriggerMode":
            dct = {"triggerMode": self.triggerMode}
        elif key == "SetTriggerDelay":
            self.tdelay = float(params["value"])
        elif key == "GetTriggerDelay":
            dct = {"tdelay": self.tdelay}
        elif key == "_GetTraceCatalog":
            dct = {"trace_catalog": self._trace_catalog_string()}
        elif key == "_SetSparameter":
            if self.activeTrace is not None:
                self.activeTrace.sparameter = str(params["sparam"]).upper()
        elif key == "_DeleteTrace":
            pass
        elif key == "_CreateTraceDef":
            pass
        elif key == "_ActivateTrace":
            pass
        elif key == "_SelectTrace":
            pass
        elif key == "_CreateWindow":
            pass
        elif key == "_DeleteWindow":
            pass
        elif key == "CreateChannel":
            self._channel_enabled = True
        elif key == "_DeleteChannel":
            self._channel_enabled = False
        elif key == "SetNWAMode":
            self._nwa_mode = "NWA"
        elif key == "GetDescription":
            dct = {"IDN": self.IDN}
        elif key == "_GetStimulus":
            dct = {"stimulus": ",".join(f"{value:.16e}" for value in self._stimulus_values())}
        elif key == "_GetSpectrum":
            x_values = self._stimulus_values()
            y_values = self._synthetic_response(x_values)
            self.power = (x_values, y_values)
            dct = {"spectrum": ",".join(f"{value:.12f}" for value in y_values)}

        self._update(dct)
        return dct

    def GetDescription(self):
        """Return the virtual instrument identification without bus access."""
        return 0, self.IDN

    def write(self, cmd):
        """Handle a small SCPI-like command subset without a hardware bus."""
        cmd = str(cmd).strip()
        upper = cmd.upper()
        self._last_response = ""
        if upper == "*IDN?":
            self._last_response = self.IDN
        elif upper in {"FREQ:CENT?", "SENS:FREQ:CENT?", f"SENS{self.internChannel}:FREQ:CENT?"}:
            self._last_response = str(self.center_freq)
        elif upper in {"FREQ:SPAN?", "SENS:FREQ:SPAN?", f"SENS{self.internChannel}:FREQ:SPAN?"}:
            self._last_response = str(self.span)
        elif upper in {"FREQ:STAR?", "SENS:FREQ:STAR?", f"SENS{self.internChannel}:FREQ:STAR?"}:
            self._last_response = str(self.start_freq)
        elif upper in {"FREQ:STOP?", "SENS:FREQ:STOP?", f"SENS{self.internChannel}:FREQ:STOP?"}:
            self._last_response = str(self.stop_freq)
        elif upper in {"SWE:POIN?", "SENS:SWE:POIN?", f"SENS{self.internChannel}:SWE:POIN?"}:
            self._last_response = str(self.spoints)
        elif upper in {"SWE:TYPE?", "SENS:SWE:TYPE?", f"SENS{self.internChannel}:SWE:TYPE?"}:
            self._last_response = self.sweepType
        elif upper in {"INIT:CONT?", f"INIT{self.internChannel}:CONT?"}:
            self._last_response = "1" if self.sweepMode == "CONTINUOUS" else "0"
        elif upper.startswith("*RST"):
            self._virtual_reset()
        elif upper.startswith("INIT"):
            self._sweep_generation += 1
        elif upper in {"QUIT", "SYST:LOC"}:
            pass
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

    def Init(self, ini=None, channel=None):
        """Initialize the virtual analyzer from the INI file without opening any bus."""
        if channel is None:
            channel = 1
        error = NETWORKAN.Init(self, ini, channel, ignore_bus=True)
        self.conf.setdefault("init_value", {})
        self.conf["init_value"]["virtual"] = True
        self._virtual_reset()
        self.windows = {}
        self.traces = {}
        self.activeTrace = None
        self.activeWindow = None
        self.activeTrace_Name = None
        self.activeTrace_WinNum = None
        self.activeWindow_Name = None

        sec = f"channel_{channel}"
        try:
            self.levelunit = self._conf_value(sec, "unit")
        except KeyError:
            self.levelunit = self._internal_unit

        self._run_cmd("SetNWAMode")
        self._run_cmd("CreateChannel")

        create_window_args = self._conf_value(sec, "CreateWindow")
        if create_window_args is None:
            raise RuntimeError("CreateWindow must be defined in the INI")
        self._call_config_method("CreateWindow", create_window_args)
        self._call_config_method("SetWindow", create_window_args)

        create_trace_args = self._conf_value(sec, "CreateTrace")
        if create_trace_args is None:
            raise RuntimeError("CreateTrace must be defined in the INI")
        self._call_config_method("CreateTrace", create_trace_args)
        first_trace_name = self._parse_ini_args(create_trace_args)[0]
        self.SetTrace(first_trace_name)

        for func, args in list(self.conf[sec].items()):
            if str(func).lower() in ("createtrace", "createwindow", "unit"):
                continue
            try:
                self._call_config_method(func, args)
            except (AttributeError, NotImplementedError):
                pass
        return error


def main():
    """Run a small local smoke test against the virtual ZVL driver."""
    try:
        ini = sys.argv[1]
    except IndexError:
        ini = io.StringIO(
            format_block(
                """
                [DESCRIPTION]
                description: 'Virtual ZVL'
                type:        'NETWORKANALYZER'
                vendor:      'Rohde&Schwarz'
                serialnr:
                deviceid:
                driver:

                [Init_Value]
                fstart: 100e6
                fstop: 6e9
                fstep: 1
                gpib: 18
                virtual: 1

                [Channel_1]
                unit: 'dB'
                SetRefLevel: 10
                SetRBW: 10e3
                SetSpan: 5999991000
                CreateWindow: 'default'
                CreateTrace: 'default','S21'
                SetSweepCount: 1
                SetSweepPoints: 401
                SetSweepType: 'LINEAR'
                """
            )
        )
    else:
        with open(ini, "r", encoding="utf-8") as handle:
            ini = io.StringIO(handle.read())

    nw = NETWORKANALYZER()
    nw.Init(ini, channel=1)
    print(nw.GetDescription())
    print(nw.GetWindow())
    print(nw.GetTrace())
    print(nw.GetSpectrum()[1][0][:5])
    print(nw.GetSpectrum()[1][1][:5])


if __name__ == "__main__":
    main()
