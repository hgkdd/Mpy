# -*- coding: utf-8 -*-
#
import io
import sys
import time
from scuq import si, quantities, ucomponents

from mpylab.device.fieldprobe import FIELDPROBE as FLDPRB


class FIELDPROBE(FLDPRB):
    def __init__(self):
        FLDPRB.__init__(self)
        self._internal_unit = si.VOLT / si.METER
        self.freq = None
        self._cmds = {'Zero': [],
                      'Trigger': [],
                      'GetBatteryState': [("Battery?", r'(?P<BATT>\d+)')],
                      'Quit': [],
                      'GetDescription': [('*IDN?', r'(?P<IDN>.*)')]}

    def Init(self, ini=None, channel=None):
        self.term_chars = '\r'
        self.error = FLDPRB.Init(self, ini, channel)
        self.write('CORR,ON')
        return self.error

    def SetFreq(self, freq):
        self.error = 0
        if freq >= 1e9:
            fs = "FREQ,%07.3fG" % (freq * 1e-9)
        elif freq >= 1e6:
            fs = "FREQ,%07.3fM" % (freq * 1e-6)
        else:
            fs = "FREQ,%07.3fK" % (freq * 1e-3)
        self.write(fs)
        time.sleep(0.1)
        tmpl = r"FREQ,(?P<f>\d{3}\.\d{3})(?P<u>[KMG])"
        ans = self.query("FREQ?", tmpl)
        if ans:
            factors = {'K': 1e3, 'M': 1e6, 'G': 1e9}
            freq = float(ans['f']) * factors[ans['u']]
        else:
            self.error = 1
            freq = None
        self.freq = freq
        return self.error, freq

    def GetData(self):
        time.sleep(0.5)
        self.error = 0
        cmd = "D,%d?" % self.channel
        tmpl = r"D,%d,(?P<x>[\d.]{5}),(?P<y>[\d.]{5}),(?P<z>[\d.]{5}),(?P<t>[\d.]{5})" % self.channel
        for i in range(5):  # 5 tries
            ans = self.query(cmd, tmpl)
            if ans:
                break
            time.sleep(0.1)
        # print ans
        if self.freq <= 1e9:
            relerr = 0.096  # 0.8 dB
        else:
            relerr = 0.17  # 1.4 dB

        data = [
            quantities.Quantity(self._internal_unit, ucomponents.UncertainInput(float(ans[i]), float(ans[i]) * relerr))
            for i in 'xyz']
        return self.error, data

    def GetDataNB(self, retrigger):
        return self.GetData()

    def GetBatteryState(self):
        self.error = 0
        return self.error, 1.0


def test():
    from mpylab.tools.util import format_block
    ini = format_block("""
                        [DESCRIPTION]
                        description: 'FL7018@FM7004'
                        description: 'FL7018@FM7004'
                        type:        'FIELDPROBE'
                        vendor:      'Amplifier Research'
                        serialnr:
                        deviceid:
                        driver:

                        [Init_Value]
                        fstart: 3e6
                        fstop: 18e9
                        fstep: 0
                        gpib: 4
                        virtual: 0

                        [Channel_1]
                        name: EField
                        unit: Voverm
                        """)
    ini = io.StringIO(ini)
    dev = FIELDPROBE()
    dev.Init(ini)
    return dev


def main():
    from mpylab.tools.util import format_block
    from mpylab.device.fieldprobe_ui import UI as UI
    #
    # Wird für den Test des Treibers keine ini-Datei über die Kommnadoweile eingegebnen, dann muss eine virtuelle Standard-ini-Datei erzeugt
    # werden. Dazu wird der hinterlegte ini-Block mit Hilfe der Methode 'format_block' formatiert und der Ergebnis-String mit Hilfe des Modules
    # 'StringIO' in eine virtuelle Datei umgewandelt.
    #
    try:
        ini = sys.argv[1]
    except IndexError:
        ini = format_block("""
                        [DESCRIPTION]
                        description: 'FL7018@FM7004'
                        type:        'FIELDPROBE'
                        vendor:      'Amplifier Research'
                        serialnr:
                        deviceid:
                        driver:

                        [Init_Value]
                        fstart: 3e6
                        fstop: 18e9
                        fstep: 0
                        gpib: 4
                        virtual: 0

                        [Channel_1]
                        name: EField
                        unit: Voverm
                        """)
        ini = io.StringIO(ini)
    dev = FIELDPROBE()
    ui = UI(dev, ini=ini)
    ui.configure_traits()


if __name__ == '__main__':
    main()
