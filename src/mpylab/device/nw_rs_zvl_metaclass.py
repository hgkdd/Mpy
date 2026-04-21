# -*- coding: utf-8 -*-
#
"""This is :mod:`mpylab.device.nw_rs_zvl`:

   :author: Christian Albrecht, Hans Georg Krauthäuser

   :license: GPL-3 or higher
"""
import re
import ast

from mpylab.device.networkanalyzer import NETWORKANALYZER as NETWORKAN
from mpylab.tools.spacing import logspaceN, linspaceN
from mpylab.device.meta_driver import Meta_Driver, CommandsStorage, Command, Parameter, Function
from mpylab.device.r_types import TUPLE_OF_FLOAT
from mpylab.device.mpy_exceptions import GeneralDriverError


class NETWORKANALYZER(NETWORKAN, metaclass=Meta_Driver):
    """
    Dieser Treiber ist für einen R&S ZVL Vector Network Analyzer geschrieben.

    Für jede Instanz dieser Klasse wird auf dem Gerät ein neuer Channel erstellt.

    Jedem Channel können mehrere Traces zugeordnet werden. Auf dem Gerät muss für alle
    Channels jeder Trace einen eindeutigen Namen besitzen. Die Treiberklasse ist so konzipiert,
    dass diese Vorgabe auf jeden Fall eingehalten wird. Deshalb entsprechen die Trace-Namen
    auf dem Gerät nicht denen, welche der Funktion ``CreateTrace(tracename, sparam)``
    übergeben wurden. So könnte beispielsweise in zwei Instanzen dieser Klasse der Name
    ``"Trc1"`` verwendet werden; auf dem Gerät würden z. B. die Namen
    ``"Trc1_Ch1WIN1TR9"`` und ``"Trc1_Ch2WIN1TR10"`` verwendet werden.

    Für eine nähere Beschreibung der Channels und Traces schauen Sie bitte in das Handbuch
    des Gerätes.

    .. rubric:: Das ``_cmds``-Dict

    In der Variablen ``_cmds`` wird eine Instanz der Klasse ``CommandsStorage`` gespeichert,
    welche sich wie ein Dict verhält. In dem Dict ``CommandsStorage`` werden ``Command``-
    oder ``Function``-Objekte abgelegt. Jedes dieser Objekte entspricht einem VISA-Kommando.
    Für eine nähere Beschreibung der Klassen siehe: ``tools.Command`` und ``tools.Function``.

    Das ``_cmds``-Dict ist die zentrale Sammelstelle für alle VISA-Kommandos. Aus diesem Dict
    erstellt die Driver-Metaklasse Funktionen für die Klasse, die nach dem Erstellen eines
    Objektes sofort wie normale Methoden verwendet werden können.

    .. rubric:: Possibility-Maps

    Nicht immer entsprechen die von den VISA-Befehlen verwendeten Werte den allgemein bekannten
    Bezeichnungen, oder eine Firma bezeichnet eine bestimmte Funktionalität anders als allgemein
    üblich. Um solche Probleme leicht zu lösen, gibt es die Possibility-Maps. Mit ihnen können
    VISA-spezifische Werte auf allgemein gültige Werte gemappt und zurückgemappt werden.

    Possibility-Maps können nur in einer konkreten Implementierung eines Treibers verwendet
    werden, nicht in einer Driver-Superklasse.

    Für eine nähere Beschreibung der Verwendung siehe: ``tools.Meta_Driver``.

    .. rubric:: Possibility-Listen

    Possibilities sind mögliche Werte für einen Parameter. Bei bestimmten Parametern können
    immer nur bestimmte Werte übergeben werden. So sind beispielsweise bei ``sparam``
    (S-Parameter) ausschließlich ``('S11', 'S12', 'S21', 'S22')`` möglich. Damit nicht
    jeder kleine Schreibfehler sofort zum Abbruch des Programms führt und damit sichergestellt
    ist, dass immer ein richtiger Wert übergeben wird, wird mithilfe eines Fuzzy-String-
    Vergleichs der übergebene Wert auf einen in der Possibility-Liste vorhandenen Wert
    zurückgeführt.

    Possibility-Listen können sowohl in einer konkreten Implementierung einer Driver-Klasse
    als auch in einer Driver-Superklasse definiert werden. Es wird geraten, die Definition
    immer in der Superklasse vorzunehmen, damit die Possibilities für alle Driver gleich sind.

    Für eine genauere Beschreibung siehe: ``tools.Meta_Driver``.

    .. rubric:: Methoden

    Siehe auch :class:`mpylab.device.networkanalyzer.NETWORKANALYZER`

    .. method:: CreateWindow(windowName)

       Create a new plot window.

       :param windowName: Name for the new window
       :type windowName: str
       :return: Name of the new window
       :rtype: str

    .. method:: DelWindow()

       Delete the currently active window.

       :return: Name/ID information of the deleted window
       :rtype: tuple

    .. method:: SetWindow(windowName)

       Select an existing window as the active window.

       :param windowName: Name of the window which should be selected
       :type windowName: str
       :return: Name of the currently active window
       :rtype: str

    .. method:: GetWindow()

       Get the name of the currently active window.

       :return: Name of the currently active window
       :rtype: str

    .. method:: GetSpectrum()

       Get the spectrum of the currently active trace.

       :return: tuple of x-values and y-values
       :rtype: tuple
    """

    NETWORKANALYZERS = []

    GetSweepType_rmap = {
        'LOG': 'LOGARITHMIC',
        'LIN': 'LINEAR',
    }

    sweepMode_possib_map = {
        'CONTINUOUS': 'ON',
        'SINGLE': 'OFF',
    }

    GetSweepMode_rmap = {
        '1': 'CONTINUOUS',
        '0': 'SINGLE',
    }

    _cmds = CommandsStorage(
        NETWORKAN,
        Command(
            'SetCenterFreq',
            'SENSe{channel:d}:FREQuency:CENTer {cfreq:s} HZ',
            (
                Parameter('channel', class_attr='internChannel'),
                Parameter('cfreq', ptype=float),
            ),
            rfunction='GetCenterFreq'
        ),
        Command(
            'GetCenterFreq',
            'SENSe{channel:d}:FREQuency:CENTer?',
            Parameter('channel', class_attr='internChannel'),
            rtype="<default>"
        ),
        Command(
            'SetSpan',
            'SENSe{channel:d}:FREQuency:SPAN {span:s} HZ',
            (
                Parameter('channel', class_attr='internChannel'),
                Parameter('span', ptype=float),
            ),
            rfunction='GetSpan'
        ),
        Command(
            'GetSpan',
            'SENSe{channel:d}:FREQuency:SPAN?',
            Parameter('channel', class_attr='internChannel'),
            rtype="<default>"
        ),
        Command(
            'SetStartFreq',
            'SENSe{channel:d}:FREQuency:STARt {stfreq:s} HZ',
            (
                Parameter('channel', class_attr='internChannel'),
                Parameter('stfreq', ptype=float)
            ),
            rfunction='GetStartFreq'
        ),
        Command(
            'GetStartFreq',
            'SENSe{channel:d}:FREQuency:STARt?',
            Parameter('channel', class_attr='internChannel'),
            rtype="<default>"
        ),
        Command(
            'SetStopFreq',
            'SENSe{channel:d}:FREQuency:STOP {spfreq:s} HZ',
            (
                Parameter('channel', class_attr='internChannel'),
                Parameter('spfreq', ptype=float)
            ),
            rfunction='GetStopFreq'
        ),
        Command(
            'GetStopFreq',
            'SENSe{channel:d}:FREQuency:STOP?',
            Parameter('channel', class_attr='internChannel'),
            rtype="<default>"
        ),
        Command(
            'SetRBW',
            'SENSe{channel:d}:BANDwidth:RESolution {rbw:s} HZ',
            (
                Parameter('channel', class_attr='internChannel'),
                Parameter('rbw', ptype=float)
            ),
            rfunction='GetRBW'
        ),
        Command(
            'GetRBW',
            'SENSe{channel:d}:BANDwidth:RESolution?',
            Parameter('channel', class_attr='internChannel'),
            rtype="<default>"
        ),
        Command(
            'SetRefLevel',
            'DISPlay:WINDow{WindowName:s}:TRACe{windTraceNumber:s}:Y:SCALe:RLEVel {reflevel:s} DBM',
            (
                Parameter('WindowName', class_attr='activeWindow_Name'),
                Parameter('windTraceNumber', class_attr='activeTrace_WinNum'),
                Parameter('reflevel', ptype=float)
            ),
            rfunction='GetRefLevel'
        ),
        Command(
            'GetRefLevel',
            'DISPlay:WINDow{WindowName:s}:TRACe{windTraceNumber:s}:Y:SCALe:RLEVel?',
            (
                Parameter('WindowName', class_attr='activeWindow_Name'),
                Parameter('windTraceNumber', class_attr='activeTrace_WinNum')
            ),
            rtype="<default>"
        ),
        Command(
            'SetDivisionValue',
            'DISPlay:WINDow{WindowName:s}:TRACe{windTraceNumber:s}:Y:SCALe:PDIVision {divivalue:s} DBM',
            (
                Parameter('WindowName', class_attr='activeWindow_Name'),
                Parameter('windTraceNumber', class_attr='activeTrace_WinNum'),
                Parameter('divivalue', ptype=float)
            ),
            rfunction='GetDivisionValue'
        ),
        Command(
            'GetDivisionValue',
            'DISPlay:WINDow{WindowName:s}:TRACe{windTraceNumber:s}:Y:SCALe:PDIVision?',
            (
                Parameter('WindowName', class_attr='activeWindow_Name'),
                Parameter('windTraceNumber', class_attr='activeTrace_WinNum')
            ),
            rtype="<default>"
        ),
        Function('CreateTrace', (
            Command(
                'CreateTrace',
                "CALCulate{channel:d}:PARameter:SDEFine '{tracename:s}', '{sparam:s}'",
                (
                    Parameter('channel', class_attr='internChannel'),
                    Parameter('tracename', ptype=str),
                    Parameter('sparam', ptype=str)
                ),
            ),
            Command(
                'ActivedTrace',
                "DISPlay:WINDow{windowName:s}:TRACe{windTraceNumber:d}:FEED '{tracename:s}'",
                (
                    Parameter('windowName', class_attr='activeWindow_Name'),
                    Parameter('windTraceNumber', ptype=int),
                    Parameter('tracename', ptype=str)
                )
            ),
        )),
        Command(
            'DelTrace',
            "CALCulate{channel:d}:PARameter:DELete '{traceName:s}'",
            (
                Parameter('channel', class_attr='internChannel'),
                Parameter('traceName', ptype=str)
            )
        ),
        Command(
            'GetTrace',
            'CALCulate{channel:d}:PARameter:CATalog?',
            Parameter('channel', class_attr='internChannel'),
            rtype="<default>"
        ),
        Command(
            'SetTrace',
            "CALCulate{channel:d}:PARameter:SELect '{traceName:s}'",
            (
                Parameter('channel', class_attr='internChannel'),
                Parameter('traceName', ptype=str)
            )
        ),
        Command(
            'SetSparameter',
            "CALCulate{channel:d}:PARameter:MEASure '{traceName:s}' '{sparam:s}'",
            (
                Parameter('channel', class_attr='internChannel'),
                Parameter('traceName', class_attr='activeTrace_Name'),
                Parameter('sparam', ptype=str)
            ),
            rfunction='GetSparameter'
        ),
        Command(
            'SetSweepType',
            'SENSe{channel:d}:SWEep:TYPE {sweepType:s}',
            (
                Parameter('channel', class_attr='internChannel'),
                Parameter('sweepType', ptype=str)
            ),
            rfunction='GetSweepType'
        ),
        Command(
            'GetSweepType',
            'SENSe{channel:d}:SWEep:TYPE?',
            Parameter('channel', class_attr='internChannel'),
            rtype='<default>'
        ),
        Command(
            'SetSweepCount',
            'SENSe{channel:d}:SWEep:COUNt {sweepCount:s}',
            (
                Parameter('channel', class_attr='internChannel'),
                Parameter('sweepCount', ptype=int)
            ),
            rfunction='GetSweepCount'
        ),
        Command(
            'GetSweepCount',
            'SENSe{channel:d}:SWEep:COUNt?',
            Parameter('channel', class_attr='internChannel'),
            rtype='<default>'
        ),
        Command(
            'NewSweepCount',
            'INITiate{channel:d}:IMMediate',
            Parameter('channel', class_attr='internChannel')
        ),
        Command(
            'SetSweepPoints',
            'SENSe{channel:d}:SWEep:POINts {spoints:s}',
            (
                Parameter('channel', class_attr='internChannel'),
                Parameter('spoints', ptype=int)
            ),
            rfunction='GetSweepPoints'
        ),
        Command(
            'GetSweepPoints',
            'SENSe{channel:d}:SWEep:POINts?',
            Parameter('channel', class_attr='internChannel'),
            rtype='<default>'
        ),
        Command(
            'SetSweepMode',
            "INITiate{channel:d}:CONTinuous {sweepMode:s}",
            (
                Parameter('channel', class_attr='internChannel'),
                Parameter('sweepMode', ptype=str)
            ),
            rfunction='GetSweepMode'
        ),
        Command(
            'GetSweepMode',
            'INITiate{channel:d}:CONTinuous?',
            Parameter('channel', class_attr='internChannel'),
            rtype=str
        ),
        Command(
            'SetTriggerMode',
            'TRIGger{channel:d}:SEQuence:SOURce {triggerMode:s}',
            (
                Parameter('channel', class_attr='internChannel'),
                Parameter('triggerMode', ptype=str)
            ),
            rfunction='GetTriggerMode'
        ),
        Command(
            'GetTriggerMode',
            'TRIGger{channel:d}:SEQuence:SOURce?',
            Parameter('channel', class_attr='internChannel'),
            rtype='<default>'
        ),
        Command(
            'SetTriggerDelay',
            'TRIGger{channel:d}:SEQuence:HOLDoff {tdelay:s} s',
            (
                Parameter('channel', class_attr='internChannel'),
                Parameter('tdelay', ptype=float)
            ),
            rfunction='GetTriggerDelay'
        ),
        Command(
            'GetTriggerDelay',
            'TRIGger{channel:d}:SEQuence:HOLDoff?',
            Parameter('channel', class_attr='internChannel'),
            rtype='<default>'
        ),
        Command(
            'CreateWindow',
            'DISPlay:WINDow{windowName:d}:STATe ON',
            Parameter('windowName', ptype=int),
        ),
        Command(
            'DelWindow',
            'DISPlay:WINDow{windowName:d}:STATe OFF',
            Parameter('windowName', ptype=int),
        ),
        Command(
            'CreateChannel',
            'CONFigure:CHANnel{channel:d}:STATe ON',
            Parameter('channel', class_attr='internChannel')
        ),
        Command(
            'DelChannel',
            'CONFigure:CHANnel{channel:d}:STATe OFF',
            Parameter('channel', class_attr='internChannel')
        ),
        Command(
            'GetSpectrum',
            'CALCulate{channel:d}:DATA? FDAT',
            Parameter('channel', class_attr='internChannel'),
            rtype=TUPLE_OF_FLOAT()
        ),
        Command('SetNWAMode', "INSTrument:SELect NWA", ()),
        Command('GetDescription', '*IDN?', (), rtype=str)
    )

    def __init__(self):
        NETWORKAN.__init__(self)
        self.traces = {}
        self.windows = {}
        self._internal_unit = 'dBm'
        NETWORKANALYZER.NETWORKANALYZERS.append(self)
        self.internChannel = self.__gethighestChannelNumber()
        self.activeTrace = None
        self.activeWindow = None
        self.activeTrace_Name = None
        self.activeTrace_WinNum = None
        self.activeWindow_Name = None

    def close(self):
        """Gibt lokale und geräteseitige Ressourcen bestmöglich frei."""
        try:
            if self.activeTrace is not None and self.activeTrace.getName() in self.traces:
                self.DelTrace()
        except Exception:
            pass
        try:
            if self.activeWindow is not None and self.activeWindow.getName() in self.windows:
                self.DelWindow()
        except Exception:
            pass
        try:
            self._DelChannel()
        except Exception:
            pass
        try:
            NETWORKANALYZER.NETWORKANALYZERS.remove(self)
        except ValueError:
            pass

    def _require_active_window(self):
        if self.activeWindow is None:
            raise GeneralDriverError("Kein aktives Window ausgewählt")

    def _require_active_trace(self):
        if self.activeTrace is None:
            raise GeneralDriverError("Kein aktiver Trace ausgewählt")

    def _parse_ini_args(self, arg_string):
        value = ast.literal_eval(f"({arg_string})")
        if not isinstance(value, tuple):
            value = (value,)
        return value

    def _call_config_method(self, func_name, arg_string):
        method = getattr(self, func_name, None)
        if method is None:
            raise AttributeError(f"Unbekannte Init-Funktion: {func_name}")
        args = self._parse_ini_args(arg_string)
        return method(*args)

    def CreateWindow(self, windowName):
        if windowName in self.windows:
            raise GeneralDriverError(f"Window '{windowName}' existiert bereits")
        win = WINDOW(windowName)
        self.windows[windowName] = win
        self._CreateWindow(win.getInternNumber())
        return 0, windowName

    def DelWindow(self):
        self._require_active_window()
        win = self.activeWindow
        win_name = win.getName()
        intern_number = win.getInternNumber()
        if self.activeTrace is not None and self.activeTrace.getWindow() is win:
            self.activeTrace = None
            self.activeTrace_Name = None
            self.activeTrace_WinNum = None
        del self.windows[win_name]
        self.activeWindow = None
        self.activeWindow_Name = None
        return self._DelWindow(intern_number)

    def SetWindow(self, windowName):
        win = self.windows.get(windowName)
        if win is None:
            raise GeneralDriverError(f"Unbekanntes Window: {windowName}")
        self.activeWindow = win
        self.activeWindow_Name = win.getInternName()
        return self.GetWindow()

    def GetWindow(self):
        self._require_active_window()
        return 0, self.activeWindow.getName()

    def CreateTrace(self, tracename, sparam):
        self._require_active_window()
        if tracename in self.traces:
            raise GeneralDriverError(f"Trace '{tracename}' existiert in dieser Instanz bereits")
        raw_catalog = self._GetTrace()[1]
        existing_traces = re.split(r",", raw_catalog[1:-1]) if raw_catalog else []
        tra = TRACE(self, tracename, self.activeWindow, sparam)
        if tra.getInternName() in existing_traces:
            raise GeneralDriverError(f"Trace '{tracename}' existiert bereits auf dem Gerät")
        self.traces[tracename] = tra
        self._CreateTrace(tra.getInternName(), sparam, tra.getTraceWindowNumber())
        return 0, tracename

    def DelTrace(self):
        self._require_active_trace()
        tra = self.activeTrace
        trace_name = tra.getName()
        intern_name = tra.getInternName()
        del self.traces[trace_name]
        self.activeTrace = None
        self.activeTrace_Name = None
        self.activeTrace_WinNum = None
        return self._DelTrace(intern_name)

    def SetTrace(self, traceName):
        tra = self.traces.get(traceName)
        if tra is None:
            raise GeneralDriverError(f"Unbekannter Trace: {traceName}")
        self.activeTrace = tra
        self.activeTrace_Name = tra.getInternName()
        self.activeTrace_WinNum = tra.getTraceWindowNumber()
        self._SetTrace(self.activeTrace_Name)
        return self.GetTrace()

    def GetTrace(self):
        self._require_active_trace()
        raw_catalog = self._GetTrace()[1]
        trace = re.split(r",", raw_catalog[1:-1]) if raw_catalog else []
        try:
            trace_index = trace.index(self.activeTrace.getInternName())
        except ValueError as exc:
            raise GeneralDriverError("Aktiver Trace wurde im Gerätekatalog nicht gefunden") from exc
        if trace_index + 1 >= len(trace):
            raise GeneralDriverError("Ungültiger Trace-Katalog vom Gerät zurückgegeben")
        return 0, (trace[trace_index], trace[trace_index + 1])

    def GetSparameter(self):
        return 0, self.GetTrace()[1][1]

    def SetSweepCount(self, sweepCount):
        if sweepCount == 0:
            error, ans = self.SetSweepMode('CONTINUOUS')
            if ans != 'CONTINUOUS':
                raise GeneralDriverError('SweepCount konnte nicht deaktiviert werden')
            return 0, 0
        error, ans = self.SetSweepMode('SINGLE')
        if ans != 'SINGLE':
            raise GeneralDriverError('SweepCount konnte nicht aktiviert werden')
        return self._SetSweepCount(sweepCount)

    def GetChannel(self):
        return 0, self.internChannel

    def GetSpectrum(self):
        error, spec = self._GetSpectrum()
        error, sweepType = self.GetSweepType()
        error, start = self.GetStartFreq()
        error, stop = self.GetStopFreq()
        error, points = self.GetSweepPoints()
        if sweepType == 'LOGARITHMIC':
            xValues = logspaceN(start, stop, points, endpoint=1, precision=0)
        elif sweepType == 'LINEAR':
            xValues = linspaceN(start, stop, points, endpoint=1, precision=0)
        else:
            raise GeneralDriverError(f'SweepType {sweepType} wird nicht unterstützt')
        return 0, (tuple(xValues), spec)

    def getChannelNumber(self):
        return self.internChannel

    def __gethighestChannelNumber(self):
        numb = 1
        for nw in NETWORKANALYZER.NETWORKANALYZERS:
            if nw.getChannelNumber() >= numb:
                numb = nw.getChannelNumber() + 1
        return numb

    def Init(self, ini=None, channel=None):
        """
        Die Init-Funktion initialisiert das Gerät und muss vor allen anderen
        Funktionen aufgerufen werden.

        Für die Initialisierung werden alle Parameter aus der INI-Datei ausgelesen
        und dem Gerät übergeben.
        """
        if channel is None:
            channel = 1
        error = NETWORKAN.Init(self, ini, channel)
        sec = f'channel_{channel}'
        try:
            self.levelunit = self.conf[sec]['unit']
        except KeyError:
            self.levelunit = self._internal_unit
        self.SetNWAMode()
        self.CreateChannel()
        create_window_args = self.conf[sec].get('CreateWindow')
        if create_window_args is None:
            raise GeneralDriverError("CreateWindow muss in der INI definiert sein")
        self._call_config_method('CreateWindow', create_window_args)
        self._call_config_method('SetWindow', create_window_args)
        raw_catalog = self._GetTrace()[1]
        trace = re.split(r",", raw_catalog[1:-1]) if raw_catalog else []
        if trace and trace[0] != '':
            i = 0
            while i < len(trace):
                self._DelTrace(trace[i])
                i += 2
        create_trace_args = self.conf[sec].get('CreateTrace')
        if create_trace_args is None:
            raise GeneralDriverError("CreateTrace muss in der INI definiert sein")
        self._call_config_method('CreateTrace', create_trace_args)
        first_trace_name = self._parse_ini_args(create_trace_args)[0]
        self.SetTrace(first_trace_name)
        for func, args in list(self.conf[sec].items()):
            if func in ('CreateTrace', 'CreateWindow', 'unit'):
                continue
            try:
                self._call_config_method(func, args)
            except (AttributeError, NotImplementedError):
                pass
        return error


class TRACE:
    """
    Klasse zum Verwalten der Traces auf dem Gerät.

    Für jeden Trace wird eine neue Instanz dieser Klasse erstellt. Die Klasse
    ermittelt einen eindeutigen Namen für den neuen Trace. Für diese Aufgabe
    besitzt sie eine Klassenvariable, in der alle Traces gespeichert sind
    (unabhängig von der konkreten Instanz). Weiterhin speichert diese Klasse
    alle weiteren relevanten Informationen eines Traces.
    """

    TRACES = []

    def __init__(self, nw, name, win, sparam):
        TRACE.TRACES.append(self)
        self.networkanalyzer = nw
        self.name = name
        self.window = win
        self.sparameter = sparam
        self.traceWindowNumber = self.__gethighestTraceWindowNumber()
        self.internName = f'{name}_Ch{self.networkanalyzer.getChannelNumber()}WIN{self.window.getInternName()}TR{self.traceWindowNumber}'

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


class WINDOW:
    """
    Klasse zum Verwalten der Windows auf dem Gerät.

    Für jedes Window wird eine neue Instanz dieser Klasse erstellt. Die Klasse
    ermittelt eine eindeutige Nummer für das neue Window. Für diese Aufgabe
    besitzt sie eine Klassenvariable, in der alle Windows gespeichert werden
    (unabhängig von der konkreten Instanz).
    """

    WINDOWS = []

    def __init__(self, name):
        WINDOW.WINDOWS.append(self)
        self.name = name
        self.internNumber = self.__gethighestWindowNumber()

    def __gethighestWindowNumber(self):
        numb = 1
        for win in WINDOW.WINDOWS:
            if win.getInternNumber() >= numb:
                numb = win.getInternNumber() + 1
        return numb

    def getInternNumber(self):
        return self.internNumber

    def getInternName(self):
        return str(self.internNumber)

    def getName(self):
        return self.name

if __name__ == "__main__":
    import sys
    import io
    from mpylab.tools.util import format_block

    try:
        ini = sys.argv[1]
    except IndexError:
        ini_text = format_block("""
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
        ini = io.StringIO(ini_text)
    else:
        try:
            with open(ini, "r", encoding="utf-8") as f:
                ini = io.StringIO(f.read())
        except OSError as e:
            print(f"INI-Datei konnte nicht gelesen werden: {e}")
            sys.exit(1)

    print("=== R&S ZVL Treiber Texttest ===")
    nw = NETWORKANALYZER()

    try:
        print("Initialisiere Gerät ...")
        nw.Init(ini=ini, channel=1)

        print("Beschreibung:", nw.GetDescription())
        print("Channel:", nw.GetChannel())
        print("Window:", nw.GetWindow())
        print("Trace:", nw.GetTrace())
        print("S-Parameter:", nw.GetSparameter())
        print("Startfrequenz:", nw.GetStartFreq())
        print("Stopfrequenz:", nw.GetStopFreq())
        print("Sweep-Typ:", nw.GetSweepType())
        print("Sweep-Punkte:", nw.GetSweepPoints())
        print("RBW:", nw.GetRBW())
        print("RefLevel:", nw.GetRefLevel())

        try:
            print("Spektrum lesen ...")
            err, spec = nw.GetSpectrum()
            xvals, yvals = spec
            print("Anzahl x-Werte:", len(xvals))
            print("Anzahl y-Werte:", len(yvals))
            if xvals:
                print("Erste x-Werte:", xvals[:5])
            if yvals:
                print("Erste y-Werte:", yvals[:5])
        except Exception as e:
            print("GetSpectrum fehlgeschlagen:", e)

    except Exception as e:
        print("Texttest fehlgeschlagen:", e)
        sys.exit(1)
    finally:
        try:
            nw.close()
        except Exception as e:
            print("close() fehlgeschlagen:", e)

    print("Texttest beendet.")

