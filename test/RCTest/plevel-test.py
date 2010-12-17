from numpy import linspace,concatenate, log10
from scuq.quantities import Quantity
from scuq.si import WATT
from mpy.tools.util import locate
from mpy.tools.mgraph import MGraph, Leveler

def dBm2W (v):
    return 10**(v*0.1)*0.001
def W2dBm (v):
    return 10*log10(v*1000)

MpyDIRS=['\\MpyConfig\\LargeRC', '.']


dot='mvk-immunity.dot'
    #print dot
    # keys: names in program, values: names in graph
names={'sg': 'Sg',
       'amp_in': 'Amp_Input',
       'amp_out': 'Amp_Output',
       'pm_fwd': 'Pm1',
       'pm_bwd': 'Pm2',
       'output': 'TxAnt',
       'input': 'RxAnt',
       'pm_in': 'Pm'}


mg=MGraph(fname_or_data=dot, map=names, SearchPaths=MpyDIRS)
instrumentation=mg.CreateDevices()
print instrumentation

soll=Quantity(WATT, 10)

try:
    mg.Init_Devices()
    freqs=linspace(80e6, 1000e6, 20)

    for f in freqs:
        mg.EvaluateConditions()
        (minf, maxf) = mg.SetFreq_Devices(f)
        mg.RFOn_Devices()
        lev=Leveler(mg, mg.name.sg, mg.name.output, mg.name.output, mg.name.pm_fwd)
        sglv, pm_fwd_val = lev.adjust_level(soll)
        err, pm_ref_val=instrumentation[mg.name.pm_in].GetData()
        print f, sglv, pm_fwd_val, pm_ref_val 
        mg.RFOff_Devices()
finally:
    mg.Quit_Devices()