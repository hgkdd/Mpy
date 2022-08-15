import time
import sys
sys.path.insert(0, '\\herbrig\\new-umddevice')
sys.path.insert(0, '\\herbrig\\scuq')
import new_umddevice
#import pdb

#ini="m://umd-config//largeMSC//ini//umd-rs-smr.ini"
ini="m://umd-config//largeMSC//ini//umd-rs-smr-real.ini"

c=new_umddevice.UMDSignalgenerator()



c.Init(ini,1)

print('\n\n+++++++++++++Frequenztest+++++++++++++')
for f in (100000000, 80000000, 90000000):
    fehler,wert=c.setRFFreq(f)
    print(('f=',f,':',fehler, wert))
    time.sleep(1)

print('\n+++++++++++++Level Test+++++++++++++')
fehler,wert=c.setRFLevel(-50)
print(('level -50:',fehler, wert))
time.sleep(2)
fehler,wert=c.setRFLevel(-20)
print(('level -20:', fehler, wert))

print('\n+++++++++++++AN-AUS Test+++++++++++++')
fehler,wert=c.setRFstate(1)
print(('AN:', fehler, wert))
time.sleep(1)
fehler,wert=c.setRFstate(0)
print(('AUS:', fehler, wert))


print('\n+++++++++++++ConfAM-Test + AM-Test+++++++++++++')
fehler,wert=c.ConfAM(0, 25000, 20, 0, 0)
print(('ConfAM:', fehler, wert))
fehler,wert=c.setRFstate(1)
time.sleep(3)

fehler,wert=c.AM(0)
print(('AM-off:', fehler, wert))
fehler,wert=c.ConfAM(0, 20000, 20, 1, 0)
print(('ConfAM:', fehler, wert))

fehler,wert=c.AM(1)
print(('AM-on:', fehler, wert))
time.sleep(2)
fehler,wert=c.AM(0)
print(('AM-off:', fehler, wert))

fehler,wert=c.setRFFreq(90000000)
print((fehler, wert))
fehler,wert=c.setRFLevel(-20)
print((fehler, wert))

print('\n+++++++++++++ConfPM-Test + PM-Test+++++++++++++')
#int source, double freq, int pol, double width, double delay
fehler,wert=c.ConfPM(0, 40000, 0, 10e-6, 1e-7)
print(('ConfPM:', fehler, wert))

fehler,wert=c.setRFstate(1)
time.sleep(2)
fehler,wert=c.PM(0)
print(('PM-off:', fehler, wert))
fehler,wert=c.ConfPM(0, 40000, 0, 20e-6, 1e-7)
print(('ConfPM:', fehler, wert))
fehler,wert=c.PM(1)
print(('PM-on:', fehler, wert))
time.sleep(2)
fehler,wert=c.PM(0)
print(('PM-off:', fehler, wert))
time.sleep(1)

fehler,wert=c.setRFstate(0)
c.Quit()
