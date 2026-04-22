# -*- coding: utf-8 -*-
"""Graphical test utility for amplifier drivers."""

import argparse
import configparser
import importlib
import io
import sys
from pathlib import Path

from PySide6 import QtCore, QtWidgets

from mpylab.device.amplifier_virtual import AMPLIFIER as VIRTUAL_AMPLIFIER
from mpylab.device.nport_ui import NPortWidget
from mpylab.device.ui_ini_draft import clear_ini_draft
from mpylab.tools.configuration import parse_ini_value, strbool
from mpylab.tools.util import format_block


SETTINGS_APP = "amplifier_ui"


std_ini_text = format_block("""
    [description]
    DESCRIPTION = Virtual Amplifier
    TYPE = AMPLIFIER
    VENDOR = mpylab
    SERIALNR =
    DEVICEID =
    DRIVER = amplifier_virtual.py

    [INIT_VALUE]
    FSTART = 10e6
    FSTOP = 6e9
    FSTEP = 0
    NR_OF_CHANNELS = 2
    VIRTUAL = 1

    [CHANNEL_1]
    NAME = S21
    UNIT = dB
    INTERPOLATION = LOG
    FILE = io.StringIO(format_block('''
        FUNIT: Hz
        UNIT: dB
        ABSERROR: 0.5
        10e6 40
        100e6 43
        1e9 45
        3e9 44
        6e9 42
        '''))

    [CHANNEL_2]
    NAME = MAXIN
    UNIT = dBm
    INTERPOLATION = LOG
    FILE = io.StringIO(format_block('''
        FUNIT: Hz
        UNIT: dBm
        ABSERROR: 0.0
        10e6 -10
        6e9 -10
        '''))
    """).strip()


class AmplifierWidget(NPortWidget):
    """N-port style amplifier UI with guarded active-state controls."""

    def __init__(self, instance, ini=None, parent=None, use_ini_draft=True):
        self._operate_allowed = False
        self._operate_blocked_count = 0
        self._raw_operate = None
        super().__init__(
            instance,
            ini=ini if ini is not None else io.StringIO(std_ini_text),
            kind="amplifier",
            parent=parent,
            use_ini_draft=use_ini_draft,
        )
        self.setWindowTitle("Amplifier Test Utility")
        self._install_operate_guard()
        self._refresh_amp_state_fields()

    def _build_ui(self):
        super()._build_ui()
        self._build_active_tab()

    def _build_active_tab(self):
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)

        info = QtWidgets.QLabel(
            "Operate is guarded. The default answer is No, and automatic Operate calls are blocked unless explicitly allowed."
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        button_row = QtWidgets.QHBoxLayout()
        self.pon_button = QtWidgets.QPushButton("POn")
        self.pon_button.clicked.connect(lambda: self._run_state_command("POn"))
        self.operate_button = QtWidgets.QPushButton("Operate")
        self.operate_button.clicked.connect(self.on_operate_clicked)
        self.standby_button = QtWidgets.QPushButton("Standby")
        self.standby_button.clicked.connect(lambda: self._run_state_command("Standby"))
        self.poff_button = QtWidgets.QPushButton("POff")
        self.poff_button.clicked.connect(lambda: self._run_state_command("POff"))
        for button in (self.pon_button, self.operate_button, self.standby_button, self.poff_button):
            button_row.addWidget(button)
        button_row.addStretch()
        layout.addLayout(button_row)

        form = QtWidgets.QFormLayout()
        self.amp_state_edit = QtWidgets.QLineEdit()
        self.amp_state_edit.setReadOnly(True)
        self.operate_blocked_edit = QtWidgets.QLineEdit()
        self.operate_blocked_edit.setReadOnly(True)
        form.addRow("State", self.amp_state_edit)
        form.addRow("Blocked Operate Calls", self.operate_blocked_edit)
        layout.addLayout(form)
        layout.addStretch()
        self.tabs.insertTab(2, tab, "Active")

    def _load_ini(self):
        from mpylab.device.ui_ini_draft import load_ini_with_draft

        content = load_ini_with_draft(
            self,
            self.ini_edit,
            self.ini_source,
            std_ini_text,
            SETTINGS_APP,
            use_draft=self.use_ini_draft,
        )
        self._last_ini_text = content

    def _refresh_status_bar(self, state=None):
        state = state or ("Busy" if self._busy else "Ready")
        self.state_label.setText(f"State: {state}")
        self.init_label.setText(f"Init: {'initialized' if self._is_initialized else 'not initialized'}")
        self.driver_label.setText(f"Driver: {type(self.dev).__module__}.{type(self.dev).__name__}")
        self.error_label.setText(f"Last error: {self._last_error_text}")

    def _ini_driver_settings(self, ini_text):
        config = configparser.ConfigParser()
        config.read_file(io.StringIO(ini_text))
        description = {}
        init_value = {}
        for section in config.sections():
            key = section.strip().lower()
            if key == "description":
                description = {name.lower(): parse_ini_value(value) for name, value in config.items(section)}
            elif key == "init_value":
                init_value = {name.lower(): parse_ini_value(value) for name, value in config.items(section)}
        driver = str(description.get("driver", "") or "").strip()
        virtual = strbool(init_value.get("virtual", False))
        return driver, virtual

    def _module_name_from_driver(self, driver, virtual):
        if virtual:
            return "amplifier_virtual"
        module_name = Path(driver).with_suffix("").name.strip()
        return module_name or "amplifier_virtual"

    def _instantiate_driver(self, module_name):
        module = importlib.import_module(f"mpylab.device.{module_name}")
        driver_cls = getattr(module, "AMPLIFIER")
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
            self._install_operate_guard()
            return
        old_driver = self.dev
        self.dev = self._instantiate_driver(module_name)
        self._install_operate_guard()
        self._is_initialized = False
        self.log_message(f"Driver switched from {type(old_driver).__module__} to {type(self.dev).__module__}.")
        self._refresh_status_bar()

    def _install_operate_guard(self):
        original = getattr(self.dev, "Operate", None)
        if original is None:
            self._raw_operate = None
            return
        if getattr(original, "_mpylab_operate_guard", False):
            return
        self._raw_operate = original

        def guarded_operate(*args, **kwargs):
            if self._operate_allowed:
                return original(*args, **kwargs)
            self._operate_blocked_count += 1
            return 0

        guarded_operate._mpylab_operate_guard = True
        self.dev.Operate = guarded_operate

    def _refresh_amp_state_fields(self):
        if not hasattr(self, "amp_state_edit"):
            return
        state = getattr(self.dev, "state", "unknown")
        self.amp_state_edit.setText(str(state))
        self.operate_blocked_edit.setText(str(self._operate_blocked_count))

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

    def _run_state_command(self, method_name):
        method = getattr(self.dev, method_name)

        def success(result):
            self._refresh_amp_state_fields()
            self.log_message(f"{method_name} returned: {result}")

        self._start_task(method_name, method, success)

    def on_operate_clicked(self):
        answer = QtWidgets.QMessageBox.question(
            self,
            "Operate Amplifier?",
            "Operate can enable RF output or gain. Execute Operate now?",
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
            QtWidgets.QMessageBox.StandardButton.No,
        )
        if answer != QtWidgets.QMessageBox.StandardButton.Yes:
            self.log_message("Operate canceled by user.")
            return
        if self._raw_operate is None:
            self._show_missing_operate()
            return

        def task():
            self._operate_allowed = True
            try:
                return self._raw_operate()
            finally:
                self._operate_allowed = False

        self._start_task("Operate", task, lambda result: self._refresh_amp_state_fields())

    def _show_missing_operate(self):
        QtWidgets.QMessageBox.warning(self, "Operate unavailable", "Current driver does not implement Operate().")

    def on_init_clicked(self):
        ini_text = self.ini_edit.toPlainText()
        channel = self.channel_spin.value()
        try:
            self._select_driver_from_ini(ini_text)
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "Driver Selection Error", str(exc))
            return

        def task():
            return self.dev.Init(io.StringIO(ini_text), channel=channel)

        def success(err):
            self._is_initialized = (err == 0)
            self._refresh_amp_state_fields()
            self._set_plot_range_from_loaded_data()
            self.refresh_status()

        self._start_task("Init", task, success)

    def refresh_status(self):
        def task():
            snapshot = {
                "description": self.dev.GetDescription(),
                "freq": self.dev.GetFreq(),
                "channels": self.dev.GetChannels() if hasattr(self.dev, "GetChannels") else (0, tuple(self.dev.data.keys())),
                "virtual": self.dev.GetVirtual(),
            }
            get_state = getattr(self.dev, "GetState", None)
            snapshot["amp_state"] = get_state() if get_state is not None else (0, getattr(self.dev, "state", "unknown"))
            return snapshot

        def success(snapshot):
            self.description_edit.setText(str(snapshot["description"][1]))
            self.freq_edit.setText(str(snapshot["freq"][1]))
            channels = tuple(snapshot["channels"][1])
            self.channels_edit.setText(", ".join(channels))
            self.virtual_edit.setText(str(snapshot["virtual"][1]))
            self.amp_state_edit.setText(str(snapshot["amp_state"][1]))
            self.operate_blocked_edit.setText(str(self._operate_blocked_count))
            self._sync_channel_combos(channels)

        self._start_task("Refresh Status", task, success)

    def on_save_ini_clicked(self):
        path, _filter = QtWidgets.QFileDialog.getSaveFileName(self, "Save INI", "", "INI Files (*.ini *.txt);;All Files (*)")
        if not path:
            return
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(self.ini_edit.toPlainText())
        clear_ini_draft(self)

    def on_smoke_clicked(self):
        ini_text = self.ini_edit.toPlainText()
        channel = self.channel_spin.value()
        try:
            self._select_driver_from_ini(ini_text)
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "Driver Selection Error", str(exc))
            return

        def task():
            lines = [f"Init: {self.dev.Init(io.StringIO(ini_text), channel=channel)}"]
            lines.append(f"Description: {self.dev.GetDescription()}")
            lines.append(f"Channels: {self.dev.GetChannels()}")
            first = next(iter(self.dev.data.keys()))
            lines.append(f"SetFreq: {self.dev.SetFreq(self.freq_spin.value_hz())}")
            lines.append(f"GetFreq: {self.dev.GetFreq()}")
            lines.append(f"GetData({first}): {self.dev.GetData(first)}")
            lines.append(f"Standby: {self.dev.Standby()}")
            return "\n".join(lines)

        self._start_task("Smoke Test", task, lambda result: self.smoke_result.setPlainText(result))

    def closeEvent(self, event):
        if self._active_thread is not None and self._active_thread.isRunning():
            event.ignore()
            QtWidgets.QMessageBox.information(
                self, "Operation in progress", "Close after the current operation has finished."
            )
            return
        try:
            if hasattr(self.dev, "Standby"):
                self.dev.Standby()
                self.log_message("Standby sent before close.")
        except Exception as exc:
            self.log_message(f"Standby on close failed: {type(exc).__name__}: {exc}")
        try:
            if hasattr(self.dev, "Quit"):
                self.dev.Quit()
        except Exception as exc:
            self.log_message(f"Quit on close failed: {type(exc).__name__}: {exc}")
        super().closeEvent(event)


UI = AmplifierWidget


def main(argv=None):
    parser = argparse.ArgumentParser(description="Amplifier driver test utility")
    parser.add_argument("--ini", help="Path to an INI file to preload")
    parser.add_argument("--virtual", action="store_true", help="Use the virtual amplifier driver")
    parser.add_argument(
        "--threaded",
        action="store_true",
        help="Run driver calls in worker threads. Disabled by default for backend stability.",
    )
    args = parser.parse_args(argv)

    if args.virtual:
        amp = VIRTUAL_AMPLIFIER()
        ini = io.StringIO(std_ini_text)
    else:
        amp = VIRTUAL_AMPLIFIER()
        ini = args.ini if args.ini else io.StringIO(std_ini_text)
        print("Driver will be selected from the INI file on Init. Using virtual amplifier until then.")

    app = QtWidgets.QApplication(sys.argv if argv is None else [sys.argv[0], *argv])
    window = AmplifierWidget(amp, ini=ini, use_ini_draft=not args.virtual)
    window._use_worker_threads = args.threaded
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
