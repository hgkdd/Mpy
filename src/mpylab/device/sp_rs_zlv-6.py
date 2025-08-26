# -*- coding: utf-8 -*-
#
import functools
import io
import re
import sys

from numpy import linspace

from mpylab.device.spectrumanalyzer import SPECTRUMANALYZER as SPECTRUMAN


#
#
# Für den Spectrumanalyzer R&S ZVL wird die Klasse 'zlv-6' definiert.
# Diese greift auf die Unterklasse SPECTRUMANALYZER (spectrumanalyzer.py) und darüber auf die Unterklasse DRIVER (driver.py) zu.
#
class SPECTRUMANALYZER(SPECTRUMAN):

    # *************************************************************************
    #
    #                    Init
    # *************************************************************************
    def __init__(self):

        # Map: {Allgemein gültige Bezeichnung : Bezeichnung Gerät}
        self.MapTRACEMODES = {'WRITE': 'WRITe',
                              'VIEW': 'VIEW',
                              'AVERAGE': 'AVERage',
                              'BLANK': 'OFF',  # Off umsetzen!!!!!  #RMS??
                              'MAXHOLD': 'MAXHold',
                              'MINHOLD': 'MINHold'
                              }

        self.MapDETECTORS = {'AUTOSELECT': 'auto',  # auto umsetzen!!!! #Auto richtig?
                             'AUTOPEAK': 'APEak',
                             'MAXPEAK': 'POSitive',
                             'MINPEAK': 'NEGative',
                             'SAMPLE': 'SAMPle',
                             'RMS': 'RMS',
                             'AVERAGE': 'AVERage',
                             'DET_QPEAK': 'QPEak'
                             }

        self.MapTRIGGERMODES = {'FREE': 'IMMediate',
                                'VIDEO': 'VID',
                                'EXTERNAL': 'EXT'
                                }

        # Back Map: {RückgabeWert von Gerät : Allgemein gültige Bezeichnung}
        self.MapTRACEMODES_Back = {'WRIT': 'WRITE',
                                   'VIEW': 'VIEW',
                                   'AVER': 'AVERAGE',
                                   'OFF': 'BLANK',
                                   'MAXH': 'MAXHOLD',
                                   'MINH': 'MINHOLD'
                                   }

        self.MapDETECTORS_Back = {'auto': 'AUTOSELECT',  # auto umsetzen!!!! #Auto richtig?
                                  'APE': 'AUTOPEAK',
                                  'POS': 'MAXPEAK',
                                  'NEG': 'MINPEAK',
                                  'SAMP': 'SAMPLE',
                                  'RMS': 'RMS',
                                  'AVER': 'AVERAGE',
                                  'QPE': 'DET_QPEAK'
                                  }

        self.MapTRIGGERMODES_Back = {'IMM': 'FREE',
                                     'VID': 'VIDEO',
                                     'EXT': 'EXTERNAL'
                                     }

        SPECTRUMAN.__init__(self)
        self.trace = 1
        self._internal_unit = 'dBm'

        #
        # Im Wörterbuch '._cmds' werden die Befehle zum Steuern des speziellen Spektrumanalysator definiert, z.B. SetFreq() zum Setzen
        # der Frequenz. Diese können in der Dokumentation des entsprechenden Spektrumanalysator nachgeschlagen werden.
        # In der Unterklasse SPECTRUMANALYZER wurden bereits Methoden zur Ansteuerung eines allgemeinen Spektrumanalysators definiert,
        # welche die Steuerbefehle aus dem hier definierten '.cmds' Wörterbuch abrufen.
        # Das Wörterbuch enthält für jeden Eintrag ein Schlüsselwort mit dem allgemeinen Befehl als String, z.B. SetFreq(). Diesem
        # Schlüsselwort wird eine Liste zugeordnet, wobei jeder Listeneintrag ein Tupel ist und jeder Tupel einen Befehl und eine Vorlage
        # für die darauffolgende Antwort des Signalgenerators enthaelt.
        #
        self._cmds = {'SetCenterFreq': [("'FREQuency:CENTer %s HZ'%something", None)],
                      'GetCenterFreq': [('FREQuency:CENTer?', r'(?P<cfreq>%s)' % self._FP)],
                      'SetSpan': [("'FREQuency:SPAN %s HZ'%something", None)],
                      'GetSpan': [('FREQuency:SPAN?', r'(?P<span>%s)' % self._FP)],
                      'SetStartFreq': [("'FREQuency:STARt %s HZ'%something", None)],
                      'GetStartFreq': [('FREQuency:STARt?', r'(?P<stfreq>%s)' % self._FP)],
                      'SetStopFreq': [("'FREQuency:STOP %s HZ'%something", None)],
                      'GetStopFreq': [('FREQuency:STOP?', r'(?P<spfreq>%s)' % self._FP)],
                      'SetRBWAuto': [("SENSe:BANDwidth:RESolution:Auto On", None)],
                      'SetRBW': [("'SENSe:BANDwidth:RESolution %s HZ'%something", None)],
                      'GetRBW': [('SENSe:BANDwidth:RESolution?', r'(?P<rbw>%s)' % self._FP)],
                      # VBW kann nur bestimmt Werte annehmen
                      # The command is not available if FFT filtering is switched on and the set bandwidth is <= 30 kHz or if the quasi–peak detector is switched on.
                      'SetVBWAuto': [("SENSe:BANDwidth:VIDeo:Auto On", None)],
                      'SetVBW': [("'SENSe:BANDwidth:VIDeo %s HZ'%something", None)],
                      'GetVBW': [('SENSe:BANDwidth:VIDeo?', r'(?P<vbw>%s)' % self._FP)],
                      'SetRefLevel': [("'DISP:WIND:TRAC%s:Y:RLEV %s DBM'%(self.trace,something)", None)],
                      'GetRefLevel': [("'DISP:WIND:TRAC%s:Y:RLEV?'%self.trace", r'(?P<reflevel>%s)' % self._FP)],
                      'SetAtt': [("'INPut:ATTenuation %s DB'%something", None)],
                      'GetAtt': [('INPut:ATTenuation?', r'(?P<att>%s)' % self._FP)],
                      'SetAttAuto': [("INPut:ATTenuation:AUTO ON", None)],
                      # SetAttMode wird nicht über die standart SetGetSomething Funktion realisiert, siehe weiter unten
                      # 'SetAttMode': [("'ATTMode %s'%something", None)],
                      # 'GetAttMode':  [('ATTMode?', r'ATTMODE (?P<attmode>.*)')],
                      # SetPreAmp wird nicht über die standart SetGetSomething Funktion zur verfügung gestellt,
                      # sondern es wurde ein spezielle definiert, siehe weiter unten.
                      'SetPreAmp': [("'INPut:GAIN:STATe %s'%something", None)],
                      'GetPreAmp': [('INPut:GAIN:STATe?', r'(?P<preamp>%s)' % self._FP)],
                      'SetDetectorAuto': [("'SENSe:DETector%s:Auto On'%self.trace", None)],
                      'SetDetector': [("'SENSe:DETector%s %s'%(self.trace,something)", None)],
                      'GetDetector': [("'SENSe:DETector%s?'%self.trace", r'(?P<det>.*)')],
                      'SetTraceMode': [("'DISPlay:WINDow:TRACe%s:MODE %s'%(self.trace,something)", None)],
                      'SetTraceModeBlank': [("'DISPlay:WINDow:TRACe%s:STATe OFF'%(self.trace)", None)],
                      # GetTraceMode wird über dei standart SetGetSomething Funktion realisiert, siehe weiter unten
                      'GetTraceMode': [("'DISPlay:WINDow:TRACe%s:MODE?'%self.trace", r'(?P<tmode>.*)')],
                      'GetTraceModeBlank': [("'DISPlay:WINDow:TRACe%s:STATe?'%(self.trace)", r'(?P<tmodeblank>\d+)')],
                      # SetTrace wird über dei standart SetGetSomething Funktion realisiert, siehe weiter unten
                      # 'SetTrace':  [("'TRACE %d'%trace", None)],
                      # 'GetTrace':  [('TRACE?', r'TRACE (?P<trace>\d+)')],
                      'SetSweepCount': [("'SENSe:SWEep:COUNt %d'%something", None)],
                      'GetSweepCount': [('SENSe:SWEep:COUNt?', r'(?P<scount>\d+)')],
                      'SetSweepTimeAuto': [("SENSe:SWEep:TIME:Auto On", None)],
                      'SetSweepTime': [("'SENSe:SWEep:TIME %s s'%something", None)],
                      'GetSweepTime': [('SENSe:SWEep:TIME?', r'(?P<stime>%s)' % self._FP)],
                      'SetSweepPoints': [("'SWEep:POINts %s '%something", None)],
                      'GetSweepPoints': [('SWEep:POINts?', r'(?P<spoints>\d+)')],
                      'GetSpectrum': [("'TRACe:DATA? TRACE%s'%self.trace",
                                       r'(?P<power>([-+]?(\d+(\.\d*)?|\d*\.\d+)([eE][-+]?\d+)?,?)+)')],
                      # Später:
                      # 'GetSpectrumNB':  [('DATA?', r'DATA (?P<power>%s)'%self._FP)],
                      'SetTriggerMode': [("'TRIGger:SOURce %s'%something", None)],
                      'GetTriggerMode': [('TRIGger:SOURce?', r'(?P<trgmode>.*)')],
                      'SetTriggerDelay': [("'TRIGger:TIME:RINTerval %s s'%something", None)],
                      'GetTriggerDelay': [('TRIGger:TIME:RINTerval?', r'(?P<tdelay>%s)' % self._FP)],
                      # 'SetWindow':  [('WINDOW %d'%window, None)],
                      # 'Quit':     [('QUIT', None)],
                      'SetSANMode': [("INSTrument:SELect SAN", None)],
                      'GetDescription': [('*IDN?', r'(?P<IDN>.*)')]}

        # Die nachfolgende List stellt im Prinzip eine Tabelle mit drei Spalten dar.
        # In der ersten Spalte steht der Name der Funktion auf welche die entprechende Zeile der Tabelle
        # zutrifft.
        # In der zweiten Spalte stehen mögliche Werte die der Funktion übergeben werden können. Die
        # möglichen Werte können wiederum in Listen gespeichert werden. So ist es mölich einem Befehl
        # mehrer Werte zuzuordnen. Achtung!!! Die Werte werden als reguläre Expression interpretiert!!
        # In der dritten Spalte sind die Befehle vermerkt, welche den möglichen Werten in der vorhergehenden
        # Spalte, zugeordnent werden. 
        complex = [
            ('SetRBW',
             [('auto', 'a'), ('.+')],
             ['SetRBWAuto', 'SetRBW']),
            ('SetVBW',
             ['auto', '.+'],
             ['SetVBWAuto', 'SetVBW']),
            ('SetAtt',
             ['auto', '.+'],
             ['SetAttAuto', 'SetAtt']),
            ('SetDetector',
             [('auto', 'AUTOSELECT'), '.+'],
             ['SetDetectorAuto', 'SetDetector']),
            ('SetSweepTime',
             ['auto', '.+'],
             ['SetSweepTimeAuto', 'SetSweepTime']),
            ('SetTraceMode',
             [('off', 'BLANK'), '.+'],
             ['SetTraceModeBlank', 'SetTraceMode'])
        ]

        # Dieser Teil ist nötig, weil die meisten Funktionen erst durch setattr in der init der
        # Main Klasse erstellt werden. Um die so erstellten Funktionen wieder zu überlagern,
        # muss sie durch setattr wieder überschreiben lassen:
        self._cmds['Complex'] = complex

        setattr(self, "SetAttMode",
                functools.partial(self._SetAttModeIntern))
        setattr(self, "GetAttMode",
                functools.partial(self._GetAttModeIntern))
        setattr(self, "SetTrace",
                functools.partial(self._SetTraceIntern))
        setattr(self, "GetTrace",
                functools.partial(self._GetTraceIntern))
        setattr(self, "SetPreAmp",
                functools.partial(self._SetPreAmpIntern))
        setattr(self, "GetPreAmp",
                functools.partial(self._GetPreAmpIntern))

        self.GetTraceModeSuper = self.GetTraceMode
        setattr(self, "GetTraceMode",
                functools.partial(self._GetTraceModeIntern))
        self.SetTraceModeSuper = self.SetTraceMode
        setattr(self, "SetTraceMode",
                functools.partial(self._SetTraceModeIntern))

    # ************************************
    #  Spectrum aus Gerät auslesen
    # ************************************
    def GetSpectrum(self):
        self.error = 0
        dct = self._do_cmds('GetSpectrum', locals())
        self._update(dct)
        if self.error == 0:
            if not dct:
                self.power = 0
        else:
            self.power = float(self.power)

        # Spectrum wird als ein String vom Gerät übertragen.
        # Werte sind durch Komma getrennt, und werden mit Hilfe von
        # split in eine liste umgewandelt.
        self.power = re.split(',', self.power)

        xValues = linspace(self.GetStartFreq()[1], self.GetStopFreq()[1], len(self.power))
        # Die einzelnen Werte der Liste werden hier in float Zahlen
        # umgewandelt
        pow = []
        for i in self.power:
            pow.append(float(i))

        # xValues als auch y=pow in einem Tuple speichern
        self.power = (tuple(xValues), tuple(pow))
        return self.error, self.power

    # ******************************************************************************
    #
    #             Abgeänderte standard SetGet Funktionen
    # *******************************************************************************

    # Blank, also Trace aus, wird nicht druch den Standard TraceMode Befehl
    # realisiert, deshalb muss erst geprüfft werden, ob der Trace aus ist -
    # GetTraceModeBlank liefert 0 zurück. Ist er aus lieft die Funktion Blank
    # zurück, anderfalls wird die uhrsprüngliche GetTraceMode Funktion aufgerufen und deren
    # Ergebniss zurückgegeben.
    def _GetTraceModeIntern(self):
        dct = self._do_cmds('GetTraceModeBlank', locals())
        self._update(dct)
        if int(self.tmodeblank) == 0:
            return self.error, 'BLANK'
        else:
            return self.GetTraceModeSuper()

    # Blank, also Trace aus, wird nicht druch den Standard TraceMode Befehl
    # realisiert. Nach der ersten zeile entspricht die Funktion _GetTraceModeIntern(self) siehe dort.
    # Die erste Zeile ruft den uhrsprünglichen SetTraceMode Befehl auf, ob jetzt der Set-Befehl
    # für Blank oder der standard Set-Befehl ausgeführt werden soll, wird über die complex-Liste geregelt.
    def _SetTraceModeIntern(self, something):
        err, ret = self.SetTraceModeSuper(something)
        dct = self._do_cmds('GetTraceModeBlank', locals())
        self._update(dct)
        if int(self.tmodeblank) == 0:
            return err, 'BLANK'
        else:
            return err, ret

    def _SetPreAmpIntern(self, something):

        # PreAmp kann bei ZVL nur ON oder OFF sein. Also wird on gesetzt sobald ein Abschwächung
        # gestezt wird, egal wie groß.
        if something == 0:
            something = "OFF"
        else:
            something = "ON"

        self.error = 0
        dct = self._do_cmds("SetPreAmp", locals())
        self._update(dct)
        dct = self._do_cmds("GetPreAmp", locals())
        self._update(dct)
        if self.error == 0:
            if not dct:
                self.preamp = 0
            else:
                self.preamp = float(self.preamp)
        # Die Abfrage nach PreAmp? ergibt nur eins oder Null
        # Wenn eins, dann ist PreAmp auf 20dB gesetzt
        # Wenn Null, dann ist PreAmp Off bzw. auf 0dB gesetzt
        if self.preamp == 1:
            self.preamp = 20
        elif self.preamp == 0:
            self.preamp = 0
        else:
            self.error = 1
        return self.error, self.preamp

    def _GetPreAmpIntern(self):
        self.error = 0
        dct = self._do_cmds("GetPreAmp", locals())
        self._update(dct)
        if self.error == 0:
            if not dct:
                self.preamp = 0
            else:
                self.preamp = float(self.preamp)
        # Die Abfrage nach PreAmp? ergibt nur eins oder Null
        # Wenn eins, dann ist PreAmp auf 20dB gesetzt
        # Wenn Null, dann ist PreAmp Off bzw. auf 0dB gesetzt
        if self.preamp == 1:
            self.preamp = 20
        elif self.preamp == 0:
            self.preamp = 0
        else:
            self.error = 1
        return self.error, self.preamp

    # Gerät hat keine Funktion um auszwählen, welcher Trace bearbeitet werden soll.
    # Statt dessen wird die entsprechende Trace Nummer mit den Befehlen übergeben,
    # um das zu ermöglichen die Trace Nummer in einer Variable gespeichert.
    def _SetTraceIntern(self, trace):
        self.trace = trace
        return 0, trace

    def _GetTraceIntern(self):
        return 0, self.trace

    # Att Modes gibt es bei diesem Gerät nicht, deshalb wird immer der standard gestzt,
    # bzw. zurückgegeben.
    def _SetAttModeIntern(self, trace):
        return 0, 'LOWNOISE'

    def _GetAttModeIntern(self):
        return 0, 'LOWNOISE'

    # Diese Funktion schlaten das ZVL in den Spectrum Analyzer Mode
    def SetSANMode(self):
        self.error = 0
        dct = self._do_cmds('SetSANMode', locals())
        self._update(dct)
        return self.error, 0

    # ***************************************************************************
    #
    #       Die Init Funktion initialisiert das Gerät, sie muss als erstes aufgerufen werden
    # ***************************************************************************
    def Init(self, ini=None, channel=None):

        if channel is None:
            channel = 1
        self.error = SPECTRUMAN.Init(self, ini, channel)
        sec = 'channel_%d' % channel
        try:
            self.levelunit = self.conf[sec]['unit']
        except KeyError:
            self.levelunit = self._internal_unit

        # Schaltet das ZVL in in den SAN - Spectrum analyzer Mode
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
        self._cmds['Preset'] = []
        presets = [('trace',
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
                   # ('attmode', ###??????
                   #     [('0','auto'), ('1','manual')],
                   #     [('INPut:ATTenuation::AUTO ON', None),('INPut:ATTenuation::AUTO OFF', None)]),
                   ('sweeptime',
                    None,
                    'SetSweepTime'),
                   ('sweeppoints',
                    None,
                    'SetSweepPoints')]

        # self.SetTrace(self.conf[sec]['trace'])

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
            # print k, vals, actions
            try:
                v = self.conf[sec][k]

                if (vals is None):
                    try:
                        err, ret = getattr(self, actions)(v)
                        if err != 0:
                            self.error = err
                            return self.error
                    except (AttributeError):
                        self._cmds['Preset'].append((eval(actions[0]), actions[1]))
                else:
                    for idx, vi in enumerate(vals):
                        if v.lower() in vi:
                            self._cmds['Preset'].append(actions[idx])
            except KeyError:
                pass

        #
        # Initialisierung des Signalgenerators über die Methode '._do_cmds' der Klasse DRIVER (driver.py)
        #
        dct = self._do_cmds('Preset', locals())
        self._update(dct)
        return self.error


##########################################################################       
#
# Die Funktion main() wird nur zum Test des Treibers verwendet!
###########################################################################
def main():
    from mpylab.tools.util import format_block
    # from mpylab.device.signalgenerator_ui import UI as UI
    #
    # Wird für den Test des Treibers keine ini-Datei über die Kommnadoweile eingegebnen, dann muss eine virtuelle Standard-ini-Datei erzeugt
    # werden. Dazu wird der hinterlegte ini-Block mit Hilfe der Methode 'format_block' formatiert und der Ergebnis-String mit Hilfe des Modules
    # 'StringIO' in eine virtuelle Datei umgewandelt.
    #
    try:
        ini = sys.argv[1]
    except IndexError:
        ini = format_block("""
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
        ini = io.StringIO(ini)

    # #
    # # Zum Test des Treibers werden sogenannte Konsistenzabfragen ('assert' Bedingungen) verwendet, welche einen 'AssertationError' liefern,
    # # falls die Bedingung 'false' ist. Zuvor wird eine Testfrequenz und ein Level festgelegt, ein Objekt der Klasse SMB100A erzeugt und der
    # # Signalgenerator initialisiert.
    # #
    # from mpylab.device.spectrumanalyzer_ui import UI as UI
    sp = SPECTRUMANALYZER()
    try:
        from mpylab.device.spectrumanalyzer_ui import UI as UI
    except ImportError:
        pass
    else:
        ui = UI(sp, ini=ini)
        ui.configure_traits()
        sys.exit(0)

    err = sp.Init(ini)
    assert err == 0, 'Init() fails with error %d' % (err)

    _assertlist = [("SetTrace", 1, "assert"),
                   ("SetCenterFreq", 200e6, "assert"),
                   ("SetSpan", 6e9, "assert"),
                   ("SetStartFreq", 6e3, "assert"),
                   ("SetStopFreq", 6e9, "assert"),
                   ("SetRBW", "auto", "print"),  # 200e3
                   ("SetVBW", "auto", "print"),  # 10e3
                   ("SetRefLevel", -20, "assert"),
                   ("SetAtt", "auto", "print"),  # 20
                   ("SetPreAmp", 0, "assert"),
                   ("SetDetector", "AUTOSELECT", "print"),
                   # 'AUTOSELECT', 'AUTOPEAK', 'MAXPEAK', 'MINPEAK', 'SAMPLE', 'RMS', 'QUASIPEAK'
                   ("SetTraceMode", "WRITE", "print"),  # 'WRITE','VIEW','AVERAGE', 'BLANK', 'MAXHOLD', 'MINHOLD
                   ("SetSweepCount", 100, "assert"),
                   ("SetSweepTime", "auto", "print"),
                   ("SetTriggerMode", "VIDEO", "print"),  # 'FREE', 'VIDEO', 'EXTERNAL'
                   ("SetTriggerDelay", 0, "print"),
                   ("SetSweepPoints", 500, "assert")
                   ]

    for funk, value, test in _assertlist:
        err, ret = getattr(sp, funk)(value)
        assert err == 0, '%s() fails with error %d' % (funk, err)
        if value != None:
            if test == "assert":
                assert ret == value, '%s() returns freq=%s instead of %s' % (funk, ret, value)
            else:
                print(('%s(): Rückgabewert: %s   Sollwert: %s' % (funk, ret, value)))
        else:
            print(('%s(): Rückgabewert: %s' % (funk, ret)))

    err, spectrum = sp.GetSpectrum()
    assert err == 0, 'GetSpectrum() fails with error %d' % (err)
    print(spectrum)

    # err=sp.Quit()
    # assert err==0, 'Quit() fails with error %d'%(err)


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
