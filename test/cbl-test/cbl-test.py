import sys
sys.path.insert(0,'..')

import nport

ini=sys.argv[1]

cbl=nport.CABLE()
cbl.init(ininame=ini)

for freq in (1e9,): #range(10,90):
    cbl.setFreq(freq)
    err, uq=cbl.getData(what='S21')
    val=uq.get_value(uq.__unit__).get_value()
    err=uq.get_value(uq.__unit__).get_uncertainty(uq.get_value(uq.__unit__))
    print freq, val.real, val.imag, err.real, err.imag
