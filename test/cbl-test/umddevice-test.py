import sys
sys.path.insert(0,'..')

import device as ud

ini=sys.argv[1]

cbl=ud.Cable()
cbl.Init(ini)

print "Reading the description"
print cbl.GetDescription()


print "Loop: SetFreq and GetData"
for freq in range(10,90):
    cbl.SetFreq(freq)
    err, uq=cbl.GetData('S21')
    val=uq.get_value(uq.__unit__).get_value()
    err=uq.get_value(uq.__unit__).get_uncertainty(uq.get_value(uq.__unit__))
    print freq, val.real, val.imag, err.real, err.imag


print "setVirtual, getVirtual"
print cbl.SetVirtual(True), cbl.GetVirtual()
print cbl.SetVirtual(False), cbl.GetVirtual()

print "Quit"
print cbl.Quit()
