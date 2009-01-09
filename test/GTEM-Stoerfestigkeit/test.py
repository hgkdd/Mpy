import scipy
import math
scipy.pkgload('interpolate')
import sys
sys.path.insert(0,'..')
from aunits import *
import mgraph
from scuq import *
import scr3502

class GTEM_SUSCEPTIBILITY(object):
    def __init__(self, conf):
        self.conf=conf
        self.mg=mgraph.MGraph(dotfile=self.conf['dot'])
        self.mg.CreateDevices()
        self.mg.Init_Devices()
        self.EField=self.conf['EField']
        self.soll_leistung=dat_interpol(self.conf['calib'])
        self.fstart=self.conf['fstart']
        self.fstop=self.conf['fstop']
        self.fstep=self.conf['fstep']
        self.nf=int((self.fstop-self.fstart)/self.fstep)
        self.sg = self.mg.nodes['sg']['inst']
        self.pmfwd = self.mg.nodes['pm1']['inst']
        self.eut=scr3502.scr3502()

    def Measure(self):
        flist=[self.fstart+i*self.fstep for i in range(self.nf)]
        p_soll_list=map(dBm2Watt, self.soll_leistung(flist))
        self.mg.Zero_Devices()
        self.mg.RFOn_Devices()
        for f, psoll in zip(flist,p_soll_list):
            self.mg.SetFreq_Devices(f)
            self.eut.setFreq(f)
            self.mg.EvaluateConditions()
            att_amp_pm1 = self.mg.get_path_correction('amp_out', 'pm1', POWERRATIO)['total']
            att_amp_pm1 = abs(att_amp_pm1.__value__.get_value())
            att_amp_gtem = self.mg.get_path_correction('amp_out', 'gtem', POWERRATIO)['total']
            att_amp_gtem = abs(att_amp_gtem.__value__.get_value())
            cfactor=0
            sg_power=self.adjust_power(psoll)
            while not 0.9<cfactor<1.1:
                self.sg.SetLevel(sg_power)
                err, pist = self.pmfwd.GetData()
                pist=pist/att_amp_pm1*att_amp_gtem
                pist=pist.__value__.get_value()
                cfactor = psoll/pist
                sg_power=sg_power*cfactor
            print f, sg_power, psoll, pist, cfactor
            eutlevel=self.eut.getLevel()
            print "EUT:", eutlevel
        self.mg.RFOff_Devices()

    def adjust_power(self, psoll):
        psoll=quantities.Quantity(si.WATT, psoll)
        att_sg_gtem = self.mg.get_path_correction('sg', 'gtem', POWERRATIO)['total']
        att_sg_gtem=abs(att_sg_gtem.__value__.get_value())
        guess_sg=psoll/att_sg_gtem
        return guess_sg
            
    def Quit(self):
        self.mg.Quit_Devices()
        self.eut.quit()

def dat_interpol(cfile):
    flist=[]
    plist=[]
    for line in file(cfile):
        if line.startswith('#'):
            continue
        freq, power = map(float,line.split())
        freq=freq*1e6
        flist.append(freq)
        plist.append(power)
    interp=scipy.interpolate.interp1d(flist,plist)
    return interp

def dBm2Watt(p):
    return pow(10, p*0.1)*1e-3

def Watt2dBm(p):
    return 10*math.log10(p*1e3)

if __name__ == '__main__':
    dot=  "m:\\new-umddevice\\GTEM-Stoerfestigkeit\\gtem-stoerfestigkeit.dot"   #sys.argv[1]
    calib='Gtem-Kal.Okt2007-gesamt.csv'

    conf={'dot': dot,
          'EField': 10.0,
          'calib': calib,
          'fstart': 100e6,
          'fstop': 1000e6,
          'fstep': 100e6
          }

    #power=dat_interpol(conf['calib'])
    #print map(dBm2Watt,power(567e6))

    gtem=GTEM_SUSCEPTIBILITY(conf)
    gtem.Measure()
    gtem.Quit()
    
