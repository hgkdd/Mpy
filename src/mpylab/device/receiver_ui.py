# -*- coding: utf-8 -*-
"""Graphical test utility for receiver drivers."""

import argparse
import configparser
import importlib
import io
import sys
from datetime import datetime
from pathlib import Path

from PySide6 import QtCore, QtWidgets

from mpylab.device.ui_frequency import FrequencyControl
from mpylab.device.ui_ini_draft import IniPlainTextEdit, clear_ini_draft, load_ini_with_draft
from mpylab.tools.configuration import parse_ini_value, strbool
from mpylab.tools.util import format_block


std_ini_text = format_block("""
                [DESCRIPTION]
                description: Virtual Receiver
                type:        RECEIVER
                vendor:      mpylab
                serialnr:    VIRTUAL
                deviceid:    receiver_virtual
                driver:      receiver_virtual.py

                [Init_Value]
                fstart: 9e3
                fstop: 30e6
                fstep: 1
                visa:
                virtual: 1
                nr_of_channels: 1

                [Channel_1]
                name: RFIn
                min_attenuation: 10
                meas_time: 0.05
                preamplifier: off
                unit: dBuV
                attenuation: auto
                rbw: auto
                detector: PEAK
                """).strip()
SETTINGS_APP = "receiver_ui"


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


class ReceiverWidget(QtWidgets.QWidget):
    """Thread-aware test UI for the common receiver driver API."""

    def __init__(self, instance, ini=None, parent=None, use_ini_draft=True):
        super().__init__(parent)

        self.rx = instance
        self.ini_source = ini if ini is not None else io.StringIO(std_ini_text)
        self.use_ini_draft = use_ini_draft
        self._last_ini_text = ""
        self._status_fields = {}
        self._status_raw = {}
        self._busy = False
        self._is_initialized = False
        self._last_error_text = "none"
        self._last_reading = None
        self._active_thread = None
        self._active_task = None
        self._task_label = None
        self._task_result = None
        self._task_error = None
        self._task_on_success = None
        self._task_on_error = None
        self._task_on_finished = None
        self._use_worker_threads = False
        self._poll_timer = QtCore.QTimer(self)
        self._poll_timer.timeout.connect(self.on_poll_timeout)

        self.setWindowTitle("Receiver Test Utility")
        self.resize(1120, 780)

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

        bottom = QtWidgets.QHBoxLayout()
        self.state_label = QtWidgets.QLabel()
        self.init_state_label = QtWidgets.QLabel()
        self.driver_label = QtWidgets.QLabel()
        self.last_error_label = QtWidgets.QLabel()
        self.last_error_label.setMinimumWidth(300)
        self.last_error_label.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        bottom.addWidget(self.state_label)
        bottom.addSpacing(10)
        bottom.addWidget(self.init_state_label)
        bottom.addSpacing(10)
        bottom.addWidget(self.driver_label)
        bottom.addSpacing(10)
        bottom.addWidget(self.last_error_label, 1)

        self.refresh_all_button = QtWidgets.QPushButton("Refresh All")
        self.refresh_all_button.clicked.connect(self.refresh_all)
        bottom.addWidget(self.refresh_all_button)

        self.close_button = QtWidgets.QPushButton("Close")
        self.close_button.clicked.connect(self.close)
        bottom.addWidget(self.close_button)

        main_layout.addLayout(bottom)
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
        row = QtWidgets.QHBoxLayout()
        self.refresh_status_button = QtWidgets.QPushButton("Refresh Status")
        self.refresh_status_button.clicked.connect(self.refresh_status)
        row.addWidget(self.refresh_status_button)
        row.addStretch()
        layout.addLayout(row)

        grid = QtWidgets.QGridLayout()
        specs = [
            ("Description", "GetDescription"),
            ("Frequency", "GetFreq"),
            ("RBW", "GetResolutionBandwidth"),
            ("Measurement Time", "GetMeasTime"),
            ("Attenuation", "GetAttenuation"),
            ("Min. Attenuation", "GetMinAttenuation"),
            ("Detector", "GetDetector"),
            ("Preamplifier", "GetPreamplifier"),
            ("Virtual", "GetVirtual"),
            ("Last Reading", "_last_reading"),
        ]
        for idx, (label, key) in enumerate(specs):
            edit = QtWidgets.QLineEdit()
            edit.setReadOnly(True)
            edit.setText("unknown")
            self._status_fields[key] = edit
            row_idx = idx // 2
            col = (idx % 2) * 2
            grid.addWidget(QtWidgets.QLabel(label), row_idx, col)
            grid.addWidget(edit, row_idx, col + 1)
        layout.addLayout(grid)
        layout.addStretch()
        self.tabs.addTab(tab, "Status")

    def _build_measurement_tab(self):
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)

        main_group = QtWidgets.QGroupBox("Measurement")
        main_layout = QtWidgets.QGridLayout(main_group)
        self.freq_control = FrequencyControl(default_hz=1e6)
        self.freq_control.valueApplied.connect(self.on_set_freq_clicked)
        self.freq_indicator = QtWidgets.QLabel("unknown")
        self.freq_indicator.setMinimumWidth(90)
        self.read_freq_button = QtWidgets.QPushButton("Read Frequency")
        self.read_freq_button.clicked.connect(self.on_read_freq_clicked)
        main_layout.addWidget(QtWidgets.QLabel("Frequency"), 0, 0)
        main_layout.addWidget(self.freq_control, 0, 1)
        main_layout.addWidget(self.freq_indicator, 0, 2)
        main_layout.addWidget(self.read_freq_button, 0, 3)

        self.rbw_control = FrequencyControl(default_hz=9e3)
        self.rbw_control.valueApplied.connect(self.on_set_rbw_clicked)
        self.rbw_auto_check = QtWidgets.QCheckBox("Auto")
        self.rbw_auto_check.toggled.connect(self.on_rbw_auto_toggled)
        main_layout.addWidget(QtWidgets.QLabel("RBW"), 1, 0)
        main_layout.addWidget(self.rbw_control, 1, 1)
        main_layout.addWidget(self.rbw_auto_check, 1, 2)

        self.meas_time_spin = QtWidgets.QDoubleSpinBox()
        self.meas_time_spin.setRange(0.0, 10_000.0)
        self.meas_time_spin.setDecimals(6)
        self.meas_time_spin.setValue(0.05)
        self.meas_time_spin.setSuffix(" s")
        self.set_meas_time_button = QtWidgets.QPushButton("Apply")
        self.set_meas_time_button.clicked.connect(self.on_set_meas_time_clicked)
        main_layout.addWidget(QtWidgets.QLabel("Measurement Time"), 2, 0)
        main_layout.addWidget(self.meas_time_spin, 2, 1)
        main_layout.addWidget(self.set_meas_time_button, 2, 3)

        self.detector_combo = QtWidgets.QComboBox()
        self.detector_combo.addItems(["PEAK", "QPEAK", "AVERAGE"])
        self.detector_combo.currentTextChanged.connect(self.on_detector_changed)
        main_layout.addWidget(QtWidgets.QLabel("Detector"), 3, 0)
        main_layout.addWidget(self.detector_combo, 3, 1)

        self.preamp_combo = QtWidgets.QComboBox()
        self.preamp_combo.addItems(["OFF", "ON"])
        self.preamp_combo.currentTextChanged.connect(self.on_preamp_changed)
        main_layout.addWidget(QtWidgets.QLabel("Preamplifier"), 4, 0)
        main_layout.addWidget(self.preamp_combo, 4, 1)

        att_group = QtWidgets.QGroupBox("Attenuation")
        att_layout = QtWidgets.QGridLayout(att_group)
        self.att_spin = QtWidgets.QDoubleSpinBox()
        self.att_spin.setRange(0.0, 200.0)
        self.att_spin.setDecimals(2)
        self.att_spin.setSuffix(" dB")
        self.att_auto_check = QtWidgets.QCheckBox("Auto")
        self.att_auto_check.toggled.connect(self.on_att_auto_toggled)
        self.set_att_button = QtWidgets.QPushButton("Apply Attenuation")
        self.set_att_button.clicked.connect(self.on_set_attenuation_clicked)
        self.min_att_spin = QtWidgets.QDoubleSpinBox()
        self.min_att_spin.setRange(0.0, 200.0)
        self.min_att_spin.setDecimals(2)
        self.min_att_spin.setSuffix(" dB")
        self.set_min_att_button = QtWidgets.QPushButton("Apply Min.")
        self.set_min_att_button.clicked.connect(self.on_set_min_attenuation_clicked)
        att_layout.addWidget(QtWidgets.QLabel("Attenuation"), 0, 0)
        att_layout.addWidget(self.att_spin, 0, 1)
        att_layout.addWidget(self.att_auto_check, 0, 2)
        att_layout.addWidget(self.set_att_button, 0, 3)
        att_layout.addWidget(QtWidgets.QLabel("Minimum"), 1, 0)
        att_layout.addWidget(self.min_att_spin, 1, 1)
        att_layout.addWidget(self.set_min_att_button, 1, 3)

        action_row = QtWidgets.QHBoxLayout()
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
        action_row.addWidget(self.trigger_button)
        action_row.addWidget(self.measure_button)
        action_row.addWidget(self.measure_nb_button)
        action_row.addWidget(self.retrigger_check)
        action_row.addWidget(self.poll_check)
        action_row.addWidget(self.poll_interval_spin)
        action_row.addStretch()

        self.reading_label = QtWidgets.QLabel("No reading")
        font = self.reading_label.font()
        font.setPointSize(24)
        font.setBold(True)
        self.reading_label.setFont(font)
        self.reading_label.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)

        layout.addWidget(main_group)
        layout.addWidget(att_group)
        layout.addLayout(action_row)
        layout.addWidget(self.reading_label)
        layout.addStretch()
        self.tabs.addTab(tab, "Measurement")
        self._set_freq_indicator("unknown")

    def _build_command_tab(self):
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
        layout.addWidget(QtWidgets.QLabel("Smoke test: Init, status readback, SetFreq, Trigger, GetDataNB, Quit."))
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
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_edit.appendPlainText(f"[{timestamp}] {message}")

    def _driver_display_name(self):
        driver_type = f"{type(self.rx).__module__}.{type(self.rx).__name__}"
        idn = getattr(self.rx, "IDN", "") or ""
        return f"Driver: {driver_type}" + (f" | {idn}" if idn else "")

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
        method = getattr(self.rx, method_name, None)
        if method is None:
            raise AttributeError(f"Driver does not implement {method_name}()")
        return method(*args, **kwargs)

    def _split_error_value(self, result):
        if isinstance(result, tuple) and len(result) >= 2:
            return result[0], result[1]
        return 0, result

    def _display_value(self, value):
        return str(value)

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
            return "receiver_virtual"
        return Path(driver).with_suffix("").name.lower()

    def _instantiate_driver(self, module_name):
        module = importlib.import_module(f"mpylab.device.{module_name}")
        driver_cls = getattr(module, "RECEIVER")
        search_paths = getattr(self.rx, "SearchPaths", None)
        if search_paths is not None:
            try:
                return driver_cls(SearchPaths=search_paths)
            except TypeError:
                pass
        return driver_cls()

    def _select_driver_from_ini(self, ini_text):
        driver, virtual = self._ini_driver_settings(ini_text)
        module_name = self._module_name_from_driver(driver, virtual)
        current_module = type(self.rx).__module__.split(".")[-1]
        if current_module == module_name:
            return
        old_driver = self.rx
        self.rx = self._instantiate_driver(module_name)
        self._is_initialized = False
        self._status_raw = {}
        self._last_reading = None
        self._refresh_status_bar()
        self.log_message(f"Driver switched from {type(old_driver).__module__} to {type(self.rx).__module__}.")

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
        path, _filter = QtWidgets.QFileDialog.getOpenFileName(self, "Open INI File", "", "INI Files (*.ini *.txt);;All Files (*)")
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
        path, _filter = QtWidgets.QFileDialog.getSaveFileName(self, "Save INI File", "", "INI Files (*.ini *.txt);;All Files (*)")
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

        self._start_task("Init", lambda: self._driver_method("Init", ini=io.StringIO(ini_text), channel=channel), on_success=success)

    def on_quit_clicked(self):
        def success(result):
            self._is_initialized = False
            self._poll_timer.stop()
            self.poll_check.setChecked(False)
            self._refresh_status_bar()
            self.log_message(f"Quit returned: {result}")

        self._start_task("Quit", lambda: self._driver_method("Quit"), on_success=success)

    def on_set_freq_clicked(self, freq=None):
        freq = self.freq_control.value_hz() if freq is None else freq
        self._set_freq_indicator("pending")

        def success(result):
            _err, value = self._split_error_value(result)
            try:
                readback = float(value)
            except (TypeError, ValueError):
                self._set_freq_indicator("unknown", f"Readback is not numeric: {result}")
                return
            self.freq_control.set_value_hz(readback)
            if abs(readback - freq) <= max(1.0, abs(freq) * 1e-9):
                self._set_freq_indicator("ok")
            else:
                self._set_freq_indicator("mismatch", f"expected {freq}, got {readback}")
            self._set_status_field("GetFreq", self._display_value(result))

        self._start_task("Set Frequency", lambda: self._driver_method("SetFreq", freq), on_success=success)

    def on_read_freq_clicked(self):
        self._set_freq_indicator("pending")

        def success(result):
            _err, value = self._split_error_value(result)
            try:
                freq = float(value)
            except (TypeError, ValueError):
                self._set_freq_indicator("unknown", f"Readback is not numeric: {result}")
                return
            self.freq_control.set_value_hz(freq)
            self._set_freq_indicator("ok")
            self._set_status_field("GetFreq", self._display_value(result))

        self._start_task("Read Frequency", lambda: self._driver_method("GetFreq"), on_success=success)

    def on_set_rbw_clicked(self, rbw=None):
        rbw = self.rbw_control.value_hz() if rbw is None else rbw
        self.rbw_auto_check.setChecked(False)
        self._start_task("Set RBW", lambda: self._driver_method("SetResolutionBandwidth", rbw), on_success=self._handle_rbw)

    def on_rbw_auto_toggled(self, checked):
        self.rbw_control.set_enabled(not checked)
        if checked:
            self._start_task("Set RBW Auto", lambda: self._driver_method("SetResolutionBandwidth", None), on_success=self._handle_rbw)

    def _handle_rbw(self, result):
        _err, value = self._split_error_value(result)
        try:
            self.rbw_control.set_value_hz(float(value))
        except (TypeError, ValueError):
            pass
        self._set_status_field("GetResolutionBandwidth", self._display_value(result))

    def on_set_meas_time_clicked(self):
        value = self.meas_time_spin.value()
        self._start_task("Set Measurement Time", lambda: self._driver_method("SetMeasTime", value), on_success=self._handle_meas_time)

    def _handle_meas_time(self, result):
        _err, value = self._split_error_value(result)
        try:
            self.meas_time_spin.setValue(float(value))
        except (TypeError, ValueError):
            pass
        self._set_status_field("GetMeasTime", self._display_value(result))

    def on_detector_changed(self, detector):
        if self._is_initialized:
            self._start_task("Set Detector", lambda: self._driver_method("SetDetector", detector), on_success=lambda result: self._set_status_field("GetDetector", self._display_value(result)))

    def on_preamp_changed(self, state):
        if self._is_initialized:
            self._start_task("Set Preamplifier", lambda: self._driver_method("SetPreamplifier", state), on_success=lambda result: self._set_status_field("GetPreamplifier", self._display_value(result)))

    def on_att_auto_toggled(self, checked):
        self.att_spin.setEnabled(not checked)
        if checked:
            self._start_task("Set Attenuation Auto", lambda: self._driver_method("SetAttenuation", None), on_success=self._handle_attenuation)

    def on_set_attenuation_clicked(self):
        value = None if self.att_auto_check.isChecked() else self.att_spin.value()
        self._start_task("Set Attenuation", lambda: self._driver_method("SetAttenuation", value), on_success=self._handle_attenuation)

    def _handle_attenuation(self, result):
        _err, value = self._split_error_value(result)
        try:
            self.att_spin.setValue(float(value))
        except (TypeError, ValueError):
            pass
        self._set_status_field("GetAttenuation", self._display_value(result))

    def on_set_min_attenuation_clicked(self):
        value = self.min_att_spin.value()
        self._start_task("Set Min Attenuation", lambda: self._driver_method("SetMinAttenuation", value), on_success=self._handle_min_attenuation)

    def _handle_min_attenuation(self, result):
        _err, value = self._split_error_value(result)
        try:
            self.min_att_spin.setValue(float(value))
        except (TypeError, ValueError):
            pass
        self._set_status_field("GetMinAttenuation", self._display_value(result))

    def on_trigger_clicked(self):
        self._start_task("Trigger", lambda: self._driver_method("Trigger"))

    def on_measure_clicked(self):
        self._start_task("GetData", lambda: self._driver_method("GetData"), on_success=self._handle_reading)

    def on_measure_nb_clicked(self):
        retrigger = self.retrigger_check.isChecked()
        self._start_task("GetDataNB", lambda: self._driver_method("GetDataNB", retrigger), on_success=self._handle_reading)

    def on_poll_toggled(self, checked):
        if checked:
            self._poll_timer.start(self.poll_interval_spin.value())
        else:
            self._poll_timer.stop()

    def on_poll_timeout(self):
        if not self._busy and self._is_initialized:
            self.on_measure_nb_clicked()

    def _handle_reading(self, result):
        _err, value = self._split_error_value(result)
        self._last_reading = value
        self.reading_label.setText(str(value))
        self._set_status_field("_last_reading", str(value))

    def on_raw_query_clicked(self):
        cmd = self.raw_command_edit.text().strip()
        if not cmd:
            return
        self._start_task("Raw Query", lambda: self.rx.query(cmd), on_success=lambda result: self.raw_output.appendPlainText(f"> {cmd}\n{result}"))

    def on_raw_write_clicked(self):
        cmd = self.raw_command_edit.text().strip()
        if not cmd:
            return
        self._start_task("Raw Write", lambda: self.rx.write(cmd), on_success=lambda result: self.raw_output.appendPlainText(f"> {cmd}\n{result}"))

    def on_smoke_clicked(self):
        ini_text = self.ini_edit.toPlainText()
        channel = self.channel_spin.value()
        freq = self.freq_control.value_hz()
        try:
            self._select_driver_from_ini(ini_text)
        except Exception as exc:
            self._show_error("Driver Selection Error", exc)
            return

        def task():
            lines = []
            lines.append(f"Init: {self.rx.Init(ini=io.StringIO(ini_text), channel=channel)}")
            for getter in ("GetDescription", "GetFreq", "GetResolutionBandwidth", "GetDetector", "GetPreamplifier"):
                if hasattr(self.rx, getter):
                    lines.append(f"{getter}: {getattr(self.rx, getter)()!r}")
            lines.append(f"SetFreq({freq}): {self.rx.SetFreq(freq)!r}")
            lines.append(f"Trigger: {self.rx.Trigger()!r}")
            lines.append(f"GetDataNB: {self.rx.GetDataNB(True)!r}")
            if hasattr(self.rx, "Quit"):
                lines.append(f"Quit: {self.rx.Quit()!r}")
            return "\n".join(lines)

        def success(output):
            self.smoke_output.setPlainText(output)
            self._is_initialized = False
            self._refresh_status_bar()

        self._start_task("Smoke Test", task, on_success=success)

    def refresh_status(self, on_complete=None):
        getters = [
            "GetDescription",
            "GetFreq",
            "GetResolutionBandwidth",
            "GetMeasTime",
            "GetAttenuation",
            "GetMinAttenuation",
            "GetDetector",
            "GetPreamplifier",
            "GetVirtual",
        ]

        def task():
            snapshot = {}
            for getter in getters:
                if not hasattr(self.rx, getter):
                    snapshot[getter] = "not implemented"
                    continue
                try:
                    snapshot[getter] = getattr(self.rx, getter)()
                except Exception as exc:
                    snapshot[getter] = f"{type(exc).__name__}: {exc}"
            snapshot["_last_reading"] = self._last_reading
            return snapshot

        def success(snapshot):
            self._status_raw = snapshot
            for key, value in snapshot.items():
                self._set_status_field(key, self._display_value(value))
            self._populate_controls_from_status(snapshot)
            if on_complete is not None:
                on_complete()

        self._start_task("Refresh Status", task, on_success=success)

    def _populate_controls_from_status(self, snapshot):
        value = self._value_from_result(snapshot.get("GetFreq"))
        if value is not None:
            try:
                self.freq_control.set_value_hz(float(value))
                self._set_freq_indicator("ok")
            except (TypeError, ValueError):
                pass
        value = self._value_from_result(snapshot.get("GetResolutionBandwidth"))
        if value is not None:
            try:
                self.rbw_control.set_value_hz(float(value))
            except (TypeError, ValueError):
                pass
        value = self._value_from_result(snapshot.get("GetMeasTime"))
        if value is not None:
            try:
                self.meas_time_spin.setValue(float(value))
            except (TypeError, ValueError):
                pass
        value = self._value_from_result(snapshot.get("GetAttenuation"))
        if value is not None:
            try:
                self.att_spin.setValue(float(value))
            except (TypeError, ValueError):
                pass
        value = self._value_from_result(snapshot.get("GetMinAttenuation"))
        if value is not None:
            try:
                self.min_att_spin.setValue(float(value))
            except (TypeError, ValueError):
                pass
        value = self._value_from_result(snapshot.get("GetDetector"))
        if isinstance(value, str) and value.upper() in ("PEAK", "QPEAK", "AVERAGE"):
            self.detector_combo.setCurrentText(value.upper())
        value = self._value_from_result(snapshot.get("GetPreamplifier"))
        if isinstance(value, str) and value.upper() in ("ON", "OFF"):
            self.preamp_combo.setCurrentText(value.upper())

    def _value_from_result(self, result):
        if isinstance(result, tuple) and len(result) >= 2:
            return result[1]
        return result

    def refresh_all(self):
        self.refresh_status()

    def closeEvent(self, event):
        if self._busy and self._active_thread is not None:
            QtWidgets.QMessageBox.information(self, "Operation in progress", "Please wait until the current device operation has finished.")
            event.ignore()
            return
        self._poll_timer.stop()
        try:
            if hasattr(self.rx, "Quit"):
                self.rx.Quit()
        except Exception as exc:
            self.log_message(f"Driver Quit failed: {type(exc).__name__}: {exc}")
        super().closeEvent(event)


UI = ReceiverWidget


def _make_default_instance(args):
    from mpylab.device.receiver_virtual import RECEIVER

    ini = io.StringIO(std_ini_text.replace("virtual: 1", "virtual: 1" if args.virtual else "virtual: 0"))
    if not args.virtual:
        print("Driver will be selected from the INI file on Init. Using virtual receiver until then.")
    return RECEIVER(), ini


def main(argv=None):
    parser = argparse.ArgumentParser(description="Receiver driver test utility")
    parser.add_argument("ini", nargs="?", help="Optional path to an INI file.")
    parser.add_argument("--virtual", action="store_true", help="Use the virtual receiver driver.")
    parser.add_argument(
        "--threaded",
        action="store_true",
        help="Run driver calls in worker threads. Disabled by default for VISA backend stability.",
    )
    args = parser.parse_args(argv)

    rx, ini = _make_default_instance(args)
    if args.ini:
        try:
            with open(args.ini, "r", encoding="utf-8") as handle:
                ini = io.StringIO(handle.read())
        except OSError as exc:
            print(f"INI file could not be read: {exc}")
            return 1

    app = QtWidgets.QApplication(sys.argv if argv is None else [sys.argv[0], *argv])
    window = ReceiverWidget(rx, ini=ini, use_ini_draft=not args.virtual)
    window._use_worker_threads = args.threaded
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
