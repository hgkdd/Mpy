# -*- coding: utf-8 -*-
import time

from mpylab.device.amplifier import AMPLIFIER as AMP


class AMPLIFIER(AMP):
    conftmpl = AMP.conftmpl
    conftmpl['init_value']['gpib'] = int

    def __init__(self):
        AMP.__init__(self)
        self._cmds = {'POn': [("ON", None)],
                      'POff': [("SB", None)],
                      'Operate': [("ON", None)],
                      'Standby': [("SB", None)],
                      'GetDescription': [('*IDN?', r'(?P<IDN>.*)')]}
        self.term_chars = '\r\n'

    def Init(self, ini=None, channel=None):
        self.error = AMP.Init(self, ini, channel)
        self.POn()
        self.Operate()
        self.write('M1')
        self.write('ZA')
        return self.error

    def _getstat(self):
        dct = self.query('ST', r'(?P<st>.*)')
        B1 = int(dct['st'][:2], 16)
        E = int(dct['st'][2:], 16)
        # assert E==0, "IFI SMX25: error from ST command. error = %d"%E
        return B1, E

    def SetFreq(self, freq):
        AMP.SetFreq(self, freq)
        B1, E = self._getstat()
        # use ~B1 because active is LOW
        # bit 5 is Band 1 active
        # bit 6 is Band 2 active
        if (~B1 & 1 << 5) and (freq >= 250e6):
            self.write('B2')
            while ~B1 & 1 << 5 or E:
                B1, E = self._getstat()
                time.sleep(.4)
        elif (~B1 & 1 << 6) and (freq < 250e6):
            self.write('B1')
            while ~B1 & 1 << 6 or E:
                B1, E = self._getstat()
                time.sleep(.4)
        return self.error, freq


def main():
    import sys
    import io

    from mpylab.tools.util import format_block
    import scuq

    try:
        ini = sys.argv[1]
    except IndexError:
        ini = format_block("""
                         [description]
                         DESCRIPTION = SMX25
                         TYPE = AMPLIFIER
                         VENDOR = IFI
                         SERIALNR = 
                         DEVICEID = 
                         DRIVER =

                         [INIT_VALUE]
                         FSTART = 10e3
                         FSTOP = 1e9
                         FSTEP = 0.0
                         NR_OF_CHANNELS = 2
                         GPIB = 9
                         VIRTUAL = 0

                         [CHANNEL_1]
                         NAME = S21
                         UNIT = dB
                         INTERPOLATION = LOG
                         FILE = io.StringIO(format_block('''
                                                                FUNIT: Hz
                                                                UNIT: dB
                                                                ABSERROR: 0.5
                                                                80e6 50
                                                                1e9 50
                                                                '''))
                         [CHANNEL_2]
                         NAME = MAXIN
                         UNIT = dBm
                         INTERPOLATION = LOG
                         FILE = io.StringIO(format_block('''
                                                                FUNIT: Hz
                                                                UNIT: dBm
                                                                ABSERROR: 0.0
                                                                80e6 0
                                                                1e9 0
                                                                '''))
                         """)
        ini = io.StringIO(ini)

    amp = AMPLIFIER()
    err = amp.Init(ini)
    ctx = scuq.ucomponents.Context()
    while True:
        freq = float(eval(input("Freq / Hz: ")))
        if freq < 0:
            break
        amp.SetFreq(freq)
        err, uq = amp.GetData(what='S21')
        val, unc, unit = ctx.value_uncertainty_unit(uq)
        print((freq, uq, val, unc, unit))


if __name__ == '__main__':
    main()
