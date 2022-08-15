import time
import random
import numpy as np
from visa import *
import pyvisa.vpp43 as vpp43

def linav(dbvals):
    linmean=np.mean(np.power(10, dbvals))
    return np.log10(linmean)


class GT(object):
    instances=[]
    lasttrigger=None
    def __init__(self, ch=1, N=10, trg_threshold=0):
        self.N=N
        self.ch=ch
        self.master=not bool(GT.instances)  # True if empty list
        GT.instances.append(self)
        self.trg_threshold=trg_threshold
        self.value=None
        
        self.other=None
        if len(GT.instances)>1:
            self.other=[s for s in GT.instances if s != self][0]
        if self.master:
            self.pm = instrument("GPIB::13")
            self.pm.write('FBUF PRE GET BUFFER %d'%self.N)
        else:
            self.pm=self.other.pm
            
    def Trigger(self):
        if self._data_valid() and self.value:
            return
        time.sleep(0.1)
        self.pm.write('FBUF DUMP')
        GT.lasttrigger=time.time()
        buf=self.pm.read()
        values=[float(d) for d in buf.split(',')]
        if self.ch==1:
            self.value=linav(values[:self.N])
            if self.other and self.other._data_valid():
                self.other.value=linav(values[self.N:])
        else:
            self.value=linav(values[self.N:])
            if self.other and self.other._data_valid():
                self.other.value=linav(values[:self.N])
        
    def GetData(self):
        return self.value
    
    def _data_valid(self):
        if GT.lasttrigger:
            now=time.time()
            return (now-GT.lasttrigger)<=self.trg_threshold
        else:
            return False
            
if __name__ == "__main__":
    pm1=GT(ch=1, trg_threshold=.1)
    pm2=GT(ch=2, trg_threshold=.1)
    
    a=None
    b=None
    while True:
        if random.random() > 0.5:
            t=1
            pm1.Trigger()
        else:
            t=2
            pm2.Trigger()
        if random.random() > 0.5:
            r=1
            a=pm1.GetData()
            if a:
                a='%+7.2f'%a
        else:
            r=2
            b=pm2.GetData()
            if b:
                b='%+7.2f'%b
        print(("%d %d %s %s"%(t, r, a, b)))
        