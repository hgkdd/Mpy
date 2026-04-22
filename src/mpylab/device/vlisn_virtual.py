# -*- coding: utf-8 -*-
"""Virtual V-LISN driver for UI and workflow tests without hardware."""

import io
import math
import re
from copy import deepcopy

from scuq import quantities, ucomponents

from mpylab.device.vlisn import VLISN as BASE_VLISN
from mpylab.tools.util import format_block


class VLISN(BASE_VLISN):
    """Synthetic V-LISN implementation using the public VLISN API."""

    conftmpl = deepcopy(BASE_VLISN.conftmpl)
    conftmpl["channel_%d"]["file"] = lambda value: value

    def __init__(self, SearchPaths=None):
        super().__init__(SearchPaths=SearchPaths)
        self.IDN = "Virtual,V-LISN,000000,1.0"
        self.freq = None
        self.path = "L"
        self.filter = False
        self.channels = ("S21",)
        self._last_response = ""
        self.conf = {
            "description": {"description": self.IDN},
            "init_value": {"virtual": True, "path": self.path, "filter": self.filter},
        }

    def Init(self, ini=None, channel=None, ignore_bus=True):
        """Initialize the virtual V-LISN from INI without opening a bus."""
        self.error = BASE_VLISN.Init(self, ini=ini, channel=channel, ignore_bus=True)
        self.conf.setdefault("init_value", {})
        self.conf["init_value"]["virtual"] = True
        self.path = str(self.conf["init_value"].get("path", self.path)).upper()
        self.filter = bool(self.conf["init_value"].get("filter", self.filter))
        self.freq = float(self.conf["init_value"].get("fstart", 9e3))
        self.channels = tuple(self.data.keys())
        if not self.channels:
            self.channels = ("S21",)
        return self.error

    def GetDescription(self):
        """Return the virtual device identification."""
        return 0, self.conf.get("description", {}).get("description", self.IDN)

    def SetVirtual(self, virtual):
        """Set virtual flag for API compatibility."""
        self.conf.setdefault("init_value", {})["virtual"] = bool(virtual)
        return 0

    def GetVirtual(self):
        """Return whether this driver is virtual."""
        return 0, True

    def SetFreq(self, freq):
        """Set and return the active interpolation frequency in Hz."""
        self.freq = float(freq)
        return 0, self.freq

    def GetFreq(self):
        """Return the active interpolation frequency in Hz."""
        return 0, self.freq

    def GetChannels(self):
        """Return available correction data names."""
        return 0, self.channels

    def SetPath(self, path):
        """Set and return the selected LISN path."""
        candidate = str(path).upper()
        aliases = {"L": "L", "L1": "L1", "L2": "L2", "L3": "L3", "N": "N"}
        if candidate not in aliases:
            raise RuntimeError("V-LISN: Path has to be in ('L', 'L1', 'L2', 'L3', 'N')")
        self.path = aliases[candidate]
        return self.GetPath()

    def GetPath(self):
        """Return the selected LISN path."""
        return 0, self.path

    def SetFilter(self, state):
        """Set and return the simulated filter state."""
        if isinstance(state, str):
            state = state.strip().lower() in {"1", "true", "yes", "on"}
        self.filter = bool(state)
        return self.GetFilter()

    def GetFilter(self):
        """Return the simulated filter state."""
        return 0, bool(self.filter)

    def GetData(self, what):
        """Return a synthetic correction value for the selected data channel."""
        if self.freq is None:
            self.freq = 9e3
        channel = self._resolve_channel(what)
        if channel is None:
            return -1, None
        if channel in self.data:
            return BASE_VLISN.GetData(self, channel)
        db_value = self._synthetic_db(channel)
        value, unit = self.convert.c2scuq("dB", db_value)
        rel_uncertainty = 0.03 + 0.01 * abs(math.sin(math.log10(max(self.freq, 1.0))))
        uncertainty = abs(value) * rel_uncertainty
        return 0, quantities.Quantity(unit, ucomponents.UncertainInput(value, uncertainty))

    def Quit(self):
        """Close the virtual V-LISN."""
        return 0

    def _resolve_channel(self, what):
        requested = str(what).lower().replace(" ", "")
        for channel in self.channels:
            if requested == str(channel).lower().replace(" ", ""):
                return channel
        return None

    def _synthetic_db(self, channel):
        freq = max(float(self.freq), 1.0)
        norm = (math.log10(freq) - math.log10(9e3)) / max(math.log10(30e6) - math.log10(9e3), 1e-9)
        path_offset = {"L": 0.0, "L1": 0.0, "L2": 0.25, "L3": -0.2, "N": 0.5}.get(self.path, 0.0)
        filter_offset = -3.0 if self.filter else 0.0
        channel_offset = (sum(ord(ch) for ch in str(channel)) % 7) * 0.1
        return -10.0 + 1.8 * norm + 0.4 * math.sin(2.0 * math.pi * norm) + path_offset + filter_offset + channel_offset

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
        elif upper == "PATH?":
            self._last_response = self.path
        elif upper.startswith("PATH "):
            self.SetPath(cmd.split()[1])
        elif upper == "FILTER?":
            self._last_response = "1" if self.filter else "0"
        elif upper.startswith("FILTER "):
            self.SetFilter(cmd.split()[1])
        elif upper == "CHANNELS?":
            self._last_response = ",".join(self.channels)
        elif upper.startswith("DATA?"):
            parts = cmd.split(maxsplit=1)
            what = parts[1] if len(parts) > 1 else self.channels[0]
            self._last_response = str(self.GetData(what))
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


if __name__ == "__main__":
    ini = io.StringIO(format_block("""
        [DESCRIPTION]
        description: Virtual V-LISN
        type: VLISN
        vendor: mpylab
        serialnr: VIRTUAL
        deviceid: vlisn_virtual
        driver: vlisn_virtual.py

        [INIT_VALUE]
        fstart: 9e3
        fstop: 30e6
        fstep: 0
        visa:
        nr_of_channels: 1
        path: L
        unit: dB
        filter: 0
        virtual: 1

        [CHANNEL_1]
        name: S21
        unit: dB
        interpolation: LOG
        file: io.StringIO(format_block('''
            FUNIT: Hz
            UNIT: dB
            RELERROR: 0
            9e3 -10
            30e6 -10
            '''))
    """))
    dev = VLISN()
    dev.Init(ini=ini)
    dev.SetFreq(1e6)
    print(dev.GetDescription())
    print(dev.GetPath())
    print(dev.GetData("S21"))
