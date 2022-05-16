import pickle
import sys
from numpy import linspace, log10, concatenate
from scuq.quantities import Quantity
from scuq.si import WATT
import mpy.env.univers.AmplifierTest
from mpy.tools.util import locate


def dBm2W(v):
    return 10 ** (v * 0.1) * 0.001


def W2dBm(v):
    return 10 * log10(v * 1000)


description = "BLWA 0810 100"
MpyDIRS = ['\\MpyConfig\\LargeRC', '.']

arg = 'evaluate'
try:
    arg = sys.argv[1]
except:
    pass

if arg.startswith('m'):
    dot = 'mvk-immunity-term.dot'
    # print dot
    # keys: names in program, values: names in graph
    names = {'sg': 'Sg',
             'amp_in': 'Amp_Input',
             'amp_out': 'Amp_Output',
             'pm_fwd': 'Pm1',
             'pm_bwd': 'Pm2',
             'output': 'TxAnt'}

    AT = mpy.env.univers.AmplifierTest.AmplifierTest(SearchPaths=MpyDIRS)
    AT.set_logfile('%s.log' % description)

    freqs = linspace(80e6, 1e9, 20)

    levels = [Quantity(WATT, dBm2W(dBmval)) for dBmval in linspace(-30, 3, 34)]
    AT.Measure(description=description,
               dotfile=dot,
               names=names,
               freqs=freqs,
               levels=levels, virtual=False, delay=.2)
    pickle.dump(AT, open('%s.p' % description, 'wb'), 2)
else:
    AT = pickle.load(open('%s.p' % description, 'rb'))
    AT.GetGainAndCompression(description=description)
    pickle.dump(AT, open('%s-processed.p' % description, 'wb'), 2)
    AT = pickle.load(open('%s-processed.p' % description, 'rb'))
    AT.OutputIniFile(description=description, fname='amp-lf-bonn-blwa.ini',
                     driver="amp_blwa_0810_100.py", gpib=8)
