import pickle
import time

import numpy
import pylab
from scuq.quantities import Quantity
from scuq.si import WATT

from mpy.tools.aunits import *
from mpy.tools.mgraph import MGraph, Leveler


def dBm2W(v):
    return 10 ** (v * 0.1) * 0.001


def W2dBm(v):
    return 10 * numpy.log10(v * 1000)


MpyDIRS = ['\\MpyConfig\\LargeRC', '.']  # Suchpfad fuer dot, ini, dat

dot = 'mvk-immunity-src.dot'  # Messaufbau mit PMM Feldsonde ohne BLWA Verstaerker (Small RC)

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
mg = MGraph(fname_or_data=dot, themap=names, SearchPaths=MpyDIRS)  # Graph initialisieren
instrumentation = mg.CreateDevices()  # Geraete Instanzen
tuner = instrumentation[mg.name.tuner]  # Tuner
fp = instrumentation[mg.name.fp]  # Feldsonde
pm = instrumentation[mg.name.pm_in]
#
outname = "FieldProbeTest.p"
#
freq = [1.5e9, 3e9, 5e9, 7e9, 10e9]  # Liste der zu messenden Frequenzen
#  
Pmax1 = 80  # Leistungsbegrenzung f-Bereich 1 (Verstaerker BLWA & BLMA, max 100W)
Pmax2 = 24  # Leistungsbegrenzung f-Bereich 2 (Verstaerker BLMA, max 30W)
Pmax3 = 16  # Leistungsbegrenzung f-Bereich 3 (Verstaerker BLMA, max 20W)
Pmin = 0.01
Ppoints1 = 90 * 2
Ppoints2 = 50 * 2
Ppoints3 = 40 * 2  # max Anzahl der Punkte fuer den jeweiligen Leistungsbereich
Emax = 400  # max Feldstaerke der verwendeten Feldsonde
T_stirrer = 10  # # Periodendauer Ruehrerdrehung
#
try:
    print(' ')
    print('Please wait!')
    print(' --> devices initiated')
    mg.Init_Devices()
    #
    print(' --> data set created')
    DataDct = dict.fromkeys(freq, {})
    #
    print(' --> measurement started')
    for f in freq:
        DataDct[f] = {}
        #
        mg.EvaluateConditions()
        (minf, maxf) = mg.SetFreq_Devices(f)
        mg.RFOn_Devices()
        lev = Leveler(mg, mg.name.sg, mg.name.output, mg.name.output, mg.name.pm_fwd)
        #        
        if (f > 1e7) and (f <= 2e9):
            # power=numpy.logspace(numpy.log10(Pmin),numpy.log10(Pmax1),PPoints)
            p = numpy.linspace(numpy.sqrt(Pmin), numpy.sqrt(Pmax1), Ppoints1)
            power = p ** 2
        elif (f > 2e9) and (f <= 6e9):
            # power=numpy.logspace(numpy.log10(Pmin),numpy.log10(Pmax2),PPoints)
            p = numpy.linspace(numpy.sqrt(Pmin), numpy.sqrt(Pmax2), Ppoints2)
            power = p ** 2
        elif (f > 6e9) and (f < 18e9):
            # power=numpy.logspace(numpy.log10(Pmin),numpy.log10(Pmax3),PPoints)
            p = numpy.linspace(numpy.sqrt(Pmin), numpy.sqrt(Pmax3), Ppoints3)
            power = p ** 2
        else:
            break
        #
        for P in power:
            Ptarget = Quantity(WATT, P)
            #
            mg.RFOn_Devices()
            #  
            sglv, p_val = lev.adjust_level(Ptarget)
            Preal = p_val.get_expectation_value_as_float()
            #
            err, p_rx = pm.GetData()
            rxcorr = mg.get_path_correction(mg.name.pm_in, mg.name.input, unit=POWERRATIO)
            #
            # print 10*numpy.log10(1000*p_rx.get_expectation_value_as_float())
            #
            if P * 0.8 < Preal:
                DataDct[f][Preal] = {}
            else:
                break
            #
            t0 = time.time()
            e_vals = []
            p_rx_vals = []
            while True:  # Mehrfachmessung Feldstaerke ueber Ruehrerdrehung fuer anschl Mittelwertbildung
                err, e_val = fp.GetData()
                e_vals.append(e_val)
                #
                err, p_rx = pm.GetData()
                p_rx_vals.append(p_rx)
                #
                t = time.time()
                if t - t0 > T_stirrer:
                    break
            #
            N = float(len(e_vals))  # N = Anzahl der Feldstaerkemesswerte pro Ruehrerdrehung --> Mittelwertbildung
            #
            ex = DataDct[f][Preal]['Ex'] = sum([e[0].get_expectation_value_as_float() for e in e_vals]) / N
            ey = DataDct[f][Preal]['Ey'] = sum([e[1].get_expectation_value_as_float() for e in e_vals]) / N
            ez = DataDct[f][Preal]['Ez'] = sum([e[2].get_expectation_value_as_float() for e in e_vals]) / N
            et = DataDct[f][Preal]['Emag'] = numpy.sqrt(ex ** 2 + ey ** 2 + ez ** 2)
            pr = DataDct[f][Preal]['Prx'] = sum([p.get_expectation_value_as_float() for p in p_rx_vals]) / N * 1000
            #             
            print(
                'freq:  %.2f GHZ  power:  %.3f W real Power %.3f W Ex: %.2f  Ey: %.2f  Ez:  %.2f  Emag: %.2f  N: %.2f  Prx: %.2f' % (
                    f / 1e9, P, Preal, ex, ey, ez, et, N, pr))
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
          'figure.figsize': (6, 8)}
pylab.rcParams.update(params)
#
pylab.axes([0.125, 0.05, 0.825, 0.9])  # pylab.axes([0.125,0.125,0.825,0.825])
#
pylab.subplot(211)
pylab.xlabel('Square root of input power P in W^(-1/2)')
pylab.ylabel('Field strength E in V/m')
#  
for f in freq:
    power = sorted(DataDct[f].keys())
    Plot_P = numpy.sqrt(numpy.array(power))
    Plot_Emag = numpy.zeros((len(Plot_P)))
    #
    for i in range(len(power)):
        if DataDct[f][power[i]]['Emag'] is None:
            Plot_Emag[i] = None
        else:
            Plot_Emag[i] = DataDct[f][power[i]]['Emag']
    #
    pylab.plot(Plot_P, Plot_Emag, '.', label='%.1f GHz' % (f / 1e9))
    #
    xdata = Plot_P[0:10]
    ydata = Plot_Emag[0:10]
    #
    polycoeffs = numpy.polyfit(xdata, ydata, 1)
    yfit = numpy.polyval(polycoeffs, xdata)
    pylab.plot(xdata, yfit, color='grey')
    #
    yfit = numpy.polyval(polycoeffs, Plot_P)
    pylab.plot(Plot_P, yfit, color='grey', linestyle='dotted')
#
pylab.grid(True)
pylab.legend(loc='upper left')
#   
pylab.subplot(212)
pylab.xlabel('Input power P in W')
pylab.ylabel('Received power P in mW')
#
for f in freq:
    power = sorted(DataDct[f].keys())
    Plot_Pin = numpy.array(power)
    Plot_Prx = numpy.zeros((len(Plot_Pin)))
    #
    for i,pw in enumerate(power):
        if DataDct[f][pw]['Emag'] is None:
            Plot_Prx[i] = None
        else:
            Plot_Prx[i] = DataDct[f][pw]['Prx']
    #
    pylab.plot(Plot_Pin, Plot_Prx, '.', label='%.1f GHz' % (f / 1e9))
    #
    xdata = Plot_Pin
    ydata = Plot_Prx
    #
    polycoeffs = numpy.polyfit(xdata, ydata, 1)
    yfit = numpy.polyval(polycoeffs, xdata)
    pylab.plot(xdata, yfit, color='grey')
#
pylab.grid(True)
pylab.legend(loc='upper left')
#
pylab.savefig('FieldProbeTest_SmallRC.png', dpi=200)
pylab.show()
