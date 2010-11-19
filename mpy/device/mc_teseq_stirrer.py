# -*- coding: utf-8 -*-
import time
import serial

from mpy.device.motorcontroller import MOTORCONTROLLER as MC

class MOTORCONTROLLER(MC):
    """
    Class to control TESEQ stirrer.
    """
    def __init__(self, port=2):
        pass

    def _state(self):
        ans=self.ask('?') # ask for status
        ans=ans.split(",")
        stopped=(ans[0]=='1')
        ca=float(ans[1]) # current angle
        drive_init_ok=(ans[2]=='0')
        fail=(ans[3]=='1')
        return stopped, ca, drive_init_ok, fail 
    
    def _wait(self):
        stopped=False
        while not stopped: # loop until stirrer is stopped
            stopped, ca, drive_init_ok, fail = self._state()
            time.sleep(0.2) # don't jam the serial bus
        return self.ca
    
    def _write(self, cmd):
        self.dev.flushInput() # flush input buffer before new cmd is send
        n=self.dev.write('%s\r'%cmd)
        return n-1
    
    def _read(self):
        ans=self.dev.readline(eol='\r')
        return ans
        
    def _ask(self, cmd):
        self._write(cmd)
        while self.dev.inWaiting() == 0: # wait until something is ready to read
            time.sleep(0.1)
        ans=[]
        while self.dev.inWaiting() > 0: # read until there's no more to read
            time.sleep(0.1)
            d=self._read()
            #print d
            ans.append(d)
        ans=''.join(ans)
        #print cmd, '->', ans
        return ans
    
    def _Info(self):
        ans=self._ask('INFO')
        return ans
        
    def Init(self, ini=None, channel=None):
        if channel is None:
            channel=1
        #self.error=MC.Init(self, ini, channel)
        sec='channel_%d'%channel

        port=2
        maxspeed=6
        minspeed=0.18
        acc=65
        self.dev=serial.Serial(port=port, # 2 -> COM3 
                            baudrate=9600,
                            bytesize=serial.EIGHTBITS,
                            parity=serial.PARITY_NONE,
                            stopbits=serial.STOPBITS_ONE,
                            timeout=None)
        ans=self._ask('INIT')
        self._wait()
        if not self.drive_init_ok:
            raise UserError
        # set maxspeed, minspeed and acc to save and valid values
        if maxspeed is None:
            maxspeed=6
        else:
            maxspeed=min(6,maxspeed)
            maxspeed=max(0.18,maxspeed)
        if minspeed is None:
            minspeed=0.18
        else:
            minspeed=min(6,minspeed)
            minspeed=max(0.18,minspeed)
        if acc is None:
            acc=65
        else:
            acc=min(65, acc)
            acc=max(40, acc)
        cmds=('MAXSPEED:%f'%maxspeed,
              'MINSPEED:%f'%minspeed,
              'ACC:%f'%acc)
        for cmd in cmds:
            #print cmd
            ans=self._ask(cmd)
            #print ans
        return self.ca
    
    def Goto(self, pos):
        self.error=0
        # wrap angle
        pos=pos%360
        self.ask('RMA:%f'%pos)
        # _wait until stirrer stopped
        self._wait()
        return self.error, self.ca

    def Move(self, dir):
        self.error=0
        if dir==1:
            self._write('DIR:1')
            self._write('RMS')
        elif dir==-1:
            self._write('DIR:0')
            self._write('RMS')
        else:
            self._write('Stop')
        return self.error, dir

    def GetState(self):
        self.error=0
        stopped, ca, drive_init_ok, fail = self._state()
        if stopped:
            return self.error, ca, 0
        else:
            ca2=ca
            d=0
            while (not stopped) or (ca2!=ca):
                time.sleep(0.1)
                stopped, ca2, drive_init_ok, fail = self._state()
            if ca2>ca:
                d=1
            elif ca2<ca:
                d=-1
            return self.error, ca2, d

if __name__ == '__main__':
    pass