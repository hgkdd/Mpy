# -*- coding: utf-8 -*-

import io
import sys

from PySide6 import QtWidgets, QtCore

from scuq.quantities import Quantity
from mpylab.tools.util import format_block
from mpylab.device.device import CONVERT

conv = CONVERT()

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
                outpoutstate: 0
                """).strip()


class SignalGeneratorWidget(QtWidgets.QWidget):
    def __init__(self, instance, ini=None, parent=None):
        super().__init__(parent)

        self.sg = instance
        self.ini_source = ini if ini is not None else io.StringIO(std_ini_text)

        self.int_unit = "dBm"

        self.RF_is_on = False
        self.AM_is_on = False
        self.PM_is_on = False

        self.level = -100.0
        self.unit = "dBm"

        self.amfreq = 1e3
        self.amdepth = 0.8
        self.amwave = "SINE"
        self.amsource = "INT1"
        self.lfout = "OFF"

        self.pmfreq = 1000.0
        self.pmwidth = 100e-6
        self.pmdelay = 0.0
        self.pmpol = "NORMAL"
        self.pmsource = "INT"

        self.setWindowTitle("Signalgenerator")
        self.resize(900, 700)

        self._build_ui()
        self._load_ini()
        self._connect_signals()

    # ---------------------------------------------------------
    # UI
    # ---------------------------------------------------------

    def _build_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)

        self.tabs = QtWidgets.QTabWidget()
        main_layout.addWidget(self.tabs)

        self._build_ini_tab()
        self._build_freq_tab()
        self._build_level_tab()
        self._build_am_tab()
        self._build_pm_tab()

        rf_group = QtWidgets.QGroupBox("RF")
        rf_layout = QtWidgets.QVBoxLayout(rf_group)

        self.rf_status = QtWidgets.QLineEdit("RF unknown")
        self.rf_status.setReadOnly(True)

        self.rf_button = QtWidgets.QPushButton("RF On/Off")

        rf_layout.addWidget(self.rf_status)
        rf_layout.addWidget(self.rf_button)

        main_layout.addWidget(rf_group)

        button_row = QtWidgets.QHBoxLayout()
        button_row.addStretch()

        self.close_button = QtWidgets.QPushButton("Schließen")
        self.close_button.clicked.connect(self.close)
        button_row.addWidget(self.close_button)

        main_layout.addLayout(button_row)

    def _build_ini_tab(self):
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)

        self.ini_edit = QtWidgets.QPlainTextEdit()
        self.ini_edit.setMinimumHeight(220)

        self.init_button = QtWidgets.QPushButton("Init")

        layout.addWidget(self.ini_edit)
        layout.addWidget(self.init_button)
        layout.addStretch()

        self.tabs.addTab(tab, "Ini")

    def _build_freq_tab(self):
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QFormLayout(tab)

        self.freq_spin = QtWidgets.QDoubleSpinBox()
        self.freq_spin.setDecimals(3)
        self.freq_spin.setRange(0.0, 1e12)
        self.freq_spin.setValue(0.0)
        self.freq_spin.setSingleStep(1e6)
        self.freq_spin.setSuffix(" Hz")

        layout.addRow("FREQ", self.freq_spin)
        self.tabs.addTab(tab, "Freq")

    def _build_level_tab(self):
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QFormLayout(tab)

        self.level_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.level_slider.setMinimum(-1000)   # -100.0 dBm
        self.level_slider.setMaximum(0)       #   0.0 dBm
        self.level_slider.setValue(-1000)

        self.level_spin = QtWidgets.QDoubleSpinBox()
        self.level_spin.setDecimals(1)
        self.level_spin.setRange(-100.0, 0.0)
        self.level_spin.setSingleStep(0.1)
        self.level_spin.setValue(-100.0)
        self.level_spin.setSuffix(" dBm")

        row = QtWidgets.QHBoxLayout()
        row.addWidget(self.level_slider)
        row.addWidget(self.level_spin)

        container = QtWidgets.QWidget()
        container.setLayout(row)

        layout.addRow("LEVEL", container)
        self.tabs.addTab(tab, "Level")

    def _build_am_tab(self):
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QFormLayout(tab)

        self.amsource_combo = QtWidgets.QComboBox()
        self.amsource_combo.addItems(["INT1", "INT2", "EXT1", "EXT2"])

        self.amfreq_spin = QtWidgets.QDoubleSpinBox()
        self.amfreq_spin.setDecimals(3)
        self.amfreq_spin.setRange(0.0, 1e9)
        self.amfreq_spin.setValue(1000.0)
        self.amfreq_spin.setSuffix(" Hz")

        self.amdepth_spin = QtWidgets.QDoubleSpinBox()
        self.amdepth_spin.setDecimals(3)
        self.amdepth_spin.setRange(0.0, 1.0)
        self.amdepth_spin.setValue(0.8)
        self.amdepth_spin.setSingleStep(0.01)

        self.amwave_combo = QtWidgets.QComboBox()
        self.amwave_combo.addItems(["SINE", "SQUARE", "TRIANGLE"])

        self.lfout_combo = QtWidgets.QComboBox()
        self.lfout_combo.addItems(["OFF", "ON"])

        self.am_status = QtWidgets.QLineEdit("AM is Off")
        self.am_status.setReadOnly(True)

        self.am_button = QtWidgets.QPushButton("AM On/Off")

        layout.addRow("AMSOURCE", self.amsource_combo)
        layout.addRow("AMFREQ", self.amfreq_spin)
        layout.addRow("AMDEPTH", self.amdepth_spin)
        layout.addRow("AMWAVE", self.amwave_combo)
        layout.addRow("LFOUT", self.lfout_combo)
        layout.addRow("", self.am_status)
        layout.addRow("", self.am_button)

        self.tabs.addTab(tab, "AM")

    def _build_pm_tab(self):
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QFormLayout(tab)

        self.pmsource_combo = QtWidgets.QComboBox()
        self.pmsource_combo.addItems(["INT", "EXT1", "EXT2"])

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

        self.pmpol_combo = QtWidgets.QComboBox()
        self.pmpol_combo.addItems(["NORMAL", "INVERTED"])

        self.pm_status = QtWidgets.QLineEdit("PM is Off")
        self.pm_status.setReadOnly(True)

        self.pm_button = QtWidgets.QPushButton("PM On/Off")

        layout.addRow("PMSOURCE", self.pmsource_combo)
        layout.addRow("PMFREQ", self.pmfreq_spin)
        layout.addRow("PMWIDTH", self.pmwidth_spin)
        layout.addRow("PMDELAY", self.pmdelay_spin)
        layout.addRow("PMPOL", self.pmpol_combo)
        layout.addRow("", self.pm_status)
        layout.addRow("", self.pm_button)

        self.tabs.addTab(tab, "PM")

    def _connect_signals(self):
        self.init_button.clicked.connect(self.on_init_clicked)
        self.rf_button.clicked.connect(self.on_rf_clicked)
        self.am_button.clicked.connect(self.on_am_clicked)
        self.pm_button.clicked.connect(self.on_pm_clicked)

        self.freq_spin.valueChanged.connect(self.on_freq_changed)

        self.level_slider.valueChanged.connect(self.on_level_slider_changed)
        self.level_spin.valueChanged.connect(self.on_level_spin_changed)

        self.amfreq_spin.valueChanged.connect(self.on_am_config_changed)
        self.amdepth_spin.valueChanged.connect(self.on_am_config_changed)
        self.amwave_combo.currentTextChanged.connect(self.on_am_config_changed)
        self.amsource_combo.currentTextChanged.connect(self.on_am_config_changed)
        self.lfout_combo.currentTextChanged.connect(self.on_am_config_changed)

        self.pmfreq_spin.valueChanged.connect(self.on_pm_config_changed)
        self.pmsource_combo.currentTextChanged.connect(self.on_pm_config_changed)
        self.pmwidth_spin.valueChanged.connect(self.on_pm_config_changed)
        self.pmpol_combo.currentTextChanged.connect(self.on_pm_config_changed)
        self.pmdelay_spin.valueChanged.connect(self.on_pm_config_changed)

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
            self.sg.Init(ini)

            # Achtung: im Original steht einmal "outpoutstate" im INI,
            # später aber "outputstate" in conf.
            self.RF_is_on = self.sg.conf["channel_1"]["outputstate"] in ("1", "on", "ON", True)

            self.AM_is_on = False
            self.PM_is_on = False

            self.level = self.sg.conf["channel_1"]["level"]
            self.unit = self.sg.conf["channel_1"]["unit"]
            self.level = conv.c2c(self.unit, self.int_unit, self.level)

            self._set_level_ui(float(self.level))

            self.amfreq = 1e3
            self.amdepth = 0.8
            self.amwave = "SINE"
            self.amsource = "INT1"
            self.lfout = "OFF"

            self.pmfreq = 1000.0
            self.pmwidth = 100e-6
            self.pmdelay = 0.0
            self.pmsource = "INT"
            self.pmpol = "NORMAL"

            self.amfreq_spin.setValue(self.amfreq)
            self.amdepth_spin.setValue(self.amdepth)
            self.amwave_combo.setCurrentText(self.amwave)
            self.amsource_combo.setCurrentText(self.amsource)
            self.lfout_combo.setCurrentText(self.lfout)

            self.pmfreq_spin.setValue(self.pmfreq)
            self.pmwidth_spin.setValue(self.pmwidth)
            self.pmdelay_spin.setValue(self.pmdelay)
            self.pmsource_combo.setCurrentText(self.pmsource)
            self.pmpol_combo.setCurrentText(self.pmpol)

            self.update_rf()
            self.update_am()
            self.update_pm()

        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Init-Fehler", str(e))

    def on_rf_clicked(self):
        try:
            self.RF_is_on = not self.RF_is_on
            if self.RF_is_on:
                self.sg.RFOn()
            else:
                self.sg.RFOff()
            self.update_rf()
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "RF-Fehler", str(e))

    def on_am_clicked(self):
        try:
            self.AM_is_on = not self.AM_is_on
            if self.AM_is_on:
                self.sg.AMOn()
            else:
                self.sg.AMOff()
            self.update_am()
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "AM-Fehler", str(e))

    def on_pm_clicked(self):
        try:
            self.PM_is_on = not self.PM_is_on
            if self.PM_is_on:
                self.sg.PMOn()
            else:
                self.sg.PMOff()
            self.update_pm()
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "PM-Fehler", str(e))

    def on_freq_changed(self, value):
        try:
            self.sg.SetFreq(value)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "FREQ-Fehler", str(e))

    def on_level_slider_changed(self, value):
        dbm_value = value / 10.0
        if abs(self.level_spin.value() - dbm_value) > 1e-9:
            self.level_spin.blockSignals(True)
            self.level_spin.setValue(dbm_value)
            self.level_spin.blockSignals(False)
        self._apply_level(dbm_value)

    def on_level_spin_changed(self, value):
        slider_value = int(round(value * 10))
        if self.level_slider.value() != slider_value:
            self.level_slider.blockSignals(True)
            self.level_slider.setValue(slider_value)
            self.level_slider.blockSignals(False)
        self._apply_level(value)

    def _apply_level(self, value):
        try:
            self.level = value
            lv, unit = conv.c2scuq(self.int_unit, self.level)
            self.sg.SetLevel(Quantity(unit, lv))
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "LEVEL-Fehler", str(e))

    def _set_level_ui(self, value):
        self.level_spin.blockSignals(True)
        self.level_slider.blockSignals(True)

        self.level_spin.setValue(value)
        self.level_slider.setValue(int(round(value * 10)))

        self.level_spin.blockSignals(False)
        self.level_slider.blockSignals(False)

    def on_am_config_changed(self, *args):
        try:
            self.amfreq = self.amfreq_spin.value()
            self.amdepth = self.amdepth_spin.value()
            self.amwave = self.amwave_combo.currentText()
            self.amsource = self.amsource_combo.currentText()
            self.lfout = self.lfout_combo.currentText()

            self.sg.ConfAM(self.amsource, self.amfreq, self.amdepth, self.amwave, self.lfout)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "AM-Konfigurationsfehler", str(e))

    def on_pm_config_changed(self, *args):
        try:
            self.pmfreq = self.pmfreq_spin.value()
            self.pmsource = self.pmsource_combo.currentText()
            self.pmwidth = self.pmwidth_spin.value()
            self.pmpol = self.pmpol_combo.currentText()
            self.pmdelay = self.pmdelay_spin.value()

            self.sg.ConfPM(self.pmsource, self.pmfreq, self.pmpol, self.pmwidth, self.pmdelay)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "PM-Konfigurationsfehler", str(e))

    def update_rf(self):
        self.rf_status.setText("RF is On" if self.RF_is_on else "RF is Off")

    def update_am(self):
        self.am_status.setText("AM is On" if self.AM_is_on else "AM is Off")

    def update_pm(self):
        self.pm_status.setText("PM is On" if self.PM_is_on else "PM is Off")

    def closeEvent(self, event):
        try:
            if hasattr(self.sg, "Quit"):
                self.sg.Quit()
        except Exception:
            pass
        super().closeEvent(event)


# ---------------------------------------------------------
# Beispielstart mit Dummy-Generator
# ---------------------------------------------------------

if __name__ == "__main__":
    class DummySG:
        def __init__(self):
            self.conf = {
                "channel_1": {
                    "outputstate": "0",
                    "level": -20,
                    "unit": "dBm",
                }
            }

        def Init(self, ini):
            print("Init called")
            print(ini.read())

        def RFOn(self):
            self.conf["channel_1"]["outputstate"] = "1"
            print("RFOn")

        def RFOff(self):
            self.conf["channel_1"]["outputstate"] = "0"
            print("RFOff")

        def AMOn(self):
            print("AMOn")

        def AMOff(self):
            print("AMOff")

        def PMOn(self):
            print("PMOn")

        def PMOff(self):
            print("PMOff")

        def SetFreq(self, value):
            print("SetFreq", value)

        def SetLevel(self, quantity):
            print("SetLevel", quantity)

        def ConfAM(self, source, freq, depth, wave, lfout):
            print("ConfAM", source, freq, depth, wave, lfout)

        def ConfPM(self, source, freq, pol, width, delay):
            print("ConfPM", source, freq, pol, width, delay)

        def Quit(self):
            print("Quit")

    app = QtWidgets.QApplication(sys.argv)
    window = SignalGeneratorWidget(DummySG())
    window.show()
    sys.exit(app.exec())