import sys
# sys.path.insert(0,'..')

from mpy.device import amplifier

ini = sys.argv[1]

dev = amplifier.AMPLIFIER()
dev.init(ininame=ini)

for freq in range(10, 90):
    dev.setFreq(freq)
    err, uq = dev.getData(what='S21')
    val = uq.get_value(uq.__unit__).get_value()
    err = uq.get_value(uq.__unit__).get_uncertainty(uq.get_value(uq.__unit__))
    print(freq, val.real, val.imag, err.real, err.imag)

print(dev.SetState('Blah_und_Blub'), dev.Operate())
