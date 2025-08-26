# -*- coding: utf-8 -*-
import pyvisa
import time
from mpylab.device.amplifier import AMPLIFIER as AMP


class AMPLIFIER(AMP):
    conftmpl = AMP.conftmpl
    conftmpl['init_value']['gpib'] = int

    def __init__(self):
        AMP.__init__(self)
        self.operating = False
        self._cmds = {'POn': [("AMP_OFF", None)],
                      'POff': [("AMP_OFF", None)],
                      'Operate': [("AMP_ON", None)],
                      'Standby': [("AMP_OFF", None)],
                      'GetDescription': [('*IDN?', r'(?P<IDN>.*)')]}
        self.term_chars = '\n'
        self.error = None

    def Init(self, ini=None, channel=None):
        self.error = AMP.Init(self, ini, channel)
        # self.POn()
        self.Standby()
        # time.sleep(2)
        return self.error

    def _query(self, cmd, N=5, sleep=0.2):
        ans = None
        for _ in range(N):
            try:
                ans = self.dev.query(cmd)
                break  # no exception
            except pyvisa.VisaIOError:
                time.sleep(sleep)
                continue  # try again
        else:
            raise  # re raise exception
        return ans

    def _wait(self, state=False):
        while True:
            ans = self._query('AMP?')
            rstate = (ans == 'AMP_ON')
            if state == rstate:
                break
            time.sleep(0.1)

    def SetFreq(self, freq):
        self.error = 0
        if (1e9 <= freq <= 18e9) and (not self.operating):
            self.Operate()
            time.sleep(2)
            self.operating = True
        elif (not 1e9 <= freq <= 18e9) and self.operating:
            self.Standby()
            self.operating = False
            return self.error, freq

        swstat = self._query('SW01?')
        assert swstat.startswith('SW01_')
        swstat = int(swstat[-1])
        if freq <= 2e9:
            sw = 1
        elif freq <= 6e9:
            sw = 2
        else:
            sw = 3

        if sw != swstat:
            self.Standby()
            self._wait(False)
            self.write('SW01_%d' % sw)
            self.Operate()
            self._wait(True)
            time.sleep(2)
        self.error, freq = AMP.SetFreq(self, freq)
        time.sleep(0.2)
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
                         DESCRIPTION = BLMA1018 100
                         TYPE = AMPLIFIER
                         VENDOR = Bonn
                         SERIALNR = 
                         DEVICEID = 
                         DRIVER =

                         [INIT_VALUE]
                         FSTART = 1e9
                         FSTOP = 18e9
                         FSTEP = 0.0
                         NR_OF_CHANNELS = 2
                         GPIB = 7
                         VIRTUAL = 0

                         [CHANNEL_1]
                         NAME = S21
                         UNIT = dB
                         INTERPOLATION = LOG
                         FILE = io.StringIO(format_block('''
                                                                FUNIT: Hz
                                                                UNIT: dB
                                                                ABSERROR: 0.5
                                                                1e9 50
                                                                2e9 50
                                                                2.001e0 44.8
                                                                6e9 44.8
                                                                6.001e9 43
                                                                18e9 43
                                                                '''))
                         [CHANNEL_2]
                         NAME = MAXIN
                         UNIT = dBm
                         INTERPOLATION = LOG
                         FILE = io.StringIO(format_block('''
                                                                FUNIT: Hz
                                                                UNIT: dBm
                                                                ABSERROR: 0.0
                                                                1e9 -5
                                                                18e9 -5
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
    amp.POff()


if __name__ == '__main__':
    main()
