# -*- coding: utf-8 -*-
import sys
import io
import time

from scuq import si, quantities, ucomponents

from mpy.device.fieldprobe import FIELDPROBE as FLDPRB


class FIELDPROBE(FLDPRB):
    conftmpl = FLDPRB.conftmpl
    conftmpl['init_value']['visa'] = str

    def __init__(self):
        FLDPRB.__init__(self)
        self._internal_unit = si.VOLT / si.METER
        self.freq = None
        self._cmds = {'GetFreq': [(":syst:freq?", r'(?P<freq>%s)' % self._FP)],
                      'Zero': [],
                      'Trigger': [],
                      'Quit': [(':SYST:LAS:EN 0', None)],
                      'GetDescription': [('*IDN?', r'(?P<IDN>.*)')]}
        self.term_chars = '\r\n'
        self.error = None
        self.mode = None

    def Init(self, ini=None, channel=None):
        self.error = FLDPRB.Init(self, ini, channel)
        # wait for laser ready
        self.write(':syst:las:en 1')
        return self.error

    def wait_for_laser_ready(self):
        while True:
            ans = self.query(':syst:las:rdy?', r'(?P<laser>\d)')
            if ans:
                if int(ans['laser']) == 1:
                    break
            time.sleep(.1)

    def setMode(self, mode):
        mode = int(mode)

        if self.mode == mode:
            return mode

        if 0 <= mode <= 8:
            self.write(f':syst:mod {mode}')
            while True:
                ans = self.query(f':syst:mod?', None)
                if int(ans) == mode:
                    break
        self.wait_for_laser_ready()
        self.mode = mode
        return mode

    def SetFreq(self, freq):
        self.error = 0
        self.setMode(0)
        #if freq > 400e6:
        #    self.setMode(0)
        #else:
        #    self.setMode(3)
        self.write(f':syst:freq {freq}')
        tmpl = r'(?P<freq>%s)' % self._FP
        ans = self.query(":syst:freq?", tmpl)
        if ans:
            freq = float(ans['freq'])
        else:
            self.error = 1
            freq = None
        self.freq = freq
        return self.error, freq


    def GetData(self):
        self.error = 0
        cmd = ":meas:all?"
        tmpl = r"(?P<x>[\d.]+),(?P<y>[\d.]+),(?P<z>[\d.]+),(?P<m>[\d.]+)"
        ans = self.query(cmd, tmpl)
        # print(ans)
        if self.freq <= 30e6:
            relerr = 0.072  # 0.6 dB
        elif 30e6 < self.freq <= 1e9:
            relerr = 0.12  # 1 dB
        elif 1e9 < self.freq:
            relerr = 0.17  # 1.4 dB


        data = [
            quantities.Quantity(self._internal_unit, ucomponents.UncertainInput(float(ans[i]), float(ans[i]) * relerr))
            for i in 'xyz']
        return self.error, data

    def GetDataNB(self, retrigger):
        return self.GetData()


def main():
    from mpy.tools.util import format_block

    try:
        ini = sys.argv[1]
    except IndexError:
        ini = format_block("""
                        [DESCRIPTION]
                        description: 'LSProbe 1.2'
                        type:        'FIELDPROBE'
                        vendor:      'LUMILOOP'
                        serialnr:
                        deviceid:
                        driver:

                        [Init_Value]
                        fstart: 10e3
                        fstop: 8.2e9
                        fstep: 0
                        visa: TCPIP0::192.168.88.3::10000::SOCKET
                        virtual: 0

                        [Channel_1]
                        name: EField
                        unit: Voverm
                        """)
        ini = io.StringIO(ini)
    dev = FIELDPROBE()

    dev.Init(ini=ini, channel=1)
    err, des = dev.GetDescription()

    for f in [100e6, 1e9, 8e9]:
        err, ff = dev.SetFreq(f)
        print(f"Frequency set to: {ff} Hz")
        for i in range(10):
            err, dat = dev.GetData()
            time.sleep(0.1)
            print(dat[0], dat[1], dat[2])

    dev.Quit()

if __name__ == '__main__':
    main()
