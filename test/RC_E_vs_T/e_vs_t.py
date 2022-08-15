import sys
import pickle as pickle
from numpy import linspace,concatenate, log10, sqrt
from scuq.quantities import Quantity
from scuq.si import WATT, VOLT, METER
from mpy.tools.util import locate
from mpy.tools.mgraph import MGraph, Leveler

def dBm2W (v):
    return 10**(v*0.1)*0.001
def W2dBm (v):
    return 10*log10(v*1000)
def Emag(seq):
    #print seq
    l = [s*s for s in seq]
    #print l
    sqsum=sum(l, Quantity( VOLT**2/METER**2, 0))
    #print sqsum
    return sqrt(sqsum)

outname="e_vs_t_800MHz.p"  # Pickle File (Ausgabe)
soll=Quantity(WATT, 20)   # Leistung am Fusspunkt Tx
tpos=list(range(360))  # Tuner Positionen
fcenter=150e6 
fspan=5e6
Nf=200    
freqs=linspace(fcenter-0.5*fspan, fcenter+0.5*fspan, Nf)  # Frequenzliste
    
MpyDIRS=['\\MpyConfig\\LargeRC', '.']  # Suchpfad fuer dot, ini, dat

dot='mvk-immunity.dot' # Messaufbau
    #print dot
    # keys: names in program, values: names in graph
names={'sg': 'Sg',
       'amp_in': 'Amp_Input',
       'amp_out': 'Amp_Output',
       'pm_fwd': 'Pm1',
       'pm_bwd': 'Pm2',
       'output': 'TxAnt',
       'input': 'RxAnt',
       'pm_in': 'Pm',
       'tuner': 'Tuner',
       'fp':    'Fprobe'}


mg=MGraph(fname_or_data=dot, map=names, SearchPaths=MpyDIRS)  # Graph initialisieren
instrumentation=mg.CreateDevices()  # Geraete Instanzen
#print instrumentation.keys()
tuner=instrumentation[mg.name.tuner]  # Tuner
fp=instrumentation[mg.name.fp] # Feldsonde

    
try:
    mg.Init_Devices()  # Geraete Initialisieren
    try:
        dct=pickle.load(open(outname, 'rb'))  # Weiter nach Abbruch?
        completed_tp=set(tpos) # liste der bereits vollstaendig gemessenen Tuner Pos
        for f in freqs:
            t=set([a for a in list(dct[f].keys()) if dct[f][a] != None])
            completed_tp=completed_tp.intersection(t)
        #print completed_tp
    except:
        completed_tp=set()  # nix vollstaendig
        dct=dict.fromkeys(freqs, {})  # Ergebnis dict initialisieren
        for f in freqs:
            dct[f]=dict.fromkeys(tpos)
    for tp in tpos:   # ueber alle Tuner Positionen
        if tp in completed_tp:
            continue
        tuner.Goto(tp)
        mg.RFOn_Devices()
        for f in freqs:   # Ueber alle Frequenzen
            mg.EvaluateConditions()
            (minf, maxf) = mg.SetFreq_Devices(f)
            lev=Leveler(mg, mg.name.sg, mg.name.output, mg.name.output, mg.name.pm_fwd)
            sglv, p_val = lev.adjust_level(soll)  # Leistung einregeln
            err, e_val = fp.GetData() # Sonde auslesen
            print((tp, f))
            dct[f][tp]=e_val  # Werte (x,y,z) sichern
        mg.RFOff_Devices()
        fout=open(outname, 'wb')  
        pickle.dump(dct, fout, 2)  # weg damit...
        fout.close()
finally:
    mg.Quit_Devices()