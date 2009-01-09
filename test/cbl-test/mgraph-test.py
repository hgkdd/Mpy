import sys
#sys.path.insert(0,'..')
from measure.device.aunits import *
import measure.tools.mgraph as mgraph

dot=sys.argv[1]
fr = sys.argv[2]
to = sys.argv[3]


mg=mgraph.MGraph(dotfile=dot)


mg.CreateDevices()
mg.Init_Devices()

for f in (500e6, 2000e6):# range(10,90):
    print "Freq:", f
    mg.SetFreq_Devices(f)
    mg.EvaluateConditions()
    corr=mg.get_path_correction(fr, to, POWERRATIO)
    for k,v in corr.items():
        print k, v

mg.Quit_Devices()
