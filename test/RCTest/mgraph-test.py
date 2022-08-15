from numpy import linspace,concatenate, log10
from scuq.quantities import Quantity
from scuq.si import WATT
from mpy.tools.util import locate
from mpy.tools.mgraph import MGraph

def dBm2W (v):
    return 10**(v*0.1)*0.001
def W2dBm (v):
    return 10*log10(v*1000)

MpyDIRS=['\\MpyConfig\\LargeRC', '.']


dot='mvk-immunity.dot'
    #print dot
    # keys: names in program, values: names in graph
names={'sg': 'Sg',
       'amp_in': 'Amp_Input',
       'amp_out': 'Amp_Output',
       'pm_fwd': 'Pm1',
       'pm_bwd': 'Pm2',
       'output': 'TxAnt'}


mg=MGraph(fname_or_data=dot, map=names, SearchPaths=MpyDIRS)
mg.CreateDevices()
try:
    mg.Init_Devices()

    f=200e6
    while True:
        fin=eval(input("Frequenz in Hz [%f]? "%f))
        try:
            f=float(fin)
        except:
            pass
        if f < 0:
            break
        mg.EvaluateConditions()
        mg.SetFreq_Devices(f)
        start=eval(input("Start: "))
        end=eval(input("Ende: "))
        start=mg.get_gname(start)
        end=mg.get_gname(end)
        if start != None and end != None: 
            pathcorr=mg.get_path_correction(start, end)
            paths=mg.find_all_paths(start, end)
            if len(paths)>1:
                print(("FEHLER: mehrere Pfade", paths))
            elif len(paths)==1:
                p=paths[0]
                print((' -> '.join([' -> '.join(pi.obj_dict['points']) for pi in p])))
            expec=abs(pathcorr.get_expectation_value_as_float())
            print((pathcorr.get_expectation_value(), expec, 20*log10(expec)))
finally:
    mg.Quit_Devices()