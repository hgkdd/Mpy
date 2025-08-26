# -*- coding: utf-8 -*-
#
import io
import sys

from mpylab.device.signalgenerator import SIGNALGENERATOR as SGNLGNRTR
# from scuq import *
from mpylab.tools.Configuration import fstrcmp


#
#
# Für den Signalgnerator SMF100A
# Diese greift auf die Unterklasse SIGNALGENERATOR (signalgenerator.py) und darüber auf die Unterklasse DRIVER (driver.py) zu.
#
class SIGNALGENERATOR(SGNLGNRTR):
    def __init__(self):
        SGNLGNRTR.__init__(self)
        # print self.map
        self.map['AM_sources']['INT1'] = 'LF1'
        self.map['AM_sources']['INT2'] = 'LF2'
        self.map['AM_waveforms']['SQUARE'] = 'SQU'
        self.map['AM_waveforms']['TRIANGLE'] = 'TRI'
        self.map['AM_LFOut']['OFF'] = '0'
        self.map['AM_LFOut']['ON'] = '1'
        self.map['PM_sources']['EXT1'] = 'EXT'
        self.map['PM_pol']['NORMAL'] = 'NORM'
        self.map['PM_pol']['INVERTED'] = 'INV'

        # print self.map
        self._internal_unit = 'dBm'
        #
        # Im Wörterbuch '._cmds' werden die Befehle zum Steuern des speziellen Signalgenerators definiert, z.B. SetFreq() zum Setzen
        # der Frequenz. Diese können in der Dokumentation des entsprechenden Signalgenerators nachgeschlagen werden.
        # In der Unterklasse SIGNALGENERATOR wurden bereits Methoden zur Ansteuerung eines allgemeinen Signalgenerators definiert,
        # welche die Steuerbefehle aus dem hier definierten '.cmds' Wörterbuch abrufen.
        # Das Wörterbuch enthält für jeden Eintrag ein Schlüsselwort mit dem allgemeinen Befehl als String, z.B. SetFreq(). Diesem
        # Schlüsselwort wird eine Liste zugeordnet, wobei jeder Listeneintrag ein Tupel ist und jeder Tupel einen Befehl und eine Vorlage
        # für die darauffolgende Antwort des Signalgenerators enthaelt.
        #
        self._cmds = {'Init': [('*RST', None),
                               ('OUTP:ALL:STAT OFF', None)],
                      'Quit': [('OUTP:ALL:STAT OFF', None)],
                      'RFOn': [('OUTP:ALL:STAT ON', None)],
                      'RFOff': [('OUTP:ALL:STAT OFF', None)],
                      'AMOn': [('AM:STAT ON', None)],
                      'AMOff': [('AM:STAT OFF', None)],
                      'PMOn': [('PULM:STAT ON', None),
                               ('MOD:STAT ON', None)],
                      'PMOff': [('PULM:STAT OFF', None),
                                ('MOD:STAT OFF', None)],
                      'SetFreq': [("'SOUR:FREQ:CW %fHz'%freq", None)],
                      'GetFreq': [('SOUR:FREQ:CW?', r'(?P<freq>%s)' % self._FP)],
                      'SetLevel': [(
                                   "'SOUR:POW:LEVEL:IMM:AMPL %f'%self.convert.scuq2c(unit, self._internal_unit, float(level))[0]",
                                   None)],
                      'GetLevel': [('SOUR:POW:LEVEL:IMM:AMPL?', r'(?P<level>%s)' % (self._FP))],
                      'GetDescription': [('*IDN?', r'(?P<IDN>.*)')]}
        # 
        #

    def ConfAM(self, source, freq, depth, waveform, LFOut):
        source = fstrcmp(source, self.AM_sources, n=1, cutoff=0, ignorecase=True)[0]
        waveform = fstrcmp(waveform, self.AM_waveforms, n=1, cutoff=0, ignorecase=True)[0]
        lfo = 1
        if source == 'INT2':
            lfo = 2
        if source in ('EXT_AC', 'EXT_DC', 'TWOTONE_AC', 'TWOTONE_DC'):
            raise NotImplementedError
        if source == 'OFF':
            return self.AMOff()
        if waveform in ('NOISE', 'SAWTOOTH'):
            raise NotImplementedError

        self._cmds['ConfAM'] = [("'" + 'SOUR:AM:SOUR ' + "%s'%source", None),
                                ('SOUR:AM:SOUR?', '(?P<source>\S+)'),
                                ("'" + 'SOUR:AM:DEPT ' + "%dPCT'%(int(depth*100))", None),
                                # Vorlage enthielt '%d %%' !!!???
                                ('SOUR:AM:DEPT?', '(?P<depth>\d+)'),
                                ("'" + 'SOUR:LFO%d:FREQ ' % lfo + "%s HZ'%freq", None),
                                ('SOUR:LFO%d:FREQ?' % lfo, '(?P<freq>%s)' % self._FP),
                                ("'" + 'SOUR:LFO%d:SHAP ' % lfo + "%s'%(waveform)", None),  # waveform --> SINE | SQUare
                                ('SOUR:LFO%d:SHAP?' % lfo, '(?P<waveform>\S+)'),
                                ("'" + 'SOUR:LFO%d ' % lfo + "%s'%(LFOut)", None),
                                ('SOUR:LFO%d?' % lfo, '(?P<LFOut>\S+)')]
        return SGNLGNRTR.ConfAM(self, source, freq, depth, waveform, LFOut)

    def ConfPM(self, source, freq, pol, width, delay):
        source = fstrcmp(source, self.PM_sources, n=1, cutoff=0, ignorecase=True)[0]
        if source == 'EXT2':
            raise NotImplementedError
        if source == 'OFF':
            return self.PMOff()
        self._cmds['ConfPM'] = [("'PULM:SOUR %s'%source", None),
                                ('PULM:SOUR?', '(?P<source>\S+)'),
                                ("'PULM:POL %s'%pol", None),
                                ('PULM:POL?', '(?P<pol>\S+)'),
                                ("'PULM:WIDT %f s'%width", None),
                                ('PULM:WIDT?', '(?P<width>%s)' % self._FP),
                                ("'PULM:DEL %f s'%delay", None),
                                ('PULM:DEL?', '(?P<delay>%s)' % self._FP),
                                ("'PULM:PER %f s'%(1.0/freq)", None),
                                ('PULM:PER?', '(?P<period>%s)' % self._FP)]

        self.error = SGNLGNRTR.ConfPM(self, source, freq, pol, width, delay)

        return self.error

    def Init(self, ini=None, channel=None):
        if channel is None:
            channel = 1
        self.error = SGNLGNRTR.Init(self, ini, channel)
        sec = 'channel_%d' % channel
        try:
            self.levelunit = self.conf[sec]['unit']
        except KeyError:
            self.levelunit = self._internal_unit
        #   
        # In der Methode 'main()' wird das Objekt sg der Klasse SMB100A definiert. Die Befehlsliste (dictionary) 'sg._cmds' der
        # Klasse SMB100A wird mit einem Eintag namens 'Preset' erweitert und bekommt als Wert zunächst eine leere Liste zugewiesen.
        # Als Wert wurde eine Liste gewählt, da zur Initilisierung mehrere Befehle notwendig sein können. Jedem Listeneintrag bzw.
        # Initialisierungseschritt muss ein Tupel bestehend aus dem Befehl und der Auswertung der Signalgeneratorantwort zugewiesen
        # werden. Zur Auswahl der notwendigen Initialisierungsschritte wird zunächst die Liste 'presets' definiert. Dabei handelt
        # es sich um eine Art Tabelle mit drei Spalten, welche die möglichen Initialisierungsschritte und falls vorhanden zugehörigen
        # Optionen inhaltet. 
        #
        self._cmds['Preset'] = []
        presets = [('attmode',
                    [('0', 'auto'), ('1', 'fixed')],
                    [('OUTP:AMOD AUTO', None), ('OUTP:AMOD FIX', None)]),
                   ('attenuation',
                    None,
                    ("'SOUR:POW:ATT %fdB'%self.convert.c2c(self.levelunit, self._internal_unit, float(v))", None)),
                   ('leveloffset',
                    None,
                    ("'SOUR:POW:LEV:IMM:OFFS %f'%self.convert.c2c(self.levelunit, self._internal_unit, float(v))",
                     None)),
                   ('levellimit',
                    None,
                    ("'SOUR:POW:LIM:AMPL %f'%self.convert.c2c(self.levelunit, self._internal_unit, float(v))", None)),
                   ('level',
                    None,
                    ("'SOUR:POW:LEVEL:IMM:AMPL %f'%self.convert.c2c(self.levelunit, self._internal_unit, float(v))",
                     None)),
                   ('outputstate',
                    [('1', 'on')],
                    [('OUTP:STAT ON', None)])]
        #
        # Die zur Initialisierung des Signalgenerators notwendigen Schritte werden durch zeilenweise Betrachtung der Liste 'presets'
        # herausgefiltert und in die Befehlsliste (dictionary) 'self._cmds' übertragen und stehen damit stehen auch in 'sg._cmds' zur
        # Verfügung.
        # Die Klassenvariable '.conf' (dictionary) wurde in der (Unter-)Klasse DRIVER definert.
        # -> If / else Anweisung zur Behandlung von Initialisierungsschritten ohne Optionen (if) und mit Optionen (else).
        # -> Bei Initialisierungsschritten mit Optionen erfolg die Auswahl der notwendigen Option über...(???)
        # 
        for k, vals, actions in presets:
            # print k, vals, actions
            # print '---------------------------'
            try:
                v = self.conf[sec][k]
                if vals is None:
                    # print self.convert.c2c, self.levelunit, self._internal_unit, float(v)
                    # print actions[0]
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
    #


# Die Funktion main() wird nur zum Test des Treibers verwendet!
#
def main():
    from mpylab.tools.util import format_block
    from mpylab.device.signalgenerator_ui import UI as UI
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
                        description: 'SMF100A'
                        type:        'SIGNALGENERATOR'
                        vendor:      'Rohde&Schwarz'
                        serialnr:
                        deviceid:
                        driver:

                        [Init_Value]
                        fstart: 100e3
                        fstop: 22e9
                        fstep: 1
                        visa: TCPIP::192.168.88.248::INSTR
                        virtual: 0

                        [Channel_1]
                        name: RFOut
                        level: -100.0
                        unit: dBm
                        outpoutstate: 0
                        """)
        ini = io.StringIO(ini)
    sg = SIGNALGENERATOR()
    ui = UI(sg, ini=ini)
    ui.configure_traits()


def test():
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
                        description: 'SMF100A'
                        type:        'SIGNALGENERATOR'
                        vendor:      'Rohde&Schwarz'
                        serialnr:
                        deviceid:
                        driver:

                        [Init_Value]
                        fstart: 100e3
                        fstop: 22e9
                        fstep: 1
                        visa: TCPIP::192.168.88.248::INSTR
                        virtual: 0

                        [Channel_1]
                        name: RFOut
                        level: -100.0
                        unit: dBm
                        outpoutstate: 0
                        """)
        ini = io.StringIO(ini)
    sg = SIGNALGENERATOR()
    sg.Init(ini)
    return sg


#
#          
#  ------------ Hauptprogramm ---------------------------
#
# Die Treiberdatei selbst und damit das Hauptprogramm wird nur gestartet, um den Treibercode zu testen. In diesem Fall springt
# das Programm direkt in die Funktion 'main()'. Bei der späteren Verwendung des Treibers wird nur die Klasse 'SMB100A' und deren
# Methoden importiert.
#
if __name__ == '__main__':
    #main()
    sg = test()
    print(sg.GetDescription())

