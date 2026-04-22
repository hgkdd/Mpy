# -*- coding: utf-8 -*-
"""Virtual spectrum analyzer driver for UI and API tests."""

import configparser
import io
import math
import re

from mpylab.device.spectrumanalyzer import SPECTRUMANALYZER as BASE_SPECTRUMANALYZER
from mpylab.tools.configuration import parse_ini_value


class SPECTRUMANALYZER(BASE_SPECTRUMANALYZER):
    """Deterministic spectrum analyzer model with the standard driver API."""

    def __init__(self, SearchPaths=None):
        super().__init__(SearchPaths=SearchPaths)
        self._restore_virtual_api()
        self.conf = {"description": {"description": "Virtual SpectrumAnalyzer"}, "init_value": {"virtual": True}}
        self.cfreq = 3.05e9
        self.span = 5.9e9
        self.stfreq = 100e6
        self.spfreq = 6e9
        self.rbw = 10e3
        self.vbw = 10e6
        self.reflevel = -20.0
        self.att = 0.0
        self.attmode = "NORMAL"
        self.preamp = 0.0
        self.det = "AUTOPEAK"
        self.tmode = "WRITE"
        self.trace = 1
        self.scount = 0
        self.stime = 10e-3
        self.spoints = 500
        self.trgmode = "FREE"
        self.tdelay = 0.0
        self._last_response = ""

    def _restore_virtual_api(self):
        for name in (
            "SetCenterFreq", "GetCenterFreq", "SetSpan", "GetSpan",
            "SetStartFreq", "GetStartFreq", "SetStopFreq", "GetStopFreq",
            "SetRBW", "GetRBW", "SetVBW", "GetVBW",
            "SetRefLevel", "GetRefLevel", "SetAtt", "GetAtt",
            "SetAttMode", "GetAttMode", "SetPreAmp", "GetPreAmp",
            "SetDetector", "GetDetector", "SetTraceMode", "GetTraceMode",
            "SetTrace", "GetTrace", "SetSweepCount", "GetSweepCount",
            "SetSweepTime", "GetSweepTime", "SetSweepPoints", "GetSweepPoints",
            "SetTriggerMode", "GetTriggerMode", "SetTriggerDelay", "GetTriggerDelay",
        ):
            self.__dict__.pop(name, None)

    def Init(self, ini=None, channel=None, ignore_bus=True):
        text = self._read_ini(ini)
        if text:
            self._load_config(text)
        self.error = 0
        return self.error

    def _read_ini(self, ini):
        if ini is None:
            return ""
        if hasattr(ini, "read"):
            return ini.read()
        with open(ini, "r", encoding="utf-8") as handle:
            return handle.read()

    def _load_config(self, text):
        config = configparser.ConfigParser()
        config.read_file(io.StringIO(text))
        for section in config.sections():
            key = section.lower()
            values = {name.lower(): parse_ini_value(value) for name, value in config.items(section)}
            if key == "description":
                self.conf["description"] = values
            elif key == "init_value":
                self.conf["init_value"] = values
                self.conf["init_value"]["virtual"] = True
                self.stfreq = float(values.get("fstart", self.stfreq))
                self.spfreq = float(values.get("fstop", self.spfreq))
            elif key == "channel_1":
                self.reflevel = float(values.get("reflevel", self.reflevel))
                self.rbw = self._numeric_or_text(values.get("rbw", self.rbw), self.rbw)
                self.vbw = float(values.get("vbw", self.vbw))
                self.span = float(values.get("span", self.spfreq - self.stfreq))
                self.trace = int(values.get("trace", self.trace))
                self.tmode = str(values.get("tracemode", self.tmode)).upper()
                self.det = str(values.get("detector", self.det)).upper()
                self.scount = int(values.get("sweepcount", self.scount))
                self.trgmode = str(values.get("triggermode", self.trgmode)).upper()
                self.attmode = str(values.get("attmode", self.attmode)).upper()
                self.stime = float(values.get("sweeptime", self.stime))
                self.spoints = int(values.get("sweeppoints", self.spoints))
        self._update_center_span()

    def _numeric_or_text(self, value, fallback):
        try:
            return float(value)
        except (TypeError, ValueError):
            return str(value) if value is not None else fallback

    def _update_center_span(self):
        self.span = float(self.spfreq - self.stfreq)
        self.cfreq = float(self.stfreq + self.span / 2.0)

    def _set_range_from_center_span(self):
        self.stfreq = float(self.cfreq - self.span / 2.0)
        self.spfreq = float(self.cfreq + self.span / 2.0)

    def GetDescription(self):
        self.error = 0
        return self.error, self.conf.get("description", {}).get("description", "Virtual SpectrumAnalyzer")

    def GetVirtual(self):
        self.error = 0
        return self.error, True

    def SetCenterFreq(self, value):
        self.cfreq = float(value)
        self._set_range_from_center_span()
        return 0, self.cfreq

    def GetCenterFreq(self):
        return 0, self.cfreq

    def SetSpan(self, value):
        self.span = float(value)
        self._set_range_from_center_span()
        return 0, self.span

    def GetSpan(self):
        return 0, self.span

    def SetStartFreq(self, value):
        self.stfreq = float(value)
        self._update_center_span()
        return 0, self.stfreq

    def GetStartFreq(self):
        return 0, self.stfreq

    def SetStopFreq(self, value):
        self.spfreq = float(value)
        self._update_center_span()
        return 0, self.spfreq

    def GetStopFreq(self):
        return 0, self.spfreq

    def SetRBW(self, value):
        self.rbw = self._numeric_or_text(value, self.rbw)
        return 0, self.rbw

    def GetRBW(self):
        return 0, self.rbw

    def SetVBW(self, value):
        self.vbw = float(value)
        return 0, self.vbw

    def GetVBW(self):
        return 0, self.vbw

    def SetRefLevel(self, value):
        self.reflevel = float(value)
        return 0, self.reflevel

    def GetRefLevel(self):
        return 0, self.reflevel

    def SetAtt(self, value):
        self.att = self._numeric_or_text(value, self.att)
        return 0, self.att

    def GetAtt(self):
        return 0, self.att

    def SetAttAuto(self):
        self.att = "auto"
        return 0, self.att

    def SetAttMode(self, value):
        self.attmode = str(value).upper()
        return 0, self.attmode

    def GetAttMode(self):
        return 0, self.attmode

    def SetPreAmp(self, value):
        self.preamp = float(value)
        return 0, self.preamp

    def GetPreAmp(self):
        return 0, self.preamp

    def SetDetector(self, value):
        self.det = str(value).upper()
        return 0, self.det

    def GetDetector(self):
        return 0, self.det

    def SetTraceMode(self, value):
        self.tmode = str(value).upper()
        return 0, self.tmode

    def GetTraceMode(self):
        return 0, self.tmode

    def SetTrace(self, value):
        self.trace = int(value)
        return 0, self.trace

    def GetTrace(self):
        return 0, self.trace

    def SetSweepCount(self, value):
        self.scount = int(value)
        return 0, self.scount

    def GetSweepCount(self):
        return 0, self.scount

    def SetSweepTime(self, value):
        self.stime = float(value)
        return 0, self.stime

    def GetSweepTime(self):
        return 0, self.stime

    def SetSweepPoints(self, value):
        self.spoints = max(2, int(value))
        return 0, self.spoints

    def GetSweepPoints(self):
        return 0, self.spoints

    def SetTriggerMode(self, value):
        self.trgmode = str(value).upper()
        return 0, self.trgmode

    def GetTriggerMode(self):
        return 0, self.trgmode

    def SetTriggerDelay(self, value):
        self.tdelay = float(value)
        return 0, self.tdelay

    def GetTriggerDelay(self):
        return 0, self.tdelay

    def GetSpectrum(self):
        x = []
        y = []
        points = max(2, int(self.spoints))
        stop = self.spfreq
        start = self.stfreq
        for idx in range(points):
            frac = idx / (points - 1)
            freq = start + (stop - start) * frac
            carrier = -15.0 * math.exp(-((freq - self.cfreq) / max(self.span / 12.0, 1.0)) ** 2)
            ripple = 4.0 * math.sin(2.0 * math.pi * frac * 9.0)
            noise = 1.5 * math.sin(2.0 * math.pi * frac * 37.0)
            x.append(freq)
            y.append(self.reflevel - 55.0 + carrier + ripple + noise)
        return 0, (x, y)

    def GetSpectrumNB(self):
        return self.GetSpectrum()

    def Quit(self):
        self.error = 0
        return self.error

    def write(self, cmd):
        """Handle a small SCPI-like command subset without a hardware bus."""
        cmd = str(cmd).strip()
        upper = cmd.upper()
        self._last_response = ""
        if upper == "*IDN?":
            self._last_response = self.conf.get("description", {}).get("description", "Virtual SpectrumAnalyzer")
        elif upper == "CENTERFREQ?":
            self._last_response = f"CENTERFREQ {self.cfreq} HZ"
        elif upper.startswith("CENTERFREQ "):
            self.SetCenterFreq(float(cmd.split()[1]))
        elif upper == "SPAN?":
            self._last_response = f"SPAN {self.span} HZ"
        elif upper.startswith("SPAN "):
            self.SetSpan(float(cmd.split()[1]))
        elif upper == "RBW?":
            self._last_response = f"RBW {self.rbw} HZ"
        elif upper.startswith("RBW "):
            self.SetRBW(cmd.split()[1])
        elif upper == "VBW?":
            self._last_response = f"VBW {self.vbw} HZ"
        elif upper.startswith("VBW "):
            self.SetVBW(float(cmd.split()[1]))
        elif upper == "DATA?":
            x, y = self.GetSpectrum()[1]
            self._last_response = "DATA " + ",".join(f"{freq:g}:{amp:g}" for freq, amp in zip(x, y))
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
