# -*- coding: utf-8 -*-
"""Legacy device wrapper and unit-conversion helpers."""

import math
from mpylab.tools.configuration import fstrcmp
from mpylab.tools.aunits import *
from scuq import units
from scuq import si


class Device:
    """
    Was the old OLD Wrapper class to use either py-drivers or DLL-drivers.
    Now, only ErrorNames and convert remains
    """
    _ErrorNames = ("No Error",
                   "Warning",
                   "No Free Instance",
                   "No GPIB Available",
                   "INI-file Token Error",
                   "Initialization Error",
                   "General Driver Error",
                   "No Valid Instance",
                   "Wrong DLL",
                   "Channel Range Error",
                   "General Channel Error",
                   "Warning: Not Switched",
                   "Switch Error",
                   "DAQ Device Error",
                   "No Supported Function",
                   "Frequency Range Error",
                   "COM Port Error",
                   "Warning: Assuming Far Field")
    # Err Codes of the CVI drivers
    _ErrorDict = dict([(2 ** i, n) for i, n in enumerate(_ErrorNames)])
    _Errors = dict([(n, 2 ** i) for i, n in enumerate(_ErrorNames)])
    # del i,n

    def __init__(self, **kw):
        self.instance = None
        self.error = 0
        self.virtual = False
        self.convert = CONVERT()
        self.channel = None

    def GetLastError(self):
        """Return the last stored error bitmask."""
        return self.error

    def GetLastErrorStr(self):
        """Return a pipe-separated string for active error flags."""
        return '|'.join([err for i, err in list(self.__class__._ErrorDict.items()) if ((self.error & 1 << i) != 0)])

class CONVERT:
    """Legacy converter between historic UMD units and scuq units."""

    # (old_unit , scuq_unit , lin_factor(10 or 20) , si_factor)
    units_list = (('UMD_dimensionless', units.ONE, None, 1.),
                  ('UMD_dBm', si.WATT, 10., 1e-3),
                  ('UMD_W', si.WATT, None, 1.),
                  ('UMD_dBuV', si.VOLT, 20., 1e-6),
                  ('UMD_V', si.VOLT, None, 1.),
                  ('UMD_dB', POWERRATIO, 10., 1.),  # example: S-Parameter - Treiber korrigieren
                  ('UMD_Hz', si.HERTZ, None, 1.),
                  ('UMD_kHz', si.HERTZ, None, 1e3),
                  ('UMD_MHz', si.HERTZ, None, 1e6),
                  ('UMD_GHz', si.HERTZ, None, 1e9),
                  ('UMD_Voverm', EFIELD, None, 1.),
                  ('UMD_dBVoverm', EFIELD, 20., 1.),
                  ('UMD_m', si.METER, None, 1.),
                  ('UMD_cm', si.METER, None, 1e-2),
                  ('UMD_mm', si.METER, None, 1e-3),
                  ('UMD_deg', si.RADIAN, None, 180. / math.pi),  # Grad hinzu!!
                  ('UMD_rad', si.RADIAN, None, 1.),
                  ('UMD_steps', units.ONE, None, 1.),
                  ('UMD_dBoverm', EFIELD / si.VOLT, 20., 1.),
                  ('UMD_dBi', POWERRATIO, 10., 1.),
                  ('UMD_dBd', POWERRATIO, 10., 1.64),  # half wave dipole
                  ('UMD_oneoverm', EFIELD / si.VOLT, None, 1),
                  ('UMD_Aoverm', HFIELD, None, 1.),
                  ('UMD_dBAoverm', HFIELD, 20., 1.),
                  ('UMD_Woverm2', POYNTING, None, 1.),
                  ('UMD_dBWoverm2', POYNTING, 10., 1.),
                  ('UMD_Soverm', HFIELD / si.METER, None, 1.),
                  ('UMD_dBSoverm', HFIELD / si.METER, 20., 1.),
                  ('UMD_amplituderatio', AMPLITUDERATIO, None, 1.),
                  ('UMD_powerratio', POWERRATIO, None, 1.),
                  ('UMD_sqrtW', si.WATT.sqrt(), None, 1.),
                  ('UMD_VovermoversqrtW', EFIELD / si.WATT.sqrt(), None, 1.))

    def __init__(self):
        self.udct = dict(((l[0], l[1:]) for l in self.units_list))
        self.cunits = list(self.udct.keys())

        def _ident(x):
            return x

        def _mul(fac):
            def m(x):
                return x * fac

            return m

        self.cmethods = {}
        for cu in self.cunits:
            self.cmethods[cu] = dict.fromkeys(self.cunits, None)  # preset
            self.cmethods[cu][cu] = _ident  # identity
        self.cmethods['UMD_dimensionless']['UMD_steps'] = _ident
        self.cmethods['UMD_steps']['UMD_dimensionless'] = _ident

        self.cmethods['UMD_dBm']['UMD_W'] = self._dB2lin(10, 1e-3)
        self.cmethods['UMD_W']['UMD_dBm'] = self._lin2dB(10, 1000)

        self.cmethods['UMD_dBuV']['UMD_V'] = self._dB2lin(20, 1e-6)
        self.cmethods['UMD_V']['UMD_dBuV'] = self._lin2dB(20, 1e6)

        self.cmethods['UMD_dB']['UMD_powerratio'] = self._dB2lin(10, 1)
        self.cmethods['UMD_powerratio']['UMD_dB'] = self._lin2dB(10, 1)

        self.cmethods['UMD_dB']['UMD_amplituderatio'] = self._dB2lin(20, 1)
        self.cmethods['UMD_amplituderatio']['UMD_dB'] = self._lin2dB(20, 1)

        self.cmethods['UMD_Hz']['UMD_kHz'] = _mul(1e-3)
        self.cmethods['UMD_kHz']['UMD_Hz'] = _mul(1e3)
        self.cmethods['UMD_Hz']['UMD_MHz'] = _mul(1e-6)
        self.cmethods['UMD_MHz']['UMD_Hz'] = _mul(1e6)
        self.cmethods['UMD_Hz']['UMD_GHz'] = _mul(1e-9)
        self.cmethods['UMD_GHz']['UMD_Hz'] = _mul(1e9)
        self.cmethods['UMD_kHz']['UMD_MHz'] = _mul(1e-3)
        self.cmethods['UMD_MHz']['UMD_kHz'] = _mul(1e3)
        self.cmethods['UMD_kHz']['UMD_GHz'] = _mul(1e-6)
        self.cmethods['UMD_GHz']['UMD_kHz'] = _mul(1e6)
        self.cmethods['UMD_MHz']['UMD_GHz'] = _mul(1e-3)
        self.cmethods['UMD_GHz']['UMD_MHz'] = _mul(1e3)

        self.cmethods['UMD_Voverm']['UMD_dBVoverm'] = self._lin2dB(20, 1)
        self.cmethods['UMD_dBVoverm']['UMD_Voverm'] = self._dB2lin(20, 1)

        self.cmethods['UMD_m']['UMD_cm'] = _mul(1e2)
        self.cmethods['UMD_cm']['UMD_m'] = _mul(1e-2)
        self.cmethods['UMD_m']['UMD_mm'] = _mul(1e3)
        self.cmethods['UMD_mm']['UMD_m'] = _mul(1e-3)
        self.cmethods['UMD_cm']['UMD_mm'] = _mul(1e1)
        self.cmethods['UMD_mm']['UMD_cm'] = _mul(1e-1)

        self.cmethods['UMD_deg']['UMD_rad'] = _mul(math.pi / 180.)
        self.cmethods['UMD_rad']['UMD_deg'] = _mul(180. / math.pi)

        self.cmethods['UMD_oneoverm']['UMD_dBVoverm'] = self._lin2dB(20, 1)
        self.cmethods['UMD_dBoverm']['UMD_oneoverm'] = self._dB2lin(20, 1)

        self.cmethods['UMD_dBi']['UMD_dBd'] = (lambda x: x - 2.15)
        self.cmethods['UMD_dBd']['UMD_dBi'] = (lambda x: x + 2.15)
        self.cmethods['UMD_dBi']['UMD_powerratio'] = self._dB2lin(10, 1)
        self.cmethods['UMD_powerratio']['UMD_dBi'] = self._lin2dB(10, 1)
        self.cmethods['UMD_dBi']['UMD_amplituderatio'] = self._dB2lin(20, 1)
        self.cmethods['UMD_amplituderatio']['UMD_dBi'] = self._lin2dB(20, 1)
        self.cmethods['UMD_dBd']['UMD_powerratio'] = self._dB2lin(10, 1.64)
        self.cmethods['UMD_powerratio']['UMD_dBd'] = self._lin2dB(10, 1. / 1.64)
        self.cmethods['UMD_dBd']['UMD_amplituderatio'] = self._dB2lin(20, 1.64 ** 2)
        self.cmethods['UMD_amplituderatio']['UMD_dBd'] = self._lin2dB(20, 1. / 1.64 ** 2)

        self.cmethods['UMD_Aoverm']['UMD_dBAoverm'] = self._lin2dB(20, 1)
        self.cmethods['UMD_dBAoverm']['UMD_Aoverm'] = self._dB2lin(20, 1)

        self.cmethods['UMD_Woverm2']['UMD_dBWoverm2'] = self._lin2dB(10, 1)
        self.cmethods['UMD_dBWoverm2']['UMD_Woverm2'] = self._dB2lin(10, 1)

        self.cmethods['UMD_Soverm']['UMD_dBSoverm'] = self._lin2dB(20, 1)
        self.cmethods['UMD_dBSoverm']['UMD_Soverm'] = self._dB2lin(20, 1)

        self.cmethods['UMD_amplituderatio']['UMD_powerratio'] = (lambda x: x * x)
        self.cmethods['UMD_powerratio']['UMD_amplituderatio'] = (lambda x: math.sqrt(x))

    def c2c(self, fromunit, tounit, data):
        """Convert values from one legacy unit token to another."""
        isSequence = True
        try:
            len(data)
        except TypeError:
            isSequence = False
            data = (data,)

        ret = []
        fuguess = fstrcmp(fromunit, self.cunits, cutoff=0, ignorecase=True)[0]
        tuguess = fstrcmp(tounit, self.cunits, cutoff=0, ignorecase=True)[0]
        # print self.cunits
        # print fromunit, '->', fuguess
        # print tounit, '->', tuguess
        c_meth = self.cmethods[fuguess][tuguess]
        if c_meth is None:
            return None
        for d in data:
            ret.append(c_meth(d))
        if not isSequence:
            ret = ret[0]
        return ret

    def c2scuq(self, Cunit, data):
        """Convert legacy-unit values to scuq-compatible unit/value pairs."""
        isSequence = True
        try:
            len(data)
        except TypeError:
            isSequence = False
            data = (data,)

        ret = []
        try:
            Cunit.lower()
        except AttributeError:
            # print Cunit, type(Cunit)
            Cunit = self.units_list[Cunit][0]
        guess = fstrcmp(Cunit, self.cunits, cutoff=0, ignorecase=True)[0]
        uconf = self.udct[guess]

        for item in data:
            if uconf[1] is not None:  # dB
                try:  # complex
                    # linearize
                    litem = complex(10 ** (item.r / uconf[1]),
                                    10 ** (item.i / uconf[1]))
                except AttributeError:  # real
                    litem = 10 ** (item / uconf[1])
            else:
                litem = item
            ret.append(litem * uconf[2])

        if not isSequence:
            ret = ret[0]
        return ret, uconf[0]

    def scuq2c(self, Sunit, Cunit, data):
        """Convert scuq values back to legacy-unit values."""
        isSequence = True
        try:
            len(data)
        except TypeError:
            isSequence = False
            data = (data,)

        ret = []
        guess = fstrcmp(Cunit, self.cunits, cutoff=0, ignorecase=True)[0]
        pos = self.get_Cunit_int(guess)  # Cunit is an integer
        uconf = self.udct[guess]  # XXX?(bei Berechnung Richtung berücksichtigen)
        if uconf[0] != Sunit:
            return None

        for item in data:
            if uconf[1] is not None:  # Unit => dB (no dB in scuq available)
                if 'r' in dir(item):  # complex
                    # linearize
                    ##                    litem=complex(math.log10(item.r)*uconf[1],
                    ##                                  math.log10(item.i)*uconf[1])
                    litem = complex(uconf[1] * math.log10(item.r / uconf[2]),
                                    uconf[1] * math.log10(item.i / uconf[2]))

                else:  # real
                    ##                    litem=math.log10(item)*uconf[1]
                    litem = uconf[1] * math.log10(item / uconf[2])
            else:
                litem = item / uconf[2]
            ret.append(litem)
        if not isSequence:
            ret = ret[0]
        return ret, pos

    def get_Cunit_int(self, Cunit):
        """Return the index of a legacy unit token in ``units_list``."""
        old_list = [l[0] for l in self.units_list]
        position = old_list.index(Cunit)
        return position

    def _lin2dB(self, dBfac=None, sifac=None):
        """e.g. W2dBm=_lin2dB(10,1000)"""
        if dBfac is None:
            dBfac = 10
        if sifac is None:
            sifac = 1.0

        def m(inp):
            try:
                ret = dBfac * math.log10(inp * sifac)
            except OverflowError as ValueError:
                ret = None
            return ret

        return m

    def _dB2lin(self, dBfac=None, sifac=None):
        """e.g. dBm2W=_dB2lin(10,1e-3)"""
        if dBfac is None:
            dBfac = 10
        if sifac is None:
            sifac = 1.0

        def m(inp):
            return 10 ** (inp / float(dBfac)) * sifac

        return m


class CONVERT:
    """Current converter between compact display units and scuq units."""

    # (unit_name, scuq_unit, lin_factor(10 or 20) or None, si_factor)
    units_list = (
        ('dimensionless', units.ONE, None, 1.0),
        ('dBm', si.WATT, 10.0, 1e-3),
        ('W', si.WATT, None, 1.0),
        ('dBuV', si.VOLT, 20.0, 1e-6),
        ('V', si.VOLT, None, 1.0),
        ('dB', POWERRATIO, 10.0, 1.0),
        ('Hz', si.HERTZ, None, 1.0),
        ('kHz', si.HERTZ, None, 1e3),
        ('MHz', si.HERTZ, None, 1e6),
        ('GHz', si.HERTZ, None, 1e9),
        ('V/m', EFIELD, None, 1.0),
        ('dBV/m', EFIELD, 20.0, 1.0),
        ('m', si.METER, None, 1.0),
        ('cm', si.METER, None, 1e-2),
        ('mm', si.METER, None, 1e-3),
        ('deg', si.RADIAN, None, math.pi / 180.0),
        ('rad', si.RADIAN, None, 1.0),
        ('steps', units.ONE, None, 1.0),
        ('dB/m', EFIELD / si.VOLT, 20.0, 1.0),
        ('dBi', POWERRATIO, 10.0, 1.0),
        ('dBd', POWERRATIO, 10.0, 1.64),   # half wave dipole
        ('1/m', EFIELD / si.VOLT, None, 1.0),
        ('A/m', HFIELD, None, 1.0),
        ('dBA/m', HFIELD, 20.0, 1.0),
        ('W/m2', POYNTING, None, 1.0),
        ('dBW/m2', POYNTING, 10.0, 1.0),
        ('S/m', HFIELD / si.METER, None, 1.0),
        ('dBS/m', HFIELD / si.METER, 20.0, 1.0),
        ('amplituderatio', AMPLITUDERATIO, None, 1.0),
        ('powerratio', POWERRATIO, None, 1.0),
        ('sqrtW', si.WATT.sqrt(), None, 1.0),
        ('V/m/sqrtW', EFIELD / si.WATT.sqrt(), None, 1.0),
    )

    def __init__(self):
        self.udct = {name: (scuq_unit, db_fac, si_fac) for name, scuq_unit, db_fac, si_fac in self.units_list}
        self.cunits = list(self.udct.keys())

        def _ident(x):
            return x

        def _mul(fac):
            def m(x):
                return x * fac
            return m

        self.cmethods = {}
        for cu in self.cunits:
            self.cmethods[cu] = dict.fromkeys(self.cunits, None)
            self.cmethods[cu][cu] = _ident

        self.cmethods['dimensionless']['steps'] = _ident
        self.cmethods['steps']['dimensionless'] = _ident

        self.cmethods['dBm']['W'] = self._dB2lin(10, 1e-3)
        self.cmethods['W']['dBm'] = self._lin2dB(10, 1000)

        self.cmethods['dBuV']['V'] = self._dB2lin(20, 1e-6)
        self.cmethods['V']['dBuV'] = self._lin2dB(20, 1e6)

        self.cmethods['dB']['powerratio'] = self._dB2lin(10, 1)
        self.cmethods['powerratio']['dB'] = self._lin2dB(10, 1)

        self.cmethods['dB']['amplituderatio'] = self._dB2lin(20, 1)
        self.cmethods['amplituderatio']['dB'] = self._lin2dB(20, 1)

        self.cmethods['Hz']['kHz'] = _mul(1e-3)
        self.cmethods['kHz']['Hz'] = _mul(1e3)
        self.cmethods['Hz']['MHz'] = _mul(1e-6)
        self.cmethods['MHz']['Hz'] = _mul(1e6)
        self.cmethods['Hz']['GHz'] = _mul(1e-9)
        self.cmethods['GHz']['Hz'] = _mul(1e9)
        self.cmethods['kHz']['MHz'] = _mul(1e-3)
        self.cmethods['MHz']['kHz'] = _mul(1e3)
        self.cmethods['kHz']['GHz'] = _mul(1e-6)
        self.cmethods['GHz']['kHz'] = _mul(1e6)
        self.cmethods['MHz']['GHz'] = _mul(1e-3)
        self.cmethods['GHz']['MHz'] = _mul(1e3)

        self.cmethods['V/m']['dBV/m'] = self._lin2dB(20, 1)
        self.cmethods['dBV/m']['V/m'] = self._dB2lin(20, 1)

        self.cmethods['m']['cm'] = _mul(1e2)
        self.cmethods['cm']['m'] = _mul(1e-2)
        self.cmethods['m']['mm'] = _mul(1e3)
        self.cmethods['mm']['m'] = _mul(1e-3)
        self.cmethods['cm']['mm'] = _mul(1e1)
        self.cmethods['mm']['cm'] = _mul(1e-1)

        self.cmethods['deg']['rad'] = _mul(math.pi / 180.0)
        self.cmethods['rad']['deg'] = _mul(180.0 / math.pi)

        self.cmethods['1/m']['dB/m'] = self._lin2dB(20, 1)
        self.cmethods['dB/m']['1/m'] = self._dB2lin(20, 1)

        self.cmethods['dBi']['dBd'] = lambda x: x - 2.15
        self.cmethods['dBd']['dBi'] = lambda x: x + 2.15

        self.cmethods['dBi']['powerratio'] = self._dB2lin(10, 1)
        self.cmethods['powerratio']['dBi'] = self._lin2dB(10, 1)
        self.cmethods['dBi']['amplituderatio'] = self._dB2lin(20, 1)
        self.cmethods['amplituderatio']['dBi'] = self._lin2dB(20, 1)

        self.cmethods['dBd']['powerratio'] = self._dB2lin(10, 1.64)
        self.cmethods['powerratio']['dBd'] = self._lin2dB(10, 1.0 / 1.64)
        self.cmethods['dBd']['amplituderatio'] = self._dB2lin(20, 1.64 ** 2)
        self.cmethods['amplituderatio']['dBd'] = self._lin2dB(20, 1.0 / (1.64 ** 2))

        self.cmethods['A/m']['dBA/m'] = self._lin2dB(20, 1)
        self.cmethods['dBA/m']['A/m'] = self._dB2lin(20, 1)

        self.cmethods['W/m2']['dBW/m2'] = self._lin2dB(10, 1)
        self.cmethods['dBW/m2']['W/m2'] = self._dB2lin(10, 1)

        self.cmethods['S/m']['dBS/m'] = self._lin2dB(20, 1)
        self.cmethods['dBS/m']['S/m'] = self._dB2lin(20, 1)

        self.cmethods['amplituderatio']['powerratio'] = lambda x: x * x
        self.cmethods['powerratio']['amplituderatio'] = lambda x: math.sqrt(x)

    def c2c(self, fromunit, tounit, data):
        """Convert values from one unit string to another."""
        is_sequence = True
        try:
            len(data)
        except TypeError:
            is_sequence = False
            data = (data,)

        ret = []
        fuguess = fstrcmp(fromunit, self.cunits, cutoff=0, ignorecase=True)[0]
        tuguess = fstrcmp(tounit, self.cunits, cutoff=0, ignorecase=True)[0]

        c_meth = self.cmethods[fuguess][tuguess]
        if c_meth is None:
            return None

        for d in data:
            ret.append(c_meth(d))

        if not is_sequence:
            return ret[0]
        return ret

    def c2scuq(self, cunit, data):
        """Convert native values into scuq values and return the scuq unit."""
        is_sequence = True
        try:
            len(data)
        except TypeError:
            is_sequence = False
            data = (data,)

        ret = []
        guess = fstrcmp(cunit, self.cunits, cutoff=0, ignorecase=True)[0]
        scuq_unit, db_fac, si_fac = self.udct[guess]

        for item in data:
            if db_fac is not None:
                try:
                    litem = complex(
                        10 ** (item.r / db_fac),
                        10 ** (item.i / db_fac)
                    )
                except AttributeError:
                    litem = 10 ** (item / db_fac)
            else:
                litem = item

            ret.append(litem * si_fac)

        if not is_sequence:
            return ret[0], scuq_unit
        return ret, scuq_unit

    def scuq2c(self, sunit, cunit, data):
        """Convert scuq values back into the requested native unit."""
        is_sequence = True
        try:
            len(data)
        except TypeError:
            is_sequence = False
            data = (data,)

        ret = []
        guess = fstrcmp(cunit, self.cunits, cutoff=0, ignorecase=True)[0]
        scuq_unit, db_fac, si_fac = self.udct[guess]

        if scuq_unit != sunit:
            return None

        for item in data:
            if db_fac is not None:
                if 'r' in dir(item):
                    litem = complex(
                        db_fac * math.log10(item.r / si_fac),
                        db_fac * math.log10(item.i / si_fac)
                    )
                else:
                    litem = db_fac * math.log10(item / si_fac)
            else:
                litem = item / si_fac

            ret.append(litem)

        if not is_sequence:
            return ret[0], guess
        return ret, guess

    def _lin2dB(self, dBfac=None, sifac=None):
        if dBfac is None:
            dBfac = 10
        if sifac is None:
            sifac = 1.0

        def m(inp):
            try:
                return dBfac * math.log10(inp * sifac)
            except OverflowError:
                return None

        return m

    def _dB2lin(self, dBfac=None, sifac=None):
        if dBfac is None:
            dBfac = 10
        if sifac is None:
            sifac = 1.0

        def m(inp):
            return 10 ** (inp / float(dBfac)) * sifac

        return m


if __name__ == '__main__':
    pass
