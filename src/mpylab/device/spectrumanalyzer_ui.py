# -*- coding: utf-8 -*-
"""Graphical test utility for spectrum analyzer drivers."""

import argparse
import configparser
import importlib
import io
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
from PySide6 import QtCore, QtWidgets

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure

from mpylab.device.spectrumanalyzer_virtual import SPECTRUMANALYZER as VIRTUAL_SPECTRUMANALYZER
from mpylab.device.ui_frequency import FrequencyControl
from mpylab.device.ui_ini_draft import IniPlainTextEdit, clear_ini_draft, load_ini_with_draft
from mpylab.tools.configuration import parse_ini_value, strbool
from mpylab.tools.util import format_block


SETTINGS_APP = "spectrumanalyzer_ui"


std_ini_text = format_block("""
                [DESCRIPTION]
                description: Virtual SpectrumAnalyzer
                type:        SPECTRUMANALYZER
                vendor:      mpylab
                serialnr:
                deviceid:
                driver:      spectrumanalyzer_virtual.py

                [Init_Value]
                fstart: 100e6
                fstop: 6e9
                fstep: 1
                gpib: 20
                virtual: 1
                nr_of_channels: 1

                [Channel_1]
                unit: dBm
                attenuation: auto
                reflevel: -20
                rbw: auto
                vbw: 10e6
                span: 5.9e9
                trace: 1
                tracemode: WRITE
                detector: AUTOPEAK
                sweepcount: 0
                triggermode: FREE
                attmode: NORMAL
                sweeptime: 10e-3
                sweeppoints: 500
                """).strip()


class MplCanvas(FigureCanvas):
    def __init__(self, parent=None):
        self.figure = Figure(figsize=(7, 4), dpi=100)
        self.ax = self.figure.add_subplot(111)
        super().__init__(self.figure)
        self.setParent(parent)
        self.update_plot([], [])

    def update_plot(self, x, y):
        self.ax.clear()
        self.ax.plot(x, y, linewidth=1.2)
        self.ax.set_title("Spectrum")
        self.ax.set_xlabel("Frequency / Hz")
        self.ax.set_ylabel("Amplitude / dBm")
        self.ax.grid(True, alpha=0.35)
        self.figure.tight_layout()
        self.draw()


class UI(QtWidgets.QWidget):
    mainTab = (
        "CenterFreq", "Span", "StartFreq", "StopFreq", "RBW", "VBW",
        "RefLevel", "Att", "AttMode", "PreAmp", "Detector", "TraceMode",
        "Trace", "SweepCount", "SweepTime", "TriggerMode", "TriggerDelay", "SweepPoints",
    )

    field_types = {
        "CenterFreq": float,
        "Span": float,
        "StartFreq": float,
        "StopFreq": float,
        "RBW": str,
        "VBW": float,
        "RefLevel": float,
        "Att": str,
        "AttMode": str,
        "PreAmp": float,
        "Detector": str,
        "TraceMode": str,
        "Trace": int,
        "SweepCount": int,
        "SweepTime": float,
        "TriggerMode": str,
        "TriggerDelay": float,
        "SweepPoints": int,
    }
    frequency_fields = {"CenterFreq", "Span", "StartFreq", "StopFreq", "RBW", "VBW"}

    def __init__(self, instance, ini=None, parent=None, use_ini_draft=True):
        super().__init__(parent)
        self.sp = instance
        self.ini_source = ini if ini is not None else io.StringIO(std_ini_text)
        self.use_ini_draft = use_ini_draft
        self.value_widgets = {}
        self.new_widgets = {}
        self._is_initialized = False
        self._last_error_text = "none"
        self.power = None

        self.setWindowTitle("Spectrum Analyzer Test Utility")
        self.resize(1200, 850)
        self._build_ui()
        self._load_ini()
        self._refresh_status_bar()
        self.log_message("UI ready.")

    def _build_ui(self):
        outer = QtWidgets.QVBoxLayout(self)
        self.tabs = QtWidgets.QTabWidget()
        outer.addWidget(self.tabs)
        self._build_ini_tab()
        self._build_status_tab()
        self._build_main_tab()
        self._build_spectrum_tab()
        self._build_plot_tab()
        self._build_log_tab()

        bottom = QtWidgets.QHBoxLayout()
        self.state_label = QtWidgets.QLabel()
        self.init_label = QtWidgets.QLabel()
        self.driver_label = QtWidgets.QLabel()
        self.error_label = QtWidgets.QLabel()
        self.error_label.setMinimumWidth(300)
        self.error_label.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        bottom.addWidget(self.state_label)
        bottom.addSpacing(10)
        bottom.addWidget(self.init_label)
        bottom.addSpacing(10)
        bottom.addWidget(self.driver_label)
        bottom.addSpacing(10)
        bottom.addWidget(self.error_label, 1)
        self.refresh_button = QtWidgets.QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.refresh_status)
        self.close_button = QtWidgets.QPushButton("Close")
        self.close_button.clicked.connect(self.close)
        bottom.addWidget(self.refresh_button)
        bottom.addWidget(self.close_button)
        outer.addLayout(bottom)

    def _build_ini_tab(self):
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)
        row = QtWidgets.QHBoxLayout()
        self.init_button = QtWidgets.QPushButton("Init / Re-Init")
        self.init_button.clicked.connect(self.on_init_clicked)
        self.load_button = QtWidgets.QPushButton("Load INI")
        self.load_button.clicked.connect(self.on_load_ini_clicked)
        self.save_button = QtWidgets.QPushButton("Save INI")
        self.save_button.clicked.connect(self.on_save_ini_clicked)
        row.addWidget(self.init_button)
        row.addWidget(self.load_button)
        row.addWidget(self.save_button)
        row.addStretch()
        self.ini_edit = IniPlainTextEdit()
        self.ini_edit.setMinimumHeight(260)
        layout.addLayout(row)
        layout.addWidget(self.ini_edit)
        self.tabs.addTab(tab, "Ini")

    def _build_status_tab(self):
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QFormLayout(tab)
        self.description_edit = QtWidgets.QLineEdit()
        self.description_edit.setReadOnly(True)
        self.virtual_edit = QtWidgets.QLineEdit()
        self.virtual_edit.setReadOnly(True)
        self.last_spectrum_edit = QtWidgets.QLineEdit()
        self.last_spectrum_edit.setReadOnly(True)
        layout.addRow("Description", self.description_edit)
        layout.addRow("Virtual", self.virtual_edit)
        layout.addRow("Last Spectrum", self.last_spectrum_edit)
        self.tabs.addTab(tab, "Status")

    def _build_main_tab(self):
        tab = QtWidgets.QWidget()
        outer_layout = QtWidgets.QVBoxLayout(tab)
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        content = QtWidgets.QWidget()
        form_layout = QtWidgets.QVBoxLayout(content)
        for name in self.mainTab:
            form_layout.addWidget(self._create_main_row(name))
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
        self.get_spectrum_button_1.clicked.connect(self.on_get_spectrum_clicked)
        layout.addWidget(self.spectrum_edit)
        layout.addWidget(self.get_spectrum_button_1)
        self.tabs.addTab(tab, "Spectrum")

    def _build_plot_tab(self):
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)
        self.plot = MplCanvas()
        self.toolbar = NavigationToolbar(self.plot, self)
        self.get_spectrum_button_2 = QtWidgets.QPushButton("GetSpectrum")
        self.get_spectrum_button_2.clicked.connect(self.on_get_spectrum_clicked)
        layout.addWidget(self.toolbar)
        layout.addWidget(self.plot)
        layout.addWidget(self.get_spectrum_button_2)
        self.tabs.addTab(tab, "Plot")

    def _build_log_tab(self):
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)
        self.log_edit = QtWidgets.QPlainTextEdit()
        self.log_edit.setReadOnly(True)
        layout.addWidget(self.log_edit)
        self.tabs.addTab(tab, "Log")

    def _create_main_row(self, name):
        row = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(row)
        layout.setContentsMargins(4, 4, 4, 4)
        value_widget = QtWidgets.QLineEdit()
        value_widget.setReadOnly(True)
        value_widget.setMinimumWidth(180)
        new_widget = self._create_input_widget(name, self.field_types.get(name, str))
        new_widget.setMinimumWidth(160)
        set_button = QtWidgets.QPushButton(f"Set{name}")
        get_button = QtWidgets.QPushButton(f"Get{name}")
        if isinstance(new_widget, FrequencyControl):
            new_widget.valueApplied.connect(lambda value, n=name: self._call_setter(n, value))
        set_button.clicked.connect(lambda checked=False, n=name: self._call_setter(n))
        get_button.clicked.connect(lambda checked=False, n=name: self._call_getter(n))
        self.value_widgets[name] = value_widget
        self.new_widgets[name] = new_widget
        layout.addWidget(QtWidgets.QLabel(name))
        layout.addSpacing(12)
        layout.addWidget(QtWidgets.QLabel("Value"))
        layout.addWidget(value_widget)
        layout.addSpacing(12)
        layout.addWidget(QtWidgets.QLabel("New"))
        layout.addWidget(new_widget)
        layout.addSpacing(12)
        layout.addWidget(set_button)
        layout.addWidget(get_button)
        layout.addStretch()
        return row

    def _create_input_widget(self, name, py_type):
        if name in self.frequency_fields:
            return FrequencyControl(default_hz=10e6)
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
        load_ini_with_draft(
            self,
            self.ini_edit,
            self.ini_source,
            std_ini_text,
            SETTINGS_APP,
            use_draft=self.use_ini_draft,
        )

    def log_message(self, message):
        self.log_edit.appendPlainText(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")

    def _refresh_status_bar(self):
        self.state_label.setText("State: Ready")
        self.init_label.setText(f"Init: {'initialized' if self._is_initialized else 'not initialized'}")
        self.driver_label.setText(f"Driver: {type(self.sp).__module__}.{type(self.sp).__name__}")
        self.error_label.setText(f"Last error: {self._last_error_text}")

    def _show_error(self, title, exc):
        self._last_error_text = str(exc)
        self._refresh_status_bar()
        self.log_message(f"{title}: {type(exc).__name__}: {exc}")
        QtWidgets.QMessageBox.critical(self, title, str(exc))

    def _result_value(self, result):
        return result[1] if isinstance(result, (tuple, list)) and len(result) >= 2 else result

    def _get_input_value(self, name):
        widget = self.new_widgets[name]
        if isinstance(widget, FrequencyControl):
            return widget.value_hz()
        if isinstance(widget, (QtWidgets.QSpinBox, QtWidgets.QDoubleSpinBox)):
            return widget.value()
        return widget.text()

    def _set_input_value(self, name, value):
        widget = self.new_widgets.get(name)
        if widget is None:
            return
        if isinstance(widget, QtWidgets.QSpinBox):
            widget.setValue(int(float(value)))
        elif isinstance(widget, FrequencyControl):
            if str(value).strip().lower() == "auto":
                return
            widget.set_value_hz(float(value))
        elif isinstance(widget, QtWidgets.QDoubleSpinBox):
            widget.setValue(float(value))
        else:
            widget.setText(str(value))

    def _set_value_display(self, name, value):
        self.value_widgets[name].setText(str(value))
        self._set_input_value(name, value)

    def _ini_driver_settings(self, ini_text):
        config = configparser.ConfigParser()
        config.read_file(io.StringIO(ini_text))
        description = {}
        init_value = {}
        for section in config.sections():
            key = section.strip().lower()
            if key == "description":
                description = {name.lower(): parse_ini_value(value) for name, value in config.items(section)}
            elif key == "init_value":
                init_value = {name.lower(): parse_ini_value(value) for name, value in config.items(section)}
        driver = str(description.get("driver", "") or "").strip()
        virtual = strbool(init_value.get("virtual", False))
        return driver, virtual

    def _module_name_from_driver(self, driver, virtual):
        if virtual or not driver or Path(driver).with_suffix("").name.lower() == "dummy":
            return "spectrumanalyzer_virtual"
        module_name = Path(driver).with_suffix("").name
        if module_name == "sp_rs_zvl":
            return "sa_rs_zvl"
        return module_name

    def _instantiate_driver(self, module_name):
        module = importlib.import_module(f"mpylab.device.{module_name}")
        driver_cls = getattr(module, "SPECTRUMANALYZER")
        search_paths = getattr(self.sp, "SearchPaths", None)
        if search_paths is not None:
            try:
                return driver_cls(SearchPaths=search_paths)
            except TypeError:
                pass
        return driver_cls()

    def _select_driver_from_ini(self, ini_text):
        driver, virtual = self._ini_driver_settings(ini_text)
        module_name = self._module_name_from_driver(driver, virtual)
        current_module = type(self.sp).__module__.split(".")[-1]
        if current_module == module_name:
            return
        old_driver = self.sp
        self.sp = self._instantiate_driver(module_name)
        self._is_initialized = False
        self.log_message(f"Driver switched from {type(old_driver).__module__} to {type(self.sp).__module__}.")
        self._refresh_status_bar()

    def on_load_ini_clicked(self):
        path, _filter = QtWidgets.QFileDialog.getOpenFileName(
            self, "Open INI", "", "INI Files (*.ini *.txt);;All Files (*)"
        )
        if not path:
            return
        with open(path, "r", encoding="utf-8") as handle:
            self.ini_edit.setPlainText(handle.read())
        self.log_message(f"Loaded INI file: {path}")

    def on_save_ini_clicked(self):
        path, _filter = QtWidgets.QFileDialog.getSaveFileName(
            self, "Save INI", "", "INI Files (*.ini *.txt);;All Files (*)"
        )
        if not path:
            return
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(self.ini_edit.toPlainText())
        clear_ini_draft(self)
        self.log_message(f"Saved INI file: {path}")

    def on_init_clicked(self):
        ini_text = self.ini_edit.toPlainText()
        try:
            self._select_driver_from_ini(ini_text)
            err = self.sp.Init(io.StringIO(ini_text))
            self._is_initialized = (err == 0)
            self._last_error_text = "none"
            self.refresh_status()
            for item in self.mainTab:
                self._call_getter(item, show_errors=False)
            self.log_message(f"Init returned: {err}")
            self._refresh_status_bar()
        except Exception as exc:
            self._is_initialized = False
            self._show_error("Init Error", exc)

    def refresh_status(self):
        try:
            self.description_edit.setText(str(self._result_value(self.sp.GetDescription())))
            get_virtual = getattr(self.sp, "GetVirtual", None)
            self.virtual_edit.setText(str(self._result_value(get_virtual())) if get_virtual else "unknown")
            self._last_error_text = "none"
            self._refresh_status_bar()
        except Exception as exc:
            self._show_error("Refresh Status Error", exc)

    def _call_getter(self, name, show_errors=True):
        try:
            method = getattr(self.sp, f"Get{name}")
            value = self._result_value(method())
            self._set_value_display(name, value)
            return value
        except Exception as exc:
            if show_errors:
                self._show_error(f"Get{name} Error", exc)
            return None

    def _call_setter(self, name, value=None):
        try:
            method = getattr(self.sp, f"Set{name}")
            input_value = self._get_input_value(name) if value is None else value
            result_value = self._result_value(method(input_value))
            self._set_value_display(name, result_value)
            self._last_error_text = "none"
            self._refresh_status_bar()
        except Exception as exc:
            self._show_error(f"Set{name} Error", exc)

    def on_get_spectrum_clicked(self):
        try:
            result = self.sp.GetSpectrum()
            self.power = self._result_value(result)
            if self.power is None or len(self.power) != 2:
                raise ValueError(f"GetSpectrum must return (x, y), got {self.power!r}")
            x = np.array(self.power[0], dtype=float)
            y = np.array(self.power[1], dtype=float)
            self.plot.update_plot(x, y)
            self.spectrum_edit.setPlainText(f"{self.power[0]}\n\n{self.power[1]}")
            self.last_spectrum_edit.setText(f"{len(x)} points, {x[0]:g} Hz .. {x[-1]:g} Hz")
            self._last_error_text = "none"
            self._refresh_status_bar()
            self.log_message(f"Spectrum acquired: {len(x)} points.")
        except Exception as exc:
            self._show_error("GetSpectrum Error", exc)

    def closeEvent(self, event):
        try:
            if hasattr(self.sp, "Quit"):
                self.sp.Quit()
                self.log_message("Driver Quit sent.")
        except Exception as exc:
            self.log_message(f"Driver Quit failed: {type(exc).__name__}: {exc}")
        super().closeEvent(event)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Spectrum analyzer driver test utility")
    parser.add_argument("--ini", help="Path to an INI file to preload")
    parser.add_argument("--virtual", action="store_true", help="Use the virtual spectrum analyzer driver")
    parser.add_argument("--threaded", action="store_true", help="Accepted for consistency; spectrum analyzer calls run synchronously")
    args = parser.parse_args(argv)

    if args.virtual:
        dev = VIRTUAL_SPECTRUMANALYZER()
        ini = io.StringIO(std_ini_text)
    else:
        dev = VIRTUAL_SPECTRUMANALYZER()
        ini = args.ini if args.ini else io.StringIO(std_ini_text)
        print("Driver will be selected from the INI file on Init. Using virtual spectrum analyzer until then.")

    app = QtWidgets.QApplication(sys.argv if argv is None else [sys.argv[0], *argv])
    ui = UI(dev, ini=ini, use_ini_draft=not args.virtual)
    ui.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
