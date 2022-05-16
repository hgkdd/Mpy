import time
import numpy
from scuq import *
from mpy.tools.mgraph import MGraph
from mpy.tools.util import format_block
from mpy.device.device import CONVERT

conv = CONVERT()

dot = 'smwtest.dot'

mg = MGraph(dot)

instrumentation = mg.CreateDevices()
for k, v in instrumentation.items():
    globals()[k] = v  # create devices in current namespace

mg.Init_Devices()  # init all devices in graph

try:
    mg.Zero_Devices()
    mg.RFOn_Devices()

    pwrmeters = ('pm',)
    for f in numpy.arange(10e6, 1e9, 10e6):
        mg.SetFreq_Devices(f)
        mg.EvaluateConditions()
        for pw in range(-50, 1, 1):
            val, unit = conv.c2scuq('dBm', pw)
            lv = quantities.Quantity(unit, val)
            sg.SetLevel(lv)
            time.sleep(0.5)
            results = mg.Read(pwrmeters)
            # print results
            print(f, end=' ')
            for p in pwrmeters:
                print(pw, conv.scuq2c(results[p].__unit__, 'dBm', results[p].__value__)[0], end=' ')
            print()
        print()
finally:
    mg.RFOff_Devices()
    mg.Quit_Devices()
