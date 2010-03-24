# -*- coding: utf-8 -*-
#
import functools
import re,time
import sys
import StringIO
from scuq import *
from mpy.device.networkanalyzer import NETWORKANALYZER as NETWORKAN
from mpy.tools.Configuration import fstrcmp

import numpy

#
#
# Für den Spectrumanalyzer R&S ZVL wird die Klasse 'zlv-6' definiert.
# Diese greift auf die Unterklasse SPECTRUMANALYZER (spectrumanalyzer.py) und darüber auf die Unterklasse DRIVER (driver.py) zu.
#
class NETWORKANALYZER(NETWORKAN):
    NETWORKANALYZERS=[]


    #S11 | S12 | S21 | S22
    #TRACEMODES=('WRITe', 'VIEW', 'AVERage', 'MAXHold', 'MINHold', 'RMS')
    
    #Map: {Allgemein gültige Bezeichnung : Bezeichnung Gerät} 
#    MapTRACEMODES={'WRITE':         'WRITe',
#                   'VIEW':          'VIEW',
#                   'AVERAGE':       'AVERage',
#                   'BLANK':         'OFF',       #Off umsetzen!!!!!  #RMS??
#                   'MAXHOLD':       'MAXHold',
#                   'MINHOLD':       'MINHold'
#                   }
    
    

    #Back Map: {RückgabeWert von Gerät : Allgemein gültige Bezeichnung} 
    MapSWEEPTYPES_Back={'LOG'  :   'LOGARITHMIC',
                        'LIN'  :   'LINEAR',
                        }
    
    MapSINGELSWEEP={'SINGEL' : 'OFF',
                    'CONTINUOUS': 'ON'}

    MapSINGELSWEEP_Back={'0' : 'SINGEL',
                         '1': 'CONTINUOUS'}
    


    
    
    #*************************************************************************
    #
    #                    Init
    #*************************************************************************
    def __init__(self):    
        NETWORKAN.__init__(self)
        self.traces={}
        self.windows={}
        self._internal_unit='dBm'
        
        NETWORKANALYZER.NETWORKANALYZERS.append(self)
        self.internChannel=-1
        self.internChannel=self.__gethighestChannelNumber()

        #
        # Im Wörterbuch '._cmds' werden die Befehle zum Steuern des speziellen Spektrumanalysator definiert, z.B. SetFreq() zum Setzen
        # der Frequenz. Diese können in der Dokumentation des entsprechenden Spektrumanalysator nachgeschlagen werden.
        # In der Unterklasse NETWORKANALYZER wurden bereits Methoden zur Ansteuerung eines allgemeinen Spektrumanalysators definiert,
        # welche die Steuerbefehle aus dem hier definierten '.cmds' Wörterbuch abrufen.
        # Das Wörterbuch enthält für jeden Eintrag ein Schlüsselwort mit dem allgemeinen Befehl als String, z.B. SetFreq(). Diesem
        # Schlüsselwort wird eine Liste zugeordnet, wobei jeder Listeneintrag ein Tupel ist und jeder Tupel einen Befehl und eine Vorlage
        # für die darauffolgende Antwort des Signalgenerators enthaelt.
        #
        self._cmds={'SetCenterFreq':  [("'SENSe%d:FREQuency:CENTer %s HZ'%(self.internChannel,something)", None)],              #Manual S. 499
                    'GetCenterFreq':  [("'SENSe%d:FREQuency:CENTer?'%(self.internChannel)", r'(?P<cfreq>%s)'%self._FP)],        #Manual S. 499
                    'SetSpan':  [("'SENSe%d:FREQuency:SPAN %s HZ'%(self.internChannel,something)", None)],                      #Manual S. 500
                    'GetSpan':  [("'SENSe%d:FREQuency:SPAN?'%(self.internChannel)", r'(?P<span>%s)'%self._FP)],                 #Manual S. 500
                    'SetStartFreq':  [("'SENSe%d:FREQuency:STARt %s HZ'%(self.internChannel,something)", None)],                #Manual S. 501
                    'GetStartFreq':  [("'SENSe%d:FREQuency:STARt?'%(self.internChannel)", r'(?P<stfreq>%s)'%self._FP)],         #Manual S. 501
                    'SetStopFreq':  [("'SENSe%d:FREQuency:STOP %s HZ'%(self.internChannel,something)", None)],                  #Manual S. 501
                    'GetStopFreq':  [("'SENSe%d:FREQuency:STOP?'%(self.internChannel)", r'(?P<spfreq>%s)'%self._FP)],           #Manual S. 501
                    # Meas/Resolution Bandwidht:
                    'SetRBW':  [("'SENSe%d:BANDwidth:RESolution %s HZ'%(self.internChannel,something)", None)],                 #Manual S. 473
                    'GetRBW':  [("'SENSe%d:BANDwidth:RESolution?'%(self.internChannel)", r'(?P<rbw>%s)'%self._FP)],             #Manual S. 473
                    ###[SENSe<Ch>:]BANDwidth|BWIDth[:RESolution]:SELect FAST | NORMal???
                   'SetRefLevel':  [("'DISPlay:WINDow%s:TRACe%s:Y:SCALe:RLEVel %s DBM'%(internWindow,windTraceNumber,something)", None)],            #Manual S. 430
                   'GetRefLevel':  [("'DISPlay:WINDow%s:TRACe%s:Y:SCALe:RLEVel?'%(internWindow,windTraceNumber)", r'(?P<reflevel>%s)'%self._FP)],    #Manual S. 430
                   'SetDivisionValue': [("'DISPlay:WINDow%s:TRACe%s:Y:SCALe:PDIVision %s DBM'%(internWindow,windTraceNumber,something)", None)],                 #Manual S. 429
                   'GetDivisionValue': [("'DISPlay:WINDow%s:TRACe%s:Y:SCALe:PDIVision?'%(internWindow,windTraceNumber)", r'(?P<setDivisionvalue>%s)'%self._FP)], #Manual S. 429    
                

                     ###Trace Mode nur Max hold
                     #CALCulate<Chn>:PHOLd MAX | OFF                #Manual S. 386
                     ###Dafür bei Sweep average!!!!!! 
                     #[SENSe<Ch>:]AVERage[:STATe] <Boolean>           #Manual S. 473
                     #[SENSe<Ch>:]AVERage:CLEar                       #Manual S. 472 
                    #'SetTraceMode':  [("'DISPlay:WINDow:TRACe%s:MODE %s'%(self.trace,something)", None)],  
                    #'GetTraceMode':  [("'DISPlay:WINDow:TRACe%s:MODE?'%self.trace", r'(?P<tmode>.*)')],
                    #'GetTraceModeBlank':  [("'DISPlay:WINDow:TRACe%s:STATe?'%(self.trace)", r'(?P<tmodeblank>\d+)')],
                    'SetTrace':  [("'CALCulate%d:PARameter:SDEFine \\'%s\\', \\'%s\\''%(self.internChannel,internTracename,measParam)", None)],    #Manual S. 384
                    'GetTrace':  [("'CALCulate%d:PARameter:CATalog?'%(self.internChannel)", r'(?P<trace>.*)')],                                    #Manual S. 381
               #    'DelTrace':  [("'CALCulate<Ch>:PARameter:DELete %s'%(self.internChannel,internTracename)",None)],                              #Manual S. 382
                    'ShwoTrace': [("'DISPlay:WINDow%d:TRACe%d:FEED \\'%s\\''%(internWindow,windTraceNumber,internTracename)",None)],                #Manual S. 426
                    'SetActiveTrace': [("'CALCulate%d:PARameter:SELect \\'%s\\''%(self.internChannel,internTracename)",None)],            
                     
                    'SetChannel': [("'CONFigure:CHANnel%d:STATe ON'%(self.internChannel)",None)],
               #     'DelChannel': [("'CONFigure:CHANnel%d:STATe OFF'%self.internChannel";None)],
               #     'GetChannel': [("'CONFigure:CHANnel%d:CATalog?'%self.internChannel", r'(?P<chan>.*')],             #Manual S. 415 
                    
                                   
                    'SetSweepType': [("'SENSe%d:SWEep:TYPE %s'%(self.internChannel,something)",None)],                   # LINear | LOGarithmic | SEGMent    #Manual S. 523
                    'GetSweepType': [("'SENSe%d:SWEep:TYPE?'%(self.internChannel)",r'(?P<sweepType>.*)')],
                    'SetSweepCount':  [("'SENSe%d:SWEep:COUNt %s'%(self.internChannel,something)", None)],            #Manual S. 520
                    'GetSweepCount':  [("'SENSe%d:SWEep:COUNt?'%(self.internChannel)", r'(?P<sweepcount>\d+)')],             #Manual S. 520
                    'SetSweepPoints':  [("'SENSe%d:SWEep:POINts %s '%(self.internChannel,something)", None)],            #Manual S. 521
                    'GetSweepPoints':  [("'SENSe%d:SWEep:POINts?'%(self.internChannel)", r'(?P<spoints>\d+)')],          #Manual S. 521
                    'SetSingelSweep':  [("'INITiate%d:CONTinuous %s'%(self.internChannel,something)",None)],            #Manual S. 442
                    'GetSingelSweep':  [("'INITiate%d:CONTinuous?'%(self.internChannel)",r'(?P<singelSweep>.*)')],      #Manual S. 442 
                    'GetSpectrum':  [("'CALCulate%d:DATA? FDAT'%(self.internChannel)", r'(?P<power>([-+]?(\d+(\.\d*)?|\d*\.\d+)([eE][-+]?\d+)?,?)+)')],      #Manual S. 339
                    #Später:
                    #'GetSpectrumNB':  [('DATA?', r'DATA (?P<power>%s)'%self._FP)],
 
                    'SetWindow':  [("'DISPlay:WINDow%d:STATe ON'%internWindow", None)],                               #Manual S. 424
              #      'DelWindow':  [("'DISPlay:WINDow<Wnd>:STATe OFF'%internWindow", None)],                          #Manual S. 424
              #      'GetWindow':  [("...", r'WINDOW (?P<wind>.*')],
                    
                    #'Quit':     [('QUIT', None)],
                    'SetNWAMode': [("INSTrument:SELect NWA", None)],
                    'GetDescription': [('*IDN?', r'(?P<IDN>.*)')]}
        
        # Die nachfolgende List stellt im Prinzip eine Tabelle mit drei Spalten dar.
        # In der ersten Spalte steht der Name der Funktion auf welche die entprechende Zeile der Tabelle
        # zutrifft.
        # In der zweiten Spalte stehen mögliche Werte die der Funktion übergeben werden können. Die
        # möglichen Werte können wiederum in Listen gespeichert werden. So ist es mölich einem Befehl
        # mehrer Werte zuzuordnen. Achtung!!! Die Werte werden als reguläre Expression interpretiert!!
        # In der dritten Spalte sind die Befehle vermerkt, welche den möglichen Werten in der vorhergehenden
        # Spalte, zugeordnent werden. 
        complex=[ ]
        
        
        # Dieser Teil ist nötig, weil die meisten Funktionen erst durch setattr in der init der
        # Main Klasse erstellt werden. Um die so erstellten Funktionen wieder zu überlagern,
        # muss sie durch setattr wieder überschreiben lassen:
        self._cmds['Complex']=complex
         
        
        
        setattr(self, "SetWindow", 
                          functools.partial(self._SetWindowIntern))
       # setattr(self, "GetWindow", 
       #                   functools.partial(self._GetWindowIntern)) 
          
        setattr(self, "SetTrace", 
                          functools.partial(self._SetTraceIntern))
        setattr(self, "GetTrace", 
                          functools.partial(self._GetTraceIntern))
        
        
        self.SetSweepCountSuper=self.SetSweepCount
        setattr(self, "SetSweepCount", 
                          functools.partial(self._SetSweepCountIntern))
        
        setattr(self, "SetRefLevel", 
                          functools.partial(self._SetRefLevelIntern))
        setattr(self, "GetRefLevel", 
                          functools.partial(self._GetRefLevelIntern))
    
    
    #******************************************************************************
    #
    #             Abgeänderte standard SetGet Funktionen
    #*******************************************************************************   

        
    
    #Erstellt ein neues Festern, dazu muss die Fensternumer übergeben werden.
    #Die hier übergebenen Nummer ist nur in der aktuellen Instanz güllig.
    #Die eigentliche auf dem Gerät verwendet Nummer wird von der Klasse selbständig ermittelt,
    #und ist über alle Instancen hinweg eindeutig.
    def _SetWindowIntern(self,winNumber):
        win=WINDOW(winNumber,self)
        self.windows.update({winNumber : win})
        #Nummer des Fensters holen, die auf dem Gerät verwendet weden soll.
        internWindow=win.getInternNumber()
        
        self.error=0
        dct=self._do_cmds('SetWindow', locals())
        self._update(dct)
        return self.error,0
        


    #Diese Funktion legt einen neuen Trace auf dem Gerät an
    # *tracename: Name des Traces, dieser ist nur für die aktuelle Instance gültig. Auf dem Gerät
    #        wird ein Name von der Klasse erstellt, der über alle Instancen hinweg eindeutig ist.
    # *measParam: Als String muss übergeben werde, was gemessen werden soll. z.B. "S11"
    # *winNumber: Her muss die Nummer des Fensters angegeben werden, in dem der Trace dargestellt werden soll.
    #             Das Fenster muss vorher mit SetWindow(self, winNumber) angelegt werden.
    def _SetTraceIntern(self,tracename,measParam,winNumber):
        
        tra = TRACE(tracename,self.windows.get(winNumber),measParam,self)
        self.traces.update({tracename: tra})
        #Nummer des Traces holen die auf dem Gerät verwendet werden soll
        internTracename=tra.getInternName()
        windTraceNumber=tra.getTraceWindowNumber()
        #Nummer des Fenster holen, die auf dem Gerät verwendet wird.
        internWindow = self.windows.get(winNumber).getInternNumber()
        
        self.error=0
        dct=self._do_cmds('SetTrace', locals())
        self._update(dct)
        
        dct=self._do_cmds('ShwoTrace', locals())
        self._update(dct)
        
        return self.error,0
    
    def _GetTraceIntern(self,tracename):
        tra = self.traces.get(tracename)
        internTracename = tra.getInternName()
        
        
        self.error=0
        dct=self._do_cmds('GetTrace', locals())
        self._update(dct)
        
        trace = re.split(r",",self.trace[1:-1])
        #print trace.index(internTracename)+1
        #print trace

        return self.error,trace[trace.index(internTracename)+1]
    
        
    def _SetSweepCountIntern(self,something):
        self.error=0
        self.error=self.SetSingelSweep("SINGEL")[0]
        self.error,ret=self.SetSweepCountSuper(something)
        return self.error,ret
    
    def _SetRefLevelIntern(self,tracename,level):
        self.error=0
        tra = self.traces.get(tracename)
        windTraceNumber = tra.getTraceWindowNumber()
        internWindow = tra.getWindow().getInternNumber()
        something=level
        dct=self._do_cmds('SetRefLevel', locals())
        self._update(dct)
        self.error,ret=self.GetRefLevel(tracename)
        return self.error,ret
        
        
    def _GetRefLevelIntern(self,tracename):
        self.error=0
        tra = self.traces.get(tracename)
        windTraceNumber = tra.getTraceWindowNumber()
        internWindow = tra.getWindow().getInternNumber()
        dct=self._do_cmds('GetRefLevel', locals())
        self._update(dct)
        if not dct:
                 self.reflevel=self.reflevel
        else:
                 self.reflevel=float(self.reflevel)        
        return self.error,self.reflevel
    
    #************************************   
    #  Spectrum aus Gerät auslesen
    #************************************
    def GetSpectrum(self,tracename):
        tra = self.traces.get(tracename)
        internTracename = tra.getInternName()
        
        
        self.error=0
        dct=self._do_cmds('SetActiveTrace', locals())
        self._update(dct)
        
        #sleep ist nötig, da das Gerät einen Moment benötigt, bis es den ActiveTrace
        #richtig gesetzt hat
        time.sleep(0.1)
        
        dct=self._do_cmds('GetSpectrum', locals())
        self._update(dct)
        if self.error == 0:
            if not dct:
             self.power=0
        else:
             self.power=float(self.power)
        
        #Spectrum wird als ein String vom Gerät übertragen.
        #Werte sind durch Komma getrennt, und werden mit Hilfe von
        #split in eine liste umgewandelt.
        self.power=re.split(',', self.power)

        #print self.GetStartFreq()
        #print self.GetStopFreq()
        #print self.GetSweepType()

        #print numpy.logspace(self.GetStartFreq()[1],self.GetStopFreq()[1],num=len(self.power))
        #print numpy.linspace(self.GetStartFreq()[1],self.GetStopFreq()[1],len(self.power))
        # xValues = 
        #Die einzelnen Werte der Liste werden hier in float Zahlen
        #umgewandelt   
       # pow=[]
       # for i in self.power:
       #     pow.append(float(i))

        #xValues als auch y=pow in einem Tuple speichern
       # self.power = (tuple(xValues),tuple(pow))
        return self.error, self.power
    



    #******************************************************************************
    #
    #             Verwaltungs Funktionen
    #*******************************************************************************


    def getChannelNumber(self):
        return self.internChannel


    def __gethighestChannelNumber(self):
        numb=1
        for nw in NETWORKANALYZER.NETWORKANALYZERS:
            if (nw.getChannelNumber() >= numb):
                numb = nw.getChannelNumber()+1
        return numb

   #Erstellt einne neuen Channel auf dem Gerät
    def _SetChannelIntern(self):
        
        self.error=0
        dct=self._do_cmds('SetChannel', locals())
        self._update(dct)
        return self.error,0
            
    #Diese Funktion schlaten das ZVL in den Spectrum Analyzer Mode
    def SetNWAMode(self):
        self.error=0
        dct=self._do_cmds('SetNWAMode', locals())
        self._update(dct)
        return self.error,0
    


    #***************************************************************************
    #
    #       Die Init Funktion initialisiert das Gerät, sie muss als erstes aufgerufen werden
    #***************************************************************************
    def Init(self, ini=None, channel=None):                
        if channel is None:
            channel=1
        self.error=NETWORKAN.Init(self, ini, channel)
        sec='channel_%d'%channel
        try:
            self.levelunit=self.conf[sec]['unit']
        except KeyError:
            self.levelunit=self._internal_unit
        
        
        
        
        #Schaltet das ZVL in in den SAN - Spectrum analyzer Mode
        self.SetNWAMode()
        
        #Erstellt einne neuen Channel auf dem Gerät
        self._SetChannelIntern()
        
        #   
        # Die Befehlsliste (dictionary) 'self._cmds'  wird mit einem Eintag namens 'Preset' erweitert und bekommt als Wert zunächst eine leere Liste zugewiesen.
        # Als Wert wurde eine Liste gewählt, da zur Initilisierung mehrere Befehle notwendig sein können. Jedem Listeneintrag bzw.
        # Initialisierungseschritt muss ein Tupel bestehend aus dem Befehl und eine Auswertung der Spektrumanalysator Antwort zugewiesen
        # werden. 
        # Zur Auswahl der notwendigen Initialisierungsschritte wird zunächst die Liste 'presets' definiert. Dabei handelt
        # es sich um eine Art Tabelle mit drei Spalten, welche die möglichen Initialisierungsschritte und falls vorhanden zugehörigen
        # Optionen inhaltet. 
        #
        self._cmds['Preset']=[]
        presets=[
                 #('trace',
                 #     None,
                 #     'SetTrace')
                      ]
        
        
        #self.SetTrace(self.conf[sec]['trace'])
        
        #
        # Die zur Initialisierung des Signalgenerators notwendigen Schritte werden durch zeilenweise Betrachtung der Liste 'presets'
        # herausgefiltert und in die Befehlsliste (dictionary) 'self._cmds['Preset']' übertragen und stehen damit stehen auch in 'sg._cmds' zur
        # Verfügung.
        # Die Klassenvariable '.conf' (dictionary) wurde in der (Unter-)Klasse DRIVER definert, sie enthält die Daten der ini-Datei.
        # In 'sec' ist gespeicher welcher Channel bearbeitet wird, somit erhält man über '.conf[sec]' zugriff auf die
        # Einstellungen für den aktuellen channel.
        #
        # -> If / else Anweisung zur Behandlung von Initialisierungsschritten ohne Optionen (if) und mit Optionen (else).
        # -> Wurden keine Optionen Angeben so wird versucht ob action dem Namen einer Funktion entspricht,
        #    ist dies der Fall, wird die entsprechende Funktion ausgeführt.
        #    Gibt es keine passende Funktion so der Befehl in 'self._cmds['Preset']' übertragen.
        # -> Wurden in 'presets' Optionen angegeben, dann werden diese einzeln durch eine for-Schleife abgearbeitet.
        #    Durch eine if-Anweiseung wird überprüft, welcher der möglichen Optionen in der ini-Datei angegeben wurden.
        #    Wird eine Übereinstimmung gefunden, wird der Befehl in 'self._cmds['Preset']' übertragen.
        # 
        for k, vals, actions in presets:
            #print k, vals, actions
            try:
                v=self.conf[sec][k] 
        
                if (vals is None):
                    try:
                        err,ret=getattr(self,actions)(v)
                        if err != 0:
                            self.error=err
                            return self.error
                    except (AttributeError):
                        self._cmds['Preset'].append((eval(actions[0]),actions[1])) 
                else:
                    for idx,vi in enumerate(vals):
                        if v.lower() in vi:
                            self._cmds['Preset'].append(actions[idx])
            except KeyError:
                pass
            
            
        #
        # Initialisierung des Signalgenerators über die Methode '._do_cmds' der Klasse DRIVER (driver.py)
        #
        dct=self._do_cmds('Preset', locals())
        self._update(dct)                
        return self.error
        
            
    
class TRACE(object):
    
    TRACES=[]
    
    def __init__(self,name,win,measParam,nw):
        TRACE.TRACES.append(self)
        self.name=name
        self.window=win
        self.networkanalyzer=nw
        self.measParameter = measParam
        self.traceWindowNumber=-1
        self.traceWindowNumber=self.__gethighestTraceWindowNumber()
        self.internName='%s_Ch%dWIN%dTR%d'%(name,self.networkanalyzer.getChannelNumber(),self.window.getInternNumber(),self.traceWindowNumber)
    def __gethighestTraceWindowNumber(self):
        numb=9
        for trace in TRACE.TRACES:
            if (trace.getTraceWindowNumber() >= numb):
                numb = trace.getTraceWindowNumber()+1
        return numb
            
    def getTraceWindowNumber(self):
        return self.traceWindowNumber
    
    def getName(self):
        return self.name
    
    def getInternName(self):
        return self.internName
    
    def getMeasParameter(self):
        return self.measParameter
    
    def getWindow(self):
        return self.window
    
    def getNetworkanalyzer(self):
        return self.networkanalyzer
    
    
class WINDOW(object):
    
    WINDOWS=[]
    
    def __init__(self,number,nw):
        WINDOW.WINDOWS.append(self)
        self.networkanalyzer=nw
        self.number=number
        self.internNumber=-1
        self.internNumber=self.__gethighestWindowNumber()
        
    def __gethighestWindowNumber(self):
        numb=1
        for win in WINDOW.WINDOWS:
            if (win.getInternNumber() >= numb):
                numb = win.getInternNumber()+1
        return numb
        
    def getInternNumber(self):
        return self.internNumber
    
    def getNumber(self):
        return self.number
    
    def getNetworkanalyzer(self):
        return self.networkanalyzer



##########################################################################       
#
# Die Funktion main() wird nur zum Test des Treibers verwendet!
###########################################################################
def main():
    from mpy.tools.util import format_block
    #from mpy.device.signalgenerator_ui import UI as UI
    #
    # Wird f￼r den Test des Treibers keine ini-Datei ￼ber die Kommnadoweile eingegebnen, dann muss eine virtuelle Standard-ini-Datei erzeugt
    # werden. Dazu wird der hinterlegte ini-Block mit Hilfe der Methode 'format_block' formatiert und der Ergebnis-String mit Hilfe des Modules
    # 'StringIO' in eine virtuelle Datei umgewandelt.
    #
    try:
        ini=sys.argv[1]
    except IndexError:
        ini=format_block("""
                        [DESCRIPTION]
                        description: 'ZLV-K1'
                        type:        'NETWORKANALYZER'
                        vendor:      'Rohde&Schwarz'
                        serialnr:
                        deviceid:
                        driver:

                        [Init_Value]
                        fstart: 100e6
                        fstop: 6e9
                        fstep: 1
                        gpib: 20
                        virtual: 0

                        [Channel_1]
                        unit: 'dBm'
                        attenuation: auto
                        reflevel: -20
                        rbw: auto
                        vbw: 10e6
                        span: 6e9
                        trace: 1
                        tracemode: 'WRITe'
                        detector: 'APEak'
                        sweepcount: 0
                        triggermode: 'IMMediate'
                        attmode: auto
                        sweeptime: 10e-3
                        sweeppoints: 500
                        """)
                        # rbw: 3e6
        ini=StringIO.StringIO(ini)
        
        
        ini2=format_block("""
                        [DESCRIPTION]
                        description: 'ZLV-K1'
                        type:        'NETWORKANALYZER'
                        vendor:      'Rohde&Schwarz'
                        serialnr:
                        deviceid:
                        driver:

                        [Init_Value]
                        fstart: 100e6
                        fstop: 6e9
                        fstep: 1
                        gpib: 20
                        virtual: 0

                        [Channel_1]
                        unit: 'dBm'
                        attenuation: auto
                        reflevel: -20
                        rbw: auto
                        vbw: 10e6
                        span: 6e9
                        trace: 1
                        tracemode: 'WRITe'
                        detector: 'APEak'
                        sweepcount: 0
                        triggermode: 'IMMediate'
                        attmode: auto
                        sweeptime: 10e-3
                        sweeppoints: 500
                        """)
                        # rbw: 3e6
        ini2=StringIO.StringIO(ini2)
        
    # #
    # # Zum Test des Treibers werden sogenannte Konsistenzabfragen ('assert' Bedingungen) verwendet, welche einen 'AssertationError' liefern,
    # # falls die Bedingung 'false' ist. Zuvor wird eine Testfrequenz und ein Level festgelegt, ein Objekt der Klasse SMB100A erzeugt und der
    # # Signalgenerator initialisiert.
    # #
    #from mpy.device.networkanalyzer_ui import UI as UI
    nw=NETWORKANALYZER()
    nw2=NETWORKANALYZER()
    try:
        from mpy.device.networkanalyzer_ui import UI as UI
    except ImportError:
        pass
    else:
        ui=UI(nw,ini=ini)
        ui.configure_traits()
        sys.exit(0)    
    
    err=nw.Init(ini)
    assert err==0, 'Init() fails with error %d'%(err)
    
    
    err=nw2.Init(ini2)
    assert err==0, 'Init() fails with error %d'%(err)
    
    
    
    nw.SetWindow(1)
    nw.SetTrace("Trc1","S11",1)
    #nw.SetTrace("Trc2","S11",1)
    
    
    #nw2.SetWindow(1)
    #nw2.SetTrace("Trc2","S11",1)
    #nw2.SetTrace("Trc3","S21",1)
    #nw2.SetWindow(2)
    #nw2.SetTrace("Trc2","S22",2)
    
    
    ret=nw.GetTrace("Trc1")
    print '%s(): Rückgabewert: %s   Sollwert: %s'%("GetTrace",ret[1],"--")
    
    ret= nw.SetRefLevel("Trc1",0)     #Default: 0
    print '%s(): Rückgabewert: %s   Sollwert: %s'%("SetRefLevel",ret[1],"20")
     
    
    _assertlist=[
                 ("SetCenterFreq", 3e9,"assert"),                     #Default:3e9
                  ('SetSpan',5999991000,"print"),                            #Default:6e9
                  ('SetStartFreq',9e3,"assert"),                      #Default:9e3
                  ('SetStopFreq',6e9,"assert"),                       #Default:6e9
                  ('SetRBW',10e3,"assert"),                           #Default:10e3
                  ('SetSweepType',"LOGARITHMIC","print"),                  #LINear | LOGARITHMIC | SEGMent   
                  ('SetSweepPoints',50,"assert"),                     #Default: 201  
                  ('SetSingelSweep',"CONTINUOUS" ,"print"),           #Singel,continuous 
                  #('SetSweepCount',1,"print"),                       #Default: 1
                 ]
 
    for funk,value,test in _assertlist:
        err,ret = getattr(nw,funk)(value)
        assert err==0,  '%s() fails with error %d'%(funk,err)
        if value != None:
            if test == "assert":
                assert ret==value, '%s() returns freq=%s instead of %s'%(funk,ret,value)
            else:
                print '%s(): Rückgabewert: %s   Sollwert: %s'%(funk,ret,value)
        else:
            print '%s(): Rückgabewert: %s'%(funk,ret)


    err,spectrum=nw.GetSpectrum("Trc1")
    assert err==0, 'GetSpectrum() fails with error %d'%(err)
    print spectrum
    
    #err,spectrum=nw.GetSpectrum("Trc2")
    #assert err==0, 'GetSpectrum() fails with error %d'%(err)
    #print spectrum
    
    #err=nw.Quit()
    #assert err==0, 'Quit() fails with error %d'%(err)
#
#      
#  ------------ Hauptprogramm ---------------------------
#
# Die Treiberdatei selbst und damit das Hauptprogramm wird nur gestartet, um den Treibercode zu testen. In diesem Fall springt
# das Programm direkt in die Funktion 'main()'. Bei der sp￤teren Verwendung des Treibers wird nur die Klasse 'SMB100A' und deren
# Methoden importiert.
#
if __name__ == '__main__':
    main()
