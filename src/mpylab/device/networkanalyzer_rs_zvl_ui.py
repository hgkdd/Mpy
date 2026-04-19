# -*- coding: utf-8 -*-
#
"""ZVL-specific graphical test utility."""

import io
import sys

from PySide6 import QtCore, QtWidgets

from mpylab.device.networkanalyzer_ui import NetworkAnalyzerWidget
from mpylab.device.nw_rs_zvl import NETWORKANALYZER


class UI(NetworkAnalyzerWidget):
    """ZVL-specific extension of the generic network analyzer test utility."""

    def __init__(self, instance, ini=None, parent=None):
        super().__init__(instance, ini=ini, parent=parent)
        self.setWindowTitle("R&S ZVL Test Utility")
        self._build_zvl_topology_tab()
        self.refresh_all()

    def _build_zvl_topology_tab(self):
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)

        toolbar = QtWidgets.QHBoxLayout()
        self.refresh_topology_button = QtWidgets.QPushButton("Refresh Topology")
        self.refresh_topology_button.clicked.connect(self.refresh_topology)
        toolbar.addWidget(self.refresh_topology_button)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        splitter = QtWidgets.QSplitter()
        layout.addWidget(splitter)

        window_group = QtWidgets.QGroupBox("Windows")
        window_layout = QtWidgets.QVBoxLayout(window_group)
        self.window_list = QtWidgets.QListWidget()
        self.window_list.itemSelectionChanged.connect(self.on_window_selected_in_list)
        window_layout.addWidget(self.window_list)

        window_input_row = QtWidgets.QHBoxLayout()
        self.window_name_edit = QtWidgets.QLineEdit()
        self.window_name_edit.setPlaceholderText("window name")
        window_input_row.addWidget(self.window_name_edit)
        window_layout.addLayout(window_input_row)

        window_button_row = QtWidgets.QHBoxLayout()
        self.create_window_button = QtWidgets.QPushButton("Create")
        self.create_window_button.clicked.connect(self.on_create_window_clicked)
        self.select_window_button = QtWidgets.QPushButton("Select")
        self.select_window_button.clicked.connect(self.on_select_window_clicked)
        self.delete_window_button = QtWidgets.QPushButton("Delete Active")
        self.delete_window_button.clicked.connect(self.on_delete_window_clicked)
        window_button_row.addWidget(self.create_window_button)
        window_button_row.addWidget(self.select_window_button)
        window_button_row.addWidget(self.delete_window_button)
        window_layout.addLayout(window_button_row)

        trace_group = QtWidgets.QGroupBox("Traces")
        trace_layout = QtWidgets.QVBoxLayout(trace_group)
        self.trace_list = QtWidgets.QListWidget()
        self.trace_list.itemSelectionChanged.connect(self.on_trace_selected_in_list)
        trace_layout.addWidget(self.trace_list)

        trace_form = QtWidgets.QFormLayout()
        self.trace_name_edit = QtWidgets.QLineEdit()
        self.trace_name_edit.setPlaceholderText("trace name")
        self.sparam_combo = QtWidgets.QComboBox()
        self.sparam_combo.addItems(["S11", "S12", "S21", "S22"])
        trace_form.addRow("Trace Name", self.trace_name_edit)
        trace_form.addRow("S-Parameter", self.sparam_combo)
        trace_layout.addLayout(trace_form)

        trace_button_row = QtWidgets.QHBoxLayout()
        self.create_trace_button = QtWidgets.QPushButton("Create")
        self.create_trace_button.clicked.connect(self.on_create_trace_clicked)
        self.select_trace_button = QtWidgets.QPushButton("Select")
        self.select_trace_button.clicked.connect(self.on_select_trace_clicked)
        self.delete_trace_button = QtWidgets.QPushButton("Delete Active")
        self.delete_trace_button.clicked.connect(self.on_delete_trace_clicked)
        trace_button_row.addWidget(self.create_trace_button)
        trace_button_row.addWidget(self.select_trace_button)
        trace_button_row.addWidget(self.delete_trace_button)
        trace_layout.addLayout(trace_button_row)

        active_group = QtWidgets.QGroupBox("Active Objects")
        active_layout = QtWidgets.QFormLayout(active_group)
        self.active_window_field = QtWidgets.QLineEdit()
        self.active_window_field.setReadOnly(True)
        self.active_trace_field = QtWidgets.QLineEdit()
        self.active_trace_field.setReadOnly(True)
        self.active_sparam_field = QtWidgets.QLineEdit()
        self.active_sparam_field.setReadOnly(True)
        self.set_sparam_button = QtWidgets.QPushButton("Apply to Active Trace")
        self.set_sparam_button.clicked.connect(self.on_set_sparameter_clicked)
        active_layout.addRow("Active Window", self.active_window_field)
        active_layout.addRow("Active Trace", self.active_trace_field)
        active_layout.addRow("Current S-Parameter", self.active_sparam_field)
        active_layout.addRow("Set S-Parameter", self.set_sparam_button)

        splitter.addWidget(window_group)
        splitter.addWidget(trace_group)
        splitter.addWidget(active_group)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 1)

        self.tabs.insertTab(2, tab, "Topology")

    def after_refresh_all(self):
        self.refresh_topology()

    def refresh_topology(self):
        self.window_list.clear()
        self.trace_list.clear()

        windows = getattr(self.dv, "windows", {})
        traces = getattr(self.dv, "traces", {})

        for name, win in sorted(windows.items(), key=lambda item: item[1].getInternNumber()):
            item = QtWidgets.QListWidgetItem(f"{name}  [#{win.getInternNumber()}]")
            item.setData(QtCore.Qt.ItemDataRole.UserRole, name)
            self.window_list.addItem(item)

        for name, trace in sorted(traces.items(), key=lambda item: item[1].getTraceWindowNumber()):
            item = QtWidgets.QListWidgetItem(
                f"{name}  [{trace.getsparameter()} | {trace.getInternName()}]"
            )
            item.setData(QtCore.Qt.ItemDataRole.UserRole, name)
            self.trace_list.addItem(item)

        self.active_window_field.setText(self._status_value("GetWindow"))
        self.active_trace_field.setText(self._status_value("GetTrace"))
        self.active_sparam_field.setText(self._status_value("GetSparameter"))

    def _selected_window_name(self):
        item = self.window_list.currentItem()
        if item is None:
            raise ValueError("No window selected")
        return item.data(QtCore.Qt.ItemDataRole.UserRole)

    def _selected_trace_name(self):
        item = self.trace_list.currentItem()
        if item is None:
            raise ValueError("No trace selected")
        return item.data(QtCore.Qt.ItemDataRole.UserRole)

    def on_window_selected_in_list(self):
        item = self.window_list.currentItem()
        if item is not None:
            self.window_name_edit.setText(item.data(QtCore.Qt.ItemDataRole.UserRole))

    def on_trace_selected_in_list(self):
        item = self.trace_list.currentItem()
        if item is not None:
            self.trace_name_edit.setText(item.data(QtCore.Qt.ItemDataRole.UserRole))

    def on_create_window_clicked(self):
        name = self.window_name_edit.text().strip()
        if not name:
            self._show_error("Create Window Error", ValueError("Window name is empty"))
            return
        self._apply_and_refresh("CreateWindow", lambda: self._call_driver("CreateWindow", name))

    def on_select_window_clicked(self):
        try:
            name = self.window_name_edit.text().strip() or self._selected_window_name()
        except Exception as exc:
            self._show_error("Select Window Error", exc)
            return
        self._apply_and_refresh("SetWindow", lambda: self._call_driver("SetWindow", name))

    def on_delete_window_clicked(self):
        self._apply_and_refresh("DelWindow", lambda: self._call_driver("DelWindow"))

    def on_create_trace_clicked(self):
        trace_name = self.trace_name_edit.text().strip()
        sparam = self.sparam_combo.currentText().strip()
        if not trace_name:
            self._show_error("Create Trace Error", ValueError("Trace name is empty"))
            return
        self._apply_and_refresh("CreateTrace", lambda: self._call_driver("CreateTrace", trace_name, sparam))

    def on_select_trace_clicked(self):
        try:
            trace_name = self.trace_name_edit.text().strip() or self._selected_trace_name()
        except Exception as exc:
            self._show_error("Select Trace Error", exc)
            return
        self._apply_and_refresh("SetTrace", lambda: self._call_driver("SetTrace", trace_name))

    def on_delete_trace_clicked(self):
        self._apply_and_refresh("DelTrace", lambda: self._call_driver("DelTrace"))

    def on_set_sparameter_clicked(self):
        sparam = self.sparam_combo.currentText().strip()
        self._apply_and_refresh("SetSparameter", lambda: self._call_driver("SetSparameter", sparam))


if __name__ == "__main__":
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
                        SetSweepCount: 1
                        SetSweepPoints: 401
                        SetSweepType: 'LINEAR'
                        """)
        ini = io.StringIO(ini_text)
    else:
        try:
            with open(ini, "r", encoding="utf-8") as f:
                ini = io.StringIO(f.read())
        except OSError as exc:
            print(f"INI file could not be read: {exc}")
            sys.exit(1)

    nw = NETWORKANALYZER()
    app = QtWidgets.QApplication(sys.argv)
    ui = UI(nw, ini=ini)
    ui.show()
    sys.exit(app.exec())
