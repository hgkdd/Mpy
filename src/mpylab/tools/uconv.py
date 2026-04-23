"""Unit conversion helpers used by parser and devices.

This module is the canonical conversion backend in mpylab. The public API
supports both directions:

- unit/value -> Quantity (`to_quantity`)
- Quantity -> target unit/value (`from_quantity`)

The mapping is case-insensitive for unit names.
"""

from __future__ import annotations

import math

from numpy import array, log10, ndarray, power
from scuq import si, units
from scuq.quantities import Quantity

from mpylab.tools.aunits import AMPLITUDERATIO, EFIELD, HFIELD, POWERRATIO, POYNTING


def _ident(v):
    """Identity mapping."""
    return v


def _from_dBfac(fac):
    """Convert dB values to linear values with factor `fac`."""

    def lin(db):
        return 10 ** (db / fac)

    return lin


def _to_dBfac(fac):
    """Convert linear values to dB values with factor `fac`."""

    def db(lin):
        return fac * log10(lin)

    return db


def _addsum(method, summand):
    """Compose `method` and add a constant afterwards."""

    def new_m(v):
        return summand + method(v)

    return new_m


def _mulfac(method, fac):
    """Compose `method` and multiply by a constant afterwards."""

    def new_m(v):
        return fac * method(v)

    return new_m


def lin2dB(dBfac=None, sifac=None):
    """Create a converter from linear input to dB output.

    Example:
    `W2dBm = lin2dB(10, 1e3)`
    """
    if dBfac is None:
        dBfac = 10
    if sifac is None:
        sifac = 1.0

    def m(inp):
        if type(inp) in (int, float):
            inp = [inp]
        if not isinstance(inp, ndarray):
            inp = array(inp, dtype=float)
        ans = dBfac * log10(inp * sifac)
        if ans.size == 1:
            return ans[0]
        return ans

    return m


def dB2lin(dBfac=None, sifac=None):
    """Create a converter from dB input to linear output.

    Example:
    `dBm2W = dB2lin(10, 1e-3)`
    """
    if dBfac is None:
        dBfac = 10
    if sifac is None:
        sifac = 1.0

    def m(inp):
        if type(inp) in (int, float):
            inp = [inp]
        if not isinstance(inp, ndarray):
            inp = array(inp, dtype=float)
        ans = power(10.0, inp / float(dBfac)) * sifac
        if ans.size == 1:
            return ans[0]
        return ans

    return m


class UConv:
    """Central registry for unit conversion methods.

    `uconv` maps input unit strings to tuples `(target_scuq_unit, converter)`.
    `uconv_from_quantity` maps scuq unit-string representation to outbound
    converters keyed by destination unit string.
    """

    uconv = {}
    uconv_from_quantity = {}

    @classmethod
    def normalize_unit(cls, unit):
        """Normalize a unit name to its dictionary key representation."""
        if not isinstance(unit, str):
            raise TypeError("unit must be a string")
        return unit.strip().lower()

    @classmethod
    def get(cls, unit):
        """Return `(scuq_unit, converter)` for input unit string."""
        key = cls.normalize_unit(unit)
        try:
            return cls.uconv[key]
        except KeyError as exc:
            raise ValueError(f"Unknown unit: {unit}") from exc

    @classmethod
    def convert(cls, unit, value):
        """Convert a numeric value from `unit` to canonical scuq base."""
        dim, fn = cls.get(unit)
        return dim, fn(value)

    @classmethod
    def to_quantity(cls, fromunit, value):
        """Create a scuq `Quantity` from unit string and value."""
        dim, converted = cls.convert(fromunit, value)
        return Quantity(dim, converted)

    @classmethod
    def _quantity_unit_key(cls, obj):
        """Return the normalized unit key used by reverse mapping."""
        try:
            unit = obj._unit
        except AttributeError as exc:
            raise TypeError("obj must be a scuq Quantity-like object with '_unit'") from exc
        return str(unit)

    @classmethod
    def from_quantity(cls, tounit, obj):
        """Convert a scuq `Quantity` to a float in destination unit `tounit`."""
        tounit_norm = cls.normalize_unit(tounit)
        unit_key = cls._quantity_unit_key(obj)
        try:
            unit_map = cls.uconv_from_quantity[unit_key]
        except KeyError as exc:
            raise ValueError(f"No outbound conversion mapping for quantity unit: {unit_key}") from exc
        try:
            method = unit_map[tounit_norm]
        except KeyError as exc:
            raise ValueError(f"Cannot convert quantity unit '{unit_key}' to '{tounit}'") from exc
        value = obj.get_expectation_value_as_float()
        return method(value)

    @classmethod
    def unit_exists(cls, unit):
        """Return `True` if the input unit is known."""
        key = cls.normalize_unit(unit)
        return key in cls.uconv

    @classmethod
    def available_units(cls):
        """Return all supported input units."""
        return tuple(sorted(cls.uconv.keys()))

    @classmethod
    def available_output_units(cls, obj):
        """Return outbound unit strings available for a Quantity object."""
        unit_key = cls._quantity_unit_key(obj)
        return tuple(sorted(cls.uconv_from_quantity.get(unit_key, {}).keys()))


UConv.uconv = {
    "1": (units.ONE, _ident),
    "dimensionless": (units.ONE, _ident),
    "dbm": (si.WATT, _mulfac(_from_dBfac(10), 1e-3)),
    "w": (si.WATT, _ident),
    "dbuv": (si.VOLT, _mulfac(_from_dBfac(20), 1e-6)),
    "v": (si.VOLT, _ident),
    "db": (POWERRATIO, _from_dBfac(10)),
    "hz": (si.HERTZ, _ident),
    "khz": (si.HERTZ, _mulfac(_ident, 1e3)),
    "mhz": (si.HERTZ, _mulfac(_ident, 1e6)),
    "ghz": (si.HERTZ, _mulfac(_ident, 1e9)),
    "v/m": (EFIELD, _ident),
    "dbv/m": (EFIELD, _from_dBfac(20)),
    "m": (si.METER, _ident),
    "cm": (si.METER, _mulfac(_ident, 1e-2)),
    "mm": (si.METER, _mulfac(_ident, 1e-3)),
    "deg": (si.RADIAN, _mulfac(_ident, math.pi / 180.0)),
    "rad": (si.RADIAN, _ident),
    "steps": (units.ONE, _ident),
    "db1/m": (EFIELD / si.VOLT, _from_dBfac(20)),
    "dbi": (POWERRATIO, _from_dBfac(10)),
    "dbd": (POWERRATIO, _mulfac(_from_dBfac(10), 1.64)),
    "1/m": (EFIELD / si.VOLT, _ident),
    "a/m": (HFIELD, _ident),
    "dba/m": (HFIELD, _from_dBfac(20)),
    "w/m2": (POYNTING, _ident),
    "dbw/m2": (POYNTING, _from_dBfac(20)),
    "s/m": (HFIELD / si.VOLT, _ident),
    "dbs/m": (HFIELD / si.VOLT, _from_dBfac(20)),
    "amplituderatio": (AMPLITUDERATIO, _ident),
    "powerratio": (POWERRATIO, _ident),
    "h": (si.HENRY, _ident),
    "f": (si.FARAD, _ident),
}

UConv.uconv_from_quantity = {
    "1": {"1": _ident, "dimensionless": _ident, "steps": _ident},
    "W": {"dbm": _addsum(_to_dBfac(10), 30), "w": _ident},
    "V": {"dbuv": _addsum(_to_dBfac(20), 120), "v": _ident},
    "(W/W)": {
        "db": _to_dBfac(10),
        "dbi": _to_dBfac(10),
        "dbd": _addsum(_to_dBfac(10), -2.15),
        "powerratio": _ident,
        "powerration": _ident,
    },
    "Hz": {"hz": _ident, "khz": _mulfac(_ident, 1e-3), "mhz": _mulfac(_ident, 1e-6), "ghz": _mulfac(_ident, 1e-9)},
    "V/m": {"v/m": _ident, "dbv/m": _to_dBfac(20)},
    "m": {"m": _ident, "cm": _mulfac(_ident, 1e2), "mm": _mulfac(_ident, 1e3)},
    "rad": {"rad": _ident, "deg": _mulfac(_ident, 180.0 / math.pi)},
    "m^(-1)": {"db1/m": _to_dBfac(20), "1/m": _ident},
    "(V/V)": {"amplituderatio": _ident},
    "H": {"h": _ident},
    "F": {"f": _ident},
    "A*m^(-1)": {"a/m": _ident, "dba/m": _to_dBfac(20)},
    "W*m^(-2)": {"w/m2": _ident, "dbw/m2": _to_dBfac(20)},
    "A*m^(-1)*V^(-1)": {"s/m": _ident, "a/m": _ident, "dbs/m": _to_dBfac(20)},
}


def to_quantity(fromunit, value):
    """Backward-compatible convenience wrapper around `UConv.to_quantity`."""
    return UConv.to_quantity(fromunit, value)


def from_quantity(tounit, obj):
    """Backward-compatible convenience wrapper around `UConv.from_quantity`."""
    return UConv.from_quantity(tounit, obj)


W2dBm = lin2dB(10, 1e3)
dBm2W = dB2lin(10, 1e-3)
mW2dBm = lin2dB(10, 1)
dBm2mW = dB2lin(10, 1)
V2dBuV = lin2dB(20, 1e6)
dBuV2V = dB2lin(20, 1e-6)
uV2dBuV = lin2dB(20, 1)
dBuV2uV = dB2lin(20, 1)


if __name__ == "__main__":
    import math as _math

    def _assert_close(name, actual, expected, tol=1e-12):
        if abs(actual - expected) > tol:
            raise AssertionError(f"{name}: expected {expected}, got {actual}")

    print("Running uconv self-test...")

    # 1) Forward conversion and case-insensitivity.
    dim, w0 = UConv.convert("dBm", 0.0)
    _assert_close("0 dBm -> W", w0, 1e-3)
    print(f"OK: 0 dBm -> {w0} [{dim}]")

    # 2) Quantity creation and reverse conversion.
    q_f = UConv.to_quantity("MHz", 123.456)
    hz_val = UConv.from_quantity("Hz", q_f)
    mhz_val = UConv.from_quantity("mhz", q_f)
    _assert_close("MHz roundtrip", mhz_val, 123.456, tol=1e-9)
    _assert_close("MHz to Hz", hz_val, 123.456e6, tol=1e-3)
    print("OK: Quantity roundtrip for frequency units")

    # 3) Angle conversion.
    q_a = UConv.to_quantity("deg", 180.0)
    rad_val = UConv.from_quantity("rad", q_a)
    _assert_close("180 deg -> rad", rad_val, _math.pi)
    print("OK: Angle conversions")

    # 4) Vector/scalar helper compatibility.
    _assert_close("W2dBm(1e-3)", W2dBm(1e-3), 0.0)
    _assert_close("dBm2W(0)", dBm2W(0.0), 1e-3)
    vec = dBm2W([0, 10, 20])
    if tuple(vec.shape) != (3,):
        raise AssertionError(f"Unexpected vector shape: {vec.shape}")
    print("OK: lin2dB/dB2lin scalar and vector paths")

    # 5) Error-path checks.
    try:
        UConv.get("this_unit_does_not_exist")
        raise AssertionError("Expected ValueError for unknown unit")
    except ValueError:
        pass
    try:
        UConv.from_quantity("dbm", 1.234)
        raise AssertionError("Expected TypeError for invalid quantity object")
    except TypeError:
        pass
    print("OK: Error-path checks")

    print("uconv self-test passed.")
