# -*- coding: utf-8 -*-
#
import sys
import StringIO
from scuq import *
from mpy.device.spectrumanalyzer import SPECTRUMANALYZER as SPECTRUMAN

#
#
# Für den Spectrumanalyzer R&S ZVL wird die Klasse 'zlv-6' definiert.
# Diese greift auf die Unterklasse SPECTRUMANALYZER (spectrumanalyzer.py) und darüber auf die Unterklasse DRIVER (driver.py) zu.
#
class SPECTRUMANALYZER(SPECTRUMANALYZER):
    def __init__(self):
        SPECTRUMAN.__init__(self)
        #???
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
        self._cmds={'SetCenterFreq':  [("'FREQuency:CENTer %s HZ'%cfreq", None)],
                    'GetCenterFreq':  [('FREQuency:CENTer?', r'(?P<cfreq>%s) HZ'%self._FP)],
                    'SetSpan':  [("'FREQuency:SPAN %s HZ'%span", None)],
                    'GetSpan':  [('FREQuency:SPAN?', r'(?P<span>%s) HZ'%self._FP)],
                    'SetStartFreq':  [("'FREQuency:STARt %s HZ'%stfreq", None)],
                    'GetStartFreq':  [('FREQuency:STARt?', r'(?P<stfreq>%s) HZ'%self._FP)],
                    'SetStopFreq':  [("'FREQuency:STOP %s HZ'%spfreq", None)],
                    'GetStopFreq':  [('FREQuency:STOP?', r'(?P<spfreq>%s) HZ'%self._FP)],
                    #??? SetRBW Auto?
                    'SetRBW':  [("'BANDwidth:RESolution %s HZ'%rbw", None)],
                    'GetRBW':  [('BANDwidth:RESolution?', r'(?P<rbw>%s) HZ'%self._FP)],
                    #??? SetVBW Auto?
                    #VBW kann nur bestimmt Werte annehmen
                    #The command is not available if FFT filtering is switched on and the set bandwidth is <= 30 kHz or if the quasi–peak detector is switched on.
                    'SetVBW':  [("'BANDwidth:VIDeo %s HZ'%vbw", None)],
                    'GetVBW':  [('BANDwidth:VIDeo?', r'(?P<vbw>%s) HZ'%self._FP)],
                    'SetRefLevel':  [("'DISP:WIND:TRAC:Y:RLEV %s DBM'%level", None)],
                    'GetRefLevel':  [('DISP:WIND:TRAC:Y:RLEV?', r'(?P<level>%s) DBM'%self._FP)],
                    'SetAtt':  [("'INPut:ATTenuation %s DB'%att", None)],
                    'GetAtt':  [('INPut:ATTenuation?', r'(?P<att>%s) DB'%self._FP)],
                    'SetAttAuto':  [("INPut:ATTenuation:AUTO ON", None)],
                    #??? PreAmp Nur on/off Seite: 663 Manual?
                    #'SetPreAmp':  [("'PREAMP %s DB'%freq", None)],
                    #'GetPreAmp':  [('PREAMP?', r'PREAMP (?P<preamp>%s) DB'%self._FP)],
                    #??? SetDetector Auto?
                    'SetDetector':  [("'SENSe:DETector%s %s'%(self.trace,det)", None)],
                    'GetDetector':  [("'SENSe:DETector%s?'%self.trace", r'(?P<det>.*)')],
                    'SetTraceMode':  [("'DISPlay:WINDow:TRACe%s:MODE %s'%(self.trace,tmode)", None)],
                    'GetTraceMode':  [("'DISPlay:WINDow:TRACe%s:MODE?'%self.trace", r'(?P<tmode>.*)')],
                    #SetTrace wird über eine Funktion realisiert, siehe weiter unten
                    #'SetTrace':  [("'TRACE %d'%trace", None)],
                    #'GetTrace':  [('TRACE?', r'TRACE (?P<trace>\d+)')],
                    'SetSweepCount':  [("'SENSe:SWEep:COUNt %d'%scount", None)],
                    'GetSweepCount':  [('SENSe:SWEep:COUNt?', r'(?P<scount>\d+)')],
                    #??? SetSweepTime Auto?
                    'SetSweepTime':  [("'SENSe:SWEep:TIME %s us'%stime", None)],
                    'GetSweepTime':  [('SENSe:SWEep:TIME?', r'(?P<stime>%s) us'%self._FP)],
                    #??? Was ist mit SweepTime Auto? Als eigene Funktion?
                    'GetSpectrum':  [("'TRACe:DATA? TRACE%s?'%self.trace", r'DATA (?P<power>%s)'%self._FP)],
                    #Später:
                    #'GetSpectrumNB':  [('DATA?', r'DATA (?P<power>%s)'%self._FP)],
                    #???? Trigger Befehle richtig?
                    'SetTriggerMode': [('TRIGger:SOURce %d'%tmode, None)],
                    'SetTriggerDelay':  [('TRIGge:TIME:RINTerval %s us'%tdelay, None)],
                    #'SetWindow':  [('WINDOW %d'%window, None)],
                    #'Quit':     [('QUIT', None)],
                    'GetDescription': [('*IDN?', r'(?P<IDN>.*)')]}
        # 
        #
    def Init(self, ini=None, channel=None):
        
        if channel is None:
            channel=1
        self.error=SGNLGNRTR.Init(self, ini, channel)
        sec='channel_%d'%channel
        try:
            self.levelunit=self.conf[sec]['unit']
        except KeyError:
            self.levelunit=self._internal_unit
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
        presets=[('attenuation',
                      None,
                      ("'INPut:ATTenuation %f'%self.convert.c2c(self.levelunit, self._internal_unit, float(v))", None)),
                 ('reflevel',
                      None,
                      ("'DISP:WIND:TRAC:Y:RLEV %f'%self.convert.c2c(self.levelunit, self._internal_unit, float(v))", None)),
                 ('rbw',
                      None,
                      ("'BANDwidth:RESolution %s HZ'%v", None)),
                 ('vbw',
                      None,
                      ("'BANDwidth:VIDeo %s HZ'%v", None)),
                 ('span',
                      None,
                      ("'FREQuency:SPAN %s HZ'%v", None)),
                 ('trace',
                      None,
                      ("'self.SetTrace(%d)'%v",None)),
                 ('tracemode',
                      None,
                      ("'DISPlay:WINDow:TRACe%s:MODE %s'%(self.trace,v)", None)),
                 ('detector',
                      None,
                      ("'SENSe:DETector%s %s'%(self.trace,v)", None)),
                 ('sweepcount',
                      None,
                      ("'SENSe:SWEep:COUNt %d'%v", None)),
                 ('triggermode',
                      None,
                      ("'TRIGger:SOURce %d'%v", None)),
                 ('attmode',
                      [('0','auto'), ('1','manual')],
                      [('INPut:ATTenuation::AUTO ON', None),('INPut:ATTenuation::AUTO OFF', None)]),
                 ('sweeptime',
                      None,
                      ("'SENSe:SWEep:TIME %s us'%v", None))]
        #
        # Die zur Initialisierung des Signalgenerators notwendigen Schritte werden durch zeilenweise Betrachtung der Liste 'presets'
        # herausgefiltert und in die Befehlsliste (dictionary) 'self._cmds['Preset']' übertragen und stehen damit stehen auch in 'sg._cmds' zur
        # Verfügung.
        # Die Klassenvariable '.conf' (dictionary) wurde in der (Unter-)Klasse DRIVER definert, sie enthält die Daten der ini-Datei.
        # In 'sec' ist gespeicher welcher Channel bearbeitet wird, somit erhält man über '.conf[sec]' zugriff auf die
        # Einstellungen für den aktuellen channel.
        # -> If / else Anweisung zur Behandlung von Initialisierungsschritten ohne Optionen (if) und mit Optionen (else).
        # -> Wurden in 'presets' Optionen angegeben, dann werden diese einzeln durch eine for-Schleife abgerufen.
        #    Durch eine if-Anweiseung wird überprüft, welcher der möglichen Optionen in der ini-Datei angegeben wurden.
        #    Wird eine Übereinstimmung gefunden, wird der Befehl in 'self._cmds['Preset']' übertragen.
        # 
        for k, vals, actions in presets:
            print k, vals, actions
            try:
                v=self.conf[sec][k] 
                if (vals is None):  
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

    def SetTrace(self,trace):
        self.trace=trace
        return 0, trace
    
    def GetTrace(self):
        retrun 0,self.trace
        
        
        
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
                        #??? braucht es die unit?
                        unit: 'dBm'
                        attenuation: 10
                        reflevel: -20
                        rbw: 3e6
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
                        
        ini=StringIO.StringIO(ini)
        
    # #
    # # Zum Test des Treibers werden sogenannte Konsistenzabfragen ('assert' Bedingungen) verwendet, welche einen 'AssertationError' liefern,
    # # falls die Bedingung 'false' ist. Zuvor wird eine Testfrequenz und ein Level festgelegt, ein Objekt der Klasse SMB100A erzeugt und der
    # # Signalgenerator initialisiert.
    # #
    sg=SIGNALGENERATOR()
    try:
        from mpy.device.signalgenerator_ui import UI as UI
    except ImportError:
        pass
    else:
        ui=UI(sg,ini=ini)
        ui.configure_traits()
        sys.exit(0)	
    
    centerFreq=300e6
    span=6e9
    startFreq=6e3
    stopFreq=6e9
    rbw=100e3
    vbw=10e3
    refLevel=-20
    att=10
    preAmp=0
    detector=''
    traceMode=''
    trace=1
    sweepCount=100
    sweepTime=100
    triggerMode=''
    triggerDelay=10
    
    
    err=sg.Init(ini)
    assert err==0, 'Init() fails with error %d'%(err)
    
    err,freq=sg.SetCenterFreq(centerFreq)
    assert err==0, 'SetCenterFreq() fails with error %d'%(err)
    assert freq==centerFreq, 'SetCenterFreq() returns freq=%e instead of %e'%(freq, centerFreq)
    
    err,freq=sg.SetSpan(span)
    assert err==0, 'SetSpan() fails with error %d'%(err)
    assert freq==span, 'SetSpan() returns freq=%e instead of %e'%(freq, span)
    
    err,freq=sg.SetStartFreq(startFreq)
    assert err==0, 'SetStartFreq() fails with error %d'%(err)
    assert freq==startFreq, 'SetStartFreq() returns freq=%e instead of %e'%(freq, startFreq)
    
    err,freq=sg.SetStopFreq(stopFreq)
    assert err==0, 'SetStopFreq() fails with error %d'%(err)
    assert freq==stopFreq, 'SetStopFreq() returns freq=%e instead of %e'%(freq, stopFreq)
    
    err,freq=sg.SetRBW(rbw)
    assert err==0, 'SetRBW() fails with error %d'%(err)
    assert freq==rbw, 'SetRBW() returns freq=%e instead of %e'%(freq, rbw)
    
    err,freq=sg.SetVBW(vbw)
    assert err==0, 'SetVBW() fails with error %d'%(err)
    assert freq==vbw, 'SetVBW() returns freq=%e instead of %e'%(freq, vbw)
    
    err,freq=sg.SetRefLevel(att)
    assert err==0, 'SetRefLevel() fails with error %d'%(err)
    assert freq==att, 'SetRefLevel() returns freq=%e instead of %e'%(freq, att)
    
    err,freq=sg.SetAtt(att)
    assert err==0, 'SetAtt() fails with error %d'%(err)
    assert freq==att, 'SetAtt() returns freq=%e instead of %e'%(freq, att)
    
    err,freq=sg.SetAttAuto()
    assert err==0, 'SetAttAuto() fails with error %d'%(err)
    
    err,freq=sg.SetPreAmp(preAmp)
    assert err==0, 'SetPreAmp() fails with error %d'%(err)
    assert freq==preAmp, 'SetPreAmp() returns freq=%e instead of %e'%(freq, preAmp)
    
    err,freq=sg.SetDetector(detector)
    assert err==0, 'SetDetector() fails with error %d'%(err)
    assert freq==detector, 'SetDetector() returns freq=%e instead of %e'%(freq, detector)
    
    err,freq=sg.SetTraceMode(traceMode)
    assert err==0, 'SetTraceMode() fails with error %d'%(err)
    assert freq==traceMode, 'SetTraceMode() returns freq=%e instead of %e'%(freq, traceMode)
    
    err,freq=sg.SetTrace(trace)
    assert err==0, 'SetTrace() fails with error %d'%(err)
    assert freq==trace, 'SetTrace() returns freq=%e instead of %e'%(freq, trace)
    
    err,freq=sg.SetSweepCount(sweepCount)
    assert err==0, 'SetSweepCount() fails with error %d'%(err)
    assert freq==sweepCount, 'SetSweepCount() returns freq=%e instead of %e'%(freq, sweepCount)
    
    err,freq=sg.SetSweepTime(sweepTime)
    assert err==0, 'SetSweepTime() fails with error %d'%(err)
    assert freq==sweepTime, 'SetSweepTime() returns freq=%e instead of %e'%(freq, sweepTime)
    
    err,spectrum=sg.GetSpectrum()
    assert err==0, 'GetSpectrum() fails with error %d'%(err)
    print spectrum
    
    err,_=sg.SetTriggerMode(triggerMode)
    assert err==0, 'SetTriggerMode() fails with error %d'%(err)
    
    err,_=sg.SetTriggerDelay(triggerDelay)
    assert err==0, 'SetTriggerDelay() fails with error %d'%(err)
    
    
    #err=sg.Quit()
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

