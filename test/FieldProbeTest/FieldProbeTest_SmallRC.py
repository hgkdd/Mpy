import sys
import cPickle as pickle
import scipy
import numpy
import pylab
import time
from scuq.quantities import Quantity
from scuq.si import WATT, VOLT, METER
from mpy.tools.util import locate
from mpy.tools.mgraph import MGraph, Leveler

def dBm2W (v):
    return 10**(v*0.1)*0.001
def W2dBm (v):
    return 10*log10(v*1000)


    
MpyDIRS=['\\MpyConfig\\LargeRC', '.']  # Suchpfad fuer dot, ini, dat 

dot='mvk-immunity-pmm.dot' # Messaufbau mit PMM Feldsonde ohne BLWA Verstaerker
    
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
#
mg=MGraph(fname_or_data=dot, map=names, SearchPaths=MpyDIRS)    # Graph initialisieren
instrumentation=mg.CreateDevices()                              # Geraete Instanzen
tuner=instrumentation[mg.name.tuner]                            # Tuner
fp=instrumentation[mg.name.fp]                                  # Feldsonde
#
outname="FieldProbeTest.p" 
#
freq=[1e9,3e9,5e9,7e9,9e9] # Liste der zu messenden Frequenzen
#  
Pmax1=80                    # Leistungsbegrenzung f-Bereich 1 (Verstaerker BLWA & BLMA, max 100W)
Pmax2=24                    # Leistungsbegrenzung f-Bereich 2 (Verstaerker BLMA, max 30W)   
Pmax3=16                    # Leistungsbegrenzung f-Bereich 3 (Verstaerker BLMA, max 20W)
Pmin=0.01                   
PPoints=30                  # max Anzahl der Punkte fuer den jeweiligen Leistungsbereich
Emax=400                    # max Feldstaerke der verwendeten Feldsonde
T_stirrer=5 #               # Periodendauer Ruehrerdrehung
#
try:
    print ' '
    print 'Please wait!'
    print ' --> devices initiated' 
    mg.Init_Devices()  
    #
    print ' --> data set created'
    DataDct=dict.fromkeys(freq, {})
    #
    print ' --> measurement started'
    for f in freq:
        DataDct[f]={}
        #
        mg.EvaluateConditions()
        (minf, maxf) = mg.SetFreq_Devices(f)
        mg.RFOn_Devices()
        lev=Leveler(mg, mg.name.sg, mg.name.output, mg.name.output, mg.name.pm_fwd)
        #        
        if (f>=8e7) and (f<=2e9):   
            power=scipy.logspace(scipy.log10(Pmin),scipy.log10(Pmax1),PPoints)
        elif (f>2e9) and (f<=6e9):
            power=scipy.logspace(scipy.log10(Pmin),scipy.log10(Pmax2),PPoints)
        elif (f>6e9) and (f<18e9):
            power=scipy.logspace(scipy.log10(Pmin),scipy.log10(Pmax3),PPoints)
        else:
            break
        #
        for P in power: 
            Ptarget=Quantity(WATT, P) 
            #
            mg.RFOn_Devices()
            #  
            sglv, p_val = lev.adjust_level(Ptarget)
            Preal=p_val.get_expectation_value_as_float()
            #
            if P*0.8 < Preal:
                DataDct[f][Preal]={}
            else:
                break
            #
            t0=time.time()
            e_vals=[]
            while True: # Mehrfachmessung Feldstaerke ueber Ruehrerdrehung fuer anschl Mittelwertbildung
                err, e_val = fp.GetData()
                e_vals.append(e_val)
                t=time.time()
                if t-t0 > T_stirrer:
                    break
            #
            N=float(len(e_vals)) # N = Anzahl der Feldstaerkemesswerte pro Ruehrerdrehung --> Mittelwertbildung
            #
            ex=DataDct[f][Preal]['Ex'] =sum([e[0].get_expectation_value_as_float() for e in e_vals])/N
            ey=DataDct[f][Preal]['Ey'] =sum([e[1].get_expectation_value_as_float() for e in e_vals])/N
            ez=DataDct[f][Preal]['Ez'] =sum([e[2].get_expectation_value_as_float() for e in e_vals])/N        
            et=DataDct[f][Preal]['Emag']=scipy.sqrt(ex**2+ey**2+ez**2)
            #             
            print 'freq:  %.2f GHZ  power:  %.3f W real Power %.3f W Ex: %.2f  Ey: %.2f  Ez:  %.2f  Emag: %.2f  N: %.2f'%(f/1e9,P,p_val.get_expectation_value_as_float(),ex,ey,ez,et,N) 
            # 
            if DataDct[f][Preal]['Emag']>Emax:
                break
        mg.RFOff_Devices()
    #
    fout=open(outname, 'wb')  
    pickle.dump(DataDct, fout, 2)
    fout.close()
    
finally:
    mg.Quit_Devices()   
#
params = {'backend': 'ps',
            'font.size': 10,
            'axes.titlesize': 10,
            'axes.labelsize': 10,
            'text.fontsize': 10,
            'legend.fontsize': 10,
            'xtick.labelsize': 10,
            'ytick.labelsize': 10,
            'text.usetex': False,   
            'figure.figsize': (6,4)}
pylab.rcParams.update(params) 
#
pylab.axes([0.125,0.125,0.825,0.825])
#
pylab.xlabel('square root of input power P in sqrt(W)')
pylab.ylabel('field strength E in V/m')
#
for f in freq:
    power       = sorted(DataDct[f].keys())
    Plot_power  = numpy.sqrt(numpy.array(power)) # Plot_power  = 10*numpy.log10(numpy.array(power)*1e3)
    Plot_Emag2  = numpy.zeros((len(Plot_power))) 
    for i in range(len(power)): 
        if DataDct[f][power[i]]['Emag']==None:
            Plot_Emag2[i]=None
        else:    
            Plot_Emag2[i]=(DataDct[f][power[i]]['Emag'])
    #
    pylab.plot(Plot_power, Plot_Emag2,'.',label='%.1f GHz'%(f/1e9))
#
#pylab.ylim(1e-5,1e1)
#pylab.xlim(0,50)
pylab.grid(True)
pylab.legend(loc='upper left')
pylab.savefig('FieldProbeTest.png',dpi=200)
pylab.show()        
    
    