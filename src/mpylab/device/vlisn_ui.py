# -*- coding: utf-8 -*-
"""Graphical test utility for V-LISN drivers."""

import argparse
import configparser
import csv
import importlib
import io
import sys
from datetime import datetime
from pathlib import Path

from PySide6 import QtCore, QtWidgets

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from scuq.ucomponents import Context

from mpylab.device.ui_frequency import FrequencyControl
from mpylab.device.ui_ini_draft import IniPlainTextEdit, clear_ini_draft, load_ini_with_draft
from mpylab.device.ui_quantity_display import INI_UNIT_MODE, SCUQ_UNIT_MODE, quantity_display_values
from mpylab.device.vlisn_virtual import VLISN as VIRTUAL_VLISN
from mpylab.tools.configuration import parse_ini_value, strbool
from mpylab.tools.util import format_block


SETTINGS_APP = "vlisn_ui"


std_ini_text = format_block("""
                [DESCRIPTION]
                description: Virtual V-LISN
                type:        VLISN
                vendor:      mpylab
                serialnr:    VIRTUAL
                deviceid:    vlisn_virtual
                driver:      vlisn_virtual.py

                [INIT_VALUE]
                fstart: 9e3
                fstop: 30e6
                fstep: 0
                visa:
                nr_of_channels: 1
                path: L
                unit: dB
                filter: 0
                virtual: 1

                [CHANNEL_1]
                name: S21
                unit: dB
                interpolation: LOG
                file: io.StringIO(format_block('''
                    FUNIT: Hz
                    UNIT: dB
                    RELERROR: 0
                    9e3 -10
                    30e6 -10
                    '''))
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


class VlisnCanvas(FigureCanvas):
    """Matplotlib canvas for V-LISN correction data."""

    def __init__(self, parent=None):
        self.figure = Figure(figsize=(7, 4), dpi=100)
        self.ax = self.figure.add_subplot(111)
        self._grid_enabled = True
        super().__init__(self.figure)
        self.setParent(parent)
        self.update_plot([])

    def set_grid_enabled(self, enabled):
        """Enable or disable plot grid."""
        self._grid_enabled = bool(enabled)
        self.ax.grid(self._grid_enabled, alpha=0.35)
        self.draw_idle()

    def update_plot(self, rows, what=""):
        """Redraw correction values over frequency."""
        self.ax.clear()
        if rows:
            x = [row["frequency_hz"] for row in rows]
            y = [row["value"] for row in rows]
            yerr = [row["uncertainty"] for row in rows]
            self.ax.errorbar(x, y, yerr=yerr, marker="o", linewidth=1.2, capsize=3)
            self.ax.set_xscale("log")
        else:
            self.ax.text(0.5, 0.5, "No V-LISN data acquired", ha="center", va="center", transform=self.ax.transAxes)
        self.ax.set_title("V-LISN Correction")
        self.ax.set_xlabel("Frequency / Hz")
        unit = rows[0]["unit"] if rows else ""
        self.ax.set_ylabel(f"{what} / {unit}".strip(" /"))
        self.ax.grid(self._grid_enabled, alpha=0.35)
        self.figure.tight_layout()
        self.draw()


class VlisnWidget(QtWidgets.QWidget):
    """Thread-aware test UI for the common V-LISN driver API."""

    def __init__(self, instance, ini=None, parent=None, use_ini_draft=True):
        super().__init__(parent)
        self.dev = instance
        self.ini_source = ini if ini is not None else io.StringIO(std_ini_text)
        self.use_ini_draft = use_ini_draft
        self._status_fields = {}
        self._busy = False
        self._is_initialized = False
        self._last_error_text = "none"
        self._last_data = None
        self._history = []
        self._last_plot_rows = []
        self._ctx = Context()
        self._use_worker_threads = False
        self._active_thread = None
        self._active_task = None
        self._task_label = None
        self._task_result = None
        self._task_error = None
        self._task_on_success = None
        self._task_on_error = None
        self._task_on_finished = None

        self.setWindowTitle("V-LISN Test Utility")
        self.resize(1180, 850)
        self._build_ui()
        self._load_ini()
        self.log_message("UI ready.")

    def _build_ui(self):
        main = QtWidgets.QVBoxLayout(self)
        self.tabs = QtWidgets.QTabWidget()
        main.addWidget(self.tabs)
        self._build_connection_tab()
        self._build_status_tab()
        self._build_data_tab()
        self._build_plot_tab()
        self._build_raw_tab()
        self._build_smoke_tab()
        self._build_log_tab()

        bottom = QtWidgets.QHBoxLayout()
        self.state_label = QtWidgets.QLabel()
        self.init_label = QtWidgets.QLabel()
        self.driver_label = QtWidgets.QLabel()
        self.error_label = QtWidgets.QLabel()
        self.error_label.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        bottom.addWidget(self.state_label)
        bottom.addSpacing(10)
        bottom.addWidget(self.init_label)
        bottom.addSpacing(10)
        bottom.addWidget(self.driver_label)
        bottom.addSpacing(10)
        bottom.addWidget(self.error_label, 1)
        self.refresh_button = QtWidgets.QPushButton("Refresh All")
        self.refresh_button.clicked.connect(self.refresh_status)
        self.close_button = QtWidgets.QPushButton("Close")
        self.close_button.clicked.connect(self.close)
        bottom.addWidget(self.refresh_button)
        bottom.addWidget(self.close_button)
        main.addLayout(bottom)
        self._refresh_status_bar()

    def _build_connection_tab(self):
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)
        row = QtWidgets.QHBoxLayout()
        self.init_button = QtWidgets.QPushButton("Init / Re-Init")
        self.init_button.clicked.connect(self.on_init_clicked)
        self.quit_button = QtWidgets.QPushButton("Quit")
        self.quit_button.clicked.connect(self.on_quit_clicked)
        self.load_button = QtWidgets.QPushButton("Load INI")
        self.load_button.clicked.connect(self.on_load_ini_clicked)
        self.save_button = QtWidgets.QPushButton("Save INI")
        self.save_button.clicked.connect(self.on_save_ini_clicked)
        row.addWidget(self.init_button)
        row.addWidget(self.quit_button)
        row.addWidget(self.load_button)
        row.addWidget(self.save_button)
        row.addStretch()
        self.ini_edit = IniPlainTextEdit()
        self.ini_edit.setMinimumHeight(330)
        layout.addLayout(row)
        layout.addWidget(self.ini_edit)
        self.tabs.addTab(tab, "Connection")

    def _build_status_tab(self):
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)
        grid = QtWidgets.QGridLayout()
        specs = [
            ("Description", "GetDescription"),
            ("Virtual", "GetVirtual"),
            ("Frequency", "GetFreq"),
            ("Path", "GetPath"),
            ("Filter", "GetFilter"),
            ("Channels", "GetChannels"),
            ("Last Data", "_last_data"),
        ]
        for idx, (label, key) in enumerate(specs):
            field = QtWidgets.QLineEdit()
            field.setReadOnly(True)
            field.setText("unknown")
            self._status_fields[key] = field
            row = idx // 2
            col = (idx % 2) * 2
            grid.addWidget(QtWidgets.QLabel(label), row, col)
            grid.addWidget(field, row, col + 1)
        layout.addLayout(grid)
        layout.addStretch()
        self.tabs.addTab(tab, "Status")

    def _build_data_tab(self):
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)
        form = QtWidgets.QGridLayout()
        self.freq_control = FrequencyControl(default_hz=1e6)
        self.freq_control.valueApplied.connect(self.on_set_freq_clicked)
        self.read_freq_button = QtWidgets.QPushButton("Read Frequency")
        self.read_freq_button.clicked.connect(self.on_read_freq_clicked)
        form.addWidget(QtWidgets.QLabel("Frequency"), 0, 0)
        form.addWidget(self.freq_control, 0, 1)
        form.addWidget(self.read_freq_button, 0, 2)

        self.path_combo = QtWidgets.QComboBox()
        self.path_combo.addItems(["L", "L1", "L2", "L3", "N"])
        self.set_path_button = QtWidgets.QPushButton("Set Path")
        self.set_path_button.clicked.connect(self.on_set_path_clicked)
        form.addWidget(QtWidgets.QLabel("Path"), 1, 0)
        form.addWidget(self.path_combo, 1, 1)
        form.addWidget(self.set_path_button, 1, 2)

        self.filter_check = QtWidgets.QCheckBox("Filter On")
        self.filter_check.toggled.connect(self.on_set_filter_toggled)
        form.addWidget(QtWidgets.QLabel("Filter"), 2, 0)
        form.addWidget(self.filter_check, 2, 1)

        self.what_combo = QtWidgets.QComboBox()
        self.what_combo.setEditable(True)
        self.what_combo.addItem("S21")
        self.get_data_button = QtWidgets.QPushButton("GetData")
        self.get_data_button.clicked.connect(self.on_get_data_clicked)
        form.addWidget(QtWidgets.QLabel("Data Name"), 3, 0)
        form.addWidget(self.what_combo, 3, 1)
        form.addWidget(self.get_data_button, 3, 2)
        layout.addLayout(form)

        self.value_edit = QtWidgets.QLineEdit()
        self.value_edit.setReadOnly(True)
        self.detail_edit = QtWidgets.QPlainTextEdit()
        self.detail_edit.setReadOnly(True)
        layout.addWidget(QtWidgets.QLabel("Value"))
        layout.addWidget(self.value_edit)
        layout.addWidget(self.detail_edit)
        self.tabs.addTab(tab, "Data")

    def _build_plot_tab(self):
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)
        toolbar = QtWidgets.QHBoxLayout()
        self.plot_what_combo = QtWidgets.QComboBox()
        self.plot_what_combo.setEditable(True)
        self.plot_what_combo.addItem("S21")
        self.start_freq_control = FrequencyControl(default_hz=9e3)
        self.stop_freq_control = FrequencyControl(default_hz=30e6)
        self.points_spin = QtWidgets.QSpinBox()
        self.points_spin.setRange(2, 10_000)
        self.points_spin.setValue(101)
        self.display_mode_combo = QtWidgets.QComboBox()
        self.display_mode_combo.addItems([INI_UNIT_MODE, SCUQ_UNIT_MODE])
        self.display_mode_combo.currentTextChanged.connect(lambda _text: self._replot_last_rows())
        self.plot_button = QtWidgets.QPushButton("Plot Channel")
        self.plot_button.clicked.connect(self.on_plot_clicked)
        self.export_csv_button = QtWidgets.QPushButton("Export CSV")
        self.export_csv_button.clicked.connect(self.on_export_csv_clicked)
        self.clear_plot_button = QtWidgets.QPushButton("Clear Plot")
        self.clear_plot_button.clicked.connect(self.on_clear_plot_clicked)
        self.grid_button = QtWidgets.QPushButton("Grid On")
        self.grid_button.setCheckable(True)
        self.grid_button.setChecked(True)
        self.grid_button.toggled.connect(self.on_grid_toggled)
        toolbar.addWidget(QtWidgets.QLabel("Data"))
        toolbar.addWidget(self.plot_what_combo)
        toolbar.addWidget(QtWidgets.QLabel("Start"))
        toolbar.addWidget(self.start_freq_control)
        toolbar.addWidget(QtWidgets.QLabel("Stop"))
        toolbar.addWidget(self.stop_freq_control)
        toolbar.addWidget(QtWidgets.QLabel("Points"))
        toolbar.addWidget(self.points_spin)
        toolbar.addWidget(QtWidgets.QLabel("Display"))
        toolbar.addWidget(self.display_mode_combo)
        toolbar.addWidget(self.plot_button)
        toolbar.addWidget(self.export_csv_button)
        toolbar.addWidget(self.clear_plot_button)
        toolbar.addWidget(self.grid_button)
        toolbar.addStretch()
        self.plot = VlisnCanvas()
        self.plot_toolbar = NavigationToolbar(self.plot, self)
        layout.addLayout(toolbar)
        layout.addWidget(self.plot_toolbar)
        layout.addWidget(self.plot)
        self.tabs.addTab(tab, "Plot")

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
        layout.addWidget(QtWidgets.QLabel("Smoke test: Init, SetFreq, SetPath, SetFilter, GetData, Quit."))
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

    def _load_ini(self):
        content = load_ini_with_draft(self, self.ini_edit, self.ini_source, std_ini_text, SETTINGS_APP, use_draft=self.use_ini_draft)
        self._last_ini_text = content

    def log_message(self, message):
        self.log_edit.appendPlainText(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")

    def _refresh_status_bar(self, state_text=None):
        if state_text is None:
            state_text = "Busy" if self._busy else "Ready"
        self.state_label.setText(f"State: {state_text}")
        self.init_label.setText(f"Init: {'initialized' if self._is_initialized else 'not initialized'}")
        self.driver_label.setText(f"Driver: {type(self.dev).__module__}.{type(self.dev).__name__}")
        self.error_label.setText(f"Last error: {self._last_error_text}")

    def _set_busy(self, busy, label=None):
        self._busy = busy
        self.tabs.setEnabled(not busy)
        self.refresh_button.setEnabled(not busy)
        self.close_button.setEnabled(not busy)
        self._refresh_status_bar(f"Busy: {label}" if busy and label else "Ready")

    def _start_task(self, label, func, on_success=None, on_error=None, on_finished=None):
        if self._busy:
            QtWidgets.QMessageBox.information(self, "Operation in progress", "Another operation is still running.")
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
                self._set_busy(False)
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
        task.completed.connect(self._task_completed, QtCore.Qt.QueuedConnection)
        task.finished.connect(thread.quit)
        task.finished.connect(task.deleteLater)
        thread.finished.connect(self._task_finished, QtCore.Qt.QueuedConnection)
        thread.finished.connect(thread.deleteLater)
        self._active_thread = thread
        self._active_task = task
        thread.start()
        return True

    @QtCore.Slot(object, object)
    def _task_completed(self, result, error):
        self._task_result = result
        self._task_error = error

    @QtCore.Slot()
    def _task_finished(self):
        label = self._task_label or "Task"
        result = self._task_result
        error = self._task_error
        on_success = self._task_on_success
        on_error = self._task_on_error
        on_finished = self._task_on_finished
        self._active_thread = None
        self._active_task = None
        self._task_label = None
        self._task_result = None
        self._task_error = None
        self._task_on_success = None
        self._task_on_error = None
        self._task_on_finished = None
        self._set_busy(False)
        self._finish_task(label, result, error, on_success, on_error, on_finished)

    def _finish_task(self, label, result, error, on_success, on_error, on_finished):
        if error is None:
            self._last_error_text = "none"
            self.log_message(f"{label} succeeded.")
            if on_success is not None:
                on_success(result)
        else:
            if label == "Init":
                self._is_initialized = False
            self._last_error_text = str(error)
            self.log_message(f"{label} failed: {type(error).__name__}: {error}")
            if on_error is not None:
                on_error(error)
            else:
                self._show_error(f"{label} Error", error)
        self._refresh_status_bar()
        if on_finished is not None:
            on_finished()

    def _show_error(self, title, error):
        self._refresh_status_bar()
        QtWidgets.QMessageBox.critical(self, title, str(error))

    def _driver_method(self, method_name, *args, **kwargs):
        method = getattr(self.dev, method_name, None)
        if method is None:
            raise AttributeError(f"Driver does not implement {method_name}()")
        return method(*args, **kwargs)

    def _split_error_value(self, result):
        if isinstance(result, tuple) and len(result) == 2:
            return result
        return 0, result

    def _result_value(self, result):
        return self._split_error_value(result)[1]

    def _display_quantity(self, quantity, what=None):
        try:
            return quantity_display_values(
                quantity,
                device=self.dev,
                what=what,
                mode=self.display_mode_combo.currentText(),
                context=self._ctx,
            )
        except Exception:
            return quantity, 0.0, ""

    def _ini_driver_settings(self, ini_text):
        config = configparser.ConfigParser()
        config.read_file(io.StringIO(ini_text))
        description = {}
        init_value = {}
        for section in config.sections():
            section_key = section.strip().lower()
            if section_key == "description":
                description = {key.lower(): parse_ini_value(value) for key, value in config.items(section)}
            elif section_key == "init_value":
                init_value = {key.lower(): parse_ini_value(value) for key, value in config.items(section)}
        driver = str(description.get("driver", "") or "").strip()
        virtual = strbool(init_value.get("virtual", False))
        return driver, virtual

    def _module_name_from_driver(self, driver, virtual):
        if virtual or not driver or Path(driver).with_suffix("").name.lower() == "dummy":
            return "vlisn_virtual"
        return Path(driver).with_suffix("").name

    def _instantiate_driver(self, module_name):
        module = importlib.import_module(f"mpylab.device.{module_name}")
        driver_cls = getattr(module, "VLISN")
        search_paths = getattr(self.dev, "SearchPaths", None)
        if search_paths is not None:
            try:
                return driver_cls(SearchPaths=search_paths)
            except TypeError:
                pass
        return driver_cls()

    def _select_driver_from_ini(self, ini_text):
        driver, virtual = self._ini_driver_settings(ini_text)
        module_name = self._module_name_from_driver(driver, virtual)
        current_module = type(self.dev).__module__.split(".")[-1]
        if current_module == module_name:
            return
        old_driver = self.dev
        self.dev = self._instantiate_driver(module_name)
        self._is_initialized = False
        self._history = []
        self._refresh_status_bar()
        self.log_message(f"Driver switched from {type(old_driver).__module__} to {type(self.dev).__module__}.")

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
        try:
            self._select_driver_from_ini(ini_text)
        except Exception as exc:
            self._show_error("Driver Selection Error", exc)
            return

        def success(err):
            self._is_initialized = (err == 0)
            self.log_message(f"Init returned: {err}")
            self.refresh_status()

        self._start_task("Init", lambda: self._driver_method("Init", io.StringIO(ini_text)), on_success=success)

    def on_quit_clicked(self):
        def success(result):
            self._is_initialized = False
            self._refresh_status_bar()
            self.log_message(f"Quit returned: {result}")

        self._start_task("Quit", lambda: self._driver_method("Quit"), on_success=success)

    def on_set_freq_clicked(self, freq=None):
        freq = self.freq_control.value_hz() if freq is None else freq
        self._start_task("Set Frequency", lambda: self._driver_method("SetFreq", freq), on_success=self._handle_freq)

    def on_read_freq_clicked(self):
        self._start_task("Read Frequency", lambda: self._driver_method("GetFreq"), on_success=self._handle_freq)

    def _handle_freq(self, result):
        _err, value = self._split_error_value(result)
        if value is not None:
            self.freq_control.set_value_hz(float(value))
        self._set_status_field("GetFreq", result)

    def on_set_path_clicked(self):
        path = self.path_combo.currentText()
        self._start_task("Set Path", lambda: self._driver_method("SetPath", path), on_success=self._handle_path)

    def _handle_path(self, result):
        path = str(self._result_value(result))
        idx = self.path_combo.findText(path)
        if idx >= 0:
            self.path_combo.setCurrentIndex(idx)
        self._set_status_field("GetPath", result)

    def on_set_filter_toggled(self, checked):
        if self._is_initialized:
            self._start_task("Set Filter", lambda: self._driver_method("SetFilter", checked), on_success=lambda result: self._set_status_field("GetFilter", result))

    def on_get_data_clicked(self):
        what = self.what_combo.currentText().strip()
        self._start_task("GetData", lambda: self._driver_method("GetData", what), on_success=lambda result: self._handle_data(result, what))

    def _handle_data(self, result, what):
        err, quantity = self._split_error_value(result)
        if err != 0 or quantity is None:
            self.value_edit.setText(str(result))
            return
        value, uncertainty, unit = self._display_quantity(quantity, what=what)
        self.value_edit.setText(f"{value:g} +/- {uncertainty:g} {unit}".strip())
        self.detail_edit.setPlainText(str(result))
        self._last_data = quantity
        row = {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "frequency_hz": self.freq_control.value_hz(),
            "path": self.path_combo.currentText(),
            "filter": self.filter_check.isChecked(),
            "what": what,
            "value": float(value),
            "uncertainty": abs(float(uncertainty)),
            "unit": unit,
        }
        self._history.append(row)
        self._set_status_field("_last_data", self.value_edit.text())

    def _set_status_field(self, key, value):
        field = self._status_fields.get(key)
        if field is not None:
            field.setText(str(value))

    def refresh_status(self):
        def task():
            snapshot = {}
            for method_name in ("GetDescription", "GetVirtual", "GetFreq", "GetPath", "GetFilter", "GetChannels"):
                method = getattr(self.dev, method_name, None)
                if method is None:
                    snapshot[method_name] = "not implemented"
                    continue
                try:
                    snapshot[method_name] = method()
                except Exception as exc:
                    snapshot[method_name] = f"{type(exc).__name__}: {exc}"
            snapshot["_last_data"] = self._last_data
            return snapshot

        def success(snapshot):
            for key, value in snapshot.items():
                self._set_status_field(key, value)
            channels = self._result_value(snapshot.get("GetChannels"))
            if isinstance(channels, (tuple, list)):
                current = self.what_combo.currentText()
                self.what_combo.clear()
                self.plot_what_combo.clear()
                self.what_combo.addItems([str(item) for item in channels])
                self.plot_what_combo.addItems([str(item) for item in channels])
                if current:
                    idx = self.what_combo.findText(current)
                    if idx >= 0:
                        self.what_combo.setCurrentIndex(idx)
                    idx = self.plot_what_combo.findText(current)
                    if idx >= 0:
                        self.plot_what_combo.setCurrentIndex(idx)
            freq = self._result_value(snapshot.get("GetFreq"))
            try:
                if freq is not None:
                    self.freq_control.set_value_hz(float(freq))
            except (TypeError, ValueError):
                pass
            path = self._result_value(snapshot.get("GetPath"))
            if isinstance(path, str):
                idx = self.path_combo.findText(path)
                if idx >= 0:
                    self.path_combo.setCurrentIndex(idx)
            flt = self._result_value(snapshot.get("GetFilter"))
            if isinstance(flt, bool):
                self.filter_check.blockSignals(True)
                self.filter_check.setChecked(flt)
                self.filter_check.blockSignals(False)
            self._refresh_status_bar()

        self._start_task("Refresh Status", task, on_success=success)

    def on_plot_clicked(self):
        what = self.plot_what_combo.currentText().strip()
        start = self.start_freq_control.value_hz()
        stop = self.stop_freq_control.value_hz()
        points = self.points_spin.value()

        def task():
            if stop <= start:
                raise ValueError("Stop frequency must be greater than start frequency")
            rows = []
            step = (stop - start) / (points - 1)
            for idx in range(points):
                freq = start + idx * step
                self.dev.SetFreq(freq)
                err, quantity = self.dev.GetData(what)
                if err != 0:
                    raise RuntimeError(f"GetData({what!r}) failed at {freq:g} Hz with error {err}")
                rows.append(
                    {
                        "frequency_hz": float(freq),
                        "path": self.path_combo.currentText(),
                        "filter": self.filter_check.isChecked(),
                        "what": what,
                        "quantity": str(quantity),
                        "_quantity": quantity,
                    }
                )
            return rows

        self._start_task("Plot Channel", task, on_success=lambda rows: self._plot_rows(rows, what))

    def _plot_rows(self, rows, what):
        self._last_plot_rows = rows
        self._replot_last_rows()
        if rows:
            self.freq_control.set_value_hz(rows[-1]["frequency_hz"])
            self._set_status_field("GetFreq", rows[-1]["frequency_hz"])

    def _display_plot_row(self, row):
        what = row["what"]
        quantity = row.get("_quantity")
        value, uncertainty, unit = quantity_display_values(
            quantity,
            device=self.dev,
            what=what,
            mode=self.display_mode_combo.currentText(),
            context=self._ctx,
        )
        display_row = dict(row)
        display_row["value"] = float(value)
        display_row["uncertainty"] = abs(float(uncertainty))
        display_row["unit"] = unit
        display_row.pop("_quantity", None)
        return display_row

    def _display_plot_rows(self):
        return [self._display_plot_row(row) for row in self._last_plot_rows]

    def _replot_last_rows(self):
        if not self._last_plot_rows:
            return
        what = self.plot_what_combo.currentText().strip()
        self.plot.update_plot(self._display_plot_rows(), what=what)

    def on_raw_query_clicked(self):
        cmd = self.raw_command_edit.text().strip()
        if not cmd:
            return
        if not hasattr(self.dev, "query"):
            self._show_error("Raw Query Error", AttributeError("driver did not expose query"))
            return
        self._start_task("Raw Query", lambda: self.dev.query(cmd), on_success=lambda result: self.raw_output.appendPlainText(f"> {cmd}\n{result}"))

    def on_raw_write_clicked(self):
        cmd = self.raw_command_edit.text().strip()
        if not cmd:
            return
        if not hasattr(self.dev, "write"):
            self._show_error("Raw Write Error", AttributeError("driver did not expose write"))
            return
        self._start_task("Raw Write", lambda: self.dev.write(cmd), on_success=lambda result: self.raw_output.appendPlainText(f"> {cmd}\n{result}"))

    def on_export_csv_clicked(self):
        if not self._last_plot_rows:
            self._show_error("Export CSV Error", ValueError("No data acquired"))
            return
        path, _filter = QtWidgets.QFileDialog.getSaveFileName(self, "Export V-LISN CSV", "", "CSV Files (*.csv);;All Files (*)")
        if not path:
            return
        try:
            with open(path, "w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=["frequency_hz", "path", "filter", "what", "value", "uncertainty", "unit", "quantity"])
                writer.writeheader()
                writer.writerows(self._display_plot_rows())
            self.log_message(f"Exported CSV: {path}")
        except OSError as exc:
            self._show_error("Export CSV Error", exc)

    def on_clear_plot_clicked(self):
        self._last_plot_rows = []
        self.plot.update_plot(self._last_plot_rows, what=self.plot_what_combo.currentText().strip())

    def on_grid_toggled(self, checked):
        self.grid_button.setText("Grid On" if checked else "Grid Off")
        self.plot.set_grid_enabled(checked)

    def on_smoke_clicked(self):
        ini_text = self.ini_edit.toPlainText()
        freq = self.freq_control.value_hz()
        what = self.what_combo.currentText().strip() or "S21"
        try:
            self._select_driver_from_ini(ini_text)
        except Exception as exc:
            self._show_error("Driver Selection Error", exc)
            return

        def task():
            lines = [f"Init: {self.dev.Init(io.StringIO(ini_text))}"]
            lines.append(f"GetDescription: {self.dev.GetDescription()!r}")
            lines.append(f"SetFreq({freq}): {self.dev.SetFreq(freq)!r}")
            lines.append(f"SetPath({self.path_combo.currentText()}): {self.dev.SetPath(self.path_combo.currentText())!r}")
            lines.append(f"SetFilter({self.filter_check.isChecked()}): {self.dev.SetFilter(self.filter_check.isChecked())!r}")
            lines.append(f"GetData({what}): {self.dev.GetData(what)!r}")
            if hasattr(self.dev, "Quit"):
                lines.append(f"Quit: {self.dev.Quit()!r}")
            return "\n".join(lines)

        self._start_task("Smoke Test", task, on_success=self.smoke_output.setPlainText)

    def closeEvent(self, event):
        if self._active_thread is not None and self._active_thread.isRunning():
            event.ignore()
            QtWidgets.QMessageBox.information(self, "Operation in progress", "Close after current operation.")
            return
        try:
            if hasattr(self.dev, "Quit"):
                self.dev.Quit()
        except Exception:
            pass
        super().closeEvent(event)


UI = VlisnWidget


def _make_default_instance(args):
    ini = io.StringIO(std_ini_text.replace("virtual: 1", "virtual: 1" if args.virtual else "virtual: 0"))
    if not args.virtual:
        print("Driver will be selected from the INI file on Init. Using virtual V-LISN until then.")
    return VIRTUAL_VLISN(), ini


def main(argv=None):
    parser = argparse.ArgumentParser(description="V-LISN driver test utility")
    parser.add_argument("ini", nargs="?", help="Optional path to an INI file.")
    parser.add_argument("--virtual", action="store_true", help="Use the virtual V-LISN driver.")
    parser.add_argument("--threaded", action="store_true", help="Run driver calls in worker threads.")
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
    ui = VlisnWidget(dev, ini=ini, use_ini_draft=not args.virtual)
    ui._use_worker_threads = args.threaded
    ui.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
