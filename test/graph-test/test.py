from mpy.device import device
from scuq import *

amp_ini='smx25.ini'
sg_ini='rs_swm.ini'
pm_ini='gt8540c.ini'

amp=device.Amplifier()
amp.Init(amp_ini)
sg=device.Signalgenerator()
sg.Init(sg_ini)
pm1=device.Powermeter()
pm1.Init(pm_ini, 1)
pm2=device.Powermeter()
pm2.Init(pm_ini, 2)

sg.RFOn()

lv=quantities.Quantity(si.WATT, 1e-4)
sg.SetLevel(lv)
for freq in (100e6, 500e6, 900e6):
    sg.SetFreq(freq)
    amp.SetFreq(freq)
    pm1.SetFreq(freq)
    pm2.SetFreq(freq)
    
    print pm1.GetData()[1]
    print pm2.GetData()[1]
    
sg.RFOff()

amp.Quit()
sg.Quit()
pm1.Quit()
pm2.Quit()