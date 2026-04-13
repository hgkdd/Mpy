# -*- coding: utf-8 -*-
"""
This is :mod:`mpylab.tools.uconv`.

   Provides unit conversions (for DataFile(Parser); used for dat files)

   :author: Hans Georg Krauthäuser (main author)

   :license: GPLv3 or higher
"""

import math
import scuq.units as units
import scuq.si as si
from mpylab.tools.aunits import EFIELD, HFIELD, POWERRATIO, AMPLITUDERATIO, POYNTING


class UConv:
    uconv = {}

    @staticmethod
    def _ident(v):
        return v

    @staticmethod
    def _dBfac(fac):
        def dB(v):
            return pow(10, v / fac)
        return dB

    @staticmethod
    def _mulfac(method, fac):
        def new_m(v):
            return fac * method(v)
        return new_m

    @classmethod
    def normalize_unit(cls, unit):
        if not isinstance(unit, str):
            raise TypeError("unit must be a string")
        return unit.strip().lower()

    @classmethod
    def get(cls, unit):
        key = cls.normalize_unit(unit)
        try:
            return cls.uconv[key]
        except KeyError as exc:
            raise ValueError(f"Unknown unit: {unit}") from exc

    @classmethod
    def convert(cls, unit, value):
        dim, fn = cls.get(unit)
        return dim, fn(value)

    @classmethod
    def unit_exists(cls, unit):
        key = cls.normalize_unit(unit)
        return key in cls.uconv

    @classmethod
    def available_units(cls):
        return tuple(sorted(cls.uconv.keys()))


UConv.uconv = {
    "1": (units.ONE, UConv._ident),
    "dimensionless": (units.ONE, UConv._ident),

    "dbm": (si.WATT, UConv._mulfac(UConv._dBfac(10), 1e-3)),
    "w": (si.WATT, UConv._ident),

    "dbuv": (si.VOLT, UConv._mulfac(UConv._dBfac(20), 1e-6)),
    "v": (si.VOLT, UConv._ident),

    "db": (POWERRATIO, UConv._dBfac(10)),

    "hz": (si.HERTZ, UConv._ident),
    "khz": (si.HERTZ, UConv._mulfac(UConv._ident, 1e3)),
    "mhz": (si.HERTZ, UConv._mulfac(UConv._ident, 1e6)),
    "ghz": (si.HERTZ, UConv._mulfac(UConv._ident, 1e9)),

    "v/m": (EFIELD, UConv._ident),
    "dbv/m": (EFIELD, UConv._dBfac(20)),

    "m": (si.METER, UConv._ident),
    "cm": (si.METER, UConv._mulfac(UConv._ident, 1e-2)),
    "mm": (si.METER, UConv._mulfac(UConv._ident, 1e-3)),

    "deg": (si.RADIAN, UConv._mulfac(UConv._ident, math.pi / 180.0)),
    "rad": (si.RADIAN, UConv._ident),

    "steps": (units.ONE, UConv._ident),

    "db1/m": (EFIELD / si.VOLT, UConv._dBfac(20)),
    "dbi": (POWERRATIO, UConv._dBfac(10)),
    "dbd": (POWERRATIO, UConv._mulfac(UConv._dBfac(10), 1.64)),  # 1.64: Directivity of a half wave dipole
    "1/m": (EFIELD / si.VOLT, UConv._ident),

    "a/m": (HFIELD, UConv._ident),
    "dba/m": (HFIELD, UConv._dBfac(20)),

    "w/m2": (POYNTING, UConv._ident),
    "dbw/m2": (POYNTING, UConv._dBfac(20)),

    "s/m": (HFIELD / si.VOLT, UConv._ident),
    "dbs/m": (HFIELD / si.VOLT, UConv._dBfac(20)),

    "amplituderatio": (AMPLITUDERATIO, UConv._ident),
    "powerratio": (POWERRATIO, UConv._ident),

    "h": (si.HENRY, UConv._ident),
    "f": (si.FARAD, UConv._ident),
}


if __name__ == "__main__":
    tests = [
        ("dBm", 0),
        ("dbuv", 120),
        ("MHz", 100),
        ("cm", 12.5),
        ("deg", 180),
        ("dbd", 0),
    ]

    for unit, value in tests:
        dim, converted = UConv.convert(unit, value)
        print(f"{value} {unit} -> {converted} [{dim}]")