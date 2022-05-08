import random
import sys
import StringIO
from math import log10
from mpy.tools.util import format_block
from mpy.device.sg_rs_swm import SIGNALGENERATOR
from mpy.device.pm_gt_8540c import POWERMETER
from scuq import *
import time

ini=format_block("""
                [DESCRIPTION]
                description: 'SWM'
                type:        'SIGNALGENERATOR'
                vendor:      'Rohde&Schwarz'
                serialnr:
                deviceid:
                driver:

                [Init_Value]
                fstart: 100e6
                fstop: 18e9
                fstep: 1
                gpib: 15
                virtual: 0

                [Channel_1]
                name: RFOut
                level: -100
                unit: 'dBm'
                outpoutstate: 0
                """)
ini=io.StringIO(ini)

sg=SIGNALGENERATOR()
sg.Init(ini)

ini=format_block("""
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
                unit: dBm
                filter: -1
                #resolution: 
                rangemode: auto
                #manrange: 
                swr: 1.1
                trg_threshold: 0.5

                [Channel_2]
                name: B
                unit: 'W'
                trg_threshold: 0.5
                """)
ini=io.StringIO(ini)
pm=POWERMETER()
pm.Init(ini,2)
sg.RFOn()
while True:
    freq = random.uniform(10., 18000.0)
    level= random.randint(-50,10)
    sg.SetFreq(freq*1e6)
    pm.SetFreq(freq*1e6)
    sg.SetLevel(quantities.Quantity(si.WATT, 0.001*10**(level*0.1)))
    time.sleep(0.1)
    pm.Trigger()
    err, pist=pm.GetData()
    dbist=pist.get_expectation_value_as_float()
    dbist=10*log10(dbist*1000)
    print freq, level, dbist, level-dbist
    sys.stdout.flush()
sg.Quit()
pm.Quit()