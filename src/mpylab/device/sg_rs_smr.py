# -*- coding: utf-8 -*-
"""mpylab.device.sg_rs_smr module."""
import sys
import io
from scuq import *
from mpylab.device.signalgenerator import SIGNALGENERATOR as SGNLGNRTR

# import pprint

class SIGNALGENERATOR(SGNLGNRTR):
    """SIGNALGENERATOR class."""
    def __init__(self, **kw):
        SGNLGNRTR.__init__(self, **kw)
        self._internal_unit = 'dBm'
        self._cmds = {'Init': [('*RST', None),
                               (':OUTPUT1:STATE OFF', None)],
                      'SetFreq': [(':SOURCE:FREQ:CW {freq:f}Hz', None)],
                      'GetFreq': [(':SOURCE:FREQ:CW?', rf'(?P<freq>{self._FP})')],
                      'SetLevel': [
                                    (
                                        lambda self, unit, level, **kwargs:
                                            f":SOUR:POW:LEV:IMM:AMPL {self.convert.scuq2c(unit, self._internal_unit, float(level))[0]:f}",
                                        None
                                    )
                                ],
                      'GetLevel': [(':SOUR:POW:LEV:IMM:AMPL?', rf'(?P<level>{self._FP})')],
                      'ConfAM': [
                                ("AM:FREQ {freq} HZ", None),
                                ('AM:FREQ?', lambda self, **kwargs: rf'FREQ (?P<freq>{self._FP}) HZ'),

                                ("AM:SOURCE {source}", None),
                                ('AM:SOURCE?', r'SOURCE (?P<source>\S+)'),

                                (
                                    lambda self, depth, **kwargs:
                                        f"AM:DEPTH {int(depth * 100):d} %",
                                    None
                                ),
                                ('AM:DEPTH?', r'DEPTH (?P<depth>\d+)'),

                                ("AM:WAVEFRM {waveform}", None),
                                ('AM:WAVEFRM?', r'WFRM (?P<waveform>\S+)'),

                                ("LF:OUT {LFOut}", None),
                                ('LF:OUT??', r'LF (?P<LFOut>\S+)')
                                ],
                      'RFOn': [(':OUTPUT1:STATE ON', None)],
                      'RFOff': [(':OUTPUT1:STATE OFF', None)],
                      'AMOn': [(':SOUR:AM:STAT ON', None)],
                      'AMOff': [(':SOUR:AM:STAT OFF', None)],
                      'PMOn': [(':SOUR:PULM:STAT ON', None)],
                      'PMOff': [(':SOUR:PULM:STAT OFF', None)],
                      'Quit': [(':OUTPUT1:STATE OFF', None)],
                      'GetDescription': [('*IDN?', r'(?P<IDN>.*)')]}

    def Init(self, ini=None, channel=None):
        """Init method."""
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
        # presets = [('attmode',
        #             [('0', 'auto'), ('1', 'fixed')],
        #             [(':OUTPUT:AMOD AUTO', None), (':OUTPUT:AMOD FIXED', None)]),
        #            ('attenuation',
        #             None,
        #             ("':OUTP:ATT %f dB'%self.convert.c2c(self.levelunit, self._internal_unit, float(v))", None)),
        #            ('leveloffset',
        #             None,
        #             ("':SOUR:POW:LEV:IMM:AMPL:OFFS %f'%self.convert.c2c(self.levelunit, self._internal_unit, float(v))",
        #              None)),
        #            ('levellimit',
        #             None,
        #             ("':SOUR:POW:LIM:AMPL %f'%self.convert.c2c(self.levelunit, self._internal_unit, float(v))", None)),
        #            ('level',
        #             None,
        #             ("':SOUR:POW:LEV:IMM:AMPL %f'%self.convert.c2c(self.levelunit, self._internal_unit, float(v))",
        #              None)),
        #            ('outputstate',
        #             [('1', 'on')],
        #             [(':OUTPUT1:STATE ON', None)])]
        #
        # for k, vals, actions in presets:
        #     print((k, vals, actions))
        #     try:
        #         v = self.conf[sec][k]
        #         # print sec, k, v
        #         if (vals is None):  # no comparision
        #             # print actions[0], self.convert.c2c(self.levelunit, self._internal_unit, float(v)), float(v), self.levelunit
        #             # print eval(actions[0])
        #             self._cmds['Preset'].append((eval(actions[0]), actions[1]))
        #         else:
        #             for idx, vi in enumerate(vals):
        #                 if v.lower() in vi:
        #                     self._cmds['Preset'].append(actions[idx])
        #     except KeyError:
        #         pass
        # dct = self._do_cmds('Preset', locals())
        # self._update(dct)
        presets = [
            (
                'attmode',
                [('0', 'auto'), ('1', 'fixed')],
                [
                    (':OUTPUT:AMOD AUTO', None),
                    (':OUTPUT:AMOD FIXED', None)
                ]
            ),
            (
                'attenuation',
                None,
                (
                    lambda self, v, **kwargs:
                    f":OUTP:ATT {self.convert.c2c(self.levelunit, self._internal_unit, float(v)):f} dB",
                    None
                )
            ),
            (
                'leveloffset',
                None,
                (
                    lambda self, v, **kwargs:
                    f":SOUR:POW:LEV:IMM:AMPL:OFFS {self.convert.c2c(self.levelunit, self._internal_unit, float(v)):f}",
                    None
                )
            ),
            (
                'levellimit',
                None,
                (
                    lambda self, v, **kwargs:
                    f":SOUR:POW:LIM:AMPL {self.convert.c2c(self.levelunit, self._internal_unit, float(v)):f}",
                    None
                )
            ),
            (
                'level',
                None,
                (
                    lambda self, v, **kwargs:
                    f":SOUR:POW:LEV:IMM:AMPL {self.convert.c2c(self.levelunit, self._internal_unit, float(v)):f}",
                    None
                )
            ),
            (
                'outputstate',
                [('1', 'on')],
                [
                    (':OUTPUT1:STATE ON', None)
                ]
            )
        ]

        self._apply_presets(presets, sec)

        dct = self._do_cmds('Preset', locals())
        self._update(dct)
        # pprint.pprint(self._cmds)
        return self.error


def main():
    """main function."""
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

    sg = SIGNALGENERATOR()
    err = sg.Init(ini)
    assert err == 0, f'Init() fails with error {err}'
    err, freq = sg.SetFreq(fr)
    assert err == 0, f'SetFreq() fails with error {err}'
    assert freq == fr, f'SetFreq() returns freq={freq:e} instead of {fr:e}'
    err, _ = sg.RFOn()
    assert err == 0, f'RFOn() fails with error {err}'
    err, level = sg.SetLevel(lv)
    assert err == 0, f'SetLevel() fails with error {err}'
    assert level == lv, f'SetLevel() returns level={level} instead of {lv}'
    err = sg.Quit()
    assert err == 0, f'Quit() fails with error {err}'


if __name__ == '__main__':
    main()
