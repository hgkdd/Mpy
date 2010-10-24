import time
import sys
import numpy as np
from scuq import quantities,si,units
from mpy.tools.mgraph import MGraph
from mpy.tools.aunits import POWERRATIO

dot='gtem-immunity.dot'
mg=MGraph(dot)
names={'sg': 'sg',
       'amp_in': 'amp_in',
       'amp_out': 'amp_out',
       'pm_fwd': 'pm1',
       'pm_bwd': 'pm2',
       'output': 'gtem'}

instrumentation=mg.CreateDevices()
sg=instrumentation[names['sg']]

mg.Init_Devices()  # init all devices in graph

try:

    readlist=[names['pm_fwd'], names['pm_bwd']] 
    for f in np.linspace(10e3, 4.2e9, 100):
        if f <= 1103037676.77:
            continue
        #print "Freq: %.3f MHz"%(f/1e6),
        mg.SetFreq_Devices(f)
        mg.EvaluateConditions()
        # s21 of the connections
        c_sg_amp=mg.get_path_correction(names['sg'], names['amp_in'], POWERRATIO)
        c_amp_out=mg.get_path_correction(names['amp_out'], names['output'], POWERRATIO)
        c_amp_pm1=mg.get_path_correction(names['amp_out'], names['pm_fwd'], POWERRATIO)
        c_amp_pm2=mg.get_path_correction(names['amp_out'], names['pm_bwd'], POWERRATIO)

        mg.RFOn_Devices()
        for dbmlv in np.linspace(-30, 0, 31):
            lv=quantities.Quantity(si.WATT, 10**(dbmlv*0.1)*1e-3)
            sg.SetLevel(lv)
            time.sleep(0.2)
            
            # for var in [c_sg_amp, c_amp_out, c_amp_pm1, c_amp_pm2]:
                # #print str(var)
                # for k,v in var.items():
                    # print "\t%s: %s"%(k, abs(v))
            
            mg.NBTrigger(readlist)
            results=mg.Read(readlist)
            #print results
            #for p in readlist:
            #    print p, results[p],
            #print
            
            pin=lv*c_sg_amp['total']
            pin.set_strict(False)
            pin=quantities.Quantity(si.WATT, pin.get_value(si.WATT))
            pfwd=results[names['pm_fwd']]
            pout=pfwd/c_amp_pm1['total']
            pout.set_strict(False)
            pout=quantities.Quantity(si.WATT, pout.get_value(si.WATT))
            pgtem=pout*c_amp_out['total']
            pgtem.set_strict(False)
            pgtem=quantities.Quantity(si.WATT, pgtem.get_value(si.WATT))
            print f, abs(lv), abs(pin), abs(pout), abs(pgtem) 
            sys.stdout.flush()
        print
        
        mg.RFOff_Devices()
            
finally:    
    mg.RFOff_Devices()
    mg.Quit_Devices()  