# -*- coding: utf-8 -*-

import io
import sys
import numpy as np

from PySide6 import QtWidgets, QtCore

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from mpylab.tools.util import format_block
from mpylab.device.device import CONVERT

conv = CONVERT()

std_ini_text = format_block("""
                [DESCRIPTION]
                description: sp template
                type:        'SPECTRUMANALYZER'
                vendor:      some company
                serialnr:    SN12345
                deviceid:    internal ID
                driver:      dummy.py

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
                attmode: 'auto'
                sweeptime: 10e-3
                sweeppoints: 500
                """).strip()


class MplCanvas(FigureCanvas):
    def __init__(self, parent=None):
        self.figure = Figure()
        self.ax = self.figure.add_subplot(111)
        super().__init__(self.figure)
        self.setParent(parent)

        self.ax.set_title("Spectrum")
        self.ax.set_xlabel("Frequenz in Hz")
        self.ax.set_ylabel("Amplitude in dBm")
        self._line, = self.ax.plot([], [])

    def update_plot(self, x, y):
        self.ax.clear()
        self.ax.plot(x, y)
        self.ax.set_title("Spectrum")
        self.ax.set_xlabel("Frequenz in Hz")
        self.ax.set_ylabel("Amplitude in dBm")
        self.ax.relim()
        self.ax.autoscale_view()
        self.draw()


class UI(QtWidgets.QWidget):
    int_unit = "dBm"

    mainTab = (
        "CenterFreq", "Span", "StartFreq", "StopFreq", "RBW", "VBW",
        "RefLevel", "Att", "AttMode", "PreAmp", "Detector", "TraceMode",
        "Trace", "SweepCount", "SweepTime", "TriggerMode", "TriggerDelay", "SweepPoints"
    )

    # Typisierung der "new..." Eingabefelder möglichst nah am Traits-Original
    field_types = {
        "CenterFreq": float,
        "Span": float,
        "StartFreq": float,
        "StopFreq": float,
        "RBW": str,
        "VBW": str,
        "RefLevel": float,
        "Att": str,
        "AttMode": str,
        "PreAmp": float,
        "Detector": str,
        "TraceMode": str,
        "Trace": int,
        "SweepCount": int,
        "SweepTime": str,
        "TriggerMode": str,
        "TriggerDelay": float,
        "SweepPoints": int,
    }

    def __init__(self, instance, ini=None, parent=None):
        super().__init__(parent)

        self.sp = instance
        self.ini_source = ini if ini is not None else io.StringIO(std_ini_text)

        self.power = ()
        self.value_widgets = {}
        self.new_widgets = {}

        self.setWindowTitle("Spectrumanalyer")
        self.resize(1200, 850)

        self._build_ui()
        self._load_ini()

    # ------------------------------------------------------------------
    # UI-Aufbau
    # ------------------------------------------------------------------

    def _build_ui(self):
        outer = QtWidgets.QVBoxLayout(self)

        self.tabs = QtWidgets.QTabWidget()
        outer.addWidget(self.tabs)

        self._build_ini_tab()
        self._build_main_tab()
        self._build_spectrum_tab()
        self._build_plot_tab()

        bottom = QtWidgets.QHBoxLayout()
        bottom.addStretch()

        self.close_button = QtWidgets.QPushButton("Schließen")
        self.close_button.clicked.connect(self.close)
        bottom.addWidget(self.close_button)

        outer.addLayout(bottom)

    def _build_ini_tab(self):
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)

        self.ini_edit = QtWidgets.QPlainTextEdit()
        self.ini_edit.setMinimumHeight(220)

        self.init_button = QtWidgets.QPushButton("Init")
        self.init_button.clicked.connect(self._Init_fired)

        layout.addWidget(self.ini_edit)
        layout.addWidget(self.init_button)
        layout.addStretch()

        self.tabs.addTab(tab, "Ini")

    def _build_main_tab(self):
        tab = QtWidgets.QWidget()
        outer_layout = QtWidgets.QVBoxLayout(tab)

        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)

        content = QtWidgets.QWidget()
        form_layout = QtWidgets.QVBoxLayout(content)

        for name in self.mainTab:
            row = self._create_main_row(name)
            form_layout.addWidget(row)

        form_layout.addStretch()
        scroll.setWidget(content)

        outer_layout.addWidget(scroll)
        self.tabs.addTab(tab, "Main")

    def _build_spectrum_tab(self):
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)

        self.spectrum_edit = QtWidgets.QPlainTextEdit()
        self.spectrum_edit.setReadOnly(True)

        self.get_spectrum_button_1 = QtWidgets.QPushButton("GetSpectrum")
        self.get_spectrum_button_1.clicked.connect(self._GetSpectrum_fired)

        layout.addWidget(self.spectrum_edit)
        layout.addWidget(self.get_spectrum_button_1)
        layout.addStretch()

        self.tabs.addTab(tab, "Spectrum")

    def _build_plot_tab(self):
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)

        self.plot = MplCanvas()

        self.get_spectrum_button_2 = QtWidgets.QPushButton("GetSpectrum")
        self.get_spectrum_button_2.clicked.connect(self._GetSpectrum_fired)

        layout.addWidget(self.plot)
        layout.addWidget(self.get_spectrum_button_2)

        self.tabs.addTab(tab, "Plot")

    def _create_main_row(self, name: str) -> QtWidgets.QWidget:
        row = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(row)
        layout.setContentsMargins(4, 4, 4, 4)

        value_label = QtWidgets.QLabel("Wert")
        value_widget = QtWidgets.QLineEdit()
        value_widget.setReadOnly(True)
        value_widget.setMinimumWidth(180)

        new_label = QtWidgets.QLabel("Neu")
        new_widget = self._create_input_widget(self.field_types.get(name, str))
        new_widget.setMinimumWidth(160)

        set_button = QtWidgets.QPushButton(f"Set{name}")
        get_button = QtWidgets.QPushButton(f"Get{name}")

        set_button.clicked.connect(lambda checked=False, n=name: self._call_setter(n))
        get_button.clicked.connect(lambda checked=False, n=name: self._call_getter(n))

        self.value_widgets[name] = value_widget
        self.new_widgets[name] = new_widget

        layout.addWidget(QtWidgets.QLabel(name))
        layout.addSpacing(12)
        layout.addWidget(value_label)
        layout.addWidget(value_widget)
        layout.addSpacing(12)
        layout.addWidget(new_label)
        layout.addWidget(new_widget)
        layout.addSpacing(12)
        layout.addWidget(set_button)
        layout.addWidget(get_button)
        layout.addStretch()

        return row

    def _create_input_widget(self, py_type):
        if py_type is int:
            widget = QtWidgets.QSpinBox()
            widget.setRange(-1_000_000_000, 1_000_000_000)
            return widget

        if py_type is float:
            widget = QtWidgets.QDoubleSpinBox()
            widget.setDecimals(6)
            widget.setRange(-1e15, 1e15)
            widget.setSingleStep(1.0)
            return widget

        return QtWidgets.QLineEdit()

    def _load_ini(self):
        if hasattr(self.ini_source, "read"):
            try:
                content = self.ini_source.read()
            except Exception:
                content = std_ini_text
        else:
            content = str(self.ini_source)

        self.ini_edit.setPlainText(content)

    # ------------------------------------------------------------------
    # Hilfsfunktionen
    # ------------------------------------------------------------------

    def _show_error(self, title, exc):
        QtWidgets.QMessageBox.critical(self, title, str(exc))

    def _get_input_value(self, name):
        widget = self.new_widgets[name]
        if isinstance(widget, QtWidgets.QSpinBox):
            return widget.value()
        if isinstance(widget, QtWidgets.QDoubleSpinBox):
            return widget.value()
        return widget.text()

    def _set_value_display(self, name, value):
        self.value_widgets[name].setText(str(value))

    def _call_getter(self, name):
        try:
            method = getattr(self.sp, f"Get{name}")
            result = method()
            value = result[1] if isinstance(result, (tuple, list)) and len(result) >= 2 else result
            self._set_value_display(name, value)
        except Exception as e:
            self._show_error(f"Get{name}-Fehler", e)

    def _call_setter(self, name):
        try:
            method = getattr(self.sp, f"Set{name}")
            new_value = self._get_input_value(name)
            result = method(new_value)
            value = result[1] if isinstance(result, (tuple, list)) and len(result) >= 2 else result
            self._set_value_display(name, value)
        except Exception as e:
            self._show_error(f"Set{name}-Fehler", e)

    # ------------------------------------------------------------------
    # Entsprechungen der Traits-Methoden
    # ------------------------------------------------------------------

    def _GetSpectrum_fired(self):
        try:
            self.power = self.sp.GetSpectrum()[1]
            x = np.array(self.power[0])
            y = np.array(self.power[1])

            self.plot.update_plot(x, y)
            self.spectrum_edit.setPlainText(f"{self.power[0]}\n\n\n{self.power[1]}")
        except Exception as e:
            self._show_error("GetSpectrum-Fehler", e)

    def _Init_fired(self):
        try:
            ini = io.StringIO(self.ini_edit.toPlainText())
            self.sp.Init(ini)

            for item in self.mainTab:
                self._call_getter(item)
        except Exception as e:
            self._show_error("Init-Fehler", e)

    # ------------------------------------------------------------------
    # Optional wie früher
    # ------------------------------------------------------------------

    def closeEvent(self, event):
        try:
            if hasattr(self.sp, "Quit"):
                self.sp.Quit()
        except Exception:
            pass
        super().closeEvent(event)


def main():
    class DummySpectrumAnalyzer:
        def __init__(self):
            self.values = {
                "CenterFreq": 3e9,
                "Span": 6e9,
                "StartFreq": 100e6,
                "StopFreq": 6e9,
                "RBW": "auto",
                "VBW": "10e6",
                "RefLevel": -20.0,
                "Att": "auto",
                "AttMode": "auto",
                "PreAmp": 0.0,
                "Detector": "APEak",
                "TraceMode": "WRITe",
                "Trace": 1,
                "SweepCount": 0,
                "SweepTime": "10e-3",
                "TriggerMode": "IMMediate",
                "TriggerDelay": 0.0,
                "SweepPoints": 500,
            }

        def Init(self, ini):
            print("Init called")
            print(ini.read())

        def GetSpectrum(self):
            x = np.linspace(100e6, 6e9, 500)
            y = -70 + 8 * np.sin(np.linspace(0, 20, 500))
            return 0, (x.tolist(), y.tolist())

        def Quit(self):
            print("Quit called")

        def __getattr__(self, name):
            if name.startswith("Get"):
                key = name[3:]
                def getter():
                    return 0, self.values[key]
                return getter

            if name.startswith("Set"):
                key = name[3:]
                def setter(value):
                    self.values[key] = value
                    return 0, value
                return setter

            raise AttributeError(name)

    app = QtWidgets.QApplication(sys.argv)
    ui = UI(DummySpectrumAnalyzer())
    ui.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()