import pickle as pickle
from mpy.tools.mgraph import MGraph

MpyDIRS=['\\MpyConfig\\LargeGTEM', '.']

dot='simple.dot'
#print dot
# keys: names in program, values: names in graph
names={'pm1': 'pm1'}

mg=MGraph(dot, names, MpyDIRS)
mg.CreateDevices()
mg.Init_Devices()
s=pickle.dumps(mg)
mg.Quit_Devices()

del mg

mg = pickle.loads(s)
mg.CreateDevices()
mg.Init_Devices()
mg.Quit_Devices()
