# -*- coding: utf-8 -*-
"""PMM 9010 spectrum analyzer driver (chapter 14 remote protocol)."""

import re
import struct
from copy import deepcopy

from numpy import linspace

from mpylab.device.spectrumanalyzer import SPECTRUMANALYZER as SPECTRUMAN


def _number_or_auto(value):
    if isinstance(value, str) and value.strip().lower() == "auto":
        return "auto"
    return float(value)


class SPECTRUMANALYZER(SPECTRUMAN):
    """Concrete PMM 9010 analyzer driver."""

    conftmpl = deepcopy(SPECTRUMAN.conftmpl)
    conftmpl["init_value"]["visa"] = str
    if "gpib" in conftmpl["init_value"]:
        del conftmpl["init_value"]["gpib"]
    conftmpl["channel_%d"]["rbw"] = _number_or_auto
    conftmpl["channel_%d"]["vbw"] = _number_or_auto
    conftmpl["channel_%d"]["sweeptime"] = _number_or_auto
    conftmpl["channel_%d"]["attenuation"] = _number_or_auto

    _DET_TO_ID = {"MAXPEAK": 1, "AUTOPEAK": 1, "AVERAGE": 2, "RMS": 3}
    _ID_TO_DET = {1: "MAXPEAK", 2: "AVERAGE", 3: "RMS"}

    def __init__(self, **kw):
        super().__init__(**kw)
        self.IDN = "PMM,9019,000000,1.0"
        self._internal_unit = "dBm"
        self.detector = "MAXPEAK"
        self.trace = 1
        self.attmode = "LOWNOISE"
        self.tdelay = 0.0

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
        self.error = super().Init(ini, channel)
        sec = f"channel_{channel}"
        self.levelunit = self.conf[sec].get("unit", self._internal_unit)

        self.SetAtt(self.conf[sec].get("attenuation", "auto"))
        self.SetRefLevel(self.conf[sec].get("reflevel", 100.0))
        self.SetStartFreq(self.conf["init_value"]["fstart"])
        self.SetStopFreq(self.conf["init_value"]["fstop"])
        self.SetDetector(self.conf[sec].get("detector", "MAXPEAK"))
        self.SetSweepTime(self.conf[sec].get("sweeptime", "auto"))
        self.SetPreAmp(self.conf[sec].get("preamp", 0))
        return self.error

    def SetStartFreq(self, something):
        self.error = 0
        self._send(f"SART {something}")
        return self.GetStartFreq()

    def GetStartFreq(self):
        self.error = 0
        self.stfreq = self._first_float(self._ask("?ART"))
        return self.error, self.stfreq

    def SetStopFreq(self, something):
        self.error = 0
        self._send(f"SAOP {something}")
        return self.GetStopFreq()

    def GetStopFreq(self):
        self.error = 0
        self.spfreq = self._first_float(self._ask("?AOP"))
        return self.error, self.spfreq

    def SetCenterFreq(self, something):
        self.error = 0
        span = self.GetSpan()[1]
        start = float(something) - 0.5 * span
        stop = float(something) + 0.5 * span
        self._send(f"SAFF {start},{stop}")
        return self.GetCenterFreq()

    def GetCenterFreq(self):
        self.error = 0
        self.cfreq = self._first_float(self._ask("?ACE"))
        return self.error, self.cfreq

    def SetSpan(self, something):
        self.error = 0
        center = self.GetCenterFreq()[1]
        start = center - 0.5 * float(something)
        stop = center + 0.5 * float(something)
        self._send(f"SAFF {start},{stop}")
        return self.GetSpan()

    def GetSpan(self):
        self.error = 0
        self.span = self._first_float(self._ask("?ASP"))
        return self.error, self.span

    def SetAtt(self, something):
        self.error = 0
        if isinstance(something, str) and something.strip().lower() == "auto":
            self._send("SAAT -1")
        else:
            self._send(f"SAAT {float(something)}")
        return self.GetAtt()

    def GetAtt(self):
        self.error = 0
        self.att = self._first_float(self._ask("?AAT"))
        return self.error, self.att

    def SetRefLevel(self, something):
        self.error = 0
        # PMM uses one display command valid for analyzer/manual/sweep.
        self.reflevel = float(something)
        self._send(f"SDIS 100;{self.reflevel};")
        return self.GetRefLevel()

    def GetRefLevel(self):
        self.error = 0
        # No dedicated query in chapter 14, keep software mirror.
        return self.error, self.reflevel

    def SetDetector(self, something):
        self.error = 0
        key = str(something).strip().upper()
        det_id = self._DET_TO_ID.get(key, 1)
        self._send(f"SADT {det_id}")
        return self.GetDetector()

    def GetDetector(self):
        self.error = 0
        ans = self._ask("?ADT").upper()
        if "RMS" in ans:
            self.detector = "RMS"
        elif "AVG" in ans:
            self.detector = "AVERAGE"
        else:
            self.detector = "MAXPEAK"
        return self.error, self.detector

    def SetSweepTime(self, something):
        self.error = 0
        if isinstance(something, str) and something.strip().lower() == "auto":
            self.stime = 1.0
            return self.error, self.stime
        self._send(f"SAHT {float(something) * 1e3}")
        return self.GetSweepTime()

    def GetSweepTime(self):
        self.error = 0
        self.stime = self._first_float(self._ask("?AHT")) * 1e-3
        return self.error, self.stime

    def SetTrace(self, trace):
        self.trace = int(trace)
        return 0, self.trace

    def GetTrace(self):
        return 0, self.trace

    def SetTraceMode(self, tmode):
        self.tmode = str(tmode).upper()
        return 0, self.tmode

    def GetTraceMode(self):
        return 0, getattr(self, "tmode", "WRITE")

    def SetSweepCount(self, scount):
        self.scount = int(scount)
        return 0, self.scount

    def GetSweepCount(self):
        return 0, getattr(self, "scount", 1)

    def SetSweepPoints(self, points):
        self.spoints = int(points)
        return 0, self.spoints

    def GetSweepPoints(self):
        return 0, getattr(self, "spoints", 0)

    def SetTriggerMode(self, trgmode):
        self.trgmode = str(trgmode).upper()
        return 0, self.trgmode

    def GetTriggerMode(self):
        return 0, getattr(self, "trgmode", "FREE")

    def SetAttMode(self, attmode):
        self.attmode = "LOWNOISE"
        return 0, self.attmode

    def GetAttMode(self):
        return 0, self.attmode

    def SetTriggerDelay(self, delay):
        self.tdelay = float(delay)
        return 0, self.tdelay

    def GetTriggerDelay(self):
        return 0, self.tdelay

    def SetPreAmp(self, something):
        self.error = 0
        state = "ON" if self._is_on(something) or float(something) != 0 else "OFF"
        self._send(f"SAPA {state}")
        return self.GetPreAmp()

    def GetPreAmp(self):
        self.error = 0
        ans = self._ask("?APA").upper()
        self.preamp = 20 if "ON" in ans else 0
        return self.error, self.preamp

    def _read_exact_bytes(self, nbytes):
        if self.dev is None or not hasattr(self.dev, "read_bytes"):
            raise RuntimeError("Binary analyzer reply requires pyvisa message-based device with read_bytes().")
        return self.dev.read_bytes(nbytes, break_on_termchar=False)

    def _read_analyzer_reply(self):
        # 14.5.3: 8-byte "AGO=OK\\r\\n" + 40-byte header + int16 levels (hundredth dBm).
        self._send("SAGO")
        prefix = self._read_exact_bytes(8)
        if not prefix.startswith(b"AGO=OK"):
            raise RuntimeError(f"Unexpected analyzer reply prefix: {prefix!r}")
        header_tail = self._read_exact_bytes(40)
        header = prefix + header_tail
        start_hz = struct.unpack("<f", header[8:12])[0]
        stop_hz = struct.unpack("<f", header[12:16])[0]
        step_hz = struct.unpack("<f", header[16:20])[0]
        if step_hz <= 0:
            raise RuntimeError(f"Invalid analyzer step frequency: {step_hz}")
        npts = int(round((stop_hz - start_hz) / step_hz)) + 1
        npts = max(npts, 2)
        levels_raw = self._read_exact_bytes(2 * npts)
        levels = struct.unpack(f"<{npts}h", levels_raw)
        yvalues = [v / 100.0 for v in levels]
        xvalues = linspace(start_hz, stop_hz, npts)
        return tuple(xvalues), tuple(yvalues)

    def GetSpectrum(self):
        self.error = 0
        try:
            self.power = self._read_analyzer_reply()
            return self.error, self.power
        except Exception:
            # Fallback path for transports that do not support binary read.
            self.error = 1
            return self.error, None

    def GetDescription(self):
        self.error = 0
        self.IDN = self._ask("?IDN")
        return self.error, self.IDN

    def Quit(self):
        self.error = 0
        self._send("SSTP")
        return self.error


def main():
    import sys

    from mpylab.tools.util import format_block

    try:
        ini = sys.argv[1]
    except IndexError:
        ini = format_block("""
                        [DESCRIPTION]
                        description: 'PMM 9010'
                        type:        'SPECTRUMANALYZER'
                        vendor:      'PMM'
                        serialnr:
                        deviceid:
                        driver: sa_pmm_9010.py

                        [Init_Value]
                        fstart: 10
                        fstop: 30e6
                        fstep: 1
                        visa: TCPIP::192.168.88.253::INSTR
                        virtual: 0

                        [Channel_1]
                        unit: dBm
                        attenuation: auto
                        reflevel: 100.0
                        rbw: auto
                        vbw: auto
                        span: 30e6
                        trace: 1
                        tracemode: WRITE
                        detector: MAXPEAK
                        sweepcount: 1
                        triggermode: FREE
                        attmode: LOWNOISE
                        sweeptime: auto
                        sweeppoints: 501
                        """)

    sa = SPECTRUMANALYZER()
    print(f"Init: {sa.Init(ini=ini, channel=1)}")
    print(f"Description: {sa.GetDescription()}")
    print(f"Spectrum status: {sa.GetSpectrum()[0]}")


if __name__ == "__main__":
    main()
