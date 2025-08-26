# -*- coding: utf-8 -*-


import math

from scuq import *

from mpylab.device.driver import DRIVER
from mpylab.tools.Configuration import strbool


class POWERMETER(DRIVER):
    """
    Child class for all py-drivers for power meters.
    
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
                         'gpib': int,
                         'virtual': strbool,
                         'nr_of_channels': int},
                    'channel_%d':
                        {'name': str,
                         'filter': int,
                         'unit': str,
                         'resolution': int,
                         'rangemode': str,
                         'manrange': float,
                         'swr1': float,
                         'swr2': float,
                         'sensor': str}}
       
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
        - *gpib*: GPIB address of the device
        - *virtual*: 0, false or 1, true. Virtual device are usefull for testing and debugging.
        - *nr_of_channels*: indicates how many channel sections follow
    - Section *channel_%d* (*%d* may be 1, 2, ...)
        - *name*: a string identifying the channel.
        - *filter*: device specific integer specifying the filter used
        - *unit*: a string containing the unit of the returned power readings. 
          However, :mod:`scuq` will ignore dB-settings, and the returned power will contain 
          the unit anyway.
        - *resolution*: device specific integer giving the resolutuion of the returned power
        - *rangemode*: 'auto', 'autoonce', or 'manual'
        - *manrange*: fload specifiing the range in manual range mode
        - *swr*: VSWR of the measured two port. May be used in uncertainty calculations
        - *sensor*: string specifying the used power sensor. May be used in uncertainty calculations.

    """
    ZeroCorrection = ('OFF', 'ON')
    RANGE = ('MANUAL', 'AUTO', 'AUTOONCE')

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
                     'gpib': int,
                     'virtual': strbool,
                     'nr_of_channels': int},
                'channel_%d':
                    {'name': str,
                     'filter': int,
                     'unit': str,
                     'resolution': int,
                     'rangemode': str,
                     'manrange': float,
                     'swr1': float,
                     'swr2': float,
                     'sensor': str}}

    _FP = r'[-+]?(\d+(\.\d*)?|\d*\.\d+)([eE][-+]?\d+)?'

    def __init__(self):
        DRIVER.__init__(self)
        self._cmds = {'SetFreq': [("'FREQ %s HZ'%freq", None)],
                      'GetFreq': [('FREQ?', r'FREQ (?P<freq>%s) HZ' % self._FP)],
                      'GetData': [('POW?', r'POW (?P<power>%s) (?P<unit>)\S+' % self._FP)],
                      'GetDataNB': [('POW?', r'POW (?P<power>%s) (?P<unit>)\S+' % self._FP)],
                      'Trigger': [('TRG', None)],
                      'ZeroOn': [('ZERO ON', None)],
                      'ZeroOff': [('ZERO OFF', None)],
                      'Quit': [('QUIT', None)],
                      'GetDescription': [('*IDN?', r'(?P<IDN>.*)')]}
        self.freq = None
        self.power = None
        self.unit = None
        self.channel = None
        self._internal_unit = 'dBm'

    def SetFreq(self, freq):
        """
        Set the frequency to *freq* (in Hz). This is importend to use the correct correction from
        the sensor EEPROM.
        
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

    def Zero(self, state='on'):
        """
        If *state* is 'on', zero correction is tuned on.

        (self.error, 0) is returned.
        """
        self.error = 0
        # print 'aca tambien'
        if state.lower() == 'on':
            dct = self._do_cmds('ZeroOn', locals())
            self._update(dct)
        else:
            dct = self._do_cmds('ZeroOff', locals())
            self._update(dct)
        return self.error, 0

    def GetData(self):
        """
        Read a power measurement from the instrument.
        
        ``(self.error, obj)`` is returned where ``obj`` is a instance of 
        :class:`scuq.quantities.Quantity`.
        """
        self.error = 0
        dct = self._do_cmds('GetData', locals())
        self._update(dct)

        if self.error == 0 and self.power:
            self.update_internal_unit()
            swr_err = self.get_standard_mismatch_uncertainty()
            self.power = float(self.power)
            try:
                obj = quantities.Quantity(eval(self._internal_unit),
                                          ucomponents.UncertainInput(self.power, self.power * swr_err))
            except (AssertionError, NameError):
                self.power, self.unit = self.convert.c2scuq(self._internal_unit, float(self.power))
                obj = quantities.Quantity(self.unit,
                                          ucomponents.UncertainInput(self.power, self.power * swr_err))
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

    def update_internal_unit(self, ch=None, unit='DBM'):
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

    def get_standard_mismatch_uncertainty(self):
        """
        Returns the standard uncertainty (relative error) due to the mismatch between generator and load.
        
        *vswr1* and *vswr2* are the voltage standing wave ratio of generator and load.
        
        The uncertainty is returned on a linear scale (dB = 10 * log10 (1+a)).
        
        The expanded uncertainty is obtained by multiplying with the correct coverage factor. 
        Here, this is 0.997*sqrt(2) approx 1.4 (U-shaped distribution) for 95% coverage.
        """
        chdict = self.conf['channel_%d' % self.channel]
        vswr1 = chdict.get('swr1', 1.0)
        vswr2 = chdict.get('swr2', 1.0)
        # calculate reflection coefficients from vswr
        G1 = (vswr1 - 1.) / (vswr1 + 1.)
        G2 = (vswr2 - 1.) / (vswr2 + 1.)
        umax = (1. + G1 * G2) ** 2
        umin = (1. - G1 * G2) ** 2
        # print G1, G2, umax, umin
        width = umax - umin
        sigma = width / (2. * math.sqrt(2.))
        return sigma


if __name__ == '__main__':
    import sys

    try:
        ini = sys.argv[1]
    except IndexError:
        ini = None

    d = POWERMETER()
    d.Init(ini)
    if not ini:
        d.SetVirtual(False)

    err, des = d.GetDescription()
    print(("Description: %s" % des))

    for freq in [100]:
        print(("Set freq to %e Hz" % freq))
        err, rfreq = d.SetFreq(freq)
        if err == 0:
            print(("Freq set to %e Hz" % rfreq))
        else:
            print("Error setting freq")

    d.Quit()
