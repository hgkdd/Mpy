# -*- coding: utf-8 -*-

import io
import sys

from PySide6 import QtWidgets, QtCore

from mpylab.tools.util import format_block
from mpylab.device.device import CONVERT
from mpylab.device.ui_ini_draft import load_ini_with_draft

conv = CONVERT()
SETTINGS_APP = "fieldprobe_ui"

std_ini_text = format_block("""
                [DESCRIPTION]
                description: 'FP TEMPLATE'
                type:        'FIELDPROBE'
                vendor:      'Some Vendor'
                serialnr:
                deviceid:
                driver:

                [Init_Value]
                fstart: 3e6
                fstop: 18e9
                fstep: 0
                gpib: 4
                virtual: 0

                [Channel_1]
                name: EField
                unit: Voverm
                """).strip()


class UI(QtWidgets.QWidget):
    def __init__(self, instance, ini=None, parent=None):
        super().__init__(parent)

        self.dev = instance
        self.ini_source = ini if ini is not None else io.StringIO(std_ini_text)

        self.ch = 1
        self.unit = ""
        self.setWindowTitle("Fieldprobe")
        self.resize(750, 500)

        self._build_ui()
        self._load_ini()
        self._connect_signals()

    # ---------------------------------------------------------
    # UI
    # ---------------------------------------------------------

    def _build_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)

        tabs = QtWidgets.QTabWidget()
        main_layout.addWidget(tabs)

        # Ini-Tab
        ini_tab = QtWidgets.QWidget()
        ini_layout = QtWidgets.QVBoxLayout(ini_tab)

        self.ini_edit = QtWidgets.QPlainTextEdit()
        self.ini_edit.setMinimumHeight(220)

        form = QtWidgets.QFormLayout()
        self.channel_spin = QtWidgets.QSpinBox()
        self.channel_spin.setMinimum(1)
        self.channel_spin.setValue(1)
        form.addRow("CHANNEL", self.channel_spin)

        self.init_button = QtWidgets.QPushButton("Init")

        ini_layout.addWidget(self.ini_edit)
        ini_layout.addLayout(form)
        ini_layout.addWidget(self.init_button)
        ini_layout.addStretch()

        # Freq-Tab
        freq_tab = QtWidgets.QWidget()
        freq_layout = QtWidgets.QFormLayout(freq_tab)

        self.freq_spin = QtWidgets.QDoubleSpinBox()
        self.freq_spin.setDecimals(3)
        self.freq_spin.setRange(0.0, 1e12)
        self.freq_spin.setValue(1e6)
        self.freq_spin.setSingleStep(1e3)
        self.freq_spin.setSuffix(" Hz")

        freq_layout.addRow("FREQ", self.freq_spin)

        tabs.addTab(ini_tab, "Ini")
        tabs.addTab(freq_tab, "Freq")

        self.trigger_button = QtWidgets.QPushButton("Trigger")
        main_layout.addWidget(self.trigger_button)

        power_group = QtWidgets.QGroupBox("Power")
        power_layout = QtWidgets.QVBoxLayout(power_group)

        self.power_edit = QtWidgets.QLineEdit()
        self.power_edit.setReadOnly(True)

        power_layout.addWidget(self.power_edit)
        main_layout.addWidget(power_group)

        bottom = QtWidgets.QHBoxLayout()
        bottom.addStretch()

        self.close_button = QtWidgets.QPushButton("Schließen")
        self.close_button.clicked.connect(self.close)
        bottom.addWidget(self.close_button)

        main_layout.addLayout(bottom)

    def _connect_signals(self):
        self.init_button.clicked.connect(self._Init_fired)
        self.trigger_button.clicked.connect(self._TRIGGER_fired)
        self.freq_spin.valueChanged.connect(self._FREQ_changed)
        self.channel_spin.valueChanged.connect(self._CHANNEL_changed)

    def _load_ini(self):
        load_ini_with_draft(self, self.ini_edit, self.ini_source, std_ini_text, SETTINGS_APP)

    # ---------------------------------------------------------
    # Logik
    # ---------------------------------------------------------

    def _Init_fired(self):
        try:
            ini = io.StringIO(self.ini_edit.toPlainText())
            self.ch = self.channel_spin.value()
            self.dev.Init(ini, self.ch)

            self.unit = self.dev.conf[f"channel_{self.ch}"]["unit"]
            self._FREQ_changed(self.freq_spin.value())

        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Init-Fehler", str(e))

    def _TRIGGER_fired(self):
        try:
            self.dev.Trigger()
            err, data = self.dev.GetData()
            self.power_edit.setText(str(data))
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Trigger-Fehler", str(e))

    def _FREQ_changed(self, value=None):
        try:
            if value is None:
                value = self.freq_spin.value()
            self.dev.SetFreq(value)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "FREQ-Fehler", str(e))

    def _CHANNEL_changed(self, value):
        try:
            if hasattr(self.dev, "Quit"):
                self.dev.Quit()
        except Exception:
            pass

        self._Init_fired()

    def closeEvent(self, event):
        try:
            if hasattr(self.dev, "Quit"):
                self.dev.Quit()
        except Exception:
            pass
        super().closeEvent(event)


def main():
    class DummyFieldProbe:
        def __init__(self):
            self.conf = {
                "channel_1": {"unit": "Voverm"},
                "channel_2": {"unit": "Voverm"},
            }

        def Init(self, ini, ch):
            print("Init called, channel:", ch)
            print(ini.read())

        def Trigger(self):
            print("Trigger called")

        def GetData(self):
            return 0, 12.34

        def SetFreq(self, value):
            print("SetFreq:", value)

        def Quit(self):
            print("Quit called")

    app = QtWidgets.QApplication(sys.argv)
    ui = UI(DummyFieldProbe())
    ui.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
