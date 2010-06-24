# -*- coding: utf-8 -*-
#
import sys
import re
import struct
import bidict
import StringIO
import serial
from scuq import *
from mpy.tools.Configuration import fstrcmp
from mpy.device.fieldprobe import FIELDPROBE as FLDPRB

class FIELDPROBE(FLDPRB):
    def __init__(self):
        FLDPRB.__init__(self)
        self._internal_unit='Voverm'

    def Init(self, ini=None, channel=None):
        if channel is None:
            channel=1
        #self.error=FLDPRB.Init(self, ini, channel)
        sec='channel_%d'%channel
        try:
            self.unit=self.conf[sec]['unit']
        except KeyError:
            self.unit=self._internal_unit

        self.com=3
        self.dev=serial.Serial('COM%d'%self.com)
        self.dev.timeout=1
        self.dev.write('#00e 600') # switch off after 3 minutes
        return 0

    def GetDescription(self):
        self.error=0
        self.dev.write('#00?v*')
        des=[]
        while True:
            ans=self.dev.read(1)
            if ans==';':
                break
            des.append(ans)
        des=''.join(des)
        print des
        m=re.match(r'.*v(.*):(.*) (.*)', des)
        model,fw,date=m.groups()
        return self.error, "Company: PMM, Model: %s, FW: %s, DATE: %s"%(model,fw,date)
    
    def SetFreq(self, freq):
        self.error=0
        rfreq=None
        ifreq=int(freq*1e-4)
        cmd='#00k %d*'%ifreq
        print cmd
        self.dev.write(cmd)
        for i in range(10):
            ans=self.dev.read(1)
            if ans == 'k':
                break
        #print len(ans), ans, repr(ans)
        if ans=='k':
            rfreq=struct.unpack('<f', self.dev.read(4))[0]
            #print rfreq
        else:
            self.error=1
        return self.error, rfreq*1e6
    
    def GetData(self):
        self.error=0
        data=None
        self.dev.write('#00?A*')
        ans=self.dev.read(1)
        if ans=='A':
            data=struct.unpack('<3f', self.dev.read(12))
        else: 
            self.error=1
        return self.error, data
    
    def GetDataNB(self, retrigger):
        return self.GetData()
        
    def Zero(self, state):
        self.error=0
        return self.error
        
    def Trigger(self):
        self.error=0
        return self.error
    
    def GetBatteryState(self):
        self.error=0
        state = 'BATTERY LOW'
        self.dev.write('#00?b*')
        ans=self.dev.read(1)
        nn=0
        if ans=='b':
            nn=struct.unpack('<H', self.dev.read(2))[0]
            #print nn
        else: 
            self.error=1
        percent=3*1.6*nn/1024
        print percent
        if percent>10:
            state='BATTERY OK'
        return self.error, state
    
    def Quit(self):
        self.error=0
        return self.error
            
def main():
    from mpy.tools.util import format_block
    from mpy.device.fieldprobe_ui import UI as UI
    #
    # Wird für den Test des Treibers keine ini-Datei über die Kommnadoweile eingegebnen, dann muss eine virtuelle Standard-ini-Datei erzeugt
    # werden. Dazu wird der hinterlegte ini-Block mit Hilfe der Methode 'format_block' formatiert und der Ergebnis-String mit Hilfe des Modules
    # 'StringIO' in eine virtuelle Datei umgewandelt.
    #
    try:
        ini=sys.argv[1]
    except IndexError:
        ini=format_block("""
                        [DESCRIPTION]
                        description: 'SMF100A'
                        type:        'SIGNALGENERATOR'
                        vendor:      'Rohde&Schwarz'
                        serialnr:
                        deviceid:
                        driver:

                        [Init_Value]
                        fstart: 100e3
                        fstop: 22e9
                        fstep: 1
                        gpib: 28
                        virtual: 0

                        [Channel_1]
                        name: RFOut
                        level: -100.0
                        unit: dBm
                        outpoutstate: 0
                        """)
        ini=StringIO.StringIO(ini)
    sg=SIGNALGENERATOR()
    ui=UI(sg,ini=ini)
    ui.configure_traits()

if __name__ == '__main__':
    main()

