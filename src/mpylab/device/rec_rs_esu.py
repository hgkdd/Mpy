# -*- coding: utf-8 -*-
"""This is :mod:`mpylab.device.rec_rs_esu`.

   Provides driver for Rohde&Schwarz ESU EMI receiver family.
   :author: Hans Georg Krauthaeuser (main author)

   :license: GPL-3 or higher
"""
import io
import numpy as np

from scuq.quantities import Quantity
from scuq.si import VOLT, WATT
from scuq.ucomponents import UncertainInput

from mpylab.device.receiver import RECEIVER as REC
from mpylab.tools.util import case_insensitive_string_compare


class RECEIVER(REC):
    """Concrete R&S ESU receiver driver based on the generic RECEIVER API."""

    def __init__(self, **kw):
        super().__init__(**kw)
        self._cmds = {
            "SetFreq": [("FREQ:CENT {freq} HZ", None)],
            "GetFreq": [("FREQ:CENT?", rf"(?P<freq>{self._FP})")],
            "GetData": [("TRAC? SING", r"(?P<level>[-+0-9eE., ]+)")],
            "GetDataNB": [("TRAC? SING", r"(?P<level>[-+0-9eE., ]+)")],
            "Trigger": [("INIT;*WAI", None)],
            "SetAttenuation": [("INP:ATT:AUTO OFF", None), ("INP:ATT {attenuation} DB", None)],
            "GetAttenuation": [("INP:ATT?", rf"(?P<attenuation>{self._FP})")],
            "SetMeasTime": [("SWE:TIME {meas_time} s", None)],
            "GetMeasTime": [("SWE:TIME?", rf"(?P<meas_time>{self._FP})")],
            "SetDetector": [("DET:REC {detector}", None)],
            "SetPreamplifier": [("INP:GAIN:STAT {preamplifier}", None)],
            "GetPreamplifier": [("INP:GAIN:STAT?", r"(?P<preamplifier>.*)")],
            "SetResolutionBandwidth": [("BAND:AUTO OFF", None), ("BAND {rbw} HZ", None)],
            "GetResolutionBandwidth": [("BAND?", rf"(?P<rbw>{self._FP})")],
            "Quit": [("*CLS", None)],
            "GetDescription": [("*IDN?", r"(?P<IDN>.*)")],
        }
        self.error = 0
        self.min_attenuation = 10
        self.detector_map = {
            "peak": "POS",
            "maxpeak": "POS",
            "minpeak": "NEG",
            "qpeak": "QPE",
            "average": "AVER",
            "caverage": "CAV",
            "rms": "RMS",
            "crms": "CRMS",
        }
        self.send_opc = False
        self.delay = 0.1

    def Init(self, ini=None, channel=None):
        """Initialize receiver state and apply configuration for one channel."""
        if channel is None:
            channel = 1
        self.error = super().Init(ini=ini, channel=channel)

        sec = f"channel_{channel}"
        try:
            self.unit = self.conf[sec]["unit"]
            if case_insensitive_string_compare(self.unit, "Watt"):
                self.unit = WATT
            elif case_insensitive_string_compare(self.unit, "Volt"):
                self.unit = VOLT
            else:
                raise RuntimeError(f"Unrecognized unit: {self.unit}")
        except KeyError:
            self.unit = VOLT

        self.write("*CLS")
        self.write("*RST")
        self.write("INST:SEL REC")
        self.write("INIT:CONT OFF")
        # Keep a deterministic receiver output unit and convert from it.
        self.write("CALC:UNIT:POW DBUV")
        self._internal_unit = "dBuV"
        self.error, self.min_attenuation = self.SetMinAttenuation(self.conf[sec]["min_attenuation"])
        self.error, self.detector = self.SetDetector(self.conf[sec]["detector"])
        self.error, self.rbw = self.SetResolutionBandwidth(self.conf[sec]["rbw"])
        self.error, self.meas_time = self.SetMeasTime(self.conf[sec]["meas_time"])
        self.error, self.preamplifier = self.SetPreamplifier(self.conf[sec]["preamplifier"])
        self.error, self.attenuation = self.SetAttenuation(self.conf[sec]["attenuation"])
        return self.error

    def _get_db_from_obj(self, obj, Z=50):
        value = obj.get_expectation_value_as_float()
        dBval = None
        unit = obj._unit
        if unit is VOLT:
            if case_insensitive_string_compare(self._internal_unit, "dBuV"):
                dBval = 20 * np.log10(value * 1e6)
            elif case_insensitive_string_compare(self._internal_unit, "dBm"):
                mW = value * value / Z * 1e3
                dBval = 10 * np.log10(mW)
            else:
                raise RuntimeError(f"Unrecognized unit: {self._internal_unit}")
        elif unit is WATT:
            if case_insensitive_string_compare(self._internal_unit, "dBuV"):
                uV = np.sqrt(value * Z) * 1e6
                dBval = 20 * np.log10(uV)
            elif case_insensitive_string_compare(self._internal_unit, "dBm"):
                dBval = 10 * np.log10(value * 1e3)
            else:
                raise RuntimeError(f"Unrecognized unit: {self._internal_unit}")
        else:
            raise RuntimeError(f"Unrecognized unit: {self.unit}")
        return dBval

    def _convert_level_to_unit(self, lev, Z=50):
        if self._internal_unit == "dBm":
            if self.unit is WATT:
                lev = np.power(10, 0.1 * lev) * 1e-3
            elif self.unit is VOLT:
                lev = lev + 90 + 10 * np.log10(Z)
                lev = np.power(10, 0.05 * lev) * 1e-6
            else:
                raise RuntimeError(f"Unrecognized unit: {self.unit}")
        elif self._internal_unit == "dBuV":
            if self.unit is WATT:
                lev = lev - 90 - 10 * np.log10(Z)
                lev = np.power(10, 0.1 * lev) * 1e-3
            elif self.unit is VOLT:
                lev = np.power(10, 0.05 * lev) * 1e-6
            else:
                raise RuntimeError(f"Unrecognized unit: {self.unit}")
        else:
            raise RuntimeError(f"Unrecognized internal unit: {self._internal_unit}")
        return lev

    def _create_lev_object(self, level):
        level = float(level)
        level = self._convert_level_to_unit(level)
        relerr = 0.122 if self.unit == WATT else 0.059
        return Quantity(self.unit, UncertainInput(level, level * relerr))

    def SetPreamplifier(self, preamplifier):
        """Set preamplifier state and return the applied value."""
        self.error = 0
        dct = self._do_cmds("SetPreamplifier", locals())
        self._update(dct)
        dct = self._do_cmds("GetPreamplifier", locals())
        self._update(dct)
        return self.error, self.preamplifier

    def GetPreamplifier(self):
        """Return the current preamplifier state."""
        self.error = 0
        dct = self._do_cmds("GetPreamplifier", locals())
        self._update(dct)
        return self.error, self.preamplifier

    def SetDetector(self, detector):
        """Set detector mode and return the resulting detector token."""
        self.error = 0
        detector = self.detector_map[str(detector).lower()]
        dct = self._do_cmds("SetDetector", locals())
        self._update(dct)
        self.detector = detector
        return self.error, self.detector

    def GetDetector(self):
        """Return the currently selected detector token."""
        self.error = 0
        if self.detector is None:
            self.detector = "POS"
        return self.error, self.detector

    def SetMeasTime(self, meas_time):
        """Set sweep time or keep automatic timing when requested."""
        self.error = 0
        if meas_time is None or case_insensitive_string_compare(meas_time, "auto"):
            self.meas_time = 0.1
        else:
            dct = self._do_cmds("SetMeasTime", locals())
            self._update(dct)
            dct = self._do_cmds("GetMeasTime", locals())
            self._update(dct)
        return self.error, self.meas_time

    def GetMeasTime(self):
        """Return the configured sweep time."""
        self.error = 0
        dct = self._do_cmds("GetMeasTime", locals())
        self._update(dct)
        return self.error, self.meas_time

    def SetResolutionBandwidth(self, rbw):
        """Set resolution bandwidth or enable automatic bandwidth."""
        self.error = 0
        if rbw is None or case_insensitive_string_compare(rbw, "auto"):
            self.write("BAND:AUTO ON")
        else:
            dct = self._do_cmds("SetResolutionBandwidth", locals())
            self._update(dct)
        dct = self._do_cmds("GetResolutionBandwidth", locals())
        self._update(dct)
        return self.error, self.rbw

    def SetAttenuation(self, attenuation):
        """Set input attenuation and return the effective value in dB."""
        self.error = 0
        if attenuation is None or case_insensitive_string_compare(attenuation, "auto"):
            self.write("INP:ATT:AUTO ON")
        else:
            attenuation = int(np.ceil(float(attenuation) / 10.0)) * 10
            attenuation = int(max(self.min_attenuation, attenuation))
            dct = self._do_cmds("SetAttenuation", locals())
            self._update(dct)
        dct = self._do_cmds("GetAttenuation", locals())
        self._update(dct)
        self.attenuation = float(self.attenuation)
        return self.error, self.attenuation

    def GetData(self):
        """Trigger one measurement and return it as a quantity object."""
        self.error = 0
        self.Trigger()
        dct = self._do_cmds("GetData", locals())
        self._update(dct)
        if isinstance(self.level, str) and "," in self.level:
            self.level = self.level.split(",", 1)[0].strip()
        if self.level is None or self.level == "":
            self.error = -1
            return self.error, None
        obj = self._create_lev_object(self.level)
        return self.error, obj

    def GetDataNB(self, retrigger):
        """Return a non-blocking measurement and optionally retrigger."""
        obj = None
        self.error = 0
        dct = self._do_cmds("GetDataNB", locals())
        self._update(dct)
        if self.level:
            if self.level == "0.00":
                self.level = None
                self.error = -1
                return self.error, None
            obj = self._create_lev_object(self.level)
            if retrigger is True or case_insensitive_string_compare(retrigger, "on"):
                self.Trigger()
        return self.error, obj

    def SetMinAttenuation(self, att):
        """Set minimum attenuation floor and enforce it on current settings."""
        self.min_attenuation = max(att, 0)
        if self.attenuation is None or self.min_attenuation > self.attenuation:
            self.error, self.attenuation = self.SetAttenuation(self.min_attenuation)
        return 0, self.min_attenuation

    def GetMinAttenuation(self):
        """Return the configured minimum attenuation floor in dB."""
        return 0, self.min_attenuation


def main():
    """Run a simple manual smoke test for the ESU receiver driver."""
    import sys
    from mpylab.tools.util import format_block

    try:
        ini = sys.argv[1]
    except IndexError:
        ini = format_block("""
                        [DESCRIPTION]
                        description: 'R&S ESU'
                        type:        'RECEIVER'
                        vendor:      'Rohde&Schwarz'
                        serialnr:
                        deviceid:
                        driver: rec_rs_esu.py

                        [Init_Value]
                        fstart: 20
                        fstop: 26.5e9
                        fstep: 1
                        visa: TCPIP::192.168.88.253::INSTR
                        virtual: 0

                        [Channel_1]
                        name: RFin
                        min_attenuation: 10
                        meas_time: 0.05
                        preamplifier: on
                        unit: Watt
                        attenuation: auto
                        rbw: auto
                        detector: PEAK
                        """)
        ini = io.StringIO(ini)

    rec = RECEIVER()
    rec.Init(ini=ini, channel=1)

    err, des = rec.GetDescription()
    print(f"Description: {des}")
    for freq in [9e3, 100e3, 500e3, 1e6, 10e6, 30e6]:
        print(f"Set freq to {freq} Hz")
        err, returned_freq = rec.SetFreq(freq)
        err, dat = rec.GetData()
        print(f"Freq {returned_freq} Hz, Level: {dat} --> {rec._get_db_from_obj(dat)} {rec._internal_unit}")
    rec.Quit()


if __name__ == "__main__":
    main()
