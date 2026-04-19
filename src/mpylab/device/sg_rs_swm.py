# -*- coding: utf-8 -*-

import io
import sys

from mpylab.device.signalgenerator import SIGNALGENERATOR as SGNLGNRTR


# import pprint


class SIGNALGENERATOR(SGNLGNRTR):
    def __init__(self, **kw):
        SGNLGNRTR.__init__(self, **kw)
        self._internal_unit = 'dBm'
        self._cmds = {'Init': [('*RST', None),
                               (':FREQ:CW 10MHZ', None),
                               (':RF_POWER OFF', None)],
                      'SetFreq': [("':FREQUENCY:CW {freq:.4f} Hz'", None)],
                      'GetFreq': [(':FREQUENCY:CW?', rf':FREQUENCY:CW (?P<freq>{self._FP})')],
                      'SetLevel': [
                                    (
                                        lambda self, unit, level, **kwargs:
                                            f":RF_LEVEL:INTERNAL {self.convert.scuq2c(unit, self._internal_unit, float(level))[0]:f} DBM",
                                        None
                                    )
                                ],
                      'GetLevel': [(':RF_LEVEL:INTERNAL?', rf':RF_LEVEL:INTERNAL (?P<level>{self._FP})')],
                      'ConfAM': [
                                    (
                                        lambda self, depth, **kwargs:
                                            f":MODULATION:AM:INTERNAL {min(80, int(depth * 100)):d} PCT",
                                        None
                                    ),
                                    (
                                        ':MODULATION:AM:INTERNAL?',
                                        r':MODULATION:AM:INTERNAL (?P<depth>\d+) PCT'
                                    )
                                ],
                      'RFOn': [(':RF_POWER ON', None)],
                      'RFOff': [(':RF_POWER OFF', None)],
                      'AMOn': [(':MODULATION:AM:INTERNAL ON', None)],
                      'AMOff': [(':MODULATION:AM:INTERNAL OFF', None)],
                      'PMOn': [(':MODULATION:PULS:INTERNAL ON', None)],
                      'PMOff': [(':MODULATION:PULS:INTERNAL OFF', None)],
                      'Quit': [(':RF_POWER OFF', None)],
                      'GetDescription': [('*IDN?', r'(?P<IDN>.*)')]}

    def Init(self, ini=None, channel=None):
        self.term_chars = '\n'
        if channel is None:
            channel = 1
        self.error = SGNLGNRTR.Init(self, ini, channel)
        sec = f'channel_{channel}'
        try:
            self.levelunit = self.conf[sec]['unit']
        except KeyError:
            self.levelunit = self._internal_unit

        self._cmds['Preset'] = []
        # key, vals, actions
        # presets = [('attmode',
        #             [('0', 'auto'), ('1', 'fixed')],
        #             [(':SPECIAL_FUNCTION 3', None), (':SPECIAL_FUNCTION 4', None)]),
        #            ('attenuation',
        #             None,
        #             ("':SPECIAL_FUNCTION 23,%f'%self.convert.c2c(self.levelunit, self._internal_unit, float(v))", None)),
        #            ('level',
        #             None,
        #             ("':RF_LEVEL:INTERNAL %f DBM'%self.convert.c2c(self.levelunit, self._internal_unit, float(v))",
        #              None)),
        #            ('outputstate',
        #             [('1', 'on')],
        #             [(':RF_POWER ON', None)])]
        #
        # for k, vals, actions in presets:
        #     # print k, vals, actions
        #     try:
        #         v = self.conf[sec][k]
        #         # print sec, k, v
        #         if vals is None:  # no comparision
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
                    (':SPECIAL_FUNCTION 3', None),
                    (':SPECIAL_FUNCTION 4', None)
                ]
            ),
            (
                'attenuation',
                None,
                (
                    lambda self, v, **kwargs:
                    f":SPECIAL_FUNCTION 23,{self.convert.c2c(self.levelunit, self._internal_unit, float(v)):f}",
                    None
                )
            ),
            (
                'level',
                None,
                (
                    lambda self, v, **kwargs:
                    f":RF_LEVEL:INTERNAL {self.convert.c2c(self.levelunit, self._internal_unit, float(v)):f} DBM",
                    None
                )
            ),
            (
                'outputstate',
                [('1', 'on')],
                [
                    (':RF_POWER ON', None)
                ]
            )
        ]

        for k, vals, actions in presets:
            try:
                v = self.conf[sec][k]

                if vals is None:
                    cmd, tmpl = actions

                    if callable(cmd):
                        self._cmds['Preset'].append(
                            (
                                lambda _self, _cmd=cmd, _v=v, **kwargs:
                                _cmd(_self, v=_v, **kwargs),
                                tmpl
                            )
                        )
                    else:
                        self._cmds['Preset'].append((cmd, tmpl))

                else:
                    v_cmp = str(v).lower()
                    for idx, vi in enumerate(vals):
                        if v_cmp in vi:
                            self._cmds['Preset'].append(actions[idx])

            except KeyError:
                pass

        dct = self._do_cmds('Preset', locals())
        self._update(dct)
        # pprint.pprint(self._cmds)
        return self.error


def main():
    from mpylab.tools.util import format_block
    from mpylab.device.signalgenerator_ui import SignalGeneratorWidget as UI

    try:
        ini = sys.argv[1]
    except IndexError:
        ini = format_block("""
                        [DESCRIPTION]
                        description: 'SWM'
                        type:        'SIGNALGENERATOR'
                        vendor:      'Rohde&Schwarz'
                        serialnr:
                        deviceid:
                        driver:

                        [Init_Value]
                        fstart: 100e6
                        fstop: 18e9
                        fstep: 1
                        gpib: 15
                        virtual: 0

                        [Channel_1]
                        name: RFOut
                        level: -100
                        unit: 'dBm'
                        outpoutstate: 0
                        """)
        ini = io.StringIO(ini)

    sg = SIGNALGENERATOR()
    ui = UI(sg, ini=ini)
    ui.configure_traits()


if __name__ == '__main__':
    main()
