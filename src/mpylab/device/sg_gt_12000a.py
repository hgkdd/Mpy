# -*- coding: utf-8 -*-

# Driver for Signal Generator Giga-tronics Series 12000A Microwave Synthesizer 

# implements a file-like class, StringIO, that reads and writes a string buffer
import io
# System-specific parameters and functions
import sys

# class library for the evaluation of scalar- and complex-valued uncertain quantities
from scuq import *

# parent class for all signal generators
from mpylab.device.signalgenerator import SIGNALGENERATOR as SGNLGNRTR


# enables you to control all kinds of measurement equipment through various busses (GPIB, RS232, USB)
# import pprint

# child class for the special signalgenerator
class SIGNALGENERATOR(SGNLGNRTR):
    # function for initialization
    def __init__(self):
        # initialize parent class
        SGNLGNRTR.__init__(self)
        # overwrite internal unit
        self._internal_unit = 'dBm'
        # overwrite defined commands, save as a dictionary
        # key is a string
        # value is a list of a tuples
        # a tuble consists of a command (string) and a template (string)
        # the template is only used for command that read
        self._cmds = {  # for initialization
            'Init': [('*RST', None),  # reset
                     ('CW 10 MZ', None),  # set frequency to 10 MHz
                     ('RF 0', None)],  # turn RF output off
            # set a certain continous wave frequecy
            'SetFreq': [("'CW %.1f HZ'%freq", None)],
            # read the continuos wave frequency value
            'GetFreq': [('OPCW', r'(?P<freq>%s)' % self._FP)],
            # set a continous wave power level
            'SetLevel': [("'PL %f DBM'%self.convert.scuq2c(unit, self._internal_unit, float(level))[0]", None)],
            # read the continous wave power level
            'GetLevel': [('OPPL', r'(?P<level>%s)' % (self._FP))],
            # configure amplitude modulation
            'ConfAM': [("'AD %d'%(min(80,int(depth*100)))", None)],
            # turn RF output on
            'RFOn': [('RF 1', None)],
            # turn RF output off
            'RFOff': [('RF 0', None)],
            # turn amplitude modulation on
            'AMOn': [('AM 2', None)],
            # turn amplitude modulation off
            'AMOff': [('AM 0', None)],
            # turn pulse modulation on
            'PMOn': [('PM 2', None)],
            # turn pulse modulation off
            'PMOff': [('PM 0', None)],
            # turn off after measurement has finished
            'Quit': [('RF 0', None)],
            # ask for the instrument id
            'GetDescription': [('*IDN?', r'(?P<IDN>.*)')]}

    def Init(self, ini=None, channel=None):
        # line feed character from PyVISA
        self.term_chars = '\n'
        # use standard channel 1 if no channel is set
        if channel is None:
            channel = 1
        # initialize the parent class of all signal generators
        self.error = SGNLGNRTR.Init(self, ini, channel)
        # string with current channel
        sec = 'channel_%d' % channel
        try:
            # set levelunit with the 'unit' of the parent class
            self.levelunit = self.conf[sec]['unit']
        except KeyError:
            # use the interal defined unit otherwise
            self.levelunit = self._internal_unit
        # delete all presets from the command list
        self._cmds['Preset'] = []
        # key, vals, actions
        presets = [('attmode',
                    [('0', 'auto'), ('1', 'fixed')],
                    [(':SPECIAL_FUNCTION 3', None), (':SPECIAL_FUNCTION 4', None)]),
                   ('attenuation',
                    None,
                    ("':SPECIAL_FUNCTION 23,%f'%self.convert.c2c(self.levelunit, self._internal_unit, float(v))", None)),
                   ('level',
                    None,
                    ("':RF_LEVEL:INTERNAL %f DBM'%self.convert.c2c(self.levelunit, self._internal_unit, float(v))",
                     None)),
                   ('outputstate',
                    [('1', 'on')],
                    [(':RF_POWER ON', None)])]

        for k, vals, actions in presets:
            # print k, vals, actions
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
                        description: 'GT_12000A'
                        type:        'SIGNALGENERATOR'
                        vendor:      'Giga-tronics'
                        serialnr:
                        deviceid:
                        driver:

                        [Init_Value]
                        fstart: 2e9
                        fstop: 8e9
                        fstep: 1
                        gpib: 6
                        virtual: 0

                        [Channel_1]
                        name: RFOut
                        level: -100
                        unit: 'dBm'
                        outputstate: 0
                        """)
        ini = io.StringIO(ini)

    # define a signal level
    lv = quantities.Quantity(si.WATT, 1e-2)
    # define a frequency
    fr = 1e9

    # load the signalgenerator class
    sg = SIGNALGENERATOR()

    # try to initialize
    err = sg.Init(ini)
    assert err == 0, 'Init() fails with error %d' % (err)

    # try to set frequency
    err, freq = sg.SetFreq(fr)
    assert err == 0, 'SetFreq() fails with error %d' % (err)
    assert freq == fr, 'SetFreq() returns freq=%e instead of %e' % (freq, fr)

    # try to switch RF on
    err, _ = sg.RFOn()
    assert err == 0, 'RFOn() fails with error %d' % (err)

    # try to set a level
    err, level = sg.SetLevel(lv)
    assert err == 0, 'SetLevel() fails with error %d' % (err)
    assert level == lv, 'SetLevel() returns level=%s instead of %s' % (level, lv)

    # try to quit
    err = sg.Quit()
    assert err == 0, 'Quit() fails with error %d' % (err)


if __name__ == '__main__':
    main()
