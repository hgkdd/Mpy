import time
import sys
import numpy as np
from scuq import quantities,si,units
from mpy.tools.mgraph import MGraph
from mpy.tools.aunits import POWERRATIO

def dBm2W (v):
    return 10**(v*0.1)*0.001
def W2dBm (v):
    return 10*np.log10(v*1000)


dot='gtem-immunity.dot'
# keys: names in program, values: names in graph
names={'sg': 'sg',
       'amp_in': 'amp_in',
       'amp_out': 'amp_out',
       'pm_fwd': 'pm1',
       'pm_bwd': 'pm2',
       'output': 'gtem'}
mg=MGraph(dot, names)

instrumentation=mg.CreateDevices()
sg=instrumentation.sg

mg.Init_Devices()  # init all devices in graph

try:

    readlist=[ mg.get_gname(dev) for dev in ('pm_fwd','pm_bwd') ] 
    for f in np.linspace(10e3, 4.2e9, 10):
        mg.SetFreq_Devices(f)
        mg.EvaluateConditions()
        
        # s21 of the connections
        c_sg_amp  = mg.get_path_correction(mg.name.sg, mg.name.amp_in, POWERRATIO)
        c_amp_out = mg.get_path_correction(mg.name.amp_out, mg.name.output, POWERRATIO)
        c_amp_pm1 = mg.get_path_correction(mg.name.amp_out, mg.name.pm_fwd, POWERRATIO)
        c_amp_pm2 = mg.get_path_correction(mg.name.amp_out, mg.name.pm_bwd, POWERRATIO)

        mg.RFOn_Devices()
        for dbmlv in np.linspace(-30, 0, 31):
            lv=quantities.Quantity(si.WATT, dBm2W(dbmlv))
            sg.SetLevel(lv)
            time.sleep(0.2)
            
            mg.NBTrigger(readlist)
            results=mg.Read(readlist)

            pfwd=results[mg.name.pm_fwd]
            pin=(lv*c_sg_amp).reduce_to(si.WATT)
            pout=(pfwd/c_amp_pm1).reduce_to(si.WATT)
            pgtem=(pout*c_amp_out).reduce_to(si.WATT)

            print f, abs(lv), abs(pin), abs(pout), abs(pgtem) 
            sys.stdout.flush()
        print
        
        mg.RFOff_Devices()
            
finally:    
    mg.RFOff_Devices()
    mg.Quit_Devices()  