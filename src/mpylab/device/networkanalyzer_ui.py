# -*- coding: utf-8 -*-

import csv
import io
import sys
from datetime import datetime

import numpy as np
from PySide6 import QtCore, QtWidgets

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure

from mpylab.tools.util import format_block
from mpylab.device.ui_frequency import FrequencyControl
from mpylab.device.ui_ini_draft import IniPlainTextEdit, clear_ini_draft, load_ini_with_draft

std_ini_text = format_block("""
                [DESCRIPTION]
                description: nw template
                type:        'Networkanalyser'
                vendor:      some company
                serialnr:    SN12345
                deviceid:    internal ID
                driver:      dummy.py

                [Init_Value]
                fstart: 100e6
                fstop: 6e9
                fstep: 1
                gpib: 18
                virtual: 0

                [Channel_1]
                unit: 'dBm'
                SetRefLevel: 0
                SetRBW: 10e3
                SetSpan: 5999991000
                CreateWindow: 'default'
                CreateTrace: 'default','S11'
                SetSweepCount: 1
                SetSweepPoints: 50
                SetSweepType: 'LINEAR'
                """).strip()
SETTINGS_APP = "networkanalyzer_ui"


class DriverTask(QtCore.QObject):
    """Execute one driver-related callable inside a dedicated Qt thread."""

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
    """Matplotlib canvas used to display the currently acquired spectrum."""

    def __init__(self, parent=None):
        self.figure = Figure(facecolor="#f3f4f6")
        self.ax = self.figure.add_subplot(111)
        self._plot_title = "Trace Data"
        self._y_label = "Amplitude"
        self._grid_enabled = False
        super().__init__(self.figure)
        self.setParent(parent)
        self.ax.set_facecolor("#ffffff")
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Expanding,
        )
        self.updateGeometry()
        self._configure_axes(show_placeholder=True)
        self.draw()

    def _configure_axes(self, show_placeholder=False):
        self.ax.set_title(self._plot_title)
        self.ax.set_xlabel("Frequency in Hz")
        self.ax.set_ylabel(self._y_label)
        self.ax.grid(self._grid_enabled)
        for spine in self.ax.spines.values():
            spine.set_color("#666666")
        if show_placeholder:
            self.ax.text(
                0.5,
                0.5,
                "No spectrum acquired",
                transform=self.ax.transAxes,
                ha="center",
                va="center",
                color="#666666",
            )

    def set_plot_title(self, title):
        """Update the plot title and redraw the canvas."""
        self._plot_title = title or "Trace Data"
        self._configure_axes()
        self.draw_idle()

    def set_y_label(self, label):
        """Update the Y-axis label and redraw the canvas."""
        self._y_label = label or "Amplitude"
        self._configure_axes()
        self.draw_idle()

    def set_grid_enabled(self, enabled):
        """Enable or disable the plot grid."""
        self._grid_enabled = bool(enabled)
        self._configure_axes()
        self.draw_idle()

    def update_spectrum(self, x, y, logarithmic=False):
        """Redraw the spectrum plot with the provided x/y arrays."""
        self.ax.clear()
        self.ax.plot(x, y, linewidth=1.2)
        self._configure_axes()
        self.ax.set_xscale("log" if logarithmic else "linear")
        self.ax.relim()
        self.ax.autoscale_view()
        self.draw()

    def clear_plot(self):
        """Clear the current plot contents."""
        self.ax.clear()
        self._configure_axes(show_placeholder=True)
        self.draw()


class NetworkAnalyzerWidget(QtWidgets.QWidget):
    """Generic graphical test utility for network analyzer style drivers."""

    def __init__(self, instance, ini=None, parent=None, use_ini_draft=True):
        super().__init__(parent)

        self.dv = instance
        self.ini_source = ini if ini is not None else io.StringIO(std_ini_text)
        self.use_ini_draft = use_ini_draft
        self.power = ()
        self._last_ini_text = ""
        self._status_fields = {}
        self._status_raw = {}
        self._control_widgets = {}
        self._control_specs = {}
        self._last_trace_data = None
        self._last_spectrum_summary = None
        self._busy = False
        self._active_thread = None
        self._active_task = None
        self._task_label = None
        self._task_result = None
        self._task_error = None
        self._task_on_success = None
        self._task_on_error = None
        self._task_on_finished = None
        self._use_worker_threads = False
        self._is_initialized = False
        self._last_error_text = "none"
        self._default_plot_title = "Trace Data"

        self.setWindowTitle("Network Analyzer Test Utility")
        self.resize(1280, 900)

        self._build_ui()
        self._load_ini()
        self.log_message("UI ready.")

    def _build_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)

        self.tabs = QtWidgets.QTabWidget()
        main_layout.addWidget(self.tabs)

        self._build_connection_tab()
        self._build_status_tab()
        self._build_controls_tab()
        self._build_spectrum_tab()
        self._build_log_tab()

        bottom_bar = QtWidgets.QHBoxLayout()
        self.state_label = QtWidgets.QLabel()
        self.init_state_label = QtWidgets.QLabel()
        self.driver_label = QtWidgets.QLabel()
        self.last_error_label = QtWidgets.QLabel()
        self.last_error_label.setMinimumWidth(280)
        self.last_error_label.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        bottom_bar.addWidget(self.state_label)
        bottom_bar.addSpacing(12)
        bottom_bar.addWidget(self.init_state_label)
        bottom_bar.addSpacing(12)
        bottom_bar.addWidget(self.driver_label)
        bottom_bar.addSpacing(12)
        bottom_bar.addWidget(self.last_error_label, 1)
        bottom_bar.addStretch()

        self.refresh_all_button = QtWidgets.QPushButton("Refresh All")
        self.refresh_all_button.clicked.connect(self.refresh_all)
        bottom_bar.addWidget(self.refresh_all_button)

        self.close_button = QtWidgets.QPushButton("Close")
        self.close_button.clicked.connect(self.close)
        bottom_bar.addWidget(self.close_button)

        main_layout.addLayout(bottom_bar)
        self._refresh_status_bar()

    def _build_connection_tab(self):
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)

        top_row = QtWidgets.QHBoxLayout()
        self.channel_spin = QtWidgets.QSpinBox()
        self.channel_spin.setMinimum(1)
        self.channel_spin.setMaximum(128)
        self.channel_spin.setValue(1)

        self.init_button = QtWidgets.QPushButton("Init / Re-Init")
        self.init_button.clicked.connect(self.on_init_clicked)

        self.load_ini_button = QtWidgets.QPushButton("Load INI File")
        self.load_ini_button.clicked.connect(self.on_load_ini_clicked)

        self.save_ini_button = QtWidgets.QPushButton("Save INI File")
        self.save_ini_button.clicked.connect(self.on_save_ini_clicked)

        top_row.addWidget(QtWidgets.QLabel("Channel"))
        top_row.addWidget(self.channel_spin)
        top_row.addWidget(self.init_button)
        top_row.addWidget(self.load_ini_button)
        top_row.addWidget(self.save_ini_button)
        top_row.addStretch()

        self.ini_edit = IniPlainTextEdit()
        self.ini_edit.setMinimumHeight(320)

        layout.addLayout(top_row)
        layout.addWidget(self.ini_edit)
        self.tabs.addTab(tab, "Connection")

    def _build_status_tab(self):
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)

        refresh_row = QtWidgets.QHBoxLayout()
        self.refresh_status_button = QtWidgets.QPushButton("Refresh Status")
        self.refresh_status_button.clicked.connect(self.refresh_status)
        refresh_row.addWidget(self.refresh_status_button)
        refresh_row.addStretch()
        layout.addLayout(refresh_row)

        status_grid = QtWidgets.QGridLayout()
        status_specs = [
            ("Description", "GetDescription"),
            ("Channel", "GetChannel"),
            ("Window", "GetWindow"),
            ("Trace", "GetTrace"),
            ("S-Parameter", "GetSparameter"),
            ("Center Freq", "GetCenterFreq"),
            ("Start Freq", "GetStartFreq"),
            ("Stop Freq", "GetStopFreq"),
            ("Span", "GetSpan"),
            ("RBW", "GetRBW"),
            ("Ref Level", "GetRefLevel"),
            ("Division", "GetDivisionValue"),
            ("Sweep Type", "GetSweepType"),
            ("Sweep Mode", "GetSweepMode"),
            ("Sweep Count", "GetSweepCount"),
            ("Sweep Points", "GetSweepPoints"),
            ("Trigger Mode", "GetTriggerMode"),
            ("Trigger Delay", "GetTriggerDelay"),
        ]

        for idx, (label, getter) in enumerate(status_specs):
            value = QtWidgets.QLineEdit()
            value.setReadOnly(True)
            self._status_fields[getter] = value
            row = idx // 2
            col = (idx % 2) * 2
            status_grid.addWidget(QtWidgets.QLabel(label), row, col)
            status_grid.addWidget(value, row, col + 1)

        layout.addLayout(status_grid)
        layout.addStretch()
        self.tabs.addTab(tab, "Status")

    def _build_controls_tab(self):
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)

        controls_grid = QtWidgets.QGridLayout()
        control_specs = [
            ("Center Frequency", "center_freq", FrequencyControl(default_hz=1e9), self.on_set_center_freq_clicked),
            ("Span", "span", FrequencyControl(default_hz=1e9), self.on_set_span_clicked),
            ("RBW", "rbw", FrequencyControl(default_hz=10e3), self.on_set_rbw_clicked),
            ("Ref Level", "ref_level", QtWidgets.QLineEdit(), self.on_set_ref_level_clicked),
            ("Division Value", "division_value", QtWidgets.QLineEdit(), self.on_set_division_clicked),
            ("Sweep Type", "sweep_type", self._build_combo(("LINEAR", "LOGARITHMIC", "SEGMENT")), self.on_set_sweep_type_clicked),
            ("Sweep Mode", "sweep_mode", self._build_combo(("CONTINUOUS", "SINGLE")), self.on_set_sweep_mode_clicked),
            ("Sweep Count", "sweep_count", QtWidgets.QSpinBox(), self.on_set_sweep_count_clicked),
            ("Sweep Points", "sweep_points", QtWidgets.QSpinBox(), self.on_set_sweep_points_clicked),
            ("Trigger Mode", "trigger_mode", self._build_combo(("IMMEDIATE", "EXTERNAL")), self.on_set_trigger_mode_clicked),
            ("Trigger Delay [s]", "trigger_delay", QtWidgets.QLineEdit(), self.on_set_trigger_delay_clicked),
        ]

        for idx, (label, key, widget, handler) in enumerate(control_specs):
            if isinstance(widget, QtWidgets.QSpinBox):
                widget.setMaximum(1_000_000)
                widget.setMinimum(0)
            button = None
            if isinstance(widget, FrequencyControl):
                widget.valueApplied.connect(handler)
            else:
                button = QtWidgets.QPushButton("Apply")
                button.clicked.connect(handler)
            indicator = QtWidgets.QLabel("unknown")
            indicator.setMinimumWidth(72)
            self._control_widgets[key] = widget
            self._control_specs[key] = {"indicator": indicator}
            controls_grid.addWidget(QtWidgets.QLabel(label), idx, 0)
            controls_grid.addWidget(widget, idx, 1)
            if button is not None:
                controls_grid.addWidget(button, idx, 2)
            controls_grid.addWidget(indicator, idx, 3)
            self._set_indicator_state(key, "unknown")

        quick_row = QtWidgets.QHBoxLayout()
        self.pull_from_device_button = QtWidgets.QPushButton("Populate Controls From Device")
        self.pull_from_device_button.clicked.connect(self.populate_controls_from_status)
        quick_row.addWidget(self.pull_from_device_button)

        self.single_sweep_button = QtWidgets.QPushButton("Start Single Sweep")
        self.single_sweep_button.clicked.connect(self.on_single_sweep_clicked)
        quick_row.addWidget(self.single_sweep_button)

        self.smoke_test_button = QtWidgets.QPushButton("Run Smoke Test")
        self.smoke_test_button.clicked.connect(self.on_run_smoke_test_clicked)
        quick_row.addWidget(self.smoke_test_button)
        quick_row.addStretch()

        layout.addLayout(controls_grid)
        layout.addLayout(quick_row)
        layout.addStretch()
        self.tabs.addTab(tab, "Controls")

    def _build_spectrum_tab(self):
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)

        toolbar = QtWidgets.QHBoxLayout()
        self.acquire_spectrum_button = QtWidgets.QPushButton("Acquire Spectrum")
        self.acquire_spectrum_button.clicked.connect(self.on_get_spectrum_clicked)
        toolbar.addWidget(self.acquire_spectrum_button)

        self.acquire_single_button = QtWidgets.QPushButton("Single Sweep + Acquire")
        self.acquire_single_button.clicked.connect(self.on_single_sweep_and_get_spectrum_clicked)
        toolbar.addWidget(self.acquire_single_button)

        self.clear_plot_button = QtWidgets.QPushButton("Clear Plot")
        self.clear_plot_button.clicked.connect(self.on_clear_plot_clicked)
        toolbar.addWidget(self.clear_plot_button)

        self.export_csv_button = QtWidgets.QPushButton("Export CSV")
        self.export_csv_button.clicked.connect(self.on_export_csv_clicked)
        toolbar.addWidget(self.export_csv_button)

        self.grid_toggle_button = QtWidgets.QPushButton("Grid Off")
        self.grid_toggle_button.setCheckable(True)
        self.grid_toggle_button.toggled.connect(self.on_grid_toggled)
        toolbar.addWidget(self.grid_toggle_button)
        toolbar.addStretch()

        title_row = QtWidgets.QHBoxLayout()
        title_row.addWidget(QtWidgets.QLabel("Plot Title"))
        self.plot_title_edit = QtWidgets.QLineEdit(self._default_plot_title)
        self.plot_title_edit.editingFinished.connect(self.on_plot_title_changed)
        title_row.addWidget(self.plot_title_edit)

        splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        self.canvas = MplCanvas()
        self.canvas.setMinimumHeight(280)
        self.canvas_toolbar = NavigationToolbar(self.canvas, tab)
        splitter.addWidget(self.canvas)

        self.spectrum_edit = QtWidgets.QPlainTextEdit()
        self.spectrum_edit.setReadOnly(True)
        self.spectrum_edit.setMinimumHeight(120)
        splitter.addWidget(self.spectrum_edit)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([520, 180])

        self.spectrum_summary_label = QtWidgets.QLabel("No spectrum acquired.")
        self.spectrum_summary_label.setWordWrap(True)

        layout.addLayout(toolbar)
        layout.addLayout(title_row)
        layout.addWidget(self.canvas_toolbar)
        layout.addWidget(splitter)
        layout.addWidget(self.spectrum_summary_label)
        self.tabs.addTab(tab, "Spectrum")

    def _build_log_tab(self):
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)

        toolbar = QtWidgets.QHBoxLayout()
        self.clear_log_button = QtWidgets.QPushButton("Clear Log")
        self.clear_log_button.clicked.connect(self.log_edit_clear)
        toolbar.addWidget(self.clear_log_button)
        toolbar.addStretch()

        self.log_edit = QtWidgets.QPlainTextEdit()
        self.log_edit.setReadOnly(True)

        layout.addLayout(toolbar)
        layout.addWidget(self.log_edit)
        self.tabs.addTab(tab, "Log")

    def _build_combo(self, items):
        combo = QtWidgets.QComboBox()
        combo.addItems(list(items))
        return combo

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

    def log_edit_clear(self):
        self.log_edit.clear()

    def log_message(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_edit.appendPlainText(f"[{timestamp}] {message}")

    def _driver_display_name(self):
        """Return a short driver identity string for the status bar."""
        driver_type = type(self.dv).__name__
        idn = getattr(self.dv, "IDN", "") or ""
        if idn:
            return f"Driver: {driver_type} | {idn}"
        return f"Driver: {driver_type}"

    def _refresh_status_bar(self, state_text=None):
        """Update the bottom status bar labels."""
        if state_text is None:
            state_text = "Busy" if self._busy else "Ready"
        self.state_label.setText(f"State: {state_text}")
        self.init_state_label.setText(
            f"Init: {'initialized' if self._is_initialized else 'not initialized'}"
        )
        self.driver_label.setText(self._driver_display_name())
        self.last_error_label.setText(f"Last error: {self._last_error_text}")

    def _set_busy(self, busy, message=None):
        self._busy = busy
        self.tabs.setEnabled(not busy)
        self.refresh_all_button.setEnabled(not busy)
        self.close_button.setEnabled(not busy)
        if busy:
            state_text = f"Busy: {message}" if message else "Busy"
        else:
            state_text = message if message is not None else "Ready"
        self._refresh_status_bar(state_text)

    def _start_task(
        self,
        label,
        func,
        on_success=None,
        on_error=None,
        on_finished=None,
    ):
        if self._busy:
            QtWidgets.QMessageBox.information(
                self,
                "Operation in progress",
                "Another device operation is still running.",
            )
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
                self._set_busy(False, "Idle")

            if error is None:
                self.log_message(f"{label} succeeded.")
                if on_success is not None:
                    on_success(result)
            else:
                if label == "Init":
                    self._is_initialized = False
                self.log_message(f"{label} failed: {type(error).__name__}: {error}")
                if on_error is not None:
                    on_error(error)
                else:
                    self._show_error(f"{label} Error", error)

            if on_finished is not None:
                on_finished()
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
        self._set_busy(False, "Idle")

        self._task_label = None
        self._task_result = None
        self._task_error = None
        self._task_on_success = None
        self._task_on_error = None
        self._task_on_finished = None

        if error is None:
            self.log_message(f"{label} succeeded.")
            if on_success is not None:
                on_success(result)
        else:
            if label == "Init":
                self._is_initialized = False
            self.log_message(f"{label} failed: {type(error).__name__}: {error}")
            if on_error is not None:
                on_error(error)
            else:
                self._show_error(f"{label} Error", error)

        if on_finished is not None:
            on_finished()

    def _display_value(self, value):
        if isinstance(value, tuple):
            return ", ".join(str(item) for item in value)
        return str(value)

    def _driver_method(self, method_name, *args, **kwargs):
        method = getattr(self.dv, method_name, None)
        if method is None:
            raise AttributeError(f"Driver does not implement {method_name}()")
        return method(*args, **kwargs)

    def _show_error(self, title, error):
        self._last_error_text = str(error)
        self._refresh_status_bar()
        QtWidgets.QMessageBox.critical(self, title, str(error))

    def _set_status_field(self, key, text):
        widget = self._status_fields.get(key)
        if widget is not None:
            widget.setText(text)

    def _status_value(self, getter):
        widget = self._status_fields.get(getter)
        return widget.text().strip() if widget is not None else ""

    def _active_sparameter_label(self):
        """Return the best available Y-axis label derived from the active S-parameter."""
        raw_sparam = self._status_raw.get("GetSparameter")
        if isinstance(raw_sparam, str) and raw_sparam.strip():
            return raw_sparam.strip()
        return "Amplitude"

    def on_load_ini_clicked(self):
        path, _filter = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Open INI File",
            "",
            "INI Files (*.ini *.txt);;All Files (*)",
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            self.ini_edit.setPlainText(content)
            self._last_ini_text = content
            self.log_message(f"Loaded INI file: {path}")
        except Exception as exc:
            self._show_error("INI Load Error", exc)

    def on_save_ini_clicked(self):
        path, _filter = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Save INI File",
            "",
            "INI Files (*.ini *.txt);;All Files (*)",
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self.ini_edit.toPlainText())
            clear_ini_draft(self)
            self.log_message(f"Saved INI file: {path}")
        except Exception as exc:
            self._show_error("INI Save Error", exc)

    def on_init_clicked(self):
        ini_text = self.ini_edit.toPlainText()
        self._last_ini_text = ini_text
        channel = self.channel_spin.value()

        def task():
            return self._driver_method("Init", ini=io.StringIO(ini_text), channel=channel)

        def success(err):
            self._is_initialized = (err == 0)
            if err == 0:
                self._last_error_text = "none"
            self._refresh_status_bar()
            self.log_message(f"Init returned: {err}")
            self.refresh_all()

        self._start_task("Init", task, on_success=success)

    def _collect_status_snapshot(self):
        getter_specs = [
            "GetDescription",
            "GetChannel",
            "GetWindow",
            "GetTrace",
            "GetSparameter",
            "GetCenterFreq",
            "GetStartFreq",
            "GetStopFreq",
            "GetSpan",
            "GetRBW",
            "GetRefLevel",
            "GetDivisionValue",
            "GetSweepType",
            "GetSweepMode",
            "GetSweepCount",
            "GetSweepPoints",
            "GetTriggerMode",
            "GetTriggerDelay",
        ]

        snapshot = {}
        for getter in getter_specs:
            if not hasattr(self.dv, getter):
                continue
            try:
                err, value = self._driver_method(getter)
                text = self._display_value(value) if err == 0 else f"ERR {err}"
                snapshot[getter] = {"text": text, "value": value, "err": err}
            except Exception as exc:
                snapshot[getter] = {"text": f"{type(exc).__name__}: {exc}", "value": None, "err": None}
        return snapshot

    def _apply_status_snapshot(self, snapshot):
        self._status_raw = {}
        for getter, info in snapshot.items():
            text = info["text"]
            self._set_status_field(getter, text)
            self._status_raw[getter] = info["value"] if info["err"] == 0 else None
        self._update_control_indicators()
        self.canvas.set_y_label(self._active_sparameter_label())

    def refresh_status(self, on_complete=None):
        def success(snapshot):
            self._apply_status_snapshot(snapshot)
            if on_complete is not None:
                on_complete()

        self._start_task("Refresh Status", self._collect_status_snapshot, on_success=success)

    def populate_controls_from_status(self):
        mapping = {
            "center_freq": "GetCenterFreq",
            "span": "GetSpan",
            "rbw": "GetRBW",
            "ref_level": "GetRefLevel",
            "division_value": "GetDivisionValue",
            "sweep_type": "GetSweepType",
            "sweep_mode": "GetSweepMode",
            "sweep_count": "GetSweepCount",
            "sweep_points": "GetSweepPoints",
            "trigger_mode": "GetTriggerMode",
            "trigger_delay": "GetTriggerDelay",
        }

        for control_key, getter in mapping.items():
            widget = self._control_widgets[control_key]
            raw_value = self._status_raw.get(getter)
            if raw_value is None:
                continue
            try:
                if isinstance(widget, QtWidgets.QComboBox):
                    idx = widget.findText(str(raw_value))
                    if idx >= 0:
                        widget.setCurrentIndex(idx)
                elif isinstance(widget, FrequencyControl):
                    widget.set_value_hz(float(raw_value))
                elif isinstance(widget, QtWidgets.QSpinBox):
                    widget.setValue(int(float(raw_value)))
                else:
                    widget.setText(str(raw_value))
            except Exception:
                self.log_message(f"Could not populate control {control_key} from {getter}='{raw_value}'")
        self._update_control_indicators()

    def _set_indicator_state(self, key, state, message=None):
        spec = self._control_specs.get(key)
        if spec is None:
            return
        indicator = spec["indicator"]
        styles = {
            "unknown": ("unknown", "#777777"),
            "pending": ("pending", "#d98c00"),
            "ok": ("match", "#2e8b57"),
            "mismatch": ("mismatch", "#b22222"),
        }
        text, color = styles.get(state, styles["unknown"])
        indicator.setText(text)
        indicator.setStyleSheet(f"color: {color}; font-weight: bold;")
        indicator.setToolTip(message or "")

    def _control_current_value(self, key):
        widget = self._control_widgets[key]
        if isinstance(widget, QtWidgets.QComboBox):
            return widget.currentText().strip()
        if isinstance(widget, FrequencyControl):
            return widget.value_hz()
        if isinstance(widget, QtWidgets.QSpinBox):
            return int(widget.value())
        return widget.text().strip()

    def _normalize_indicator_value(self, key, value):
        """Normalize control/readback values to the public API vocabulary."""
        if value is None:
            return None

        if key == "sweep_mode":
            mapping = {
                "1": "CONTINUOUS",
                "ON": "CONTINUOUS",
                "0": "SINGLE",
                "OFF": "SINGLE",
                "CONTINUOUS": "CONTINUOUS",
                "SINGLE": "SINGLE",
                "SINGEL": "SINGLE",
            }
            return mapping.get(str(value).strip().upper(), str(value).strip().upper())

        if key == "sweep_type":
            mapping = {
                "LIN": "LINEAR",
                "LINEAR": "LINEAR",
                "LOG": "LOGARITHMIC",
                "LOGARITHMIC": "LOGARITHMIC",
                "SEGM": "SEGMENT",
                "SEGMENT": "SEGMENT",
            }
            return mapping.get(str(value).strip().upper(), str(value).strip().upper())

        if key == "trigger_mode":
            return str(value).strip().upper()

        return value

    def _update_control_indicators(self):
        mapping = {
            "center_freq": "GetCenterFreq",
            "span": "GetSpan",
            "rbw": "GetRBW",
            "ref_level": "GetRefLevel",
            "division_value": "GetDivisionValue",
            "sweep_type": "GetSweepType",
            "sweep_mode": "GetSweepMode",
            "sweep_count": "GetSweepCount",
            "sweep_points": "GetSweepPoints",
            "trigger_mode": "GetTriggerMode",
            "trigger_delay": "GetTriggerDelay",
        }

        for key, getter in mapping.items():
            readback = self._status_raw.get(getter)
            if readback is None:
                self._set_indicator_state(key, "unknown", "No valid readback available.")
                continue
            current = self._normalize_indicator_value(key, self._control_current_value(key))
            readback = self._normalize_indicator_value(key, readback)
            try:
                if isinstance(current, int):
                    matches = current == int(float(readback))
                elif key in {"sweep_type", "sweep_mode", "trigger_mode"}:
                    matches = str(current).strip().upper() == str(readback).strip().upper()
                else:
                    matches = abs(float(current) - float(readback)) <= max(1e-12, abs(float(readback)) * 1e-9)
            except Exception:
                matches = str(current).strip() == str(readback).strip()

            if matches:
                self._set_indicator_state(key, "ok", f"Readback matches device value {readback!r}.")
            else:
                self._set_indicator_state(
                    key,
                    "mismatch",
                    f"Control value {current!r} differs from device value {readback!r}.",
                )

    def _line_edit_float(self, key):
        widget = self._control_widgets[key]
        if isinstance(widget, FrequencyControl):
            return widget.value_hz()
        text = widget.text().strip()
        if not text:
            raise ValueError("Input field is empty")
        return float(text)

    def _combo_value(self, key):
        return self._control_widgets[key].currentText().strip()

    def _spin_value(self, key):
        return int(self._control_widgets[key].value())

    def _apply_and_refresh(self, label, callable_):
        def success(result):
            self.log_message(f"{label}: {result!r}")
            self.refresh_all()

        self._start_task(label, callable_, on_success=success)

    def on_set_center_freq_clicked(self, value=None):
        self._set_indicator_state("center_freq", "pending", "Write in progress.")
        self._apply_and_refresh("SetCenterFreq", lambda: self._driver_method("SetCenterFreq", value if value is not None else self._line_edit_float("center_freq")))

    def on_set_span_clicked(self, value=None):
        self._set_indicator_state("span", "pending", "Write in progress.")
        self._apply_and_refresh("SetSpan", lambda: self._driver_method("SetSpan", value if value is not None else self._line_edit_float("span")))

    def on_set_rbw_clicked(self, value=None):
        self._set_indicator_state("rbw", "pending", "Write in progress.")
        self._apply_and_refresh("SetRBW", lambda: self._driver_method("SetRBW", value if value is not None else self._line_edit_float("rbw")))

    def on_set_ref_level_clicked(self):
        self._set_indicator_state("ref_level", "pending", "Write in progress.")
        self._apply_and_refresh("SetRefLevel", lambda: self._driver_method("SetRefLevel", self._line_edit_float("ref_level")))

    def on_set_division_clicked(self):
        self._set_indicator_state("division_value", "pending", "Write in progress.")
        self._apply_and_refresh("SetDivisionValue", lambda: self._driver_method("SetDivisionValue", self._line_edit_float("division_value")))

    def on_set_sweep_type_clicked(self):
        self._set_indicator_state("sweep_type", "pending", "Write in progress.")
        self._apply_and_refresh("SetSweepType", lambda: self._driver_method("SetSweepType", self._combo_value("sweep_type")))

    def on_set_sweep_mode_clicked(self):
        self._set_indicator_state("sweep_mode", "pending", "Write in progress.")
        self._apply_and_refresh("SetSweepMode", lambda: self._driver_method("SetSweepMode", self._combo_value("sweep_mode")))

    def on_set_sweep_count_clicked(self):
        self._set_indicator_state("sweep_count", "pending", "Write in progress.")
        self._apply_and_refresh("SetSweepCount", lambda: self._driver_method("SetSweepCount", self._spin_value("sweep_count")))

    def on_set_sweep_points_clicked(self):
        self._set_indicator_state("sweep_points", "pending", "Write in progress.")
        self._apply_and_refresh("SetSweepPoints", lambda: self._driver_method("SetSweepPoints", self._spin_value("sweep_points")))

    def on_set_trigger_mode_clicked(self):
        self._set_indicator_state("trigger_mode", "pending", "Write in progress.")
        self._apply_and_refresh("SetTriggerMode", lambda: self._driver_method("SetTriggerMode", self._combo_value("trigger_mode")))

    def on_set_trigger_delay_clicked(self):
        self._set_indicator_state("trigger_delay", "pending", "Write in progress.")
        self._apply_and_refresh("SetTriggerDelay", lambda: self._driver_method("SetTriggerDelay", self._line_edit_float("trigger_delay")))

    def on_single_sweep_clicked(self):
        def action():
            if hasattr(self.dv, "SetSweepMode"):
                self._driver_method("SetSweepMode", "SINGLE")
            if hasattr(self.dv, "NewSweepCount"):
                return self._driver_method("NewSweepCount")
            raise AttributeError("Driver does not support NewSweepCount()")

        self._apply_and_refresh("Single Sweep", action)

    def on_single_sweep_and_get_spectrum_clicked(self):
        def task():
            if hasattr(self.dv, "SetSweepMode"):
                self._driver_method("SetSweepMode", "SINGLE")
            if hasattr(self.dv, "NewSweepCount"):
                self._driver_method("NewSweepCount")
            sweep_type = None
            if hasattr(self.dv, "GetSweepType"):
                err, sweep_type = self._driver_method("GetSweepType")
                if err != 0:
                    sweep_type = None
            err, power = self._driver_method("GetSpectrum")
            if err != 0:
                raise RuntimeError(f"GetSpectrum returned error code {err}")
            return {"sweep_type": sweep_type, "power": power, "source": "single sweep"}

        self._start_task(
            "Single Sweep + Spectrum",
            task,
            on_success=self._handle_spectrum_result,
        )

    def _handle_spectrum_result(self, result):
        sweep_type = result.get("sweep_type")
        power = result.get("power")
        source = result.get("source", "acquire")

        self.power = power
        self._last_trace_data = power
        x = np.asarray(power[0], dtype=float)
        y = np.asarray(power[1], dtype=float)
        logarithmic = sweep_type == "LOGARITHMIC"

        self.canvas.set_y_label(self._active_sparameter_label())
        self.canvas.update_spectrum(x, y, logarithmic=logarithmic)

        preview = [
            f"x-points: {len(x)}",
            f"y-points: {len(y)}",
        ]
        if len(x) > 0:
            preview.append(f"first point: x={x[0]:.6e}, y={y[0]:.6e}")
            preview.append(f"last point:  x={x[-1]:.6e}, y={y[-1]:.6e}")
        preview.append("")
        preview.append("X values:")
        preview.append(", ".join(f"{value:.6e}" for value in x[:50]))
        preview.append("")
        preview.append("Y values:")
        preview.append(", ".join(f"{value:.6e}" for value in y[:50]))
        self.spectrum_edit.setPlainText("\n".join(preview))
        y_min = float(np.min(y)) if len(y) else float("nan")
        y_max = float(np.max(y)) if len(y) else float("nan")
        self._last_spectrum_summary = {
            "points": len(x),
            "source": source,
            "sweep_type": sweep_type,
            "y_min": y_min,
            "y_max": y_max,
        }
        summary_parts = [
            f"Last acquisition: {len(x)} points",
            f"source: {source}",
        ]
        if sweep_type:
            summary_parts.append(f"sweep: {sweep_type}")
        if len(y):
            summary_parts.append(f"y-range: {y_min:.6e} .. {y_max:.6e}")
        self.spectrum_summary_label.setText(", ".join(summary_parts))
        self.log_message(f"Spectrum acquired: {len(x)} points ({source})")
        self.refresh_all()

    def on_get_spectrum_clicked(self):
        def task():
            sweep_type = None
            if hasattr(self.dv, "GetSweepType"):
                err, sweep_type = self._driver_method("GetSweepType")
                if err != 0:
                    sweep_type = None
            err, power = self._driver_method("GetSpectrum")
            if err != 0:
                raise RuntimeError(f"GetSpectrum returned error code {err}")
            return {"sweep_type": sweep_type, "power": power, "source": "acquire"}

        self._start_task("Acquire Spectrum", task, on_success=self._handle_spectrum_result)

    def on_clear_plot_clicked(self):
        self.canvas.clear_plot()
        self.spectrum_edit.clear()
        self._last_trace_data = None
        self._last_spectrum_summary = None
        self.spectrum_summary_label.setText("No spectrum acquired.")
        self.log_message("Spectrum plot cleared.")

    def on_plot_title_changed(self):
        self.canvas.set_plot_title(self.plot_title_edit.text().strip() or self._default_plot_title)

    def on_grid_toggled(self, checked):
        self.canvas.set_grid_enabled(checked)
        self.grid_toggle_button.setText("Grid On" if checked else "Grid Off")

    def on_export_csv_clicked(self):
        if self._last_trace_data is None:
            self._show_error("Export CSV Error", ValueError("No spectrum data available."))
            return

        default_name = f"spectrum_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Export Spectrum CSV",
            default_name,
            "CSV Files (*.csv);;All Files (*)",
        )
        if not path:
            return

        x_values, y_values = self._last_trace_data
        try:
            with open(path, "w", encoding="utf-8", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(["frequency_hz", "amplitude"])
                for x_value, y_value in zip(x_values, y_values):
                    writer.writerow([f"{float(x_value):.16e}", f"{float(y_value):.16e}"])
        except OSError as exc:
            self._show_error("Export CSV Error", exc)
            return

        self.log_message(f"Spectrum exported to {path}")

    def _run_smoke_test(self):
        checks = [
            ("GetDescription", ()),
            ("GetChannel", ()),
            ("GetSweepType", ()),
            ("GetSweepMode", ()),
            ("GetSweepCount", ()),
            ("GetSweepPoints", ()),
            ("GetCenterFreq", ()),
            ("GetSpan", ()),
            ("GetRBW", ()),
            ("GetTriggerMode", ()),
        ]
        results = []
        for method_name, args in checks:
            if not hasattr(self.dv, method_name):
                results.append(f"{method_name}: skipped")
                continue
            err, value = self._driver_method(method_name, *args)
            if err != 0:
                raise RuntimeError(f"{method_name} returned error code {err}")
            results.append(f"{method_name}: {value!r}")

        if hasattr(self.dv, "SetSweepMode"):
            err, value = self._driver_method("SetSweepMode", "SINGLE")
            if err != 0:
                raise RuntimeError(f"SetSweepMode returned error code {err}")
            results.append(f"SetSweepMode('SINGLE'): {value!r}")
        if hasattr(self.dv, "NewSweepCount"):
            err, value = self._driver_method("NewSweepCount")
            if err != 0:
                raise RuntimeError(f"NewSweepCount returned error code {err}")
            results.append(f"NewSweepCount: {value!r}")
        if hasattr(self.dv, "GetSpectrum"):
            err, power = self._driver_method("GetSpectrum")
            if err != 0:
                raise RuntimeError(f"GetSpectrum returned error code {err}")
            x_values, y_values = power
            results.append(f"GetSpectrum: {len(x_values)} x-points, {len(y_values)} y-points")
        return results

    def on_run_smoke_test_clicked(self):
        def success(lines):
            self.log_message("Smoke test completed.")
            for line in lines:
                self.log_message(f"  {line}")
            self.refresh_all()

        self._start_task("Smoke Test", self._run_smoke_test, on_success=success)

    def refresh_all(self):
        def complete():
            self.populate_controls_from_status()
            self.after_refresh_all()

        self.refresh_status(on_complete=complete)

    def after_refresh_all(self):
        """Hook for subclasses that need to update additional UI state."""

    def closeEvent(self, event):
        if self._busy and self._active_thread is not None:
            QtWidgets.QMessageBox.information(
                self,
                "Operation in progress",
                "Please wait until the current device operation has finished.",
            )
            event.ignore()
            return
        try:
            if hasattr(self.dv, "close"):
                self.dv.close()
            elif hasattr(self.dv, "Quit"):
                self.dv.Quit()
        except Exception as exc:
            self.log_message(f"Driver cleanup failed: {type(exc).__name__}: {exc}")
        super().closeEvent(event)


if __name__ == "__main__":
    threaded = "--threaded" in sys.argv
    if threaded:
        sys.argv.remove("--threaded")

    class DummyNetworkDriver:
        def Init(self, ini=None, channel=1):
            print("Init called")
            if ini is not None:
                print(ini.read())
            return 0

        def GetDescription(self):
            return 0, "Dummy network analyzer"

        def GetChannel(self):
            return 0, 1

        def GetSweepType(self):
            return 0, "LINEAR"

        def GetSweepMode(self):
            return 0, "CONTINUOUS"

        def GetSweepCount(self):
            return 0, 1

        def GetSweepPoints(self):
            return 0, 200

        def GetCenterFreq(self):
            return 0, 3.05e9

        def GetStartFreq(self):
            return 0, 1e8

        def GetStopFreq(self):
            return 0, 6e9

        def GetSpan(self):
            return 0, 5.9e9

        def GetRBW(self):
            return 0, 10e3

        def GetTriggerMode(self):
            return 0, "IMMEDIATE"

        def GetTriggerDelay(self):
            return 0, 0.0

        def GetSpectrum(self):
            x = np.linspace(1e8, 6e9, 200)
            y = -40 + 10 * np.sin(np.linspace(0, 8 * np.pi, 200))
            return 0, (x.tolist(), y.tolist())

        def Quit(self):
            print("Quit called")

    app = QtWidgets.QApplication(sys.argv)
    w = NetworkAnalyzerWidget(DummyNetworkDriver())
    w._use_worker_threads = threaded
    w.show()
    sys.exit(app.exec())
