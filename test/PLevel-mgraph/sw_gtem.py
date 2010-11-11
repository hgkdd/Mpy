# -*- coding: utf-8 -*-
import visa

LF='R1P1'
HF='R1P2'

TERM='R2P0'
GTEM='R2P1'

REST='R3P1R4P0'
sw_freq=1000e6

class SWController(object):
    def __init__(self):
        self.sw=visa.instrument('GPIB::4')#, term_chars = visa.LF)
    
    def ask(self, cmd):
        if not self.sw:
            return None
        ans=self.sw.ask(cmd)
        return ans
    
    def Init(self, ini, ch=1):
        self.ch=ch
        self.ask('R1P4R2P0R3P1R4P0') # save settings
        if ch==1:
            self.R2=GTEM
        else:
            self.R2=TERM
        return 0
    
    def SetFreq(self, f):
        if f<sw_freq:
            cmd=LF+self.R2+REST
        else:
            cmd=HF+self.R2+REST
        ans=self.ask(cmd)
        return 0, f

    def Quit(self):
        self.ask('R1P4R2P0R3P1R4P0') # save settings
        return 0

if __name__ == '__main__':
    import numpy as np
    import time
    
    sw=SWController()
    sw.Init(0)
    for f in np.linspace(0,4.2e9,10):
        print f, sw.SetFreq(f)
        time.sleep(0.5)
    sw.Quit()