Data-Files
-----------

This is the grammar of data files which can be parsed with the :class:`mpy.tools.dataparser.DatFile` class::

   line : FUNIT unit              # frequency unit used from here
        | UNIT unit               # unit used from here
        | UNIT from_unit to_unit  # values are in from_unit and are converted to to_unit
        | RELERROR fp_value       # use relative error fp_value from here
        | ABSERROR value          # use absolute error value from here
        | freq value value value  # value, lower, and upper bound for this freq (triple will be sorted)
        | freq value              # value for this freq (RELERROR or ABSERROR will be used)

   value : fp_value                  # floating point value
         | ( fp_value , fp_value )   # complex: (real part, imaginary part)
         | [ fp_value , fp_value ]   # complex: [magnitude, angle in deg]

Allowed units and unit conversions are taken from al dictionary `uconv` in :class:`mpy.tools.dataparser.UConv`::

    uconv={ "1":    (units.ONE, _ident),
            "dimensionless":    (units.ONE, _ident),
            "dbm":  (si.WATT, _mulfac(_dBfac(10), 1e-3)),
            "w":    (si.WATT, _ident),
            "dbuv": (si.VOLT, _mulfac(_dBfac(20), 1e-6)),
            "v":    (si.VOLT, _ident),
            "db":   (POWERRATIO, _dBfac(10)),
            "hz":   (si.HERTZ, _ident),
            "khz":  (si.HERTZ, _mulfac(_ident,1e3)),
            "mhz":  (si.HERTZ, _mulfac(_ident,1e6)),
            "ghz":  (si.HERTZ, _mulfac(_ident,1e9)),
            "v/m":  (EFIELD, _ident),
            "dbv/m": (EFIELD, _dBfac(20)),
            "m": (si.METER, _ident),
            "cm": (si.METER, _mulfac(_ident,1e-2)),
            "mm": (si.METER, _mulfac(_ident,1e-3)),
            "deg": (si.RADIAN, _mulfac(_ident, math.pi/180.0)),
            "rad": (si.RADIAN, _ident),
            "steps": (units.ONE, _ident), 
            "db1/m": (EFIELD/si.VOLT, _dBfac(20)),
            "dbi": (POWERRATIO, _dBfac(10)),
            "dbd": (POWERRATIO,  _mulfac(_dBfac(10),1.64)),   # 1.64: Directivity of a half wave dipole
            "1/m": (EFIELD/si.VOLT, _ident),
            "a/m": (HFIELD, _ident),
            "dba/m": (HFIELD, _dBfac(20)),
            "w/m2": (POYNTING, _ident),
            "dbw/m2": (POYNTING, _dBfac(20)),
            "s/m": (HFIELD/si.VOLT, _ident),
            "dbs/m": (HFIELD/si.VOLT, _dBfac(20)),
            "amplituderatio": (AMPLITUDERATIO, _ident),
            "powerratio": (POWERRATIO, _ident),
            "h": (si.HENRY,_ident),
            "f": (si.FARAD,_ident)}

