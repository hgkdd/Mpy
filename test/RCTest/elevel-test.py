import sys
from numpy import linspace,concatenate, log10, sqrt
from scuq.quantities import Quantity
from scuq.si import WATT, VOLT, METER
from mpylab.tools.util import locate
from mpylab.tools.mgraph import MGraph, Leveler

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
       'pm_in': 'Pm',
       'tuner': 'tuner',
       'fp':    'Fprobe'}


mg=MGraph(fname_or_data=dot, map=names, SearchPaths=MpyDIRS)
instrumentation=mg.CreateDevices()
#print instrumentation

soll=Quantity(VOLT/METER, 20)
def Emag(seq):
    #print seq
    l = [s*s for s in seq]
    #print l
    sqsum=sum(l, Quantity( VOLT**2/METER**2, 0))
    #print sqsum
    return sqrt(sqsum)

try:
    mg.Init_Devices()
    freqs=linspace(80e6, 18e9, 100)

    for f in freqs:
        mg.EvaluateConditions()
        (minf, maxf) = mg.SetFreq_Devices(f)
        mg.RFOn_Devices()
        lev=Leveler(mg, mg.name.sg, mg.name.output, mg.name.fp, mg.name.fp, datafunc=Emag)
        sglv, e_val = lev.adjust_level(soll)
        err, e_val = instrumentation[mg.name.fp].GetData()
        print((f, W2dBm(sglv.get_expectation_value_as_float()), soll, e_val))
        sys.stdout.flush()
        mg.RFOff_Devices()
finally:
    mg.Quit_Devices()