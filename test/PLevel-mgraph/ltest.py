from numpy import linspace, concatenate
from scuq import *
from mpy.tools.mgraph import MGraph, Leveler


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
err = mg.Init_Devices()

freqb1=linspace(10e3, 200e6, 20)
freqb2=linspace(200e6, 1e9 , 20)
freqs = concatenate((freqb1,freqb2))

soll=quantities.Quantity(si.WATT, 1)


for f in freqs:
    mg.EvaluateConditions()
    (minf, maxf) = mg.SetFreq_Devices(f)
    mg.RFOn_Devices()
    lev=Leveler(mg, mg.name.sg, mg.name.output, mg.name.output, mg.name.pm_fwd)
    lev.adjust_level(soll)
    mg.RFOff_Devices()

    


