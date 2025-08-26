# -*- coding: utf-8 -*-

import bidict
from scuq import quantities
from scuq import si
from mpylab.device.driver import DRIVER
from mpylab.tools.Configuration import strbool, fstrcmp


class SIGNALGENERATOR(DRIVER):
    """
    Parent class for all py-drivers for signal generators.

    The parent class is :class:`mpylab.device.driver.DRIVER`.
    """
    AM_sources = ('INT1', 'INT2', 'EXT1', 'EXT2', 'EXT_AC', 'EXT_DC', 'TWOTONE_AC', 'TWOTONE_DC', 'OFF')
    AM_waveforms = ('SINE', 'SQUARE', 'TRIANGLE', 'NOISE', 'SAWTOOTH')
    AM_LFOut = ('OFF', 'ON')

    PM_sources = ('INT', 'EXT1', 'EXT2', 'OFF')
    PM_pol = ('NORMAL', 'INVERTED')

    ATT_modes = ('AUTO', 'FIXED')

    map = {}
    for name in ('AM_sources',
                 'AM_waveforms',
                 'AM_LFOut',
                 'PM_sources',
                 'PM_pol',
                 'ATT_modes'):
        map[name] = bidict.bidict([(a, a) for a in eval(name)])  # key=value

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
                     'visa': str,
                     'virtual': strbool},
                'channel_%d':
                    {'name': str,
                     'level': float,
                     'unit': str,
                     'leveloffset': float,
                     'levellimit': float,
                     'outputstate': str,
                     'attmode': str,
                     'attenuation': float}}

    # regular expression for a Fixed Point value in the raw string notation
    # this is the same as %e,%E,%f,%F known from scanf
    _FP = r'[-+]?(\d+(\.\d*)?|\d*\.\d+)([eE][-+]?\d+)?'

    # defintion from http://docs.python.org/library/re.html
    # _FP=r'[-+]?(\d+(\.\d*)?|\.\d+)([eE][-+]?\d+)?'

    def __init__(self):
        DRIVER.__init__(self)
        self._cmds = {'SetFreq': [("'FREQ %s HZ'%freq", None)],
                      'GetFreq': [('FREQ?', r'FREQ (?P<freq>%s) HZ' % self._FP)],
                      'SetLevel': [("'LEVEL %s %s'%(level,unit)", None)],
                      'GetLevel': [('LEVEL?', r'LEVEL (?P<level>%s) (?P<unit>\S+)' % self._FP)],
                      'ConfAM': [("'AM:FREQ %s HZ'%freq", None),
                                 ('AM:FREQ?', 'FREQ (?P<freq>%s) HZ' % self._FP),
                                 ("'AM:SOURCE %s'%source", None),
                                 ('AM:SOURCE?', 'SOURCE (?P<source>\S+)'),
                                 ("'AM:DEPTH %d %%'%(int(depth*100))", None),
                                 ('AM:DEPTH?', 'DEPTH (?P<depth>\d+)'),
                                 ("'AM:WAVEFRM %s'%(waveform)", None),
                                 ('AM:WAVEFRM?', 'WFRM (?P<waveform>\S+)'),
                                 ("'LF:OUT %s'%(LFOut)", None),
                                 ('LF:OUT??', 'LF (?P<LFOut>\S+)')],
                      'RFOn': [('RFOn', None)],
                      'RFOff': [('RFOff', None)],
                      'AMOn': [('AMOn', None)],
                      'AMOff': [('AMOff', None)],
                      'PMOn': [('PMOn', None)],
                      'PMOff': [('PMOff', None)],
                      'Quit': [('QUIT', None)],
                      'GetDescription': [('*IDN?', r'(?P<IDN>.*)')]}
        self.freq = None
        self.level = None
        self.unit = None
        self._internal_unit = 'dBm'

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

    def SetLevel(self, lv):
        self.error = 0
        level = lv.get_value(lv._unit)
        unit = lv._unit

        dct = self._do_cmds('SetLevel', locals())  # conversion to self._internal_unit is done inside _do_cmd
        self._update(dct)
        dct = self._do_cmds('GetLevel', locals())
        self._update(dct)

        if self.error == 0 and self.level:
            self.level = float(self.level)
            try:
                obj = quantities.Quantity(eval(self._internal_unit), self.level)
            except (AssertionError, NameError):
                self.level, self.unit = self.convert.c2scuq(self._internal_unit, float(self.level))
                obj = quantities.Quantity(self.unit, self.level)
        else:
            obj = None
        return self.error, obj

    def SetState(self, state):
        self.error = 0
        if state.lower() == 'on':
            dct = self._do_cmds('RFOn', locals())
            self._update(dct)
        else:
            dct = self._do_cmds('RFOff', locals())
            self._update(dct)
        return self.error, 0

    def ConfAM(self, source, freq, depth, waveform, LFOut):
        self.error = 0
        source = fstrcmp(source, self.AM_sources, n=1, cutoff=0, ignorecase=True)[0]
        source = self.map['AM_sources'][source]
        waveform = fstrcmp(waveform, self.AM_waveforms, n=1, cutoff=0, ignorecase=True)[0]
        waveform = self.map['AM_waveforms'][waveform]
        LFOut = fstrcmp(LFOut, self.AM_LFOut, n=1, cutoff=0, ignorecase=True)[0]
        LFOut = self.map['AM_LFOut'][LFOut]
        dct = self._do_cmds('ConfAM', locals())
        # print dct
        dct['source'] = self.map['AM_sources'].inverse[dct['source']]  # inverse mapping from bidict
        dct['waveform'] = self.map['AM_waveforms'].inverse[dct['waveform']]  # inverse mapping from bidict
        dct['LFOut'] = self.map['AM_LFOut'].inverse[dct['LFOut']]  # inverse mapping from bidict
        dct['depth'] = float(dct['depth'])
        if dct['depth'] > 1:  # depth was returned in PCT
            dct['depth'] = 0.01 * dct['depth']
        dct['freq'] = float(dct['freq'])
        # print dct
        self._update(dct)
        return self.error

    def ConfPM(self, source, freq, pol, width, delay):
        self.error = 0
        source = fstrcmp(source, self.PM_sources, n=1, cutoff=0, ignorecase=True)[0]
        source = self.map['PM_sources'][source]
        pol = fstrcmp(pol, self.PM_pol, n=1, cutoff=0, ignorecase=True)[0]
        pol = self.map['PM_pol'][pol]
        dct = self._do_cmds('ConfPM', locals())
        dct['source'] = self.map['PM_sources'][:dct['source']]
        dct['pol'] = self.map['PM_pol'][:dct['pol']]
        if 'period' in dct:
            dct['freq'] = 1. / float(dct['period'])
        self._update(dct)
        return self.error

    def SetAM(self, state):
        self.error = 0
        if state.lower() == 'on':
            dct = self._do_cmds('AMOn', locals())
            self._update(dct)
        else:
            dct = self._do_cmds('AMOff', locals())
            self._update(dct)
        return self.error, 0

    def SetPM(self, state):
        self.error = 0
        if state.lower() == 'on':
            dct = self._do_cmds('PMOn', locals())
            self._update(dct)
        else:
            dct = self._do_cmds('PMOff', locals())
            self._update(dct)
        return self.error, 0

    def RFOn(self):
        return self.SetState('ON')

    def RFOff(self):
        return self.SetState('OFF')

    def AMOn(self):
        return self.SetAM('ON')

    def AMOff(self):
        return self.SetAM('OFF')

    def PMOn(self):
        return self.SetPM('ON')

    def PMOff(self):
        return self.SetPM('OFF')


if __name__ == '__main__':
    import sys

    try:
        ini = sys.argv[1]
    except IndexError:
        ini = None

    sg = SIGNALGENERATOR()
    sg.Init(ini)
    if not ini:
        sg.SetVirtual(False)

    err, des = sg.GetDescription()
    # print "Description: %s"%des

    for freq in [100]:
        print(("Set freq to %e Hz" % freq))
        err, rfreq = sg.SetFreq(freq)
        if err == 0:
            print(("Freq set to %e Hz" % rfreq))
        else:
            print("Error setting freq")

    lv = quantities.Quantity(si.VOLT, 10)
    print(("Set level to %s" % lv))
    err, lv = sg.SetLevel(lv)
    if err == 0:
        print(("Level set to: %s" % lv))
    else:
        print("Error setting level")

    err = sg.ConfAM('int', 100e3, 0.8, 'siNe', 'oN')

    err = sg.ConfPM('int', 100e3, 'NORMAL', 1e-3, 0)

    print((sg.SetState('On')))
    print((sg.SetState('Off')))
    print((sg.SetPM('On')))
    print((sg.SetPM('OFF')))
    print((sg.SetAM('On')))
    print((sg.SetAM('off')))

    sg.Quit()
