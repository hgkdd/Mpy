#import time
import sys
sys.path.insert(0, '..')
import device
#import pdb

ini="m://umd-config//largeMSC//ini//umd-antenna2.ini"

#c=umddevice.UMDCable()
c=device.Antenna()



c.Init(ini,2)
#print dir(c)

for f in (100000000, 80000000,90000000):

    fehler,wert=c.SetFreq(f)

    w='gain'
    err, obj=c.GetData(w)
    print obj
c.Quit()
