# -*- coding: utf-8 -*-

import re
import functools
from mpy.tools.Configuration import Configuration,strbool,fstrcmp
from scuq import *
from mpy.device.device import CONVERT, Device
from mpy.device.driver import DRIVER

class SPECTRUMANALYZER(DRIVER):
    """
    Parent class of all py-drivers for spectrum analyzers.
    
    The parent class is :class:`mpy.device.driver.DRIVER`.
    """
    
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
        self._cmds={'SetCenterFreq':  [("'CENTERFREQ %s HZ'%cfreq", None)],
                    'GetCenterFreq':  [('CENTERFREQ?', r'CENTERFREQ (?P<cfreq>%s) HZ'%self._FP)],
                    'SetSpan':  [("'SPAN %s HZ'%span", None)],
                    'GetSpan':  [('SPAN?', r'SPAN (?P<span>%s) HZ'%self._FP)],
                    'SetStartFreq':  [("'STARTFREQ %s HZ'%stfreq", None)],
                    'GetStartFreq':  [('STARTFREQ?', r'STARTFREQ (?P<stfreq>%s) HZ'%self._FP)],
                    'SetStopFreq':  [("'STOPFREQ %s HZ'%spfreq", None)],
                    'GetStopFreq':  [('STOPFREQ?', r'STOPFREQ (?P<spfreq>%s) HZ'%self._FP)],
                    'SetRBW':  [("'RBW %s HZ'%rbw", None)],
                    'GetRBW':  [('RBW?', r'RBW (?P<rbw>%s) HZ'%self._FP)],
                    'SetVBW':  [("'VBW %s HZ'%vbw", None)],
                    'GetVBW':  [('VBW?', r'VBW (?P<vbw>%s) HZ'%self._FP)],
                    'SetRefLevel':  [("'REFLEVEL %s DBM'%level", None)],
                    'GetRefLevel':  [('REFLEVEL?', r'REFLEVEL (?P<level>%s) DBM'%self._FP)],
                    'SetAtt':  [("'ATT %s DB'%freq", None)],
                    'GetAtt':  [('ATT?', r'ATT (?P<att>%s) DB'%self._FP)],
                    'SetAttAuto':  [("ATT -1", None)],
                    'SetPreAmp':  [("'PREAMP %s DB'%freq", None)],
                    'GetPreAmp':  [('PREAMP?', r'PREAMP (?P<preamp>%s) DB'%self._FP)],
                    'SetDetector':  [("'DET %s'%det", None)],
                    'GetDetector':  [('DET?', r'DET (?P<det>%s)'%self._FP)],
                    'SetTraceMode':  [("'TMODE %s'%tmode", None)],
                    'GetTraceMode':  [('TMODE?', r'TMODE (?P<tmode>%s)'%self._FP)],
                    'SetTrace':  [("'TRACE %d'%trace", None)],
                    'GetTrace':  [('TRACE?', r'TRACE (?P<trace>\d+)')],
                    'SetSweepCount':  [("'SWEEPCOUNT %d'%scount", None)],
                    'GetSweepCount':  [('SWEEPCOUNT?', r'SWEEPCOUNT (?P<scount>\d+)')],
                    'SetSweepTime':  [("'SWEEPTIME %s us'%stime", None)],
                    'GetSweepTime':  [('SWEEPTIME?', r'SWEEPTIME (?P<stime>%s) us'%self._FP)],
                    'GetSpectrum':  [('DATA?', r'DATA (?P<power>%s)'%self._FP)],
                    'GetSpectrumNB':  [('DATA?', r'DATA (?P<power>%s)'%self._FP)],
                    'SetTriggerMode': [('TRGMODE %d'%tmode, None)],
                    'SetTriggerDelay':  [('TRGDELAY %s us'%tdelay, None)],
                    'SetWindow':  [('WINDOW %d'%window, None)],
                    'Quit':     [('QUIT', None)],
                    'GetDescription': [('*IDN?', r'(?P<IDN>.*)')]}

        _setgetlist=[("SetCenterFreq", "GetCenterFreq", "cfreq", float),
                     ("SetSpan", "GetSpan", "span", float),
                     ("SetStartFreq", "GetStartFreq", "stfreq", float),
                     ("SetStopFreq", "GetStopFreq", "spfreq", float),
                     ("SetRBW", "GetRBW", "rbw", float),
                     ("SetVBW", "GetVBW", "vbw", float),
                     ("SetRefLevel", "GetRefLevel", "reflevel", float),
                     ("SetAtt", "GetAtt", "att", float),
                     ("SetPreAmp", "GetPreAmp", "preamp", float),
                     ("SetDetector", "GetDetector", "det", int),
                     ("SetTraceMode", "GetTraceMode", "tmode", int),
                     ("SetTrace", "GetTrace", "trace", int),
                     ("SetSweepCount", "GetSweepCount", "scount", int),
                     ("SetSweepTime", "GetSweepTime", "stime", float)]

        for setter, getter, what, type_ in _setgetlist:
            setattr(self, what, None)
            # closure...
            setattr(self, setter, functools.partial(self._SetGetSomething, setter=setter, getter=getter, type_=type_))

        self.power=None
        self.unit=None
        self._internal_unit='dBm'

    def _SetGetSomething(self, setter, getter, something, type_):
        self.error=0
        dct=self._do_cmds(setter, locals())
        self._update(dct)
        dct=self._do_cmds(getter, locals())
        self._update(dct)
        if self.error == 0:
            if not dct:
                setattr(self, something, eval(something))
            else:
                setattr(self, something, type_(getattr(self, something)))
        return self.error, getattr(self, something)


#     def SetCenterFreq(self, cfreq):
#         self.error=0
#         dct=self._do_cmds('SetCenterFreq', locals())
#         self._update(dct)
#         dct=self._do_cmds('GetCenterFreq', locals())
#         self._update(dct)
#         if self.error == 0:
#             if not dct:
#                 self.cfreq=cfreq
#             else:
#                 self.cfreq=float(self.cfreq)
#             #print self.freq
#         return self.error, self.cfreq


if __name__ == '__main__':
    import sys

    try:
        ini=sys.argv[1]
    except IndexError:
        ini=None


    d=SPECTRUMANALYZER()
    d.Init(ini)
    if not ini:
        d.SetVirtual(False)

    err, des=d.GetDescription()
    print "Description: %s"%des

    for cfreq in [100]:
        print "Set center freq to %e Hz"%cfreq
        err, rfreq = d.SetCenterFreq(cfreq)
        if err == 0:
            print "Center Freq set to %e Hz"%rfreq
        else:
            print "Error setting center freq"


    d.Quit()
