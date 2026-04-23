# -*- coding: utf-8 -*-
"""Shared display conversion for quantities loaded from INI data files."""

import math

from scuq.ucomponents import Context


INI_UNIT_MODE = "INI/file unit"
SCUQ_UNIT_MODE = "scuq unit"


_DB_UNITS = {
    "db": (10.0, 1.0, "dB"),
    "dbi": (10.0, 1.0, "dBi"),
    "dbd": (10.0, 1.64, "dBd"),
    "dbm": (10.0, 1e-3, "dBm"),
    "dbuv": (20.0, 1e-6, "dBuV"),
    "dbv/m": (20.0, 1.0, "dBV/m"),
    "db1/m": (20.0, 1.0, "dB1/m"),
    "dba/m": (20.0, 1.0, "dBA/m"),
    "dbw/m2": (20.0, 1.0, "dBW/m2"),
    "dbs/m": (20.0, 1.0, "dBS/m"),
}


def data_file_unit(device, what):
    """Return the unit declared in the parsed file block for a data channel."""
    entry = getattr(device, "data", {}).get(what, {})
    datafile = entry.get("datafile") if isinstance(entry, dict) else None
    unit = getattr(datafile, "fromunit", None)
    if unit:
        return str(unit)
    if isinstance(entry, dict) and entry.get("unit"):
        return str(entry["unit"])
    return ""


def quantity_display_values(quantity, *, device=None, what=None, mode=INI_UNIT_MODE, context=None):
    """Return ``(value, uncertainty, unit)`` for UI display.

    The default mode converts logarithmic INI/file units back to their original
    notation, while ``SCUQ_UNIT_MODE`` exposes the raw scuq representation.
    """
    ctx = context or Context()
    value, uncertainty, scuq_unit = ctx.value_uncertainty_unit(quantity)
    if mode == SCUQ_UNIT_MODE:
        return value, uncertainty, str(scuq_unit)

    unit = data_file_unit(device, what) if device is not None and what is not None else ""
    normalized = unit.strip().lower()
    if normalized not in _DB_UNITS:
        return value, uncertainty, str(scuq_unit)

    try:
        value_f = float(abs(value))
        uncertainty_f = abs(float(uncertainty))
    except (TypeError, ValueError):
        return value, uncertainty, str(scuq_unit)

    if value_f <= 0:
        return value, uncertainty, str(scuq_unit)

    factor, reference, display_unit = _DB_UNITS[normalized]
    display_value = factor * math.log10(value_f / reference)
    display_uncertainty = factor / math.log(10.0) * uncertainty_f / value_f
    return display_value, display_uncertainty, display_unit
