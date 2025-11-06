# -*- coding: utf-8 -*-
"""This is :mod:`mpylab.device.rec_rs_ESHS30``.

   Provides driver for Rec RS ESHS30.
   :author: Hans Georg Krauthäuser (main author)

   :license: GPL-3 or higher
"""
import numpy as np

from mpylab.device.receiver import RECEIVER as REC
from scuq.quantities import Quantity
from scuq.ucomponents import UncertainInput
from scuq.si import VOLT, WATT


class RECEIVER(REC):
    def __init__(self):
        super().__init__()
        self._cmds = {'SetFreq': [("f'FREQUENCY {freq} HZ'", None)],
                      'GetFreq': [('FREQUENCY?', r'FREQUENCY (?P<freq>%s)' % self._FP)],
                      'GetData': [('LEVEL?', r'LEVEL (?P<level>%s)' % self._FP)],
                      'GetDataNB': [('LEVEL:LASTVALUE?', r'LEVEL:LASTVALUE (?P<level>%s)' % self._FP)],
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
            self.unit = self.conf[sec]['unit']
            if self.unit.upper() == 'WATT':
                self.unit = WATT
            elif self.unit.upper() == 'VOLT':
                self.unit = VOLT
            else:
                raise RuntimeError('Unrecognized unit: %s' % self.unit)
        except KeyError:
            self.unit = VOLT
        self._get_internal_unit()
        return self.error

    def _get_internal_unit(self):
        ans = self.query('SPECIALFUNC?', None)
        ans = ans[ans.index(',20,') + 4 : ans.index(',21,')]    # dBm ist SPECIALFUNC 20
        if ans == 'ON':
            self._internal_unit = 'dBm'
        else:
            self._internal_unit = 'dBuV'
        return self._internal_unit

    def _convert_level_to_unit(self, lev, Z=50):
        if self._internal_unit == 'dBm':   # level is in dBm
            if self.unit is WATT:
                lev = np.pow(10, (0.1*lev)) * 1e-3   # Watt
            elif self.unit is VOLT:
                lev = lev + 90 + 10*np.log10(Z)   # dBuV
                lev = np.pow(10, (0.05*lev)) * 1e-6   # Volt
            else:
                raise RuntimeError('Unrecognized unit: %s' % self.unit)
        elif self._internal_unit == 'dBuV':
            if self.unit is WATT:
                lev = lev - 90 - 10*np.log10(Z)   # dBm
                lev = np.pow(10, (0.1*lev)) * 1e-3   # Watt
            elif self.unit is VOLT:
                lev = np.power(10, (0.05*lev)) * 1e-6   # Volt
            else:
                raise RuntimeError('Unrecognized unit: %s' % self.unit)
        else:
            raise RuntimeError('Unrecognized internal unit: %s' % self._internal_unit)
        return lev


    def _create_lev_object(self, lev):
        self.level = float(self.level)
        self.level = self._convert_level_to_unit(self.level)
        # uncertainty is 0.5 dB
        if self.unit == WATT:
            relerr = 0.122
        else:
            relerr = 0.059
        obj = Quantity(self.unit, UncertainInput(self.level, self.level*relerr))
        return obj

    def GetData(self):
        self.error = 0
        dct = self._do_cmds('GetData', locals())
        self._update(dct)
        obj = self._create_lev_object(self.level)
        return self.error, obj

    def GetDataNB(self, retrigger):
        """
        Non-blocking version of :meth:`GetData`.

        If implemented, this function will return ``(-1, None)`` until the answer from the device is available.
        Then, it will return ``self.error, obj)``.

        If *retrigger* is ``True`` or ``'on'``, the device will be triggered for a new measurment after the measurement has been
        red.

        If not implemented, the method will return :meth:`GetData`.
        """
        obj = None
        self.error = 0
        dct = self._do_cmds('GetDataNB', locals())
        self._update(dct)
        if self.level:
            if self.level == '0.00':
                return None    # Not ready yet
            obj = self._create_lev_object(self.level)
            if retrigger is True or retrigger.upper() == 'ON':
                self.Trigger()
        return self.error, obj


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
                        unit: Watt
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
        err, dat = d.GetData()
        print(f"Freq {rfreq} Hz, Level: {dat}")


    for _rbw in np.linspace(200, 20e3, 100, endpoint=True):
        err, rbw = d.SetResolutionBandwidth(_rbw)
        print(f"RBW (Hz) {_rbw} = {rbw}")

    d.Quit()


if __name__ == '__main__':
    main()
