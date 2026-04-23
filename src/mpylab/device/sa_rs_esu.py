# -*- coding: utf-8 -*-
"""R&S ESU spectrum analyzer driver."""

import functools
import io
import re
import sys
from copy import deepcopy

from numpy import linspace

from mpylab.device.spectrumanalyzer import SPECTRUMANALYZER as SPECTRUMAN


def _number_or_auto(value):
    """Accept numeric values and the keyword 'auto' from INI files."""
    if isinstance(value, str) and value.strip().lower() == "auto":
        return "auto"
    return float(value)


class SPECTRUMANALYZER(SPECTRUMAN):
    """Spectrum analyzer driver for R&S ESU in analyzer mode."""
    conftmpl = deepcopy(SPECTRUMAN.conftmpl)
    conftmpl["init_value"]["visa"] = str
    conftmpl["channel_%d"]["vbw"] = _number_or_auto
    conftmpl["channel_%d"]["sweeptime"] = _number_or_auto

    def __init__(self, **kw):
        super().__init__(**kw)
        self.IDN = "Rohde&Schwarz,ESU,000000,1.0"

        self.MapTRACEMODES = {
            "WRITE": "WRIT",
            "VIEW": "VIEW",
            "AVERAGE": "AVER",
            "BLANK": "OFF",
            "MAXHOLD": "MAXH",
            "MINHOLD": "MINH",
        }
        self.MapTRACEMODES_Back = {
            "WRIT": "WRITE",
            "VIEW": "VIEW",
            "AVER": "AVERAGE",
            "MAXH": "MAXHOLD",
            "MINH": "MINHOLD",
            "OFF": "BLANK",
        }

        self.MapDETECTORS = {
            "AUTOSELECT": "APE",
            "AUTOPEAK": "APE",
            "MAXPEAK": "POS",
            "MINPEAK": "NEG",
            "SAMPLE": "SAMP",
            "RMS": "RMS",
            "AVERAGE": "AVER",
            "DET_QPEAK": "QPE",
        }
        self.MapDETECTORS_Back = {
            "APE": "AUTOPEAK",
            "POS": "MAXPEAK",
            "NEG": "MINPEAK",
            "SAMP": "SAMPLE",
            "RMS": "RMS",
            "AVER": "AVERAGE",
            "QPE": "DET_QPEAK",
            "CRMS": "RMS",
            "CAV": "AVERAGE",
        }

        self.MapTRIGGERMODES = {
            "FREE": "IMM",
            "VIDEO": "VID",
            "EXTERNAL": "EXT",
        }
        self.MapTRIGGERMODES_Back = {
            "IMM": "FREE",
            "VID": "VIDEO",
            "EXT": "EXTERNAL",
        }

        self.trace = 1
        self._internal_unit = "dBm"

        self._cmds = {
            "SetCenterFreq": [("FREQ:CENT {something} HZ", None)],
            "GetCenterFreq": [("FREQ:CENT?", rf"(?P<cfreq>{self._FP})")],
            "SetSpan": [("FREQ:SPAN {something} HZ", None)],
            "GetSpan": [("FREQ:SPAN?", rf"(?P<span>{self._FP})")],
            "SetStartFreq": [("FREQ:STAR {something} HZ", None)],
            "GetStartFreq": [("FREQ:STAR?", rf"(?P<stfreq>{self._FP})")],
            "SetStopFreq": [("FREQ:STOP {something} HZ", None)],
            "GetStopFreq": [("FREQ:STOP?", rf"(?P<spfreq>{self._FP})")],
            "SetRBWAuto": [("BAND:AUTO ON", None)],
            "SetRBW": [("BAND {something} HZ", None)],
            "GetRBW": [("BAND?", rf"(?P<rbw>{self._FP})")],
            "SetVBWAuto": [("BAND:VID:AUTO ON", None)],
            "SetVBW": [("BAND:VID {something} HZ", None)],
            "GetVBW": [("BAND:VID?", rf"(?P<vbw>{self._FP})")],
            "SetRefLevel": [("DISP:WIND:TRAC:Y:RLEV {something} DBM", None)],
            "GetRefLevel": [("DISP:WIND:TRAC:Y:RLEV?", rf"(?P<reflevel>{self._FP})")],
            "SetAtt": [("INP:ATT {something} DB", None)],
            "GetAtt": [("INP:ATT?", rf"(?P<att>{self._FP})")],
            "SetAttAuto": [("INP:ATT:AUTO ON", None)],
            "SetPreAmp": [("INP:GAIN:STAT {something}", None)],
            "GetPreAmp": [("INP:GAIN:STAT?", r"(?P<preamp>.*)")],
            "SetDetectorAuto": [("DET:AUTO ON", None)],
            "SetDetector": [("DET {something}", None)],
            "GetDetector": [("DET?", r"(?P<det>.*)")],
            "SetTraceMode": [("DISP:WIND:TRAC:MODE {something}", None)],
            "SetTraceModeBlank": [("DISP:WIND:TRAC OFF", None)],
            "GetTraceMode": [("DISP:WIND:TRAC:MODE?", r"(?P<tmode>.*)")],
            "GetTraceModeBlank": [("DISP:WIND:TRAC?", r"(?P<tmodeblank>.*)")],
            "SetSweepCount": [("SWE:COUN {something}", None)],
            "GetSweepCount": [("SWE:COUN?", r"(?P<scount>\d+)")],
            "SetSweepTimeAuto": [("SWE:TIME:AUTO ON", None)],
            "SetSweepTime": [("SWE:TIME {something} s", None)],
            "GetSweepTime": [("SWE:TIME?", rf"(?P<stime>{self._FP})")],
            "SetSweepPoints": [("SWE:POIN {something}", None)],
            "GetSweepPoints": [("SWE:POIN?", r"(?P<spoints>\d+)")],
            "GetSpectrum": [
                ("TRAC? TRACE{self.trace}",
                 r"(?P<power>([-+]?(\d+(\.\d*)?|\d*\.\d+)([eE][-+]?\d+)?,?)+)")
            ],
            "SetTriggerMode": [("TRIG:SOUR {something}", None)],
            "GetTriggerMode": [("TRIG:SOUR?", r"(?P<trgmode>.*)")],
            "SetSANMode": [("INST:SEL SAN", None)],
            "GetDescription": [("*IDN?", r"(?P<IDN>.*)")],
        }

        complex_cmds = [
            ("SetRBW", [("auto", "a"), ".+"], ["SetRBWAuto", "SetRBW"]),
            ("SetVBW", ["auto", ".+"], ["SetVBWAuto", "SetVBW"]),
            ("SetAtt", ["auto", ".+"], ["SetAttAuto", "SetAtt"]),
            ("SetDetector", [("auto", "AUTOSELECT"), ".+"], ["SetDetectorAuto", "SetDetector"]),
            ("SetSweepTime", ["auto", ".+"], ["SetSweepTimeAuto", "SetSweepTime"]),
            ("SetTraceMode", [("off", "BLANK"), ".+"], ["SetTraceModeBlank", "SetTraceMode"]),
        ]
        self._cmds["Complex"] = complex_cmds

        setattr(self, "SetAttMode", functools.partial(self._SetAttModeIntern))
        setattr(self, "GetAttMode", functools.partial(self._GetAttModeIntern))
        setattr(self, "SetTrace", functools.partial(self._SetTraceIntern))
        setattr(self, "GetTrace", functools.partial(self._GetTraceIntern))
        setattr(self, "SetPreAmp", functools.partial(self._SetPreAmpIntern))
        setattr(self, "GetPreAmp", functools.partial(self._GetPreAmpIntern))

        self.GetTraceModeSuper = self.GetTraceMode
        setattr(self, "GetTraceMode", functools.partial(self._GetTraceModeIntern))
        self.SetTraceModeSuper = self.SetTraceMode
        setattr(self, "SetTraceMode", functools.partial(self._SetTraceModeIntern))

        # ESU receiver/analyzer docs do not expose a simple trigger delay command in this API shape.
        self.tdelay = 0.0
        setattr(self, "SetTriggerDelay", functools.partial(self._SetTriggerDelayIntern))
        setattr(self, "GetTriggerDelay", functools.partial(self._GetTriggerDelayIntern))

    def GetSpectrum(self):
        self.error = 0
        dct = self._do_cmds("GetSpectrum", locals())
        self._update(dct)
        if self.error != 0:
            return self.error, None
        if not dct or not getattr(self, "power", None):
            self.error = -1
            return self.error, None
        self.power = [value for value in re.split(",", self.power.strip()) if value]
        xvalues = linspace(self.GetStartFreq()[1], self.GetStopFreq()[1], len(self.power))
        yvalues = [float(value) for value in self.power]
        self.power = (tuple(xvalues), tuple(yvalues))
        return self.error, self.power

    def _GetTraceModeIntern(self):
        dct = self._do_cmds("GetTraceModeBlank", locals())
        self._update(dct)
        if str(getattr(self, "tmodeblank", "")).strip().upper() in {"OFF", "0"}:
            return self.error, "BLANK"
        return self.GetTraceModeSuper()

    def _SetTraceModeIntern(self, something):
        err, ret = self.SetTraceModeSuper(something)
        dct = self._do_cmds("GetTraceModeBlank", locals())
        self._update(dct)
        if str(getattr(self, "tmodeblank", "")).strip().upper() in {"OFF", "0"}:
            return err, "BLANK"
        return err, ret

    def _SetPreAmpIntern(self, something):
        if float(something) == 0:
            something = "OFF"
        else:
            something = "ON"
        self.error = 0
        dct = self._do_cmds("SetPreAmp", locals())
        self._update(dct)
        dct = self._do_cmds("GetPreAmp", locals())
        self._update(dct)
        state = str(getattr(self, "preamp", "")).strip().upper()
        if state in {"1", "ON"}:
            self.preamp = 20
        elif state in {"0", "OFF"}:
            self.preamp = 0
        else:
            self.error = 1
        return self.error, self.preamp

    def _GetPreAmpIntern(self):
        self.error = 0
        dct = self._do_cmds("GetPreAmp", locals())
        self._update(dct)
        state = str(getattr(self, "preamp", "")).strip().upper()
        if state in {"1", "ON"}:
            self.preamp = 20
        elif state in {"0", "OFF"}:
            self.preamp = 0
        else:
            self.error = 1
        return self.error, self.preamp

    def _SetTraceIntern(self, trace):
        self.trace = trace
        return 0, trace

    def _GetTraceIntern(self):
        return 0, self.trace

    def _SetAttModeIntern(self, _attmode):
        return 0, "LOWNOISE"

    def _GetAttModeIntern(self):
        return 0, "LOWNOISE"

    def _SetTriggerDelayIntern(self, delay):
        self.tdelay = float(delay)
        return 0, self.tdelay

    def _GetTriggerDelayIntern(self):
        return 0, self.tdelay

    def SetSANMode(self):
        self.error = 0
        dct = self._do_cmds("SetSANMode", locals())
        self._update(dct)
        return self.error, 0

    def Init(self, ini=None, channel=None):
        if channel is None:
            channel = 1
        self.error = super().Init(ini, channel)
        sec = f"channel_{channel}"
        try:
            self.levelunit = self.conf[sec]["unit"]
        except KeyError:
            self.levelunit = self._internal_unit

        self.SetSANMode()
        # Ensure front-panel display stays active even if previous sessions disabled it.
        self.write("SYST:DISP:UPD ON")
        self.write("INIT:DISP ON")

        self._cmds["Preset"] = []
        presets = [
            ("trace", None, "SetTrace"),
            ("attenuation", None, "SetAtt"),
            ("reflevel", None, "SetRefLevel"),
            ("rbw", None, "SetRBW"),
            ("vbw", None, "SetVBW"),
            ("span", None, "SetSpan"),
            ("tracemode", None, "SetTraceMode"),
            ("detector", None, "SetDetector"),
            ("sweepcount", None, "SetSweepCount"),
            ("triggermode", None, "SetTriggerMode"),
            ("sweeptime", None, "SetSweepTime"),
            ("sweeppoints", None, "SetSweepPoints"),
        ]
        self._apply_presets(presets, sec)
        dct = self._do_cmds("Preset", locals())
        self._update(dct)
        return self.error


def main():
    from PySide6 import QtWidgets
    from mpylab.tools.util import format_block
    from mpylab.device.spectrumanalyzer_ui import UI

    ini = format_block("""
                    [DESCRIPTION]
                    description: 'R&S ESU'
                    type:        'SPECTRUMANALYZER'
                    vendor:      'Rohde&Schwarz'
                    serialnr:
                    deviceid:
                    driver: sa_rs_esu.py

                    [Init_Value]
                    fstart: 20
                    fstop: 26.5e9
                    fstep: 1
                    visa: TCPIP::192.168.88.253::INSTR
                    virtual: 0

                    [Channel_1]
                    unit: 'dBm'
                    attenuation: auto
                    reflevel: -20
                    rbw: auto
                    vbw: auto
                    span: 10e6
                    trace: 1
                    tracemode: 'WRITE'
                    detector: 'AUTOPEAK'
                    sweepcount: 0
                    triggermode: 'FREE'
                    attmode: auto
                    sweeptime: auto
                    sweeppoints: 625
                    """)
    ini = io.StringIO(ini)

    app = QtWidgets.QApplication(sys.argv)
    sp = SPECTRUMANALYZER()
    ui = UI(sp, ini=ini)
    ui.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
