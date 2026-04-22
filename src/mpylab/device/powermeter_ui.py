# -*- coding: utf-8 -*-
"""Graphical test utility for powermeter drivers."""

import argparse
import configparser
import inspect
import importlib
import io
import sys
from datetime import datetime
from pathlib import Path

from PySide6 import QtCore, QtWidgets

from mpylab.tools.configuration import parse_ini_value, strbool
from mpylab.tools.util import format_block
from mpylab.device.ui_ini_draft import IniPlainTextEdit, clear_ini_draft, load_ini_with_draft


std_ini_text = format_block("""
                [DESCRIPTION]
                description: PM template
                type:        POWERMETER
                vendor:      some company
                serialnr:    SN12345
                deviceid:    internal ID
                driver:      pm_virtual.py

                [Init_Value]
                fstart: 100e3
                fstop: 18e9
                fstep: 1
                gpib: 13
                virtual: 1
                nr_of_channels: 2

                [Channel_1]
                name: A
                unit: dBm
                swr1: 1.1
                swr2: 1.1
                value: -20 + f/1e10
                uncertainty: 0.1

                [Channel_2]
                name: B
                unit: dBm
                swr1: 1.1
                swr2: 1.1
                value: -30
                uncertainty: 0.2
                """).strip()
SETTINGS_APP = "powermeter_ui"


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


class PowerMeterWidget(QtWidgets.QWidget):
    """Threaded test UI for the common powermeter driver API."""

    def __init__(self, instance, ini=None, parent=None, use_ini_draft=True):
        super().__init__(parent)

        self.pm = instance
        self.ini_source = ini if ini is not None else io.StringIO(std_ini_text)
        self.use_ini_draft = use_ini_draft
        self._last_ini_text = ""
        self._status_fields = {}
        self._status_raw = {}
        self._busy = False
        self._is_initialized = False
        self._last_error_text = "none"
        self._last_power = None
        self._channel_drivers = {}

        self._active_thread = None
        self._active_task = None
        self._task_label = None
        self._task_result = None
        self._task_error = None
        self._task_on_success = None
        self._task_on_error = None
        self._task_on_finished = None
        self._use_worker_threads = False

        self.setWindowTitle("Powermeter Test Utility")
        self.resize(1050, 760)

        self._build_ui()
        self._load_ini()
        self.log_message("UI ready.")

    def _build_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)

        self.tabs = QtWidgets.QTabWidget()
        main_layout.addWidget(self.tabs)

        self._build_connection_tab()
        self._build_status_tab()
        self._build_measurement_tab()
        self._build_command_tab()
        self._build_smoke_tab()
        self._build_log_tab()

        bottom_bar = QtWidgets.QHBoxLayout()
        self.state_label = QtWidgets.QLabel()
        self.init_state_label = QtWidgets.QLabel()
        self.driver_label = QtWidgets.QLabel()
        self.last_error_label = QtWidgets.QLabel()
        self.last_error_label.setMinimumWidth(300)
        self.last_error_label.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)

        bottom_bar.addWidget(self.state_label)
        bottom_bar.addSpacing(10)
        bottom_bar.addWidget(self.init_state_label)
        bottom_bar.addSpacing(10)
        bottom_bar.addWidget(self.driver_label)
        bottom_bar.addSpacing(10)
        bottom_bar.addWidget(self.last_error_label, 1)

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
        self.channel_spin.valueChanged.connect(self.on_channel_changed)

        self.init_button = QtWidgets.QPushButton("Init / Re-Init")
        self.init_button.clicked.connect(self.on_init_clicked)

        self.quit_button = QtWidgets.QPushButton("Quit")
        self.quit_button.clicked.connect(self.on_quit_clicked)

        self.load_ini_button = QtWidgets.QPushButton("Load INI File")
        self.load_ini_button.clicked.connect(self.on_load_ini_clicked)

        self.save_ini_button = QtWidgets.QPushButton("Save INI File")
        self.save_ini_button.clicked.connect(self.on_save_ini_clicked)

        top_row.addWidget(QtWidgets.QLabel("Channel"))
        top_row.addWidget(self.channel_spin)
        top_row.addWidget(self.init_button)
        top_row.addWidget(self.quit_button)
        top_row.addWidget(self.load_ini_button)
        top_row.addWidget(self.save_ini_button)
        top_row.addStretch()

        self.ini_edit = IniPlainTextEdit()
        self.ini_edit.setMinimumHeight(360)

        layout.addLayout(top_row)
        layout.addWidget(self.ini_edit)
        self.tabs.addTab(tab, "Connection")

    def _build_status_tab(self):
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)

        top_row = QtWidgets.QHBoxLayout()
        self.refresh_status_button = QtWidgets.QPushButton("Refresh Status")
        self.refresh_status_button.clicked.connect(self.refresh_status)
        top_row.addWidget(self.refresh_status_button)
        top_row.addStretch()
        layout.addLayout(top_row)

        grid = QtWidgets.QGridLayout()
        status_specs = [
            ("Description", "GetDescription"),
            ("Frequency", "GetFreq"),
            ("Last Power", "_last_power"),
            ("Internal Unit", "_internal_unit"),
            ("Configured Unit", "_configured_unit"),
            ("Channel", "_channel"),
            ("Virtual", "GetVirtual"),
            ("Bus Ready", "_bus_ready"),
        ]

        for idx, (label, key) in enumerate(status_specs):
            value = QtWidgets.QLineEdit()
            value.setReadOnly(True)
            value.setText("unknown")
            self._status_fields[key] = value
            row = idx // 2
            col = (idx % 2) * 2
            grid.addWidget(QtWidgets.QLabel(label), row, col)
            grid.addWidget(value, row, col + 1)

        layout.addLayout(grid)
        layout.addStretch()
        self.tabs.addTab(tab, "Status")

    def _build_measurement_tab(self):
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)

        grid = QtWidgets.QGridLayout()
        self.freq_spin = QtWidgets.QDoubleSpinBox()
        self.freq_spin.setDecimals(3)
        self.freq_spin.setRange(0.0, 1e12)
        self.freq_spin.setValue(1e9)
        self.freq_spin.setSingleStep(1e6)
        self.freq_spin.setSuffix(" Hz")

        self.apply_freq_button = QtWidgets.QPushButton("Apply Frequency")
        self.apply_freq_button.clicked.connect(self.on_apply_freq_clicked)
        self.read_freq_button = QtWidgets.QPushButton("Readback")
        self.read_freq_button.clicked.connect(self.on_read_freq_clicked)
        self.freq_indicator = QtWidgets.QLabel("unknown")

        grid.addWidget(QtWidgets.QLabel("Frequency"), 0, 0)
        grid.addWidget(self.freq_spin, 0, 1)
        grid.addWidget(self.apply_freq_button, 0, 2)
        grid.addWidget(self.read_freq_button, 0, 3)
        grid.addWidget(self.freq_indicator, 0, 4)

        self.trigger_button = QtWidgets.QPushButton("Trigger")
        self.trigger_button.clicked.connect(self.on_trigger_clicked)
        self.measure_button = QtWidgets.QPushButton("GetData")
        self.measure_button.clicked.connect(self.on_measure_clicked)
        self.measure_nb_button = QtWidgets.QPushButton("GetDataNB")
        self.measure_nb_button.clicked.connect(self.on_measure_nb_clicked)
        self.retrigger_check = QtWidgets.QCheckBox("Retrigger after NB read")
        self.zero_on_button = QtWidgets.QPushButton("Zero On")
        self.zero_on_button.clicked.connect(lambda: self.on_zero_clicked("on"))
        self.zero_off_button = QtWidgets.QPushButton("Zero Off")
        self.zero_off_button.clicked.connect(lambda: self.on_zero_clicked("off"))

        button_row = QtWidgets.QHBoxLayout()
        button_row.addWidget(self.trigger_button)
        button_row.addWidget(self.measure_button)
        button_row.addWidget(self.measure_nb_button)
        button_row.addWidget(self.retrigger_check)
        button_row.addSpacing(20)
        button_row.addWidget(self.zero_on_button)
        button_row.addWidget(self.zero_off_button)
        button_row.addStretch()

        power_group = QtWidgets.QGroupBox("Power")
        power_layout = QtWidgets.QVBoxLayout(power_group)
        self.power_edit = QtWidgets.QLineEdit()
        self.power_edit.setReadOnly(True)
        self.power_edit.setText("unknown")
        self.power_detail_edit = QtWidgets.QPlainTextEdit()
        self.power_detail_edit.setReadOnly(True)
        power_layout.addWidget(self.power_edit)
        power_layout.addWidget(self.power_detail_edit)

        layout.addLayout(grid)
        layout.addLayout(button_row)
        layout.addWidget(power_group)
        layout.addStretch()
        self._set_freq_indicator("unknown")
        self.tabs.addTab(tab, "Measurement")

    def _build_command_tab(self):
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QFormLayout(tab)

        self.command_combo = QtWidgets.QComboBox()
        self.command_combo.setEditable(True)
        self.command_combo.addItems(["*IDN?", "*TST?", "SYST:ERR?"])
        self.regex_edit = QtWidgets.QLineEdit()
        self.regex_edit.setPlaceholderText("optional regex template, e.g. (?P<IDN>.*)")
        self.raw_query_button = QtWidgets.QPushButton("Query")
        self.raw_query_button.clicked.connect(self.on_raw_query_clicked)
        self.raw_write_button = QtWidgets.QPushButton("Write")
        self.raw_write_button.clicked.connect(self.on_raw_write_clicked)
        self.raw_answer_edit = QtWidgets.QPlainTextEdit()
        self.raw_answer_edit.setReadOnly(True)

        button_row = QtWidgets.QHBoxLayout()
        button_row.addWidget(self.raw_query_button)
        button_row.addWidget(self.raw_write_button)
        button_row.addStretch()
        button_widget = QtWidgets.QWidget()
        button_widget.setLayout(button_row)

        layout.addRow("Command", self.command_combo)
        layout.addRow("Regex", self.regex_edit)
        layout.addRow("", button_widget)
        layout.addRow("Answer", self.raw_answer_edit)
        self.tabs.addTab(tab, "Raw Command")

    def _build_smoke_tab(self):
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)

        self.run_smoke_button = QtWidgets.QPushButton("Run Smoke Test")
        self.run_smoke_button.clicked.connect(self.on_run_smoke_test_clicked)
        self.smoke_result_edit = QtWidgets.QPlainTextEdit()
        self.smoke_result_edit.setReadOnly(True)

        layout.addWidget(QtWidgets.QLabel("Smoke test: Init, GetDescription, SetFreq, Trigger, GetData, Zero Off, Quit."))
        layout.addWidget(self.run_smoke_button)
        layout.addWidget(self.smoke_result_edit)
        self.tabs.addTab(tab, "Smoke Test")

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
        driver_type = f"{type(self.pm).__module__}.{type(self.pm).__name__}"
        idn = getattr(self.pm, "IDN", "") or ""
        return f"Driver: {driver_type}" + (f" | {idn}" if idn else "")

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
            return "pm_virtual"
        return Path(driver).with_suffix("").name.lower()

    def _instantiate_driver(self, module_name):
        module = importlib.import_module(f"mpylab.device.{module_name}")
        driver_cls = getattr(module, "POWERMETER")
        search_paths = getattr(self.pm, "SearchPaths", None)
        if search_paths is not None:
            try:
                return driver_cls(SearchPaths=search_paths)
            except TypeError:
                pass
        return driver_cls()

    def _select_driver_from_ini(self, ini_text):
        driver, virtual = self._ini_driver_settings(ini_text)
        module_name = self._module_name_from_driver(driver, virtual)
        current_module = type(self.pm).__module__.split(".")[-1]
        if current_module == module_name:
            return

        old_driver = self.pm
        self._reset_driver_class_state(module_name)
        self.pm = self._instantiate_driver(module_name)
        self._channel_drivers = {}
        self._is_initialized = False
        self._status_raw = {}
        self._refresh_status_bar()
        self.log_message(
            f"Driver switched from {type(old_driver).__module__} to {type(self.pm).__module__}."
        )

    def _reset_driver_class_state(self, module_name):
        if module_name != "pm_lumiloop_lspm":
            return
        module = importlib.import_module("mpylab.device.pm_lumiloop_lspm")
        driver_cls = getattr(module, "POWERMETER")
        driver_cls.instances = {}
        driver_cls.main_instance = None
        driver_cls.data = []

    def _refresh_status_bar(self, state_text=None):
        if state_text is None:
            state_text = "Busy" if self._busy else "Ready"
        self.state_label.setText(f"State: {state_text}")
        self.init_state_label.setText(f"Init: {'initialized' if self._is_initialized else 'not initialized'}")
        self.driver_label.setText(self._driver_display_name())
        self.last_error_label.setText(f"Last error: {self._last_error_text}")

    def _set_busy(self, busy, message=None):
        self._busy = busy
        self.tabs.setEnabled(not busy)
        self.refresh_all_button.setEnabled(not busy)
        self.close_button.setEnabled(not busy)
        state_text = f"Busy: {message}" if busy and message else ("Ready" if not busy else "Busy")
        self._refresh_status_bar(state_text)

    def _start_task(self, label, func, on_success=None, on_error=None, on_finished=None):
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
                self._set_busy(False, "Ready")

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
        self._set_busy(False, "Ready")

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

    def _show_error(self, title, error):
        self._last_error_text = str(error)
        self._refresh_status_bar()
        QtWidgets.QMessageBox.critical(self, title, str(error))

    def _driver_method(self, method_name, *args, **kwargs):
        method = getattr(self.pm, method_name, None)
        if method is None:
            raise AttributeError(f"Driver does not implement {method_name}()")
        return method(*args, **kwargs)

    def _display_value(self, value):
        if isinstance(value, tuple):
            return ", ".join(str(item) for item in value)
        return str(value)

    def _set_status_field(self, key, text):
        widget = self._status_fields.get(key)
        if widget is not None:
            widget.setText(text)

    def _set_freq_indicator(self, state, message=None):
        styles = {
            "unknown": ("unknown", "#777777"),
            "pending": ("pending", "#d98c00"),
            "ok": ("match", "#2e8b57"),
            "mismatch": ("mismatch", "#b22222"),
        }
        text, color = styles.get(state, styles["unknown"])
        self.freq_indicator.setText(text)
        self.freq_indicator.setStyleSheet(f"color: {color}; font-weight: bold;")
        self.freq_indicator.setToolTip(message or "")

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
            with open(path, "r", encoding="utf-8") as handle:
                content = handle.read()
            self.ini_edit.setPlainText(content)
            self._last_ini_text = content
            self.log_message(f"Loaded INI file: {path}")
        except OSError as exc:
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
        current_module = type(self.pm).__module__.split(".")[-1]
        if current_module == "pm_lumiloop_lspm":
            self._reset_driver_class_state(current_module)
            self._channel_drivers = {}
            self.pm = self._instantiate_driver(current_module)

        def task():
            return self._init_channel_driver(ini_text, channel)

        def success(err):
            self._is_initialized = (err == 0)
            self._last_error_text = "none" if err == 0 else self._last_error_text
            self._refresh_status_bar()
            self.log_message(f"Init returned: {err}")
            self.refresh_status()

        self._start_task("Init", task, on_success=success)

    def _init_channel_driver(self, ini_text, channel):
        self._ensure_lumiloop_main_channel(ini_text, channel)
        driver = self._channel_drivers.get(channel)
        current_module = type(self.pm).__module__.split(".")[-1]
        if driver is None or type(driver).__module__.split(".")[-1] != current_module:
            driver = self._instantiate_driver(current_module)
            self._channel_drivers[channel] = driver
        self.pm = driver
        err = self._driver_method("Init", ini=io.StringIO(ini_text), channel=channel)
        self._init_remaining_lumiloop_channels(ini_text)
        self.pm = self._channel_drivers.get(channel, self.pm)
        return err

    def _configured_channel_count(self, ini_text):
        try:
            config = configparser.ConfigParser()
            config.read_file(io.StringIO(ini_text))
            init_value = {key.lower(): parse_ini_value(value) for key, value in config.items("Init_Value")}
            return int(init_value.get("channels", init_value.get("nr_of_channels", 1)))
        except Exception:
            return 1

    def _ensure_lumiloop_main_channel(self, ini_text, requested_channel):
        current_module = type(self.pm).__module__.split(".")[-1]
        if current_module != "pm_lumiloop_lspm" or requested_channel == 1 or 1 in self._channel_drivers:
            return
        main_driver = self._instantiate_driver(current_module)
        self._channel_drivers[1] = main_driver
        self.pm = main_driver
        main_driver.Init(ini=io.StringIO(ini_text), channel=1)

    def _init_remaining_lumiloop_channels(self, ini_text):
        current_module = type(self.pm).__module__.split(".")[-1]
        if current_module != "pm_lumiloop_lspm":
            return
        channel_count = self._configured_channel_count(ini_text)
        for channel in range(1, channel_count + 1):
            if channel in self._channel_drivers:
                continue
            driver = self._instantiate_driver(current_module)
            self._channel_drivers[channel] = driver
            driver.Init(ini=io.StringIO(ini_text), channel=channel)

    def on_quit_clicked(self):
        def success(result):
            self._is_initialized = False
            self._channel_drivers = {}
            self._refresh_status_bar()
            self.log_message(f"Quit returned: {result}")

        self._start_task("Quit", lambda: self._driver_method("Quit"), on_success=success)

    def on_channel_changed(self, channel):
        driver = self._channel_drivers.get(channel)
        if driver is not None:
            self.pm = driver
            self._last_power = None
            self._refresh_status_bar()
            self.refresh_status()

    def on_apply_freq_clicked(self):
        freq = self.freq_spin.value()
        self._set_freq_indicator("pending")

        def success(result):
            self._handle_freq_readback(result, expected=freq)

        self._start_task("Set Frequency", lambda: self._driver_method("SetFreq", freq), on_success=success)

    def on_read_freq_clicked(self):
        self._set_freq_indicator("pending")

        def success(result):
            self._handle_freq_readback(result)

        self._start_task("Read Frequency", lambda: self._driver_method("GetFreq"), on_success=success)

    def _handle_freq_readback(self, result, expected=None):
        value = self._extract_driver_value(result)
        try:
            freq = float(value)
        except (TypeError, ValueError):
            self._set_freq_indicator("unknown", f"Readback is not numeric: {result}")
            return

        if expected is None:
            expected = self.freq_spin.value()
        self.freq_spin.blockSignals(True)
        self.freq_spin.setValue(freq)
        self.freq_spin.blockSignals(False)
        if abs(freq - expected) <= max(1.0, abs(expected) * 1e-9):
            self._set_freq_indicator("ok")
        else:
            self._set_freq_indicator("mismatch", f"expected {expected}, got {freq}")
        self._set_status_field("GetFreq", self._display_value(result))

    def on_trigger_clicked(self):
        self._start_task("Trigger", lambda: self._driver_method("Trigger"))

    def on_measure_clicked(self):
        self._start_task("GetData", lambda: self._driver_method("GetData"), on_success=self._handle_power_result)

    def on_measure_nb_clicked(self):
        retrigger = self.retrigger_check.isChecked()

        def task():
            method = getattr(self.pm, "GetDataNB", None)
            if method is None:
                raise AttributeError("Driver does not implement GetDataNB()")
            if self._call_accepts_argument(method, "retrigger"):
                return method(retrigger)
            return method()

        self._start_task("GetDataNB", task, on_success=self._handle_power_result)

    def on_zero_clicked(self, state):
        self._start_task(f"Zero {state.upper()}", lambda: self._driver_method("Zero", state))

    def _handle_power_result(self, result):
        err, data = self._split_error_value(result)
        if err == -1 and data is None:
            self.power_edit.setText("measurement pending")
            self.power_detail_edit.setPlainText(self._display_value(result))
            self._last_power = None
            return
        self._last_power = data
        self.power_edit.setText(str(data))
        self.power_detail_edit.setPlainText(self._display_value(result))
        self._set_status_field("_last_power", str(data))
        self.log_message(f"Power read: {data}")

    def on_raw_query_clicked(self):
        cmd = self.command_combo.currentText().strip()
        tmpl = self.regex_edit.text().strip() or None
        if not cmd:
            return

        def task():
            query = getattr(self.pm, "query", None)
            if query is None:
                raise AttributeError("Driver does not expose query()")
            return query(cmd, tmpl)

        def success(result):
            self.raw_answer_edit.setPlainText(self._display_value(result))

        self._start_task("Raw Query", task, on_success=success)

    def on_raw_write_clicked(self):
        cmd = self.command_combo.currentText().strip()
        if not cmd:
            return

        def task():
            write = getattr(self.pm, "write", None)
            if write is None:
                raise AttributeError("Driver does not expose write()")
            return write(cmd)

        def success(result):
            self.raw_answer_edit.setPlainText(self._display_value(result))

        self._start_task("Raw Write", task, on_success=success)

    def on_run_smoke_test_clicked(self):
        ini_text = self.ini_edit.toPlainText()
        channel = self.channel_spin.value()
        freq = self.freq_spin.value()

        def task():
            lines = []
            err = self.pm.Init(io.StringIO(ini_text), channel)
            lines.append(f"Init: {err}")
            if hasattr(self.pm, "GetDescription"):
                lines.append(f"GetDescription: {self.pm.GetDescription()}")
            lines.append(f"SetFreq({freq}): {self.pm.SetFreq(freq)}")
            if hasattr(self.pm, "Trigger"):
                lines.append(f"Trigger: {self.pm.Trigger()}")
            lines.append(f"GetData: {self.pm.GetData()}")
            if hasattr(self.pm, "Zero"):
                lines.append(f"Zero off: {self.pm.Zero('off')}")
            if hasattr(self.pm, "Quit"):
                lines.append(f"Quit: {self.pm.Quit()}")
            return "\n".join(lines)

        def success(result):
            self._is_initialized = False
            self.smoke_result_edit.setPlainText(result)
            self._refresh_status_bar()

        self._start_task("Smoke Test", task, on_success=success)

    def refresh_all(self):
        self.refresh_status()

    def refresh_status(self, on_complete=None):
        def task():
            return self._collect_status_snapshot()

        def success(snapshot):
            self._apply_status_snapshot(snapshot)
            if on_complete is not None:
                on_complete()

        self._start_task("Refresh Status", task, on_success=success)

    def _collect_status_snapshot(self):
        snapshot = {}
        for method_name in ("GetDescription", "GetFreq", "GetVirtual"):
            method = getattr(self.pm, method_name, None)
            if method is None:
                snapshot[method_name] = {"text": "not implemented", "value": None, "err": None}
                continue
            try:
                result = method()
                err, value = self._split_error_value(result)
                snapshot[method_name] = {"text": self._display_value(result), "value": value, "err": err}
            except Exception as exc:
                snapshot[method_name] = {"text": f"{type(exc).__name__}: {exc}", "value": None, "err": exc}

        channel = getattr(self.pm, "channel", None)
        configured_unit = ""
        try:
            configured_unit = self.pm.conf[f"channel_{channel}"].get("unit", "")
        except Exception:
            configured_unit = getattr(self.pm, "levelunit", "")

        snapshot["_last_power"] = {"text": str(self._last_power), "value": self._last_power, "err": 0}
        snapshot["_internal_unit"] = {"text": str(getattr(self.pm, "_internal_unit", "")), "value": None, "err": 0}
        snapshot["_configured_unit"] = {"text": str(configured_unit), "value": configured_unit, "err": 0}
        snapshot["_channel"] = {"text": str(channel), "value": channel, "err": 0}
        snapshot["_bus_ready"] = {"text": str(getattr(self.pm, "bus_ready", "")), "value": None, "err": 0}
        return snapshot

    def _apply_status_snapshot(self, snapshot):
        self._status_raw = snapshot
        for key, data in snapshot.items():
            self._set_status_field(key, data.get("text", ""))
        freq_data = snapshot.get("GetFreq", {})
        if freq_data.get("err") == 0 and freq_data.get("value") is not None:
            self._handle_freq_readback((0, freq_data["value"]))
        self._last_error_text = "none"
        self._refresh_status_bar()

    def _split_error_value(self, result):
        if isinstance(result, tuple) and len(result) == 2:
            return result
        return 0, result

    def _extract_driver_value(self, result):
        return self._split_error_value(result)[1]

    def _call_accepts_argument(self, method, name):
        try:
            sig = inspect.signature(method)
        except (TypeError, ValueError):
            return True
        params = sig.parameters
        if any(param.kind == inspect.Parameter.VAR_POSITIONAL for param in params.values()):
            return True
        if any(param.kind == inspect.Parameter.VAR_KEYWORD for param in params.values()):
            return True
        return name in params or len(params) > 0

    def _shutdown_driver_safely(self):
        if self._active_thread is not None and self._active_thread.isRunning():
            return False
        try:
            self.pm.Quit()
        except Exception:
            pass
        return True

    def closeEvent(self, event):
        if not self._shutdown_driver_safely():
            QtWidgets.QMessageBox.information(
                self,
                "Operation in progress",
                "The current device operation is still running. Close the window after it has finished.",
            )
            event.ignore()
            return
        super().closeEvent(event)


UI = PowerMeterWidget


def _make_default_instance(args):
    if args.virtual:
        from mpylab.device.pm_virtual import POWERMETER
        return POWERMETER(), io.StringIO(std_ini_text)

    from mpylab.device.pm_virtual import POWERMETER
    print("No hardware driver selected; using virtual powermeter. Pass --virtual to make this explicit.")
    return POWERMETER(), io.StringIO(std_ini_text)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Powermeter driver test utility")
    parser.add_argument("--virtual", action="store_true", help="Use the virtual powermeter driver")
    parser.add_argument("--ini", help="Path to an INI file to preload")
    parser.add_argument(
        "--threaded",
        action="store_true",
        help="Run driver calls in worker threads. Disabled by default for VISA backend stability.",
    )
    args = parser.parse_args(argv)

    pm, ini = _make_default_instance(args)
    if args.ini:
        ini = args.ini

    app = QtWidgets.QApplication(sys.argv if argv is None else [sys.argv[0], *argv])
    window = PowerMeterWidget(pm, ini=ini, use_ini_draft=not args.virtual)
    window._use_worker_threads = args.threaded
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
