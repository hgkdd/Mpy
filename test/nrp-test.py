import time
import random
import numpy as np
from visa import *

ch=1
masks=(2,4,8,16)
mask=masks[ch-1]

pm=instrument("GPIB::22")
pm.write("INIT%d:CONT OFF"%ch)
pm.write("SENS:AVER:STAT OFF")

while True:
    finished=False
    pm.write("INIT%d:IMM"%ch)
    while not finished:
        time.sleep(.01)
        print '.',
        stat=int(pm.ask("STAT:OPER:MEAS:SUMM:COND?"))
        if not (stat & mask):
            finished=True
    val=pm.ask("FETCH%d?"%ch)
    print val
