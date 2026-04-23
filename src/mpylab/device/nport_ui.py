# -*- coding: utf-8 -*-
"""Graphical test utility for passive n-port, cable and antenna data drivers."""

import argparse
import csv
import io
import sys
from datetime import datetime

from PySide6 import QtCore, QtWidgets

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from scuq.ucomponents import Context

from mpylab.device.nport import ANTENNA, CABLE, NPORT
from mpylab.device.ui_frequency import FrequencyControl
from mpylab.device.ui_quantity_display import INI_UNIT_MODE, SCUQ_UNIT_MODE, quantity_display_values
from mpylab.tools.util import format_block
from mpylab.device.ui_ini_draft import IniPlainTextEdit, clear_ini_draft, load_ini_with_draft


SETTINGS_APP = "nport_ui"


def demo_ini(kind="nport"):
    """Return demo INI content for one passive device kind."""
    kind = kind.lower()
    if kind == "antenna":
        dtype = "ANTENNA"
        description = "Demo Antenna"
        name = "AF"
        unit = "dB"
        rows = """
            30e6 18
            80e6 14
            200e6 11
            500e6 16
            1e9 21
            3e9 27
            6e9 31
            """
    elif kind == "cable":
        dtype = "CABLE"
        description = "Demo Cable"
        name = "S21"
        unit = "dB"
        rows = """
            10e6 -0.2
            100e6 -0.8
            500e6 -1.9
            1e9 -2.8
            3e9 -5.4
            6e9 -8.7
            10e9 -12.5
            """
    else:
        dtype = "NPORT"
        description = "Demo N-Port"
        name = "S21"
        unit = "dB"
        rows = """
            10e6 -40
            100e6 -32
            500e6 -20
            1e9 -12
            3e9 -6
            6e9 -9
            10e9 -18
            """

    return format_block(f"""
        [description]
        DESCRIPTION = {description}
        TYPE = {dtype}
        VENDOR = mpylab
        SERIALNR =
        DEVICEID =
        DRIVER =

        [INIT_VALUE]
        FSTART = 10e6
        FSTOP = 10e9
        FSTEP = 0
        NR_OF_CHANNELS = 1
        VIRTUAL = 1

        [CHANNEL_1]
        NAME = {name}
        UNIT = {unit}
        INTERPOLATION = LOG
        FILE = io.StringIO(format_block('''
            FUNIT: Hz
            UNIT: {unit}
            ABSERROR: 0.2
            {rows}
        '''))
        """).strip()


class DriverTask(QtCore.QObject):
    """Execute one callable in a worker thread."""

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
    """Matplotlib canvas for passive data plots."""

    def __init__(self, parent=None, width=7, height=4, dpi=100):
        self.figure = Figure(figsize=(width, height), dpi=dpi)
        self.axes = self.figure.add_subplot(111)
        super().__init__(self.figure)
        self.setParent(parent)


class NPortWidget(QtWidgets.QWidget):
    """Threaded test UI for NPORT/CABLE/ANTENNA passive data drivers."""

    def __init__(self, instance, ini=None, kind="nport", parent=None, use_ini_draft=True):
        super().__init__(parent)
        self.dev = instance
        self.kind = kind
        self.ini_source = ini if ini is not None else io.StringIO(demo_ini(kind))
        self.use_ini_draft = use_ini_draft
        self._last_ini_text = ""
        self._busy = False
        self._is_initialized = False
        self._last_error_text = "none"
        self._last_plot_rows = []
        self._ctx = Context()

        self._active_thread = None
        self._active_task = None
        self._task_label = None
        self._task_result = None
        self._task_error = None
        self._task_on_success = None
        self._use_worker_threads = False

        self.setWindowTitle(f"{kind.upper()} Passive Data Test Utility")
        self.resize(1150, 820)
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
        self._build_smoke_tab()
        self._build_log_tab()

        bottom = QtWidgets.QHBoxLayout()
        self.state_label = QtWidgets.QLabel()
        self.init_label = QtWidgets.QLabel()
        self.driver_label = QtWidgets.QLabel()
        self.error_label = QtWidgets.QLabel()
        self.error_label.setMinimumWidth(300)
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

    def _build_connection_tab(self):
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)
        row = QtWidgets.QHBoxLayout()
        self.channel_spin = QtWidgets.QSpinBox()
        self.channel_spin.setRange(1, 128)
        self.init_button = QtWidgets.QPushButton("Init / Re-Init")
        self.init_button.clicked.connect(self.on_init_clicked)
        self.load_button = QtWidgets.QPushButton("Load INI")
        self.load_button.clicked.connect(self.on_load_ini_clicked)
        self.save_button = QtWidgets.QPushButton("Save INI")
        self.save_button.clicked.connect(self.on_save_ini_clicked)
        row.addWidget(QtWidgets.QLabel("Channel"))
        row.addWidget(self.channel_spin)
        row.addWidget(self.init_button)
        row.addWidget(self.load_button)
        row.addWidget(self.save_button)
        row.addStretch()
        self.ini_edit = IniPlainTextEdit()
        layout.addLayout(row)
        layout.addWidget(self.ini_edit)
        self.tabs.addTab(tab, "Connection")

    def _build_status_tab(self):
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QFormLayout(tab)
        self.description_edit = QtWidgets.QLineEdit()
        self.description_edit.setReadOnly(True)
        self.freq_edit = QtWidgets.QLineEdit()
        self.freq_edit.setReadOnly(True)
        self.channels_edit = QtWidgets.QLineEdit()
        self.channels_edit.setReadOnly(True)
        self.virtual_edit = QtWidgets.QLineEdit()
        self.virtual_edit.setReadOnly(True)
        layout.addRow("Description", self.description_edit)
        layout.addRow("Frequency", self.freq_edit)
        layout.addRow("Available Data", self.channels_edit)
        layout.addRow("Virtual", self.virtual_edit)
        self.tabs.addTab(tab, "Status")

    def _build_data_tab(self):
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)
        form = QtWidgets.QGridLayout()
        self.what_combo = QtWidgets.QComboBox()
        self.what_combo.setEditable(True)
        self.freq_spin = FrequencyControl(default_hz=1e9)
        self.freq_spin.valueApplied.connect(self.on_set_freq_clicked)
        self.get_data_button = QtWidgets.QPushButton("Get Data")
        self.get_data_button.clicked.connect(self.on_get_data_clicked)
        form.addWidget(QtWidgets.QLabel("What"), 0, 0)
        form.addWidget(self.what_combo, 0, 1)
        form.addWidget(QtWidgets.QLabel("Frequency"), 1, 0)
        form.addWidget(self.freq_spin, 1, 1)
        form.addWidget(self.get_data_button, 1, 2)
        self.data_result = QtWidgets.QPlainTextEdit()
        self.data_result.setReadOnly(True)
        layout.addLayout(form)
        layout.addWidget(self.data_result)
        self.tabs.addTab(tab, "Data")

    def _build_plot_tab(self):
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)
        controls = QtWidgets.QHBoxLayout()
        self.plot_what_combo = QtWidgets.QComboBox()
        self.plot_what_combo.setEditable(True)
        self.start_spin = FrequencyControl(default_hz=10e6)
        self.stop_spin = FrequencyControl(default_hz=10e9)
        self.points_spin = QtWidgets.QSpinBox()
        self.points_spin.setRange(2, 10000)
        self.points_spin.setValue(201)
        self.errorbar_check = QtWidgets.QCheckBox("Plot uncertainty")
        self.errorbar_check.setChecked(True)
        self.display_mode_combo = QtWidgets.QComboBox()
        self.display_mode_combo.addItems([INI_UNIT_MODE, SCUQ_UNIT_MODE])
        self.display_mode_combo.currentTextChanged.connect(lambda _text: self._replot_last_rows())
        self.plot_button = QtWidgets.QPushButton("Plot")
        self.plot_button.clicked.connect(self.on_plot_clicked)
        self.export_button = QtWidgets.QPushButton("Export CSV")
        self.export_button.clicked.connect(self.on_export_csv_clicked)
        controls.addWidget(QtWidgets.QLabel("What"))
        controls.addWidget(self.plot_what_combo)
        controls.addWidget(QtWidgets.QLabel("Start"))
        controls.addWidget(self.start_spin)
        controls.addWidget(QtWidgets.QLabel("Stop"))
        controls.addWidget(self.stop_spin)
        controls.addWidget(QtWidgets.QLabel("Points"))
        controls.addWidget(self.points_spin)
        controls.addWidget(QtWidgets.QLabel("Display"))
        controls.addWidget(self.display_mode_combo)
        controls.addWidget(self.errorbar_check)
        controls.addWidget(self.plot_button)
        controls.addWidget(self.export_button)
        self.canvas = MplCanvas(self)
        self.toolbar = NavigationToolbar(self.canvas, self)
        layout.addLayout(controls)
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)
        self.tabs.addTab(tab, "Plot")

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
        content = load_ini_with_draft(
            self,
            self.ini_edit,
            self.ini_source,
            demo_ini(self.kind),
            f"{SETTINGS_APP}_{self.kind}",
            use_draft=self.use_ini_draft,
        )
        self._last_ini_text = content

    def log_message(self, message):
        self.log_edit.appendPlainText(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")

    def _refresh_status_bar(self, state=None):
        state = state or ("Busy" if self._busy else "Ready")
        self.state_label.setText(f"State: {state}")
        self.init_label.setText(f"Init: {'initialized' if self._is_initialized else 'not initialized'}")
        self.driver_label.setText(f"Driver: {type(self.dev).__name__}")
        self.error_label.setText(f"Last error: {self._last_error_text}")

    def _set_busy(self, busy, label=None):
        self._busy = busy
        self.tabs.setEnabled(not busy)
        self.refresh_button.setEnabled(not busy)
        self.close_button.setEnabled(not busy)
        self._refresh_status_bar(f"Busy: {label}" if busy and label else None)

    def _start_task(self, label, func, on_success=None):
        if self._busy:
            QtWidgets.QMessageBox.information(self, "Operation in progress", "Another operation is still running.")
            return
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
                self.log_message(f"{label} succeeded.")
                self._last_error_text = "none"
                if on_success is not None:
                    on_success(result)
            else:
                self._last_error_text = str(error)
                self.log_message(f"{label} failed: {type(error).__name__}: {error}")
                if label == "Init":
                    self._is_initialized = False
            return True

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
            self.log_message(f"{label} succeeded.")
            self._last_error_text = "none"
            if on_success is not None:
                on_success(result)
        else:
            self._last_error_text = str(error)
            self.log_message(f"{label} failed: {type(error).__name__}: {error}")
            QtWidgets.QMessageBox.critical(self, f"{label} Error", str(error))
        self._refresh_status_bar()

    def on_load_ini_clicked(self):
        path, _filter = QtWidgets.QFileDialog.getOpenFileName(self, "Open INI", "", "INI Files (*.ini *.txt);;All Files (*)")
        if not path:
            return
        with open(path, "r", encoding="utf-8") as handle:
            self.ini_edit.setPlainText(handle.read())

    def on_save_ini_clicked(self):
        path, _filter = QtWidgets.QFileDialog.getSaveFileName(self, "Save INI", "", "INI Files (*.ini *.txt);;All Files (*)")
        if not path:
            return
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(self.ini_edit.toPlainText())
        clear_ini_draft(self)

    def on_init_clicked(self):
        ini_text = self.ini_edit.toPlainText()
        channel = self.channel_spin.value()

        def task():
            return self.dev.Init(io.StringIO(ini_text), channel=channel)

        def success(err):
            self._is_initialized = (err == 0)
            self._set_plot_range_from_loaded_data()
            self.refresh_status()

        self._start_task("Init", task, success)

    def refresh_status(self):
        def task():
            return {
                "description": self.dev.GetDescription(),
                "freq": self.dev.GetFreq(),
                "channels": self.dev.GetChannels() if hasattr(self.dev, "GetChannels") else (0, tuple(self.dev.data.keys())),
                "virtual": self.dev.GetVirtual(),
            }

        def success(snapshot):
            self.description_edit.setText(str(snapshot["description"][1]))
            self.freq_edit.setText(str(snapshot["freq"][1]))
            channels = tuple(snapshot["channels"][1])
            self.channels_edit.setText(", ".join(channels))
            self.virtual_edit.setText(str(snapshot["virtual"][1]))
            self._sync_channel_combos(channels)

        self._start_task("Refresh Status", task, success)

    def _sync_channel_combos(self, channels):
        for combo in (self.what_combo, self.plot_what_combo):
            current = combo.currentText()
            combo.blockSignals(True)
            combo.clear()
            combo.addItems([str(ch) for ch in channels])
            if current:
                idx = combo.findText(current)
                if idx >= 0:
                    combo.setCurrentIndex(idx)
            combo.blockSignals(False)

    def _set_plot_range_from_loaded_data(self):
        frequencies = []
        for entry in getattr(self.dev, "data", {}).values():
            data = entry.get("data") if isinstance(entry, dict) else None
            if isinstance(data, dict):
                frequencies.extend(float(freq) for freq in data.keys())
        if not frequencies:
            return
        fstart = min(frequencies)
        fstop = max(frequencies)
        if fstop <= fstart:
            return
        self.start_spin.set_value_hz(fstart)
        self.stop_spin.set_value_hz(fstop)
        self.freq_spin.set_value_hz(fstart)
        self.log_message(f"Plot range set from INI data: {fstart:g} Hz .. {fstop:g} Hz.")

    def on_set_freq_clicked(self, freq=None):
        if freq is None:
            freq = self.freq_spin.value_hz()
        self._start_task("Set Frequency", lambda: self.dev.SetFreq(freq), lambda result: self.freq_edit.setText(str(result[1])))

    def on_get_data_clicked(self):
        what = self.what_combo.currentText().strip()
        freq = self.freq_spin.value_hz()

        def task():
            self.dev.SetFreq(freq)
            return self.dev.GetData(what)

        def success(result):
            self.data_result.setPlainText(str(result))

        self._start_task("Get Data", task, success)

    def on_plot_clicked(self):
        what = self.plot_what_combo.currentText().strip()
        start = self.start_spin.value_hz()
        stop = self.stop_spin.value_hz()
        points = self.points_spin.value()

        def task():
            if stop <= start:
                raise ValueError("Stop frequency must be greater than start frequency")
            rows = []
            step = (stop - start) / (points - 1)
            for idx in range(points):
                freq = start + idx * step
                self.dev.SetFreq(freq)
                err, uq = self.dev.GetData(what)
                if err != 0:
                    raise RuntimeError(f"GetData({what!r}) failed at {freq} Hz with error {err}")
                rows.append((freq, uq))
            return rows

        self._start_task("Plot", task, self._plot_rows)

    def _to_float(self, value):
        try:
            return float(value)
        except (TypeError, ValueError):
            return abs(value)

    def _plot_rows(self, rows):
        self._last_plot_rows = rows
        self._replot_last_rows()

    def _display_row(self, row, what, mode):
        freq, uq = row
        value, uncertainty, unit = quantity_display_values(
            uq,
            device=self.dev,
            what=what,
            mode=mode,
            context=self._ctx,
        )
        return freq, value, uncertainty, unit, uq

    def _display_rows(self):
        what = self.plot_what_combo.currentText().strip()
        mode = self.display_mode_combo.currentText()
        return [self._display_row(row, what, mode) for row in self._last_plot_rows]

    def _replot_last_rows(self):
        if not self._last_plot_rows:
            return
        rows = self._display_rows()
        x = [row[0] for row in rows]
        y = [self._to_float(row[1]) for row in rows]
        yerr = [abs(self._to_float(row[2])) for row in rows]
        unit = rows[0][3] if rows else ""
        what = self.plot_what_combo.currentText().strip()
        ax = self.canvas.axes
        ax.clear()
        if self.errorbar_check.isChecked():
            ax.errorbar(x, y, yerr=yerr, fmt="-o", markersize=3, capsize=2, linewidth=1)
        else:
            ax.plot(x, y, "-o", markersize=3)
        ax.set_xscale("log")
        ax.set_xlabel("Frequency / Hz")
        ax.set_ylabel(f"{what} / {unit}")
        ax.set_title(f"{type(self.dev).__name__}: {what}")
        ax.grid(True, which="both", alpha=0.35)
        self.canvas.figure.tight_layout()
        self.canvas.draw()

    def on_export_csv_clicked(self):
        if not self._last_plot_rows:
            QtWidgets.QMessageBox.information(self, "No data", "Plot data first.")
            return
        path, _filter = QtWidgets.QFileDialog.getSaveFileName(self, "Export CSV", "", "CSV Files (*.csv);;All Files (*)")
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["frequency_hz", "value", "standard_uncertainty", "unit", "quantity"])
            for freq, value, uncertainty, unit, uq in self._display_rows():
                writer.writerow([freq, value, uncertainty, unit, uq])
        self.log_message(f"Exported CSV: {path}")

    def on_smoke_clicked(self):
        ini_text = self.ini_edit.toPlainText()
        channel = self.channel_spin.value()

        def task():
            lines = [f"Init: {self.dev.Init(io.StringIO(ini_text), channel=channel)}"]
            lines.append(f"Description: {self.dev.GetDescription()}")
            lines.append(f"Channels: {self.dev.GetChannels()}")
            first = next(iter(self.dev.data.keys()))
            lines.append(f"SetFreq: {self.dev.SetFreq(self.freq_spin.value_hz())}")
            lines.append(f"GetFreq: {self.dev.GetFreq()}")
            lines.append(f"GetData({first}): {self.dev.GetData(first)}")
            lines.append(f"Quit: {self.dev.Quit()}")
            return "\n".join(lines)

        self._start_task("Smoke Test", task, lambda result: self.smoke_result.setPlainText(result))

    def closeEvent(self, event):
        if self._active_thread is not None and self._active_thread.isRunning():
            event.ignore()
            QtWidgets.QMessageBox.information(self, "Operation in progress", "Close after the current operation has finished.")
            return
        try:
            self.dev.Quit()
        except Exception:
            pass
        super().closeEvent(event)


UI = NPortWidget


def make_instance(kind):
    kind = kind.lower()
    if kind == "cable":
        return CABLE()
    if kind == "antenna":
        return ANTENNA()
    return NPORT()


def main(argv=None):
    parser = argparse.ArgumentParser(description="Passive n-port/cable/antenna test utility")
    parser.add_argument("--kind", choices=("nport", "cable", "antenna"), default="nport")
    parser.add_argument("--ini", help="Path to an INI file to preload")
    parser.add_argument("--virtual", action="store_true", help="Use built-in demo data; accepted for consistency")
    parser.add_argument(
        "--threaded",
        action="store_true",
        help="Run driver calls in worker threads. Disabled by default for backend stability.",
    )
    args = parser.parse_args(argv)

    ini = args.ini
    if ini is None:
        ini = io.StringIO(demo_ini(args.kind))

    app = QtWidgets.QApplication(sys.argv if argv is None else [sys.argv[0], *argv])
    window = NPortWidget(make_instance(args.kind), ini=ini, kind=args.kind, use_ini_draft=not args.virtual)
    window._use_worker_threads = args.threaded
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
