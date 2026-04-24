# -*- coding: utf-8 -*-
#
"""mpylab.device.sg_rs_smb100a module."""
import io
import sys

# from scuq import *
from mpylab.device.signalgenerator import SIGNALGENERATOR as SGNLGNRTR


#
#
# Für den Signalgnerator SMB100A mit dem Softwarepaket SMB-B106 zur Verwendung bis 6GHz wird die Klasse 'SMB100A' definiert.
# Diese greift auf die Unterklasse SIGNALGENERATOR (signalgenerator.py) und darüber auf die Unterklasse DRIVER (driver.py) zu.
#
class SIGNALGENERATOR(SGNLGNRTR):
    """SIGNALGENERATOR class."""
    def __init__(self, **kw):
        SGNLGNRTR.__init__(self, **kw)
        self.map['AM_sources']['INT1'] = 'INT'
        self.map['AM_sources']['INT2'] = 'N/A'
        self.map['AM_waveforms']['SQUARE'] = 'SQU'
        self.map['AM_LFOut']['Off'] = '0'
        self.map['AM_LFOut']['On'] = '1'
        self.map['PM_sources']['EXT1'] = 'EXT'
        self.map['PM_pol']['NORMAL'] = 'NORM'
        self.map['PM_pol']['INVERTED'] = 'INV'
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
                               ('OUTP:STAT OFF', None)],
                      'Quit': [('OUTP:STAT OFF', None)],
                      'RFOn': [('OUTP:STAT ON', None)],
                      'RFOff': [('OUTP:STAT OFF', None)],
                      'AMOn': [('SOUR:AM:STAT ON', None)],
                      'AMOff': [('SOUR:AM:STAT OFF', None)],
                      'PMOn': [('SOUR:PULM:STAT ON', None)],
                      'PMOff': [('SOUR:PULM:STAT OFF', None)],
                      'SetFreq': [('SOUR:FREQ:CW {freq:f}Hz', None)],
                      'GetFreq': [('SOUR:FREQ:CW?', rf'(?P<freq>{self._FP})')],
                      'SetLevel': [
                          (
                              lambda self, unit, level, **kwargs:
                              f"SOUR:POW:LEVEL:IMM:AMPL {self.convert.scuq2c(unit, self._internal_unit, float(level))[0]:f}",
                              None
                          )
                      ],
                      #'SetLevel': [(
                      #             "'SOUR:POW:LEVEL:IMM:AMPL %f'%self.convert.scuq2c(unit, self._internal_unit, float(level))[0]",
                      #             None)],
                      'GetLevel': [('SOUR:POW:LEVEL:IMM:AMPL?', rf'(?P<level>{self._FP})')],
                      'ConfAM': [
                          ("SOUR:AM:SOUR {source}", None),
                          ('SOUR:AM:SOUR?', r'(?P<source>\S+)'),

                          (
                              lambda self, depth, **kwargs:
                              f"SOUR:AM:DEPT {int(depth * 100):d}",
                              None
                          ),
                          ('SOUR:AM:DEPT?', r'(?P<depth>\d+)'),

                          ("SOUR:LFO:FREQ {freq} HZ", None),
                          ('SOUR:LFO:FREQ?', rf'(?P<freq>{self._FP})'),

                          ("SOUR:LFO:SHAP {waveform}", None),
                          ('SOUR:LFO:SHAP?', r'(?P<waveform>\S+)'),

                          ("LFO:STAT {LFOut}", None),
                          ('LFO:STAT?', r'(?P<LFOut>\d+)')
                      ],
                      # 'ConfAM': [("SOUR:AM:SOUR {source}", None),
                      #            ('SOUR:AM:SOUR?', r'(?P<source>\S+)'),
                      #            ("'SOUR:AM:DEPT %d '%(int(depth*100))", None),  # Vorlage enthielt '%d %%' !!!???
                      #            ('SOUR:AM:DEPT?', r'(?P<depth>\d+)'),
                      #            ("SOUR:LFO:FREQ {freq} HZ", None),
                      #            ('SOUR:LFO:FREQ?', rf'(?P<freq>{self._FP})'),
                      #            ("'SOUR:LFO:SHAP {waveform}'", None),  # waveform --> SINE | SQUare
                      #            ('SOUR:LFO:SHAP?', r'(?P<waveform>\S+)'),
                      #            ("'LFO:STAT {LFOut}}'", None),
                      #            ('LFO:STAT?', r'(?P<LFOut>\d+)')],
                      'GetDescription': [('*IDN?', r'(?P<IDN>.*)')]}
        # 
        #

    def Init(self, ini=None, channel=None):
        """Init method."""
        if channel is None:
            channel = 1
        self.error = SGNLGNRTR.Init(self, ini, channel)
        sec = f'channel_{channel}'
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

        # presets = [('attmode',
        #             [('0', 'auto'), ('1', 'fixed')],
        #             [('OUTP:AMOD AUTO', None), ('OUTP:AMOD FIX', None)]),
        #            # ('attenuation',
        #            #     None,
        #            #     ("'OUTP:ATT %f dB'%self.convert.c2c(self.levelunit, self._internal_unit, float(v))", None)),
        #            ('leveloffset',
        #             None,
        #             ("'SOUR:POW:LEV:IMM:OFFS %f'%self.convert.c2c(self.levelunit, self._internal_unit, float(v))",
        #              None)),
        #            ('levellimit',
        #             None,
        #             ("'SOUR:POW:LIM:AMPL %f'%self.convert.c2c(self.levelunit, self._internal_unit, float(v))", None)),
        #            ('level',
        #             None,
        #             ("'SOUR:POW:LEVEL:IMM:AMPL %f'%self.convert.c2c(self.levelunit, self._internal_unit, float(v))",
        #              None)),
        #            ('outputstate',
        #             [('1', 'on')],
        #             [('OUTP:STAT ON', None)])]
        # #
        # # Die zur Initialisierung des Signalgenerators notwendigen Schritte werden durch zeilenweise Betrachtung der Liste 'presets'
        # # herausgefiltert und in die Befehlsliste (dictionary) 'self._cmds' übertragen und stehen damit stehen auch in 'sg._cmds' zur
        # # Verfügung.
        # # Die Klassenvariable '.conf' (dictionary) wurde in der (Unter-)Klasse DRIVER definert.
        # # -> If / else Anweisung zur Behandlung von Initialisierungsschritten ohne Optionen (if) und mit Optionen (else).
        # # -> Bei Initialisierungsschritten mit Optionen erfolg die Auswahl der notwendigen Option über...(???)
        # #
        # for k, vals, actions in presets:
        #     # print k, vals, actions
        #     # print '---------------------------'
        #     try:
        #         v = self.conf[sec][k]
        #         if vals is None:
        #             # print self.convert.c2c, self.levelunit, self._internal_unit, float(v)
        #             # print actions[0]
        #             self._cmds['Preset'].append((eval(actions[0]), actions[1]))
        #         else:
        #             for idx, vi in enumerate(vals):
        #                 if v.lower() in vi:
        #                     self._cmds['Preset'].append(actions[idx])
        #     except KeyError:
        #         pass
        # #
        # # Initialisierung des Signalgenerators über die Methode '._do_cmds' der Klasse DRIVER (driver.py)
        # #
        # dct = self._do_cmds('Preset', locals())
        # self._update(dct)
        presets = [
            (
                'attmode',
                [('0', 'auto'), ('1', 'fixed')],
                [
                    ('OUTP:AMOD AUTO', None),
                    ('OUTP:AMOD FIX', None),
                ]
            ),
            # (
            #     'attenuation',
            #     None,
            #     (
            #         lambda self, v, **kwargs:
            #             f"OUTP:ATT {self.convert.c2c(self.levelunit, self._internal_unit, float(v)):f} dB",
            #         None
            #     )
            # ),
            (
                'leveloffset',
                None,
                (
                    lambda self, v, **kwargs:
                    f"SOUR:POW:LEV:IMM:OFFS {self.convert.c2c(self.levelunit, self._internal_unit, float(v)):f}",
                    None
                )
            ),
            (
                'levellimit',
                None,
                (
                    lambda self, v, **kwargs:
                    f"SOUR:POW:LIM:AMPL {self.convert.c2c(self.levelunit, self._internal_unit, float(v)):f}",
                    None
                )
            ),
            (
                'level',
                None,
                (
                    lambda self, v, **kwargs:
                    f"SOUR:POW:LEVEL:IMM:AMPL {self.convert.c2c(self.levelunit, self._internal_unit, float(v)):f}",
                    None
                )
            ),
            (
                'outputstate',
                [('1', 'on')],
                [
                    ('OUTP:STAT ON', None)
                ]
            )
        ]

        #
        # Die zur Initialisierung des Signalgenerators notwendigen Schritte werden
        # durch zeilenweise Betrachtung der Liste 'presets' herausgefiltert und in
        # die Befehlsliste 'self._cmds' übernommen.
        #
        self._apply_presets(presets, sec)

        #
        # Initialisierung des Signalgenerators über die Methode '._do_cmds'
        # der Klasse DRIVER.
        #
        dct = self._do_cmds('Preset', locals())
        self._update(dct)
        return self.error
    #


# Die Funktion main() wird nur zum Test des Treibers verwendet!
#
def main():
    """main function."""
    import argparse
    from PySide6 import QtWidgets
    from mpylab.tools.util import format_block
    from mpylab.device.signalgenerator_ui import UI as UI
    from mpylab.device.sg_virtual import SIGNALGENERATOR as VIRTUAL_SIGNALGENERATOR
    #
    # Wird für den Test des Treibers keine ini-Datei über die Kommnadoweile eingegebnen, dann muss eine virtuelle Standard-ini-Datei erzeugt
    # werden. Dazu wird der hinterlegte ini-Block mit Hilfe der Methode 'format_block' formatiert und der Ergebnis-String mit Hilfe des Modules
    # 'StringIO' in eine virtuelle Datei umgewandelt.
    #
    parser = argparse.ArgumentParser(description="Start the SMB100A signal generator UI.")
    parser.add_argument("ini", nargs="?", help="Optional path to an INI file.")
    parser.add_argument("--virtual", action="store_true", help="Use the virtual signal generator driver.")
    args = parser.parse_args()

    if args.ini is None:
        ini = format_block("""
                        [DESCRIPTION]
                        description: 'SMB100A'
                        type:        'SIGNALGENERATOR'
                        vendor:      'Rohde&Schwarz'
                        serialnr:
                        deviceid:
                        driver:

                        [Init_Value]
                        fstart: 100e6
                        fstop: 6e9
                        fstep: 1
                        gpib: 28
                        virtual: {virtual}

                        [Channel_1]
                        name: RFOut
                        level: -100.0
                        unit: dBm
                        outputstate: 0
                        """.format(virtual=1 if args.virtual else 0))
        ini = io.StringIO(ini)
    else:
        with open(args.ini, "r", encoding="utf-8") as handle:
            ini = io.StringIO(handle.read())
    sg = VIRTUAL_SIGNALGENERATOR() if args.virtual else SIGNALGENERATOR()
    app = QtWidgets.QApplication(sys.argv)
    ui = UI(sg, ini=ini)
    ui.show()
    sys.exit(app.exec())
    # #
    # # Zum Test des Treibers werden sogenannte Konsistenzabfragen ('assert' Bedingungen) verwendet, welche einen 'AssertationError' liefern,
    # # falls die Bedingung 'false' ist. Zuvor wird eine Testfrequenz und ein Level festgelegt, ein Objekt der Klasse SMB100A erzeugt und der
    # # Signalgenerator initialisiert.
    # #
    # lv=quantities.Quantity(si.WATT, 1e-4)
    # fr=300e6
    # sg=SIGNALGENERATOR()
    # try:
    # from mpylab.device.signalgenerator_ui import UI as UI
    # except ImportError:
    # pass
    # else:
    # ui=UI(sg,ini=ini)
    # ui.configure_traits()
    # sys.exit(0)

    # err=sg.Init(ini)
    # assert err==0, 'Init() fails with error %d'%(err)
    # err,freq=sg.SetFreq(fr)
    # assert err==0, 'SetFreq() fails with error %d'%(err)
    # assert freq==fr, 'SetFreq() returns freq=%e instead of %e'%(freq, fr)
    # err, _ =sg.RFOn()
    # assert err==0, 'RFOn() fails with error %d'%(err)
    # err,level=sg.SetLevel(lv)
    # assert err==0, 'SetLevel() fails with error %d'%(err)
    # assert level==lv, 'SetLevel() returns level=%s instead of %s'%(level, lv)
    # err=sg.Quit()
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
