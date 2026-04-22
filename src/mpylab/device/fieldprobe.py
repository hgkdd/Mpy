# -*- coding: utf-8 -*-

from mpylab.device.driver import DRIVER
from mpylab.tools.configuration import strbool
from mpylab.tools.regular_expressions import FP


class FIELDPROBE(DRIVER):
    """
    Parent class for all py-drivers for field probes.

    The parent class is :class:`mpylab.device.driver.DRIVER`.
    """

    conftmpl = {'description':
                    {'description': str,
                     'type': str,
                     'vendor': str,
                     'serialnr': str,
                     'deviceid': str,
                     'driver': str,
                     'nr_of_channels': int},
                'init_value':
                    {'fstart': float,
                     'fstop': float,
                     'fstep': float,
                     'gpib': int,
                     'visa': str,
                     'virtual': strbool},
                'channel_%d':
                    {'name': str,
                     'unit': str}}

    # regular expression for a Fixed Point value in the raw string notation
    # this is the same as %e,%E,%f,%F known from scanf
    _FP = FP

    def __init__(self, SearchPaths=None):
        DRIVER.__init__(self, SearchPaths=SearchPaths)
        self._cmds = {'SetFreq': [("FREQ {freq} HZ", None)],
                      'GetFreq': [("FREQ?", rf'FREQ (?P<freq>{self._FP}) HZ')],
                      'Zero': [("Zero {ZeroState}", None)],
                      'Trigger': [("Trigger", None)],
                      'GetData': [("Data?", r'(?P<DATA>.*)')],
                      'GetDataNB': [("Data?", r'(?P<DATA>.*)'),
                                    ("ReTrigger {RETRIGGER}", None)],
                      'GetBatteryState': [("Battery?", r'(?P<BATT>\d+)')],
                      'Quit': [('QUIT', None)],
                      'GetDescription': [('*IDN?', r'(?P<IDN>.*)')],
                      'GetWaveform': [('GetWaveform', None)]}
        self.freq = None
        self.unit = None
        self._internal_unit = 'Voverm'

    def SetFreq(self, freq):
        # set a certain frequency
        self.error = 0  # reset error number
        dct = self._do_cmds('SetFreq', locals())
        self._update(dct)
        dct = self._do_cmds('GetFreq', locals())
        self._update(dct)
        if self.error == 0:
            self.freq = float(self.freq)
        return self.error, self.freq

    def GetFreq(self):
        self.error = 0
        dct = self._do_cmds('GetFreq', locals())
        self._update(dct)
        if self.error == 0 and self.freq is not None:
            self.freq = float(self.freq)
        return self.error, self.freq

    def Zero(self, state):
        self.error = 0
        self.ZeroState = 'off'
        if state.lower() == 'on':
            self.ZeroState = 'on'
        dct = self._do_cmds('Zero', locals())
        self._update(dct)
        return self.error, self.ZeroState

    def Trigger(self):
        self.error = 0
        dct = self._do_cmds('Trigger', locals())
        self._update(dct)
        return self.error, 0

    def GetData(self):
        self.error = 0
        dct = self._do_cmds('GetData', locals())
        self._update(dct)
        return self.error, self.DATA

    def GetDataNB(self, retrigger):
        self.error = 0
        RETRIGGER = 'OFF'
        if retrigger.lower() == 'on':
            RETRIGGER = 'ON'
        dct = self._do_cmds('GetDataNB', locals())
        self._update(dct)
        return self.error, self.DATA

    def GetBatteryState(self):
        self.error = 0
        dct = self._do_cmds('GetBatteryState', locals())
        self._update(dct)
        return self.error, self.BATT

    def GetWaveform(self):
        return -1, None, None, None, None


if __name__ == '__main__':
    import sys

    try:
        ini = sys.argv[1]
    except IndexError:
        ini = None

    dev = FIELDPROBE()
    dev.Init(ini)
    if not ini:
        dev.SetVirtual(False)

    err, des = dev.GetDescription()
    # print "Description: %s"%des

    for freq in [100]:
        print(f"Set freq to {freq:e} Hz")
        err, rfreq = dev.SetFreq(freq)
        if err == 0:
            print(f"Freq set to {rfreq:e} Hz")
        else:
            print("Error setting freq")

    dev.Quit()
