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

    #TRACEMODES=('WRITe', 'VIEW', 'AVERage', 'MAXHold', 'MINHold', 'RMS')
    #DETECTORS=('APEak', 'NEGative', 'POSitive', 'SAMPle', 'RMS', 'AVERage', 'QPEak')
    #TRIGGERMODES=('TIME', 'IMMediate', 'EXTern', 'IFPower', 'VIDeo')
    
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
        self.trace=1
        self._internal_unit='dBm'

        #
        # Im Wörterbuch '._cmds' werden die Befehle zum Steuern des speziellen Spektrumanalysator definiert, z.B. SetFreq() zum Setzen
        # der Frequenz. Diese können in der Dokumentation des entsprechenden Spektrumanalysator nachgeschlagen werden.
        # In der Unterklasse NETWORKANALYZER wurden bereits Methoden zur Ansteuerung eines allgemeinen Spektrumanalysators definiert,
        # welche die Steuerbefehle aus dem hier definierten '.cmds' Wörterbuch abrufen.
        # Das Wörterbuch enthält für jeden Eintrag ein Schlüsselwort mit dem allgemeinen Befehl als String, z.B. SetFreq(). Diesem
        # Schlüsselwort wird eine Liste zugeordnet, wobei jeder Listeneintrag ein Tupel ist und jeder Tupel einen Befehl und eine Vorlage
        # für die darauffolgende Antwort des Signalgenerators enthaelt.
        #
        self._cmds={'SetCenterFreq':  [("'SENSe%d:FREQuency:CENTer %s HZ'%(self.internChannel,something)", None)],            #Manual S. 499
                    'GetCenterFreq':  [('SENSe<Ch>:FREQuency:CENTer?', r'(?P<cfreq>%s)'%self._FP)],        #Manual S. 499
                    'SetSpan':  [("'SENSe<Ch>:FREQuency:SPAN %s HZ'%something", None)],                    #Manual S. 500
                    'GetSpan':  [('SENSe<Ch>:FREQuency:SPAN?', r'(?P<span>%s)'%self._FP)],                 #Manual S. 500
                    'SetStartFreq':  [("'SENSe<Ch>:FREQuency:STARt %s HZ'%something", None)],              #Manual S. 501
                    'GetStartFreq':  [('SENSe<Ch>:FREQuency:STARt?', r'(?P<stfreq>%s)'%self._FP)],         #Manual S. 501
                    'SetStopFreq':  [("'SENSe<Ch>:FREQuency:STOP %s HZ'%something", None)],                #Manual S. 501
                    'GetStopFreq':  [('SENSe<Ch>:FREQuency:STOP?', r'(?P<spfreq>%s)'%self._FP)],           #Manual S. 501
                    'SetRBW':  [("'SENSe<Ch>:BANDwidth:RESolution %s HZ'%something", None)],               #Manual S. 473
                    'GetRBW':  [('SENSe<Ch>:BANDwidth:RESolution?', r'(?P<rbw>%s)'%self._FP)],             #Manual S. 473
                    ###[SENSe<Ch>:]BANDwidth|BWIDth[:RESolution]:SELect FAST | NORMal???
                    ###
                    ###VBW Hat das Gerät nicht, haben es andere???
                    'SetRefLevel':  [("'DISPlay:WINDow<Wnd>:TRACe<WndTr>:Y:SCALe:RLEVel <numeric_value> [,'<trace_name>'] %s DBM'%(self.trace,something)", None)],            #Manual S. 430
                    'GetRefLevel':  [("'DISP:WIND:TRAC%s:Y:RLEV?'%self.trace", r'(?P<reflevel>%s)'%self._FP)],
                    'SetAtt':  [("'INPut<port_no>:ATTenuation %s DB'%something", None)],
                    'GetAtt':  [('INPut<port_no>:ATTenuation?', r'(?P<att>%s)'%self._FP)],
                    ###AttMode Hat das Gerät nicht, haben es andere???
                    #SetAttMode wird nicht über die standart SetGetSomething Funktion realisiert, siehe weiter unten
                    #'SetAttMode': [("'ATTMode %s'%something", None)],
                    #'GetAttMode':  [('ATTMode?', r'ATTMODE (?P<attmode>.*)')],
                    #SetPreAmp wird nicht über die standart SetGetSomething Funktion zur verfügung gestellt,
                    #sondern es wurde ein spezielle definiert, siehe weiter unten.
                    ###SetPreAmp hat das Gerät nicht, haben es andere???
                    #'SetPreAmp':  [("'INPut:GAIN:STATe %s'%something", None)],
                    #'GetPreAmp':  [('INPut:GAIN:STATe?', r'(?P<preamp>%s)'%self._FP)],
                    ###SetDetector hat das Gerät nicht, haben es andere???
                    #'SetDetectorAuto':   [("'SENSe:DETector%s:Auto On'%self.trace", None)],
                    #'SetDetector':  [("'SENSe:DETector%s %s'%(self.trace,something)", None)],
                    #'GetDetector':  [("'SENSe:DETector%s?'%self.trace", r'(?P<det>.*)')],
                    
                    
                    
                    
                    #'SetTraceMode':  [("'DISPlay:WINDow:TRACe%s:MODE %s'%(self.trace,something)", None)],  
                    #'GetTraceMode':  [("'DISPlay:WINDow:TRACe%s:MODE?'%self.trace", r'(?P<tmode>.*)')],
                    #'GetTraceModeBlank':  [("'DISPlay:WINDow:TRACe%s:STATe?'%(self.trace)", r'(?P<tmodeblank>\d+)')],
                    'SetTrace':  [("'CALCulate<Ch>:PARameter:SDEFine '<Trace Name>','< Meas Parameter>'%(tracename,measParam)", None)],
                    #'GetTrace':  [('TRACE?', r'TRACE (?P<trace>\d+)')],
                    'DelTrace':  [('CALCulate<Ch>:PARameter:DELete <Trace Name>')],
                    'ShwoTrace': [("'DISPlay:WINDow<Wnd>:TRACe<WndTr>:FEED '<Trace Name>''")],
                                   
                     
                    'SetChannel': [('CONFigure:CHANnel<Ch>:STATe ON')],
                    'DelChannel': [('CONFigure:CHANnel<Ch>:STATe OFF')],
                     
                                   
                                   
                    ###Sweep Type Einfügen                                                            #Manual S. 521
                    'SetSweepCount':  [("'SENSe:SWEep:COUNt %d'%something", None)],
                    'GetSweepCount':  [('SENSe:SWEep:COUNt?', r'(?P<scount>\d+)')],
                    'SetSweepTimeAuto':   [("SENSe:SWEep:TIME:Auto On", None)],
                    'SetSweepTime':  [("'SENSe:SWEep:TIME %s s'%something", None)],
                    'GetSweepTime':  [('SENSe:SWEep:TIME?', r'(?P<stime>%s)'%self._FP)],
                    'SetSweepPoints':  [("'SWEep:POINts %s '%something", None)],
                    'GetSweepPoints':  [('SWEep:POINts?', r'(?P<spoints>\d+)')], 
                    'GetSpectrum':  [("'TRACe:DATA? TRACE%s'%self.trace", r'(?P<power>([-+]?(\d+(\.\d*)?|\d*\.\d+)([eE][-+]?\d+)?,?)+)')],
                    #Später:
                    #'GetSpectrumNB':  [('DATA?', r'DATA (?P<power>%s)'%self._FP)],
                    'SetTriggerMode': [("'TRIGger:SOURce %s'%something", None)],
                    'GetTriggerMode':  [('TRIGger:SOURce?', r'(?P<trgmode>.*)')],
                    'SetTriggerDelay':  [("'TRIGger:TIME:RINTerval %s s'%something", None)],
                    'GetTriggerDelay':  [('TRIGger:TIME:RINTerval?', r'(?P<tdelay>%s)'%self._FP)],
                    
                    
                    'SetWindow':  [('DISPlay:WINDow<Wnd>:STATe ON'%window, None)],
                    'DelWindow':  [('DISPlay:WINDow<Wnd>:STATe OFF'%window, None)],
                    
                    
                    
                    #'Quit':     [('QUIT', None)],
                    'SetSANMode': [("INSTrument:SELect NWA", None)],
                    'GetDescription': [('*IDN?', r'(?P<IDN>.*)')]}
        
        # Die nachfolgende List stellt im Prinzip eine Tabelle mit drei Spalten dar.
        # In der ersten Spalte steht der Name der Funktion auf welche die entprechende Zeile der Tabelle
        # zutrifft.
        # In der zweiten Spalte stehen mögliche Werte die der Funktion übergeben werden können. Die
        # möglichen Werte können wiederum in Listen gespeichert werden. So ist es mölich einem Befehl
        # mehrer Werte zuzuordnen. Achtung!!! Die Werte werden als reguläre Expression interpretiert!!
        # In der dritten Spalte sind die Befehle vermerkt, welche den möglichen Werten in der vorhergehenden
        # Spalte, zugeordnent werden. 
        complex=[
                 ('SetVBW',
                      ['auto',        '.+'],
                      ['SetVBWAuto',  'SetVBW']),
                 ('SetAtt',
                      ['auto',        '.+'],
                      ['SetAttAuto',  'SetAtt']),
                 ('SetDetector',
                      [('auto','AUTOSELECT'),        '.+'],
                      ['SetDetectorAuto',  'SetDetector']),
                 ('SetSweepTime',
                      ['auto',        '.+'],
                      ['SetSweepTimeAuto',  'SetSweepTime']),
                 ('SetTraceMode',
                      [('off','BLANK'),        '.+'],
                      ['SetTraceModeBlank',  'SetTraceMode'])
                 ]
        
        
        # Dieser Teil ist nötig, weil die meisten Funktionen erst durch setattr in der init der
        # Main Klasse erstellt werden. Um die so erstellten Funktionen wieder zu überlagern,
        # muss sie durch setattr wieder überschreiben lassen:
        self._cmds['Complex']=complex
          
        setattr(self, "SetTrace", 
                          functools.partial(self._SetTraceIntern))
        setattr(self, "GetTrace", 
                          functools.partial(self._GetTraceIntern))
        
        

    #******************************************************************************
    #
    #             Verwaltungs Funktionen
    #*******************************************************************************


    def getChannelNumber(self):
        return self.internChannel


    def __gethighestChannelNumber(self):
        numb=0
        for nw in NETWORKANALYZERS:
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
        

    #Gerät hat keine Funktion um auszwählen, welcher Trace bearbeitet werden soll.
    #Statt dessen wird die entsprechende Trace Nummer mit den Befehlen übergeben,
    #um das zu ermöglichen die Trace Nummer in einer Variable gespeichert.
    def _SetTraceIntern(self,trace):
        self.trace=trace
        return 0, trace
    
    def _GetTraceIntern(self):
        return 0,self.trace
    
        
    
    #Diese Funktion schlaten das ZVL in den Spectrum Analyzer Mode
    def SetSANMode(self):
        self.error=0
        dct=self._do_cmds('SetSANMode', locals())
        self._update(dct)
        return self.error,0
    


    #***************************************************************************
    #
    #       Die Init Funktion initialisiert das Gerät, sie muss als erstes aufgerufen werden
    #***************************************************************************
    def Init(self, ini=None, channel=None):
        NETWORKANALYZERS.append(self)
        self.internChannel=-1
        self.internChannel=__gethighestChannelNumber()
        
        
        
        if channel is None:
            channel=1
        self.error=NETWORKAN.Init(self, ini, channel)
        sec='channel_%d'%channel
        try:
            self.levelunit=self.conf[sec]['unit']
        except KeyError:
            self.levelunit=self._internal_unit
        
        #Schaltet das ZVL in in den SAN - Spectrum analyzer Mode
        self.SetSANMode()
        
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
        presets=[('trace',
                      None,
                      'SetTrace'),
                 ('attenuation',
                      None,
                      'SetAtt'),
                 ('reflevel',
                      None,
                      'SetRefLevel'),
                 ('rbw',
                      None,
                      'SetRBW'),
                 ('vbw',
                      None,
                      'SetVBW'),
                 ('span',
                      None,
                      'SetSpan'),
                 ('tracemode',
                      None,
                      'SetTraceMode'),
                 ('detector',
                      None,
                      'SetDetector'),
                 ('sweepcount',
                      None,
                      'SetSweepCount'),
                 ('triggermode',
                      None,
                      'SetTriggerMode'),
                 #('attmode', ###??????
                 #     [('0','auto'), ('1','manual')],
                 #     [('INPut:ATTenuation::AUTO ON', None),('INPut:ATTenuation::AUTO OFF', None)]),
                 ('sweeptime',
                      None,
                      'SetSweepTime'),
                 ('sweeppoints',
                      None,
                      'SetSweepPoints')]
        
        
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
        
        
##########################################################################       
#
# Die Funktion main() wird nur zum Test des Treibers verwendet!
###########################################################################
def main():
    from mpy.tools.util import format_block
    #from mpy.device.signalgenerator_ui import UI as UI
    #
    # Wird für den Test des Treibers keine ini-Datei über die Kommnadoweile eingegebnen, dann muss eine virtuelle Standard-ini-Datei erzeugt
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
        
    # #
    # # Zum Test des Treibers werden sogenannte Konsistenzabfragen ('assert' Bedingungen) verwendet, welche einen 'AssertationError' liefern,
    # # falls die Bedingung 'false' ist. Zuvor wird eine Testfrequenz und ein Level festgelegt, ein Objekt der Klasse SMB100A erzeugt und der
    # # Signalgenerator initialisiert.
    # #
    #from mpy.device.networkanalyzer_ui import UI as UI
    sp=NETWORKANALYZER()
    try:
        from mpy.device.networkanalyzer_ui import UI as UI
    except ImportError:
        pass
    else:
        ui=UI(sp,ini=ini)
        ui.configure_traits()
        sys.exit(0)	
    
    err=sp.Init(ini)
    assert err==0, 'Init() fails with error %d'%(err)
    
    _assertlist=[("SetTrace", 1, "assert"),
                 ("SetCenterFreq", 200e6,"assert"),
                 ("SetSpan", 6e9, "assert"),
                 ("SetStartFreq", 6e3, "assert"),
                 ("SetStopFreq", 6e9, "assert"),
                 ("SetRBW", "auto", "print"), #200e3
                 ("SetVBW", "auto", "print"), #10e3
                 ("SetRefLevel", -20, "assert"), 
                 ("SetAtt", "auto", "print"), #20 
                 ("SetPreAmp", 0, "assert"),
                 ("SetDetector", "AUTOSELECT", "print"),  #'AUTOSELECT', 'AUTOPEAK', 'MAXPEAK', 'MINPEAK', 'SAMPLE', 'RMS', 'QUASIPEAK'
                 ("SetTraceMode", "WRITE", "print"), #'WRITE','VIEW','AVERAGE', 'BLANK', 'MAXHOLD', 'MINHOLD
                 ("SetSweepCount", 100, "assert"),
                 ("SetSweepTime", "auto", "print"),
                 ("SetTriggerMode", "VIDEO", "print"), #'FREE', 'VIDEO', 'EXTERNAL' 
                 ("SetTriggerDelay", 0, "print"),
                 ("SetSweepPoints", 500, "assert")
                 ]
 
    for funk,value,test in _assertlist:
        err,ret = getattr(sp,funk)(value)
        assert err==0,  '%s() fails with error %d'%(funk,err)
        if value != None:
            if test == "assert":
                assert ret==value, '%s() returns freq=%s instead of %s'%(funk,ret,value)
            else:
                print '%s(): Rückgabewert: %s   Sollwert: %s'%(funk,ret,value)
        else:
            print '%s(): Rückgabewert: %s'%(funk,ret)

    err,spectrum=sp.GetSpectrum()
    assert err==0, 'GetSpectrum() fails with error %d'%(err)
    print spectrum
    
    #err=sp.Quit()
    #assert err==0, 'Quit() fails with error %d'%(err)
#
#      
#  ------------ Hauptprogramm ---------------------------
#
# Die Treiberdatei selbst und damit das Hauptprogramm wird nur gestartet, um den Treibercode zu testen. In diesem Fall springt
# das Programm direkt in die Funktion 'main()'. Bei der späteren Verwendung des Treibers wird nur die Klasse 'SMB100A' und deren
# Methoden importiert.
#
if __name__ == '__main__':
    main()
    
    
    
    
class TRACE(Objekt):
    
    TRACES=[]
    
    def __init__(self,name,win,measParam,nw):
        TRACES.append(self)
        self.name=name
        self.window=win
        self.networkanalyzer=nw
        self.measParameter = measParam
        self.traceWindowNumber=-1
        self.traceWindowNumber=__gethighestTraceWindowNumber()
        self.internName='%s_Ch%dWIN%dTR%d'%(name,self.networkanalyzer.getChannelNumber(),self.window.getInternNumber(),self.traceWindowNumber)
    
    def __gethighestTraceWindowNumber(self):
        numb=0
        for trace in TRACES:
            if (trace.getTraceWindowNumber() >= numb):
                numb = trace.getTraceWindowNumber()+1
        return numb
            
    def getTraceWindowNumber(self):
        return self.windowNumber
    
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
    
    
class WINDOW(Objekt):
    
    WINDOWS=[]
    
    def __init__(self,number,nw):
        WINDOWS.append(self)
        self.networkanalyzer=nw
        self.number=number
        self.internNumber=-1
        self.internNumber=__gethighestWindowNumber()
        
    def __gethighestWindowNumber(self):
        numb=0
        for win in WINDOWS:
            if (win.getInternNumber() >= numb):
                numb = win.getInternNumber()+1
        return numb
        
    def getInternNumber(self):
        return self.internNumber
    
    def getNumber(self):
        return self.number
    
    def getNetworkanalyzer(self):
        return self.networkanalyzer
