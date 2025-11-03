# -*- coding: utf-8 -*-
"""This is :mod:`mpylab.device.rec_rs_ESHS30``.

   Provides driver for Rec RS ESHS30.
   :author: Hans Georg Krauthäuser (main author)

   :license: GPL-3 or higher
"""

import io
import sys

import numpy as np

from mpylab.device.spectrumanalyzer import RECEIVER as REC
from mpylab.device.driver import DRIVER


class RECEIVER(REC):
    def __init__(self):
        #super(RECEIVER, self).__init__()
        DRIVER.__init__(self)
        self.error = 0
        self._internal_unit = 'dBuV'
        self.term_chars = '\n'
        #self._cmds = {}
        #self._cmds['Complex'] = []

    def SetCenterFreq(self, freq):
        self.error = 0
        self.write(f'FREQUENCY {freq} HZ')
        self.error, freq = self.GetCenterFreq()
        return self.error, freq

    def GetCenterFreq(self):
        self.error = 0
        freq = None
        dct = self.query('FREQUENCY?', r'FREQUENCY (?P<freq>%s)' % self._FP)
        return self.error, float(dct['freq'])

    def SetSpan(self, span):
        raise NotImplementedError

    def GetSpan(self):
        raise NotImplementedError

    def SetStartFreq(self, freq):
        return self.SetCenterFreq(freq)

    def GetStartFreq(self):
        return self.GetCenterFreq()

    def SetStopFreq(self, freq):
        return self.SetCenterFreq(freq)

    def GetStopFreq(self):
        return self.GetCenterFreq()

    def SetRBW(self, freq):
        self.error = 0
        ans = self.write(f'BANDWIDTH:IF {freq} HZ')
        self.error, rbw = self.GetRBW()
        return self.error, rbw

    def GetRBW(self):
        self.error = 0
        dct = self.query('BANDWIDTH:IF?', r'BANDWIDTH:IF (?P<rbw>%s)' % self._FP)
        return self.error, float(dct['rbw'])

    def SetRBWAuto(self):
        pass

    def SetVBW(self, freq):
        pass

    def GetVBW(self):
        self.error = 0
        freq = None
        return self.error, freq

    def SetVBWAuto(self):
        pass

    def SetRefLevel(self, lvl):
        pass

    def GetRefLevel(self):
        self.error = 0
        lvl = None
        return self.error, lvl

    def SetAtt(self, att):
        att = round(att)
        att = min(att, 60)
        att = max(att, 0)
        ans = self.write(f'ATTENUATION {att} dB')

    def GetAtt(self):
        self.error = 0
        dct = self.query('ATTENUATION?', r'(?P<att>.*)')
        att = dct['att']
        return self.error, att

    def SetAttAuto(self):
        pass

    def SetAttMode(self, mode):
        pass

    def GetAttMode(self):
        self.error = 0
        mode = None
        return self.error, mode

    def SetPreAmp(self, status):
        pass

    def GetPreAmp(self):
        self.error = 0
        status = None
        return self.error, status

    def SetDetector(self, det):
        pass

    def GetDetector(self):
        self.error = 0
        det = None
        return self.error, det

    def SetDetectorAuto(self):
        pass

    def SetTraceMode(self, mode):
        pass

    def GetTraceMode(self):
        self.error = 0
        mode = None
        return self.error, mode

    def SetTraceModeBlank(self):
        pass

    def GetTraceModeBlank(self):
        self.error = 0
        mode = None
        return self.error, mode

    def SetTrace(self, number):
        pass

    def GetTrace(self):
        self.error = 0
        number = None
        return self.error, number

    def SetSweepCount(self, number):
        pass

    def GetSweepCount(self):
        self.error = 0
        number = None
        return self.error, number

    def SetSweepTime(self, sweeptime):
        pass

    def GetSweepTime(self):
        self.error = 0
        sweeptime = None
        return self.error, sweeptime

    def SetSweepTimeAuto(self):
        pass

    def SetSweepPoints(self, points):
        pass

    def GetSweepPoints(self):
        self.error = 0
        points = None
        return self.error, points

    def SetTriggerMode(self, mode):
        pass

    def GetTriggerMode(self):
        self.error = 0
        mode = None
        return self.error, mode

    def SetTriggerDelay(self, delay):
        pass

    def GetTriggerDelay(self):
        self.error = 0
        delay = None
        return self.error, delay

    def SetWindow(self, window):
        pass
    def Quit(self):
        pass

    def SetSANMode(self):
        pass

    def GetDescription(self):
        self.error = 0
        dct = self.query('*IDN?', r'(?P<desc>.*)')
        return self.error, dct['desc']

    def GetSpectrum(self):
        self.error = 0
        values = []
        return self.error, values

    def GetSpectrumNB(self):
        self.error = 0
        values = []
        return self.error, values

    def Init(self, ini=None, channel=None):
        if channel is None:
            channel = 1
        self.error = REC.Init(self, ini, channel)
        sec = 'channel_%d' % channel
        try:
            self.levelunit = self.conf[sec]['unit']
        except KeyError:
            self.levelunit = self._internal_unit
        return self.error


def main():
    from mpylab.tools.util import format_block
    try:
        ini = sys.argv[1]
    except IndexError:
        ini = format_block("""
                        [DESCRIPTION]
                        description: 'R&S ESHS30'
                        type:        'RECEIVER'
                        vendor:      'Rohde&Schwarz'
                        serialnr:
                        deviceid:
                        driver: rec_rs_ESHS30.py

                        [Init_Value]
                        fstart: 9e6
                        fstop: 30e6
                        fstep: 1
                        gpib: 17
                        virtual: 0

                        [Channel_1]
                        unit: 'dBuV'
                        attenuation: auto
                        reflevel: -20
                        rbw: auto
                        vbw: 10e6
                        span: 6e9
                        trace: 1
                        tracemode: 'WRITe'
                        detector: 'APEak'
                        sweepcount: 0
                        triggermode: 'IMMediate'
                        attmode: auto
                        sweeptime: 10e-3
                        sweeppoints: 500
                        """)
        # rbw: 3e6
        ini = io.StringIO(ini)

    rec = RECEIVER()

    err = rec.Init(ini)
    assert err == 0, 'Init() fails with error %d' % (err)
    err, des = rec.GetDescription()
    print(des)

    err, freq = rec.SetCenterFreq(20.125e3)
    print(f"Frequency (Hz) = {freq}")

    for _rbw in np.linspace(200, 10e3, 100, endpoint=True):
        err, rbw = rec.SetRBW(205)
        print(f"RBW (Hz) {_rbw} = {rbw}")



if __name__ == '__main__':
    main()
