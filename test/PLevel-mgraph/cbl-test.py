from mpylab.device.device import Cable

ini="ini/amp1out-gtem.ini"

cbl=Cable()
cbl.Init(ini)

for freq in [100e6, 1e9]:
    cbl.SetFreq(freq)
    err,dat= cbl.GetData('S21')
    print((freq, abs(dat)))
cbl.Quit()
