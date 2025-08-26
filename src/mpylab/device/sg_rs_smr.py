# -*- coding: utf-8 -*-
import sys
import io
from scuq import *
from .signalgenerator import SIGNALGENERATOR


# import pprint

class SMR(SIGNALGENERATOR):
    def __init__(self):
        SIGNALGENERATOR.__init__(self)
        self._internal_unit = 'dBm'
        self._cmds = {'Init': [('*RST', None),
                               (':OUTPUT1:STATE OFF', None)],
                      'SetFreq': [("':SOURCE:FREQ:CW %fHz'%freq", None)],
                      'GetFreq': [(':SOURCE:FREQ:CW?', r'(?P<freq>%s)' % self._FP)],
                      'SetLevel': [(
                                   "':SOUR:POW:LEV:IMM:AMPL %f'%self.convert.scuq2c(unit, self._internal_unit, float(level))[0]",
                                   None)],
                      'GetLevel': [(':SOUR:POW:LEV:IMM:AMPL?', r'(?P<level>%s)' % (self._FP))],
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
                      'RFOn': [(':OUTPUT1:STATE ON', None)],
                      'RFOff': [(':OUTPUT1:STATE OFF', None)],
                      'AMOn': [(':SOUR:AM:STAT ON', None)],
                      'AMOff': [(':SOUR:AM:STAT OFF', None)],
                      'PMOn': [(':SOUR:PULM:STAT ON', None)],
                      'PMOff': [(':SOUR:PULM:STAT OFF', None)],
                      'Quit': [(':OUTPUT1:STATE OFF', None)],
                      'GetDescription': [('*IDN?', r'(?P<IDN>.*)')]}

    def Init(self, ini=None, channel=None):
        if channel is None:
            channel = 1
        self.error = SIGNALGENERATOR.Init(self, ini, channel)
        sec = 'channel_%d' % channel
        try:
            self.levelunit = self.conf[sec]['unit']
        except KeyError:
            self.levelunit = self._internal_unit

        self._cmds['Preset'] = []
        # key, vals, actions
        presets = [('attmode',
                    [('0', 'auto'), ('1', 'fixed')],
                    [(':OUTPUT:AMOD AUTO', None), (':OUTPUT:AMOD FIXED', None)]),
                   ('attenuation',
                    None,
                    ("':OUTP:ATT %f dB'%self.convert.c2c(self.levelunit, self._internal_unit, float(v))", None)),
                   ('leveloffset',
                    None,
                    ("':SOUR:POW:LEV:IMM:AMPL:OFFS %f'%self.convert.c2c(self.levelunit, self._internal_unit, float(v))",
                     None)),
                   ('levellimit',
                    None,
                    ("':SOUR:POW:LIM:AMPL %f'%self.convert.c2c(self.levelunit, self._internal_unit, float(v))", None)),
                   ('level',
                    None,
                    ("':SOUR:POW:LEV:IMM:AMPL %f'%self.convert.c2c(self.levelunit, self._internal_unit, float(v))",
                     None)),
                   ('outputstate',
                    [('1', 'on')],
                    [(':OUTPUT1:STATE ON', None)])]

        for k, vals, actions in presets:
            print((k, vals, actions))
            try:
                v = self.conf[sec][k]
                # print sec, k, v
                if (vals is None):  # no comparision
                    # print actions[0], self.convert.c2c(self.levelunit, self._internal_unit, float(v)), float(v), self.levelunit
                    # print eval(actions[0])
                    self._cmds['Preset'].append((eval(actions[0]), actions[1]))
                else:
                    for idx, vi in enumerate(vals):
                        if v.lower() in vi:
                            self._cmds['Preset'].append(actions[idx])
            except KeyError:
                pass
        dct = self._do_cmds('Preset', locals())
        self._update(dct)
        # pprint.pprint(self._cmds)
        return self.error


def main():
    from mpylab.tools.util import format_block

    try:
        ini = sys.argv[1]
    except IndexError:
        ini = format_block("""
                        [DESCRIPTION]
                        description: 'SMR'
                        type:        'SIGNALGENERATOR'
                        vendor:      'Rohde&Schwarz'
                        serialnr:
                        deviceid:
                        driver:

                        [Init_Value]
                        fstart: 100e6
                        fstop: 20e9
                        fstep: 1
                        gpib: 15
                        virtual: 1

                        [Channel_1]
                        name: RFOut
                        level: -100
                        unit: 'dBm'
                        outpoutstate: 0
                        """)
        ini = io.StringIO(ini)

    lv = quantities.Quantity(si.WATT, 1e-4)
    fr = 300e6

    sg = SMR()
    err = sg.Init(ini)
    assert err == 0, 'Init() fails with error %d' % (err)
    err, freq = sg.SetFreq(fr)
    assert err == 0, 'SetFreq() fails with error %d' % (err)
    assert freq == fr, 'SetFreq() returns freq=%e instead of %e' % (freq, fr)
    err, _ = sg.RFOn()
    assert err == 0, 'RFOn() fails with error %d' % (err)
    err, level = sg.SetLevel(lv)
    assert err == 0, 'SetLevel() fails with error %d' % (err)
    assert level == lv, 'SetLevel() returns level=%s instead of %s' % (level, lv)
    err = sg.Quit()
    assert err == 0, 'Quit() fails with error %d' % (err)


if __name__ == '__main__':
    main()
