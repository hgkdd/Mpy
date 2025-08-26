import pickle
import sys
from numpy import linspace, concatenate, log10
from scuq.quantities import Quantity
from scuq.si import WATT
import mpylab.env.univers.AmplifierTest
from mpylab.tools.util import locate

def dBm2W (v):
    return 10**(v*0.1)*0.001
def W2dBm (v):
    return 10*log10(v*1000)

description="BLMA 1018 100_30_20"
MpyDIRS=['\\MpyConfig\\LargeRC', '.']

arg='evaluate'
try:
    arg=sys.argv[1]
except:
    pass
    
if arg.startswith('m'):
    dot='mvk-immunity-term.dot'
    #print dot
    # keys: names in program, values: names in graph
    names={'sg': 'Sg',
           'amp_in': 'Amp_Input',
           'amp_out': 'Amp_Output',
           'pm_fwd': 'Pm1',
           'pm_bwd': 'Pm2',
           'output': 'TxAnt'}

    AT = mpylab.env.univers.AmplifierTest.AmplifierTest(SearchPaths=MpyDIRS)
    AT.set_logfile('%s.log'%description)

    freqs=concatenate((linspace(1.0001e9, 2e9, 20), 
                       linspace(2.0001e9, 6e9, 20), 
                       linspace(6.0001e9, 18e9, 20))) 
    levels=[Quantity(WATT, dBm2W(dBmval)) for dBmval in linspace(-30, 3, 34)]
    AT.Measure(description=description,
               dotfile=dot,
               names=names,
               freqs=freqs,
               levels=levels, virtual=False, delay=.2)
    pickle.dump (AT, open('%s.p'%description, 'wb'), 2)
else:
    AT=pickle.load (open('%s.p'%description, 'rb'))
    AT.GetGainAndCompression(description=description)
    pickle.dump (AT, open('%s-processed.p'%description, 'wb'), 2)
    AT=pickle.load (open('%s-processed.p'%description, 'rb'))
    AT.OutputIniFile(description=description, fname='amp-hf-bonn-blma.ini', 
                                              driver="amp_blma_1018_100.py", gpib=7)
