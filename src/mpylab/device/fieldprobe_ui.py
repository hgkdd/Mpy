# -*- coding: utf-8 -*-
"""Graphical test utility for field probe drivers."""

import argparse
import configparser
import csv
import importlib
import io
import math
import sys
from datetime import datetime
from pathlib import Path

from PySide6 import QtCore, QtWidgets

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure

from mpylab.device.ui_frequency import FrequencyControl
from mpylab.device.ui_ini_draft import IniPlainTextEdit, clear_ini_draft, load_ini_with_draft
from mpylab.tools.configuration import parse_ini_value, strbool
from mpylab.tools.util import format_block


SETTINGS_APP = "fieldprobe_ui"


std_ini_text = format_block("""
                [DESCRIPTION]
                description: 'Virtual FieldProbe'
                type:        'FIELDPROBE'
                vendor:      'mpylab'
                serialnr:
                deviceid:
                driver: prb_virtual.py

                [Init_Value]
                fstart: 3e6
                fstop: 18e9
                fstep: 0
                virtual: 1

                [Channel_1]
                name: EField
                unit: Voverm
                x: 1 + f/1e9
                y: 2
                z: 3
                uncertainty: 0.1
                """).strip()


class DriverTask(QtCore.QObject):
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


class FieldProbeCanvas(FigureCanvas):
    """Matplotlib canvas for field probe trend data."""

    def __init__(self, parent=None):
        self.figure = Figure(figsize=(7, 4), dpi=100)
        self.ax = self.figure.add_subplot(111)
        self._grid_enabled = True
        super().__init__(self.figure)
        self.setParent(parent)
        self.update_plot([])

    def set_grid_enabled(self, enabled):
        """Enable or disable the trend grid."""
        self._grid_enabled = bool(enabled)
        self.ax.grid(self._grid_enabled, alpha=0.35)
        self.draw_idle()

    def update_plot(self, history):
        """Redraw Ex/Ey/Ez/|E| trend data."""
        self.ax.clear()
        if history:
            idx = [row["index"] for row in history]
            self.ax.plot(idx, [row["Ex"] for row in history], label="Ex", linewidth=1.2)
            self.ax.plot(idx, [row["Ey"] for row in history], label="Ey", linewidth=1.2)
            self.ax.plot(idx, [row["Ez"] for row in history], label="Ez", linewidth=1.2)
            self.ax.plot(idx, [row["Eabs"] for row in history], label="|E|", linewidth=1.4)
            self.ax.legend(loc="best")
        else:
            self.ax.text(0.5, 0.5, "No field data acquired", ha="center", va="center", transform=self.ax.transAxes)
        self.ax.set_title("Field Probe Trend")
        self.ax.set_xlabel("Sample")
        self.ax.set_ylabel("Field strength")
        self.ax.grid(self._grid_enabled, alpha=0.35)
        self.figure.tight_layout()
        self.draw()


class FieldProbeWidget(QtWidgets.QWidget):
    def __init__(self, instance, ini=None, parent=None, use_ini_draft=True):
        super().__init__(parent)
        self.dev = instance
        self.ini_source = ini if ini is not None else io.StringIO(std_ini_text)
        self.use_ini_draft = use_ini_draft
        self._channel_drivers = {}
        self._status_fields = {}
        self._busy = False
        self._is_initialized = False
        self._last_error_text = "none"
        self._last_data = None
        self._history = []
        self._sample_index = 0
        self._use_worker_threads = False
        self._active_thread = None
        self._active_task = None
        self._task_label = None
        self._task_result = None
        self._task_error = None
        self._task_on_success = None
        self._task_on_error = None
        self._task_on_finished = None
        self._poll_timer = QtCore.QTimer(self)
        self._poll_timer.timeout.connect(self.on_poll_timeout)

        self.setWindowTitle("FieldProbe Test Utility")
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
        self._build_measurement_tab()
        self._build_trend_tab()
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
        bottom.addWidget(self.refresh_button)
        self.close_button = QtWidgets.QPushButton("Close")
        self.close_button.clicked.connect(self.close)
        bottom.addWidget(self.close_button)
        main.addLayout(bottom)
        self._refresh_status_bar()

    def _build_connection_tab(self):
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)
        row = QtWidgets.QHBoxLayout()
        self.channel_spin = QtWidgets.QSpinBox()
        self.channel_spin.setMinimum(1)
        self.channel_spin.setMaximum(128)
        self.channel_spin.setValue(1)
        self.channel_spin.valueChanged.connect(self.on_channel_changed)
        self.init_button = QtWidgets.QPushButton("Init / Re-Init")
        self.init_button.clicked.connect(self.on_init_clicked)
        self.quit_button = QtWidgets.QPushButton("Quit")
        self.quit_button.clicked.connect(self.on_quit_clicked)
        self.load_ini_button = QtWidgets.QPushButton("Load INI File")
        self.load_ini_button.clicked.connect(self.on_load_ini_clicked)
        self.save_ini_button = QtWidgets.QPushButton("Save INI File")
        self.save_ini_button.clicked.connect(self.on_save_ini_clicked)
        row.addWidget(QtWidgets.QLabel("Channel"))
        row.addWidget(self.channel_spin)
        row.addWidget(self.init_button)
        row.addWidget(self.quit_button)
        row.addWidget(self.load_ini_button)
        row.addWidget(self.save_ini_button)
        row.addStretch()
        self.ini_edit = IniPlainTextEdit()
        self.ini_edit.setMinimumHeight(360)
        layout.addLayout(row)
        layout.addWidget(self.ini_edit)
        self.tabs.addTab(tab, "Connection")

    def _build_status_tab(self):
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)
        grid = QtWidgets.QGridLayout()
        specs = [
            ("Description", "GetDescription"),
            ("Frequency", "GetFreq"),
            ("Virtual", "GetVirtual"),
            ("Battery", "GetBatteryState"),
            ("Channel", "_channel"),
            ("Internal Unit", "_internal_unit"),
            ("Bus Ready", "_bus_ready"),
            ("Last Data", "_last_data"),
        ]
        for idx, (label, key) in enumerate(specs):
            field = QtWidgets.QLineEdit()
            field.setReadOnly(True)
            self._status_fields[key] = field
            row = idx // 2
            col = (idx % 2) * 2
            grid.addWidget(QtWidgets.QLabel(label), row, col)
            grid.addWidget(field, row, col + 1)
        layout.addLayout(grid)
        layout.addStretch()
        self.tabs.addTab(tab, "Status")

    def _build_measurement_tab(self):
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)
        freq_row = QtWidgets.QHBoxLayout()
        self.freq_spin = FrequencyControl(default_hz=1e6)
        self.freq_spin.valueApplied.connect(self.on_set_freq_clicked)
        self.read_freq_button = QtWidgets.QPushButton("Read Frequency")
        self.read_freq_button.clicked.connect(self.on_read_freq_clicked)
        freq_row.addWidget(QtWidgets.QLabel("Frequency"))
        freq_row.addWidget(self.freq_spin)
        freq_row.addWidget(self.read_freq_button)
        layout.addLayout(freq_row)

        button_row = QtWidgets.QHBoxLayout()
        self.trigger_button = QtWidgets.QPushButton("Trigger")
        self.trigger_button.clicked.connect(self.on_trigger_clicked)
        self.measure_button = QtWidgets.QPushButton("GetData")
        self.measure_button.clicked.connect(self.on_measure_clicked)
        self.measure_nb_button = QtWidgets.QPushButton("GetDataNB")
        self.measure_nb_button.clicked.connect(self.on_measure_nb_clicked)
        self.retrigger_check = QtWidgets.QCheckBox("Retrigger")
        self.retrigger_check.setChecked(True)
        self.poll_check = QtWidgets.QCheckBox("Poll GetDataNB")
        self.poll_check.toggled.connect(self.on_poll_toggled)
        self.poll_interval_spin = QtWidgets.QSpinBox()
        self.poll_interval_spin.setRange(100, 60_000)
        self.poll_interval_spin.setValue(1000)
        self.poll_interval_spin.setSuffix(" ms")
        self.zero_on_button = QtWidgets.QPushButton("Zero On")
        self.zero_on_button.clicked.connect(lambda: self.on_zero_clicked("on"))
        self.zero_off_button = QtWidgets.QPushButton("Zero Off")
        self.zero_off_button.clicked.connect(lambda: self.on_zero_clicked("off"))
        for widget in (
            self.trigger_button, self.measure_button, self.measure_nb_button,
            self.retrigger_check, self.poll_check, self.poll_interval_spin,
            self.zero_on_button, self.zero_off_button,
        ):
            button_row.addWidget(widget)
        button_row.addStretch()
        layout.addLayout(button_row)

        grid = QtWidgets.QGridLayout()
        self.component_fields = {}
        for row, key in enumerate(("Ex", "Ey", "Ez", "|E|")):
            field = QtWidgets.QLineEdit()
            field.setReadOnly(True)
            self.component_fields[key] = field
            grid.addWidget(QtWidgets.QLabel(key), row, 0)
            grid.addWidget(field, row, 1)
        layout.addLayout(grid)
        self.detail_edit = QtWidgets.QPlainTextEdit()
        self.detail_edit.setReadOnly(True)
        layout.addWidget(self.detail_edit)
        self.tabs.addTab(tab, "Measurement")

    def _build_trend_tab(self):
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)
        toolbar = QtWidgets.QHBoxLayout()
        self.export_csv_button = QtWidgets.QPushButton("Export CSV")
        self.export_csv_button.clicked.connect(self.on_export_csv_clicked)
        self.clear_trend_button = QtWidgets.QPushButton("Clear Trend")
        self.clear_trend_button.clicked.connect(self.on_clear_trend_clicked)
        self.grid_button = QtWidgets.QPushButton("Grid On")
        self.grid_button.setCheckable(True)
        self.grid_button.setChecked(True)
        self.grid_button.toggled.connect(self.on_grid_toggled)
        toolbar.addWidget(self.export_csv_button)
        toolbar.addWidget(self.clear_trend_button)
        toolbar.addWidget(self.grid_button)
        toolbar.addStretch()
        self.trend_canvas = FieldProbeCanvas()
        self.trend_toolbar = NavigationToolbar(self.trend_canvas, self)
        layout.addLayout(toolbar)
        layout.addWidget(self.trend_toolbar)
        layout.addWidget(self.trend_canvas)
        self.tabs.addTab(tab, "Trend")

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
        self.smoke_result = QtWidgets.QPlainTextEdit()
        self.smoke_result.setReadOnly(True)
        layout.addWidget(self.smoke_button)
        layout.addWidget(self.smoke_result)
        self.tabs.addTab(tab, "Smoke Test")

    def _build_log_tab(self):
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)
        self.log_edit = QtWidgets.QPlainTextEdit()
        self.log_edit.setReadOnly(True)
        layout.addWidget(self.log_edit)
        self.tabs.addTab(tab, "Log")

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

    def _driver_display_name(self):
        return f"Driver: {type(self.dev).__module__}.{type(self.dev).__name__}"

    def _refresh_status_bar(self, state_text=None):
        if state_text is None:
            state_text = "Busy" if self._busy else "Ready"
        self.state_label.setText(f"State: {state_text}")
        self.init_label.setText(f"Init: {'initialized' if self._is_initialized else 'not initialized'}")
        self.driver_label.setText(self._driver_display_name())
        self.error_label.setText(f"Last error: {self._last_error_text}")

    def _set_busy(self, busy, label=None):
        self._busy = busy
        self.tabs.setEnabled(not busy)
        self.refresh_button.setEnabled(not busy)
        self.close_button.setEnabled(not busy)
        self._refresh_status_bar(f"Busy: {label}" if busy and label else None)

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
            if error is None:
                self._last_error_text = "none"
                self.log_message(f"{label} succeeded.")
                if on_success is not None:
                    on_success(result)
            else:
                self._last_error_text = str(error)
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
        if error is None:
            self._last_error_text = "none"
            self.log_message(f"{label} succeeded.")
            if on_success is not None:
                on_success(result)
        else:
            self._last_error_text = str(error)
            self.log_message(f"{label} failed: {type(error).__name__}: {error}")
            if on_error is not None:
                on_error(error)
            else:
                self._show_error(f"{label} Error", error)
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
            return "prb_virtual"
        return Path(driver).with_suffix("").name.lower()

    def _instantiate_driver(self, module_name):
        module = importlib.import_module(f"mpylab.device.{module_name}")
        driver_cls = getattr(module, "FIELDPROBE")
        search_paths = getattr(self.dev, "SearchPaths", None)
        if search_paths is not None:
            try:
                return driver_cls(SearchPaths=search_paths)
            except TypeError:
                pass
        return driver_cls()

    def _reset_driver_class_state(self, module_name):
        if module_name != "prb_lumiloop_lsprobe":
            return
        module = importlib.import_module("mpylab.device.prb_lumiloop_lsprobe")
        driver_cls = getattr(module, "FIELDPROBE")
        driver_cls.instances = {}
        driver_cls.main_instance = None
        driver_cls.nprb = 1
        driver_cls.data = []

    def _select_driver_from_ini(self, ini_text):
        driver, virtual = self._ini_driver_settings(ini_text)
        module_name = self._module_name_from_driver(driver, virtual)
        current_module = type(self.dev).__module__.split(".")[-1]
        if current_module == module_name:
            return
        old_driver = self.dev
        self._reset_driver_class_state(module_name)
        self.dev = self._instantiate_driver(module_name)
        self._channel_drivers = {}
        self._is_initialized = False
        self._refresh_status_bar()
        self.log_message(f"Driver switched from {type(old_driver).__module__} to {type(self.dev).__module__}.")

    def _configured_channel_count(self, ini_text):
        try:
            config = configparser.ConfigParser()
            config.read_file(io.StringIO(ini_text))
            init_value = {key.lower(): parse_ini_value(value) for key, value in config.items("Init_Value")}
            return int(init_value.get("channels", init_value.get("nr_of_channels", 1)))
        except Exception:
            return 1

    def _init_channel_driver(self, ini_text, channel):
        current_module = type(self.dev).__module__.split(".")[-1]
        if current_module == "prb_lumiloop_lsprobe":
            self._reset_driver_class_state(current_module)
            self._channel_drivers = {}
            self.dev = self._instantiate_driver(current_module)
        if current_module == "prb_lumiloop_lsprobe" and channel != 1:
            main_driver = self._instantiate_driver(current_module)
            self._channel_drivers[1] = main_driver
            main_driver.Init(ini=io.StringIO(ini_text), channel=1)
        driver = self._channel_drivers.get(channel)
        if driver is None:
            driver = self._instantiate_driver(current_module)
            self._channel_drivers[channel] = driver
        self.dev = driver
        err = self._driver_method("Init", io.StringIO(ini_text), channel)
        if current_module == "prb_lumiloop_lsprobe":
            for ch in range(1, self._configured_channel_count(ini_text) + 1):
                if ch not in self._channel_drivers:
                    other = self._instantiate_driver(current_module)
                    self._channel_drivers[ch] = other
                    other.Init(ini=io.StringIO(ini_text), channel=ch)
            self.dev = self._channel_drivers.get(channel, self.dev)
        return err

    def _split_error_value(self, result):
        if isinstance(result, tuple) and len(result) == 2:
            return result
        return 0, result

    def _display_value(self, value):
        return str(value)

    def _numeric_value(self, value):
        for name in ("get_expectation_value_as_float", "get_value"):
            method = getattr(value, name, None)
            if method is not None:
                try:
                    return float(method() if name != "get_value" else method(value._unit))
                except Exception:
                    pass
        try:
            expectation = getattr(value, "_value", value)
            if hasattr(expectation, "get_expectation_value_as_float"):
                return float(expectation.get_expectation_value_as_float())
        except Exception:
            pass
        return float(value)

    def _handle_data_result(self, result):
        err, data = self._split_error_value(result)
        if err == -1 and data is None:
            self.detail_edit.setPlainText("measurement pending")
            return
        if data is None or len(data) != 3:
            raise ValueError(f"GetData must return three components, got {data!r}")
        self._last_data = data
        labels = ("Ex", "Ey", "Ez")
        for label, value in zip(labels, data):
            self.component_fields[label].setText(str(value))
        nums = [self._numeric_value(value) for value in data]
        magnitude = math.sqrt(sum(value * value for value in nums))
        unit = getattr(data[0], "_unit", "")
        self.component_fields["|E|"].setText(f"{magnitude:g} {unit}".strip())
        self.detail_edit.setPlainText(self._display_value(result))
        self._status_fields["_last_data"].setText(str(data))
        self._append_history(nums, magnitude, unit)
        self.log_message(f"Field read: Ex={data[0]}, Ey={data[1]}, Ez={data[2]}, |E|={magnitude:g}")

    def _append_history(self, components, magnitude, unit):
        self._sample_index += 1
        self._history.append(
            {
                "index": self._sample_index,
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "frequency_hz": self.freq_spin.value_hz(),
                "Ex": components[0],
                "Ey": components[1],
                "Ez": components[2],
                "Eabs": magnitude,
                "unit": str(unit),
            }
        )
        if len(self._history) > 5000:
            self._history = self._history[-5000:]
        self.trend_canvas.update_plot(self._history)

    def _set_status_field(self, key, value):
        field = self._status_fields.get(key)
        if field is not None:
            field.setText(str(value))

    def on_load_ini_clicked(self):
        path, _filter = QtWidgets.QFileDialog.getOpenFileName(
            self, "Open INI File", "", "INI Files (*.ini *.txt);;All Files (*)"
        )
        if not path:
            return
        with open(path, "r", encoding="utf-8") as handle:
            self.ini_edit.setPlainText(handle.read())
        self.log_message(f"Loaded INI file: {path}")

    def on_save_ini_clicked(self):
        path, _filter = QtWidgets.QFileDialog.getSaveFileName(
            self, "Save INI File", "", "INI Files (*.ini *.txt);;All Files (*)"
        )
        if not path:
            return
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(self.ini_edit.toPlainText())
        clear_ini_draft(self)
        self.log_message(f"Saved INI file: {path}")

    def on_init_clicked(self):
        ini_text = self.ini_edit.toPlainText()
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
            self.refresh_status()

        self._start_task("Init", lambda: self._init_channel_driver(ini_text, channel), on_success=success)

    def on_quit_clicked(self):
        def success(result):
            self._is_initialized = False
            self._channel_drivers = {}
            self._poll_timer.stop()
            self.poll_check.setChecked(False)
            self._refresh_status_bar()
            self.log_message(f"Quit returned: {result}")

        self._start_task("Quit", lambda: self._driver_method("Quit"), on_success=success)

    def on_channel_changed(self, channel):
        driver = self._channel_drivers.get(channel)
        if driver is not None:
            self.dev = driver
            self._last_data = None
            self._refresh_status_bar()
            self.refresh_status()

    def on_set_freq_clicked(self, freq=None):
        if freq is None:
            freq = self.freq_spin.value_hz()
        self._start_task("Set Frequency", lambda: self._driver_method("SetFreq", freq), on_success=self._handle_freq)

    def on_read_freq_clicked(self):
        self._start_task("Read Frequency", lambda: self._driver_method("GetFreq"), on_success=self._handle_freq)

    def _handle_freq(self, result):
        err, value = self._split_error_value(result)
        if err == 0 and value is not None:
            self.freq_spin.set_value_hz(float(value))
        self._set_status_field("GetFreq", self._display_value(result))

    def on_trigger_clicked(self):
        self._start_task("Trigger", lambda: self._driver_method("Trigger"))

    def on_measure_clicked(self):
        self._start_task("GetData", lambda: self._driver_method("GetData"), on_success=self._handle_data_result)

    def on_measure_nb_clicked(self):
        retrigger = "on" if self.retrigger_check.isChecked() else "off"
        self._start_task(
            "GetDataNB",
            lambda: self._driver_method("GetDataNB", retrigger),
            on_success=self._handle_data_result,
        )

    def on_poll_toggled(self, checked):
        if checked:
            self._poll_timer.start(self.poll_interval_spin.value())
        else:
            self._poll_timer.stop()

    def on_poll_timeout(self):
        if not self._busy and self._is_initialized:
            self.on_measure_nb_clicked()

    def on_zero_clicked(self, state):
        self._start_task(f"Zero {state.upper()}", lambda: self._driver_method("Zero", state))

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
        if not self._history:
            self._show_error("Export CSV Error", ValueError("No trend data acquired"))
            return
        path, _filter = QtWidgets.QFileDialog.getSaveFileName(self, "Export Field Trend CSV", "", "CSV Files (*.csv);;All Files (*)")
        if not path:
            return
        try:
            with open(path, "w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=["index", "timestamp", "frequency_hz", "Ex", "Ey", "Ez", "Eabs", "unit"])
                writer.writeheader()
                writer.writerows(self._history)
            self.log_message(f"Exported trend CSV: {path}")
        except OSError as exc:
            self._show_error("Export CSV Error", exc)

    def on_clear_trend_clicked(self):
        self._history = []
        self._sample_index = 0
        self.trend_canvas.update_plot(self._history)

    def on_grid_toggled(self, checked):
        self.grid_button.setText("Grid On" if checked else "Grid Off")
        self.trend_canvas.set_grid_enabled(checked)

    def refresh_status(self):
        def task():
            snapshot = {}
            for method_name in ("GetDescription", "GetFreq", "GetVirtual", "GetBatteryState"):
                method = getattr(self.dev, method_name, None)
                if method is None:
                    snapshot[method_name] = "not implemented"
                    continue
                try:
                    snapshot[method_name] = self._display_value(method())
                except Exception as exc:
                    snapshot[method_name] = f"{type(exc).__name__}: {exc}"
            channel = getattr(self.dev, "channel", getattr(self.dev, "ch", None))
            snapshot["_channel"] = channel
            snapshot["_internal_unit"] = getattr(self.dev, "_internal_unit", "")
            snapshot["_bus_ready"] = getattr(self.dev, "bus_ready", "")
            snapshot["_last_data"] = self._last_data
            return snapshot

        def success(snapshot):
            for key, value in snapshot.items():
                self._set_status_field(key, value)
            self._refresh_status_bar()

        self._start_task("Refresh Status", task, on_success=success)

    def on_smoke_clicked(self):
        ini_text = self.ini_edit.toPlainText()
        channel = self.channel_spin.value()
        freq = self.freq_spin.value_hz()

        def task():
            lines = []
            lines.append(f"Init: {self._init_channel_driver(ini_text, channel)}")
            if hasattr(self.dev, "GetDescription"):
                lines.append(f"GetDescription: {self.dev.GetDescription()}")
            lines.append(f"SetFreq({freq}): {self.dev.SetFreq(freq)}")
            lines.append(f"Trigger: {self.dev.Trigger()}")
            lines.append(f"GetData: {self.dev.GetData()}")
            if hasattr(self.dev, "GetBatteryState"):
                lines.append(f"Battery: {self.dev.GetBatteryState()}")
            if hasattr(self.dev, "Quit"):
                lines.append(f"Quit: {self.dev.Quit()}")
            return "\n".join(lines)

        self._start_task("Smoke Test", task, on_success=self.smoke_result.setPlainText)

    def closeEvent(self, event):
        if self._active_thread is not None and self._active_thread.isRunning():
            event.ignore()
            QtWidgets.QMessageBox.information(self, "Operation in progress", "Close after current operation.")
            return
        self._poll_timer.stop()
        try:
            if hasattr(self.dev, "Quit"):
                self.dev.Quit()
        except Exception:
            pass
        super().closeEvent(event)


UI = FieldProbeWidget


def main(argv=None):
    parser = argparse.ArgumentParser(description="FieldProbe driver test utility")
    parser.add_argument("ini", nargs="?", help="Optional path to an INI file.")
    parser.add_argument("--virtual", action="store_true", help="Use the virtual field probe driver")
    parser.add_argument("--threaded", action="store_true", help="Run driver calls in worker threads")
    args = parser.parse_args(argv)

    if args.virtual:
        from mpylab.device.prb_virtual import FIELDPROBE
        dev = FIELDPROBE()
        ini = io.StringIO(std_ini_text)
    else:
        from mpylab.device.prb_virtual import FIELDPROBE
        dev = FIELDPROBE()
        if args.ini:
            try:
                with open(args.ini, "r", encoding="utf-8") as handle:
                    ini = io.StringIO(handle.read())
            except OSError as exc:
                print(f"INI file could not be read: {exc}")
                return 1
        else:
            ini = io.StringIO(std_ini_text)
        print("Driver will be selected from the INI file on Init. Using virtual field probe until then.")

    app = QtWidgets.QApplication(sys.argv if argv is None else [sys.argv[0], *argv])
    ui = FieldProbeWidget(dev, ini=ini, use_ini_draft=not args.virtual)
    ui._use_worker_threads = args.threaded
    ui.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
