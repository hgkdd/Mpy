import sys
from mpy.tools.aunits import *
import mpy.tools.mgraph as mgraph

dot = sys.argv[1]
fr = sys.argv[2]
to = sys.argv[3]

mg = mgraph.MGraph(dotfile=dot)

mg.CreateDevices()
mg.Init_Devices()

for f in (500e6, 2000e6):
    print(("Freq:", f))
    mg.SetFreq_Devices(f)
    mg.EvaluateConditions()
    corr = mg.get_path_correction(fr, to, POWERRATIO)
    for k, v in list(corr.items()):
        print((k, v))

mg.Quit_Devices()
