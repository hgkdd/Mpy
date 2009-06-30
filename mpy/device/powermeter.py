# -*- coding: utf-8 -*-

import re
from mpy.tools.Configuration import Configuration,strbool,fstrcmp
from scuq import *
from mpy.device.device import CONVERT, Device
from mpy.device.driver import DRIVER

class POWERMETER(DRIVER):
    """
    Child class for all py-drivers for power meters.
    
    The parent class is :class:`mpy.device.driver.DRIVER`.
    """
    ZeroCorrection=('OFF', 'ON')
    RANGE=('MANUAL', 'AUTO', 'AUTOONCE')
    
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
                     'rangemode': int,
                     'manrange': float,
                     'swr': float,
                     'sensor': str}}

    _FP=r'[-+]?(\d+(\.\d*)?|\d*\.\d+)([eE][-+]?\d+)?'
        
    def __init__(self):
        DRIVER.__init__(self)
        self._cmds={'SetFreq':  [("'FREQ %s HZ'%freq", None)],
                    'GetFreq':  [('FREQ?', r'FREQ (?P<freq>%s) HZ'%self._FP)],
                    'GetData':  [('POW?', r'POW (?P<power>%s) (?P<unit>)\S+'%self._FP)],
                    'GetDataNB':  [('POW?', r'POW (?P<power>%s) (?P<unit>)\S+'%self._FP)],
                    'Trigger': [('TRG', None)],
                    'ZeroOn':  [('ZERO ON', None)],
                    'ZeroOff':  [('ZERO OFF', None)],
                    'Quit':     [('QUIT', None)],
                    'GetDescription': [('*IDN?', r'(?P<IDN>.*)')]}
        self.freq= None
        self.power=None
        self.unit=None
        self._internal_unit='dBm'

    def SetFreq(self, freq):
        self.error=0
        dct=self._do_cmds('SetFreq', locals())
        self._update(dct)
        dct=self._do_cmds('GetFreq', locals())
        self._update(dct)
        if self.error == 0:
            if not dct:
                self.freq=freq
            else:
                self.freq=float(self.freq)
            #print self.freq
        return self.error, self.freq

    def Trigger(self):
        self.error=0
        dct=self._do_cmds('Trigger', locals())
        self._update(dct)
        #if self.error == 0:
        #    print "Device triggered."
        return self.error

    def Zero(self, state):        
        self.error=0
        if state.lower() == 'on':
            dct=self._do_cmds('ZeroOn', locals())
            self._update(dct)
        else:
            dct=self._do_cmds('ZeroOff', locals())
            self._update(dct)
        return self.error, 0

    def GetData(self):
        self.error=0
        dct=self._do_cmds('GetData', locals()) 
        self._update(dct)

        if self.error==0 and self.power:
            self.power=float(self.power)
            try:
                obj=quantities.Quantity(eval(self._internal_unit), self.power)
            except (AssertionError, NameError):
                self.power,self.unit=self.convert.c2scuq(self._internal_unit, float(self.power))
                obj=quantities.Quantity(self.unit, self.power)
        else:
            obj=None
        return self.error, obj

    def GetDataNB(self, retrigger):
        return self.GetData()

if __name__ == '__main__':
    import sys

    try:
        ini=sys.argv[1]
    except IndexError:
        ini=None


    d=POWERMETER()
    d.Init(ini)
    if not ini:
        d.SetVirtual(False)

    err, des=d.GetDescription()
    print "Description: %s"%des

    for freq in [100]:
        print "Set freq to %e Hz"%freq
        err, rfreq = d.SetFreq(freq)
        if err == 0:
            print "Freq set to %e Hz"%rfreq
        else:
            print "Error setting freq"


    d.Quit()
