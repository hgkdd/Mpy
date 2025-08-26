# -*- coding: utf-8 -*-
#
"""This is :mod:`mpylab.device.nw_rs_zlv`:

   :author: Christian Albrecht
   :copyright: All rights reserved
   :license: no licence yet
"""

import sys
import io
import traits.api as tapi
import traitsui.api as tuiapi
from mpylab.device.networkanalyzer import NETWORKANALYZER as NETWORKAN
from mpylab.device.networkanalyzer_ui import UI as super_ui
from mpylab.tools.spacing import logspaceN, linspaceN
from mpylab.device.tools import *
from mpylab.device.r_types import *
from mpylab.device.validators import *
from mpylab.device.mpy_exceptions import *
from mpylab.device.Meta_ui import Metaui


class NETWORKANALYZER(NETWORKAN, metaclass=Meta_Driver):
    """
    This Driver use the new dirver framework!
    
    Dieser Driver ist für einen R&S ZVL Vector Network Analyzer geschrieben.
    
    Für jede Instanz dieser Klasse wird auf dem Gerät ein neuer Channel erstellt.
    
    Jedem Channel können mehrere Traces zugeordnet werden. Auf dem Gerät muss, für alle
    Channels, jeder Trace einen eindeutigen Namen besitzen, die Driver Klasse ist so konzipiert,
    dass diese Vorgabe aufjedenfall eingehalten wird. Deshalb entsprechen die Trace-Namen, auf dem
    Gerät, nicht denen welche der Funktion CreateTrace(tracename, sparam) übergeben wurden. So könnte
    beispielsweise in zwei Instanzen dieser Klasse der Name "Trc1" verwendet werden, auf dem Gerät würden
    z.B. die Namen "Trc1_Ch1WIN1TR1" und "Trc1_Ch2WIN1TR1" verwendet werden.
    
    Für eine nähere Beschreibung der Channels und Traces schauen Sie bitte ins Handbuch des Gerätes.
    
    .. rubric:: Das _cmds-Dict:
    
    In der Variable _cmds wird eine Instanz der Klasse CommandsStorage gespeichert, welche sich wie ein Dict verhält.
    In dem Dict CommandsStorage werden Command oder Function Objekte abgelegt. Jedes dieser Objekte entspricht einem 
    VISA-Komamndo. Für eine nähere Beschreibung der Command Klasse siehe: tools.Command und tools.Function.
        
    Das _cmds-Dict ist die zentrale Sammelstelle für alle VISA-Kommandos, aus diesem Dict erstellt die Driver Metaklasse
    Funktionen für die Klasse, die nach dem dem erstellen eines Objetes sofort wie normale Methoden verwendet werden
    können.
    
    .. rubric:: Possibilities_maps:
    
    Nicht immer entsprechen die von den VISA-Befehlen gewordenten Werte den allgemein bekannten Bezeichnungen oder
    eine Firma bezeichnet eine bestimmt Funktionalität anders als allgemein üblich. Um solche Probleme leicht zu 
    löschen gibt es die Possibilities_maps. Mit ihnen können VISA-bezifische Werte auf allgemein gültige gemapt und 
    zurück gemappt werden.
        
    Possibilities_maps können nur in einer konkreten Implementierung eines Driver verwendet werden, nicht in einer 
    Driver-Superklasse. 
        
    Für eine nähre Beschreibung der Verwendung, siehe: tools.Meta_Driver
    
    
    
    .. rubric:: Possibility-Listen:
    
    Possibilities sind mögliche Werte für einen Parameter. Bei bestimmen Parameter können immer nur bestimmte
    Werte übergeben werden, so sind beispielsweise bei sparam (S-Paramter) außschließlich ('S11', 'S12', 'S21', 'S22')
    möglich. Damit nicht jeder kleine Schreibfehelr sofort zum Abbruch des Programm führt und damit sichergestellt ist
    das immer ein richtier Wert übergeben wird, wird mit Hilfe eines Fuzzy-string-compares der übergebene Wert auf einen 
    in der Posssibilites-Liste vorhandenen zurückgeführt.
        
    Possibility-Listen können sowol in einer konkreten Implementierung einer Driver-Klasse als auch in einer Driver-
    Superklasse definiert werden. Es wird geraten die Definition immer in der Super-Klasse vorzunehmen, damit die 
    Possibilities für alle Driver gleich sind.
        
    Für eine genau beschreibung siehe: tools.Meta_Driver
        
    
    .. rubric:: Methods:
    
    siehe auch :class:`mpylab.device.networkanalyzer.NETWORKANALYZER`
    
    .. method:: CreateWindow(windowName):
    
          Create an new plot window.
    
          :param windowName: Name for the new window
          :type windowName: String
          :return: Name of the new Window
          :rtype: String
          
          
    .. method:: DelWindow():
        Delete the currently active window.
        
        :return: Name of the deleted window
        :rtype: String
                         
        
    .. method:: SetWindow(windowName):
        Selects an existing window as the active trace.
        
        :param windowName: Name of the window which should be selected.
        :type windowName: String
        :return: Name of the currently active window. 
        :rtype: String

    
    .. method:: GetWindow():
        Get the name of the currently active window.
    
        :return: Name of the currently active window.
        :rtype: String
    
    
    ..method:: GetSpectrum():
        Get the spectrum of the currently active trace.
        
        :return: retrun a tuple of (x-Values, y-Values)
        :rtype: float 
    """

    NETWORKANALYZERS = []

    # Map: {Allgemein gültige Bezeichnung : Bezeichnung Gerät}

    # Back Map: {RückgabeWert von Gerät : Allgemein gültige Bezeichnung}
    GetSweepType_rmap = {'LOG': 'LOGARITHMIC',
                         'LIN': 'LINEAR',
                         }

    sweepMode_possib_map = {'CONTINUOUS': 'ON',
                            'SINGEL': 'OFF'
                            }

    GetSweepMode_rmap = {'1': 'CONTINUOUS',
                         '0': 'SINGEL'
                         }

    _cmds = CommandsStorage(NETWORKAN,
                            # Manual S. 499
                            Command('SetCenterFreq', 'SENSe%(channel)d:FREQuency:CENTer %(cfreq)s HZ', (
                                Parameter('channel', class_attr='internChannel'),
                                Parameter('cfreq', ptype=float)  # requires=IN_RANGE(0,10e6))
                            ), rfunction='GetCenterFreq'),

                            # Manual S. 499
                            Command('GetCenterFreq', 'SENSe%(channel)d:FREQuency:CENTer?',
                                    Parameter('channel', class_attr='internChannel'),
                                    rtype="<default>"),

                            # Manual S. 500
                            Command('SetSpan', 'SENSe%(channel)d:FREQuency:SPAN %(span)s HZ', (
                                Parameter('channel', class_attr='internChannel'),
                                Parameter('span', ptype=float),
                            ), rfunction='GetSpan'),

                            # Manual S. 500
                            Command('GetSpan', 'SENSe%(channel)d:FREQuency:SPAN?',
                                    Parameter('channel', class_attr='internChannel'),
                                    rtype="<default>"),

                            # Manual S. 501
                            Command('SetStartFreq', 'SENSe%(channel)d:FREQuency:STARt %(stfreq)s HZ', (
                                Parameter('channel', class_attr='internChannel'),
                                Parameter('stfreq', ptype=float)
                            ), rfunction='GetStartFreq'),

                            # Manual S. 501
                            Command('GetStartFreq', 'SENSe%(channel)d:FREQuency:STARt?',
                                    Parameter('channel', class_attr='internChannel'),
                                    rtype="<default>"),

                            # Manual S. 501
                            Command('SetStopFreq', 'SENSe%(channel)d:FREQuency:STOP %(spfreq)s HZ', (
                                Parameter('channel', class_attr='internChannel'),
                                Parameter('spfreq', ptype=float)
                            ), rfunction='GetStopFreq'),

                            # Manual S. 501
                            Command('GetStopFreq', 'SENSe%(channel)d:FREQuency:STOP?',
                                    Parameter('channel', class_attr='internChannel'),
                                    rtype="<default>"),

                            # Meas/Resolution Bandwidht:
                            # Manual S. 473
                            Command('SetRBW', 'SENSe%(channel)d:BANDwidth:RESolution %(rbw)s HZ', (
                                Parameter('channel', class_attr='internChannel'),
                                Parameter('rbw', ptype=float)
                            ), rfunction='GetRBW'),

                            # Manual S. 473
                            Command('GetRBW', 'SENSe%(channel)d:BANDwidth:RESolution?',
                                    Parameter('channel', class_attr='internChannel'),
                                    rtype="<default>"),

                            # [SENSe<Ch>:]BANDwidth|BWIDth[:RESolution]:SELect FAST | NORMal???

                            # Manual S. 430
                            Command('SetRefLevel',
                                    'DISPlay:WINDow%(WindowName)s:TRACe%(windTraceNumber)s:Y:SCALe:RLEVel %(reflevel)s DBM',
                                    (
                                        Parameter('WindowName', class_attr='activeWindow_Name'),
                                        Parameter('windTraceNumber', class_attr='activeTrace_WinNum'),
                                        Parameter('reflevel', ptype=float)
                                    ), rfunction='GetRefLevel'),

                            # Manual S. 430
                            Command('GetRefLevel',
                                    'DISPlay:WINDow%(WindowName)s:TRACe%(windTraceNumber)s:Y:SCALe:RLEVel?', (
                                        Parameter('WindowName', class_attr='activeWindow_Name'),
                                        Parameter('windTraceNumber', class_attr='activeTrace_WinNum')
                                    ), rtype="<default>"),

                            # Manual S. 429
                            Command('SetDivisionValue',
                                    'DISPlay:WINDow%(WindowName)s:TRACe%(windTraceNumber)s:Y:SCALe:PDIVision %(divivalue)s DBM',
                                    (
                                        Parameter('WindowName', class_attr='activeWindow_Name'),
                                        Parameter('windTraceNumber', class_attr='activeTrace_WinNum'),
                                        Parameter('divivalue', ptype=float)
                                    ), rfunction='GetDivisionValue'),

                            # Manual S. 429
                            Command('GetDivisionValue',
                                    'DISPlay:WINDow%(WindowName)s:TRACe%(windTraceNumber)s:Y:SCALe:PDIVision?', (
                                        Parameter('WindowName', class_attr='activeWindow_Name'),
                                        Parameter('windTraceNumber', class_attr='activeTrace_WinNum')
                                    ), rtype="<default>"),

                            # Trace Mode nur Max hold
                            # Manual S. 386
                            # CALCulate<Chn>:PHOLd MAX | OFF

                            # Dafür bei Sweep average!!!!!
                            # Manual S. 473
                            # [SENSe<Ch>:]AVERage[:STATe] <Boolean>
                            # Manual S. 472
                            # [SENSe<Ch>:]AVERage:CLEar

                            Function('CreateTrace', (
                                # Manual S. 384
                                Command('CreateTrace',
                                        "CALCulate%(channel)d:PARameter:SDEFine \'%(tracename)s\', \'%(sparam)s\'", (
                                            Parameter('channel', class_attr='internChannel'),
                                            Parameter('tracename', ptype=str),
                                            Parameter('sparam', ptype=str)
                                        ), ),
                                # Manual S. 426
                                Command('ActivedTrace',
                                        "DISPlay:WINDow%(windowName)d:TRACe%(windTraceNumber)d:FEED \'%(tracename)s\'",
                                        (
                                            Parameter('windowName', class_attr='activeWindow_Name'),
                                            Parameter('windTraceNumber', ptype=int),
                                            Parameter('tracename', ptype=str)
                                        )),
                            )),

                            # Manual S. 382
                            Command('DelTrace', "CALCulate%(channel)d:PARameter:DELete \'%(traceName)s\'", (
                                Parameter('channel', class_attr='internChannel'),
                                Parameter('traceName', ptype=str)
                            )),

                            # Manual S. 381
                            Command('GetTrace', 'CALCulate%(channel)d:PARameter:CATalog?',
                                    Parameter('channel', class_attr='internChannel'),
                                    rtype="<default>"
                                    ),

                            # Manual S. 385
                            Command('SetTrace', "CALCulate%(channel)d:PARameter:SELect \'%(traceName)s\'", (
                                Parameter('channel', class_attr='internChannel'),
                                Parameter('traceName', ptype=str)
                            )),

                            # Manual S. 383
                            Command('SetSparameter',
                                    "CALCulate%(channel)d:PARameter:MEASure \'%(traceName)s\' \'%(sparam)s\'", (
                                        Parameter('channel', class_attr='internChannel'),
                                        Parameter('traceName', class_attr='activeTrace_Name'),
                                        Parameter('sparam', ptype=str)
                                    ), rfunction='GetSparameter'),

                            # Manual S. 523
                            Command('SetSweepType', 'SENSe%(channel)d:SWEep:TYPE %(sweepType)s', (
                                Parameter('channel', class_attr='internChannel'),
                                Parameter('sweepType', ptype=str)
                            ), rfunction='GetSweepType'),

                            # Manual
                            Command('GetSweepType', 'SENSe%(channel)d:SWEep:TYPE?',
                                    Parameter('channel', class_attr='internChannel'),
                                    rtype='<default>'),

                            # Manual S. 520
                            Command('SetSweepCount', 'SENSe%(channel)d:SWEep:COUNt %(sweepCount)s', (
                                Parameter('channel', class_attr='internChannel'),
                                Parameter('sweepCount', ptype=int)
                            ), rfunction='GetSweepCount'),

                            # Manual S. 520
                            Command('GetSweepCount', 'SENSe%(channel)d:SWEep:COUNt?',
                                    Parameter('channel', class_attr='internChannel'),
                                    rtype='<default>'),

                            # Manual S. 443
                            Command('NewSweepCount', 'INITiate%(channel)d:IMMediate',
                                    Parameter('channel', class_attr='internChannel')
                                    ),

                            # Manual S. 521
                            Command('SetSweepPoints', 'SENSe%(channel)d:SWEep:POINts %(spoints)s', (
                                Parameter('channel', class_attr='internChannel'),
                                Parameter('spoints', ptype=int)
                            ), rfunction='GetSweepPoints'),

                            # Manual S. 521
                            Command('GetSweepPoints', 'SENSe%(channel)d:SWEep:POINts?',
                                    Parameter('channel', class_attr='internChannel'),
                                    rtype='<default>'),

                            # Manual S. 442
                            Command('SetSweepMode', "INITiate%(channel)d:CONTinuous %(sweepMode)s", (
                                Parameter('channel', class_attr='internChannel'),
                                Parameter('sweepMode', ptype=str)
                            ), rfunction='GetSweepMode'),

                            # Manual S. 442
                            Command('GetSweepMode', 'INITiate%(channel)d:CONTinuous?',
                                    Parameter('channel', class_attr='internChannel'),
                                    rtype=str),

                            # Manula S. 547
                            Command('SetTriggerMode', 'TRIGger%(channel)d:SEQuence:SOURce %(triggerMode)s', (
                                Parameter('channel', class_attr='internChannel'),
                                Parameter('triggerMode', ptype=str)
                            ), rfunction='GetTriggerMode'),

                            # Manula S. 547
                            Command('GetTriggerMode', 'TRIGger%(channel)d:SEQuence:SOURce?',
                                    Parameter('channel', class_attr='internChannel'),
                                    rtype='<default>'),

                            # Manual S. 546
                            Command('SetTriggerDelay', 'TRIGger%(channel)d:SEQuence:HOLDoff %(tdelay)s s', (
                                Parameter('channel', class_attr='internChannel'),
                                Parameter('tdelay', ptype=int)
                            ), rfunction='GetTriggerDelay'),
                            # Manula S. 546
                            Command('GetTriggerDelay', 'TRIGger%(channel)d:SEQuence:HOLDoff?',
                                    Parameter('channel', class_attr='internChannel'),
                                    rtype='<default>'),

                            # Manual S. 424
                            Command('CreateWindow', 'DISPlay:WINDow%(windowName)d:STATe ON',
                                    Parameter('windowName', ptype=str),
                                    ),

                            # Manual S. 424
                            Command('DelWindow', 'DISPlay:WINDow%(windowName)d:STATe OFF',
                                    Parameter('windowName', ptype=int),
                                    ),

                            Command('CreateChannel', 'CONFigure:CHANnel%(channel)d:STATe ON',
                                    Parameter('channel', class_attr='internChannel')
                                    ),

                            Command('DelChannel', 'CONFigure:CHANnel%(channel)d:STATe OFF',
                                    Parameter('channel', class_attr='internChannel')
                                    ),

                            # Manual S. 415 Wird über Method realisiert
                            # 'GetChannel': [("'CONFigure:CHANnel%d:CATalog?'%self.internChannel", r'(?P<chan>.*')],

                            # Manual S. 339
                            Command('GetSpectrum', 'CALCulate%(channel)d:DATA? FDAT',
                                    Parameter('channel', class_attr='internChannel'),
                                    rtype=TUPLE_OF_FLOAT()
                                    ),

                            # Später:
                            # 'GetSpectrumNB':  [('DATA?', r'DATA (?P<power>%s)'%self._FP)],

                            # Manual
                            Command('SetNWAMode', "INSTrument:SELect NWA", ()),

                            # Manual
                            Command('GetDescription', '*IDN?', (),
                                    rtype=str)

                            # 'Quit':     [('QUIT', None)],
                            )

    # *************************************************************************
    #
    #        Init
    # *************************************************************************
    def __init__(self):
        NETWORKAN.__init__(self)

        self.traces = {}
        self.windows = {}
        self._internal_unit = 'dBm'

        NETWORKANALYZER.NETWORKANALYZERS.append(self)
        self.internChannel = -1
        self.internChannel = self.__gethighestChannelNumber()

        self.activeTrace = None
        self.activeWindow = None

    # Diese Funktion wird aufgerufen wenn eine Instanz einer Klasse gelöscht wird.
    def __del__(self):
        try:
            del NETWORKANALYZER.NETWORKANALYZERS[NETWORKANALYZER.NETWORKANALYZERS.index(self)]
        except ValueError:
            pass

    # ******************************************************************************
    #
    #     Überlagerte Funktionen
    #
    # Diese Funktionen überlagern Funktionen aus dem _cmds-Dict.
    # Dies ist nötig wenn vor dem eigentlichen Aufruf der _cmds Funktion
    # noch andere Aufgaben abgearbeitet werden müssen, oder wenn der Rückgabewert 
    # nicht direkt verwendet werden können. 
    # *******************************************************************************

    # Erstellt ein neues Festern, dazu muss der Fenstername übergeben werden.
    # Der hier übergebenen Name ist nur in der aktuellen Instanz güllig.
    # Der eigentliche auf dem Gerät verwendet Name wird von der Klasse selbständig ermittelt,
    # und ist über alle Instancen hinweg eindeutig.
    def CreateWindow(self, windowName):
        win = WINDOW(windowName)
        self.windows[windowName] = win
        self._CreateWindow(win.getInternName())
        return 0, windowName

    def DelWindow(self):
        self.activeWindow.__del__()
        del self.windows[self.activeWindow.getName()]
        return self._DelWindow(self.activeWindow_Name)

    def SetWindow(self, windowName):
        self.activeWindow = self.windows[windowName]
        self.activeWindow_Name = self.activeWindow.getInternName()
        return self.GetWindow()

    def GetWindow(self):
        return 0, self.activeWindow.getName()

    # Erstellt einen neuen Trace, dazu muss der Name für den neuen Trace übergeben werden.
    # Die hier übergebene Name ist nur in der aktuellen Instanz güllig.
    # Der eigentliche auf dem Gerät verwendet Name wird von der Klasse selbständig ermittelt,
    # und ist über alle Instancen hinweg eindeutig.
    def CreateTrace(self, tracename, sparam):

        existing_traces = re.split(r",", self._GetTrace()[1][1:-1])

        tra = TRACE(self, tracename, self.activeWindow, sparam)

        if tra.getInternName() in existing_traces:
            raise GeneralDriverError("Trace \'%s\' already exist" % tracename)

        self.traces.update({tracename: tra})
        self._CreateTrace(tra.getInternName(), sparam, tra.getTraceWindowNumber())

        return 0, tracename

    def DelTrace(self):
        self.activeTrace.__del__()
        del self.traces[self.activeTrace.getName()]
        return self._DelTrace(self.activeTrace_Name)

    def SetTrace(self, traceName):
        self.activeTrace = self.traces.get(traceName)
        self.activeTrace_Name = self.activeTrace.getInternName()
        self.activeTrace_WinNum = self.activeTrace.getTraceWindowNumber()
        self._SetTrace(self.activeTrace_Name)
        return self.GetTrace()

    # Infos über einen gestimten Trace abrufen
    def GetTrace(self):
        trace = re.split(r",", self._GetTrace()[1][1:-1])
        trace_index = trace.index(self.activeTrace.getInternName())
        # print trace_index
        # print trace
        return 0, (trace[trace_index], trace[trace_index + 1])

    def GetSparameter(self):
        return 0, self.GetTrace()[1][1]

    def SetSweepCount(self, sweepCount):
        if sweepCount == 0:
            error, ans = self.SetSweepMode('CONTINUOUS')
            if ans:
                return 0
            else:
                raise GeneralDriverError('Can not deactivate SweepCount')
        else:
            error, ans = self.SetSweepMode('SINGEL')
            if ans != 'SINGEL':
                raise GeneralDriverError('Can not activate SweepCount')

        return self._SetSweepCount(sweepCount)

    def GetChannel(self):
        return 0, self.internChannel

    # ************************************
    #  Spectrum aus Gerät auslesen
    # ************************************
    def GetSpectrum(self):

        # self.SetSweepCount(1)
        # self.NewSweepCount()
        # time.sleep(1)

        error, spec = self._GetSpectrum()
        error, sweepType = self.GetSweepType()

        if sweepType == 'LOGARITHMIC':
            xValues = logspaceN(self.GetStartFreq()[1], self.GetStopFreq()[1], self.GetSweepPoints()[1], endpoint=1,
                                precision=0)
        elif sweepType == 'LINEAR':
            xValues = linspaceN(self.GetStartFreq()[1], self.GetStopFreq()[1], self.GetSweepPoints()[1], endpoint=1,
                                precision=0)
        else:
            raise GeneralDriverError('SweeType %s is not supported' % sweepType)

        return 0, (tuple(xValues), spec)

    # ******************************************************************************
    #
    #     Verwaltungs Funktionen
    # *******************************************************************************

    def getChannelNumber(self):
        return self.internChannel

    # Ermittelt die Höchste ChannelNummer über alle Intanzen von nw_rs_zlv.py hinweg
    def __gethighestChannelNumber(self):
        numb = 1
        for nw in NETWORKANALYZER.NETWORKANALYZERS:
            if nw.getChannelNumber() >= numb:
                numb = nw.getChannelNumber() + 1
        return numb

    # ***************************************************************************
    #
    #       Die Init Funktion initialisiert das Gerät, sie muss als erstes aufgerufen werden
    # ***************************************************************************
    def Init(self, ini=None, channel=None):
        """
        Die Init Funktion initalisiert das Gerät, sie muss vor allen andren 
        Funktionen aufgerufen werden.
        
        Für das Initalisieren werden alle Parameter aus der ini-Datei aufgerufen
        und dem Gerät übergeben.
        """

        # Die Inhalte der ini-Datei sind in der Variable self.conf gespeichert.
        # Diese Variable ist ein Dict und somit entspricht die Reihenfolge der
        # Parameter nicht der in der ini-Datei.
        # Generell lässt sich das self.conf-Dicht über eine for-Schleife abarbeiten
        # (siehe ende dieser Funktion) das Problem dabei ist, dass alle Parameter in
        # einer wilkürlichen Reihenfolge auftauchen. Ist es notwendig, dass bestimmt
        # Parameter vor andren aufgerufen werden, so muss dies außerhalb der
        # For-Schleife geschehen. Diese Vorgehen wurde, in dieser konkreten Ini-Funktion,
        # bei den Parameter CreateWindow und CreatTrace angewandt.

        # Die keys im self.conf-Dict entprechen den Methoden-Namen dieser Klasse.

        if channel is None:
            channel = 1
        error = NETWORKAN.Init(self, ini, channel)

        sec = 'channel_%d' % channel
        try:
            self.levelunit = self.conf[sec]['unit']
        except KeyError:
            self.levelunit = self._internal_unit

        # Schaltet das ZVL in in den SAN - Spectrum analyzer Mode
        self.SetNWAMode()

        # Erstellt einne neuen Channel auf dem Gerät
        self.CreateChannel()

        # Diese beiden eval Funktionen erstellen ein neues Window.
        # Die dafür nötigen Paramter werden aus dem self.conf-Dict geholt.
        eval("self.%s(%s)" % ('CreateWindow', self.conf[sec]['CreateWindow']))
        eval("self.%s(%s)" % ('SetWindow', self.conf[sec]['CreateWindow']))

        # Existierende Traces im Window löschen:
        trace = re.split(r",", self._GetTrace()[1][1:-1])
        print((self._GetTrace()))
        if trace[0] != '':
            i = 0
            while i < len(trace):
                self._DelTrace(trace[i])
                i = i + 2

        # Diese beiden eval Funktionen erstellen einen neuen Trace.
        # Die dafür nötigen Paramter werden aus dem self.conf-Dict geholt.
        eval("self.%s(%s)" % ('CreateTrace', self.conf[sec]['CreateTrace']))
        eval("self.%s(%s)" % ('SetTrace', self.conf[sec]['CreateTrace'].split(',')[0]))

        # Die restlichen Prameter aus dem self.conf-Dict abarbeiten.
        for func, args in list(self.conf[sec].items()):
            # CreateTrace und CreatWindow wurden schon etwas weiter oben
            # aufgetrufen, weshalb sie hier übersprungen werden.
            if (func == 'CreateTrace') or (func == 'CreateWindow'):
                continue
            # print func,args
            try:
                eval("self.%s(%s)" % (func, args))
            except (AttributeError, NotImplementedError) as e:
                # print e
                pass

        # print "\nINIT ENDE   ",self,"\n\n"

        return error


class TRACE(object):
    """
    Klasse zum verwalten der Traces auf dem Gerät. 
    
    Für jeden Trace wird eine neue Instanz dieser Klasse erstellt. Die Klasse 
    ermittelt einen eindeuten Namen für den Neuen Trace, für diese 
    Aufgabe besitzt sie eine Klassen-Variable in der alle Traces gespeichert sind 
    (unabhängig von der  konkrten Instanz). Weiterhin speichert diese Klasse alle 
    weiteren relevanten Informationen von eine Trace.
    
    Der Name, welcher beim erstellen des Traces der Driver-Instanz übergeben wurde, 
    wird in der Variable self.name gespeichert
    
    Der Name, welcher auf dem Gerät verwendet wird und über alle Instanzen eindeutig
    ist, wird in der Variable self.internName gespeichert.
    """

    TRACES = []

    def __init__(self, nw, name, win, sparam):
        TRACE.TRACES.append(self)
        self.networkanalyzer = nw
        self.name = name
        self.window = win
        self.sparameter = sparam
        self.traceWindowNumber = -1
        self.traceWindowNumber = self.__gethighestTraceWindowNumber()
        self.internName = '%s_Ch%dWIN%sTR%d' % (
            name, self.networkanalyzer.getChannelNumber(), self.window.getInternName(), self.traceWindowNumber)

    def __del__(self):
        try:
            del TRACE.TRACES[TRACE.TRACES.index(self)]
        except ValueError:
            pass

    def __gethighestTraceWindowNumber(self):
        numb = 9
        for trace in TRACE.TRACES:
            if trace.getTraceWindowNumber() >= numb:
                numb = trace.getTraceWindowNumber() + 1
        return numb

    def getTraceWindowNumber(self):
        return self.traceWindowNumber

    def getName(self):
        return self.name

    def getInternName(self):
        return self.internName

    def getsparameter(self):
        return self.sparameter

    def getWindow(self):
        return self.window


class WINDOW(object):
    """
    Klasse zum verwalten der Windows auf dem Gerät. 
    
    Für jedes Window wird eine neue Instanz dieser Klasse erstellt. Die Klasse 
    ermittelt einen eindeutige Nummer für das neue Window, für diese 
    Aufgabe besitzt sie eine Klassen-Variable in der alle Widows gespeichert werden 
    (unabhängig von der  konkrten Instanz). 
    
    Der Name, welcher beim erstellen des Windows der Driver-Instanz übergeben wurde, 
    wird in der Variable self.name gespeichert
    
    Die Nummer, welche auf dem Gerät verwendet wird und über alle Instanzen eindeutig
    ist, wird in der Variable self.internNumbe gespeichert.
    """

    WINDOWS = []

    def __init__(self, name):
        WINDOW.WINDOWS.append(self)
        self.name = name
        self.internNumber = -1
        self.internNumber = self.__gethighestWindowNumber()

    def __del__(self):
        try:
            del WINDOW.WINDOWS[WINDOW.WINDOWS.index(self)]
        except ValueError:
            pass

    def __gethighestWindowNumber(self):
        numb = 1
        for win in WINDOW.WINDOWS:
            if win._getInternNumber() >= numb:
                numb = win._getInternNumber() + 1
        return numb

    def _getInternNumber(self):
        return self.internNumber

    def getInternName(self):
        return str(self.internNumber)

    def getName(self):
        return self.name


class UI(super_ui, metaclass=Metaui):
    """
    Klasse für die grafische Oberfläche zum Testen des Gerätes.
    
    Mit Hilfer der Metaklasse Metaui wird ein großteil aller Buttons und Felder
    automatisch anhand anhand des _commands-Dict und _cmds-Dict der Driver-Klasse bzw. 
    -Superklasse erstellt.
    
    
    In dieser Klasse können weitere tuiapi.Group erstellt werden, welche nicht schon
    durch die Super-Klasse oder Metaklasse erstellt wurden. 
    
    Diese Klasse muss von der UI-Superklasse des Drivers abgeleitet sein.
    """

    # Driver Klasse
    __driverclass__ = NETWORKANALYZER

    # Super Klasse des Drivers
    __super_driverclass__ = NETWORKAN

    # Comands aus dem _cmds-Dict welche ignoriert werden sollen.
    _ignore = ('SetChannel', 'CreateChannel', 'GetSpectrum')

    # __init__ Funktion
    def __init__(self, instance, ini=None):
        super_ui.__init__(self, instance, ini)

    SetWindow = tapi.Button("SetWindow")
    SETWINDOW = tapi.Str()
    newSETWINDOW = tapi.Str()

    def _SetWindow_fired(self):
        err, value = self.dv.SetWindow(self.newSETWINDOW)
        self.SETWINDOW = value

    Main_S = tuiapi.Group(tuiapi.Group(tuiapi.Item('SetWindow', show_label=False, width=100),
                                       tuiapi.Item('SETWINDOW', label='Wert', style='readonly', width=70),
                                       tuiapi.Item('newSETWINDOW', label='traceName', width=60),
                                       orientation='horizontal'),
                          label='Main_Rest')


##########################################################################
#
# Die Funktion main() wird nur zum Test des Treibers verwendet!
###########################################################################
def main():
    from mpylab.tools.util import format_block
    #
    # Wird für den Test des Treibers keine ini-Datei über die Kommnadoweile eingegebnen, dann muss eine virtuelle Standard-ini-Datei erzeugt
    # werden. Dazu wird der hinterlegte ini-Block mit Hilfe der Methode 'format_block' formatiert und der Ergebnis-String mit Hilfe des Modules
    # 'StringIO' in eine virtuelle Datei umgewandelt.
    #
    err = 0
    try:
        ini = sys.argv[1]
    except IndexError:
        ini = format_block("""
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
                        gpib: 18
                        virtual: 0
                        nr_of_channels: 2

                        [Channel_1]
                        unit: 'dBm'
                        SetRefLevel: 10
                        SetRBW: 10e3
                        SetSpan: 5999991000
                        CreateWindow: 'default'
                        CreateTrace: 'default','S22'
                        SetSweepCount: 0
                        SetSweepPoints: 100
                        SetSweepType: 'Log'
                        """)
        # rbw: 3e6
        ini = io.StringIO(ini)

    #        ini2=format_block("""
    #                        [DESCRIPTION]
    #                        description: 'ZLV-K1'
    #                        type:        'NETWORKANALYZER'
    #                        vendor:      'Rohde&Schwarz'
    #                        serialnr:
    #                        deviceid:
    #                        driver:

    #                        [Init_Value]
    #                        fstart: 100e6
    #                        fstop: 6e9
    #                        fstep: 1
    #                        gpib: 18
    #                        virtual: 0

    #                        [channel_1]
    #                        unit: 'dBm'
    #                        SetRefLevel: 0
    #                        SetRBW: 10e3
    #                        SetSpan: 5999991000
    #                        CreateWindow: 'default'
    #                        CreateTrace: 'default','S11'
    #                        SetSweepCount: 1
    #                        SetSweepPoints: 50
    #                        SetSweepType: 'LINEAR'
    #                        """)
    #        ini2=io.StringIO(ini2)

    # #
    # # Zum Test des Treibers werden sogenannte Konsistenzabfragen ('assert' Bedingungen) verwendet, welche einen 'AssertationError' liefern,
    # # falls die Bedingung 'false' ist. Zuvor wird eine Testfrequenz und ein Level festgelegt, ein Objekt der Klasse SMB100A erzeugt und der
    # # Signalgenerator initialisiert.
    # #
    # from mpylab.device.networkanalyzer_ui import UI as UI
    nw = NETWORKANALYZER()
    #    nw2=NETWORKANALYZER()

    try:
        UI(nw)
    except NameError:
        pass
    else:

        ui = UI(nw, ini=ini)
        ui.configure_traits()
        sys.exit(0)

    err = nw.Init(ini)
    assert err == 0, 'Init() fails with error %d' % (err)

    #    err=nw2.Init(ini2)
    #    assert err==0, 'Init() fails with error %d'%(err)

    _assertlist = [
        ("SetCenterFreq", (3e9), "assert"),  # Default:3e9
        ('SetSpan', (5999991000), "print"),  # Default:6e9
        ('SetStartFreq', (9e3), "assert"),  # Default:9e3
        ('SetStopFreq', (6e9), "assert"),  # Default:6e9
        ('SetRBW', (10e3), "assert"),  # Default:10e3
        ('SetSweepType', ("LOGARITHMIC"), "print"),  # LINear | LOGARITHMIC | SEGMent
        ('SetSweepPoints', (50), "assert"),  # Default: 201
        # ('SetSweepCount',(1),"print"),                       #Default: 1
    ]

    for funk, value, test in _assertlist:
        err, ret = eval("nw.%s(%s)" % (funk, ", ".join(value)))
        assert err == 0, '%s() fails with error %d' % (funk, err)
        if value is not None:
            if test == "assert":
                assert ret == value, '%s() returns freq=%s instead of %s' % (funk, ret, value)
            else:
                print(('%s(): Rückgabewert: %s   Sollwert: %s' % (funk, ret, value)))
        else:
            print(('%s(): Rückgabewert: %s' % (funk, ret)))

    err, spec = nw.GetSpectrum()
    assert err == 0, 'GetSpectrum() fails with error %d' % (err)
    print(spec)


#    err,spec=nw2.GetSpectrum()
#    assert err==0, 'GetSpectrum() fails with error %d'%(err)
#    print spec

# err=nw.Quit()
# assert err==0, 'Quit() fails with error %d'%(err)
#


#  ------------ Hauptprogramm ---------------------------
#
# Die Treiberdatei selbst und damit das Hauptprogramm wird nur gestartet, um den Treibercode zu testen. In diesem Fall springt
# das Programm direkt in die Funktion 'main()'. Bei der sp￤teren Verwendung des Treibers wird nur die Klasse 'SMB100A' und deren
# Methoden importiert.
#
if __name__ == '__main__':
    main()
