import sys
import pickle as pickle
import scipy
import numpy
import pylab
from scuq.quantities import Quantity
from scuq.si import WATT, VOLT, METER
from mpylab.tools.util import locate
from mpylab.tools.mgraph import MGraph, Leveler


def dBm2W(v):
    return 10 ** (v * 0.1) * 0.001


def W2dBm(v):
    return 10 * numpy.log10(v * 1000)


MpyDIRS = ['\\MpyConfig\\LargeRC', '.']  # Suchpfad fuer dot, ini, dat

dot = 'mvk-immunity.dot'  # Messung mit AR Feldsonde

names = {'sg': 'Sg',
         'amp_in': 'Amp_Input',
         'amp_out': 'Amp_Output',
         'pm_fwd': 'Pm1',
         'pm_bwd': 'Pm2',
         'output': 'TxAnt',
         'input': 'RxAnt',
         'pm_in': 'Pm',
         'tuner': 'Tuner',
         'fp': 'Fprobe'}
#
mg = MGraph(fname_or_data=dot, map=names, SearchPaths=MpyDIRS)  # Graph initialisieren
instrumentation = mg.CreateDevices()  # Geraete Instanzen
tuner = instrumentation[mg.name.tuner]  # Tuner
fp = instrumentation[mg.name.fp]  # Feldsonde
#
outname = "FieldProbeTest.p"
freq = [500e6, 1e9, 3e9, 8e9]
stirrer = 0
E = ['Ex', 'Ey', 'Ez', 'Emag']
#
Pmin = 0.1
Pmax1 = 80
Pmax2 = 25
Pmax3 = 15
Pn1 = 45
Pn2 = 25
Pn3 = 20
Emax = 600
#
try:
    print(' ')
    print('Please wait!')
    print(' --> devices initiated')
    mg.Init_Devices()
    #
    print(' --> stirrer position adjusted')
    tuner.Goto(stirrer)
    #
    print(' --> data set created')
    DataDct = dict.fromkeys(freq, {})
    #
    print(' --> measurement started')
    for f in freq:
        # DataDct[f]={}
        #
        mg.EvaluateConditions()
        (minf, maxf) = mg.SetFreq_Devices(f)
        mg.RFOn_Devices()
        lev = Leveler(mg, mg.name.sg, mg.name.output, mg.name.output, mg.name.pm_fwd)
        #
        if 8e7 <= f <= 2e9:  # (f>=8e7) and (f<=2e9):
            # power=scipy.logspace(scipy.log10(0.001),scipy.log10(Pmax1),20)
            p = scipy.linspace(scipy.sqrt(Pmin), scipy.sqrt(Pmax1), Pn1)
            power = p ** 2
            #
        elif (f > 2e9) and (f <= 6e9):
            # power=scipy.logspace(scipy.log10(0.001),scipy.log10(Pmax2),20)
            p = scipy.linspace(scipy.sqrt(Pmin), scipy.sqrt(Pmax2), Pn2)
            power = p ** 2
            #
        elif (f > 6e9) and (f < 12e9):
            # power=scipy.logspace(scipy.log10(0.001),scipy.log10(Pmax3),20)
            p = scipy.linspace(scipy.sqrt(Pmin), scipy.sqrt(Pmax3), Pn3)
            power = p ** 2
            #
        else:
            continue
        #
        for P in power:
            Ptarget = Quantity(WATT, P)
            sglv, p_val = lev.adjust_level(Ptarget)
            Preal = p_val.get_expectation_value_as_float()
            #
            if P * 0.8 < Preal:
                DataDct[f][Preal] = {}
            else:
                break
            #
            # e_val=[]
            err, e_val = fp.GetData()
            #
            DataDct[f][Preal]['Ex'] = e_val[0].get_expectation_value_as_float()
            DataDct[f][Preal]['Ey'] = e_val[1].get_expectation_value_as_float()
            DataDct[f][Preal]['Ez'] = e_val[2].get_expectation_value_as_float()
            DataDct[f][Preal]['Emag'] = scipy.sqrt(
                DataDct[f][Preal]['Ex'] ** 2 + DataDct[f][Preal]['Ey'] ** 2 + DataDct[f][Preal]['Ez'] ** 2)
            #             
            print(('f:  %dMHZ  P:  %.3fW  Preal: %.3fW Ex: %.2f  Ey: %.2f  Ez:  %.2f  Emag: %.2f' % (
            f / 1e6, P, Preal, DataDct[f][Preal]['Ex'], DataDct[f][Preal]['Ey'], DataDct[f][Preal]['Ez'],
            DataDct[f][Preal]['Emag'])))
            # 
            if DataDct[f][Preal]['Emag'] > Emax:
                break
        mg.RFOff_Devices()
    #
    fout = open(outname, 'wb')
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
          'figure.figsize': (6, 4)}
pylab.rcParams.update(params)
#
pylab.axes([0.125, 0.125, 0.825, 0.825])
#
pylab.xlabel('Square root of input power P in W^(-1/2)')
pylab.ylabel('Field strength E in V/m')
#
for f in freq:
    power = sorted(DataDct[f].keys())
    Plot_P = numpy.sqrt(numpy.array(power))
    Plot_Emag = numpy.zeros((len(Plot_P)))
    #
    for i in range(len(power)):
        # if DataDct[f][power[i]]['Emag']==None:
        #    Plot_Emag[i]=None
        # else:
        Plot_Emag[i] = DataDct[f][power[i]]['Emag']
    #
    pylab.plot(Plot_P, Plot_Emag, '.', label='%.1f GHz' % (f / 1e9))
#
pylab.ylim(0, Emax)
pylab.grid(True)
pylab.legend(loc='upper left')
pylab.savefig('FieldProbeTest.png', dpi=200)
pylab.show()
