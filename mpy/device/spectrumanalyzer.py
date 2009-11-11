# -*- coding: utf-8 -*-

import re
import functools
from mpy.tools.Configuration import Configuration,strbool,fstrcmp
from scuq import *
from mpy.device.device import CONVERT, Device
from mpy.device.driver import DRIVER

class SPECTRUMANALYZER(DRIVER):
    """
    Parent class of all py-drivers for spectrum analyzers.
    
    The parent class is :class:`mpy.device.driver.DRIVER`.
    """
    
    TRACEMODES=('WRITE','VIEW','AVERAGE', 'BLANK', 'MAXHOLD', 'MINHOLD')
    ATTMODES=('NORMAL', 'LOWNOISE', 'LOWDIST')
    #DETEC???: ['AUTOSELECT','AUTOPEAK','MAXPEAK','MINPEAK','SAMPLE','RMS', 'AVERAGE','DET_QPEAK']
    DETECTORS=('AUTOSELECT', 'AUTOPEAK', 'MAXPEAK', 'MINPEAK', 'SAMPLE', 'RMS', 'QUASIPEAK')
    TRIGGERMODES=('FREE', 'VIDEO', 'EXTERNAL')
    

    conftmpl={'description': 
                 {'description': str,
                  'type': str,
                  'vendor': str,
                  'serialnr': str,
                  'deviceid': str,
                  'driver': str},
                'init_value':
                    {'fstart': float,
                     'fstop': float,
                     'fstep': float,
                     'gpib': int,
                     'virtual': strbool,
                     'nr_of_channels': int},
                'channel_%d':
                    {'unit': str,
                     'attenuation': str,
                     'reflevel': float,
                     'rbw': str,
                     'vbw': float,
                     'span': float,
                     'trace': int,
                     'tracemode': str,
                     'detector': str,
                     'sweepcount': int,
                     'triggermode': str,
                     'attmode': str,
                     'sweeptime': float}}

    _FP=r'[-+]?(\d+(\.\d*)?|\d*\.\d+)([eE][-+]?\d+)?'
        
    def __init__(self):
        DRIVER.__init__(self)
        self._cmds={'SetCenterFreq':  [("'CENTERFREQ %s HZ'%something", None)],
                    'GetCenterFreq':  [('CENTERFREQ?', r'CENTERFREQ (?P<cfreq>%s) HZ'%self._FP)],
                    'SetSpan':  [("'SPAN %s HZ'%something", None)],
                    'GetSpan':  [('SPAN?', r'SPAN (?P<span>%s) HZ'%self._FP)],
                    'SetStartFreq':  [("'STARTFREQ %s HZ'%something", None)],
                    'GetStartFreq':  [('STARTFREQ?', r'STARTFREQ (?P<stfreq>%s) HZ'%self._FP)],
                    'SetStopFreq':  [("'STOPFREQ %s HZ'%something", None)],
                    'GetStopFreq':  [('STOPFREQ?', r'STOPFREQ (?P<spfreq>%s) HZ'%self._FP)],
                    'SetRBW':  [("'RBW %s HZ'%something", None)],
                    'GetRBW':  [('RBW?', r'RBW (?P<rbw>%s) HZ'%self._FP)],
                    'SetVBW':  [("'VBW %s HZ'%something", None)],
                    'GetVBW':  [('VBW?', r'VBW (?P<vbw>%s) HZ'%self._FP)],
                    'SetRefLevel':  [("'REFLEVEL %s DBM'%something", None)],
                    'GetRefLevel':  [('REFLEVEL?', r'REFLEVEL (?P<reflevel>%s) DBM'%self._FP)],
                    'SetAtt':  [("'ATT %s DB'%something", None)],
                    'GetAtt':  [('ATT?', r'ATT (?P<att>%s) DB'%self._FP)],
                    #Was hat das Auto zu bedeuten???
                    'SetAttAuto':  [("ATT -1", None)],
                    #Eingefügt???:
                    'SetAttMode': [("'ATTMode %s'%something", None)],
                    'GetAttMode':  [('ATTMode?', r'ATTMODE (?P<attmode>.*)')],
                    'SetPreAmp':  [("'PREAMP %s DB'%something", None)],
                    'GetPreAmp':  [('PREAMP?', r'PREAMP (?P<preamp>%s) DB'%self._FP)],
                    'SetDetector':  [("'DET %s'%something", None)],
                    'GetDetector':  [('DET?', r'DET (?P<det>.*)')],
                    'SetTraceMode':  [("'TMODE %s'%something", None)],
                    'GetTraceMode':  [('TMODE?', r'TMODE (?P<tmode>.*)')],
                    'SetTrace':  [("'TRACE %d'%trace", None)],
                    'GetTrace':  [('TRACE?', r'TRACE (?P<trace>\d+)')],
                    'SetSweepCount':  [("'SWEEPCOUNT %d'%something", None)],
                    'GetSweepCount':  [('SWEEPCOUNT?', r'SWEEPCOUNT (?P<scount>\d+)')],
                    'SetSweepTime':  [("'SWEEPTIME %s us'%something", None)],
                    'GetSweepTime':  [('SWEEPTIME?', r'SWEEPTIME (?P<stime>%s) us'%self._FP)],
                    'GetSpectrum':  [('DATA?', r'DATA (?P<power>%s)'%self._FP)],
                    'GetSpectrumNB':  [('DATA?', r'DATA (?P<power>%s)'%self._FP)],
                    'SetTriggerMode': [("'TRGMODE %d'%something", None)],
                    'GetTriggerMode':  [('TRGMODE?', r'TRGMODE (?P<trgmode>.*)')],
                    'SetTriggerDelay':  [("'TRGDELAY %s us'%something", None)],
                    'GetTriggerDelay':  [('TRGDELAY?', r'TRGDELAY (?P<tdelay>%s) us'%self._FP)],
                    'SetWindow':  [("'WINDOW %d'%window", None)],
                    'Quit':     [('QUIT', None)],
                    'GetDescription': [('*IDN?', r'(?P<IDN>.*)')]}

        _setgetlist=[("SetCenterFreq", "GetCenterFreq", "cfreq", float, None),
                     ("SetSpan", "GetSpan", "span", float, None),
                     ("SetStartFreq", "GetStartFreq", "stfreq", float, None),
                     ("SetStopFreq", "GetStopFreq", "spfreq", float, None),
                     ("SetRBW", "GetRBW", "rbw", float, None),
                     ("SetVBW", "GetVBW", "vbw", float, None),
                     ("SetRefLevel", "GetRefLevel", "reflevel", float, None),
                     ("SetAtt", "GetAtt", "att", float, None),
                     #Eingefügt???
                     ("SetAttMode", "GetAttMode", "attmode", str, "ATTMODES"),
                     ("SetPreAmp", "GetPreAmp", "preamp", float, None),
                     ("SetDetector", "GetDetector", "det", str, "DETECTORS"),
                     ("SetTraceMode", "GetTraceMode", "tmode", str, "TRACEMODES"),
                     ("SetTrace", "GetTrace", "trace", int, None),
                     ("SetSweepCount", "GetSweepCount", "scount", int, None),
                     ("SetSweepTime", "GetSweepTime", "stime", float, None),
                     ("SetTriggerMode", "GetTriggerMode", "trgmode", str, "TRIGGERMODES"),
                     ("SetTriggerDelay", "GetTriggerDelay", "tdelay", float, None)]

        # Die folgende for-Schleife arbeitet die _setgetlist ab und erzeugt dabei die Funktionen
        # über die das Gerät angesprochen werden kann.
        for setter, getter, what, type_, possibilities in _setgetlist:
            # Zuerst wird eine Klassen-Variable angelegt.
            # Dazu wird die Python-Built-in Funktion setattr verwendet. Mit ihr ist es möglich Variablen
            # anzulegen, deren Namen in einer String Variable gespeicher ist.
            # Der Aufruf setattr(self, "stfreq", 100) würde also self.stfreq=100 entprechen.
            
            # ??? warum muss die Variable angelegt werden?
            setattr(self, what, None)
            # closure...
            
            # Hier werden nun die Funktionen erzeugt.
            # Dazu wird die Python-Built-in Funktion setattr verwendet. Mit ihr ist es möglich Variablen
            # anzulegen, deren Namen in einer String Variable gespeicher ist.
            # Der Aufruf setattr(self, "stfreq", 100) würde also self.stfreq=100 entprechen.
            # Anstatt einer float Zahl oder eines Strings wird nun aber ein partial-Objekt übergeben, 
            # welches über die Funktion fuctools.partial() erzeugt wird.
            # Ein partial-Objekt verhält sich beinahe wie eine normale Funktion. Die Unterschiede
            # spielen hier keine Rolle.
            # Mit setattr(self, "SetCenterFreq", partial-Objekt) wird also eine Funktion erzeugt
            # die sich wie gewohnt ansprechen lässt. z.B. self.SetCenterFreq(100). 
            # 
            # Die Grundlage für das partial-Objekt ist eine schon bestehende Funktion, in diesem Fall
            # "self.SetGetSomething". Die zu Grunde gelegte Funktion muss functools.partial() als erstes
            # Argument übergeben werde. Die folgenden Argumente die partial() übergeben werden, werden
            # der Grund-Funktion wiederum selbst übergebe. Die übergebenen Argumente werden im
            # partial-Objekt gespeicher und jedes mal wenn ein partial-Objekt mit self.XXX() aufgerufen wird,
            # wird die Grund-Funktion mit den selben gespeicherten Argumenten aufgerufen.
            # Werden partial() nicht so viele Argumente übergeben wie die Grund-Funktion selbst hat, 
            # müssen die fehlenden Argumente beim Aufrufs des partial-Objets übergeben werden. z.B. 
            # self.XXX(100).
            # In unserem konkreten Fall bleibt beim erzeugen des partial-Objekts das Argument
            # "something" von ._SetGetSomething unberührt. something ist der Wert, der mit Hilfe
            # des VISA Befehls, gesetzt werden soll. Dieser muss dann beim Aufrufs des partial-Objetes
            # mit übergeben werden z.B. self.SetCenterFreq(100) (Die CenterFreq soll auf 100 Hz gesetzt werden)    
            setattr(self, setter, 
                          functools.partial(self._SetGetSomething, 
                                            setter=setter, 
                                            getter=getter, 
                                            type_=type_, 
                                            possibilities=possibilities,
                                            what=what))
            setattr(self, getter, 
                          functools.partial(self._GetSomething,
                                            getter=getter,
                                            type_=type_,
                                            what=what))

        self._internal_unit='dBm'


    # _SetGetSomething ist eine Funktion die nacheinander einen Visa-Write Befehl ausführt und danach
    # einen Vias-Query Befehl.
    #
    # Was ausgeführt wird, wird über die Argumente "setter" und "getter" bestimmt. Es müssen Strings
    # übergeben werden, die keys in ._cmds entsprechen.
    # 
    # Das Argument "something" bestimmt welcher Wert am Gerät eingestellt werden soll, z.B. 100 entspricht
    # einer Frequenz von 100 Hz, falls "setter" eine Frequenz verändert.
    #
    # "_type" bestimmt den Type des Rügabewerts z.B. float oder string
    #
    # "possibilities" ist eine Liste in der verschiedene Parameter für die VISA-Befehle stehen können.
    # z.B. TRACEMODES (siehe oben). Ist "possibilites" angegeben, dann wird "something" mit "possibilities 
    # über eine fuzzyStringCompare abgeglichen und die wahrscheinlichste Übereinstimmung als 
    # VISA Parameter verwendet.
    def _SetGetSomething(self, something, setter, getter, type_, possibilities, what):
        self.error=0
        if getattr(self,possibilities):
            something=fstrcmp(something, getattr(self,possibilities), n=1,cutoff=0,ignorecase=True)[0]
        dct=self._do_cmds(setter, locals())
        self._update(dct)
        dct=self._do_cmds(getter, locals())
        self._update(dct)
        if self.error == 0:
            if not dct:
                setattr(self, what, eval(what))
            else:
                setattr(self, what, type_(getattr(self, what)))
        return self.error, getattr(self, what)



    def _GetSomething(self, getter, type_, what):
        self.error=0
        dct=self._do_cmds(getter, locals())
        self._update(dct)
        if self.error == 0:
            if not dct:
                setattr(self, what, eval(what))
            else:
                setattr(self, what, type_(getattr(self, what)))
        return self.error, getattr(self, what)







#     def SetCenterFreq(self, cfreq):
#         self.error=0
#         dct=self._do_cmds('SetCenterFreq', locals())
#         self._update(dct)
#         dct=self._do_cmds('GetCenterFreq', locals())
#         self._update(dct)
#         if self.error == 0:
#             if not dct:
#                 self.cfreq=cfreq
#             else:
#                 self.cfreq=float(self.cfreq)
#             #print self.freq
#         return self.error, self.cfreq


if __name__ == '__main__':
    import sys

    try:
        ini=sys.argv[1]
    except IndexError:
        ini=None


    d=SPECTRUMANALYZER()
    d.Init(ini)
    if not ini:
        d.SetVirtual(False)

    err, des=d.GetDescription()
    print "Description: %s"%des

    for cfreq in [100]:
        print "Set center freq to %e Hz"%cfreq
        err, rfreq = d.SetCenterFreq(cfreq)
        if err == 0:
            print "Center Freq set to %e Hz"%rfreq
        else:
            print "Error setting center freq"


    d.Quit()
