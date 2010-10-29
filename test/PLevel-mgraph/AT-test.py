import cPickle as pickle
from numpy import linspace,concatenate
from scuq.quantities import Quantity
from scuq.si import WATT
import mpy.env.univers.AmplifierTest

def dBm2W (v):
    return 10**(v*0.1)*0.001
def W2dBm (v):
    return 10*np.log10(v*1000)

def get_gain_compression (pin, pout, small_signal_factor=10):
    pin_ss=[pi for pi in pin if pi <= pin[0]*small_signal_factor]
    pout_ss = pout[:len(pin_ss)]
    gain, offset = np.polyfit(pin_ss, pout_ss, 1)
    ideal = lambda pin: offset+gain*pin
    orig = interp1d(pin, pout)
    c1func = lambda pin: ideal(pin)/orig(pin)-1.259
    c3func = lambda pin: ideal(pin)/orig(pin)-1.995
    pinc1 = fmin(c1func, pin[0])
    pinc3 = fmin(c3func, pinc1)
    pountc1=orig(pinc1)
    poutc3=orig(pinc3)
    return gain, offset, pinc1, poutc1, pinc3, poutc3

dot='gtem-immunity.dot'
# keys: names in program, values: names in graph
names={'sg': 'sg',
       'amp_in': 'amp_in',
       'amp_out': 'amp_out',
       'pm_fwd': 'pm1',
       'pm_bwd': 'pm2',
       'output': 'gtem'}

AT = mpy.env.univers.AmplifierTest.AmplifierTest()
AT.set_logfile('at.log')

freqb1=linspace(10e3, 200e6, 20)
freqb2=linspace(200e6, 1e9 , 20)
freqs = concatenate((freqb1,freqb2))

AT.Measure(description="IFI SMX25",
           dotfile=dot,
           names=names,
           freqs=freqs,
           levels=[Quantity(WATT, dBm2W(dBmval)) for dBmval in linspace(-30, 0, 31)])
pickle.dump (AT, file('at-smx25.p', 'wb'), 2)