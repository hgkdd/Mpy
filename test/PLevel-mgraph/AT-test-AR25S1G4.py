import pickle as pickle
from numpy import linspace,concatenate, log10
from scuq.quantities import Quantity
from scuq.si import WATT
import mpylab.env.univers.AmplifierTest

def dBm2W (v):
    return 10**(v*0.1)*0.001
def W2dBm (v):
    return 10*log10(v*1000)

description="AR-25S1G4"
MpyDIRS=['\\MpyConfig\\LargeGTEM', '.']

    
if True:
    dot='amplifier-test-sw800e6.dot'
    # keys: names in program, values: names in graph
    names={'sg': 'sg',
           'amp_in': 'amp_in',
           'amp_out': 'amp_out',
           'pm_fwd': 'pm1',
           'pm_bwd': 'pm2',
           'output': 'gtem'}

    AT = mpylab.env.univers.AmplifierTest.AmplifierTest(SearchPaths=MpyDIRS)
    AT.set_logfile('%s.log'%description)

    freqs=linspace(800e6, 4.2e9, 50)

    AT.Measure(description=description,
               dotfile=dot,
               names=names,
               freqs=freqs,
               levels=[Quantity(WATT, dBm2W(dBmval)) for dBmval in linspace(-30, 3, 34)])
    pickle.dump (AT, open('%s-new.p'%description, 'wb'), 2)
else:
    AT=pickle.load (open('%s-new.p'%description, 'rb'))
    AT.GetGainAndCompression(description=description)
    pickle.dump (AT, open('%s-new-processed.p'%description, 'wb'), 2)
