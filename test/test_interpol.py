from interpol import *
import numpy
import scuq

freqs=[p*1e6 for p in range(16)]
phis=[p*math.pi/16 for p in range(16)]
vals=[complex(math.cos(p),math.sin(p)) for p in phis]
dct=dict((v for v in zip(freqs,vals)))
cinter=cplx_interpol(dct)
print("Complex interpolation:")
print((cinter(5e5)))
#print abs(cinter(5e5)), math.atan2(cinter(5e5).imag, cinter(5e5).real)
print()

uqvals=[scuq.quantities.Quantity(scuq.si.VOLT,v) for v in vals]
dct2=dict((v for v in zip(freqs,uqvals)))

uqinter=UQ_interpol(dct2)
print("SCUQ interpolation:")
print((uqinter(5e5)))
#print math.atan2(uqinter(5e5).imag, uqinter(5e5).real)
print()

