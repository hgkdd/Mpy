# -*- coding: utf-8 -*-
#
import io
import re
import struct
import sys
import time

import serial
from scuq import si, quantities, ucomponents

from mpylab.device.fieldprobe import FIELDPROBE as FLDPRB

debug = True


def dprint(arg):
    if debug:
        print(arg)


class FIELDPROBE(FLDPRB):
    conftmpl = FLDPRB.conftmpl
    conftmpl['init_value']['com'] = int

    def __init__(self):
        FLDPRB.__init__(self)
        self._internal_unit = si.VOLT / si.METER

    def _write(self, cmd):
        self.dev.flushInput()
        self.dev.flushOutput()
        self.dev.write(cmd)
        time.sleep(0.1)

    def _read(self, num=1):
        ans = self.dev.read(num)
        return ans

    def _query(self, cmd, num=1):
        self._write(cmd)
        ans = self._read(num)
        return ans

    def Init(self, ini=None, channel=None):
        if channel is None:
            channel = 1
        self.error = 0
        self.error = FLDPRB.Init(self, ini, channel)
        sec = 'channel_%d' % channel
        try:
            self.unit = self.conf[sec]['unit']
        except KeyError:
            self.unit = self._internal_unit

        self.com = int(self.conf['init_value']['com'])
        self.dev = serial.Serial(port='COM%d' % self.com,
                                 timeout=1,
                                 baudrate=9600)

        # self.dev.write('#00e 600*') # switch off after 10 minutes
        ans = self._query('#00e 10800*', 1)  # switch off after 3 hours
        if ans != 'e':
            self.error = 1
        self._write('#00?v*')  # set device to slave mode
        self.dev.flushInput()
        return self.error

    def GetDescription(self):
        self.error = 0
        self.write('#00?v*')
        des = []
        while True:
            ans = self._read(1)
            if ans == ';':
                self.dev.flushInput()
                break
            des.append(ans)
        des = ''.join(des)
        # print des
        m = re.match(r'.*v(.*):(.*) (.*)', des)
        model, fw, date = m.groups()
        return self.error, "Company: PMM, Model: %s, FW: %s, DATE: %s" % (model, fw, date)

    def SetFreq(self, freq):
        self.error = 0
        rfreq = None
        ifreq = int(freq * 1e-4)
        cmd = '#00k %d*' % ifreq
        # print cmd
        self._write(cmd)
        for i in range(10):
            ans = self._read(1)
            if ans == 'k':
                break
        # print len(ans), ans, repr(ans)
        if ans == 'k':
            rfreq = struct.unpack('<f', self._read(4))[0]
            # print rfreq
        else:
            self.error = 1
        self.dev.flushInput()
        return self.error, rfreq  # rfreq*1e6

    def GetData(self):
        self.error = 0
        data = None
        for i in range(5):
            ans = self._query('#00?A*', 1)
            # print 'Sonde: ',ans
            if ans == 'A':
                data = struct.unpack('<3f', self._read(12))
                # print data
                relerr = 0.1  # geschaetzt
                data = [quantities.Quantity(self._internal_unit, ucomponents.UncertainInput(v, v * relerr)) for v in
                        data]
                self.error = 0
                break
            else:
                self.error = 1
        self.dev.flushInput()
        return self.error, data

    def GetDataNB(self, retrigger):
        return self.GetData()

    def Zero(self, state):
        self.error = 0
        return self.error

    def Trigger(self):
        self.error = 0
        return self.error

    def GetBatteryState(self):
        self.error = 0
        percent = 0.0
        ans = self._query('#00?b*', 1)
        nn = 0
        if ans == 'b':
            nn = struct.unpack('<H', self._read(2))[0]
            # print nn
        else:
            self.error = 1
        percent = 3 * 1.6 * nn / 1024
        self.dev.flushInput()
        return self.error, percent * 0.01

    def Quit(self):
        self.dev.close()
        self.error = 0
        return self.error


def test():
    from mpylab.tools.util import format_block
    ini = format_block("""
                    [DESCRIPTION]
                    description: PMM EP601
                    type:        FIELDPROBE
                    vendor:      PMM
                    serialnr:
                    deviceid:
                    driver: prb_pmm_ep601.py

                    [Init_Value]
                    fstart: 10e3
                    fstop: 9.25e9
                    fstep: 0
                    COM: 3
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
                        description: PMM EP601
                        type:        FIELDPROBE
                        vendor:      PMM
                        serialnr:
                        deviceid:
                        driver:

                        [Init_Value]
                        fstart: 10e3
                        fstop: 9.25e9
                        fstep: 0
                        COM: 3
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
