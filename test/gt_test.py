import time
from visa import *
import pyvisa.vpp43 as vpp43

pm = instrument("GPIB::13")

pm.write("*IDN?")
print(pm.read())
#pm.write('GT1')
#pm.write('SWIFT GET BUFFER 10')
pm.write('BP')

for i in range(10):
    pm.write("CS")    
    pm.write('TR2')
    #time.sleep(1)
    state=0
    while state&1 != 1:
        state=vpp43.read_stb(pm.vi)
        #pm.write('*STB?')
        #state=int(pm.read())
        print('.', end=' ')
    #pm.wait_for_srq(100)
    buf=pm.read()
    print()
    print(i, buf)

    

