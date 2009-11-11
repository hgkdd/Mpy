# -*- coding: utf-8 -*-
#
import functools
import re
import sys
import StringIO
from scuq import *
from mpy.device.spectrumanalyzer import SPECTRUMANALYZER as SPECTRUMAN
from mpy.tools.Configuration import fstrcmp

#
#
# Für den Spectrumanalyzer R&S ZVL wird die Klasse 'zlv-6' definiert.
# Diese greift auf die Unterklasse SPECTRUMANALYZER (spectrumanalyzer.py) und darüber auf die Unterklasse DRIVER (driver.py) zu.
#
class SPECTRUMANALYZER(SPECTRUMAN):

    #TRACEMODES=('WRITe', 'VIEW', 'AVERage', 'MAXHold', 'MINHold', 'RMS')
    #DETECTORS=('APEak', 'NEGative', 'POSitive', 'SAMPle', 'RMS', 'AVERage', 'QPEak')
    #TRIGGERMODES=('TIME', 'IMMediate', 'EXTern', 'IFPower', 'VIDeo')
    
    #Map: {Allgemein gültige Bezeichnung:Bezeichnung Gerät} 
    MapTRACEMODES={'WRITE':         'WRITe',
                   'VIEW':          'VIEW',
                   'AVERAGE':       'AVERage',
                   'BLANK':         'OFF',       #Off umsetzen!!!!!  #RMS??
                   'MAXHOLD':       'MAXHold',
                   'MINHOLD':       'MINHold'
                   }
    
    MapDETECTORS={'AUTOSELECT':     'auto',     #auto umsetzen!!!! #Auto richtig?
                  'AUTOPEAK':       'APEak',
                  'MAXPEAK':        'POSitive',
                  'MINPEAK':        'NEGative',
                  'SAMPLE':         'SAMPle',
                  'RMS':            'RMS',
                  'AVERAGE':        'AVERage',
                  'DET_QPEAK':      'QPEak'
                  }
    MapTRIGGERMODES={'FREE':        'IMMediate',
                    'VIDEO':        'VIDeo',
                    'EXTERNAL':     'EXTern'
                    }
    
    
    def __init__(self):
        SPECTRUMAN.__init__(self)
        self.trace=1
        self._internal_unit='dBm'
        

        
        
        #
        # Im Wörterbuch '._cmds' werden die Befehle zum Steuern des speziellen Spektrumanalysator definiert, z.B. SetFreq() zum Setzen
        # der Frequenz. Diese können in der Dokumentation des entsprechenden Spektrumanalysator nachgeschlagen werden.
        # In der Unterklasse SPECTRUMANALYZER wurden bereits Methoden zur Ansteuerung eines allgemeinen Spektrumanalysators definiert,
        # welche die Steuerbefehle aus dem hier definierten '.cmds' Wörterbuch abrufen.
        # Das Wörterbuch enthält für jeden Eintrag ein Schlüsselwort mit dem allgemeinen Befehl als String, z.B. SetFreq(). Diesem
        # Schlüsselwort wird eine Liste zugeordnet, wobei jeder Listeneintrag ein Tupel ist und jeder Tupel einen Befehl und eine Vorlage
        # für die darauffolgende Antwort des Signalgenerators enthaelt.
        #
        self._cmds={'SetCenterFreq':  [("'FREQuency:CENTer %s HZ'%something", None)],
                    'GetCenterFreq':  [('FREQuency:CENTer?', r'(?P<cfreq>%s)'%self._FP)],
                    'SetSpan':  [("'FREQuency:SPAN %s HZ'%something", None)],
                    'GetSpan':  [('FREQuency:SPAN?', r'(?P<span>%s)'%self._FP)],
                    'SetStartFreq':  [("'FREQuency:STARt %s HZ'%something", None)],
                    'GetStartFreq':  [('FREQuency:STARt?', r'(?P<stfreq>%s)'%self._FP)],
                    'SetStopFreq':  [("'FREQuency:STOP %s HZ'%something", None)],
                    'GetStopFreq':  [('FREQuency:STOP?', r'(?P<spfreq>%s)'%self._FP)],
                    'SetRBWAuto':   [("SENSe:BANDwidth:RESolution:Auto On", None)],
                    'SetRBW':  [("'SENSe:BANDwidth:RESolution %s HZ'%something", None)],
                    'GetRBW':  [('SENSe:BANDwidth:RESolution?', r'(?P<rbw>%s)'%self._FP)],
                    #VBW kann nur bestimmt Werte annehmen
                    #The command is not available if FFT filtering is switched on and the set bandwidth is <= 30 kHz or if the quasi–peak detector is switched on.
                    'SetVBWAuto':   [("SENSe:BANDwidth:VIDeo:Auto On", None)],
                    'SetVBW':  [("'SENSe:BANDwidth:VIDeo %s HZ'%something", None)],
                    'GetVBW':  [('SENSe:BANDwidth:VIDeo?', r'(?P<vbw>%s)'%self._FP)],
                    'SetRefLevel':  [("'DISP:WIND:TRAC%s:Y:RLEV %s DBM'%(self.trace,something)", None)],
                    'GetRefLevel':  [("'DISP:WIND:TRAC%s:Y:RLEV?'%self.trace", r'(?P<reflevel>%s)'%self._FP)],
                    'SetAtt':  [("'INPut:ATTenuation %s DB'%something", None)],
                    'GetAtt':  [('INPut:ATTenuation?', r'(?P<att>%s)'%self._FP)],
                    'SetAttAuto':  [("INPut:ATTenuation:AUTO ON", None)],
                    #????Hat das ZVL nicht
                    #'SetAttMode': [("'ATTMode %s'%something", None)],
                    #'GetAttMode':  [('ATTMode?', r'ATTMODE (?P<attmode>.*)')],
                    #SetPreAmp wird nicht über die standart SetGetSomething Funktion zur verfügung gestellt,
                    #sondern es wurde ein spezielle definiert, siehe weiter unten.
                    'SetPreAmp':  [("'INPut:GAIN:STATe %s'%something", None)],
                    'GetPreAmp':  [('INPut:GAIN:STATe?', r'(?P<preamp>%s)'%self._FP)],
                    'SetDetectorAuto':   [("'SENSe:DETector%s:Auto On'%self.trace", None)],
                    'SetDetector':  [("'SENSe:DETector%s %s'%(self.trace,something)", None)],
                    'GetDetector':  [("'SENSe:DETector%s?'%self.trace", r'(?P<det>.*)')],
                    'SetTraceMode':  [("'DISPlay:WINDow:TRACe%s:MODE %s'%(self.trace,something)", None)],
                    'GetTraceMode':  [("'DISPlay:WINDow:TRACe%s:MODE?'%self.trace", r'(?P<tmode>.*)')],
                    #SetTrace wird über eine Funktion realisiert, siehe weiter unten
                    #'SetTrace':  [("'TRACE %d'%trace", None)],
                    #'GetTrace':  [('TRACE?', r'TRACE (?P<trace>\d+)')],
                    'SetSweepCount':  [("'SENSe:SWEep:COUNt %d'%something", None)],
                    'GetSweepCount':  [('SENSe:SWEep:COUNt?', r'(?P<scount>\d+)')],
                    'SetSweepTimeAuto':   [("SENSe:SWEep:TIME:Auto On", None)],
                    'SetSweepTime':  [("'SENSe:SWEep:TIME %s s'%something", None)],
                    'GetSweepTime':  [('SENSe:SWEep:TIME?', r'(?P<stime>%s)'%self._FP)],
                    'GetSpectrum':  [("'TRACe:DATA? TRACE%s'%self.trace", r'(?P<power>([-+]?(\d+(\.\d*)?|\d*\.\d+)([eE][-+]?\d+)?,?)+)')],
                    #Später:
                    #'GetSpectrumNB':  [('DATA?', r'DATA (?P<power>%s)'%self._FP)],
                    'SetTriggerMode': [("'TRIGger:SOURce %s'%something", None)],
                    'GetTriggerMode':  [('TRIGger:SOURce?', r'(?P<trgmode>.*)')],
                    'SetTriggerDelay':  [("'TRIGger:TIME:RINTerval %s s'%something", None)],
                    'GetTriggerDelay':  [('TRIGger:TIME:RINTerval?', r'(?P<tdelay>%s)'%self._FP)],
                    #'SetWindow':  [('WINDOW %d'%window, None)],
                    #'Quit':     [('QUIT', None)],
                    'SetSANMode': [("INSTrument:SELect SAN", None)],
                    'GetDescription': [('*IDN?', r'(?P<IDN>.*)')]}
        
        # Die nachfolgende List stellt im Prinzip eine Tabelle mit drei Spalten dar.
        # In der ersten Spalte steht der Name der Funktion auf welche die entprechende Zeile der Tabelle
        # zutrifft.
        # In der zweiten Spalte stehen mögliche Werte die der Funktion übergeben werden können. Die
        # möglichen Werte können wiederum in Listen gespeichert werden. So ist es mölich einem Befehl
        # mehrer Werte zuzuordnen. Achtung!!! Die Werte werden als reguläre Expression interpretiert!!
        # In der dritten Spalte sind die Befehl vermerkt, welche den möglichen Werten in der vorhergehenden
        # Spalte, zugeordnent werden. 
        complex=[
                 ('SetRBW',
                      [('auto','a'),        ('.+')],
                      ['SetRBWAuto',  'SetRBW']),
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
                 ]
        
        self._cmds['Complex']=complex
          
        setattr(self, "SetTrace", 
                          functools.partial(self._SetTraceIntern))
        setattr(self, "GetTrace", 
                          functools.partial(self._GetTraceIntern))
        setattr(self, "SetPreAmp", 
                          functools.partial(self._SetPreAmpIntern))
        setattr(self, "GetPreAmp", 
                          functools.partial(self._GetPreAmpIntern))


        

    def GetSpectrum(self):
        self.error=0
        dct=self._do_cmds('GetSpectrum', locals())
        self._update(dct)
        if self.error == 0:
            if not dct:
             self.power=0
        else:
             self.power=float(self.power)
        
        self.power=re.split(',', self.power) 
        return self.error, self.power
    
    def SetSANMode(self):
        self.error=0
        dct=self._do_cmds('SetSANMode', locals())
        self._update(dct)
        return self.error,0
    
    def _SetPreAmpIntern(self, something):
        
        #PreAmp kann bei ZVL nur ON oder OFF sein. Also wird on gesetzt sobald ein Abschwächung
        #gestezt wird, egal wie groß. 
        if something == 0:
            something = "OFF"
        else:
            something = "ON"
        
        self.error=0
        dct=self._do_cmds("SetPreAmp", locals())
        self._update(dct)
        dct=self._do_cmds("GetPreAmp", locals())
        self._update(dct)
        if self.error == 0:
            if not dct:
                self.preamp=0
            else:
                self.preamp=float(self.preamp)
        #Die Abfrage nach PreAmp? ergibt nur eins oder Null
        #Wenn eins, dann ist PreAmp auf 20dB gesetzt
        #Wenn Null, dann ist PreAmp Off bzw. auf 0dB gesetzt
        if self.preamp == 1:
            self.preamp=20
        elif self.preamp == 0:
            self.preamp=0
        else:
            self.error=1
        return self.error, self.preamp
    
    def _GetPreAmpIntern(self):
        self.error=0
        dct=self._do_cmds("GetPreAmp", locals())
        self._update(dct)
        if self.error == 0:
            if not dct:
                self.preamp=0
            else:
                self.preamp=float(self.preamp)
        #Die Abfrage nach PreAmp? ergibt nur eins oder Null
        #Wenn eins, dann ist PreAmp auf 20dB gesetzt
        #Wenn Null, dann ist PreAmp Off bzw. auf 0dB gesetzt
        if self.preamp == 1:
            self.preamp=20
        elif self.preamp == 0:
            self.preamp=0
        else:
            self.error=1
        return self.error, self.preamp
    
    def _SetTraceIntern(self,trace):
        self.trace=trace
        return 0, trace
    
    def _GetTraceIntern(self):
        return 0,self.trace
    
    

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
        
        ###Maping
        if possibilities:
            something=fstrcmp(something, getattr(self,possibilities), n=1,cutoff=0,ignorecase=True)[0]
            
            #Ist Map Vorhanden?
            if getattr(self,"Map%s"%possibilities):
                #Wenn Wert zum Key = None, dann Abbruch mit Fehler
                #sonst setzen von something auf Wert in Map           
                if getattr(self,"Map%s"%possibilities)[something] == None:
                    self.error=1
                    return self.error,0
                else:
                    something=getattr(self,"Map%s"%possibilities)[something]
            

        ###Complex abarbeiten
        # Das dict complex wird zeilenweiße ausgelesen und die einzelnen Spalten in die Variablen
        # k, vals und action geschrieben
        for k, vals, actions in self._cmds['Complex']:
            #print k, vals, actions
            
            # Test ob die erste Spalten dem Namen der Funktion (die in setter vermerkt ist) entspricht 
            if k is setter:
                try:
                    # Wenn keine alternativen Werte angegeben wurden, wird 
                    # sofort der setter auf action gesetzt. In setter 
                    # steht der Befehl der entgültig ausgeführt wird.
                    if (vals is None):  
                        setter = actions
                    else:
                        # Die möglichen Werte werden nacheinander druchlaufen.
                        breakfor=False
                        for idx,vi in enumerate(vals):
                            
                            #Prüft ob Werte in einem Tupel gespechert sind
                            if type(vi).__name__=='tuple':
                                # Falls die einzelnen möglichen Werte wiederum in einem Tuple
                                # gespeichert sind, werden hier durchloffen. 
                                for vii in vi:
                                    #Die Einträge werden mit something verglichen.
                                    #In something steht was der Funktion übergeben wurden.
                                    if re.search(vii, str(something), re.I) != None:
                                        setter = actions[idx]
                                        breakfor=True
                            else:
                                #Die Einträge werden mit something verglichen.
                                #In something steht was der Funktion übergeben wurden.
                                if re.search(vi, str(something), re.I) != None:
                                    setter = actions[idx]
                                    breakfor=True
                            
                            if breakfor:
                                break
                                    
                except KeyError:
                    pass
        
        self.error=0
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
        
        
        
        




        

    def Init(self, ini=None, channel=None):
        
        if channel is None:
            channel=1
        self.error=SPECTRUMAN.Init(self, ini, channel)
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
                      'SetSweepTime')]
        
        
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
        
        
        
#
# Die Funktion main() wird nur zum Test des Treibers verwendet!
#
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
                        type:        'SPECTRUMANALYZER'
                        vendor:      'Rohde&Schwarz'
                        serialnr:
                        deviceid:
                        driver:

                        [Init_Value]
                        fstart: 100e6
                        fstop: 6e9
                        fstep: 1
                        gpib: 20
                        virtual: 1

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
                        attmode: 'auto'
                        sweeptime: 10e-3
                        """)
                        # rbw: 3e6
        ini=StringIO.StringIO(ini)
        
    # #
    # # Zum Test des Treibers werden sogenannte Konsistenzabfragen ('assert' Bedingungen) verwendet, welche einen 'AssertationError' liefern,
    # # falls die Bedingung 'false' ist. Zuvor wird eine Testfrequenz und ein Level festgelegt, ein Objekt der Klasse SMB100A erzeugt und der
    # # Signalgenerator initialisiert.
    # #
    #from mpy.device.spectrumanalyzer_ui import UI as UI
    sp=SPECTRUMANALYZER()
    try:
        from mpy.device.spectrumanalyzer_ui import UI as UI
    except ImportError:
        print "test"
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
                 ("SetDetector", "auto", "print"),  #'AUTOSELECT', 'AUTOPEAK', 'MAXPEAK', 'MINPEAK', 'SAMPLE', 'RMS', 'QUASIPEAK'
                 ("SetTraceMode", "WRIT", "print"), #'WRITE','VIEW','AVERAGE', 'BLANK', 'MAXHOLD', 'MINHOLD
                 ("SetSweepCount", 100, "assert"),
                 ("SetSweepTime", "auto", "print"),
                 ("SetTriggerMode", "IMM", "print"), #'FREE', 'VIDEO', 'EXTERNAL' 
                 ("SetTriggerDelay", 0, "print"),
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
    
    err,spectrum=sp.GetRBW
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

