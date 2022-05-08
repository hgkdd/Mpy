# -*- coding: utf-8 -*-
from mpy.device.driver import DRIVER
from mpy.tools.Configuration import strbool
from mpy.tools.util import format_block

LF='R1P1'
HF='R1P2'

TERM='R2P0'
GTEM='R2P1'

REST='R3P1R4P0'

class SWController(DRIVER):
    conftmpl={'description': 
                 {'description': str,
                  'type': str,
                  'vendor': str,
                  'serialnr': str,
                  'deviceid': str,
                  'driver': str,
                  'class': str},
                'init_value':
                    {'fstart': float,
                     'fstop': float,
                     'fstep': float,
                     'gpib': int,
                     'output': str,
                     'swfreq': float,
                     'virtual': strbool}}

    def __init__(self):
        DRIVER.__init__(self)
        self.error=0
    
    def ask(self, cmd):
        if not self.dev:
            return None
        ans=self.dev.ask(cmd)
        return ans
    
    def Init(self, ini, ch=1):
        self.error=DRIVER.Init(self, ini, ch)
        
        self.ask('R1P4R2P0R3P1R4P0') # save settings

        out=None
        self.R2=TERM
        try:
            out = self.conf['init_value']['output']
        except KeyError:
            pass
        if out.lower()=='gtem':
            self.R2=GTEM

        self.swfreq=1e9
        try:
            self.swfreq = self.conf['init_value']['swfreq']
        except KeyError:
            pass

        return self.error
        
    def SetFreq(self, f):
        if f<self.swfreq:
            cmd=LF+self.R2+REST
        else:
            cmd=HF+self.R2+REST
        ans=self.ask(cmd)
        return 0, f

    def Quit(self):
        self.ask('R1P4R2P0R3P1R4P0') # save settings
        return 0

if __name__ == '__main__':
    import StringIO
    import numpy as np
    import time

    ini=format_block("""
                    [DESCRIPTION]
                    DESCRIPTION = GTEM Switch
                    TYPE = Custom
                    VENDOR = 
                    SERIALNR = 
                    DEVICEID = 
                    DRIVER = sw_gtem
                    CLASS = SWController

                    [INIT_VALUE]
                    FSTART = 0
                    FSTOP = 18e9
                    FSTEP = 0.0
                    GPIB = 4
                    OUTPUT = GTEM
                    SWFREQ = 1e9
                    VIRTUAL = 0
                    """)
    ini=io.StringIO(ini)
    
    sw=SWController()
    sw.Init(ini)
    for f in np.linspace(0,4.2e9,20):
        print f, sw.SetFreq(f)
        time.sleep(0.5)
    sw.Quit()