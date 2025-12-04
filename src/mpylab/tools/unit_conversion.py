from numpy import log10, power, array, ndarray, pi

from scuq import si
from scuq import units
from scuq.quantities import Quantity
from mpylab.tools.aunits import *

def _ident(v):
    return v

def _from_dBfac(fac):
    def lin(db):
        return 10**(db/fac)
    return lin

def _to_dBfac(fac):
    def db(lin):
        return fac * log10(lin)
    return db

def _addsum(method, sum):
    def new_m(v):
        return sum + method(v)
    return new_m

def _mulfac(method, fac):
    def new_m(v):
        return fac*method(v)
    return new_m

# keys: from unit
uconv_to_quantity = { "1":    (units.ONE, _ident),
                    "dimensionless":    (units.ONE, _ident),
                    "dbm":  (si.WATT, _mulfac(_from_dBfac(10), 1e-3)),
                    "w":    (si.WATT, _ident),
                    "dbuv": (si.VOLT, _mulfac(_from_dBfac(20), 1e-6)),
                    "v":    (si.VOLT, _ident),
                    "db":   (POWERRATIO, _from_dBfac(10)),
                    "hz":   (si.HERTZ, _ident),
                    "khz":  (si.HERTZ, _mulfac(_ident, 1e3)),
                    "mhz":  (si.HERTZ, _mulfac(_ident, 1e6)),
                    "ghz":  (si.HERTZ, _mulfac(_ident, 1e9)),
                    "v/m":  (EFIELD, _ident),
                    "dbv/m": (EFIELD, _from_dBfac(20)),
                    "m": (si.METER, _ident),
                    "cm": (si.METER, _mulfac(_ident, 1e-2)),
                    "mm": (si.METER, _mulfac(_ident, 1e-3)),
                    "deg": (si.RADIAN, _mulfac(_ident, pi/180.0)),
                    "rad": (si.RADIAN, _ident),
                    "steps": (units.ONE, _ident),
                    "db1/m": (EFIELD/si.VOLT, _from_dBfac(20)),
                    "dbi": (POWERRATIO, _from_dBfac(10)),
                    "dbd": (POWERRATIO,  _mulfac(_from_dBfac(10), 1.64)),   # 1.64: Directivity of a half wave dipole
                    "1/m": (EFIELD/si.VOLT, _ident),
                    "a/m": (HFIELD, _ident),
                    "dba/m": (HFIELD, _from_dBfac(20)),
                    "w/m2": (POYNTING, _ident),
                    "dbw/m2": (POYNTING, _from_dBfac(20)),
                    "s/m": (HFIELD/si.VOLT, _ident),
                    "dbs/m": (HFIELD/si.VOLT, _from_dBfac(20)),
                    "amplituderatio": (AMPLITUDERATIO, _ident),
                    "powerratio": (POWERRATIO, _ident),
                    "h": (si.HENRY, _ident),
                    "f": (si.FARAD, _ident)}

# dict of dict: first keys from units (str representation on scuq unit);
uconv_from_quantity = { "1":  {"1": _ident,
                               "dimensionless": _ident,
                               'steps': _ident},
                    "W":  {"dbm": _addsum(_to_dBfac(10), 30),
                           "w": _ident},
                    "V": {"dbuv": _addsum(_to_dBfac(20), 120),
                          "v":  _ident},
                    "(W/W)": {'db': _to_dBfac(10),
                            'dbi': _to_dBfac(10),
                            'dbd': _addsum(_to_dBfac(10), -2.15),  # überprüfen
                            'powerration': _ident},
                    "Hz": {'hz': _ident,
                           'khz': _mulfac(_ident, 1e-3),
                           'mhz': _mulfac(_ident, 1e-6),
                           'ghz': _mulfac(_ident, 1e-9)},
                    "V/m": {'v/m': _ident,
                            'dbv/m': _to_dBfac(20)},
                    "m": {'m': _ident,
                          'cm': _mulfac(_ident, 1e2),
                          'mm': _mulfac(_ident, 1e3)},
                    "rad": {'rad': _ident,
                            'deg': _mulfac(_ident, 180.0/pi)},
                    "m^(-1)": {'db1/m': _to_dBfac(20),
                               '1/m': _ident},
                    '(V/V)': {'amplituderatio': _ident},
                    "H": {'h': _ident},
                    "F": {'f': _ident},
                    "A*m^(-1)": {"a/m": _ident,
                                 "dba/m": _to_dBfac(20)},
                    "W*m^(-2)": {'w/m2': _ident,
                                 "dbw/m2": _to_dBfac(20)},
                    "A*m^(-1)*V^(-1)": {"a/m": _ident,
                                        "dbs/m": _to_dBfac(20)}
                        }


def to_quantity(fromunit, value):
    """
    Create a scuq quantity from a unit and a value (with conversion from dB)

    :param fromunit: str
    :param value: float
    :return: scuq quantity
    """
    scuq_unit, converter = uconv_to_quantity[fromunit.lower()]
    obj = Quantity(scuq_unit, converter(value))
    return obj

def from_quantity(tounit, obj):
    """
    Create a float from a scuq quantity (with conversion to dB)

    :param tounit: str; destination unit
    :param obj: scuq quantity
    :return: float
    """
    obj_unit_str = str(obj._unit)
    value = obj.get_expectation_value_as_float()
    method = uconv_from_quantity[obj_unit_str][tounit.lower()]
    return method(value)


def lin2dB(dBfac=None, sifac=None):
    """
    e.g. W2dBm = lin2dB(10,1000)
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
        else:
            return ans

    return m


def dB2lin(dBfac=None, sifac=None):
    """
    e.g. dBm2W = dB2lin(10,1e-3)
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
        ans = power(inp / float(dBfac), 10) * sifac
        if ans.size == 1:
            return ans[0]
        else:
            return ans

    return m

W2dBm = lin2dB(10, 1e3)
dBm2W = dB2lin(10,1e-3)

mW2dBm = lin2dB(10, 1)
dBm2mW = dB2lin(10,1)

V2dBuV = lin2dB(20,1e6)
dBuV2V = dB2lin(20,1e-6)

uV2dBuV = lin2dB(20,1)
dBuV2uV = dB2lin(20,1)

if __name__ == '__main__':
    val_Watt = 1e-3
    list_Watt = [-1, 1, 1e-3, 1e-4, 1e-5, 1e-6, 1e-7, 1e-8, 1e-9]

    print(W2dBm(val_Watt))
    print(W2dBm(list_Watt))

    u = Quantity(VOLT, 1e-6)
    print(f"Quantity: {u}")

    for val in range(-60, 60, 10):
        for unit in ('dBm', 'dBuV', 'dBV/m'):
            print(f"to_quantity: {val} {unit} -> {to_quantity(unit, val)}")

    unit = 'dBuV'
    print(f"from_quantity: {u} -> {from_quantity(unit, u)} {unit}")

