# -*- coding: utf-8 -*-
"""Graphical test utility for motor controller drivers."""

import argparse
import configparser
import importlib
import io
import math
import sys
from datetime import datetime
from pathlib import Path

from PySide6 import QtCore, QtGui, QtWidgets

from mpylab.device.mc_virtual import MOTORCONTROLLER as VIRTUAL_MOTORCONTROLLER
from mpylab.device.mc_virtual import std_ini_text
from mpylab.device.ui_ini_draft import IniPlainTextEdit, clear_ini_draft, load_ini_with_draft
from mpylab.tools.configuration import parse_ini_value, strbool


SETTINGS_APP = "motorcontroller_ui"


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


class PositionDial(QtWidgets.QWidget):
    """Simple visual angle and movement direction indicator."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._position = 0.0
        self._direction = 0
        self.setMinimumSize(260, 260)

    def set_state(self, position, direction):
        """Update displayed angle and movement direction."""
        try:
            self._position = float(position) % 360.0
        except (TypeError, ValueError):
            self._position = 0.0
        try:
            self._direction = int(direction)
        except (TypeError, ValueError):
            self._direction = 0
        self.update()

    def paintEvent(self, event):
        """Paint a compact compass-like motor position display."""
        del event
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        rect = self.rect().adjusted(16, 16, -16, -16)
        side = min(rect.width(), rect.height())
        center = self.rect().center()
        radius = side / 2.0

        painter.setPen(QtGui.QPen(QtGui.QColor("#2f3a45"), 2))
        painter.setBrush(QtGui.QColor("#f4f7f9"))
        painter.drawEllipse(center, int(radius), int(radius))

        painter.setPen(QtGui.QPen(QtGui.QColor("#8090a0"), 1))
        for angle in range(0, 360, 30):
            rad = math.radians(angle - 90)
            outer = QtCore.QPointF(center.x() + math.cos(rad) * radius, center.y() + math.sin(rad) * radius)
            inner = QtCore.QPointF(center.x() + math.cos(rad) * (radius - 10), center.y() + math.sin(rad) * (radius - 10))
            painter.drawLine(inner, outer)

        needle_angle = math.radians(self._position - 90)
        needle_end = QtCore.QPointF(
            center.x() + math.cos(needle_angle) * (radius - 28),
            center.y() + math.sin(needle_angle) * (radius - 28),
        )
        color = QtGui.QColor("#d9480f" if self._direction else "#1f6f43")
        painter.setPen(QtGui.QPen(color, 5, QtCore.Qt.SolidLine, QtCore.Qt.RoundCap))
        painter.drawLine(center, needle_end)
        painter.setBrush(color)
        painter.setPen(QtCore.Qt.NoPen)
        painter.drawEllipse(center, 6, 6)

        direction_text = {1: "clockwise", -1: "anti clockwise", 0: "stopped"}.get(self._direction, "unknown")
        painter.setPen(QtGui.QColor("#111820"))
        font = painter.font()
        font.setPointSize(14)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(self.rect(), QtCore.Qt.AlignCenter, f"{self._position:.1f} deg")
        font.setPointSize(10)
        font.setBold(False)
        painter.setFont(font)
        painter.drawText(self.rect().adjusted(0, 36, 0, 0), QtCore.Qt.AlignCenter, direction_text)


class MotorControllerWidget(QtWidgets.QWidget):
    """Thread-aware test UI for motor controller drivers."""

    def __init__(self, instance, ini=None, parent=None, use_ini_draft=True):
        super().__init__(parent)
        self.dev = instance
        self.ini_source = ini if ini is not None else io.StringIO(std_ini_text)
        self.use_ini_draft = use_ini_draft
        self._last_ini_text = ""
        self._status_fields = {}
        self._busy = False
        self._is_initialized = False
        self._last_error_text = "none"
        self._active_thread = None
        self._active_task = None
        self._task_label = None
        self._task_result = None
        self._task_error = None
        self._task_on_success = None
        self._use_worker_threads = True

        self._poll_timer = QtCore.QTimer(self)
        self._poll_timer.setInterval(500)
        self._poll_timer.timeout.connect(self.on_poll_state)

        self.setWindowTitle("Motor Controller Test Utility")
        self.resize(980, 720)
        self._build_ui()
        self._load_ini()
        self.log_message("UI ready.")
        app = QtWidgets.QApplication.instance()
        if app is not None:
            app.aboutToQuit.connect(self._safe_stop)

    def _build_ui(self):
        main = QtWidgets.QVBoxLayout(self)
        self.tabs = QtWidgets.QTabWidget()
        main.addWidget(self.tabs)
        self._build_connection_tab()
        self._build_control_tab()
        self._build_status_tab()
        self._build_raw_tab()
        self._build_smoke_tab()
        self._build_log_tab()
        self._build_safety_bar(main)

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
        self.refresh_button = QtWidgets.QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.refresh_status)
        self.close_button = QtWidgets.QPushButton("Close")
        self.close_button.clicked.connect(self.close)
        bottom.addWidget(self.refresh_button)
        bottom.addWidget(self.close_button)
        main.addLayout(bottom)
        self._refresh_status_bar()

    def _build_safety_bar(self, parent_layout):
        safety = QtWidgets.QFrame()
        safety.setFrameShape(QtWidgets.QFrame.StyledPanel)
        safety.setStyleSheet("QFrame { background: #fff4e6; border: 1px solid #f08c00; }")
        layout = QtWidgets.QHBoxLayout(safety)
        layout.setContentsMargins(10, 8, 10, 8)

        self.stop_button = QtWidgets.QPushButton("STOP")
        self.stop_button.setMinimumSize(170, 64)
        self.stop_button.setStyleSheet("font-size: 24px; font-weight: bold; background: #c92a2a; color: white;")
        self.stop_button.clicked.connect(self.on_stop_clicked)
        layout.addWidget(self.stop_button)

        self.global_position_label = QtWidgets.QLabel("Position: unknown")
        self.global_direction_label = QtWidgets.QLabel("Direction: unknown")
        self.global_motion_label = QtWidgets.QLabel("Motion: unknown")
        for label in (self.global_position_label, self.global_direction_label, self.global_motion_label):
            label.setStyleSheet("font-size: 16px; font-weight: bold; color: #111820;")
            layout.addWidget(label)
        layout.addStretch()
        parent_layout.addWidget(safety)

    def _build_connection_tab(self):
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)
        row = QtWidgets.QHBoxLayout()
        self.init_button = QtWidgets.QPushButton("Init / Re-Init")
        self.init_button.clicked.connect(self.on_init_clicked)
        self.quit_button = QtWidgets.QPushButton("Stop + Quit")
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
        layout.addLayout(row)
        layout.addWidget(self.ini_edit)
        self.tabs.addTab(tab, "Connection")

    def _build_control_tab(self):
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(tab)

        left = QtWidgets.QVBoxLayout()
        form = QtWidgets.QFormLayout()
        self.position_spin = QtWidgets.QDoubleSpinBox()
        self.position_spin.setRange(0.0, 359.999)
        self.position_spin.setDecimals(3)
        self.position_spin.setSuffix(" deg")
        self.position_spin.setValue(90.0)
        self.goto_button = QtWidgets.QPushButton("Goto")
        self.goto_button.clicked.connect(self.on_goto_clicked)
        goto_row = QtWidgets.QHBoxLayout()
        goto_row.addWidget(self.position_spin)
        goto_row.addWidget(self.goto_button)
        form.addRow("Target Position", goto_row)

        self.speed_spin = QtWidgets.QDoubleSpinBox()
        self.speed_spin.setRange(0.0, 10000.0)
        self.speed_spin.setDecimals(3)
        self.speed_spin.setSuffix(" deg/s")
        self.speed_spin.setValue(30.0)
        self.set_speed_button = QtWidgets.QPushButton("Set Speed")
        self.set_speed_button.clicked.connect(self.on_set_speed_clicked)
        speed_row = QtWidgets.QHBoxLayout()
        speed_row.addWidget(self.speed_spin)
        speed_row.addWidget(self.set_speed_button)
        form.addRow("Speed", speed_row)
        left.addLayout(form)

        move_row = QtWidgets.QHBoxLayout()
        self.ccw_button = QtWidgets.QPushButton("Anti Clockwise")
        self.ccw_button.clicked.connect(lambda: self.on_move_clicked(-1))
        self.cw_button = QtWidgets.QPushButton("Clockwise")
        self.cw_button.clicked.connect(lambda: self.on_move_clicked(1))
        move_row.addWidget(self.ccw_button)
        move_row.addWidget(self.cw_button)
        left.addLayout(move_row)

        self.poll_check = QtWidgets.QCheckBox("Poll state")
        self.poll_check.setChecked(True)
        self.poll_check.toggled.connect(self.on_poll_toggled)
        left.addWidget(self.poll_check)

        status_box = QtWidgets.QGroupBox("Current State")
        status_form = QtWidgets.QFormLayout(status_box)
        self.position_edit = QtWidgets.QLineEdit("unknown")
        self.position_edit.setReadOnly(True)
        self.direction_edit = QtWidgets.QLineEdit("unknown")
        self.direction_edit.setReadOnly(True)
        self.speed_edit = QtWidgets.QLineEdit("unknown")
        self.speed_edit.setReadOnly(True)
        status_form.addRow("Position", self.position_edit)
        status_form.addRow("Direction", self.direction_edit)
        status_form.addRow("Speed", self.speed_edit)
        left.addWidget(status_box)
        left.addStretch()

        self.position_dial = PositionDial()
        layout.addLayout(left, 1)
        layout.addWidget(self.position_dial, 1)
        self.tabs.addTab(tab, "Control")

    def _build_status_tab(self):
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QGridLayout(tab)
        specs = [
            ("Description", "GetDescription"),
            ("Virtual", "GetVirtual"),
            ("State", "GetState"),
            ("Speed", "GetSpeed"),
        ]
        for idx, (label, key) in enumerate(specs):
            field = QtWidgets.QLineEdit("unknown")
            field.setReadOnly(True)
            self._status_fields[key] = field
            row = idx // 2
            col = (idx % 2) * 2
            layout.addWidget(QtWidgets.QLabel(label), row, col)
            layout.addWidget(field, row, col + 1)
        layout.setRowStretch(2, 1)
        self.tabs.addTab(tab, "Status")

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
        layout.addWidget(QtWidgets.QLabel("Smoke test: Init, SetSpeed, Goto, Move clockwise, Stop, State, Quit."))
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
        state_text = state_text or ("Busy" if self._busy else "Ready")
        self.state_label.setText(f"State: {state_text}")
        self.init_label.setText(f"Init: {'initialized' if self._is_initialized else 'not initialized'}")
        self.driver_label.setText(f"Driver: {type(self.dev).__module__}.{type(self.dev).__name__}")
        self.error_label.setText(f"Last error: {self._last_error_text}")

    def _set_busy(self, busy, label=None):
        self._busy = busy
        for widget in (self.refresh_button, self.close_button):
            widget.setEnabled(not busy)
        self.stop_button.setEnabled(True)
        self._refresh_status_bar(f"Busy: {label}" if busy and label else None)

    def _start_task(self, label, func, on_success=None):
        if self._busy:
            QtWidgets.QMessageBox.information(self, "Operation in progress", "Another operation is still running.")
            return False
        self.log_message(f"{label} started.")
        self._set_busy(True, label)
        self._task_label = label
        self._task_result = None
        self._task_error = None
        self._task_on_success = on_success
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
        self._active_thread = None
        self._active_task = None
        self._task_label = None
        self._task_result = None
        self._task_error = None
        self._task_on_success = None
        self._set_busy(False)
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
            QtWidgets.QMessageBox.critical(self, f"{label} Error", str(error))
        self._refresh_status_bar()

    def _split_error_value(self, result):
        if isinstance(result, tuple) and len(result) >= 2:
            return result[0], result[1:]
        return 0, result

    def _driver_method(self, method_name, *args):
        method = getattr(self.dev, method_name, None)
        if method is None:
            raise AttributeError(f"Driver does not implement {method_name}()")
        return method(*args)

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
        if virtual or not driver:
            return "mc_virtual"
        return Path(driver).with_suffix("").name

    def _instantiate_driver(self, module_name):
        module = importlib.import_module(f"mpylab.device.{module_name}")
        driver_cls = getattr(module, "MOTORCONTROLLER")
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
        self._refresh_status_bar()
        self.log_message(f"Driver switched from {type(old_driver).__module__} to {type(self.dev).__module__}.")

    def on_load_ini_clicked(self):
        path, _filter = QtWidgets.QFileDialog.getOpenFileName(self, "Open INI", "", "INI Files (*.ini *.txt);;All Files (*)")
        if not path:
            return
        with open(path, "r", encoding="utf-8") as handle:
            content = handle.read()
        self.ini_edit.setPlainText(content)
        self._last_ini_text = content
        self.log_message(f"Loaded INI file: {path}")

    def on_save_ini_clicked(self):
        path, _filter = QtWidgets.QFileDialog.getSaveFileName(self, "Save INI", "", "INI Files (*.ini *.txt);;All Files (*)")
        if not path:
            return
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(self.ini_edit.toPlainText())
        clear_ini_draft(self)
        self.log_message(f"Saved INI file: {path}")

    def on_init_clicked(self):
        ini_text = self.ini_edit.toPlainText()
        self._last_ini_text = ini_text
        try:
            self._select_driver_from_ini(ini_text)
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "Driver Selection Error", str(exc))
            return

        def success(err):
            self._is_initialized = (err == 0)
            self.log_message(f"Init returned: {err}")
            self.refresh_status()
            self.on_poll_toggled(self.poll_check.isChecked())

        self._start_task("Init", lambda: self._driver_method("Init", io.StringIO(ini_text)), success)

    def on_quit_clicked(self):
        self._poll_timer.stop()
        self._start_task("Stop + Quit", lambda: (self._safe_stop(), self._driver_method("Quit")), self._handle_quit)

    def _handle_quit(self, result):
        self._is_initialized = False
        self.log_message(f"Quit returned: {result}")
        self._refresh_status_bar()

    def on_goto_clicked(self):
        self._start_task("Goto", lambda: self._driver_method("Goto", self.position_spin.value()), lambda result: self._handle_state(result))

    def on_move_clicked(self, direction):
        self._start_task("Move", lambda: self._driver_method("Move", direction), lambda _result: self.refresh_status())

    def on_set_speed_clicked(self):
        self._start_task("Set Speed", lambda: self._driver_method("SetSpeed", self.speed_spin.value()), lambda result: self._handle_speed(result))

    def on_stop_clicked(self):
        self.log_message("Safety stop requested.")
        try:
            result = self._driver_method("Move", 0)
            self.log_message(f"Stop returned: {result}")
            self.refresh_status()
        except Exception as exc:
            self._last_error_text = str(exc)
            self.log_message(f"Stop failed: {type(exc).__name__}: {exc}")
            QtWidgets.QMessageBox.critical(self, "Stop Error", str(exc))

    def _safe_stop(self):
        try:
            if hasattr(self.dev, "Move"):
                return self.dev.Move(0)
        except Exception as exc:
            self.log_message(f"Safe stop failed: {type(exc).__name__}: {exc}")
        return None

    def _direction_text(self, direction):
        try:
            direction = int(direction)
        except (TypeError, ValueError):
            return "unknown"
        if direction > 0:
            return "clockwise"
        if direction < 0:
            return "anti clockwise"
        return "stopped"

    def _handle_state(self, result):
        if isinstance(result, tuple) and len(result) >= 3:
            _err, position, direction = result[:3]
            position_text = f"{float(position):.3f} deg"
            direction_text = self._direction_text(direction)
            motion_text = "moving" if direction_text in ("clockwise", "anti clockwise") else "stopped"
            self.position_edit.setText(position_text)
            self.direction_edit.setText(direction_text)
            self.global_position_label.setText(f"Position: {position_text}")
            self.global_direction_label.setText(f"Direction: {direction_text}")
            self.global_motion_label.setText(f"Motion: {motion_text}")
            self.position_dial.set_state(position, direction)
            self._status_fields.get("GetState", QtWidgets.QLineEdit()).setText(str(result))
        self._refresh_status_bar()

    def _handle_speed(self, result):
        if isinstance(result, tuple) and len(result) >= 2:
            speed_text = f"{float(result[1]):.3f} deg/s"
            self.speed_edit.setText(speed_text)
            self._status_fields.get("GetSpeed", QtWidgets.QLineEdit()).setText(str(result))

    def refresh_status(self):
        def task():
            snapshot = {}
            for method_name in ("GetDescription", "GetVirtual", "GetState", "GetSpeed"):
                method = getattr(self.dev, method_name, None)
                if method is None:
                    snapshot[method_name] = "not implemented"
                    continue
                try:
                    snapshot[method_name] = method()
                except Exception as exc:
                    snapshot[method_name] = f"{type(exc).__name__}: {exc}"
            return snapshot

        def success(snapshot):
            for key, value in snapshot.items():
                field = self._status_fields.get(key)
                if field is not None:
                    field.setText(str(value))
            self._handle_state(snapshot.get("GetState"))
            self._handle_speed(snapshot.get("GetSpeed"))

        if not self._busy:
            self._start_task("Refresh Status", task, success)

    def on_poll_state(self):
        if self._is_initialized and not self._busy:
            self._refresh_motion_state()

    def _refresh_motion_state(self):
        """Refresh fast-changing motion state without disabling the UI."""
        try:
            state = self._driver_method("GetState")
            self._handle_state(state)
            field = self._status_fields.get("GetState")
            if field is not None:
                field.setText(str(state))
        except Exception as exc:
            self._last_error_text = str(exc)
            self.log_message(f"Poll state failed: {type(exc).__name__}: {exc}")
            self._refresh_status_bar()
            return

        get_speed = getattr(self.dev, "GetSpeed", None)
        if get_speed is None:
            return
        try:
            speed = get_speed()
            self._handle_speed(speed)
            field = self._status_fields.get("GetSpeed")
            if field is not None:
                field.setText(str(speed))
        except Exception as exc:
            self._last_error_text = str(exc)
            self.log_message(f"Poll speed failed: {type(exc).__name__}: {exc}")
            self._refresh_status_bar()

    def on_poll_toggled(self, checked):
        if checked and self._is_initialized:
            self._poll_timer.start()
        else:
            self._poll_timer.stop()

    def on_raw_query_clicked(self):
        cmd = self.raw_command_edit.text().strip()
        if cmd:
            self._start_task("Raw Query", lambda: self.dev.query(cmd), lambda result: self.raw_output.appendPlainText(f"> {cmd}\n{result}"))

    def on_raw_write_clicked(self):
        cmd = self.raw_command_edit.text().strip()
        if cmd:
            self._start_task("Raw Write", lambda: self.dev.write(cmd), lambda result: self.raw_output.appendPlainText(f"> {cmd}\n{result}"))

    def on_smoke_clicked(self):
        ini_text = self.ini_edit.toPlainText()

        def task():
            lines = [f"Init: {self.dev.Init(io.StringIO(ini_text))}"]
            lines.append(f"Description: {self.dev.GetDescription()}")
            lines.append(f"SetSpeed: {self.dev.SetSpeed(30)}")
            lines.append(f"Goto: {self.dev.Goto(90)}")
            lines.append(f"Move clockwise: {self.dev.Move(1)}")
            lines.append(f"Stop: {self.dev.Move(0)}")
            lines.append(f"State: {self.dev.GetState()}")
            lines.append(f"Quit: {self.dev.Quit()}")
            return "\n".join(lines)

        self._start_task("Smoke Test", task, lambda result: self.smoke_output.setPlainText(result))

    def _shutdown_thread(self):
        if self._active_thread is not None and self._active_thread.isRunning():
            self._active_thread.quit()
            self._active_thread.wait(3000)

    def closeEvent(self, event):
        self._poll_timer.stop()
        self._safe_stop()
        try:
            if hasattr(self.dev, "Quit"):
                self.dev.Quit()
        finally:
            self._shutdown_thread()
            super().closeEvent(event)


def main(argv=None):
    """Run the motor controller test UI."""
    parser = argparse.ArgumentParser(description="Motor controller test utility")
    parser.add_argument("ini", nargs="?", help="INI file to load")
    parser.add_argument("--virtual", action="store_true", help="start with the virtual motor controller")
    args = parser.parse_args(argv)

    app = QtWidgets.QApplication(sys.argv if argv is None else [sys.argv[0], *argv])
    ini = io.StringIO(std_ini_text) if args.virtual or not args.ini else args.ini
    window = MotorControllerWidget(VIRTUAL_MOTORCONTROLLER(), ini=ini, use_ini_draft=not args.virtual)
    window.show()
    return app.exec()


UI = MotorControllerWidget


if __name__ == "__main__":
    sys.exit(main())
