# -*- coding: utf-8 -*-
"""Virtual signal generator driver for UI and workflow tests."""

import argparse
import io
import sys

from scuq.quantities import Quantity

from mpylab.device.signalgenerator import SIGNALGENERATOR as SIGNALGEN
from mpylab.tools.configuration import fstrcmp
from mpylab.tools.util import format_block


class SIGNALGENERATOR(SIGNALGEN):
    """In-memory signal generator implementation without hardware access."""

    def __init__(self, SearchPaths=None):
        super().__init__(SearchPaths=SearchPaths)
        self.IDN = "Virtual,SignalGenerator,000000,1.0"
        self._internal_unit = "dBm"
        self._reset_state()

    def _reset_state(self):
        """Reset simulated device state to deterministic defaults."""
        self.freq = 1e9
        self.level = -100.0
        self.unit = "dBm"
        self.rf_state = "OFF"
        self.am_state = "OFF"
        self.pm_state = "OFF"
        self.am_source = "INT1"
        self.am_freq = 1e3
        self.am_depth = 0.8
        self.am_waveform = "SINE"
        self.am_lfout = "OFF"
        self.pm_source = "INT"
        self.pm_freq = 1e3
        self.pm_pol = "NORMAL"
        self.pm_width = 100e-6
        self.pm_delay = 0.0

    def _conf_value(self, section, *keys, default=None):
        """Return a config value while tolerating different key casing."""
        section_dict = self.conf.get(section, {})
        for key in keys:
            if key in section_dict:
                return section_dict[key]
            key_lower = key.lower()
            for existing_key, value in section_dict.items():
                if str(existing_key).lower() == key_lower:
                    return value
        return default

    def Init(self, ini=None, channel=None, ignore_bus=True):
        """Initialize the virtual generator from INI without opening a bus."""
        if channel is None:
            channel = 1
        self.error = SIGNALGEN.Init(self, ini, channel, ignore_bus=True)
        self.conf.setdefault("init_value", {})
        self.conf["init_value"]["virtual"] = True
        self._reset_state()

        sec = f"channel_{channel}"
        self.levelunit = self._conf_value(sec, "unit", default=self._internal_unit)

        level = self._conf_value(sec, "level", default=self.level)
        try:
            self.level = float(level)
            self.unit = self.levelunit
        except (TypeError, ValueError):
            pass

        outputstate = self._conf_value(sec, "outputstate", "outpoutstate", default="0")
        if str(outputstate).strip().lower() in {"1", "on", "true", "yes"}:
            self.rf_state = "ON"
        else:
            self.rf_state = "OFF"
        return self.error

    def GetDescription(self):
        """Return the virtual device identification."""
        return 0, self.IDN

    def SetFreq(self, freq):
        """Set and return the simulated RF frequency."""
        self.freq = float(freq)
        return 0, self.freq

    def GetFreq(self):
        """Return the simulated RF frequency."""
        return 0, self.freq

    def SetLevel(self, lv):
        """Set and return the simulated RF level."""
        try:
            self.level = float(lv.get_value(lv._unit))
            self.unit = lv._unit
            result = lv
        except AttributeError:
            self.level = float(lv)
            self.unit = self.levelunit
            result = Quantity(self.unit, self.level)
        return 0, result

    def GetLevel(self):
        """Return the simulated RF level."""
        try:
            return 0, Quantity(self.unit, self.level)
        except AssertionError:
            value, unit = self.convert.c2scuq(self.unit, self.level)
            return 0, Quantity(unit, value)

    def SetState(self, state):
        """Set RF output state using the public signal-generator API vocabulary."""
        self.rf_state = "ON" if str(state).strip().lower() == "on" else "OFF"
        return 0, 0

    def RFOn(self):
        """Enable simulated RF output."""
        return self.SetState("ON")

    def RFOff(self):
        """Disable simulated RF output."""
        return self.SetState("OFF")

    def ConfAM(self, source, freq, depth, waveform, LFOut):
        """Configure simulated amplitude modulation parameters."""
        self.am_source = fstrcmp(source, self.AM_sources, cutoff=0, ignorecase=True)[0]
        self.am_freq = float(freq)
        self.am_depth = float(depth)
        self.am_waveform = fstrcmp(waveform, self.AM_waveforms, cutoff=0, ignorecase=True)[0]
        self.am_lfout = fstrcmp(LFOut, self.AM_LFOut, cutoff=0, ignorecase=True)[0]
        return 0

    def SetAM(self, state):
        """Set simulated AM output state."""
        self.am_state = "ON" if str(state).strip().lower() == "on" else "OFF"
        return 0, 0

    def AMOn(self):
        """Enable simulated AM."""
        return self.SetAM("ON")

    def AMOff(self):
        """Disable simulated AM."""
        return self.SetAM("OFF")

    def ConfPM(self, source, freq, pol, width, delay):
        """Configure simulated pulse modulation parameters."""
        self.pm_source = fstrcmp(source, self.PM_sources, cutoff=0, ignorecase=True)[0]
        self.pm_freq = float(freq)
        self.pm_pol = fstrcmp(pol, self.PM_pol, cutoff=0, ignorecase=True)[0]
        self.pm_width = float(width)
        self.pm_delay = float(delay)
        return 0

    def SetPM(self, state):
        """Set simulated PM output state."""
        self.pm_state = "ON" if str(state).strip().lower() == "on" else "OFF"
        return 0, 0

    def PMOn(self):
        """Enable simulated PM."""
        return self.SetPM("ON")

    def PMOff(self):
        """Disable simulated PM."""
        return self.SetPM("OFF")

    def Quit(self):
        """Safely stop all simulated outputs."""
        self.RFOff()
        self.AMOff()
        self.PMOff()
        return 0


def _default_ini():
    return io.StringIO(
        format_block("""
        [DESCRIPTION]
        description: 'Virtual Signal Generator'
        type:        'SIGNALGENERATOR'
        vendor:      'mpylab'
        serialnr:
        deviceid:
        driver:

        [Init_Value]
        fstart: 100e3
        fstop: 22e9
        fstep: 1
        gpib: 15
        virtual: 1

        [Channel_1]
        name: RFOut
        level: -100
        unit: 'dBm'
        outputstate: 0
        """)
    )


def main():
    parser = argparse.ArgumentParser(description="Run a smoke test for the virtual signal generator.")
    parser.add_argument("ini", nargs="?", help="Optional INI file.")
    args = parser.parse_args()

    if args.ini:
        with open(args.ini, "r", encoding="utf-8") as handle:
            ini = io.StringIO(handle.read())
    else:
        ini = _default_ini()

    sg = SIGNALGENERATOR()
    print("Init:", sg.Init(ini=ini, channel=1))
    print("Description:", sg.GetDescription())
    print("Freq:", sg.SetFreq(1e9), sg.GetFreq())
    print("Level:", sg.SetLevel(Quantity("dBm", -20.0)), sg.GetLevel())
    print("RF:", sg.RFOn(), sg.RFOff())
    print("AM:", sg.ConfAM("INT1", 1e3, 0.8, "SINE", "OFF"), sg.AMOn(), sg.AMOff())
    print("PM:", sg.ConfPM("INT", 1e3, "NORMAL", 100e-6, 0.0), sg.PMOn(), sg.PMOff())
    print("Quit:", sg.Quit())


if __name__ == "__main__":
    main()
