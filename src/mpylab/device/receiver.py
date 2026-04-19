# -*- coding: utf-8 -*-
"""
This is the :mod:`mpylab.device.receiver` module.

   :author: Hans Georg Krauthäuser (main author)

   :license: GPLv3 or higher
"""


from scuq import *

from mpylab.device.driver import DRIVER
from mpylab.tools.configuration import strbool
from mpylab.tools.regular_expressions import FP


class RECEIVER(DRIVER):
    """
    Child class for all py-drivers for EMC receivers.
    
    The parent class is :class:`mpylab.device.driver.DRIVER`.
    
    The configuration template for this device class is::
    
        conftmpl={'description': 
                     {'description': str,
                      'type': str,
                      'vendor': str,
                      'serialnr': str,
                      'deviceid': str,
                      'driver': str},
                    'init_value':
                        {'fstart': float,
                         'fstop': float,
                         'fstep': float,
                         'visa': str,
                         'virtual': strbool,
                         'nr_of_channels': int},
                    'channel_%d':
                        {'name': str,
                         'detector': str,
                         'attenuation': str,
                         'meas_time': str,
                         'min_attenuation': int,
                         'unit': str,
                         'preamplifier': str}}
       
    The meaning is:
        
    - Section *description*
        - description: string describing the instrument
        - type: string with the instrument type (here: POWERMETER)
        - vendor: string ddescribing the vendor/manufactor
        - serialnr: string with a unique identification
        - deviceid: string with an internal id
        - driver: filename of the instrument driver (.py, .pyc, .pyd, .dll)
    - Section *init_value*
        - *fstart*: lowest possible frequency in Hz of the device
        - *fstop*: highest possible frequency in Hz of the device
        - *fstep*: smallest frequency step in Hz of the device
        - *visa*: VISA identifier
        - *virtual*: 0, false or 1, true. Virtual device are usefull for testing and debugging.
        - *nr_of_channels*: indicates how many channel sections follow
    - Section *channel_%d* (*%d* may be 1, 2, ...)
        - *name*: a string identifying the channel.
        - *detector*: detector used fpr this channel
        - *unit*: a string containing the unit of the returned power/voltage readings.
          However, :mod:`scuq` will ignore dB-settings, and the returned power/voltage will contain
          the unit anyway.
        - *meas_time*: the measuring time for that channel, or *auto*
        - *attenuation*: value of the attenuation, may be *auto*
        - *min_attenuation*: value of the minimum attenuation
        - *detector*: 'PEAK', 'AVERAGE', 'QPEAK'
        - *preamplifier*: 'on' or 'off'
    """

    conftmpl = {'description':
                    {'description': str,
                     'type': str,
                     'vendor': str,
                     'serialnr': str,
                     'deviceid': str,
                     'driver': str},
                'init_value':
                    {'fstart': float,
                     'fstop': float,
                     'fstep': float,
                     'visa': str,
                     'virtual': strbool,
                     'nr_of_channels': int},
                'channel_%d':
                    {'name': str,
                     'detector': str,
                     'attenuation': str,
                     'min_attenuation': int,
                     'meas_time': str,
                     'rbw': str,
                     'unit': str,
                     'preamplifier': str}}

    _FP = FP

    def __init__(self, SearchPaths=None):
        DRIVER.__init__(self, SearchPaths=SearchPaths)
        self._cmds = {'SetFreq': [("f'FREQUENCY {freq} HZ'", None)],
                      'GetFreq': [('FREQUENCY?', rf'FREQUENCY (?P<freq>{self._FP})')],
                      'GetData': [('LEVEL?', rf'LEVEL (?P<level>{self._FP})')],
                      'GetDataNB': [('LEVEL:LASTVALUE?', rf'LEVEL:LASTVALUE (?P<level>{self._FP})')],
                      'Trigger': [('*TRG', None)],
                      'SetAttenuation': [("f'ATTENUATION {attenuation} DB'", None)],
                      'GetAttenuation': [('ATTENUATION?', rf'ATTENUATION (?P<attenuation>{self._FP})')],
                      'SetMinAttenuation': [("f'MIN:ATTENUATION {min_attenuation} DB'", None)],
                      'GetMinAttenuation': [('MIN:ATTENUATION?', rf'MIN:ATTENUATION (?P<min_attenuation>{self._FP})')],
                      'SetMeasTime': [("f'MEASUREMENT:TIME {meas_time} s'", None)],
                      'GetMeasTime': [('MEASUREMENT:TIME?', rf'MEASUREMENT:TIME (?P<meas_time>{self._FP})')],
                      'SetDetector': [("f'DETECTOR {detector}'", None)],
                      'GetDetector': [('DETECTOR?', r'DETECTOR (?P<detector>.*)')],
                      'SetPreamplifier': [("f'PREAMPLIFIER {preamplifier}'", None)],
                      'GetPreamplifier': [('PREAMPLIFIER?', r'PREAMPLIFIER (?P<preamplifier>.*)')],
                      'SetResolutionBandwidth': [("f'BANDWIDTH:IF {rbw} HZ'", None)],
                      'GetResolutionBandwidth': [('BANDWIDTH:IF?', rf'BANDWIDTH:IF (?P<rbw>{self._FP})')],
                      'Quit': [('*CLS', None)],
                      'GetDescription': [('*IDN?', r'(?P<IDN>.*)')]}
        self.freq = None
        self.attenuation = None
        self.min_attenuation = 10
        self.meas_time = None
        self.rbw = None
        self.detector = 'PEAK'
        self.preamplifier = 'OFF'
        self.level = None
        self.unit = None
        self.channel = None
        self._internal_unit = 'dBuV'

    def SetFreq(self, freq):
        """
        Set the frequency to *freq* (in Hz).

        After setting, the freq is read back from the device.

        ``(self.error, self.freq)`` is returned.
        """
        self.error = 0
        # print freq
        dct = self._do_cmds('SetFreq', locals())
        self._update(dct)
        dct = self._do_cmds('GetFreq', locals())
        self._update(dct)
        if self.error == 0:
            if not dct:
                self.freq = freq
            else:
                self.freq = float(self.freq)
            # print self.freq
        return self.error, self.freq

    def GetFreq(self):
        """
        Get the frequency to *freq* (in Hz).

        ``(self.error, self.freq)`` is returned.
        """
        self.error = 0
        dct = self._do_cmds('GetFreq', locals())
        self._update(dct)
        return self.error, self.freq

    def Trigger(self):
        """
        Trigger a single measurement.
        
        ``self.error`` is returned.
        """
        self.error = 0
        dct = self._do_cmds('Trigger', locals())
        self._update(dct)
        # if self.error == 0:
        #    print "Device triggered."
        return self.error


    def GetData(self):
        """
        Read a power measurement from the instrument.
        
        ``(self.error, obj)`` is returned where ``obj`` is a instance of 
        :class:`scuq.quantities.Quantity`.
        """
        self.error = 0
        dct = self._do_cmds('GetData', locals())
        self._update(dct)

        if self.error == 0 and self.level:
            self.update_internal_unit()
            self.level = float(self.level)
            level_value = self.level
            iu = self._internal_unit
            if isinstance(iu, str):
                level_value, level_unit = self.convert.c2scuq(iu, level_value)  # iu ist a str 'dbm', ...
            elif isinstance(iu, units.Unit):  # iu is a scuq unit
                level_unit = iu
            else:
                raise TypeError(f"_internal_unit must be str or scuq Unit, got {type(iu).__name__}: {iu!r}")

            obj = quantities.Quantity(level_unit,
                                      ucomponents.UncertainInput(level_value, 0))
        else:
            obj = None
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
        self.error, obj = self.GetData()
        if retrigger in (True, 'ON', 'On', 'on'):
            self.Trigger()
        return self.error, obj

    def SetAttenuation(self, attenuation):
        """
        Set the attenuation to *attenuation* (in dB).

        After setting, the attenuation is read back from the device.

        ``(self.error, self.attenuation)`` is returned.
        """
        self.error = 0
        attenuation = max(attenuation, self.min_attenuation)   # ensure att is larger than min_att
        dct = self._do_cmds('SetAttenuation', locals())
        self._update(dct)
        dct = self._do_cmds('GetAttenuation', locals())
        self._update(dct)
        if self.error == 0:
            if not dct:
                self.attenuation = attenuation
            else:
                self.attenuation = float(self.attenuation)
        return self.error, self.attenuation

    def GetAttenuation(self):
        """
        Get the attenuation in dB.

        ``(self.error, self.attenuation)`` is returned.
        """
        self.error = 0
        dct = self._do_cmds('GetAttenuation', locals())
        self._update(dct)
        self.attenuation = float(self.attenuation)
        return self.error, self.attenuation


    def SetMinAttenuation(self, min_attenuation):
        """
        Set the minimum attenuation to *min_attenuation* (in dB).

        After setting, the min_attenuation is read back from the device.

        ``(self.error, self.min_attenuation)`` is returned.
        """
        self.error = 0
        min_attenuation = max(min_attenuation, 0)   # has to be > 0
        dct = self._do_cmds('SetMinAttenuation', locals())
        self._update(dct)
        dct = self._do_cmds('GetMinAttenuation', locals())
        self._update(dct)
        if self.error == 0:
            if not dct:
                self.min_attenuation = min_attenuation
            else:
                self.min_attenuation = float(self.min_attenuation)
        return self.error, self.min_attenuation

    def GetMinAttenuation(self):
        """
        Get the minimum attenuation in dB.

        ``(self.error, self.min_attenuation)`` is returned.
        """
        self.error = 0
        dct = self._do_cmds('GetMinAttenuation', locals())
        self._update(dct)
        return self.error, self.min_attenuation

    def SetMeasTime(self, meas_time):
        """
        Set the measurement time to *meas_time* (in s).

        After setting, the measurement time is read back from the device.

        ``(self.error, self.meas_time)`` is returned.
        """
        self.error = 0
        meas_time = max(meas_time, 0)   # has to be > 0
        dct = self._do_cmds('SetMeasTime', locals())
        self._update(dct)
        dct = self._do_cmds('GetMeasTime', locals())
        self._update(dct)
        if self.error == 0:
            if not dct:
                self.meas_time = meas_time
            else:
                self.meas_time = float(self.meas_time)
        return self.error, self.meas_time

    def GetMeasTime(self):
        """
        Get the measurement time in seconds.

        ``(self.error, self.meas_time)`` is returned.
        """
        self.error = 0
        dct = self._do_cmds('GetMeasTime', locals())
        self._update(dct)
        return self.error, self.meas_time

    def SetDetector(self, detector):
        """
        Set the measurement detector.

        detector has to de PEAK, QPEAK or AVERAGE

        After setting, the detector is read back from the device.

        ``(self.error, self.detector)`` is returned.
        """
        self.error = 0
        detector = detector.upper()
        if not detector in ('PEAK', 'QPEAK', 'AVERAGE'):
            self.error = -1
            raise UserWarning(f'Invalid detector {detector}.')
        dct = self._do_cmds('SetDetector', locals())
        self._update(dct)
        dct = self._do_cmds('GetDetector', locals())
        self._update(dct)
        if self.error == 0:
            if not dct:
                self.detector = detector
        return self.error, self.detector

    def GetDetector(self):
        """
        Get the detector.

        Values are PEAK, QPEAK, AVERAGE

        ``(self.error, self.detector)`` is returned.
        """
        self.error = 0
        dct = self._do_cmds('GetDetector', locals())
        self._update(dct)
        if not self.detector in ('PEAK', 'QPEAK', 'AVERAGE'):
            self.error = -1
            raise UserWarning(f'Unknown Detector {self.detector}.')
        return self.error, self.detector

    def SetPreamplifier(self, preamplifier):
        """
        Set the preamplifier.

        Values are ON or OFF

        After setting, the status is read back from the device.

        ``(self.error, self.preamplifier)`` is returned.
        """
        self.error = 0
        preamplifier = preamplifier.upper()
        if not preamplifier in ('ON', 'OFF'):
            self.error = -1
            raise UserWarning(f'Invalid Preamplifier Status {preamplifier}.')
        dct = self._do_cmds('SetPreamplifier', locals())
        self._update(dct)
        dct = self._do_cmds('GetPreamplifier', locals())
        self._update(dct)
        if self.error == 0:
            if not dct:
                self.preamplifier = preamplifier
        return self.error, self.preamplifier

    def GetPreamplifier(self):
        """
        Get the preamplifier status.

        Values are ON or OFF

        ``(self.error, self.preamplifier)`` is returned.
        """
        self.error = 0
        dct = self._do_cmds('GetPreamplifier', locals())
        self._update(dct)
        if not self.preamplifier in ('ON', 'OFF'):
            self.error = -1
            raise UserWarning(f'Unknown Preamplifier status {self.preamplifier}.')
        return self.error, self.preamplifier

    def SetResolutionBandwidth(self, rbw):
        """
        Set the resolution bandwidth  to *rbw* (in Hz).

        After setting, the bandwidth is read back from the device.

        ``(self.error, self.rbw)`` is returned.
        """
        self.error = 0
        dct = self._do_cmds('SetResolutionBandwidth', locals())
        self._update(dct)
        dct = self._do_cmds('GetResolutionBandwidth', locals())
        self._update(dct)
        if self.error == 0:
            if not dct:
                self.rbw = rbw
            else:
                self.rbw = float(self.rbw)
        return self.error, self.rbw

    def GetResolutionBandwidth(self):
        """
        Get the resolution bandwidth to *rbw* (in Hz).

        ``(self.error, self.rbw)`` is returned.
        """
        self.error = 0
        dct = self._do_cmds('GetResolutionBandwidth', locals())
        self._update(dct)
        return self.error, self.rbw



    def update_internal_unit(self, ch=None, unit='DBUV'):
        """
        Selects the output unit for the measured power values.
       
        Parameters:
            
        - *ch*: an integer specifiing the channel number of multi channel devices. Numbering is starting with 1.
        - *unit*: an string specifiing the unit for the measured data.

        The table shows the posibilities::
        
              Unit        SCPI notation
              Watt           W
              dB             DB
              dBm            DBM
              dBuV           DBUV

        """
        unit = unit
        channel = ch
        if not channel:
            channel = self.channel
        dct = self._do_cmds('Unit', locals())
        self._internal_unit = unit


if __name__ == '__main__':
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
                        unit: dBuV
                        attenuation: auto
                        rbw: auto
                        detector: PEAK
                        """)
        # rbw: 3e6
        ini = io.StringIO(ini)


    d = RECEIVER()
    d.Init(ini=ini, channel=1)
    if not ini:
        d.SetVirtual(False)

    err, des = d.GetDescription()
    print(f"Description: {des}")

    for freq in [9e3, 100e3, 500e3, 1e6, 10e6, 30e6]:
        print(f"Set freq to {freq:e} Hz")
        err, rfreq = d.SetFreq(freq)
        if err == 0:
            print(f"Freq set to {rfreq:e} Hz")
        else:
            print("Error setting freq")

    d.Quit()
