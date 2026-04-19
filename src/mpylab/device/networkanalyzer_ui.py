# -*- coding: utf-8 -*-

import io
import sys
from datetime import datetime

import numpy as np
from PySide6 import QtCore, QtWidgets

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from mpylab.tools.util import format_block

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


class MplCanvas(FigureCanvas):
    """Matplotlib canvas used to display the currently acquired spectrum."""

    def __init__(self, parent=None):
        self.figure = Figure()
        self.ax = self.figure.add_subplot(111)
        super().__init__(self.figure)
        self.setParent(parent)
        self._configure_axes()

    def _configure_axes(self):
        self.ax.set_title("Trace Data")
        self.ax.set_xlabel("Frequency in Hz")
        self.ax.set_ylabel("Amplitude")

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
        self._configure_axes()
        self.draw()


class NetworkAnalyzerWidget(QtWidgets.QWidget):
    """Generic graphical test utility for network analyzer style drivers."""

    def __init__(self, instance, ini=None, parent=None):
        super().__init__(parent)

        self.dv = instance
        self.ini_source = ini if ini is not None else io.StringIO(std_ini_text)
        self.power = ()
        self._last_ini_text = ""
        self._status_fields = {}
        self._control_widgets = {}
        self._last_trace_data = None

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
        bottom_bar.addStretch()

        self.refresh_all_button = QtWidgets.QPushButton("Refresh All")
        self.refresh_all_button.clicked.connect(self.refresh_all)
        bottom_bar.addWidget(self.refresh_all_button)

        self.close_button = QtWidgets.QPushButton("Close")
        self.close_button.clicked.connect(self.close)
        bottom_bar.addWidget(self.close_button)

        main_layout.addLayout(bottom_bar)

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

        self.ini_edit = QtWidgets.QPlainTextEdit()
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
            ("Center Frequency [Hz]", "center_freq", QtWidgets.QLineEdit(), self.on_set_center_freq_clicked),
            ("Span [Hz]", "span", QtWidgets.QLineEdit(), self.on_set_span_clicked),
            ("RBW [Hz]", "rbw", QtWidgets.QLineEdit(), self.on_set_rbw_clicked),
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
            button = QtWidgets.QPushButton("Apply")
            button.clicked.connect(handler)
            self._control_widgets[key] = widget
            controls_grid.addWidget(QtWidgets.QLabel(label), idx, 0)
            controls_grid.addWidget(widget, idx, 1)
            controls_grid.addWidget(button, idx, 2)

        quick_row = QtWidgets.QHBoxLayout()
        self.pull_from_device_button = QtWidgets.QPushButton("Populate Controls From Device")
        self.pull_from_device_button.clicked.connect(self.populate_controls_from_status)
        quick_row.addWidget(self.pull_from_device_button)

        self.single_sweep_button = QtWidgets.QPushButton("Start Single Sweep")
        self.single_sweep_button.clicked.connect(self.on_single_sweep_clicked)
        quick_row.addWidget(self.single_sweep_button)
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
        toolbar.addStretch()

        splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        self.canvas = MplCanvas()
        splitter.addWidget(self.canvas)

        self.spectrum_edit = QtWidgets.QPlainTextEdit()
        self.spectrum_edit.setReadOnly(True)
        splitter.addWidget(self.spectrum_edit)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)

        layout.addLayout(toolbar)
        layout.addWidget(splitter)
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
        if hasattr(self.ini_source, "read"):
            try:
                content = self.ini_source.read()
            except Exception:
                content = std_ini_text
        else:
            content = str(self.ini_source)

        self._last_ini_text = content
        self.ini_edit.setPlainText(content)

    def log_edit_clear(self):
        self.log_edit.clear()

    def log_message(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_edit.appendPlainText(f"[{timestamp}] {message}")

    def _display_value(self, value):
        if isinstance(value, tuple):
            return ", ".join(str(item) for item in value)
        return str(value)

    def _call_driver(self, method_name, *args):
        method = getattr(self.dv, method_name, None)
        if method is None:
            raise AttributeError(f"Driver does not implement {method_name}()")
        self.log_message(f"{method_name}({', '.join(repr(arg) for arg in args)})")
        result = method(*args)
        self.log_message(f"{method_name} -> {result!r}")
        return result

    def _show_error(self, title, error):
        self.log_message(f"{title}: {type(error).__name__}: {error}")
        QtWidgets.QMessageBox.critical(self, title, str(error))

    def _set_status_field(self, key, text):
        widget = self._status_fields.get(key)
        if widget is not None:
            widget.setText(text)

    def _status_value(self, getter):
        widget = self._status_fields.get(getter)
        return widget.text().strip() if widget is not None else ""

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
            self.log_message(f"Saved INI file: {path}")
        except Exception as exc:
            self._show_error("INI Save Error", exc)

    def on_init_clicked(self):
        try:
            ini_text = self.ini_edit.toPlainText()
            self._last_ini_text = ini_text
            ini = io.StringIO(ini_text)
            channel = self.channel_spin.value()
            err = self.dv.Init(ini=ini, channel=channel)
            self.log_message(f"Init returned: {err}")
            self.refresh_all()
        except Exception as exc:
            self._show_error("Init Error", exc)

    def refresh_status(self):
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

        for getter in getter_specs:
            if not hasattr(self.dv, getter):
                continue
            try:
                err, value = self._call_driver(getter)
                text = self._display_value(value) if err == 0 else f"ERR {err}"
            except Exception as exc:
                text = f"{type(exc).__name__}: {exc}"
                self.log_message(f"{getter} failed: {text}")
            self._set_status_field(getter, text)

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
            value = self._status_value(getter)
            if not value or value.startswith("ERR") or ":" in value:
                continue
            try:
                if isinstance(widget, QtWidgets.QComboBox):
                    idx = widget.findText(value)
                    if idx >= 0:
                        widget.setCurrentIndex(idx)
                elif isinstance(widget, QtWidgets.QSpinBox):
                    widget.setValue(int(float(value)))
                else:
                    widget.setText(value)
            except Exception:
                self.log_message(f"Could not populate control {control_key} from {getter}='{value}'")

    def _line_edit_float(self, key):
        text = self._control_widgets[key].text().strip()
        if not text:
            raise ValueError("Input field is empty")
        return float(text)

    def _combo_value(self, key):
        return self._control_widgets[key].currentText().strip()

    def _spin_value(self, key):
        return int(self._control_widgets[key].value())

    def _apply_and_refresh(self, label, callable_):
        try:
            result = callable_()
            self.log_message(f"{label}: {result!r}")
            self.refresh_all()
            return result
        except Exception as exc:
            self._show_error(f"{label} Error", exc)
            return None

    def on_set_center_freq_clicked(self):
        self._apply_and_refresh("SetCenterFreq", lambda: self._call_driver("SetCenterFreq", self._line_edit_float("center_freq")))

    def on_set_span_clicked(self):
        self._apply_and_refresh("SetSpan", lambda: self._call_driver("SetSpan", self._line_edit_float("span")))

    def on_set_rbw_clicked(self):
        self._apply_and_refresh("SetRBW", lambda: self._call_driver("SetRBW", self._line_edit_float("rbw")))

    def on_set_ref_level_clicked(self):
        self._apply_and_refresh("SetRefLevel", lambda: self._call_driver("SetRefLevel", self._line_edit_float("ref_level")))

    def on_set_division_clicked(self):
        self._apply_and_refresh("SetDivisionValue", lambda: self._call_driver("SetDivisionValue", self._line_edit_float("division_value")))

    def on_set_sweep_type_clicked(self):
        self._apply_and_refresh("SetSweepType", lambda: self._call_driver("SetSweepType", self._combo_value("sweep_type")))

    def on_set_sweep_mode_clicked(self):
        self._apply_and_refresh("SetSweepMode", lambda: self._call_driver("SetSweepMode", self._combo_value("sweep_mode")))

    def on_set_sweep_count_clicked(self):
        self._apply_and_refresh("SetSweepCount", lambda: self._call_driver("SetSweepCount", self._spin_value("sweep_count")))

    def on_set_sweep_points_clicked(self):
        self._apply_and_refresh("SetSweepPoints", lambda: self._call_driver("SetSweepPoints", self._spin_value("sweep_points")))

    def on_set_trigger_mode_clicked(self):
        self._apply_and_refresh("SetTriggerMode", lambda: self._call_driver("SetTriggerMode", self._combo_value("trigger_mode")))

    def on_set_trigger_delay_clicked(self):
        self._apply_and_refresh("SetTriggerDelay", lambda: self._call_driver("SetTriggerDelay", self._line_edit_float("trigger_delay")))

    def on_single_sweep_clicked(self):
        def action():
            if hasattr(self.dv, "SetSweepMode"):
                self._call_driver("SetSweepMode", "SINGLE")
            if hasattr(self.dv, "NewSweepCount"):
                return self._call_driver("NewSweepCount")
            raise AttributeError("Driver does not support NewSweepCount()")

        self._apply_and_refresh("Single Sweep", action)

    def on_single_sweep_and_get_spectrum_clicked(self):
        try:
            self.on_single_sweep_clicked()
            self.on_get_spectrum_clicked()
        except Exception as exc:
            self._show_error("Single Sweep + Spectrum Error", exc)

    def on_get_spectrum_clicked(self):
        try:
            sweep_type = None
            if hasattr(self.dv, "GetSweepType"):
                err, sweep_type = self._call_driver("GetSweepType")
                if err != 0:
                    sweep_type = None

            err, power = self._call_driver("GetSpectrum")
            if err != 0:
                raise RuntimeError(f"GetSpectrum returned error code {err}")

            self.power = power
            self._last_trace_data = power
            x = np.asarray(power[0], dtype=float)
            y = np.asarray(power[1], dtype=float)
            logarithmic = sweep_type == "LOGARITHMIC"

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
            self.log_message(f"Spectrum acquired: {len(x)} points")
        except Exception as exc:
            self._show_error("Spectrum Error", exc)

    def on_clear_plot_clicked(self):
        self.canvas.clear_plot()
        self.spectrum_edit.clear()
        self._last_trace_data = None
        self.log_message("Spectrum plot cleared.")

    def refresh_all(self):
        self.refresh_status()
        self.populate_controls_from_status()
        self.after_refresh_all()

    def after_refresh_all(self):
        """Hook for subclasses that need to update additional UI state."""

    def closeEvent(self, event):
        try:
            if hasattr(self.dv, "close"):
                self.dv.close()
            elif hasattr(self.dv, "Quit"):
                self.dv.Quit()
        except Exception as exc:
            self.log_message(f"Driver cleanup failed: {type(exc).__name__}: {exc}")
        super().closeEvent(event)


if __name__ == "__main__":
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
    w.show()
    sys.exit(app.exec())
