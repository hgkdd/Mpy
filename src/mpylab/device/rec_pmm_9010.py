# -*- coding: utf-8 -*-
"""PMM 9010 receiver driver (chapter 14 remote protocol)."""

import re

import numpy as np
from scuq.quantities import Quantity
from scuq.si import VOLT, WATT
from scuq.ucomponents import UncertainInput

from mpylab.device.receiver import RECEIVER as REC
from mpylab.tools.util import case_insensitive_string_compare, format_block


class RECEIVER(REC):
    """Concrete PMM 9010 receiver driver."""

    _RBW_TO_ID = {
        300e3: 1,
        100e3: 2,
        30e3: 3,
        10e3: 4,
        3e3: 5,
        9e3: 6,
        200: 7,
        1e3: 22,
        100: 23,
        10: 24,
        1e6: 9,
        120e3: 10,
    }
    _ID_TO_RBW = {v: k for k, v in _RBW_TO_ID.items()}

    _DET_IDX = {
        "peak": 0,
        "qpeak": 1,
        "quasipeak": 1,
        "rms": 2,
        "average": 3,
        "avg": 3,
        "c-rms": 4,
        "crms": 4,
        "c-average": 5,
        "cavg": 5,
    }

    def __init__(self, **kw):
        super().__init__(**kw)
        self.error = 0
        self.min_attenuation = 10
        self.detector = "peak"
        self.delay = 0.1

    def _frame(self, payload):
        payload = str(payload).strip()
        return f"#{payload}*"

    def _send(self, payload):
        return self.write(self._frame(payload))

    def _ask(self, payload):
        ans = self.query(self._frame(payload), None)
        if isinstance(ans, bytes):
            ans = ans.decode(errors="ignore")
        return str(ans or "").strip()

    @staticmethod
    def _first_float(text):
        m = re.search(r"[-+]?\d+(\.\d+)?([eE][-+]?\d+)?", str(text))
        if not m:
            raise ValueError(f"No float in reply: {text!r}")
        return float(m.group(0))

    @staticmethod
    def _is_on(value):
        return str(value).strip().lower() in {"1", "on", "true"}

    def Init(self, ini=None, channel=None):
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

        self._internal_unit = "dBuV"

        self.error, self.min_attenuation = self.SetMinAttenuation(self.conf[sec]["min_attenuation"])
        self.error, self.detector = self.SetDetector(self.conf[sec]["detector"])
        self.error, self.rbw = self.SetResolutionBandwidth(self.conf[sec]["rbw"])
        self.error, self.meas_time = self.SetMeasTime(self.conf[sec]["meas_time"])
        self.error, self.preamplifier = self.SetPreamplifier(self.conf[sec]["preamplifier"])
        self.error, self.attenuation = self.SetAttenuation(self.conf[sec]["attenuation"])
        return self.error

    def _convert_level_to_unit(self, lev, z0=50.0):
        if self._internal_unit == "dBm":
            if self.unit is WATT:
                return np.power(10.0, 0.1 * lev) * 1e-3
            if self.unit is VOLT:
                return np.power(10.0, 0.05 * (lev + 90.0 + 10.0 * np.log10(z0))) * 1e-6
        elif self._internal_unit == "dBuV":
            if self.unit is WATT:
                return np.power(10.0, 0.1 * (lev - 90.0 - 10.0 * np.log10(z0))) * 1e-3
            if self.unit is VOLT:
                return np.power(10.0, 0.05 * lev) * 1e-6
        raise RuntimeError(f"Unrecognized unit conversion: {self._internal_unit} -> {self.unit}")

    def _create_lev_object(self, level):
        level = self._convert_level_to_unit(float(level))
        relerr = 0.122 if self.unit is WATT else 0.059
        return Quantity(self.unit, UncertainInput(level, level * relerr))

    def SetFreq(self, freq):
        self.error = 0
        self._send(f"SMAF {freq}")
        return self.GetFreq()

    def GetFreq(self):
        self.error = 0
        ans = self._ask("?MAF")
        self.freq = self._first_float(ans)
        return self.error, self.freq

    def Trigger(self):
        self.error = 0
        return self.error

    def SetAttenuation(self, attenuation):
        self.error = 0
        if attenuation is None or case_insensitive_string_compare(attenuation, "auto"):
            self._send("SMAT -1")
        else:
            a = max(float(attenuation), float(self.min_attenuation))
            a = int(round(a / 5.0) * 5)
            self._send(f"SMAT {a}")
        return self.GetAttenuation()

    def GetAttenuation(self):
        self.error = 0
        ans = self._ask("?MAT")
        self.attenuation = self._first_float(ans)
        return self.error, self.attenuation

    def SetMinAttenuation(self, min_attenuation):
        self.error = 0
        self.min_attenuation = max(int(round(float(min_attenuation) / 5.0) * 5), 0)
        self._send(f"STAT {self.min_attenuation}")
        return self.GetMinAttenuation()

    def GetMinAttenuation(self):
        self.error = 0
        ans = self._ask("?TAT")
        self.min_attenuation = int(round(self._first_float(ans)))
        return self.error, self.min_attenuation

    def SetMeasTime(self, meas_time):
        self.error = 0
        if meas_time is None or case_insensitive_string_compare(meas_time, "auto"):
            self.meas_time = 1.0
            return self.error, self.meas_time
        ms = float(meas_time) * 1e3
        self._send(f"SMHT {ms}")
        return self.GetMeasTime()

    def GetMeasTime(self):
        self.error = 0
        ans = self._ask("?MHT")
        self.meas_time = self._first_float(ans) * 1e-3
        return self.error, self.meas_time

    def SetDetector(self, detector):
        self.error = 0
        det = str(detector).strip().lower()
        self.detector = det if det in self._DET_IDX else "peak"
        return self.error, self.detector

    def GetDetector(self):
        self.error = 0
        return self.error, self.detector

    def SetPreamplifier(self, preamplifier):
        self.error = 0
        state = "ON" if self._is_on(preamplifier) else "OFF"
        self._send(f"SMPA {state}")
        return self.GetPreamplifier()

    def GetPreamplifier(self):
        self.error = 0
        ans = self._ask("?MPA").upper()
        self.preamplifier = "ON" if "ON" in ans else "OFF"
        return self.error, self.preamplifier

    def SetResolutionBandwidth(self, rbw):
        self.error = 0
        if rbw is None or case_insensitive_string_compare(rbw, "auto"):
            self._send("SRBW 0")
            self.rbw = "auto"
            return self.error, self.rbw
        rbw = float(rbw)
        key = min(self._RBW_TO_ID.keys(), key=lambda x: abs(x - rbw))
        self._send(f"SRBW {self._RBW_TO_ID[key]}")
        return self.GetResolutionBandwidth()

    def GetResolutionBandwidth(self):
        self.error = 0
        ans = self._ask("?RBW")
        m = re.search(r"\b(\d+)\b", ans)
        if m:
            idx = int(m.group(1))
            self.rbw = self._ID_TO_RBW.get(idx, self.rbw)
        return self.error, self.rbw

    def _extract_level_from_det(self, ans):
        if "=" in ans:
            ans = ans.split("=", 1)[1]
        fields = [f.strip() for f in ans.replace(",", ";").split(";") if f.strip()]
        idx = self._DET_IDX.get(self.detector, 0)
        if idx >= len(fields):
            return None
        token = fields[idx]
        if "-" in token and not re.search(r"\d", token):
            return None
        try:
            return self._first_float(token)
        except ValueError:
            return None

    def GetData(self):
        self.error = 0
        ans = self._ask("?DET")
        level = self._extract_level_from_det(ans)
        if level is None:
            self.error = -1
            return self.error, None
        return self.error, self._create_lev_object(level)

    def GetDataNB(self, retrigger):
        return self.GetData()

    def GetDescription(self):
        self.error = 0
        self.IDN = self._ask("?IDN")
        return self.error, self.IDN

    def Quit(self):
        self.error = 0
        return self.error


def main():
    import sys

    try:
        ini = sys.argv[1]
    except IndexError:
        ini = format_block("""
                        [DESCRIPTION]
                        description: 'PMM 9010'
                        type:        'RECEIVER'
                        vendor:      'PMM'
                        serialnr:
                        deviceid:
                        driver: rec_pmm_9010.py

                        [Init_Value]
                        fstart: 10
                        fstop: 30e6
                        fstep: 1
                        visa: TCPIP::192.168.88.253::INSTR
                        virtual: 0

                        [Channel_1]
                        name: OUT
                        detector: PEAK
                        attenuation: auto
                        meas_time: auto
                        min_attenuation: 10
                        rbw: auto
                        preamplifier: off
                        unit: Volt
                        """)

    rec = RECEIVER()
    print(f"Init: {rec.Init(ini=ini, channel=1)}")
    print(f"Description: {rec.GetDescription()}")
    print(f"Freq set/get: {rec.SetFreq(1e6)} / {rec.GetFreq()}")
    print(f"Data: {rec.GetData()}")


if __name__ == "__main__":
    main()
