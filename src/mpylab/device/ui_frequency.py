# -*- coding: utf-8 -*-
"""Reusable frequency input widget with direct unit apply buttons."""

from PySide6 import QtCore, QtWidgets


class FrequencyControl(QtWidgets.QWidget):
    """Input a frequency-like value using a normalized value field and unit buttons."""

    valueApplied = QtCore.Signal(float)

    UNITS = (
        ("Hz", 1.0),
        ("kHz", 1e3),
        ("MHz", 1e6),
        ("GHz", 1e9),
    )

    def __init__(self, parent=None, decimals=6, default_hz=0.0):
        super().__init__(parent)
        self._buttons = {}
        self._current_unit = "Hz"
        self._highlight_style = "background-color: #2f6fed; color: white; font-weight: bold;"
        self._normal_style = ""

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        self.spin = QtWidgets.QDoubleSpinBox()
        self.spin.setDecimals(decimals)
        self.spin.setRange(0.0, 1000.0)
        self.spin.setSingleStep(1.0)
        self.spin.setKeyboardTracking(False)
        self.spin.setMinimumWidth(92)
        self.spin.setMaximumWidth(118)
        layout.addWidget(self.spin, 1)

        for label, factor in self.UNITS:
            button = QtWidgets.QToolButton()
            button.setText(label)
            button.setCheckable(True)
            button.setMinimumWidth(34)
            button.setMaximumWidth(46)
            button.clicked.connect(lambda checked=False, unit=label: self.apply_unit(unit))
            self._buttons[label] = button
            layout.addWidget(button)

        self.setSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Fixed)
        self.set_value_hz(default_hz)

    def value_hz(self):
        """Return the currently displayed value converted to Hz."""
        return float(self.spin.value()) * self._factor(self._current_unit)

    def set_value_hz(self, value_hz):
        """Display a Hz value using the largest unit that keeps the value <= 1000."""
        try:
            value = float(value_hz)
        except (TypeError, ValueError):
            value = 0.0
        value = max(0.0, value)
        unit = "Hz"
        scaled = value
        for label, factor in self.UNITS:
            candidate = value / factor
            if candidate <= 1000.0 or label == self.UNITS[-1][0]:
                unit = label
                scaled = candidate
                break
        self._current_unit = unit
        self.spin.blockSignals(True)
        self.spin.setValue(scaled)
        self.spin.blockSignals(False)
        self._update_buttons()
        self.setToolTip(f"{value:g} Hz")

    def apply_unit(self, unit):
        """Select a unit and emit the resulting value in Hz."""
        self._current_unit = unit
        self._update_buttons()
        value = self.value_hz()
        self.setToolTip(f"{value:g} Hz")
        self.valueApplied.emit(value)

    def set_enabled(self, enabled):
        """Enable or disable the input and unit buttons."""
        self.spin.setEnabled(enabled)
        for button in self._buttons.values():
            button.setEnabled(enabled)

    def _factor(self, unit):
        for label, factor in self.UNITS:
            if label == unit:
                return factor
        return 1.0

    def _update_buttons(self):
        for label, button in self._buttons.items():
            selected = label == self._current_unit
            button.setChecked(selected)
            button.setStyleSheet(self._highlight_style if selected else self._normal_style)
