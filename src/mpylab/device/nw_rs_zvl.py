# -*- coding: utf-8 -*-
#
"""Driver for the Rohde & Schwarz ZVL network analyzer."""

import ast
import functools
import io
import re
import sys

from mpylab.device.mpy_exceptions import GeneralDriverError
from mpylab.device.networkanalyzer import NETWORKANALYZER as NETWORKAN
from mpylab.tools.configuration import fstrcmp
from mpylab.tools.spacing import linspaceN, logspaceN


class NETWORKANALYZER(NETWORKAN):
    """R&S ZVL network analyzer driver implemented on top of the DRIVER base class."""

    NETWORKANALYZERS = []

    GetSweepType_rmap = {
        'LOG': 'LOGARITHMIC',
        'LIN': 'LINEAR',
        'SEGM': 'SEGMENT',
    }

    sweepMode_possib_map = {
        'CONTINUOUS': 'ON',
        'SINGLE': 'OFF',
    }

    GetSweepMode_rmap = {
        '1': 'CONTINUOUS',
        '0': 'SINGLE',
        'ON': 'CONTINUOUS',
        'OFF': 'SINGLE',
    }

    def __init__(self, SearchPaths=None):
        """Initialize driver state, per-instance channel bookkeeping and SCPI command tables."""
        super().__init__(SearchPaths=SearchPaths)
        self.IDN = "R&S,ZVL,0000,0.0"
        self.traces = {}
        self.windows = {}
        self._internal_unit = 'dBm'
        self.internChannel = self.__gethighestChannelNumber()
        NETWORKANALYZER.NETWORKANALYZERS.append(self)
        self.activeTrace = None
        self.activeWindow = None
        self.activeTrace_Name = None
        self.activeTrace_WinNum = None
        self.activeWindow_Name = None
        self.sweepType_possib = ('LINEAR', 'LOGARITHMIC', 'SEGMENT')
        self._cmds = self._build_cmds()
        self._install_simple_methods()

    def _build_cmds(self):
        """Build the low-level SCPI command map consumed by ``DRIVER._do_cmds``."""
        fp = self._FP
        return {
            'SetCenterFreq': [
                (lambda self, value, **kwargs: f"SENSe{self.internChannel:d}:FREQuency:CENTer {value} HZ", None),
            ],
            'GetCenterFreq': [
                (lambda self, **kwargs: f"SENSe{self.internChannel:d}:FREQuency:CENTer?", rf'(?P<cfreq>{fp})'),
            ],
            'SetSpan': [
                (lambda self, value, **kwargs: f"SENSe{self.internChannel:d}:FREQuency:SPAN {value} HZ", None),
            ],
            'GetSpan': [
                (lambda self, **kwargs: f"SENSe{self.internChannel:d}:FREQuency:SPAN?", rf'(?P<span>{fp})'),
            ],
            'SetStartFreq': [
                (lambda self, value, **kwargs: f"SENSe{self.internChannel:d}:FREQuency:STARt {value} HZ", None),
            ],
            'GetStartFreq': [
                (lambda self, **kwargs: f"SENSe{self.internChannel:d}:FREQuency:STARt?", rf'(?P<stfreq>{fp})'),
            ],
            'SetStopFreq': [
                (lambda self, value, **kwargs: f"SENSe{self.internChannel:d}:FREQuency:STOP {value} HZ", None),
            ],
            'GetStopFreq': [
                (lambda self, **kwargs: f"SENSe{self.internChannel:d}:FREQuency:STOP?", rf'(?P<spfreq>{fp})'),
            ],
            'SetRBW': [
                (lambda self, value, **kwargs: f"SENSe{self.internChannel:d}:BANDwidth:RESolution {value} HZ", None),
            ],
            'GetRBW': [
                (lambda self, **kwargs: f"SENSe{self.internChannel:d}:BANDwidth:RESolution?", rf'(?P<rbw>{fp})'),
            ],
            'SetRefLevel': [
                (
                    lambda self, value, **kwargs:
                    f"DISPlay:WINDow{self.activeWindow_Name}:TRACe{self.activeTrace_WinNum}:Y:SCALe:RLEVel {value}",
                    None,
                ),
            ],
            'GetRefLevel': [
                (
                    lambda self, **kwargs:
                    f"DISPlay:WINDow{self.activeWindow_Name}:TRACe{self.activeTrace_WinNum}:Y:SCALe:RLEVel?",
                    rf'(?P<reflevel>{fp})',
                ),
            ],
            'SetDivisionValue': [
                (
                    lambda self, value, **kwargs:
                    f"DISPlay:WINDow{self.activeWindow_Name}:TRACe{self.activeTrace_WinNum}:Y:SCALe:PDIVision {value}",
                    None,
                ),
            ],
            'GetDivisionValue': [
                (
                    lambda self, **kwargs:
                    f"DISPlay:WINDow{self.activeWindow_Name}:TRACe{self.activeTrace_WinNum}:Y:SCALe:PDIVision?",
                    rf'(?P<divivalue>{fp})',
                ),
            ],
            'SetSweepType': [
                (lambda self, value, **kwargs: f"SENSe{self.internChannel:d}:SWEep:TYPE {value}", None),
            ],
            'GetSweepType': [
                (lambda self, **kwargs: f"SENSe{self.internChannel:d}:SWEep:TYPE?", r'(?P<sweepType>.*)'),
            ],
            '_SetSweepCount': [
                (lambda self, value, **kwargs: f"SENSe{self.internChannel:d}:SWEep:COUNt {int(value)}", None),
            ],
            'GetSweepCount': [
                (lambda self, **kwargs: f"SENSe{self.internChannel:d}:SWEep:COUNt?", r'(?P<sweepCount>\d+)'),
            ],
            'NewSweepCount': [
                (lambda self, **kwargs: f"INITiate{self.internChannel:d}:IMMediate", None),
            ],
            'SetSweepPoints': [
                (lambda self, value, **kwargs: f"SENSe{self.internChannel:d}:SWEep:POINts {int(value)}", None),
            ],
            'GetSweepPoints': [
                (lambda self, **kwargs: f"SENSe{self.internChannel:d}:SWEep:POINts?", r'(?P<spoints>\d+)'),
            ],
            'SetSweepMode': [
                (lambda self, value, **kwargs: f"INITiate{self.internChannel:d}:CONTinuous {value}", None),
            ],
            'GetSweepMode': [
                (lambda self, **kwargs: f"INITiate{self.internChannel:d}:CONTinuous?", r'(?P<sweepMode>.*)'),
            ],
            'SetTriggerMode': [
                (lambda self, value, **kwargs: f"TRIGger{self.internChannel:d}:SEQuence:SOURce {value}", None),
            ],
            'GetTriggerMode': [
                (lambda self, **kwargs: f"TRIGger{self.internChannel:d}:SEQuence:SOURce?", r'(?P<triggerMode>.*)'),
            ],
            'SetTriggerDelay': [
                (lambda self, value, **kwargs: f"TRIGger{self.internChannel:d}:SEQuence:HOLDoff {value} s", None),
            ],
            'GetTriggerDelay': [
                (lambda self, **kwargs: f"TRIGger{self.internChannel:d}:SEQuence:HOLDoff?", rf'(?P<tdelay>{fp})'),
            ],
            '_CreateTraceDef': [
                (
                    lambda self, tracename, sparam, **kwargs:
                    f"CALCulate{self.internChannel:d}:PARameter:SDEFine '{tracename}', '{sparam}'",
                    None,
                ),
            ],
            '_ActivateTrace': [
                (
                    lambda self, window_name, wind_trace_number, tracename, **kwargs:
                    f"DISPlay:WINDow{window_name}:TRACe{wind_trace_number}:FEED '{tracename}'",
                    None,
                ),
            ],
            '_DeleteTrace': [
                (
                    lambda self, trace_name, **kwargs:
                    f"CALCulate{self.internChannel:d}:PARameter:DELete '{trace_name}'",
                    None,
                ),
            ],
            '_GetTraceCatalog': [
                (
                    lambda self, **kwargs:
                    f"CALCulate{self.internChannel:d}:PARameter:CATalog?",
                    r'(?P<trace_catalog>.*)',
                ),
            ],
            '_SelectTrace': [
                (
                    lambda self, trace_name, **kwargs:
                    f"CALCulate{self.internChannel:d}:PARameter:SELect '{trace_name}'",
                    None,
                ),
            ],
            '_SetSparameter': [
                (
                    lambda self, sparam, **kwargs:
                    f"CALCulate{self.internChannel:d}:PARameter:MEASure '{self.activeTrace_Name}' '{sparam}'",
                    None,
                ),
            ],
            '_CreateWindow': [
                (lambda self, window_name, **kwargs: f"DISPlay:WINDow{int(window_name)}:STATe ON", None),
            ],
            '_DeleteWindow': [
                (lambda self, window_name, **kwargs: f"DISPlay:WINDow{int(window_name)}:STATe OFF", None),
            ],
            'CreateChannel': [
                (lambda self, **kwargs: f"CONFigure:CHANnel{self.internChannel:d}:STATe ON", None),
            ],
            '_DeleteChannel': [
                (lambda self, **kwargs: f"CONFigure:CHANnel{self.internChannel:d}:STATe OFF", None),
            ],
            '_GetSpectrum': [
                (
                    lambda self, **kwargs:
                    f"CALCulate{self.internChannel:d}:DATA? FDAT",
                    r'(?P<spectrum>([-+]?(\d+(\.\d*)?|\d*\.\d+)([eE][-+]?\d+)?,?)+)',
                ),
            ],
            '_GetStimulus': [
                (
                    lambda self, **kwargs:
                    f"CALCulate{self.internChannel:d}:DATA:STIM?",
                    r'(?P<stimulus>([-+]?(\d+(\.\d*)?|\d*\.\d+)([eE][-+]?\d+)?,?)+)',
                ),
            ],
            'SetNWAMode': [
                ("INSTrument:SELect NWA", None),
            ],
            'GetDescription': [
                ('*IDN?', r'(?P<IDN>.*)'),
            ],
        }

    def _install_simple_methods(self):
        """Bind common set/get methods to the generic DRIVER-backed helpers."""
        specs = [
            ('SetCenterFreq', 'GetCenterFreq', 'cfreq', float, None, None, None, None),
            ('SetSpan', 'GetSpan', 'span', float, None, None, None, None),
            ('SetStartFreq', 'GetStartFreq', 'stfreq', float, None, None, None, None),
            ('SetStopFreq', 'GetStopFreq', 'spfreq', float, None, None, None, None),
            ('SetRBW', 'GetRBW', 'rbw', float, None, None, None, None),
            ('SetRefLevel', 'GetRefLevel', 'reflevel', float, '_require_active_trace', None, None, None),
            ('SetDivisionValue', 'GetDivisionValue', 'divivalue', float, '_require_active_trace', None, None, None),
            ('SetSweepType', 'GetSweepType', 'sweepType', str, None, 'sweepType_possib', None, 'GetSweepType_rmap'),
            ('SetSweepMode', 'GetSweepMode', 'sweepMode', str, None, 'sweepMode_possib', 'sweepMode_possib_map', 'GetSweepMode_rmap'),
            ('SetTriggerMode', 'GetTriggerMode', 'triggerMode', str, None, 'triggerMode_possib', None, None),
            ('SetTriggerDelay', 'GetTriggerDelay', 'tdelay', float, None, None, None, None),
            ('SetSweepPoints', 'GetSweepPoints', 'spoints', int, None, None, None, None),
        ]

        for setter, getter, attr, type_, guard, possib_attr, fwd_map, rev_map in specs:
            setattr(
                self,
                setter,
                functools.partial(
                    self._set_get_value,
                    setter=setter,
                    getter=getter,
                    attr=attr,
                    type_=type_,
                    guard=guard,
                    possibilities_attr=possib_attr,
                    forward_map_attr=fwd_map,
                    reverse_map_attr=rev_map,
                ),
            )
            setattr(
                self,
                getter,
                functools.partial(
                    self._get_value,
                    getter=getter,
                    attr=attr,
                    type_=type_,
                    guard=guard,
                    reverse_map_attr=rev_map,
                ),
            )

    def _normalize_input(self, value, possibilities_attr=None, forward_map_attr=None):
        """Normalize user input via fuzzy matching and optional forward mapping."""
        if possibilities_attr:
            possibilities = getattr(self, possibilities_attr)
            if isinstance(value, str):
                value = fstrcmp(value, possibilities, cutoff=0, ignorecase=True)[0]
        if forward_map_attr:
            value = getattr(self, forward_map_attr).get(value, value)
        return value

    def _normalize_output(self, value, reverse_map_attr=None):
        """Translate device-specific return values back into the public API vocabulary."""
        if reverse_map_attr:
            value = getattr(self, reverse_map_attr).get(value, value)
        return value

    def _run_cmd(self, key, callerdict=None):
        """Execute one entry from ``self._cmds`` and update instance attributes from its result."""
        self.error = 0
        dct = self._do_cmds(key, callerdict or {})
        self._update(dct)
        return dct

    def _parse_ascii_data(self, raw_data, label):
        """Parse a comma-separated ASCII data block returned by the analyzer."""
        if raw_data is None:
            raise GeneralDriverError(f"{label} konnte nicht vom Gerät gelesen werden")

        tokens = [token.strip() for token in raw_data.split(',') if token.strip()]
        if not tokens:
            raise GeneralDriverError(f"{label} enthält keine Werte")

        try:
            return tuple(float(token) for token in tokens)
        except ValueError as exc:
            raise GeneralDriverError(f"{label} enthält ungültige Zahlenwerte") from exc

    def _set_get_value(
        self,
        value,
        setter,
        getter,
        attr,
        type_,
        guard=None,
        possibilities_attr=None,
        forward_map_attr=None,
        reverse_map_attr=None,
    ):
        """Run a set command followed by the matching query and return the normalized result."""
        if guard:
            getattr(self, guard)()
        normalized = self._normalize_input(value, possibilities_attr=possibilities_attr, forward_map_attr=forward_map_attr)
        self._run_cmd(setter, {'value': normalized})
        dct = self._run_cmd(getter)
        if self.error == 0:
            result = type_(getattr(self, attr)) if dct else type_(normalized)
            result = self._normalize_output(result, reverse_map_attr=reverse_map_attr)
            setattr(self, attr, result)
            return self.error, result
        return self.error, getattr(self, attr, None)

    def _get_value(self, getter, attr, type_, guard=None, reverse_map_attr=None):
        """Run a query command and convert its result into the expected Python type."""
        if guard:
            getattr(self, guard)()
        dct = self._run_cmd(getter)
        if self.error == 0:
            if dct:
                result = type_(getattr(self, attr))
                result = self._normalize_output(result, reverse_map_attr=reverse_map_attr)
                setattr(self, attr, result)
            else:
                result = getattr(self, attr, None)
            return self.error, result
        return self.error, getattr(self, attr, None)

    def _require_active_window(self):
        """Ensure that a display window is currently selected."""
        if self.activeWindow is None:
            raise GeneralDriverError("Kein aktives Window ausgewählt")

    def _require_active_trace(self):
        """Ensure that a trace is currently selected."""
        if self.activeTrace is None:
            raise GeneralDriverError("Kein aktiver Trace ausgewählt")

    def _parse_ini_args(self, arg_string):
        """Parse an INI argument list into a tuple of Python values."""
        value = ast.literal_eval(f"({arg_string})")
        if not isinstance(value, tuple):
            value = (value,)
        return value

    def _call_config_method(self, func_name, arg_string):
        """Resolve and call one method referenced by the channel section in the INI file."""
        method = getattr(self, func_name, None)
        if method is None:
            raise AttributeError(f"Unbekannte Init-Funktion: {func_name}")
        args = self._parse_ini_args(arg_string)
        return method(*args)

    def close(self):
        """Best-effort cleanup of traces, windows and the channel owned by this instance."""
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
            self._run_cmd('_DeleteChannel')
        except Exception:
            pass
        try:
            NETWORKANALYZER.NETWORKANALYZERS.remove(self)
        except ValueError:
            pass

    def CreateWindow(self, windowName):
        """Create a logical window object and enable the corresponding analyzer display window."""
        if windowName in self.windows:
            raise GeneralDriverError(f"Window '{windowName}' existiert bereits")
        win = WINDOW(windowName)
        self.windows[windowName] = win
        self._run_cmd('_CreateWindow', {'window_name': win.getInternNumber()})
        if self.error != 0:
            del self.windows[windowName]
            raise GeneralDriverError(f"Window '{windowName}' konnte nicht erstellt werden")
        return 0, windowName

    def DelWindow(self):
        """Delete the currently active window and clear dependent active-trace state."""
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
        self._run_cmd('_DeleteWindow', {'window_name': intern_number})
        return self.error, win_name

    def SetWindow(self, windowName):
        """Select an existing window as the active window for subsequent operations."""
        win = self.windows.get(windowName)
        if win is None:
            raise GeneralDriverError(f"Unbekanntes Window: {windowName}")
        self.activeWindow = win
        self.activeWindow_Name = win.getInternName()
        return self.GetWindow()

    def GetWindow(self):
        """Return the name of the currently active window."""
        self._require_active_window()
        return 0, self.activeWindow.getName()

    def CreateTrace(self, tracename, sparam):
        """Create a new trace, assign its measurement parameter and attach it to the active window."""
        self._require_active_window()
        if tracename in self.traces:
            raise GeneralDriverError(f"Trace '{tracename}' existiert in dieser Instanz bereits")
        sparam = fstrcmp(sparam, self.sparam_possib, cutoff=0, ignorecase=True)[0]
        raw_catalog = self._run_cmd('_GetTraceCatalog').get('trace_catalog')
        existing_traces = re.split(r",", raw_catalog[1:-1]) if raw_catalog else []
        tra = TRACE(self, tracename, self.activeWindow, sparam)
        if tra.getInternName() in existing_traces:
            raise GeneralDriverError(f"Trace '{tracename}' existiert bereits auf dem Gerät")
        self.traces[tracename] = tra
        self._run_cmd('_CreateTraceDef', {'tracename': tra.getInternName(), 'sparam': sparam})
        self._run_cmd(
            '_ActivateTrace',
            {
                'window_name': self.activeWindow_Name,
                'wind_trace_number': tra.getTraceWindowNumber(),
                'tracename': tra.getInternName(),
            },
        )
        return self.error, tracename

    def DelTrace(self):
        """Delete the currently active trace from the analyzer and from local bookkeeping."""
        self._require_active_trace()
        tra = self.activeTrace
        trace_name = tra.getName()
        intern_name = tra.getInternName()
        del self.traces[trace_name]
        self.activeTrace = None
        self.activeTrace_Name = None
        self.activeTrace_WinNum = None
        self._run_cmd('_DeleteTrace', {'trace_name': intern_name})
        return self.error, trace_name

    def SetTrace(self, traceName):
        """Select an existing trace as the active trace for trace-related commands."""
        tra = self.traces.get(traceName)
        if tra is None:
            raise GeneralDriverError(f"Unbekannter Trace: {traceName}")
        self.activeTrace = tra
        self.activeTrace_Name = tra.getInternName()
        self.activeTrace_WinNum = tra.getTraceWindowNumber()
        self._run_cmd('_SelectTrace', {'trace_name': self.activeTrace_Name})
        return self.GetTrace()

    def GetTrace(self):
        """Return the active trace name together with its currently assigned measurement parameter."""
        self._require_active_trace()
        raw_catalog = self._run_cmd('_GetTraceCatalog').get('trace_catalog')
        trace = re.split(r",", raw_catalog[1:-1]) if raw_catalog else []
        try:
            trace_index = trace.index(self.activeTrace.getInternName())
        except ValueError as exc:
            raise GeneralDriverError("Aktiver Trace wurde im Gerätekatalog nicht gefunden") from exc
        if trace_index + 1 >= len(trace):
            raise GeneralDriverError("Ungültiger Trace-Katalog vom Gerät zurückgegeben")
        return 0, (trace[trace_index], trace[trace_index + 1])

    def SetSparameter(self, sparam):
        """Change the measurement parameter of the active trace."""
        self._require_active_trace()
        sparam = fstrcmp(sparam, self.sparam_possib, cutoff=0, ignorecase=True)[0]
        self._run_cmd('_SetSparameter', {'sparam': sparam})
        return self.GetSparameter()

    def GetSparameter(self):
        """Return the measurement parameter assigned to the active trace."""
        return 0, self.GetTrace()[1][1]

    def SetSweepCount(self, sweepCount):
        """Configure the sweep count and switch between single and continuous sweep mode as needed."""
        if sweepCount == 0:
            error, ans = self.SetSweepMode('CONTINUOUS')
            if ans != 'CONTINUOUS':
                raise GeneralDriverError('SweepCount konnte nicht deaktiviert werden')
            return 0, 0
        error, ans = self.SetSweepMode('SINGLE')
        if ans != 'SINGLE':
            raise GeneralDriverError('SweepCount konnte nicht aktiviert werden')
        self._run_cmd('_SetSweepCount', {'value': sweepCount})
        return self.GetSweepCount()

    def GetSweepCount(self):
        """Return the configured number of sweeps for single-sweep operation."""
        return self._get_value('GetSweepCount', 'sweepCount', int)

    def NewSweepCount(self):
        """Start a new single-sweep measurement sequence."""
        self._run_cmd('NewSweepCount')
        return self.error, None

    def GetChannel(self):
        """Return the analyzer channel number owned by this driver instance."""
        return 0, self.internChannel

    def SetChannel(self, chan):
        """Reject channel switching because each driver instance is permanently bound to one channel."""
        if chan != self.internChannel:
            raise GeneralDriverError('Channel ist an diese Instanz gebunden und kann nicht umgeschaltet werden')
        return 0, self.internChannel

    def GetSpectrum(self):
        """Return stimulus and formatted trace data for the active trace.

        The method prefers ``CALC:DATA:STIM?`` for the x-axis and validates that
        the formatted trace data returned by ``FDAT`` contains exactly one value
        per sweep point.
        """
        spectrum_map = self._run_cmd('_GetSpectrum')
        stimulus_map = self._run_cmd('_GetStimulus')
        spectrum = spectrum_map.get('spectrum')
        stimulus = stimulus_map.get('stimulus')
        if spectrum is None:
            return self.error, (tuple(), tuple())

        y_values = self._parse_ascii_data(spectrum, 'Trace-Daten')
        if stimulus is not None:
            xValues = self._parse_ascii_data(stimulus, 'Stimulus-Daten')
        else:
            error, sweepType = self.GetSweepType()
            error, start = self.GetStartFreq()
            error, stop = self.GetStopFreq()
            error, points = self.GetSweepPoints()

            if sweepType == 'LOGARITHMIC':
                xValues = tuple(logspaceN(start, stop, points, endpoint=1, precision=0))
            elif sweepType == 'LINEAR':
                xValues = tuple(linspaceN(start, stop, points, endpoint=1, precision=0))
            else:
                raise GeneralDriverError(
                    f'Stimulus-Daten fehlen und SweepType {sweepType} wird als Fallback nicht unterstützt'
                )

        if len(y_values) == 2 * len(xValues):
            raise GeneralDriverError(
                'Das aktuelle Trace-Format liefert 2 Werte pro Punkt. '
                'GetSpectrum unterstützt nur FDAT-Formate mit 1 Wert pro Sweep-Punkt.'
            )
        if len(y_values) != len(xValues):
            raise GeneralDriverError(
                f'Inkonsistente Datenlängen: {len(xValues)} Stimuluswerte, {len(y_values)} Trace-Werte'
            )
        return 0, (tuple(xValues), y_values)

    def getChannelNumber(self):
        """Return the internal channel number used for global instance bookkeeping."""
        return self.internChannel

    def __gethighestChannelNumber(self):
        """Compute the next free channel number across all active driver instances."""
        numb = 1
        for nw in NETWORKANALYZER.NETWORKANALYZERS:
            if nw.getChannelNumber() >= numb:
                numb = nw.getChannelNumber() + 1
        return numb

    def Init(self, ini=None, channel=None):
        """Initialize communication, create the channel/window/trace setup and apply INI settings."""
        if channel is None:
            channel = 1
        error = NETWORKAN.Init(self, ini, channel)
        sec = f'channel_{channel}'
        try:
            self.levelunit = self.conf[sec]['unit']
        except KeyError:
            self.levelunit = self._internal_unit

        self._run_cmd('SetNWAMode')
        self._run_cmd('CreateChannel')

        create_window_args = self.conf[sec].get('CreateWindow')
        if create_window_args is None:
            raise GeneralDriverError("CreateWindow muss in der INI definiert sein")
        self._call_config_method('CreateWindow', create_window_args)
        self._call_config_method('SetWindow', create_window_args)

        raw_catalog = self._run_cmd('_GetTraceCatalog').get('trace_catalog')
        trace = re.split(r",", raw_catalog[1:-1]) if raw_catalog else []
        if trace and trace[0] != '':
            i = 0
            while i < len(trace):
                self._run_cmd('_DeleteTrace', {'trace_name': trace[i]})
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
    """In-memory representation of one analyzer trace owned by a driver instance."""

    TRACES = []

    def __init__(self, nw, name, win, sparam):
        """Create a trace object and assign a unique instrument trace name."""
        TRACE.TRACES.append(self)
        self.networkanalyzer = nw
        self.name = name
        self.window = win
        self.sparameter = sparam
        self.traceWindowNumber = self.__gethighestTraceWindowNumber()
        self.internName = (
            f'{name}_Ch{self.networkanalyzer.getChannelNumber()}'
            f'WIN{self.window.getInternName()}TR{self.traceWindowNumber}'
        )

    def __gethighestTraceWindowNumber(self):
        """Return the next free trace number used within display windows."""
        numb = 9
        for trace in TRACE.TRACES:
            if trace.getTraceWindowNumber() >= numb:
                numb = trace.getTraceWindowNumber() + 1
        return numb

    def getTraceWindowNumber(self):
        """Return the display trace number associated with this trace."""
        return self.traceWindowNumber

    def getName(self):
        """Return the user-facing trace name."""
        return self.name

    def getInternName(self):
        """Return the unique instrument-side trace name."""
        return self.internName

    def getsparameter(self):
        """Return the measurement parameter assigned to this trace."""
        return self.sparameter

    def getWindow(self):
        """Return the window object this trace is attached to."""
        return self.window


class WINDOW:
    """In-memory representation of one analyzer display window."""

    WINDOWS = []

    def __init__(self, name):
        """Create a window object and assign a unique instrument window number."""
        WINDOW.WINDOWS.append(self)
        self.name = name
        self.internNumber = self.__gethighestWindowNumber()

    def __gethighestWindowNumber(self):
        """Return the next free display window number."""
        numb = 1
        for win in WINDOW.WINDOWS:
            if win.getInternNumber() >= numb:
                numb = win.getInternNumber() + 1
        return numb

    def getInternNumber(self):
        """Return the numeric window identifier used by the analyzer."""
        return self.internNumber

    def getInternName(self):
        """Return the analyzer window identifier as a string."""
        return str(self.internNumber)

    def getName(self):
        """Return the user-facing window name."""
        return self.name


if __name__ == "__main__":
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
                        SetSweepPoints: 401
                        SetSweepType: 'LINEAR'

                    """)
        ini = io.StringIO(ini_text)

    d = NETWORKANALYZER()
    d.Init(ini)
    err, des = d.GetDescription()
    print(err, des)
