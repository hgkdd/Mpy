import sys
import cPickle as pickle
import scipy
import numpy
import pylab
from scuq.quantities import Quantity
from scuq.si import WATT, VOLT, METER
from mpy.tools.util import locate
from mpy.tools.mgraph import MGraph, Leveler

def dBm2W (v):
    return 10**(v*0.1)*0.001
def W2dBm (v):
    return 10*log10(v*1000)


    
MpyDIRS=['\\MpyConfig\\LargeRC', '.']  # Suchpfad fuer dot, ini, dat

dot='mvk-immunity-pmm.dot' # Messaufbau mit PMM field probe
    
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
freq=[7.9e9]#4e9,8e9]
stirrer=int(0)     
E=['Ex','Ey','Ez','Emag']
Pmax1=80
Pmax2=25
Pmax3=15
Emax=400
#
try:
    print ' '
    print 'Please wait!'
    print ' --> devices initiated' 
    mg.Init_Devices()  
    #
    print ' --> stirrer position adjusted'
    tuner.Goto(stirrer)
    #
    print ' --> data set created'
    DataDct=dict.fromkeys(freq, {})
    #
    print ' --> measurement started'
    for f in freq:
        if (f>=8e7) and (f<=2e9):   
            power=scipy.logspace(scipy.log10(0.001),scipy.log10(Pmax1),20)
        elif (f>2e9) and (f<=6e9):
            power=scipy.logspace(scipy.log10(0.001),scipy.log10(Pmax2),20)
        elif (f>6e9) and (f<12e9):
            power=scipy.logspace(scipy.log10(0.001),scipy.log10(Pmax3),20)
        else:
            break
        #
        DataDct[f]=dict.fromkeys(power,{})
        for P in power: 
            DataDct[f][P]=dict.fromkeys(E,None)
        #
        mg.EvaluateConditions()
        (minf, maxf) = mg.SetFreq_Devices(f)
        mg.RFOn_Devices()
        lev=Leveler(mg, mg.name.sg, mg.name.output, mg.name.output, mg.name.pm_fwd)
        for P in power: 
            Ptarget=Quantity(WATT, P) 
            #
            #  
            sglv1, p_val1 = lev.adjust_level(Ptarget)
            err, e_val = fp.GetData()
            #
            # print '  freq: ', f, '   P: ', P,'   E: ', e_val
            #
            DataDct[f][P]['Ex'] =e_val[0].get_expectation_value_as_float()
            DataDct[f][P]['Ey'] =e_val[1].get_expectation_value_as_float()
            DataDct[f][P]['Ez'] =e_val[2].get_expectation_value_as_float()        
            DataDct[f][P]['Emag']=scipy.sqrt(DataDct[f][P]['Ex']**2+DataDct[f][P]['Ey']**2+DataDct[f][P]['Ez']**2)
            #             
            print 'freq:  %dMHZ  power:  %.3fW  Ex: %.2f  Ey: %.2f  Ez:  %.2f  Emag: %.2f' %(f/1e6,P,DataDct[f][P]['Ex'],DataDct[f][P]['Ey'],DataDct[f][P]['Ez'],DataDct[f][P]['Emag']) 
            # 
            if DataDct[f][P]['Emag']>Emax:
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
pylab.xlabel('Input power P in dBm')
pylab.ylabel('Squared field strength ratio E to Emax')
#
for f in freq:
    power       = sorted(DataDct[f].keys())
    Plot_power  = 10*numpy.log10(numpy.array(power)*1e3)
    Plot_Emag2  = numpy.zeros((len(Plot_power))) 
    for i in range(len(power)): 
        if DataDct[f][power[i]]['Emag']==None:
            Plot_Emag2[i]=None
        else:    
            Plot_Emag2[i]=(DataDct[f][power[i]]['Emag']/Emax)**2
    #
    pylab.semilogy(Plot_power, Plot_Emag2,'x--',label='%d MHz'%(f/1e6))
#
pylab.ylim(1e-5,1e1)
pylab.xlim(0,50)
pylab.grid(True)
pylab.legend(loc='upper left')
pylab.savefig('FieldProbeTest.png',dpi=200)
pylab.show()        
    
    