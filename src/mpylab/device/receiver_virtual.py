# -*- coding: utf-8 -*-
"""Virtual EMC receiver driver for UI and workflow tests without hardware."""

import io
import math
import re

from scuq import quantities, ucomponents, units

from mpylab.device.receiver import RECEIVER as RECEIVER_BASE
from mpylab.tools.util import format_block


class RECEIVER(RECEIVER_BASE):
    """In-memory receiver implementation using the public receiver API."""

    def __init__(self, SearchPaths=None):
        super().__init__(SearchPaths=SearchPaths)
        self.IDN = "Virtual,Receiver,000000,1.0"
        self._last_response = ""
        self._reset_state()

    def _reset_state(self):
        """Reset simulated receiver state to deterministic defaults."""
        self.freq = 1e6
        self.attenuation = 10.0
        self.min_attenuation = 10.0
        self.meas_time = 0.05
        self.rbw = 9e3
        self.detector = "PEAK"
        self.preamplifier = "OFF"
        self.level = 42.0
        self.unit = "dBuV"
        self._internal_unit = "dBuV"

    def _conf_value(self, section, *keys, default=None):
        section_dict = self.conf.get(section, {})
        for key in keys:
            if key in section_dict:
                return section_dict[key]
            lowered = key.lower()
            for existing_key, value in section_dict.items():
                if str(existing_key).lower() == lowered:
                    return value
        return default

    def Init(self, ini=None, channel=None, ignore_bus=True):
        """Initialize the virtual receiver from INI without opening a bus."""
        if channel is None:
            channel = 1
        self.error = RECEIVER_BASE.Init(self, ini, channel, ignore_bus=True)
        self.conf.setdefault("init_value", {})
        self.conf["init_value"]["virtual"] = True
        self._reset_state()

        sec = f"channel_{channel}"
        self.unit = self._conf_value(sec, "unit", default=self.unit)
        self._internal_unit = self.unit
        self.detector = str(self._conf_value(sec, "detector", default=self.detector)).upper()
        self.preamplifier = str(self._conf_value(sec, "preamplifier", default=self.preamplifier)).upper()
        self.meas_time = self._numeric_or_default(self._conf_value(sec, "meas_time", default=self.meas_time), self.meas_time)
        self.min_attenuation = self._numeric_or_default(
            self._conf_value(sec, "min_attenuation", default=self.min_attenuation),
            self.min_attenuation,
        )
        self.SetAttenuation(self._conf_value(sec, "attenuation", default=self.attenuation))
        self.SetResolutionBandwidth(self._conf_value(sec, "rbw", default=self.rbw))
        return self.error

    def _numeric_or_default(self, value, default):
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    def _synthetic_level(self):
        freq = max(float(self.freq or 1.0), 1.0)
        ripple = 5.0 * math.sin(math.log10(freq) * math.pi)
        preamp = -10.0 if self.preamplifier == "ON" else 0.0
        detector_offset = {"PEAK": 3.0, "QPEAK": 1.5, "AVERAGE": -2.0}.get(self.detector, 0.0)
        return 38.0 + ripple + detector_offset + preamp + 0.03 * float(self.attenuation or 0.0)

    def _quantity(self):
        """Return the current level as scuq Quantity using the configured unit."""
        if isinstance(self._internal_unit, str):
            level_value, level_unit = self.convert.c2scuq(self._internal_unit, self.level)
        elif isinstance(self._internal_unit, units.Unit):
            level_value = self.level
            level_unit = self._internal_unit
        else:
            raise TypeError(f"_internal_unit must be str or scuq Unit, got {type(self._internal_unit).__name__}")
        return quantities.Quantity(level_unit, ucomponents.UncertainInput(level_value, 0.25))

    def GetDescription(self):
        """Return the virtual device identification."""
        return 0, self.IDN

    def GetVirtual(self):
        """Return whether this driver is virtual."""
        return 0, True

    def SetFreq(self, freq):
        """Set and return the simulated receiver frequency in Hz."""
        self.freq = float(freq)
        return 0, self.freq

    def GetFreq(self):
        """Return the simulated receiver frequency in Hz."""
        return 0, self.freq

    def Trigger(self):
        """Trigger one synthetic measurement update."""
        self.level = self._synthetic_level()
        return 0

    def GetData(self):
        """Return one synthetic receiver reading."""
        self.Trigger()
        return 0, self._quantity()

    def GetDataNB(self, retrigger=True):
        """Return the latest synthetic reading and optionally retrigger."""
        if retrigger:
            self.Trigger()
        return 0, self._quantity()

    def SetAttenuation(self, attenuation):
        """Set fixed attenuation or accept automatic attenuation."""
        if attenuation is None or str(attenuation).strip().lower() == "auto":
            self.attenuation = self.min_attenuation
        else:
            self.attenuation = max(float(attenuation), float(self.min_attenuation))
        return 0, self.attenuation

    def GetAttenuation(self):
        """Return simulated attenuation in dB."""
        return 0, self.attenuation

    def SetMinAttenuation(self, min_attenuation):
        """Set and return simulated minimum attenuation in dB."""
        self.min_attenuation = max(float(min_attenuation), 0.0)
        self.attenuation = max(float(self.attenuation), self.min_attenuation)
        return 0, self.min_attenuation

    def GetMinAttenuation(self):
        """Return simulated minimum attenuation in dB."""
        return 0, self.min_attenuation

    def SetMeasTime(self, meas_time):
        """Set and return simulated measurement time in seconds."""
        self.meas_time = max(float(meas_time), 0.0)
        return 0, self.meas_time

    def GetMeasTime(self):
        """Return simulated measurement time in seconds."""
        return 0, self.meas_time

    def SetDetector(self, detector):
        """Set and return simulated detector mode."""
        detector = str(detector).upper()
        if detector not in ("PEAK", "QPEAK", "AVERAGE"):
            raise UserWarning(f"Invalid detector {detector}.")
        self.detector = detector
        return 0, self.detector

    def GetDetector(self):
        """Return simulated detector mode."""
        return 0, self.detector

    def SetPreamplifier(self, preamplifier):
        """Set and return simulated preamplifier state."""
        preamplifier = str(preamplifier).upper()
        if preamplifier not in ("ON", "OFF"):
            raise UserWarning(f"Invalid preamplifier state {preamplifier}.")
        self.preamplifier = preamplifier
        return 0, self.preamplifier

    def GetPreamplifier(self):
        """Return simulated preamplifier state."""
        return 0, self.preamplifier

    def SetResolutionBandwidth(self, rbw):
        """Set fixed RBW or accept automatic RBW."""
        if rbw is None or str(rbw).strip().lower() == "auto":
            self.rbw = 9e3
        else:
            self.rbw = max(float(rbw), 1.0)
        return 0, self.rbw

    def GetResolutionBandwidth(self):
        """Return simulated resolution bandwidth in Hz."""
        return 0, self.rbw

    def Quit(self):
        """Close the virtual receiver."""
        return 0

    def write(self, cmd):
        """Handle a small SCPI-like command subset without a hardware bus."""
        cmd = str(cmd).strip()
        upper = cmd.upper()
        self._last_response = ""
        if upper == "*IDN?":
            self._last_response = self.IDN
        elif upper == "FREQUENCY?":
            self._last_response = f"FREQUENCY {self.freq}"
        elif upper.startswith("FREQUENCY "):
            self.freq = float(cmd.split()[1])
        elif upper in {"LEVEL?", "LEVEL:LASTVALUE?"}:
            self._last_response = f"LEVEL {self._synthetic_level()}"
        elif upper == "BANDWIDTH:IF?":
            self._last_response = f"BANDWIDTH:IF {self.rbw}"
        elif upper == "ATTENUATION?":
            self._last_response = f"ATTENUATION {self.attenuation}"
        elif upper == "DETECTOR?":
            self._last_response = f"DETECTOR {self.detector}"
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


if __name__ == "__main__":
    ini = io.StringIO(format_block("""
        [DESCRIPTION]
        description: Virtual Receiver
        type: RECEIVER
        vendor: mpylab
        serialnr: VIRTUAL
        deviceid: receiver_virtual
        driver: receiver_virtual.py

        [Init_Value]
        fstart: 9e3
        fstop: 30e6
        fstep: 1
        visa:
        virtual: 1
        nr_of_channels: 1

        [Channel_1]
        name: RFIn
        min_attenuation: 10
        meas_time: 0.05
        preamplifier: off
        unit: dBuV
        attenuation: auto
        rbw: auto
        detector: PEAK
    """))
    rx = RECEIVER()
    rx.Init(ini=ini, channel=1)
    print(rx.GetDescription())
    print(rx.SetFreq(1e6))
    print(rx.GetData())
