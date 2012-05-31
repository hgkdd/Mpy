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
        #time.sleep(0.5)
        for _ in range(10):
            try:
                ans=self._ask('?') # ask for status
                #print ans
                ans=ans.split(",")
                stopped=(ans[0]=='1')
                #print ans,' --> ', ans[0], ans[1], ' --> ', stopped
                self.ca=float(ans[1]) # current angle
                self.drive_init_ok=(ans[2]=='0')
                fail=(ans[3]=='1')
                #print self._ask('INFO')
                break # exit for loop
            except IndexError: # structure of ans not as expected
                time.sleep(0.1)
                continue
        else: #no correct answer after 10 tries
            raise # re-raise the last expection
        return stopped, self.ca, self.drive_init_ok, fail 
    
    def _wait(self):
        stopped=False
        while not stopped: # loop until stirrer is stopped
            stopped, self.ca, self.drive_init_ok, fail = self._state()
            time.sleep(0.2) # don't jam the serial bus
        return self.ca
    
    def _write(self, cmd):
        self.dev.flushInput() # flush input buffer before new cmd is send
        n=self.dev.write('%s\r'%cmd)
        return n-1
    
    def _read(self):
        ans=self.dev.read()
        return ans
        
    def _ask(self, cmd):
        self._write(cmd)
        while self.dev.inWaiting() == 0: # wait until something is ready to read
            time.sleep(0.1)
        ans=[]
        while self.dev.inWaiting() > 0: # read until there's no more to read
            time.sleep(0.01)
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
        self.conf={}
        self.conf['init_value']={}
        self.conf['init_value']['virtual'] = False
        port=2
        maxspeed=6
        minspeed=0.18
        acc=65
        for i in range(5):
            try:
                self.dev=serial.Serial(port=port, # 2 -> COM3 
                                baudrate=9600,
                                bytesize=serial.EIGHTBITS,
                                parity=serial.PARITY_NONE,
                                stopbits=serial.STOPBITS_ONE,
                                timeout=1)
                #self.dev=io.TextIOWrapper(io.BufferedRWPair(self.ser, self.ser),
                #                            newline='\r')
                break
            except:
                time.sleep(0.5)
        else:
            raise
        
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
        self.maxspeed=maxspeed   # turns per minute
        self.degpersec = self.maxspeed * 6
        cmds=('MAXSPEED:%f'%maxspeed,
              'MINSPEED:%f'%minspeed,
              'ACC:%f'%acc)
        for cmd in cmds:
            #print cmd
            ans=self._ask(cmd)
            #print ans
        #print self._ask('INFO')
        return self.ca
    
    def Goto(self, pos):
        self.error=0
        stopped, self.ca, self.drive_init_ok, fail = self._state()
        if not stopped:
            # stop first
            self._write('STOP')
            self.ca=self._wait()
            
        # wrap angle
        pos=pos%360
        self._ask('RMA:%f'%pos)
        # _wait until stirrer stopped
        self._wait()
        return self.error, self.ca

    def Move(self, dir):
        self.error=0
        err,ca,d=self.GetState()
        if d==dir: # nothing to do
            return self.error, dir
        # stop first
        self._write('STOP')
        self.ca=self._wait()
        
        if dir==1:
            self._write('DIR:1')
            time.sleep(0.1)
            self._write('RMS')
            time.sleep(0.5)
        elif dir==-1:
            self._write('DIR:0')
            time.sleep(0.1)
            self._write('RMS')
            time.sleep(0.5)
        return self.error, dir

    def GetState(self):
        self.error=0
        stopped, self.ca, self.drive_init_ok, fail = self._state()
        first=time.time()
        if stopped:
            return self.error, self.ca, 0
        else:
            ca=self.ca
            d=0
            while (self.ca==ca):
                time.sleep(0.1)
                stopped, self.ca, self.drive_init_ok, fail = self._state()
                now=time.time()
                dt=now-first
                upguess=(ca+self.degpersec*dt)%360
                downguess=(ca-self.degpersec*dt)%360
                #print self.ca, upguess, downguess
                #print stopped, ca, self.ca
                if stopped:
                    break
            if abs(self.ca-upguess)<abs(self.ca-downguess):
                d=1
            elif abs(self.ca-upguess)>abs(self.ca-downguess):
                d=-1
            return self.error, self.ca, d
            
    def SetSpeed(self, speed):
        pass
        return 0
    def GetSpeed(self):
        pass
        return 0, 1

    def Quit(self):
        self.error=0
        stopped, self.ca, self.drive_init_ok, fail = self._state()
        if not stopped:
            # stop first
            self._write('STOP')
            self.ca=self._wait()
        self.dev.close()
        return self.error
            
def main():
    import sys
    import StringIO
    import time
    
    from mpy.tools.util import format_block
    import scuq

    try:
        ini=sys.argv[1]
    except IndexError:
        ini=format_block("""
                         [description]
                         DESCRIPTION = Teseq Motor Controller
                         TYPE = MOTORCONTROLLER
                         VENDOR = TESEQ
                         SERIALNR = 
                         DEVICEID = 
                         DRIVER = mc_teseq_stirrer.py

                         [INIT_VALUE]
                         FSTART = 0
                         FSTOP = 100e9
                         FSTEP = 0.0
                         VIRTUAL = 0
                         """)
        ini=StringIO.StringIO(ini)

    dirmap={'u': 1, 'd': -1, 's': 0}
    mc=MOTORCONTROLLER()
    err=mc.Init(ini)
    while(True):
        pos=raw_input("Pos / DEG: ")
        if pos in 'qQ':
            break
        try:
            pos=float(pos)
            err, ang = mc.Goto(pos)
            print '%.2f -> %.2f'%(pos, ang)
        except ValueError:
            pos=pos.lower()
            if pos in dirmap:
                err, dir = mc.Move(dirmap[pos])
                print 'Direction: %d'%dir
    mc.Quit()
    
if __name__ == '__main__':
    main()

