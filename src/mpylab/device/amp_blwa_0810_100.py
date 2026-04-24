# -*- coding: utf-8 -*-
"""mpylab.device.amp_blwa_0810_100 module."""
import time

from mpylab.device.amplifier import AMPLIFIER as AMP
from mpylab.tools.numeric_eval import safe_numeric_eval


class AMPLIFIER(AMP):
    """AMPLIFIER class."""
    conftmpl = AMP.conftmpl
    conftmpl['init_value']['gpib'] = int

    def __init__(self, **kw):
        AMP.__init__(self, **kw)
        self.operating = False
        self._cmds = {'POn': [("AMP_OFF", None)],
                      'POff': [("AMP_OFF", None)],
                      'Operate': [("AMP_ON", None)],
                      'Standby': [("AMP_OFF", None)],
                      'GetDescription': [('*IDN?', r'(?P<IDN>.*)')]}
        self.term_chars = '\n'

    def Init(self, ini=None, channel=None):
        """Init method."""
        self.error = AMP.Init(self, ini, channel)
        # self.POn()
        self.Standby()
        # time.sleep(2)
        return self.error

    def SetFreq(self, freq):
        """SetFreq method."""
        self.error = 0

        if (80e6 <= freq <= 1e9) and (not self.operating):
            self.Operate()
            time.sleep(2)
            self.operating = True
        elif (not 80e6 <= freq <= 1e9) and self.operating:
            self.Standby()
            self.operating = False
            return self.error, freq

        self.error, freq = AMP.SetFreq(self, freq)
        time.sleep(0.2)
        return self.error, freq


def main():
    """main function."""
    import sys
    import io

    from mpylab.tools.util import format_block
    import scuq

    try:
        ini = sys.argv[1]
    except IndexError:
        ini = format_block("""
                         [description]
                         DESCRIPTION = BLMA0810 100
                         TYPE = AMPLIFIER
                         VENDOR = Bonn
                         SERIALNR = 
                         DEVICEID = 
                         DRIVER =

                         [INIT_VALUE]
                         FSTART = 80e6
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
                                                                80e6 -5
                                                                1e9 -5
                                                                '''))
                         """)
        ini = io.StringIO(ini)

    amp = AMPLIFIER()
    err = amp.Init(ini)
    ctx = scuq.ucomponents.Context()
    while True:
        freq = safe_numeric_eval(input("Freq / Hz: "))
        if freq < 0:
            break
        amp.SetFreq(freq)
        err, uq = amp.GetData(what='S21')
        val, unc, unit = ctx.value_uncertainty_unit(uq)
        print((freq, uq, val, unc, unit))


if __name__ == '__main__':
    main()
