import sys
import time
import math
import os

from pylab import *
from wx import *
from wx.lib.dialogs import *

sys.path.insert(0, '\\herbrig\\new-umddevice')
sys.path.insert(0, '\\herbrig\\scuq')

from scuq import *
import device

dir_pfad=r"I:\herbrig\messungen"
dir_name=r'\Messung_Q_smallMSC_'+time.strftime(r'%Y%m%d_%H%M%S',time.localtime())
pfad_data=dir_pfad+dir_name
pfad_bilder=pfad_data+r'\bilder'
os.mkdir(pfad_data)
os.mkdir(pfad_bilder)


def standardabweichung(werte):
    summe=0
    for i in werte:
        summe=summe+i
    MW=summe/float(len(werte))
    summe=0
    for i in werte:
        summe=summe+(i-MW)**2
    s=(1.0/(len(werte)-1)*summe)**0.5
    return s

def regression(x,y):
    summe=0
    for i in x:
        summe=summe+i
    MWx=summe/float(len(x))
    summe=0
    for i in y:
        summe=summe+i
    MWy=summe/float(len(y))

    summeZ=0
    summeN=0
    for i in range(len(x)):
        summeZ=summeZ+(x[i]-MWx)*(y[i]-MWy)
        summeN=summeN+(x[i]-MWx)**2
    anstieg=summeZ/summeN
    return anstieg, MWy-anstieg*MWx


############    Eingabe durch dot-File  ############################

#ini_sg="m://umd-config//largeMSC//ini//umd-rs-smr-real.ini"
ini_sg="m://umd-config//smallMSC//ini//umd-gt-12000A-real.ini"
ini_sa="m://umd-config//smallMSC//ini//umd-rs-fsp-real.ini"


############    Eingabe durch Setup     ############################

f_start=9e9
f_stop=13.2e9
f_step=200e6
f=1e9

vor_f=range(int((f_stop-f_start)/f_step))
alle_f=[i*f_step+f_start for i in vor_f]


############    Einstellungen           #############################
Q=[]

sg=device.Signalgenerator()
sa=device.Spectrumanalyzer()

sg.Init(ini_sg,1)
sa.Init(ini_sa,1)

sg.SetFreq(f)
sa.SetFreq(f)
sa.SetSpan(0)
sa.SetSweepTime(9e-6)
sa.SetTraceMode('AVERAGE')
sa.SetSweepCount(300)
sa.SetRBW(10e6)
power_ref = quantities.Quantity(si.WATT, 1e-4)
sa.SetRefLevel(power_ref)

power_in = quantities.Quantity(si.WATT, 1e-5)
sg.SetLevel(power_in)
sg.ConfPM('INT', 10000,'normal', 20e-6, 1e-7)
sg.SetPM('on')
sg.SetState('On')

############    Zeit fuer man. Triggereinstellungen   ###############


app=wx.PySimpleApp()
dialog = wx.MessageDialog ( None, 'Set up Trigger...', 'Dialog Title', wx.ICON_QUESTION)
dialog.ShowModal()
dialog.Destroy()
sg.SetState('Off')
############    Durchlauf               #############################
fd =open(pfad_data+r'\Q.dat', "w")
for f in alle_f:

    sg.SetFreq(f)
    sa.SetFreq(f)
    sg.SetState('On')
    time.sleep(5)


    fehler,obj=sa.GetSpectrum(0)

    data=obj.get_value(obj.__unit__)
    values=data._UncertainInput__value
    values_dB=[10*math.log10(wert*1000) for wert in values]
               
    #print min(values_dB), max(values_dB)

    fd2 =open(pfad_data+r'\%i_MHz.dat'%int(f/1e6), "w")
    for wert in values_dB:
        fd2.write("%e\n" %wert)
    fd2.close()
    anstiege=[]
    nrly_const_bord=0.3
    eut_lvl_bord=0.4

    anzahl=10
    for el in range(len(values_dB)-anzahl+1):
        anstiege.append(standardabweichung(values_dB[el:(el+anzahl)]))


    high=1
    fall=-1
    for abw in range(len(anstiege)):
        if (anstiege[abw] < nrly_const_bord)&(high==1):
            top_const_end=abw+anzahl/2
        if (anstiege[abw] > 3.2*eut_lvl_bord)&(fall==-1):
            start_fall=abw+anzahl/2
            high=0
            fall=1
        if (anstiege[abw] < 3*eut_lvl_bord) & (fall==1):
            end_fall=abw
            fall=0
        if (anstiege[abw] < eut_lvl_bord) & (fall==0):
            eut_const=abw+anzahl/2
            fall=-1

    #print top_const_end,start_fall,end_fall,eut_const

    data=values_dB
    x=[i*(9e-6)/len(data) for i in range(len(data))]

    data_top=data[:top_const_end]
    data_top_x=x[:top_const_end]
    m,n=regression(data_top_x, data_top)
    reg_top=[]
    reg_top_x=[]
    for el in x[:(top_const_end+50)]:
        reg_top.append(m*el+n)
        reg_top_x.append(el)

    data_fall=data[start_fall:end_fall]
    data_fall_x=x[start_fall:end_fall]
    m,n=regression(data_fall_x,data_fall)
    gefaelle=m
    reg_fall=[]
    reg_fall_x=[]
    for el in x[(start_fall-10):(end_fall+10)]:
        reg_fall.append(m*el+n)
        reg_fall_x.append(el)
        
    data_eut=data[eut_const:]
    data_eut_x=x[eut_const:]
    m,n=regression(data_eut_x,data_eut)
    reg_eut=[]
    reg_eut_x=[]
    for el in x[(eut_const-50):]:
        reg_eut.append(m*el+n)
        reg_eut_x.append(el)
        
    #print time.time()-Zeit
    Q_act=abs(20*math.pi*f/gefaelle/math.log(10))
    Q.append(Q_act)
    
    fd.write("%e; %f\n" %(f, Q_act))
    
    fig=None
    fig=plot(x,data,reg_top_x, reg_top, reg_fall_x, reg_fall, reg_eut_x, reg_eut)
    savepath=pfad_bilder+r'\%i_MHz.png'%int(f/1e6)
    savefig(savepath)
    clf()
    sg.SetState('Off')




##pfad_dB=r"I:\herbrig\messungen\fall.dat"
##fd =open(pfad_dB, "w")
##for wert in values_dB:
##    fd.write("%e\n" %wert)
##fd.close()

##
##plot(anstiege)
##show()
##    

##plot(values_dB)
##show()
print "guete:",Q
fig=plot(Q)
savepath=pfad_bilder+r"\Q.png"
savefig(savepath)



fd.close()
print 'gut!'
sg.Quit()
sa.Quit()




##datei='I:\herbrig\messungen\Q_auto'
##fd =open(datei, "w")
##fd.close()

  
