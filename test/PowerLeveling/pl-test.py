import io
from mpylab.tools.util import format_block
from mpylab.device.pm_gt_8540c import POWERMETER as PM
from mpylab.device.sg_rs_smb100a import SIGNALGENERATOR as SG
from mpylab.tools.PControler import Leveler
from scuq import *

pm1ini=format_block("""
                [DESCRIPTION]
                description: 'GigaTronics 8542C Universal Power Meter'
                type:        'POWERMETER'
                vendor:      'GigaTronics'
                serialnr:
                deviceid:
                driver:

                [Init_Value]
                fstart: 100e3
                fstop: 18e9
                fstep: 1
                gpib: 13
                virtual: 0
                nr_of_channels: 2

                [Channel_1]
                name: A
                unit: 'dBm'
                filter: -1
                #resolution: 
                rangemode: auto
                #manrange: 
                swr: 1.1
                trg_threshold: 0.5

                [Channel_2]
                name: B
                unit: 'dBm'
                trg_threshold: 0.5
                """)
pm1ini=io.StringIO(pm1ini)
pm2ini=format_block("""
                [DESCRIPTION]
                description: 'GigaTronics 8542C Universal Power Meter'
                type:        'POWERMETER'
                vendor:      'GigaTronics'
                serialnr:
                deviceid:
                driver:

                [Init_Value]
                fstart: 100e3
                fstop: 18e9
                fstep: 1
                gpib: 13
                virtual: 0
                nr_of_channels: 2

                [Channel_1]
                name: A
                unit: 'dBm'
                filter: -1
                #resolution: 
                rangemode: auto
                #manrange: 
                swr: 1.1
                trg_threshold: 0.5

                [Channel_2]
                name: B
                unit: 'dBm'
                trg_threshold: 0.5
                """)
pm2ini=io.StringIO(pm2ini)

sgini=format_block("""
                [DESCRIPTION]
                description: 'SMB100A'
                type:        'SIGNALGENERATOR'
                vendor:      'Rohde&Schwarz'
                serialnr:
                deviceid:
                driver:

                [Init_Value]
                fstart: 100e6
                fstop: 6e9
                fstep: 1
                gpib: 28
                virtual: 0

                [Channel_1]
                name: RFOut
                level: -100.0
                unit: dBm
                outpoutstate: 0
                """)
sgini=io.StringIO(sgini)

class Actor(object):
    def __init__(self, sg):
        self.sg=sg
    def SetLevel(self, lv):
        lv=quantities.Quantity(si.WATT, lv)
        self.sg.SetLevel(lv)

class Monitor(object):
    def __init__(self, pm):
        self.pm=pm
        self.PinMax=1e-4
        self.g=1e5
    def Pout(self, pin):
        self.pm.Trigger()
        err, dat = self.pm.GetData()
        dat=10**(0.1*dat)*1e-3  # Watt
        return dat
        
pmFWD=PM()
pmOUT=PM()
sg=SG()

sg.Init(sgini)
sg.RFOff()
pmFWD.Init(pm1ini, 1)
pmOUT.Init(pm2ini, 2)

sg.SetFreq(200e3)
sg.RFOn()

act=Actor(sg)
mon=Monitor(pmFWD)
Lcntr=Leveler(act, mon)


for soll in [1e-4,5e-4,1e-3,1e-2]: #soll=1e-4
    pin,pmon = Lcntr.adjust_level(soll)

    pmOUT.Trigger()
    err, pout=pmOUT.GetData()
    pout=10**(0.1*pout)*1e-3
    print(("Pin: %.3e, Soll: %.2e, Mon: %.2e, Out: %.2e\n"%(pin, soll, pmon, pout)))

sg.RFOff()
sg.Quit()
pmOUT.Quit()
pmFWD.Quit()


