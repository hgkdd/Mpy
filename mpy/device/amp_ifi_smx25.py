# -*- coding: utf-8 -*-
import visa
from mpy.device.amplifier import AMPLIFIER

class SMX25(AMPLIFIER):
    conftmpl=AMPLIFIER.conftmpl
    conftmpl['init_value']['gpib']=int
    def __init__(self):
        AMPLIFIER.__init__(self)
        self._cmds={'POn':  [("ON", None)],
                    'POff':  [("SB", None)],
                    'Operate': [("ON", None)],
                    'Standby':  [("SB", None)],
                    'GetDescription': [('*IDN?', r'(?P<IDN>.*)')]}

    def Init(self, ini=None, channel=None):
        self.term_char=visa.CR+visa.LF
        self.error=AMPLIFIER.Init(self, ini, channel)
        self.write('M1')
        self.write('ZA')
        return self.error

    def SetFreq(self, freq):
        AMPLIFIER.SetFreq(self,freq)
        dct=self.query('ST', r'(?P<st>.*)')
        B1=int(dct['st'][:2],16)
        E=int(dct['st'][2:],16)
        assert E==0, "IFI SMX25: error from ST command. error = %d"%E
        if (B1 & 1<<5) and (freq >= 250e6):
            self.write('B2')
        elif (B1 & 1<<6) and (freq < 250e6):
            self.write('B1')
        return self.error, freq

def main():
    import sys
    import StringIO
    from mpy.tools.util import format_block
    import scuq

    try:
        ini=sys.argv[1]
    except IndexError:
        ini=format_block("""
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
                         FILE = StringIO.StringIO(format_block('''
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
                         FILE = StringIO.StringIO(format_block('''
                                                                FUNIT: Hz
                                                                UNIT: dBm
                                                                ABSERROR: 0.0
                                                                80e6 0
                                                                1e9 0
                                                                '''))
                         """)
        ini=StringIO.StringIO(ini)

    amp=SMX25()
    err=amp.Init(ini)
    ctx=scuq.ucomponents.Context()
    for freq in (80e6,500e6,1e9):
        amp.SetFreq(freq)
        err, uq = amp.GetData(what='S21')
        val, unc, unit=ctx.value_uncertainty_unit(uq)
        print freq, uq, val, unc, unit

if __name__ == '__main__':
    main()

