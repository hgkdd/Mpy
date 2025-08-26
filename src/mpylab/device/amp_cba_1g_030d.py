# -*- coding: utf-8 -*-
from simpleeval import simple_eval

from mpylab.device.amplifier import AMPLIFIER as AMP


class AMPLIFIER(AMP):
    conftmpl = AMP.conftmpl
    conftmpl['init_value']['gpib'] = int

    def __init__(self):
        AMP.__init__(self)
        self._cmds = {'POn': [("RFON", None)],
                      'POff': [("RFOF", None)],
                      'Operate': [("ZEROATT", None)],
                      'Standby': [("FULLATT", None)],
                      'GetDescription': [('*IDN?', r'(?P<IDN>.*)')]}
        self.term_chars = '\r\n'
        self.error = None

    def Init(self, ini=None, channel=None):
        self.error = AMP.Init(self, ini, channel)
        self.POn()
        self.Operate()
        return self.error

    def Quit(self):
        self.POff()
        self.Standby()
        return 0

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
                         DESCRIPTION = CBA1G-030D
                         TYPE = AMPLIFIER
                         VENDOR = AMETEK
                         SERIALNR = 
                         DEVICEID = 
                         DRIVER =

                         [INIT_VALUE]
                         FSTART = 1e6
                         FSTOP = 1e9
                         FSTEP = 0.0
                         NR_OF_CHANNELS = 2
                         GPIB = 2
                         VIRTUAL = 0

                         [CHANNEL_1]
                         NAME = S21
                         UNIT = dB
                         INTERPOLATION = LOG
                         FILE = io.StringIO(format_block('''
                                                                FUNIT: Hz
                                                                UNIT: dB
                                                                ABSERROR: 0.0
                                                                1e6 45
                                                                1e9 45
                                                                '''))
                         [CHANNEL_2]
                         NAME = MAXIN
                         UNIT = dBm
                         INTERPOLATION = LOG
                         FILE = io.StringIO(format_block('''
                                                                FUNIT: Hz
                                                                UNIT: dBm
                                                                ABSERROR: 0.0
                                                                1e6 0
                                                                1e9 0
                                                                '''))
                         """)
        ini = io.StringIO(ini)

    amp = AMPLIFIER()
    err = amp.Init(ini)
    print(amp.GetDescription())
    ctx = scuq.ucomponents.Context()
    while True:
        freq = float(simple_eval(input("Freq / Hz: ")))
        if freq < 0:
            break
        amp.SetFreq(freq)
        err, uq = amp.GetData(what='S21')
        val, unc, unit = ctx.value_uncertainty_unit(uq)
        print((freq, uq, val, unc, unit))
    err = amp.Quit()


if __name__ == '__main__':
    main()
