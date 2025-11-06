# -*- coding: utf-8 -*-
"""This is :mod:`mpylab.device.rec_rs_ESHS30``.

   Provides driver for Rec RS ESHS30.
   :author: Hans Georg Krauthäuser (main author)

   :license: GPL-3 or higher
"""

import io
import sys

import numpy as np

from mpylab.device.receiver import RECEIVER as REC
from mpylab.device.driver import DRIVER


class RECEIVER(REC):
    def __init__(self):
        super().__init__()
        self._cmds = {'SetFreq': [("f'FREQUENCY {freq} HZ'", None)],
                      'GetFreq': [('FREQUENCY?', r'FREQUENCY (?P<freq>%s)' % self._FP)],
                      'GetData': [('LEVEL?', r'LEVEL (?P<lev>%s)' % self._FP)],
                      'GetDataNB': [('LEVEL:LASTVALUE?', r'LEVEL:LASTVALUE (?P<lev>%s)' % self._FP)],
                      'Trigger': [('*TRG', None)],
                      'SetAttenuation': [("f'ATTENUATION {attenuation} DB'", None)],
                      'GetAttenuation': [('ATTENUATION?', r'ATTENUATION (?P<attenuation>%s)' % self._FP)],
                      'SetMinAttenuation': [("f'MIN:ATTENUATION {min_attenuation} DB'", None)],
                      'GetMinAttenuation': [('MIN:ATTENUATION?', r'MIN:ATTENUATION (?P<min_attenuation>%s)' % self._FP)],
                      'SetMeasTime': [("f'MEASUREMENT:TIME {meas_time} s'", None)],
                      'GetMeasTime': [('MEASUREMENT:TIME?', r'MEASUREMENT:TIME (?P<meas_time>%s)' % self._FP)],
                      'SetDetector': [("f'DETECTOR {detector}'", None)],
                      'GetDetector': [('DETECTOR?', r'DETECTOR (?P<detector>.*)')],
                      'SetPreamplifier': [("f'PREAMPLIFIER {preamplifier}'", None)],
                      'GetPreamplifier': [('PREAMPLIFIER?', r'PREAMPLIFIER (?P<preamplifier>.*)')],
                      'SetResolutionBandwidth': [("f'BANDWIDTH:IF {rbw} HZ'", None)],
                      'GetResolutionBandwidth': [('BANDWIDTH:IF?', r'BANDWIDTH:IF (?P<rbw>%s)' % self._FP)],
                      'Quit': [('*CLS', None)],
                      'GetDescription': [('*IDN?', r'(?P<IDN>.*)')]}
        self.error = 0

    def Init(self, ininame=None, channel=None):
        if channel is None:
            channel = 1
        self.error = super().Init(ininame=ininame, channel=channel)
        sec = 'channel_%d' % channel
        try:
            self.levelunit = self.conf[sec]['unit']
        except KeyError:
            self.levelunit = self._internal_unit
        return self.error


def main():
    import sys, io
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
                        visa: GPIB0::17::INSTR
                        virtual: 0

                        [Channel_1]
                        name: RFin
                        min_attenuation: 10
                        meas_time: 0.05
                        preamplifier: on
                        unit: dBuV
                        attenuation: auto
                        rbw: auto
                        detector: PEAK
                        """)
        # rbw: 3e6
        ini = io.StringIO(ini)


    d = RECEIVER()
    d.Init(ininame=ini, channel=1)
    if not ini:
        d.SetVirtual(False)

    err, des = d.GetDescription()
    print(("Description: %s" % des))

    for freq in [9e3, 100e3, 500e3, 1e6, 10e6, 30e6]:
        print(("Set freq to %e Hz" % freq))
        err, rfreq = d.SetFreq(freq)
        if err == 0:
            print(("Freq set to %e Hz" % rfreq))
        else:
            print("Error setting freq")


    for _rbw in np.linspace(200, 10e3, 100, endpoint=True):
        err, rbw = d.SetResolutionBandwidth(205)
        print(f"RBW (Hz) {_rbw} = {rbw}")

    d.Quit()


if __name__ == '__main__':
    main()
