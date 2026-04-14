# -*- coding: utf-8 -*-
#
"""This is :mod:`mpylab.device.networkanalyzer_rs_zvl_ui`:

   :author: Christian Albrecht, Hans Georg Krauthäuser

   :license: GPL-3 or higher
"""
from PySide6 import QtWidgets

from mpylab.device.networkanalyzer_ui import NetworkAnalyzerWidget
from nw_rs_zvl import NETWORKANALYZER


class UI(NetworkAnalyzerWidget):
    """
    PySide6-Version der UI für den R&S ZVL.

    Gegenüber ``NetworkAnalyzerWidget`` ergänzt diese Klasse den Zusatzbereich
    ``Main_Rest`` um:
        - SetWindow-Button
        - Anzeige des aktuellen Window-Werts
        - Eingabefeld für ein neues Window
    """

    def __init__(self, instance, ini=None, parent=None):
        super().__init__(instance, ini=ini, parent=parent)
        self.setWindowTitle("R&S ZVL Network Analyzer")
        self._build_zlv_tab()

    def _build_zlv_tab(self):
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)

        group = QtWidgets.QGroupBox("Main_Rest")
        group_layout = QtWidgets.QHBoxLayout(group)

        self.set_window_button = QtWidgets.QPushButton("SetWindow")
        self.set_window_button.clicked.connect(self.on_set_window_clicked)

        self.setwindow_value = QtWidgets.QLineEdit()
        self.setwindow_value.setReadOnly(True)
        self.setwindow_value.setPlaceholderText("Wert")
        self.setwindow_value.setMinimumWidth(160)

        self.new_setwindow_edit = QtWidgets.QLineEdit()
        self.new_setwindow_edit.setPlaceholderText("windowName")
        self.new_setwindow_edit.setMinimumWidth(160)

        group_layout.addWidget(self.set_window_button)
        group_layout.addWidget(QtWidgets.QLabel("Wert"))
        group_layout.addWidget(self.setwindow_value)
        group_layout.addWidget(QtWidgets.QLabel("windowName"))
        group_layout.addWidget(self.new_setwindow_edit)
        group_layout.addStretch()

        layout.addWidget(group)
        layout.addStretch()

        self.tabs.addTab(tab, "Main_Rest")

    def on_set_window_clicked(self):
        try:
            window_name = self.new_setwindow_edit.text().strip()
            if not window_name:
                QtWidgets.QMessageBox.warning(
                    self,
                    "Eingabe fehlt",
                    "Bitte einen Window-Namen eingeben."
                )
                return

            err, value = self.dv.SetWindow(window_name)
            self.setwindow_value.setText(str(value))

        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "SetWindow-Fehler", str(e))


if __name__ == "__main__":
    import sys
    import io
    from mpylab.tools.util import format_block

    try:
        ini = sys.argv[1]
    except IndexError:
        ini_text = format_block("""
                        [DESCRIPTION]
                        description: 'ZLV-K1'
                        type:        'NETWORKANALYZER'
                        vendor:      'Rohde&Schwarz'
                        serialnr:
                        deviceid:
                        driver:

                        [Init_Value]
                        fstart: 100e6
                        fstop: 6e9
                        fstep: 1
                        gpib: 18
                        virtual: 0
                        nr_of_channels: 2

                        [Channel_1]
                        unit: 'dBm'
                        SetRefLevel: 10
                        SetRBW: 10e3
                        SetSpan: 5999991000
                        CreateWindow: 'default'
                        CreateTrace: 'default','S22'
                        SetSweepCount: 0
                        SetSweepPoints: 100
                        SetSweepType: 'Log'
                        """)
        ini = io.StringIO(ini_text)
    else:
        try:
            with open(ini, "r", encoding="utf-8") as f:
                ini = io.StringIO(f.read())
        except OSError as e:
            print(f"INI-Datei konnte nicht gelesen werden: {e}")
            sys.exit(1)

    nw = NETWORKANALYZER()
    app = QtWidgets.QApplication(sys.argv)
    ui = UI(nw, ini=ini)
    ui.show()
    sys.exit(app.exec())
