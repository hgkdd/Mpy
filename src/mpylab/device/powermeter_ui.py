# -*- coding: utf-8 -*-

import sys
import io
import atexit
from PySide6 import QtWidgets, QtCore

from mpylab.tools.util import format_block
from mpylab.device.device import CONVERT

conv = CONVERT()

std_ini = format_block("""
                [DESCRIPTION]
                description: PM template
                type:        POWERMETER
                vendor:      some company
                serialnr:    SN12345
                deviceid:    internal ID
                driver:      dummy.py

                [Init_Value]
                fstart: 100e3
                fstop: 18e9
                fstep: 1
                gpib: 13
                virtual: 0
                nr_of_channels: 2

                [Channel_1]
                name: A
                unit: 'W'

                [Channel_2]
                name: B
                unit: 'W'
                """).strip()


class PowerMeterWidget(QtWidgets.QWidget):
    def __init__(self, instance, ini=None, parent=None):
        super().__init__(parent)

        self.pm = instance
        self.ini_source = ini if ini is not None else io.StringIO(std_ini)
        self.ch = 1
        self.unit = ""

        self.setWindowTitle("Powermeter")
        self.resize(700, 500)

        self._build_ui()
        self._load_initial_ini()
        self._connect_signals()

    def _build_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)

        self.tabs = QtWidgets.QTabWidget()

        # -----------------------------
        # INI TAB
        # -----------------------------
        ini_tab = QtWidgets.QWidget()
        ini_layout = QtWidgets.QVBoxLayout(ini_tab)

        self.ini_edit = QtWidgets.QPlainTextEdit()
        self.ini_edit.setPlaceholderText("INI content")

        form_layout = QtWidgets.QFormLayout()
        self.channel_spin = QtWidgets.QSpinBox()
        self.channel_spin.setMinimum(1)
        self.channel_spin.setValue(1)

        form_layout.addRow("CHANNEL", self.channel_spin)

        self.init_button = QtWidgets.QPushButton("Init")

        ini_layout.addWidget(self.ini_edit)
        ini_layout.addLayout(form_layout)
        ini_layout.addWidget(self.init_button)
        ini_layout.addStretch()

        # -----------------------------
        # FREQ TAB
        # -----------------------------
        freq_tab = QtWidgets.QWidget()
        freq_layout = QtWidgets.QFormLayout(freq_tab)

        self.freq_spin = QtWidgets.QDoubleSpinBox()
        self.freq_spin.setDecimals(3)
        self.freq_spin.setRange(0.0, 1e12)
        self.freq_spin.setValue(1e6)
        self.freq_spin.setSingleStep(1e3)
        self.freq_spin.setSuffix(" Hz")

        freq_layout.addRow("FREQ", self.freq_spin)

        # -----------------------------
        # CMD TAB
        # -----------------------------
        cmd_tab = QtWidgets.QWidget()
        cmd_layout = QtWidgets.QFormLayout(cmd_tab)

        self.idn_combo = QtWidgets.QComboBox()
        self.idn_combo.addItems(["*IDN?", "*RST"])

        self.query_button = QtWidgets.QPushButton("Query")
        self.ans_edit = QtWidgets.QLineEdit()
        self.ans_edit.setPlaceholderText("Answer")

        cmd_layout.addRow("Commands IEEE 488.2", self.idn_combo)
        cmd_layout.addRow("", self.query_button)
        cmd_layout.addRow("", self.ans_edit)

        self.tabs.addTab(ini_tab, "Ini")
        self.tabs.addTab(freq_tab, "Freq")
        self.tabs.addTab(cmd_tab, "CMD")

        # -----------------------------
        # Trigger + Power display
        # -----------------------------
        self.trigger_button = QtWidgets.QPushButton("Trigger")

        power_group = QtWidgets.QGroupBox("Power")
        power_layout = QtWidgets.QVBoxLayout(power_group)

        self.power_edit = QtWidgets.QLineEdit()
        self.power_edit.setReadOnly(True)

        power_layout.addWidget(self.power_edit)

        main_layout.addWidget(self.tabs)
        main_layout.addWidget(self.trigger_button)
        main_layout.addWidget(power_group)

    def _connect_signals(self):
        self.init_button.clicked.connect(self.on_init_clicked)
        self.trigger_button.clicked.connect(self.on_trigger_clicked)
        self.freq_spin.valueChanged.connect(self.on_freq_changed)
        self.channel_spin.valueChanged.connect(self.on_channel_changed)
        self.query_button.clicked.connect(self.on_query_clicked)

    def _load_initial_ini(self):
        if hasattr(self.ini_source, "read"):
            try:
                content = self.ini_source.read()
            except Exception:
                content = std_ini
        else:
            content = str(self.ini_source)

        self.ini_edit.setPlainText(content)

    def closeEvent(self, event):
        try:
            self.pm.Quit()
        except Exception:
            pass
        super().closeEvent(event)

    def on_init_clicked(self):
        ini_text = self.ini_edit.toPlainText()
        ini_stream = io.StringIO(ini_text)

        self.ch = self.channel_spin.value()
        self.pm.Init(ini_stream, self.ch)
        atexit.register(self.pm.Quit)

        try:
            self.unit = self.pm.conf[f'channel_{self.ch}']['unit']
        except Exception:
            self.unit = ""

        self.on_freq_changed(self.freq_spin.value())

    def on_trigger_clicked(self):
        self.pm.Trigger()
        err, data = self.pm.GetData()
        self.power_edit.setText(str(data))

    def on_freq_changed(self, value):
        try:
            self.pm.SetFreq(value)
        except Exception:
            # Optional: error display/logging
            pass

    def on_channel_changed(self, value):
        try:
            self.pm.Quit()
        except Exception:
            pass
        self.on_init_clicked()

    def on_query_clicked(self):
        """
        Entspricht sinngemäß dem Traits-Handler _QUERY_senden().
        Je nach API Deines Geräts ggf. anpassen.
        """
        try:
            # Falls query() einen Befehl erwartet, hier z. B.:
            # answer = self.pm.query(self.idn_combo.currentText())
            # self.ans_edit.setText(str(answer))

            # Angelehnt an Dein Original:
            self.pm.query()
            err, data = self.pm.GetData()
            self.power_edit.setText(str(data))

            # Optional zusätzlich:
            self.ans_edit.setText(self.idn_combo.currentText())

        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Query error", str(e))


# -------------------------------------------------
# Beispiel-Start
# -------------------------------------------------
if __name__ == "__main__":
    class DummyPM:
        def __init__(self):
            self.conf = {
                "channel_1": {"unit": "W"},
                "channel_2": {"unit": "W"},
            }

        def Init(self, ini, ch):
            print("Init called with channel", ch)
            print(ini.read())

        def Quit(self):
            print("Quit called")

        def Trigger(self):
            print("Trigger called")

        def GetData(self):
            return 0, 0.12345

        def SetFreq(self, freq):
            print("SetFreq:", freq)

        def query(self):
            print("query called")

    app = QtWidgets.QApplication(sys.argv)
    pm = DummyPM()
    window = PowerMeterWidget(pm)
    window.show()
    sys.exit(app.exec())