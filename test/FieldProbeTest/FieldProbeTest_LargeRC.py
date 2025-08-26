import pickle
import sys

import numpy
import pylab
from scuq.quantities import Quantity
from scuq.si import WATT

from mpylab.tools.mgraph import MGraph, Leveler


def dBm2W(v):
    return 10 ** (v * 0.1) * 0.001


def W2dBm(v):
    return 10 * numpy.log10(v * 1000)


if __name__ == '__main__':
    try:
        option = int(sys.argv[1])
    except IndexError:
        option = 0

    if option == 1:

        MpyDIRS = ['\\MpyConfig\\LargeRC', '.']  # Suchpfad fuer dot, ini, dat
        #
        dot = 'mvk-immunity.dot'  # Messung mit AR Feldsonde
        #
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
        #
        E = ['Ex', 'Ey', 'Ez', 'Emag']
        #
        freq = [1e9, 5e9, 10e9]
        Pmin = 0.1
        Pmax = [80, 30, 20]
        Pn = [50, 50, 50]
        Emax = 600
        stir_pos = 0
        #
        try:
            print(' ')
            print('Please wait!')
            print(' --> devices initiated')
            mg.Init_Devices()
            #
            print(' --> stirrer position adjusted')
            tuner.Goto(stir_pos)
            #
            print(' --> data set created')
            DataDct = dict.fromkeys(freq, None)
            for f in freq:
                DataDct[f] = {}
            #
            print(' --> measurement started')
            for f in freq:
                mg.EvaluateConditions()
                (minf, maxf) = mg.SetFreq_Devices(f)
                mg.RFOn_Devices()
                lev = Leveler(mg, mg.name.sg, mg.name.output, mg.name.output, mg.name.pm_fwd)
                #
                if 8e7 <= f <= 2e9:
                    p = numpy.linspace(numpy.sqrt(Pmin), numpy.sqrt(Pmax[0]), Pn[0])
                    power = p ** 2
                    #
                elif 2e9 < f <= 6e9:
                    p = numpy.linspace(numpy.sqrt(Pmin), numpy.sqrt(Pmax[1]), Pn[1])
                    power = p ** 2
                    #
                elif 6e9 < f <= 18e9:
                    p = numpy.linspace(numpy.sqrt(Pmin), numpy.sqrt(Pmax[2]), Pn[2])
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
                    err, e_val = fp.GetData()
                    #
                    DataDct[f][Preal]['Ex'] = e_val[0].get_expectation_value_as_float()
                    DataDct[f][Preal]['Ey'] = e_val[1].get_expectation_value_as_float()
                    DataDct[f][Preal]['Ez'] = e_val[2].get_expectation_value_as_float()
                    DataDct[f][Preal]['Emag'] = numpy.sqrt(
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
            outname = "FieldProbeTest.p"
            fout = open(outname, 'wb')
            pickle.dump(DataDct, fout, 2)
            fout.close()

        finally:
            mg.Quit_Devices()

    if option == 2:
        outname = "FieldProbeTest_02.p"
        DataDct = pickle.load(open(outname, 'rb'))
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
        pylab.xlabel('Wurzel der Leistung an der Sendeantenne in W^(-1/2)')
        pylab.ylabel('Feldstaerke E in V/m')
        #
        freq = sorted(DataDct.keys())
        print(freq)
        #
        for f in freq:
            Plot_P = []
            Plot_Emag = []
            #
            print((f, len(list(DataDct[f].keys())), list(DataDct[f].keys())))
            power = sorted(DataDct[f].keys())
            Plot_P = numpy.sqrt(numpy.array(power))
            Plot_Emag = numpy.zeros((len(Plot_P)))
            print((len(Plot_P)))
            #
            for i in range(len(power)):
                if DataDct[f][power[i]]['Emag'] is None:
                    Plot_Emag[i] = None
                else:
                    Plot_Emag[i] = DataDct[f][power[i]]['Emag']
            #
            pylab.plot(Plot_P, Plot_Emag, '.', label='%.1f GHz' % (f / 1e9))
            #
            xdata = Plot_P[:]
            ydata = Plot_Emag[:]
            #
            polycoeffs = numpy.polyfit(xdata, ydata, 1)
            yfit = numpy.polyval(polycoeffs, xdata)
            pylab.plot(xdata, yfit, color='grey')
            #
            yfit = numpy.polyval(polycoeffs, Plot_P)
            pylab.plot(Plot_P, yfit, color='grey', linestyle='dotted')

        #
        # pylab.ylim(0,Emax)
        pylab.grid(True)
        pylab.legend(loc='upper left')
        pylab.savefig('FieldProbeTest.png', dpi=200)
        pylab.show()
