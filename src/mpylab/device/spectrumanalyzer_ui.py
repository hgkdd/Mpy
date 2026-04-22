# -*- coding: utf-8 -*-
"""Graphical test utility for spectrum analyzer drivers."""

import argparse
import configparser
import csv
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


class DriverTask(QtCore.QObject):
    """Execute one driver callable in a worker thread."""

    completed = QtCore.Signal(object, object)
    finished = QtCore.Signal()

    def __init__(self, func):
        super().__init__()
        self._func = func

    @QtCore.Slot()
    def run(self):
        result = None
        error = None
        try:
            result = self._func()
        except Exception as exc:
            error = exc
        finally:
            self.completed.emit(result, error)
            self.finished.emit()


class MplCanvas(FigureCanvas):
    """Matplotlib canvas for spectrum data."""

    def __init__(self, parent=None):
        self.figure = Figure(figsize=(7, 4), dpi=100)
        self.ax = self.figure.add_subplot(111)
        self._title = "Spectrum"
        self._grid_enabled = True
        super().__init__(self.figure)
        self.setParent(parent)
        self.update_plot([], [])

    def set_title_text(self, title):
        """Update plot title."""
        self._title = title or "Spectrum"
        self.ax.set_title(self._title)
        self.draw_idle()

    def set_grid_enabled(self, enabled):
        """Enable or disable plot grid."""
        self._grid_enabled = bool(enabled)
        self.ax.grid(self._grid_enabled, alpha=0.35)
        self.draw_idle()

    def update_plot(self, x, y):
        """Redraw spectrum data."""
        self.ax.clear()
        if len(x) and len(y):
            self.ax.plot(x, y, linewidth=1.2)
        else:
            self.ax.text(0.5, 0.5, "No spectrum acquired", ha="center", va="center", transform=self.ax.transAxes)
        self.ax.set_title(self._title)
        self.ax.set_xlabel("Frequency / Hz")
        self.ax.set_ylabel("Amplitude / dBm")
        self.ax.grid(self._grid_enabled, alpha=0.35)
        self.figure.tight_layout()
        self.draw()


class SpectrumAnalyzerWidget(QtWidgets.QWidget):
    """Thread-aware test UI for the common spectrum analyzer driver API."""

    controls = (
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
    choice_fields = {
        "AttMode": ("NORMAL", "LOWNOISE", "LOWDIST"),
        "Detector": ("AUTOSELECT", "AUTOPEAK", "MAXPEAK", "MINPEAK", "SAMPLE", "RMS", "AVERAGE", "DET_QPEAK"),
        "TraceMode": ("WRITE", "VIEW", "AVERAGE", "BLANK", "MAXHOLD", "MINHOLD"),
        "TriggerMode": ("FREE", "VIDEO", "EXTERNAL"),
        "Att": ("auto",),
        "RBW": ("auto",),
    }

    def __init__(self, instance, ini=None, parent=None, use_ini_draft=True):
        super().__init__(parent)
        self.sp = instance
        self.ini_source = ini if ini is not None else io.StringIO(std_ini_text)
        self.use_ini_draft = use_ini_draft
        self.value_widgets = {}
        self.new_widgets = {}
        self.indicators = {}
        self._is_initialized = False
        self._last_error_text = "none"
        self._last_spectrum = None
        self._busy = False
        self._use_worker_threads = False
        self._active_thread = None
        self._active_task = None
        self._task_label = None
        self._task_result = None
        self._task_error = None
        self._task_on_success = None
        self._task_on_error = None
        self._task_on_finished = None

        self.setWindowTitle("Spectrum Analyzer Test Utility")
        self.resize(1250, 900)
        self._build_ui()
        self._load_ini()
        self.log_message("UI ready.")

    def _build_ui(self):
        outer = QtWidgets.QVBoxLayout(self)
        self.tabs = QtWidgets.QTabWidget()
        outer.addWidget(self.tabs)
        self._build_connection_tab()
        self._build_status_tab()
        self._build_controls_tab()
        self._build_spectrum_tab()
        self._build_raw_tab()
        self._build_smoke_tab()
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

        self.refresh_all_button = QtWidgets.QPushButton("Refresh All")
        self.refresh_all_button.clicked.connect(self.refresh_all)
        self.close_button = QtWidgets.QPushButton("Close")
        self.close_button.clicked.connect(self.close)
        bottom.addWidget(self.refresh_all_button)
        bottom.addWidget(self.close_button)
        outer.addLayout(bottom)
        self._refresh_status_bar()

    def _build_connection_tab(self):
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)
        row = QtWidgets.QHBoxLayout()
        self.channel_spin = QtWidgets.QSpinBox()
        self.channel_spin.setMinimum(1)
        self.channel_spin.setMaximum(128)
        self.channel_spin.setValue(1)
        self.init_button = QtWidgets.QPushButton("Init / Re-Init")
        self.init_button.clicked.connect(self.on_init_clicked)
        self.quit_button = QtWidgets.QPushButton("Quit")
        self.quit_button.clicked.connect(self.on_quit_clicked)
        self.load_button = QtWidgets.QPushButton("Load INI")
        self.load_button.clicked.connect(self.on_load_ini_clicked)
        self.save_button = QtWidgets.QPushButton("Save INI")
        self.save_button.clicked.connect(self.on_save_ini_clicked)
        row.addWidget(QtWidgets.QLabel("Channel"))
        row.addWidget(self.channel_spin)
        row.addWidget(self.init_button)
        row.addWidget(self.quit_button)
        row.addWidget(self.load_button)
        row.addWidget(self.save_button)
        row.addStretch()

        self.ini_edit = IniPlainTextEdit()
        self.ini_edit.setMinimumHeight(320)
        layout.addLayout(row)
        layout.addWidget(self.ini_edit)
        self.tabs.addTab(tab, "Connection")

    def _build_status_tab(self):
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)
        top = QtWidgets.QHBoxLayout()
        self.refresh_status_button = QtWidgets.QPushButton("Refresh Status")
        self.refresh_status_button.clicked.connect(self.refresh_status)
        top.addWidget(self.refresh_status_button)
        top.addStretch()
        layout.addLayout(top)

        grid = QtWidgets.QGridLayout()
        self.status_fields = {}
        specs = [
            ("Description", "GetDescription"),
            ("Virtual", "GetVirtual"),
            ("Center Freq", "GetCenterFreq"),
            ("Start Freq", "GetStartFreq"),
            ("Stop Freq", "GetStopFreq"),
            ("Span", "GetSpan"),
            ("RBW", "GetRBW"),
            ("VBW", "GetVBW"),
            ("Ref Level", "GetRefLevel"),
            ("Detector", "GetDetector"),
            ("Trace Mode", "GetTraceMode"),
            ("Last Spectrum", "_last_spectrum"),
        ]
        for idx, (label, key) in enumerate(specs):
            edit = QtWidgets.QLineEdit()
            edit.setReadOnly(True)
            edit.setText("unknown")
            self.status_fields[key] = edit
            row = idx // 2
            col = (idx % 2) * 2
            grid.addWidget(QtWidgets.QLabel(label), row, col)
            grid.addWidget(edit, row, col + 1)
        layout.addLayout(grid)
        layout.addStretch()
        self.tabs.addTab(tab, "Status")

    def _build_controls_tab(self):
        tab = QtWidgets.QWidget()
        outer_layout = QtWidgets.QVBoxLayout(tab)
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        content = QtWidgets.QWidget()
        form_layout = QtWidgets.QVBoxLayout(content)
        for name in self.controls:
            form_layout.addWidget(self._create_control_row(name))
        form_layout.addStretch()
        scroll.setWidget(content)
        outer_layout.addWidget(scroll)
        self.tabs.addTab(tab, "Controls")

    def _build_spectrum_tab(self):
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)

        toolbar = QtWidgets.QHBoxLayout()
        self.get_spectrum_button = QtWidgets.QPushButton("GetSpectrum")
        self.get_spectrum_button.clicked.connect(self.on_get_spectrum_clicked)
        self.get_spectrum_nb_button = QtWidgets.QPushButton("GetSpectrumNB")
        self.get_spectrum_nb_button.clicked.connect(self.on_get_spectrum_nb_clicked)
        self.export_csv_button = QtWidgets.QPushButton("Export CSV")
        self.export_csv_button.clicked.connect(self.on_export_csv_clicked)
        self.title_edit = QtWidgets.QLineEdit("Spectrum")
        self.title_edit.editingFinished.connect(lambda: self.plot.set_title_text(self.title_edit.text()))
        self.grid_button = QtWidgets.QPushButton("Grid On")
        self.grid_button.setCheckable(True)
        self.grid_button.setChecked(True)
        self.grid_button.toggled.connect(self.on_grid_toggled)
        toolbar.addWidget(self.get_spectrum_button)
        toolbar.addWidget(self.get_spectrum_nb_button)
        toolbar.addWidget(self.export_csv_button)
        toolbar.addWidget(QtWidgets.QLabel("Title"))
        toolbar.addWidget(self.title_edit, 1)
        toolbar.addWidget(self.grid_button)
        layout.addLayout(toolbar)

        splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Vertical)
        plot_widget = QtWidgets.QWidget()
        plot_layout = QtWidgets.QVBoxLayout(plot_widget)
        self.plot = MplCanvas()
        self.toolbar = NavigationToolbar(self.plot, self)
        plot_layout.addWidget(self.toolbar)
        plot_layout.addWidget(self.plot)
        self.spectrum_edit = QtWidgets.QPlainTextEdit()
        self.spectrum_edit.setReadOnly(True)
        splitter.addWidget(plot_widget)
        splitter.addWidget(self.spectrum_edit)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)
        layout.addWidget(splitter)
        self.tabs.addTab(tab, "Spectrum")

    def _build_raw_tab(self):
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)
        row = QtWidgets.QHBoxLayout()
        self.raw_command_edit = QtWidgets.QLineEdit()
        self.raw_command_edit.setPlaceholderText("*IDN?")
        self.raw_query_button = QtWidgets.QPushButton("Query")
        self.raw_query_button.clicked.connect(self.on_raw_query_clicked)
        self.raw_write_button = QtWidgets.QPushButton("Write")
        self.raw_write_button.clicked.connect(self.on_raw_write_clicked)
        row.addWidget(self.raw_command_edit, 1)
        row.addWidget(self.raw_query_button)
        row.addWidget(self.raw_write_button)
        self.raw_output = QtWidgets.QPlainTextEdit()
        self.raw_output.setReadOnly(True)
        layout.addLayout(row)
        layout.addWidget(self.raw_output)
        self.tabs.addTab(tab, "Raw Command")

    def _build_smoke_tab(self):
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)
        self.smoke_button = QtWidgets.QPushButton("Run Smoke Test")
        self.smoke_button.clicked.connect(self.on_smoke_clicked)
        self.smoke_output = QtWidgets.QPlainTextEdit()
        self.smoke_output.setReadOnly(True)
        layout.addWidget(QtWidgets.QLabel("Smoke test: Init, status readback, SetCenterFreq, GetSpectrum, Quit."))
        layout.addWidget(self.smoke_button)
        layout.addWidget(self.smoke_output)
        self.tabs.addTab(tab, "Smoke Test")

    def _build_log_tab(self):
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)
        self.log_edit = QtWidgets.QPlainTextEdit()
        self.log_edit.setReadOnly(True)
        self.clear_log_button = QtWidgets.QPushButton("Clear Log")
        self.clear_log_button.clicked.connect(self.log_edit.clear)
        layout.addWidget(self.log_edit)
        layout.addWidget(self.clear_log_button)
        self.tabs.addTab(tab, "Log")

    def _create_control_row(self, name):
        row = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(row)
        layout.setContentsMargins(4, 4, 4, 4)
        value_widget = QtWidgets.QLineEdit()
        value_widget.setReadOnly(True)
        value_widget.setMinimumWidth(170)
        new_widget = self._create_input_widget(name)
        set_button = None
        if isinstance(new_widget, FrequencyControl):
            new_widget.valueApplied.connect(lambda value, n=name: self._call_setter(n, value))
        else:
            set_button = QtWidgets.QPushButton(f"Set{name}")
            set_button.clicked.connect(lambda checked=False, n=name: self._call_setter(n))
        get_button = QtWidgets.QPushButton(f"Get{name}")
        get_button.clicked.connect(lambda checked=False, n=name: self._call_getter(n))
        indicator = QtWidgets.QLabel("unknown")
        indicator.setMinimumWidth(80)
        self.value_widgets[name] = value_widget
        self.new_widgets[name] = new_widget
        self.indicators[name] = indicator
        layout.addWidget(QtWidgets.QLabel(name))
        layout.addWidget(QtWidgets.QLabel("Value"))
        layout.addWidget(value_widget)
        layout.addWidget(QtWidgets.QLabel("New"))
        layout.addWidget(new_widget)
        if set_button is not None:
            layout.addWidget(set_button)
        layout.addWidget(get_button)
        layout.addWidget(indicator)
        layout.addStretch()
        self._set_indicator(name, "unknown")
        return row

    def _create_input_widget(self, name):
        if name in self.frequency_fields:
            return FrequencyControl(default_hz=10e6)
        if name in self.choice_fields:
            widget = QtWidgets.QComboBox()
            widget.addItems(self.choice_fields[name])
            widget.setEditable(True)
            return widget
        py_type = self.field_types.get(name, str)
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
        content = load_ini_with_draft(
            self,
            self.ini_edit,
            self.ini_source,
            std_ini_text,
            SETTINGS_APP,
            use_draft=self.use_ini_draft,
        )
        self._last_ini_text = content

    def log_message(self, message):
        self.log_edit.appendPlainText(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")

    def _refresh_status_bar(self, state_text=None):
        if state_text is None:
            state_text = "Busy" if self._busy else "Ready"
        self.state_label.setText(f"State: {state_text}")
        self.init_label.setText(f"Init: {'initialized' if self._is_initialized else 'not initialized'}")
        self.driver_label.setText(f"Driver: {type(self.sp).__module__}.{type(self.sp).__name__}")
        self.error_label.setText(f"Last error: {self._last_error_text}")

    def _set_busy(self, busy, message=None):
        self._busy = busy
        self.tabs.setEnabled(not busy)
        self.refresh_all_button.setEnabled(not busy)
        self.close_button.setEnabled(not busy)
        self._refresh_status_bar(f"Busy: {message}" if busy and message else "Ready")

    def _start_task(self, label, func, on_success=None, on_error=None, on_finished=None):
        if self._busy:
            QtWidgets.QMessageBox.information(self, "Operation in progress", "Another device operation is still running.")
            return False
        self.log_message(f"{label} started.")
        self._set_busy(True, label)
        if not self._use_worker_threads:
            result = None
            error = None
            try:
                QtWidgets.QApplication.processEvents()
                result = func()
            except Exception as exc:
                error = exc
            finally:
                self._set_busy(False, "Ready")
            self._finish_task(label, result, error, on_success, on_error, on_finished)
            return True

        self._task_label = label
        self._task_result = None
        self._task_error = None
        self._task_on_success = on_success
        self._task_on_error = on_error
        self._task_on_finished = on_finished
        thread = QtCore.QThread(self)
        task = DriverTask(func)
        task.moveToThread(thread)
        thread.started.connect(task.run)
        task.completed.connect(self._handle_task_completed, QtCore.Qt.QueuedConnection)
        task.finished.connect(thread.quit)
        task.finished.connect(task.deleteLater)
        thread.finished.connect(self._handle_task_thread_finished, QtCore.Qt.QueuedConnection)
        thread.finished.connect(thread.deleteLater)
        thread.start()
        self._active_thread = thread
        self._active_task = task
        return True

    @QtCore.Slot(object, object)
    def _handle_task_completed(self, result, error):
        self._task_result = result
        self._task_error = error

    @QtCore.Slot()
    def _handle_task_thread_finished(self):
        label = self._task_label or "Task"
        result = self._task_result
        error = self._task_error
        on_success = self._task_on_success
        on_error = self._task_on_error
        on_finished = self._task_on_finished
        self._active_task = None
        self._active_thread = None
        self._task_label = None
        self._task_result = None
        self._task_error = None
        self._task_on_success = None
        self._task_on_error = None
        self._task_on_finished = None
        self._set_busy(False, "Ready")
        self._finish_task(label, result, error, on_success, on_error, on_finished)

    def _finish_task(self, label, result, error, on_success, on_error, on_finished):
        if error is None:
            self._last_error_text = "none"
            self._refresh_status_bar()
            self.log_message(f"{label} succeeded.")
            if on_success is not None:
                on_success(result)
        else:
            if label == "Init":
                self._is_initialized = False
            self._last_error_text = str(error)
            self._refresh_status_bar()
            self.log_message(f"{label} failed: {type(error).__name__}: {error}")
            if on_error is not None:
                on_error(error)
            else:
                self._show_error(f"{label} Error", error)
        if on_finished is not None:
            on_finished()

    def _show_error(self, title, exc):
        self._last_error_text = str(exc)
        self._refresh_status_bar()
        QtWidgets.QMessageBox.critical(self, title, str(exc))

    def _driver_method(self, method_name, *args, **kwargs):
        method = getattr(self.sp, method_name, None)
        if method is None:
            raise AttributeError(f"Driver does not implement {method_name}()")
        return method(*args, **kwargs)

    def _result_value(self, result):
        return result[1] if isinstance(result, (tuple, list)) and len(result) >= 2 else result

    def _get_input_value(self, name):
        widget = self.new_widgets[name]
        if isinstance(widget, FrequencyControl):
            return widget.value_hz()
        if isinstance(widget, QtWidgets.QComboBox):
            return widget.currentText()
        if isinstance(widget, (QtWidgets.QSpinBox, QtWidgets.QDoubleSpinBox)):
            return widget.value()
        return widget.text()

    def _set_input_value(self, name, value):
        widget = self.new_widgets.get(name)
        if widget is None or value is None:
            return
        if isinstance(widget, FrequencyControl):
            if str(value).strip().lower() == "auto":
                return
            widget.set_value_hz(float(value))
        elif isinstance(widget, QtWidgets.QComboBox):
            text = str(value)
            idx = widget.findText(text, QtCore.Qt.MatchFlag.MatchFixedString)
            if idx < 0:
                widget.addItem(text)
                idx = widget.findText(text, QtCore.Qt.MatchFlag.MatchFixedString)
            widget.setCurrentIndex(idx)
        elif isinstance(widget, QtWidgets.QSpinBox):
            widget.setValue(int(float(value)))
        elif isinstance(widget, QtWidgets.QDoubleSpinBox):
            widget.setValue(float(value))
        else:
            widget.setText(str(value))

    def _set_value_display(self, name, value):
        self.value_widgets[name].setText(str(value))
        self._set_input_value(name, value)

    def _set_indicator(self, name, state, message=None):
        label = self.indicators.get(name)
        if label is None:
            return
        styles = {
            "unknown": ("unknown", "#777777"),
            "pending": ("pending", "#d98c00"),
            "ok": ("match", "#2e8b57"),
            "mismatch": ("mismatch", "#b22222"),
        }
        text, color = styles.get(state, styles["unknown"])
        label.setText(text)
        label.setStyleSheet(f"color: {color}; font-weight: bold;")
        label.setToolTip(message or "")

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
        self._last_spectrum = None
        self._refresh_status_bar()
        self.log_message(f"Driver switched from {type(old_driver).__module__} to {type(self.sp).__module__}.")

    def on_load_ini_clicked(self):
        path, _filter = QtWidgets.QFileDialog.getOpenFileName(self, "Open INI", "", "INI Files (*.ini *.txt);;All Files (*)")
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as handle:
                content = handle.read()
            self.ini_edit.setPlainText(content)
            self._last_ini_text = content
            self.log_message(f"Loaded INI file: {path}")
        except OSError as exc:
            self._show_error("INI Load Error", exc)

    def on_save_ini_clicked(self):
        path, _filter = QtWidgets.QFileDialog.getSaveFileName(self, "Save INI", "", "INI Files (*.ini *.txt);;All Files (*)")
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(self.ini_edit.toPlainText())
            clear_ini_draft(self)
            self.log_message(f"Saved INI file: {path}")
        except OSError as exc:
            self._show_error("INI Save Error", exc)

    def on_init_clicked(self):
        ini_text = self.ini_edit.toPlainText()
        self._last_ini_text = ini_text
        channel = self.channel_spin.value()
        try:
            self._select_driver_from_ini(ini_text)
        except Exception as exc:
            self._show_error("Driver Selection Error", exc)
            return

        def success(err):
            self._is_initialized = (err == 0)
            self._last_error_text = "none" if err == 0 else self._last_error_text
            self._refresh_status_bar()
            self.log_message(f"Init returned: {err}")
            self.refresh_all()

        self._start_task("Init", lambda: self._driver_method("Init", io.StringIO(ini_text), channel), on_success=success)

    def on_quit_clicked(self):
        def success(result):
            self._is_initialized = False
            self._refresh_status_bar()
            self.log_message(f"Quit returned: {result}")

        self._start_task("Quit", lambda: self._driver_method("Quit"), on_success=success)

    def refresh_status(self, on_complete=None):
        getters = ["GetDescription", "GetVirtual", "GetCenterFreq", "GetStartFreq", "GetStopFreq", "GetSpan", "GetRBW", "GetVBW", "GetRefLevel", "GetDetector", "GetTraceMode"]

        def task():
            snapshot = {}
            for getter in getters:
                method = getattr(self.sp, getter, None)
                if method is None:
                    snapshot[getter] = "not implemented"
                    continue
                try:
                    snapshot[getter] = method()
                except Exception as exc:
                    snapshot[getter] = f"{type(exc).__name__}: {exc}"
            snapshot["_last_spectrum"] = self._spectrum_summary()
            return snapshot

        def success(snapshot):
            for key, value in snapshot.items():
                field = self.status_fields.get(key)
                if field is not None:
                    field.setText(str(value))
            self._populate_controls(snapshot)
            if on_complete is not None:
                on_complete()

        self._start_task("Refresh Status", task, on_success=success)

    def refresh_all(self):
        self.refresh_status(on_complete=self.refresh_controls)

    def refresh_controls(self):
        covered = {"CenterFreq", "StartFreq", "StopFreq", "Span", "RBW", "VBW", "RefLevel", "Detector", "TraceMode"}
        names = [name for name in self.controls if name not in covered]

        def task():
            values = {}
            for name in names:
                method = getattr(self.sp, f"Get{name}", None)
                if method is None:
                    continue
                try:
                    values[name] = method()
                except Exception as exc:
                    values[name] = exc
            return values

        def success(values):
            for name, result in values.items():
                if isinstance(result, Exception):
                    self._set_indicator(name, "unknown", str(result))
                    continue
                value = self._result_value(result)
                try:
                    self._set_value_display(name, value)
                    self._set_indicator(name, "ok")
                except Exception as exc:
                    self._set_indicator(name, "unknown", str(exc))

        self._start_task("Refresh Controls", task, on_success=success)

    def _populate_controls(self, snapshot):
        mapping = {
            "CenterFreq": "GetCenterFreq",
            "StartFreq": "GetStartFreq",
            "StopFreq": "GetStopFreq",
            "Span": "GetSpan",
            "RBW": "GetRBW",
            "VBW": "GetVBW",
            "RefLevel": "GetRefLevel",
            "Detector": "GetDetector",
            "TraceMode": "GetTraceMode",
        }
        for name, getter in mapping.items():
            value = self._result_value(snapshot.get(getter))
            if value is None or isinstance(value, str) and value.endswith("not implemented"):
                continue
            try:
                self._set_value_display(name, value)
                self._set_indicator(name, "ok")
            except Exception:
                pass

    def _call_getter(self, name, show_errors=True):
        def success(result):
            value = self._result_value(result)
            self._set_value_display(name, value)
            self._set_indicator(name, "ok")

        self._set_indicator(name, "pending")
        return self._start_task(
            f"Get{name}",
            lambda: self._driver_method(f"Get{name}"),
            on_success=success,
            on_error=None if show_errors else lambda exc: self._set_indicator(name, "unknown", str(exc)),
        )

    def _call_setter(self, name, value=None):
        input_value = self._get_input_value(name) if value is None else value
        self._set_indicator(name, "pending")

        def success(result):
            readback = self._result_value(result)
            self._set_value_display(name, readback)
            if self._values_match(name, input_value, readback):
                self._set_indicator(name, "ok")
            else:
                self._set_indicator(name, "mismatch", f"expected {input_value}, got {readback}")

        self._start_task(f"Set{name}", lambda: self._driver_method(f"Set{name}", input_value), on_success=success)

    def _values_match(self, name, expected, actual):
        if name in self.frequency_fields or self.field_types.get(name) in (float, int):
            try:
                expected_f = float(expected)
                actual_f = float(actual)
                return abs(expected_f - actual_f) <= max(1e-9, abs(expected_f) * 1e-9)
            except (TypeError, ValueError):
                return str(expected).strip().lower() == str(actual).strip().lower()
        return str(expected).strip().lower() == str(actual).strip().lower()

    def on_get_spectrum_clicked(self):
        self._start_task("GetSpectrum", lambda: self._driver_method("GetSpectrum"), on_success=self._handle_spectrum)

    def on_get_spectrum_nb_clicked(self):
        self._start_task("GetSpectrumNB", lambda: self._driver_method("GetSpectrumNB"), on_success=self._handle_spectrum)

    def _handle_spectrum(self, result):
        power = self._result_value(result)
        if power is None or len(power) != 2:
            raise ValueError(f"GetSpectrum must return (x, y), got {power!r}")
        x = np.array(power[0], dtype=float)
        y = np.array(power[1], dtype=float)
        if len(x) == 0 or len(y) == 0:
            raise ValueError("GetSpectrum returned no data")
        self._last_spectrum = (x.tolist(), y.tolist())
        self.plot.update_plot(x, y)
        self.spectrum_edit.setPlainText("\n".join(f"{fx:.12g}, {fy:.12g}" for fx, fy in zip(x, y)))
        self.status_fields["_last_spectrum"].setText(self._spectrum_summary())
        self.log_message(f"Spectrum acquired: {len(x)} points.")

    def _spectrum_summary(self):
        if not self._last_spectrum:
            return "none"
        x, _y = self._last_spectrum
        return f"{len(x)} points, {x[0]:g} Hz .. {x[-1]:g} Hz"

    def on_export_csv_clicked(self):
        if not self._last_spectrum:
            self._show_error("Export CSV Error", ValueError("No spectrum acquired"))
            return
        path, _filter = QtWidgets.QFileDialog.getSaveFileName(self, "Export Spectrum CSV", "", "CSV Files (*.csv);;All Files (*)")
        if not path:
            return
        try:
            x, y = self._last_spectrum
            with open(path, "w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(["frequency_hz", "amplitude_dbm"])
                writer.writerows(zip(x, y))
            self.log_message(f"Exported spectrum CSV: {path}")
        except OSError as exc:
            self._show_error("Export CSV Error", exc)

    def on_grid_toggled(self, checked):
        self.grid_button.setText("Grid On" if checked else "Grid Off")
        self.plot.set_grid_enabled(checked)

    def on_raw_query_clicked(self):
        cmd = self.raw_command_edit.text().strip()
        if not cmd:
            return
        if not hasattr(self.sp, "query"):
            self._show_error("Raw Query Error", AttributeError("driver did not expose query"))
            return
        self._start_task("Raw Query", lambda: self.sp.query(cmd), on_success=lambda result: self.raw_output.appendPlainText(f"> {cmd}\n{result}"))

    def on_raw_write_clicked(self):
        cmd = self.raw_command_edit.text().strip()
        if not cmd:
            return
        if not hasattr(self.sp, "write"):
            self._show_error("Raw Write Error", AttributeError("driver did not expose write"))
            return
        self._start_task("Raw Write", lambda: self.sp.write(cmd), on_success=lambda result: self.raw_output.appendPlainText(f"> {cmd}\n{result}"))

    def on_smoke_clicked(self):
        ini_text = self.ini_edit.toPlainText()
        channel = self.channel_spin.value()
        try:
            self._select_driver_from_ini(ini_text)
        except Exception as exc:
            self._show_error("Driver Selection Error", exc)
            return

        def task():
            lines = [f"Init: {self.sp.Init(io.StringIO(ini_text), channel)}"]
            for getter in ("GetDescription", "GetCenterFreq", "GetSpan", "GetRBW", "GetVBW", "GetDetector"):
                if hasattr(self.sp, getter):
                    lines.append(f"{getter}: {getattr(self.sp, getter)()!r}")
            lines.append(f"SetCenterFreq(1e9): {self.sp.SetCenterFreq(1e9)!r}")
            spectrum = self.sp.GetSpectrum()
            value = self._result_value(spectrum)
            lines.append(f"GetSpectrum: {len(value[0]) if value and len(value) == 2 else 'invalid'} points")
            if hasattr(self.sp, "Quit"):
                lines.append(f"Quit: {self.sp.Quit()!r}")
            return "\n".join(lines)

        def success(output):
            self.smoke_output.setPlainText(output)
            self._is_initialized = False
            self._refresh_status_bar()

        self._start_task("Smoke Test", task, on_success=success)

    def closeEvent(self, event):
        if self._active_thread is not None and self._active_thread.isRunning():
            event.ignore()
            QtWidgets.QMessageBox.information(self, "Operation in progress", "Close after current operation.")
            return
        try:
            if hasattr(self.sp, "Quit"):
                self.sp.Quit()
                self.log_message("Driver Quit sent.")
        except Exception as exc:
            self.log_message(f"Driver Quit failed: {type(exc).__name__}: {exc}")
        super().closeEvent(event)


UI = SpectrumAnalyzerWidget


def _make_default_instance(args):
    ini = io.StringIO(std_ini_text.replace("virtual: 1", "virtual: 1" if args.virtual else "virtual: 0"))
    if not args.virtual:
        print("Driver will be selected from the INI file on Init. Using virtual spectrum analyzer until then.")
    return VIRTUAL_SPECTRUMANALYZER(), ini


def main(argv=None):
    parser = argparse.ArgumentParser(description="Spectrum analyzer driver test utility")
    parser.add_argument("ini", nargs="?", help="Optional path to an INI file.")
    parser.add_argument("--virtual", action="store_true", help="Use the virtual spectrum analyzer driver.")
    parser.add_argument(
        "--threaded",
        action="store_true",
        help="Run driver calls in worker threads. Disabled by default for VISA backend stability.",
    )
    args = parser.parse_args(argv)

    dev, ini = _make_default_instance(args)
    if args.ini:
        try:
            with open(args.ini, "r", encoding="utf-8") as handle:
                ini = io.StringIO(handle.read())
        except OSError as exc:
            print(f"INI file could not be read: {exc}")
            return 1

    app = QtWidgets.QApplication(sys.argv if argv is None else [sys.argv[0], *argv])
    ui = SpectrumAnalyzerWidget(dev, ini=ini, use_ini_draft=not args.virtual)
    ui._use_worker_threads = args.threaded
    ui.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
