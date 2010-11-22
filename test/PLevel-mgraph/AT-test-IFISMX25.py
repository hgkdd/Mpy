import cPickle as pickle
from numpy import linspace,concatenate
from scuq.quantities import Quantity
from scuq.si import WATT
import mpy.env.univers.AmplifierTest
from mpy.tools.util import locate

def dBm2W (v):
    return 10**(v*0.1)*0.001
def W2dBm (v):
    return 10*np.log10(v*1000)

description="IFI SMX25"
MpyDIRS=['\\MpyConfig\\LargeGTEM', '.']


if True:
    dot='gtem-immunity.dot'
    #print dot
    # keys: names in program, values: names in graph
    names={'sg': 'sg',
           'amp_in': 'amp_in',
           'amp_out': 'amp_out',
           'pm_fwd': 'pm1',
           'pm_bwd': 'pm2',
           'output': 'gtem'}

    AT = mpy.env.univers.AmplifierTest.AmplifierTest(SearchPaths=MpyDIRS)
    AT.set_logfile('%s.log'%description)

    freqb1=linspace(10e3, 200e6, 20)
    freqb2=linspace(200e6, 1e9 , 20)
    freqs = concatenate((freqb1,freqb2))
    levels=[Quantity(WATT, dBm2W(dBmval)) for dBmval in linspace(-5, 0, 6)]
    AT.Measure(description=description,
               dotfile=dot,
               names=names,
               freqs=freqs,
               levels=levels, virtual=False)
    pickle.dump (AT, file('%s.p'%description, 'wb'), 2)
else:
    AT=pickle.load (file('%s.p'%description, 'rb'))
    AT.GetGainAndCompression(description=description)
    pickle.dump (AT, file('%s-processed.p'%description, 'wb'), 2)
