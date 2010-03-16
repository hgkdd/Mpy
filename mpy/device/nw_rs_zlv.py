# -*- coding: utf-8 -*-
#
import functools
import re
import sys
import StringIO
from scuq import *
from mpy.device.networkanalyzer import NETWORKANALYZER as NETWORKAN
from mpy.tools.Configuration import fstrcmp

from numpy import array, linspace, add

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
#    MapTRACEMODES_Back={'WRIT'  :   'WRITE',
#                        'VIEW'  :   'VIEW',
#                        'AVER'  :   'AVERAGE',
#                        'OFF'   :   'BLANK',
#                        'MAXH'  :   'MAXHOLD',
#                        'MINH'  :   'MINHOLD'    
#                        }
    

    
    
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
        self._cmds={ # 'SetCenterFreq':  [("'SENSe%d:FREQuency:CENTer %s HZ'%(self.internChannel,something)", None)],            #Manual S. 499
                   # 'GetCenterFreq':  [('SENSe<Ch>:FREQuency:CENTer?', r'(?P<cfreq>%s)'%self._FP)],        #Manual S. 499
                   # 'SetSpan':  [("'SENSe<Ch>:FREQuency:SPAN %s HZ'%something", None)],                    #Manual S. 500
                   # 'GetSpan':  [('SENSe<Ch>:FREQuency:SPAN?', r'(?P<span>%s)'%self._FP)],                 #Manual S. 500
                   # 'SetStartFreq':  [("'SENSe<Ch>:FREQuency:STARt %s HZ'%something", None)],              #Manual S. 501
                   # 'GetStartFreq':  [('SENSe<Ch>:FREQuency:STARt?', r'(?P<stfreq>%s)'%self._FP)],         #Manual S. 501
                   # 'SetStopFreq':  [("'SENSe<Ch>:FREQuency:STOP %s HZ'%something", None)],                #Manual S. 501
                   # 'GetStopFreq':  [('SENSe<Ch>:FREQuency:STOP?', r'(?P<spfreq>%s)'%self._FP)],           #Manual S. 501
                   # 'SetRBW':  [("'SENSe<Ch>:BANDwidth:RESolution %s HZ'%something", None)],               #Manual S. 473
                   # 'GetRBW':  [('SENSe<Ch>:BANDwidth:RESolution?', r'(?P<rbw>%s)'%self._FP)],             #Manual S. 473
                    ###[SENSe<Ch>:]BANDwidth|BWIDth[:RESolution]:SELect FAST | NORMal???
                    ###
               #    'SetRefLevel':  [("'DISPlay:WINDow<Wnd>:TRACe<WndTr>:Y:SCALe:RLEVel <numeric_value> [,'<trace_name>'] %s DBM'%(self.trace,something)", None)],            #Manual S. 430
           #         'GetRefLevel':  [("'DISP:WIND:TRAC%s:Y:RLEV?'%self.trace", r'(?P<reflevel>%s)'%self._FP)],
           #         'SetAtt':  [("'INPut<port_no>:ATTenuation %s DB'%something", None)],
           #         'GetAtt':  [('INPut<port_no>:ATTenuation?', r'(?P<att>%s)'%self._FP)],

                    
                    
                    
                    
                    #'SetTraceMode':  [("'DISPlay:WINDow:TRACe%s:MODE %s'%(self.trace,something)", None)],  
                    #'GetTraceMode':  [("'DISPlay:WINDow:TRACe%s:MODE?'%self.trace", r'(?P<tmode>.*)')],
                    #'GetTraceModeBlank':  [("'DISPlay:WINDow:TRACe%s:STATe?'%(self.trace)", r'(?P<tmodeblank>\d+)')],
                    'SetTrace':  [("'CALCulate%d:PARameter:SDEFine \\'%s\\', \\'%s\\''%(internChannel,tracename,measParam)", None)],    #Manual S. 384
               #     'GetTrace':  [("'CALCulate<Ch>:PARameter:CATalog?'%internChannel", r'TRACE (?P<trace>.*)')],                                         #Manual S. 381
               #     'DelTrace':  [("'CALCulate<Ch>:PARameter:DELete <Trace Name>'%(internChannel,tracename)")],                                          #Manual S. 382
                    'ShwoTrace': [("'DISPlay:WINDow%d:TRACe%d:FEED \\'%s\\''%(window,windTraceNumber,tracename)",None)],                          #Manual S. 426
                                   
                     
                    'SetChannel': [("'CONFigure:CHANnel%d:STATe ON'%(internChannel)",None)],
               #     'DelChannel': [("'CONFigure:CHANnel<Ch>:STATe OFF'%internChannel";None)],
               #     'GetChannel': [("'CONFigure:CHANnel<Ch>:CATalog?'%internChannel", r'CHANELS (?P<chan>.*')], #Manual S. 415 
                     
                                   
                                   
                    ###Sweep Type Einfügen                                                            #Manual S. 521
                    
                    
               #     'SetSweepCount':  [("'SENSe:SWEep:COUNt %d'%something", None)],
               #     'GetSweepCount':  [('SENSe:SWEep:COUNt?', r'(?P<scount>\d+)')],
               #     'SetSweepTimeAuto':   [("SENSe:SWEep:TIME:Auto On", None)],
               #     'SetSweepTime':  [("'SENSe:SWEep:TIME %s s'%something", None)],
               #     'GetSweepTime':  [('SENSe:SWEep:TIME?', r'(?P<stime>%s)'%self._FP)],
               #     'SetSweepPoints':  [("'SWEep:POINts %s '%something", None)],
               #     'GetSweepPoints':  [('SWEep:POINts?', r'(?P<spoints>\d+)')], 
               #     'GetSpectrum':  [("'TRACe:DATA? TRACE%s'%self.trace", r'(?P<power>([-+]?(\d+(\.\d*)?|\d*\.\d+)([eE][-+]?\d+)?,?)+)')],
                    #Später:
                    #'GetSpectrumNB':  [('DATA?', r'DATA (?P<power>%s)'%self._FP)],
              #      
                    
                    
                    'SetWindow':  [("'DISPlay:WINDow%d:STATe ON'%window", None)],                      #Manual S. 424
              #      'DelWindow':  [("'DISPlay:WINDow<Wnd>:STATe OFF'%window", None)],                     #Manual S. 424
              #      'GetWindow':  [(, r'WINDOW (?P<wind>.*')],
                    
                    
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
        
        

    #Erstellt einne neuen Channel auf dem Gerät
    def _SetChannelIntern(self):
        internChannel = self.internChannel
        self.error=0
        dct=self._do_cmds('SetChannel', locals())
        self._update(dct)
        return self.error,0
        
    
    #Erstellt ein neues Festern, dazu muss die Fensternumer übergeben werden.
    #Die hier übergebenen Nummer ist nur in der aktuellen Instanz güllig.
    #Die eigentliche auf dem Gerät verwendet Nummer wird von der Klasse selbständig ermittelt,
    #und ist über alle Instancen hinweg eindeutig.
    def _SetWindowIntern(self,winNumber):
        win=WINDOW(winNumber,self)
        self.windows.update({winNumber : win})
        #Nummer des Fensters holen, die auf dem Gerät verwendet weden soll.
        window=win.getInternNumber()
        
        self.error=0
        dct=self._do_cmds('SetWindow', locals())
        self._update(dct)
        return self.error,0
        


    #Diese Funktion legt einen neuen Trace auf dem Gerät an
    # *name: Name des Traces, dieser ist nur für die aktuelle Instance gültig. Auf dem Gerät
    #        wird ein Name von der Klasse erstellt, der über alle Instancen hinweg eindeutig ist.
    # *measParam: Als String muss übergeben werde, was gemessen werden soll. z.B. "S11"
    # *winNumber: Her muss die Nummer des Fensters angegeben werden, in dem der Trace dargestellt werden soll.
    #             Das Fenster muss vorher mit SetWindow(self, winNumber) angelegt werden.
    def _SetTraceIntern(self,name,measParam,winNumber):
        
        tra = TRACE(name,self.windows.get(winNumber),measParam,self)
        self.traces.update({name: tra})
        #Nummer des Traces holen die auf dem Gerät verwendet werden soll
        tracename=tra.getInternName()
        windTraceNumber=tra.getTraceWindowNumber()
        #Nummer des Fenster holen, die auf dem Gerät verwendet wird.
        window = self.windows.get(winNumber).getInternNumber()
        internChannel = self.internChannel
        
        self.error=0
        dct=self._do_cmds('SetTrace', locals())
        self._update(dct)
        
        dct=self._do_cmds('ShwoTrace', locals())
        self._update(dct)
        
        return self.error,0
    
    def _GetTraceIntern(self):
        return self.error



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





    #************************************   
    #  Spectrum aus Gerät auslesen
    #************************************
    def GetSpectrum(self):
        self.error=0
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

        xValues = linspace(self.GetStartFreq()[1],self.GetStopFreq()[1],len(self.power))
        #Die einzelnen Werte der Liste werden hier in float Zahlen
        #umgewandelt   
        pow=[]
        for i in self.power:
            pow.append(float(i))

        #xValues als auch y=pow in einem Tuple speichern
        self.power = (tuple(xValues),tuple(pow))
        return self.error, self.power
    
   
    
    
    #******************************************************************************
    #
    #             Abgeänderte standard SetGet Funktionen
    #*******************************************************************************
        
    
        
    
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
        
        print WINDOW.WINDOWS
        
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
    nw.SetTrace("Trc2","S11",1)
    
    nw2.SetWindow(1)
    nw2.SetTrace("Trc2","S11",1)
    nw2.SetTrace("Trc3","S21",1)
    nw2.SetWindow(2)
    nw2.SetTrace("Trc2","S22",2)
    
    
    _assertlist=[]
 
    for funk,value,test in _assertlist:
        err,ret = getattr(nw,funk)(value)
        assert err==0,  '%s() fails with error %d'%(funk,err)
        if value != None:
            if test == "assert":
                assert ret==value, '%s() returns freq=%s instead of %s'%(funk,ret,value)
            else:
                print '%s(): R￼ckgabewert: %s   Sollwert: %s'%(funk,ret,value)
        else:
            print '%s(): R￼ckgabewert: %s'%(funk,ret)


    #err,nwectrum=nw.GetSpectrum()
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
