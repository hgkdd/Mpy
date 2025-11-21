# -*- coding: utf-8 -*-
"""This is :mod:`mpylab.device.rec_rs_ESHS30``.

   Provides driver for Rec RS ESHS30.
   :author: Hans Georg Krauthäuser (main author)

   :license: GPL-3 or higher
"""
import numpy as np

from mpylab.device.receiver import RECEIVER as REC
from mpylab.tools.util import case_insensitive_string_compare
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
                      'SetAttenuation': [('ATTENUATION:AUTO OFF', None), ("f'ATTENUATION {attenuation} DB'", None)],
                      'GetAttenuation': [('ATTENUATION?', r'ATTENUATION (?P<attenuation>%s)' % self._FP)],
                      #'SetMinAttenuation': [("f'MIN:ATTENUATION {min_attenuation} DB'", None)],
                      #'GetMinAttenuation': [('MIN:ATTENUATION?', r'MIN:ATTENUATION (?P<min_attenuation>%s)' % self._FP)],
                      'SetMeasTime': [("f'MEASUREMENT:TIME {meas_time} s'", None)],
                      'GetMeasTime': [('MEASUREMENT:TIME?', r'MEASUREMENT:TIME (?P<meas_time>%s)' % self._FP)],
                      'SetDetector': [("f'DETECTOR {detector}'", None)],
                      'GetDetector': [('DETECTOR?', r'DETECTOR (?P<detector>.*)')],
                      'SetPreamplifier': [("f'PREAMPLIFIER {preamplifier}'", None)],
                      'GetPreamplifier': [('PREAMPLIFIER?', r'PREAMPLIFIER (?P<preamplifier>.*)')],
                      'SetResolutionBandwidth': [("SPECIALFUNC 1,OFF", None), ("f'BANDWIDTH:IF {rbw} HZ'", None)],
                      'GetResolutionBandwidth': [('BANDWIDTH:IF?', r'BANDWIDTH:IF (?P<rbw>%s)' % self._FP)],
                      'Quit': [('*CLS', None)],
                      'GetDescription': [('*IDN?', r'(?P<IDN>.*)')]}
        self.error = 0
        self.min_attenuation = 10    # a safe value as default
        self.detector_map = {'peak': 'PEAK',
                             'qpeak': 'QUASIPEAK',
                             'average': 'AVERAGE'}

    def Init(self, ini=None, channel=None):
        if channel is None:
            channel = 1
        self.error = super().Init(ini=ini, channel=channel)

        sec = 'channel_%d' % channel
        try:
            self.unit = self.conf[sec]['unit']
            if case_insensitive_string_compare(self.unit, 'Watt'):
                self.unit = WATT
            elif case_insensitive_string_compare(self.unit, 'Volt'):
                self.unit = VOLT
            else:
                raise RuntimeError('Unrecognized unit: %s' % self.unit)
        except KeyError:
            self.unit = VOLT
        # Preset
        self.write("*CLS")
        self.write("*RST")
        self.write("PRESET")

        self._get_internal_unit()
        self.error, self.min_attenuation = self.SetMinAttenuation(self.conf[f'channel_{channel}']['min_attenuation'])
        self.error, self.detector = self.SetDetector(self.conf[f'channel_{channel}']['detector'])
        self.error, self.rbw = self.SetResolutionBandwidth(self.conf[f'channel_{channel}']['rbw'])
        self.error, self.meas_time = self.SetMeasTime(self.conf[f'channel_{channel}']['meas_time'])
        self.error, self.preamplifier = self.SetPreamplifier(self.conf[f'channel_{channel}']['preamplifier'])
        self.error, self.attenuation = self.SetAttenuation(self.conf[f'channel_{channel}']['attenuation'])


        return self.error


    def _get_db_from_obj(self, obj, Z=50):
        value = obj.get_expectation_value_as_float()
        dBval = None
        unit = obj._unit
        if unit is VOLT:
            if case_insensitive_string_compare(self._internal_unit, 'dBuV'):
                dBval = 20 * np.log10(value * 1e6)
            elif case_insensitive_string_compare(self._internal_unit, 'dBm'):
                mW = value * value / Z * 1e3
                dBval = 10 * np.log10(mW)
            else:
                raise RuntimeError('Unrecognized unit: %s' % self._internal_unit)
        elif unit is WATT:
            if case_insensitive_string_compare(self._internal_unit, 'dBuV'):
                uV = np.sqrt(value * Z) * 1e6
                dBval = 20 * np.log10(uV)
            elif case_insensitive_string_compare(self._internal_unit, 'dBm'):
                dBval = 10 * np.log10(value * 1e3)
            else:
                raise RuntimeError('Unrecognized unit: %s' % self._internal_unit)
        else:
            raise RuntimeError('Unrecognized unit: %s' % self.unit)
        return dBval

    def _get_bool_from_specialfunc(self, number):
        status = None
        key = str(number)
        ans = self.query('SPECIALFUNC?', None)
        lst = ans.lstrip('SPECIALFUNC ').split(',')
        try:
            dct = {lst[i]: lst[i+1] for i in range(0, len(lst), 2)}
            status = (dct[key] == 'ON')  # True if 'ON'
        except (IndexError, KeyError):
            raise RuntimeWarning('Unable to val for from SPECIALFUNC %s' % number)
        return status

    def _get_internal_unit(self):
        try:
            isdBm = self._get_bool_from_specialfunc(20)
        except UserWarning:
            raise RuntimeError('Unable to get internal unit from SPECIALFUNC')
        if isdBm:
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


    def _create_lev_object(self, level):
        level = float(level)
        level = self._convert_level_to_unit(level)
        # uncertainty is 0.5 dB
        if self.unit == WATT:
            relerr = 0.122
        else:
            relerr = 0.059
        obj = Quantity(self.unit, UncertainInput(level, level*relerr))
        return obj

    def SetPreamplifier(self, preamplifier):
        self.error = 0
        dct = self._do_cmds('SetPreamplifier', locals())
        self._update(dct)
        dct = self._do_cmds('GetPreamplifier', locals())
        self._update(dct)
        return self.error, self.preamplifier

    def GetPreamplifier(self):
        self.error = 0
        dct = self._do_cmds('GetPreamplifier', locals())
        self._update(dct)
        return self.error, self.preamplifier

    def SetDetector(self, detector):
        self.error = 0
        detector = self.detector_map[detector.lower()]
        dct = self._do_cmds('SetDetector', locals())
        self._update(dct)
        dct = self._do_cmds('GetDetector', locals())
        self._update(dct)
        for key, value in self.detector_map.items():
            if self.detector == value:
                self.detector = key
        return self.error, self.detector

    def GetDetector(self):
        self.error = 0
        dct = self._do_cmds('GetDetector', locals())
        self._update(dct)
        return self.error, self.detector

    def SetMeasTime(self, meas_time):
        self.error = 0
        if meas_time is None or case_insensitive_string_compare(meas_time, 'auto'):
            self.write('SPECIALFUNC 2,ON')   # couple meas_time to ZF bandwidth
        else:
            self.write('SPECIALFUNC 2,OFF')   # couple meas_time to ZF bandwidth
            dct = self._do_cmds('SetMeasTime', locals())
            self._update(dct)
        dct = self._do_cmds('GetMeasTime', locals())
        self._update(dct)
        return self.error, self.meas_time

    def GetMeasTime(self):
        self.error = 0
        dct = self._do_cmds('GetMeasTime', locals())
        self._update(dct)
        return self.error, self.meas_time

    def SetResolutionBandwidth(self, rbw):
        self.error = 0
        if rbw is None or case_insensitive_string_compare(rbw, 'auto'):
            self.write('SPECIALFUNC 1,ON')
        else:
            dct = self._do_cmds('SetResolutionBandwidth', locals())
            self._update(dct)
        dct = self._do_cmds('GetResolutionBandwidth', locals())
        self._update(dct)
        return self.error, self.rbw

    def SetAttenuation(self, attenuation):
        self.error = 0
        if attenuation is None or case_insensitive_string_compare(attenuation, 'auto'):
            self.write('ATTENUATION:AUTO ON')
        else:
            attenuation = int(np.ceil(attenuation / 10.0)) * 10    # ESHS can only 10,20,30,...
            attenuation = int(max(self.min_attenuation, attenuation))   # respect min_attenuation
            dct = self._do_cmds('SetAttenuation', locals())
            self._update(dct)
        dct = self._do_cmds('GetAttenuation', locals())
        self._update(dct)
        self.attenuation = float(self.attenuation)
        return self.error, self.attenuation


    def GetData(self):
        self.error = 0
        dct = self._do_cmds('GetData', locals())
        self._update(dct)
        obj = self._create_lev_object(self.level)
        return self.error, obj

    def GetDataNB(self, retrigger):
        """
        Non-blocking version of :meth:`GetData`.

        This function will return ``(-1, None)`` until the answer from the device is available.
        Then, it will return ``(self.error, obj)``.

        If *retrigger* is ``True`` or ``'on'``, the device will be triggered for a new measurment after the measurement has been
        red.
        """
        obj = None
        self.error = 0
        dct = self._do_cmds('GetDataNB', locals())
        self._update(dct)
        if self.level:
            if self.level == '0.00':   # this is returned from the instrument if data not ready
                self.level = None
                self.error = -1
                return self.error, None    # Not ready yet
            obj = self._create_lev_object(self.level)
            if retrigger is True or case_insensitive_string_compare(retrigger, 'on'):
                self.Trigger()
        return self.error, obj

    def SetMinAttenuation(self, att):
        self.min_attenuation = max(att, 0)   # 0 dB is minimal min_attenuation
        if self.attenuation is None or self.min_attenuation > self.attenuation:
            self.error, self.attenuation = self.SetAttenuation(self.min_attenuation)
        return 0, self.min_attenuation

    def GetMinAttenuation(self):
        return 0, self.min_attenuation


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
                        fstart: 9e3
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


    rec = RECEIVER()
    rec.Init(ini=ini, channel=1)
    if not ini:
        rec.SetVirtual(False)

    err, des = rec.GetDescription()
    print("Description: %s" % des)

    for freq in [9e3, 100e3, 500e3, 1e6, 10e6, 30e6]:
        print(f"Set freq to {freq} Hz")
        err, returned_freq = rec.SetFreq(freq)
        err, dat = rec.GetData()
        print(f"Freq {returned_freq} Hz, Level: {dat} --> {rec._get_db_from_obj(dat)} {rec._internal_unit}")

    for _rbw in np.linspace(200, 20e3, 100, endpoint=True):
        err, rbw = rec.SetResolutionBandwidth(_rbw)
        print(f"RBW (Hz) {_rbw} = {rbw}")

    rec.Quit()


if __name__ == '__main__':
    main()
