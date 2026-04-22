# -*- coding: utf-8 -*-
"""Graphical test utility for signal generator drivers."""

import argparse
import configparser
import importlib
import io
import sys
from datetime import datetime
from pathlib import Path

from PySide6 import QtCore, QtWidgets

from scuq.quantities import Quantity

from mpylab.device.device import CONVERT
from mpylab.tools.configuration import parse_ini_value, strbool
from mpylab.tools.util import format_block
from mpylab.device.ui_ini_draft import IniPlainTextEdit, clear_ini_draft, load_ini_with_draft


conv = CONVERT()
SETTINGS_ORG = "mpylab"
SETTINGS_APP = "signalgenerator_ui"
LAST_INI_PATH_KEY = "last_ini_path"


std_ini_text = format_block("""
                [DESCRIPTION]
                description: SG template
                type:        SIGNALGENERATOR
                vendor:      some company
                serialnr:    SN12345
                deviceid:    internal ID
                driver:      dummy.py

                [Init_Value]
                fstart: 100e6
                fstop: 18e9
                fstep: 1
                gpib: 15
                virtual: 0

                [Channel_1]
                name: RFOut
                level: -100
                unit: 'dBm'
                outputstate: 0
                """).strip()


class DriverTask(QtCore.QObject):
    """Execute a driver callable in a dedicated worker thread."""

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


class SignalGeneratorWidget(QtWidgets.QWidget):
    """Threaded test UI for the common signal generator driver API."""

    def __init__(self, instance, ini=None, parent=None, use_ini_draft=True):
        super().__init__(parent)

        self.sg = instance
        self.ini_source = ini if ini is not None else io.StringIO(std_ini_text)
        self.use_ini_draft = use_ini_draft
        self.ini_path = None
        self._last_ini_text = ""
        self._status_fields = {}
        self._status_raw = {}
        self._control_specs = {}
        self._busy = False
        self._is_initialized = False
        self._rf_state = "unknown"
        self._am_state = "unknown"
        self._pm_state = "unknown"
        self._last_error_text = "none"

        self._active_thread = None
        self._active_task = None
        self._task_label = None
        self._task_result = None
        self._task_error = None
        self._task_on_success = None
        self._task_on_error = None
        self._task_on_finished = None
        self._use_worker_threads = False

        self.int_unit = "dBm"

        self.setWindowTitle("Signal Generator Test Utility")
        self.resize(1180, 850)

        self._build_ui()
        self._load_ini()
        self.log_message("UI ready. RF is forced off on close.")

    def _build_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)

        self.tabs = QtWidgets.QTabWidget()
        main_layout.addWidget(self.tabs)

        self._build_connection_tab()
        self._build_status_tab()
        self._build_rf_level_tab()
        self._build_am_tab()
        self._build_pm_tab()
        self._build_smoke_tab()
        self._build_log_tab()

        bottom_bar = QtWidgets.QHBoxLayout()
        self.state_label = QtWidgets.QLabel()
        self.init_state_label = QtWidgets.QLabel()
        self.driver_label = QtWidgets.QLabel()
        self.rf_state_label = QtWidgets.QLabel()
        self.last_error_label = QtWidgets.QLabel()
        self.last_error_label.setMinimumWidth(260)
        self.last_error_label.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)

        bottom_bar.addWidget(self.state_label)
        bottom_bar.addSpacing(10)
        bottom_bar.addWidget(self.init_state_label)
        bottom_bar.addSpacing(10)
        bottom_bar.addWidget(self.rf_state_label)
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
        self.ini_edit.setMinimumHeight(340)

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
            ("Level", "GetLevel"),
            ("Virtual", "GetVirtual"),
            ("RF State", "_local_rf_state"),
            ("AM State", "_local_am_state"),
            ("PM State", "_local_pm_state"),
            ("Internal Unit", "_internal_unit"),
        ]

        for idx, (label, key) in enumerate(status_specs):
            value = QtWidgets.QLineEdit()
            value.setReadOnly(True)
            self._status_fields[key] = value
            row = idx // 2
            col = (idx % 2) * 2
            grid.addWidget(QtWidgets.QLabel(label), row, col)
            grid.addWidget(value, row, col + 1)

        layout.addLayout(grid)
        layout.addStretch()
        self.tabs.addTab(tab, "Status")

    def _build_rf_level_tab(self):
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)

        grid = QtWidgets.QGridLayout()

        self.freq_spin = QtWidgets.QDoubleSpinBox()
        self.freq_spin.setDecimals(3)
        self.freq_spin.setRange(0.0, 1e12)
        self.freq_spin.setSingleStep(1e6)
        self.freq_spin.setSuffix(" Hz")
        self.apply_freq_button = QtWidgets.QPushButton("Apply")
        self.apply_freq_button.clicked.connect(self.on_apply_freq_clicked)
        self.read_freq_button = QtWidgets.QPushButton("Readback")
        self.read_freq_button.clicked.connect(self.on_read_freq_clicked)
        self.freq_indicator = QtWidgets.QLabel("unknown")
        self._control_specs["freq"] = {"indicator": self.freq_indicator}

        grid.addWidget(QtWidgets.QLabel("Frequency"), 0, 0)
        grid.addWidget(self.freq_spin, 0, 1)
        grid.addWidget(self.apply_freq_button, 0, 2)
        grid.addWidget(self.read_freq_button, 0, 3)
        grid.addWidget(self.freq_indicator, 0, 4)

        self.level_spin = QtWidgets.QDoubleSpinBox()
        self.level_spin.setDecimals(2)
        self.level_spin.setRange(-200.0, 50.0)
        self.level_spin.setSingleStep(0.1)
        self.level_spin.setValue(-100.0)

        self.level_unit_combo = QtWidgets.QComboBox()
        self.level_unit_combo.addItems(["dBm", "dBuV", "W", "V"])

        self.apply_level_button = QtWidgets.QPushButton("Apply")
        self.apply_level_button.clicked.connect(self.on_apply_level_clicked)
        self.read_level_button = QtWidgets.QPushButton("Readback")
        self.read_level_button.clicked.connect(self.on_read_level_clicked)
        self.level_indicator = QtWidgets.QLabel("unknown")
        self._control_specs["level"] = {"indicator": self.level_indicator}

        level_box = QtWidgets.QHBoxLayout()
        level_box.addWidget(self.level_spin)
        level_box.addWidget(self.level_unit_combo)
        level_widget = QtWidgets.QWidget()
        level_widget.setLayout(level_box)

        grid.addWidget(QtWidgets.QLabel("Level"), 1, 0)
        grid.addWidget(level_widget, 1, 1)
        grid.addWidget(self.apply_level_button, 1, 2)
        grid.addWidget(self.read_level_button, 1, 3)
        grid.addWidget(self.level_indicator, 1, 4)

        rf_row = QtWidgets.QHBoxLayout()
        self.rf_on_button = QtWidgets.QPushButton("RF On")
        self.rf_on_button.clicked.connect(self.on_rf_on_clicked)
        self.rf_off_button = QtWidgets.QPushButton("RF Off")
        self.rf_off_button.clicked.connect(self.on_rf_off_clicked)
        self.rf_status = QtWidgets.QLineEdit("RF unknown")
        self.rf_status.setReadOnly(True)
        rf_row.addWidget(self.rf_on_button)
        rf_row.addWidget(self.rf_off_button)
        rf_row.addWidget(self.rf_status)
        rf_row.addStretch()

        layout.addLayout(grid)
        layout.addLayout(rf_row)
        layout.addStretch()
        self._set_indicator_state("freq", "unknown")
        self._set_indicator_state("level", "unknown")
        self.tabs.addTab(tab, "RF / Level")

    def _build_am_tab(self):
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QFormLayout(tab)

        self.amsource_combo = self._build_combo_from_driver("AM_sources", ["INT1", "INT2", "EXT1", "EXT2", "OFF"])
        self.amfreq_spin = QtWidgets.QDoubleSpinBox()
        self.amfreq_spin.setDecimals(3)
        self.amfreq_spin.setRange(0.0, 1e9)
        self.amfreq_spin.setValue(1000.0)
        self.amfreq_spin.setSuffix(" Hz")
        self.amdepth_spin = QtWidgets.QDoubleSpinBox()
        self.amdepth_spin.setDecimals(3)
        self.amdepth_spin.setRange(0.0, 1.0)
        self.amdepth_spin.setSingleStep(0.01)
        self.amdepth_spin.setValue(0.8)
        self.amwave_combo = self._build_combo_from_driver("AM_waveforms", ["SINE", "SQUARE", "TRIANGLE"])
        self.lfout_combo = self._build_combo_from_driver("AM_LFOut", ["OFF", "ON"])

        self.conf_am_button = QtWidgets.QPushButton("Configure AM")
        self.conf_am_button.clicked.connect(self.on_conf_am_clicked)
        self.am_on_button = QtWidgets.QPushButton("AM On")
        self.am_on_button.clicked.connect(self.on_am_on_clicked)
        self.am_off_button = QtWidgets.QPushButton("AM Off")
        self.am_off_button.clicked.connect(self.on_am_off_clicked)
        self.am_status = QtWidgets.QLineEdit("AM unknown")
        self.am_status.setReadOnly(True)

        button_row = QtWidgets.QHBoxLayout()
        button_row.addWidget(self.conf_am_button)
        button_row.addWidget(self.am_on_button)
        button_row.addWidget(self.am_off_button)
        button_row.addStretch()
        button_widget = QtWidgets.QWidget()
        button_widget.setLayout(button_row)

        layout.addRow("Source", self.amsource_combo)
        layout.addRow("Frequency", self.amfreq_spin)
        layout.addRow("Depth", self.amdepth_spin)
        layout.addRow("Waveform", self.amwave_combo)
        layout.addRow("LF Out", self.lfout_combo)
        layout.addRow("State", self.am_status)
        layout.addRow("", button_widget)
        self.tabs.addTab(tab, "AM")

    def _build_pm_tab(self):
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QFormLayout(tab)

        self.pmsource_combo = self._build_combo_from_driver("PM_sources", ["INT", "EXT1", "EXT2", "OFF"])
        self.pmfreq_spin = QtWidgets.QDoubleSpinBox()
        self.pmfreq_spin.setDecimals(3)
        self.pmfreq_spin.setRange(0.0, 1e9)
        self.pmfreq_spin.setValue(1000.0)
        self.pmfreq_spin.setSuffix(" Hz")
        self.pmwidth_spin = QtWidgets.QDoubleSpinBox()
        self.pmwidth_spin.setDecimals(9)
        self.pmwidth_spin.setRange(0.0, 1.0)
        self.pmwidth_spin.setValue(100e-6)
        self.pmwidth_spin.setSuffix(" s")
        self.pmdelay_spin = QtWidgets.QDoubleSpinBox()
        self.pmdelay_spin.setDecimals(9)
        self.pmdelay_spin.setRange(0.0, 10.0)
        self.pmdelay_spin.setValue(0.0)
        self.pmdelay_spin.setSuffix(" s")
        self.pmpol_combo = self._build_combo_from_driver("PM_pol", ["NORMAL", "INVERTED"])

        self.conf_pm_button = QtWidgets.QPushButton("Configure PM")
        self.conf_pm_button.clicked.connect(self.on_conf_pm_clicked)
        self.pm_on_button = QtWidgets.QPushButton("PM On")
        self.pm_on_button.clicked.connect(self.on_pm_on_clicked)
        self.pm_off_button = QtWidgets.QPushButton("PM Off")
        self.pm_off_button.clicked.connect(self.on_pm_off_clicked)
        self.pm_status = QtWidgets.QLineEdit("PM unknown")
        self.pm_status.setReadOnly(True)

        button_row = QtWidgets.QHBoxLayout()
        button_row.addWidget(self.conf_pm_button)
        button_row.addWidget(self.pm_on_button)
        button_row.addWidget(self.pm_off_button)
        button_row.addStretch()
        button_widget = QtWidgets.QWidget()
        button_widget.setLayout(button_row)

        layout.addRow("Source", self.pmsource_combo)
        layout.addRow("Frequency", self.pmfreq_spin)
        layout.addRow("Width", self.pmwidth_spin)
        layout.addRow("Delay", self.pmdelay_spin)
        layout.addRow("Polarity", self.pmpol_combo)
        layout.addRow("State", self.pm_status)
        layout.addRow("", button_widget)
        self.tabs.addTab(tab, "PM")

    def _build_smoke_tab(self):
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)

        self.smoke_include_rf_on = QtWidgets.QCheckBox("Include RF On pulse")
        self.smoke_include_rf_on.setToolTip("Disabled by default. The smoke test otherwise keeps RF off.")

        self.run_smoke_button = QtWidgets.QPushButton("Run Smoke Test")
        self.run_smoke_button.clicked.connect(self.on_run_smoke_test_clicked)

        self.smoke_result_edit = QtWidgets.QPlainTextEdit()
        self.smoke_result_edit.setReadOnly(True)

        layout.addWidget(QtWidgets.QLabel("The smoke test is conservative and sends RFOff at the end."))
        layout.addWidget(self.smoke_include_rf_on)
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

    def _build_combo_from_driver(self, attr, fallback):
        combo = QtWidgets.QComboBox()
        values = getattr(self.sg, attr, fallback)
        combo.addItems([str(value) for value in values])
        return combo

    def _refresh_driver_dependent_controls(self):
        combo_specs = [
            (self.amsource_combo, "AM_sources", ["INT1", "INT2", "EXT1", "EXT2", "OFF"]),
            (self.amwave_combo, "AM_waveforms", ["SINE", "SQUARE", "TRIANGLE"]),
            (self.lfout_combo, "AM_LFOut", ["OFF", "ON"]),
            (self.pmsource_combo, "PM_sources", ["INT", "EXT1", "EXT2", "OFF"]),
            (self.pmpol_combo, "PM_pol", ["NORMAL", "INVERTED"]),
        ]
        for combo, attr, fallback in combo_specs:
            current = combo.currentText()
            combo.clear()
            combo.addItems([str(value) for value in getattr(self.sg, attr, fallback)])
            index = combo.findText(current)
            if index >= 0:
                combo.setCurrentIndex(index)

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

    def _settings(self):
        return QtCore.QSettings(SETTINGS_ORG, SETTINGS_APP)

    def _remember_ini_path(self, path):
        if not path:
            return
        self.ini_path = str(path)
        self._settings().setValue(LAST_INI_PATH_KEY, self.ini_path)

    def log_edit_clear(self):
        self.log_edit.clear()

    def log_message(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_edit.appendPlainText(f"[{timestamp}] {message}")

    def _driver_display_name(self):
        driver_type = f"{type(self.sg).__module__}.{type(self.sg).__name__}"
        idn = getattr(self.sg, "IDN", "") or ""
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
            return "sg_virtual"
        return Path(driver).with_suffix("").name.lower()

    def _instantiate_driver(self, module_name):
        module = importlib.import_module(f"mpylab.device.{module_name}")
        driver_cls = getattr(module, "SIGNALGENERATOR")
        search_paths = getattr(self.sg, "SearchPaths", None)
        if search_paths is not None:
            try:
                return driver_cls(SearchPaths=search_paths)
            except TypeError:
                pass
        return driver_cls()

    def _select_driver_from_ini(self, ini_text):
        driver, virtual = self._ini_driver_settings(ini_text)
        module_name = self._module_name_from_driver(driver, virtual)
        current_module = type(self.sg).__module__.split(".")[-1]
        if current_module == module_name:
            return

        old_driver = self.sg
        self.sg = self._instantiate_driver(module_name)
        self._is_initialized = False
        self._rf_state = "unknown"
        self._am_state = "unknown"
        self._pm_state = "unknown"
        self._status_raw = {}
        self._refresh_driver_dependent_controls()
        self._refresh_status_bar()
        self.log_message(
            f"Driver switched from {type(old_driver).__module__} to {type(self.sg).__module__}."
        )

    def _refresh_status_bar(self, state_text=None):
        if state_text is None:
            state_text = "Busy" if self._busy else "Ready"
        self.state_label.setText(f"State: {state_text}")
        self.init_state_label.setText(f"Init: {'initialized' if self._is_initialized else 'not initialized'}")
        self.rf_state_label.setText(f"RF: {self._rf_state}")
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
        method = getattr(self.sg, method_name, None)
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
            self._remember_ini_path(path)
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
            self._remember_ini_path(path)
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

        def task():
            return self._driver_method("Init", ini=io.StringIO(ini_text), channel=channel)

        def success(err):
            self._is_initialized = (err == 0)
            self._last_error_text = "none" if err == 0 else self._last_error_text
            if err == 0:
                self._sync_local_states_from_driver()
            self._refresh_status_bar()
            self.log_message(f"Init returned: {err}")
            self.refresh_status(on_complete=self.populate_controls_from_status)

        self._start_task("Init", task, on_success=success)

    def _collect_status_snapshot(self):
        snapshot = {}
        for getter in ("GetDescription", "GetFreq", "GetLevel", "GetVirtual"):
            if not hasattr(self.sg, getter):
                continue
            try:
                err, value = self._driver_method(getter)
                snapshot[getter] = {
                    "text": self._display_value(value) if err == 0 else f"ERR {err}",
                    "value": value,
                    "err": err,
                }
            except Exception as exc:
                snapshot[getter] = {
                    "text": f"{type(exc).__name__}: {exc}",
                    "value": None,
                    "err": None,
                }

        rf_state = self._read_driver_state("GetRFState", "rf_state", self._rf_state)
        am_state = self._read_driver_state("GetAMState", "am_state", self._am_state)
        pm_state = self._read_driver_state("GetPMState", "pm_state", self._pm_state)
        snapshot["_local_rf_state"] = {"text": rf_state, "value": rf_state, "err": 0}
        snapshot["_local_am_state"] = {"text": am_state, "value": am_state, "err": 0}
        snapshot["_local_pm_state"] = {"text": pm_state, "value": pm_state, "err": 0}
        snapshot["_internal_unit"] = {
            "text": str(getattr(self.sg, "_internal_unit", "")),
            "value": getattr(self.sg, "_internal_unit", None),
            "err": 0,
        }
        return snapshot

    def _apply_status_snapshot(self, snapshot):
        self._status_raw = {}
        for getter, info in snapshot.items():
            self._set_status_field(getter, info["text"])
            self._status_raw[getter] = info["value"] if info["err"] == 0 else None
        self._rf_state = str(self._status_raw.get("_local_rf_state", self._rf_state)).lower()
        self._am_state = str(self._status_raw.get("_local_am_state", self._am_state)).lower()
        self._pm_state = str(self._status_raw.get("_local_pm_state", self._pm_state)).lower()
        self._update_readback_indicators()
        self._refresh_state_fields()

    def refresh_status(self, on_complete=None):
        def success(snapshot):
            self._apply_status_snapshot(snapshot)
            if on_complete is not None:
                on_complete()

        self._start_task("Refresh Status", self._collect_status_snapshot, on_success=success)

    def refresh_all(self):
        self.refresh_status()

    def _read_driver_state(self, getter, attr, fallback):
        if hasattr(self.sg, getter):
            try:
                err, value = self._driver_method(getter)
                if err == 0:
                    return str(value).strip().lower()
                return f"ERR {err}"
            except Exception as exc:
                return f"{type(exc).__name__}: {exc}"
        return self._state_from_driver(attr, fallback)

    def _state_from_driver(self, attr, fallback):
        value = getattr(self.sg, attr, fallback)
        if value is None:
            return "unknown"
        return str(value).strip().lower()

    def _sync_local_states_from_driver(self):
        self._rf_state = self._state_from_driver("rf_state", self._rf_state)
        self._am_state = self._state_from_driver("am_state", self._am_state)
        self._pm_state = self._state_from_driver("pm_state", self._pm_state)

    def populate_controls_from_status(self):
        freq = self._status_raw.get("GetFreq")
        if freq is not None:
            try:
                self.freq_spin.setValue(float(freq))
            except (TypeError, ValueError):
                self.log_message(f"Could not populate frequency from {freq!r}")

        level = self._status_raw.get("GetLevel")
        if level is not None:
            try:
                numeric = float(level.get_value(level._unit))
                unit = str(level._unit)
                self.level_spin.setValue(numeric)
                idx = self.level_unit_combo.findText(unit)
                if idx >= 0:
                    self.level_unit_combo.setCurrentIndex(idx)
            except Exception as exc:
                self.log_message(f"Could not populate level: {type(exc).__name__}: {exc}")
        self._update_readback_indicators()

    def _refresh_state_fields(self):
        self.rf_status.setText(f"RF is {self._rf_state}")
        self.am_status.setText(f"AM is {self._am_state}")
        self.pm_status.setText(f"PM is {self._pm_state}")
        self._refresh_status_bar()

    def _update_readback_indicators(self):
        freq = self._status_raw.get("GetFreq")
        if freq is None:
            self._set_indicator_state("freq", "unknown", "No frequency readback available.")
        else:
            try:
                current = float(self.freq_spin.value())
                readback = float(freq)
                matches = abs(current - readback) <= max(1e-6, abs(readback) * 1e-9)
            except Exception:
                matches = str(self.freq_spin.value()) == str(freq)
            self._set_indicator_state("freq", "ok" if matches else "mismatch", f"Readback: {freq!r}")

        level = self._status_raw.get("GetLevel")
        if level is None:
            self._set_indicator_state("level", "unknown", "No level readback available.")
        else:
            self._set_indicator_state("level", "ok", f"Readback: {level!r}")
            try:
                numeric = float(level.get_value(level._unit))
                unit = str(level._unit)
                self.level_spin.blockSignals(True)
                self.level_unit_combo.blockSignals(True)
                self.level_spin.setValue(numeric)
                idx = self.level_unit_combo.findText(unit)
                if idx >= 0:
                    self.level_unit_combo.setCurrentIndex(idx)
                self.level_spin.blockSignals(False)
                self.level_unit_combo.blockSignals(False)
            except Exception:
                pass

    def on_apply_freq_clicked(self):
        self._set_indicator_state("freq", "pending", "Write in progress.")
        value = self.freq_spin.value()

        def task():
            return self._driver_method("SetFreq", value)

        def success(result):
            self.log_message(f"SetFreq({value}) -> {result!r}")
            self.refresh_all()

        self._start_task("Set Frequency", task, on_success=success)

    def on_read_freq_clicked(self):
        self.refresh_status()

    def on_apply_level_clicked(self):
        self._set_indicator_state("level", "pending", "Write in progress.")
        value = self.level_spin.value()
        unit = self.level_unit_combo.currentText().strip()
        scuq_value, scuq_unit = conv.c2scuq(unit, value)
        quantity = Quantity(scuq_unit, scuq_value)

        def task():
            return self._driver_method("SetLevel", quantity)

        def success(result):
            self.log_message(f"SetLevel({quantity}) -> {result!r}")
            self.refresh_all()

        self._start_task("Set Level", task, on_success=success)

    def on_read_level_clicked(self):
        self.refresh_status()

    def on_rf_on_clicked(self):
        self._start_task("RF On", lambda: self._driver_method("RFOn"), on_success=self._rf_on_success)

    def on_rf_off_clicked(self):
        self._start_task("RF Off", lambda: self._driver_method("RFOff"), on_success=self._rf_off_success)

    def _rf_on_success(self, result):
        self._rf_state = "on"
        self.log_message(f"RFOn -> {result!r}")
        self._refresh_state_fields()

    def _rf_off_success(self, result):
        self._rf_state = "off"
        self.log_message(f"RFOff -> {result!r}")
        self._refresh_state_fields()

    def on_conf_am_clicked(self):
        source = self.amsource_combo.currentText()
        freq = self.amfreq_spin.value()
        depth = self.amdepth_spin.value()
        waveform = self.amwave_combo.currentText()
        lfout = self.lfout_combo.currentText()

        def task():
            return self._driver_method("ConfAM", source, freq, depth, waveform, lfout)

        def success(result):
            self.log_message(f"ConfAM({source}, {freq}, {depth}, {waveform}, {lfout}) -> {result!r}")
            self.refresh_all()

        self._start_task("Configure AM", task, on_success=success)

    def on_am_on_clicked(self):
        self._start_task("AM On", lambda: self._driver_method("AMOn"), on_success=self._am_on_success)

    def on_am_off_clicked(self):
        self._start_task("AM Off", lambda: self._driver_method("AMOff"), on_success=self._am_off_success)

    def _am_on_success(self, result):
        self._am_state = "on"
        self.log_message(f"AMOn -> {result!r}")
        self._refresh_state_fields()

    def _am_off_success(self, result):
        self._am_state = "off"
        self.log_message(f"AMOff -> {result!r}")
        self._refresh_state_fields()

    def on_conf_pm_clicked(self):
        source = self.pmsource_combo.currentText()
        freq = self.pmfreq_spin.value()
        pol = self.pmpol_combo.currentText()
        width = self.pmwidth_spin.value()
        delay = self.pmdelay_spin.value()

        def task():
            return self._driver_method("ConfPM", source, freq, pol, width, delay)

        def success(result):
            self.log_message(f"ConfPM({source}, {freq}, {pol}, {width}, {delay}) -> {result!r}")
            self.refresh_all()

        self._start_task("Configure PM", task, on_success=success)

    def on_pm_on_clicked(self):
        self._start_task("PM On", lambda: self._driver_method("PMOn"), on_success=self._pm_on_success)

    def on_pm_off_clicked(self):
        self._start_task("PM Off", lambda: self._driver_method("PMOff"), on_success=self._pm_off_success)

    def _pm_on_success(self, result):
        self._pm_state = "on"
        self.log_message(f"PMOn -> {result!r}")
        self._refresh_state_fields()

    def _pm_off_success(self, result):
        self._pm_state = "off"
        self.log_message(f"PMOff -> {result!r}")
        self._refresh_state_fields()

    def _run_smoke_test(self):
        results = []
        if hasattr(self.sg, "GetDescription"):
            results.append(f"GetDescription: {self._driver_method('GetDescription')!r}")
        if hasattr(self.sg, "GetFreq"):
            results.append(f"GetFreq: {self._driver_method('GetFreq')!r}")
        if hasattr(self.sg, "GetLevel"):
            results.append(f"GetLevel: {self._driver_method('GetLevel')!r}")

        freq = self.freq_spin.value()
        if hasattr(self.sg, "SetFreq"):
            results.append(f"SetFreq({freq!r}): {self._driver_method('SetFreq', freq)!r}")

        if self.smoke_include_rf_on.isChecked():
            results.append(f"RFOn: {self._driver_method('RFOn')!r}")
        results.append(f"RFOff: {self._driver_method('RFOff')!r}")
        return results

    def on_run_smoke_test_clicked(self):
        def success(lines):
            self._rf_state = "off"
            text = "\n".join(lines)
            self.smoke_result_edit.setPlainText(text)
            self.log_message("Smoke test completed.")
            for line in lines:
                self.log_message(f"  {line}")
            self.refresh_all()

        self._start_task("Smoke Test", self._run_smoke_test, on_success=success)

    def _shutdown_driver_safely(self):
        """Always try to turn RF off before closing the UI."""
        try:
            if hasattr(self.sg, "RFOff"):
                self.sg.RFOff()
                self._rf_state = "off"
                self.log_message("Safety shutdown: RFOff sent.")
        except Exception as exc:
            self.log_message(f"Safety shutdown RFOff failed: {type(exc).__name__}: {exc}")
        try:
            if hasattr(self.sg, "Quit"):
                self.sg.Quit()
                self.log_message("Driver Quit sent.")
        except Exception as exc:
            self.log_message(f"Driver Quit failed: {type(exc).__name__}: {exc}")

    def closeEvent(self, event):
        if self._busy and self._active_thread is not None:
            QtWidgets.QMessageBox.information(
                self,
                "Operation in progress",
                "Please wait until the current device operation has finished.",
            )
            event.ignore()
            return
        self._shutdown_driver_safely()
        super().closeEvent(event)


UI = SignalGeneratorWidget


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Start the signal generator test utility.")
    parser.add_argument("ini", nargs="?", help="Optional path to an INI file.")
    parser.add_argument(
        "--virtual",
        action="store_true",
        help="Use the virtual signal generator driver.",
    )
    parser.add_argument(
        "--threaded",
        action="store_true",
        help="Run driver calls in worker threads. Disabled by default for VISA backend stability.",
    )
    args = parser.parse_args()

    app = QtWidgets.QApplication(sys.argv)
    QtCore.QCoreApplication.setOrganizationName(SETTINGS_ORG)
    QtCore.QCoreApplication.setApplicationName(SETTINGS_APP)

    ini_path = None
    if args.ini:
        ini_path = args.ini
        try:
            with open(args.ini, "r", encoding="utf-8") as handle:
                ini = io.StringIO(handle.read())
        except OSError as exc:
            print(f"INI file could not be read: {exc}")
            sys.exit(1)
    elif not args.virtual:
        settings = QtCore.QSettings(SETTINGS_ORG, SETTINGS_APP)
        last_ini_path = settings.value(LAST_INI_PATH_KEY, "", str)
        if last_ini_path:
            try:
                with open(last_ini_path, "r", encoding="utf-8") as handle:
                    ini = io.StringIO(handle.read())
                ini_path = last_ini_path
                print(f"Loaded last INI file: {last_ini_path}")
            except OSError as exc:
                print(f"Last INI file could not be read: {exc}")
                ini = io.StringIO(std_ini_text)
        else:
            ini = io.StringIO(std_ini_text)
    else:
        ini = io.StringIO(std_ini_text.replace("virtual: 0", "virtual: 1" if args.virtual else "virtual: 0"))

    if args.virtual:
        from mpylab.device.sg_virtual import SIGNALGENERATOR
        sg = SIGNALGENERATOR()
    else:
        from mpylab.device.sg_virtual import SIGNALGENERATOR
        sg = SIGNALGENERATOR()
        print("Driver will be selected from the INI file on Init. Using virtual signal generator until then.")

    window = SignalGeneratorWidget(sg, ini=ini, use_ini_draft=not args.virtual)
    if ini_path is not None:
        window._remember_ini_path(ini_path)
    window._use_worker_threads = args.threaded
    window.show()
    sys.exit(app.exec())
