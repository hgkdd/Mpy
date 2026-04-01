# -*- coding: utf-8 -*-
"""This is :mod:`mpylab.device.Metaui`: Metaclass to Build a standard GUI from the _setgetlist.

   :author: Hans Georg Krauthaeuser

   :license: GPL-3 or higher
"""
import io
import re
import math
import inspect
from functools import partial

from PySide6 import QtWidgets, QtCore

""" Verwendung der Klasse:

class MyDriverUI(DriverUIWidget):
    __driverclass__ = MyConcreteDriver
    __super_driverclass__ = MyDriverBase
    _ignore = ["IrgendEinCommand"]

    WINDOW_TITLE = "Spectrumanalyzer"

    def build_extra_tabs(self):
        tabs = []

        info_tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(info_tab)
        layout.addWidget(QtWidgets.QLabel("Zusätzlicher Tab"))
        layout.addStretch()

        tabs.append(("Info", info_tab))
        return tabs

# Starten so:
if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)

    w = MyDriverUI()
    w.show()

    sys.exit(app.exec())

"""




def call_driver_method(driver, method_name, *args):
    """
    Sichere Methode zum Aufruf einer Driver-Funktion.
    Erwartet oft Rückgaben wie (err, value) und liefert dann value zurück.
    """
    method = getattr(driver, method_name)
    result = method(*args)

    if isinstance(result, (tuple, list)) and len(result) >= 2:
        return result[1]
    return result


def is_getter_name(name: str) -> bool:
    return bool(re.match(r"^[Gg]et.*$", name))


def map_param_type_to_widget(py_type):
    """
    Ersetzt Erzeuge_TapiVar() durch passende Qt-Widgets.
    """
    if py_type == int:
        w = QtWidgets.QSpinBox()
        w.setRange(-10_000_000, 10_000_000)
        return w
    elif py_type == float:
        w = QtWidgets.QDoubleSpinBox()
        w.setDecimals(9)
        w.setRange(-1e15, 1e15)
        w.setSingleStep(1.0)
        return w
    else:
        return QtWidgets.QLineEdit()


def get_widget_value(widget):
    if isinstance(widget, QtWidgets.QSpinBox):
        return widget.value()
    if isinstance(widget, QtWidgets.QDoubleSpinBox):
        return widget.value()
    if isinstance(widget, QtWidgets.QLineEdit):
        return widget.text()
    if isinstance(widget, QtWidgets.QComboBox):
        return widget.currentText()
    return None


def set_widget_value(widget, value):
    text = "" if value is None else str(value)

    if isinstance(widget, QtWidgets.QSpinBox):
        try:
            widget.setValue(int(value))
        except Exception:
            pass
        return

    if isinstance(widget, QtWidgets.QDoubleSpinBox):
        try:
            widget.setValue(float(value))
        except Exception:
            pass
        return

    if isinstance(widget, QtWidgets.QLineEdit):
        widget.setText(text)
        return

    if isinstance(widget, QtWidgets.QLabel):
        widget.setText(text)
        return


class DriverUIWidget(QtWidgets.QWidget):
    """
    PySide6-Ersatz für die TraitsUI-Metaklassenlösung.

    In Unterklassen setzen:
        __driverclass__ = KonkreteDriverKlasse
        __super_driverclass__ = DriverSuperklasse
        _ignore = []

    Optionale Erweiterung:
        def build_extra_tabs(self) -> list[tuple[str, QWidget]]:
            ...
            return [("Name", widget), ...]
    """

    __driverclass__ = None
    __super_driverclass__ = None
    _ignore = []

    WINDOW_TITLE = "Driver UI"

    def __init__(self, driver_instance=None, ini_text="", parent=None):
        super().__init__(parent)

        if self.__driverclass__ is None:
            raise ValueError("__driverclass__ muss gesetzt sein")
        if self.__super_driverclass__ is None:
            raise ValueError("__super_driverclass__ muss gesetzt sein")

        self.dv = driver_instance if driver_instance is not None else self.__driverclass__()
        self.main_entries = []
        self.command_rows = {}
        self.result_widgets = {}
        self.param_widgets = {}

        self.setWindowTitle(self.WINDOW_TITLE)
        self.resize(1100, 800)

        self._build_ui(ini_text)

    # ------------------------------------------------------------------
    # Aufbau
    # ------------------------------------------------------------------

    def _build_ui(self, ini_text: str):
        outer = QtWidgets.QVBoxLayout(self)

        self.tabs = QtWidgets.QTabWidget()
        outer.addWidget(self.tabs)

        self._build_ini_tab(ini_text)
        self._build_main_tabs_from_cmds()
        self._build_not_implemented_tabs_from_commands()
        self._add_extra_tabs()

        bottom = QtWidgets.QHBoxLayout()
        bottom.addStretch()

        self.close_button = QtWidgets.QPushButton("Schließen")
        self.close_button.clicked.connect(self.close)
        bottom.addWidget(self.close_button)

        outer.addLayout(bottom)

    def _build_ini_tab(self, ini_text: str):
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)

        self.ini_edit = QtWidgets.QPlainTextEdit()
        self.ini_edit.setPlainText(ini_text or "")
        self.ini_edit.setMinimumHeight(220)

        self.init_button = QtWidgets.QPushButton("Init")
        self.init_button.clicked.connect(self._init_clicked)

        layout.addWidget(self.ini_edit)
        layout.addWidget(self.init_button)
        layout.addStretch()

        self.tabs.addTab(tab, "Ini")

    def _build_main_tabs_from_cmds(self):
        driverclass = self.__driverclass__
        _cmds = getattr(driverclass, "_cmds", {})

        rows = []

        for command_name, command in _cmds.items():
            if command_name in self._ignore:
                continue
            if command_name in self.main_entries:
                continue

            self.main_entries.append(command_name)
            row_widget = self._create_row_for_cmd(command_name, command)
            if row_widget is not None:
                rows.append(row_widget)

        self._add_rows_chunked_as_tabs(rows, prefix="Main")

    def _build_not_implemented_tabs_from_commands(self):
        super_driverclass = self.__super_driverclass__
        commands = getattr(super_driverclass, "_commands", {})
        rows = []

        for command_name, item in commands.items():
            if command_name in self.main_entries:
                continue
            if command_name in self._ignore:
                continue

            if self._is_directly_implemented(command_name, item):
                continue

            row_widget = self._create_row_for_commands_entry(command_name, item)
            if row_widget is not None:
                rows.append(row_widget)

        self._add_rows_chunked_as_tabs(rows, prefix="NotImp")

    def _add_rows_chunked_as_tabs(self, row_widgets, prefix="Tab", chunk_size=16):
        for idx in range(0, len(row_widgets), chunk_size):
            chunk = row_widgets[idx:idx + chunk_size]

            tab = QtWidgets.QWidget()
            layout = QtWidgets.QVBoxLayout(tab)

            for row in chunk:
                layout.addWidget(row)

            layout.addStretch()
            self.tabs.addTab(tab, f"{prefix}_{idx // chunk_size}")

    def _add_extra_tabs(self):
        for title, widget in self.build_extra_tabs():
            self.tabs.addTab(widget, title)

    def build_extra_tabs(self):
        """
        Ersatz für Traits-GROUPS aus Basisklassen/UI-Klassen.
        Kann in Unterklassen überschrieben werden.
        """
        return []

    # ------------------------------------------------------------------
    # Zeilenbau für _cmds
    # ------------------------------------------------------------------

    def _create_row_for_cmd(self, command_name, command):
        row = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(row)
        layout.setContentsMargins(4, 4, 4, 4)

        # Button für das Hauptkommando
        cmd_button = QtWidgets.QPushButton(command_name)
        layout.addWidget(cmd_button)

        result_target_name = None

        # Falls das Kommando eine Rfunction hat:
        rfunction = command.Rfunction() if hasattr(command, "Rfunction") else None
        if rfunction:
            r_button = QtWidgets.QPushButton(rfunction)
            layout.addWidget(r_button)

            result_widget = QtWidgets.QLineEdit()
            result_widget.setReadOnly(True)
            result_widget.setPlaceholderText("Wert")
            result_widget.setMinimumWidth(160)
            layout.addWidget(result_widget)

            self.result_widgets[rfunction.upper()] = result_widget
            result_target_name = rfunction.upper()

            if rfunction not in self.main_entries:
                self.main_entries.append(rfunction)

            r_button.clicked.connect(partial(self._run_simple_method, rfunction, rfunction.upper()))
        else:
            result_widget = QtWidgets.QLineEdit()
            result_widget.setReadOnly(True)
            result_widget.setPlaceholderText("Wert")
            result_widget.setMinimumWidth(160)
            layout.addWidget(result_widget)

            self.result_widgets[command_name.upper()] = result_widget
            result_target_name = command_name.upper()

        # Parameterfelder
        param_widgets_for_command = []

        for param_name in getattr(command, "getParameterTuple", lambda: [])():
            param_meta = command.getParameter()[param_name]

            if param_meta.isClass_attr():
                continue

            if hasattr(self.__driverclass__, command_name):
                try:
                    sig = inspect.signature(getattr(self.__driverclass__, command_name))
                    if param_name not in sig.parameters:
                        continue
                except Exception:
                    pass

            label = QtWidgets.QLabel(param_name)
            layout.addWidget(label)

            widget = map_param_type_to_widget(param_meta.Getptype())
            widget.setMinimumWidth(120)
            layout.addWidget(widget)

            key = f"param_{command_name}_{param_name.upper()}"
            self.param_widgets[key] = widget
            param_widgets_for_command.append((param_name, widget))

        layout.addStretch()

        cmd_button.clicked.connect(
            partial(
                self._run_command_with_params,
                command_name,
                result_target_name,
                param_widgets_for_command,
            )
        )

        self.command_rows[command_name] = row
        return row

    # ------------------------------------------------------------------
    # Zeilenbau für _commands
    # ------------------------------------------------------------------

    def _create_row_for_commands_entry(self, command_name, item):
        row = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(row)
        layout.setContentsMargins(4, 4, 4, 4)

        button = QtWidgets.QPushButton(command_name)
        layout.addWidget(button)

        result_widget = QtWidgets.QLineEdit()
        result_widget.setReadOnly(True)
        result_widget.setPlaceholderText("Wert")
        result_widget.setMinimumWidth(160)
        layout.addWidget(result_widget)

        self.result_widgets[command_name.upper()] = result_widget

        param_widgets_for_command = []

        para_command = item.get("parameter")
        if para_command:
            if isinstance(para_command, str):
                para_command = (para_command,)

            for param_name in para_command:
                label = QtWidgets.QLabel(param_name)
                layout.addWidget(label)

                widget = QtWidgets.QLineEdit()
                widget.setMinimumWidth(120)
                layout.addWidget(widget)

                key = f"param_{command_name}_{param_name.upper()}"
                self.param_widgets[key] = widget
                param_widgets_for_command.append((param_name, widget))

        layout.addStretch()

        button.clicked.connect(
            partial(
                self._run_command_with_params,
                command_name,
                command_name.upper(),
                param_widgets_for_command,
            )
        )

        return row

    # ------------------------------------------------------------------
    # Logik
    # ------------------------------------------------------------------

    def _init_clicked(self):
        try:
            ini = io.StringIO(self.ini_edit.toPlainText())
            self.dv.Init(ini)

            # Alle Get-Funktionen einmal aufrufen
            for item in self.main_entries:
                if is_getter_name(item):
                    target_name = item.upper()
                    if target_name not in self.result_widgets:
                        # Falls Getter über Rfunction o.ä. angelegt wurde
                        target_name = item.upper()
                    self._run_simple_method(item, target_name)

        except Exception as e:
            self._show_error("Init-Fehler", e)

    def _run_simple_method(self, method_name, result_attr_name):
        try:
            value = call_driver_method(self.dv, method_name)
            self._set_result(result_attr_name, value)
        except Exception as e:
            self._show_error(f"Fehler bei {method_name}", e)

    def _run_command_with_params(self, command_name, result_attr_name, param_widgets_for_command):
        try:
            args = [get_widget_value(widget) for _, widget in param_widgets_for_command]
            value = call_driver_method(self.dv, command_name, *args)
            self._set_result(result_attr_name, value)
        except Exception as e:
            self._show_error(f"Fehler bei {command_name}", e)

    def _set_result(self, result_name, value):
        widget = self.result_widgets.get(result_name)
        if widget is not None:
            set_widget_value(widget, value)

    def _show_error(self, title, exc):
        QtWidgets.QMessageBox.critical(self, title, str(exc))

    def _is_directly_implemented(self, command_name, item):
        """
        Entspricht der ursprünglichen Prüfung:
        Wenn die Methode direkt implementiert ist und keinen NotImplementedError wirft,
        dann wird sie nicht in den NotImp-Tabs aufgebaut.
        """
        driverclass = self.__driverclass__

        try:
            driver_ins = driverclass()
        except Exception:
            # Wenn Instanzierung nicht klappt, lieber anzeigen statt verstecken
            return False

        try:
            params = item.get("parameter")
            args = []

            if params:
                if isinstance(params, str):
                    params = (params,)
                args = ["" for _ in params]

            method = getattr(driverclass, command_name)
            method(driver_ins, *args)

        except NotImplementedError:
            return False
        except Exception:
            # Irgendein anderer Fehler heißt nicht automatisch "implementiert"
            return False
        else:
            return True
        finally:
            # falls Driver __del__ benötigt
            try:
                driver_ins.__del__()
            except Exception:
                pass

    def closeEvent(self, event):
        try:
            if hasattr(self.dv, "Quit"):
                self.dv.Quit()
        except Exception:
            pass
        super().closeEvent(event)