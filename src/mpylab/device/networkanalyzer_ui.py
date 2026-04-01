# -*- coding: utf-8 -*-

import io
import sys

import numpy as np
from PySide6 import QtWidgets, QtCore

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from mpylab.tools.util import format_block
from mpylab.device.device import CONVERT

conv = CONVERT()

std_ini_text = format_block("""
                [DESCRIPTION]
                description: sp template
                type:        'SPECTRUMANALYZER'
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
    def __init__(self, parent=None):
        self.figure = Figure()
        self.ax = self.figure.add_subplot(111)
        super().__init__(self.figure)
        self.setParent(parent)

        self.ax.set_title("Spectrum")
        self.ax.set_xlabel("Frequenz in Hz")
        self.ax.set_ylabel("Amplitude in dBm")
        self._line, = self.ax.plot([], [])

    def update_spectrum(self, x, y, logarithmic=False):
        self.ax.clear()
        self.ax.plot(x, y)

        self.ax.set_title("Spectrum")
        self.ax.set_xlabel("Frequenz in Hz")
        self.ax.set_ylabel("Amplitude in dBm")

        if logarithmic:
            self.ax.set_xscale("log")
        else:
            self.ax.set_xscale("linear")

        self.ax.relim()
        self.ax.autoscale_view()
        self.draw()


class SpectrumAnalyzerWidget(QtWidgets.QWidget):
    """
    PySide6-Ersatz für die TraitsUI/Chaco-Oberfläche.
    """

    def __init__(self, instance, ini=None, parent=None):
        super().__init__(parent)

        self.dv = instance
        self.ini_source = ini if ini is not None else io.StringIO(std_ini_text)
        self.int_unit = "dBm"
        self.power = ()

        self.setWindowTitle("Spectrum Analyzer")
        self.resize(1000, 700)

        self._build_ui()
        self._load_ini()

    # ---------------------------------------------------------
    # UI
    # ---------------------------------------------------------

    def _build_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)

        self.tabs = QtWidgets.QTabWidget()
        main_layout.addWidget(self.tabs)

        self._build_ini_tab()
        self._build_spectrum_tab()
        self._build_plot_tab()

        bottom_bar = QtWidgets.QHBoxLayout()
        bottom_bar.addStretch()

        self.close_button = QtWidgets.QPushButton("Schließen")
        self.close_button.clicked.connect(self.close)
        bottom_bar.addWidget(self.close_button)

        main_layout.addLayout(bottom_bar)

    def _build_ini_tab(self):
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)

        self.ini_edit = QtWidgets.QPlainTextEdit()
        self.ini_edit.setMinimumHeight(220)

        self.init_button = QtWidgets.QPushButton("Init")
        self.init_button.clicked.connect(self.on_init_clicked)

        layout.addWidget(self.ini_edit)
        layout.addWidget(self.init_button)
        layout.addStretch()

        self.tabs.addTab(tab, "Ini")

    def _build_spectrum_tab(self):
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)

        self.spectrum_edit = QtWidgets.QPlainTextEdit()
        self.spectrum_edit.setReadOnly(True)

        self.get_spectrum_button_1 = QtWidgets.QPushButton("GetSpectrum")
        self.get_spectrum_button_1.clicked.connect(self.on_get_spectrum_clicked)

        layout.addWidget(self.spectrum_edit)
        layout.addWidget(self.get_spectrum_button_1)
        layout.addStretch()

        self.tabs.addTab(tab, "Spectrum")

    def _build_plot_tab(self):
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)

        self.canvas = MplCanvas()

        self.get_spectrum_button_2 = QtWidgets.QPushButton("GetSpectrum")
        self.get_spectrum_button_2.clicked.connect(self.on_get_spectrum_clicked)

        layout.addWidget(self.canvas)
        layout.addWidget(self.get_spectrum_button_2)

        self.tabs.addTab(tab, "Plot")

    def _load_ini(self):
        if hasattr(self.ini_source, "read"):
            try:
                content = self.ini_source.read()
            except Exception:
                content = std_ini_text
        else:
            content = str(self.ini_source)

        self.ini_edit.setPlainText(content)

    # ---------------------------------------------------------
    # Logik
    # ---------------------------------------------------------

    def on_init_clicked(self):
        try:
            ini = io.StringIO(self.ini_edit.toPlainText())
            self.dv.Init(ini)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Init-Fehler", str(e))

    def on_get_spectrum_clicked(self):
        try:
            sweep_type = self.dv.GetSweepType()[1]
            logarithmic = sweep_type == "LOGARITHMIC"

            self.power = self.dv.GetSpectrum()[1]
            x = np.array(self.power[0])
            y = np.array(self.power[1])

            self.canvas.update_spectrum(x, y, logarithmic=logarithmic)
            self.spectrum_edit.setPlainText(f"{self.power[0]}\n\n\n{self.power[1]}")

        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Spectrum-Fehler", str(e))

    def closeEvent(self, event):
        try:
            if hasattr(self.dv, "Quit"):
                self.dv.Quit()
        except Exception:
            pass
        super().closeEvent(event)


# ----------------------------------------------------------------------
# Beispielstart mit Dummy-Driver
# ----------------------------------------------------------------------

if __name__ == "__main__":
    class DummySpectrumDriver:
        def Init(self, ini):
            print("Init called")
            print(ini.read())

        def GetSweepType(self):
            return 0, "LINEAR"
            # alternativ:
            # return 0, "LOGARITHMIC"

        def GetSpectrum(self):
            x = np.linspace(1e8, 6e9, 200)
            y = -40 + 10 * np.sin(np.linspace(0, 8 * np.pi, 200))
            return 0, (x.tolist(), y.tolist())

        def Quit(self):
            print("Quit called")

    app = QtWidgets.QApplication(sys.argv)
    w = SpectrumAnalyzerWidget(DummySpectrumDriver())
    w.show()
    sys.exit(app.exec())