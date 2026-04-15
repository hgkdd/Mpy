# -*- coding: utf-8 -*-
from importlib import import_module
import configparser
import os
import math
from functools import cmp_to_key


import numpy
import time
from mpylab.tools.configuration import fstrcmp
from mpylab.tools.aunits import *
import mpylab.tools.umd_types as umd_types
from scuq import ucomponents, quantities
from scuq import units
from scuq import si

try:
    import ctypes as ct
except ImportError:
    ct = None
    pass


def cmp(a, b):
    return (a > b) - (a < b)


def cplx_cmp(a, b):
    # magnituide * sgn(real part)
    try:
        ma = abs(a) * a.real / abs(a.real)
        # ma=a._abs()*a.r/abs(a.r)
    except AttributeError:
        ma = a
    try:
        mb = abs(b) * b.real / abs(b.real)
        # mb=b._abs()*b.r/abs(b.r)
    except AttributeError:
        mb = b
    return cmp(ma, mb)


class Device(object):
    """
    Wrapper class to use either py-drivers or DLL-drivers.
    """
    # Err Strings of the CVI drivers
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

    # common functions of all CVI drivers
    # keys are dll function names
    # values are class attributes
    _postfix = {"init": "Init",
                "Quit": "Quit",
                "setVirtual": "SetVirtual",
                "getVirtual": "GetVirtual",
                "getDescription": "GetDescription"}
    # instrument types
    _types = ("Signalgenerator",
              "Powermeter",
              "Cable",
              "Antenna",
              "NPort",
              "Switch",
              "FieldProbe",
              "Amplifier",
              "Motorcontroller",
              "Tuner",
              "Step2Port",
              "Spectrumanalyzer",
              "Receiver",
              "VLISN",
              "VectorNetworkanalyser")
    _types = tuple([a.lower() for a in _types])
    # del a

    # prefixes of function names used in CVI drivers, e.g. UMD_SG_init, UMD_PM_init, ... 
    _prefix = ("UMD_SG_",
               "UMD_PM_",
               "UMD_CBL_",
               "UMD_ANT_",
               "UMD_NPORT_",
               "UMD_SW_",
               "UMD_PRB_",
               "UMD_AMP_",
               "UMD_MC_",
               "UMD_TUNER_",
               "UMD_S2P_",
               "UMD_SA_",
               "UMD_REC_",
               "UMD_VLISN_"
               "UMD_VNA_")
    # map instrument types to prefixes
    _prefixdict = dict(list(zip(_types, _prefix)))

    # Class names in py-drivers, e.g. SIGNALGENERATOR 
    _pyprefix = ("SIGNALGENERATOR",
                 "POWERMETER",
                 "CABLE",
                 "ANTENNA",
                 "NPORT",
                 "SWITCH",
                 "FIELDPROBE",
                 "AMPLIFIER",
                 "MOTORCONTROLLER",
                 "TUNER",
                 "SWITCHED2PORT",
                 "SPECTRUMANALYZER",
                 "RECEIVER",
                 "VLISN",
                 "VECTORNETWORKANALYZER")
    # map instrument types to prefixes
    _pyprefixdict = dict(list(zip(_types, _pyprefix)))

    def __init__(self, **kw):
        self.kw = kw
        self.instance = None
        self.error = 0
        self.virtual = False
        self.convert = CONVERT()
        self.channel = None

    def cdata_to_obj(self, c_data):
        # @Herbrig: Ich habe die Zeit wieder herausgenommen.
        # Es werden einfach die scuq Objekte zurückgegeben.

        #    tstamp=time.mktime((c_data.t.wYear, c_data.t.wMonth, c_data.t.wDay,
        #                        c_data.t.wHour, c_data.t.wMinute, c_data.t.wSecond,
        #                        c_data.t.wMilliseconds, -1, 1))

        DD = [getattr(c_data, attr) for attr in ('x', 'y', 'z', 'r') if hasattr(c_data, attr)]
        if not len(DD):
            DD = (c_data,)

        values = []
        sigmas = []
        for d in DD:
            triple, scuq_unit = self.convert.c2scuq(c_data.unit, (d.v, d.l, d.u))
            l, v, u = sorted(triple, key=cmp_to_key(cplx_cmp))
            sigma = 0.5 * (u - l)
            values.append(v)
            sigmas.append(sigma)

        if len(DD) == 1:
            values = values[0]
            sigmas = sigmas[0]
        #        print values, sigmas, c_data.v.r, c_data.v.i, c_data.unit
        ui = ucomponents.UncertainInput(values, sigmas)
        obj = quantities.Quantity(scuq_unit, ui)
        return obj

    def obj_to_cdata(self, obj, typ=None):
        if typ is None:
            typ = umd_types.UMD_CMRESULT
        s_unit = obj.__unit__
        try:
            s_value = obj.get_value(s_unit).get_value()
            s_sig = obj.get_value(s_unit).get_uncertainty(obj.get_value(s_unit))
        except AttributeError:
            s_value = obj.get_value(s_unit)
            s_sig = 0.0
        c_unit = None
        for idx, cu in enumerate(self.convert.units_list):
            if cu[1] == s_unit and cu[2] is None:  # got a lin. unit
                c_unit = idx
                break

        cdata = typ()
        v = s_value
        u = s_value + s_sig
        l = s_value - s_sig
        l, v, u = self.convert.scuq2c(s_unit, c_unit, (l, v, u))
        l, v, u = sorted((l, v, u), key=cmp_to_key(cplx_cmp))
        if typ == umd_types.UMD_CMRESULT:
            for attr in ('l', 'v', 'u'):
                try:
                    setattr(getattr(cdata, attr), 'r', locals()[attr].real)
                    setattr(getattr(cdata, attr), 'i', locals()[attr].imag)
                except AttributeError:
                    setattr(getattr(cdata, attr), 'r', locals()[attr])
                    setattr(getattr(cdata, attr), 'i', 0)
        else:
            for attr in ('l', 'v', 'u'):
                setattr(cdata, attr, locals()[attr])
        cdata.unit = c_unit
        Y, M, D, h, m, s, wd, yd, dst = time.localtime()
        tt = umd_types.SYSTEMTIME()
        tt.wYear = Y
        tt.wMonth = M
        tt.wDayOfWeek = wd
        tt.wDay = D
        tt.wHour = h
        tt.wMinute = m
        tt.wSecond = s
        tt.wMilliseconds = 0
        cdata.t = tt
        return cdata

    def Init(self, ini, channel=None):
        if channel is None:
            channel = 1
        self.channel = channel
        tmpfiles = []
        if hasattr(ini, 'read'):  # file like object
            import tempfile
            import configparser
            import io
            from mpylab.tools.util import format_block
            cp = configparser.ConfigParser()
            cp.read_file(ini)
            for section in cp.sections():
                for option, value in cp.items(section):
                    try:
                        theval = eval(value)
                        if hasattr(theval, 'read'):
                            tt = tempfile.NamedTemporaryFile()
                            tmpfiles.append(tt)
                            tt.write(theval.read())
                            tt.flush()
                            cp.set(section, option, tt.name)
                    except:
                        pass
            tmpf = tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", delete=False)
            tmpfiles.append(tmpf)
            cp.write(tmpf)
            tmpf.flush()
            tmpf.close()
            self.ini = tmpf.name
        else:
            try:
                self.ini = os.path.normpath(ini)
                open(self.ini, 'r')  # try to open the file
            except (IOError, AttributeError):
                raise "Unable to open '%s' for read." % self.ini

        # get instrument type and name of DLL from ini-file
        (self.TypeOfInstrument, self.DLLname) = self._getTypeAndDLL(self.ini)
        self.TypeOfInstrument = self.TypeOfInstrument.lower()
        try:
            # fuzzy type matching...
            best_type_guess = fstrcmp(self.TypeOfInstrument,
                                      self.__class__._types,
                                      cutoff=0,
                                      ignorecase=True)[0]
        except IndexError:
            raise 'Instrument type %s from file %s not in list of valid instrument types: %r' % (self.TypeOfInstrument,
                                                                                                 ini,
                                                                                                 self.__class__._types)
        # split extension to see if we have a DLL or a pyd
        (DLLbase, DLLext) = os.path.splitext(self.DLLname)
        DLLbasename = os.path.split(DLLbase)[1]
        DLLext = DLLext.lower()
        # the prefix of the current instrument
        self.prefix = self.__class__._prefixdict[best_type_guess]
        self.pyprefix = self.__class__._pyprefixdict[best_type_guess]
        # depending on the type we use diffent strategies to load the lib
        # print self.DLLname
        if DLLext in ('.dll', '.so'):
            lib = ct.cdll.LoadLibrary(self.DLLname)
        elif DLLext in ('.pyd', '.py', '.pyc', '.pyo'):
            # import importlib
            # print(DLLbasename)
            # print(DLLext)
            #             # print(self.prefix)
            #             # print(self.pyprefix)
            #             # print('GLOBALS:')
            #             # print(globals())
            #             # print('LOCALS:')
            #             # print(locals())
            # mod = __import__('mpylab.device.'+DLLbasename, globals(), locals(), fromlist=[None])
            mod = import_module(f'.{DLLbasename}', 'mpylab.device')
            for i in DLLbasename.split(".")[1:]:  # emulate from ... import ...
                mod = getattr(mod, i)
            try:
                lib = getattr(mod, self.pyprefix)(**self.kw)
            except TypeError:  # keyword argument unknown
                lib = getattr(mod, self.pyprefix)()
            # import DLLbasename as lib
        else:
            raise ValueError("Unknown driver type '%s'." % (DLLext))
        # our lib
        self.library = lib
        # make attributes corresponding to the common methods os all instr. types
        for post, klass in list(Device._postfix.items()):
            try:
                # eg: self._Init = lib -> UMD_SG_init
                setattr(self, "_%s" % klass, getattr(lib, "%s%s" % (self.prefix, post)))
            except AttributeError:
                # second try for pyd: self._Init = lib -> Init
                setattr(self, "_%s" % klass, getattr(lib, "%s" % (klass)))
            if post == 'init':
                # self.__Init -> self._Init_wrap(self._Init)
                # _Init_wrap is a generator function (a function that returns a function)
                # print "__%s -> _%s_warp(_%s)"%(klass, klass, klass)
                setattr(self, "_lib_%s" % klass, getattr(self, "_%s_wrap" % klass)(getattr(self, "_%s" % klass)))
                # print dir(self)
                # print getattr(self, "_%s"%klass)
                # print getattr(self, "_lib_%s"%klass)
            else:
                # self.Quit -> self._Quit_wrap(self._Quit)
                setattr(self, "%s" % klass, getattr(self, "_%s_wrap" % klass)(getattr(self, "_%s" % klass)))
        # call the init method
        # print self._lib_Init
        ret = self._lib_Init(self.ini, channel=channel)
        for tt in tmpfiles:
            tt.close()
        # update self.virtual
        self.GetVirtual()
        return ret

    def _Init_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            # method return for CVI case
            def m(ini=None, channel=None):
                if ini is None:
                    c_ini = ct.c_char_p(self.ini)
                else:
                    c_ini = ct.c_char_p(ini)
                if channel is None:
                    c_channel = ct.c_int(self.channel)
                else:
                    c_channel = ct.c_int(channel)
                c_instance = ct.c_int(0)
                c_error = ct.c_int(0)
                method.restype = ct.c_int
                retval = method(c_ini, c_channel, ct.byref(c_instance), ct.byref(c_error))
                self.instance = c_instance.value
                self.error = c_error.value
                return self.error
        else:
            # method return for py case
            m = method
        return m

    def _Quit_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            def m():
                c_instance = ct.c_int(self.instance)
                c_error = ct.c_int(0)
                method.restype = ct.c_int
                retval = method(c_instance, ct.byref(c_error))
                self.error = c_error.value
                return self.error
        else:
            m = method
        return m

    def _SetVirtual_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            def m(virt):
                c_instance = ct.c_int(self.instance)
                c_virt = ct.c_int(virt)
                c_error = ct.c_int(0)
                method.restype = ct.c_int
                retval = method(c_virt, c_instance, ct.byref(c_error))
                self.error = c_error.value
                if retval == 0:
                    self.virtual = bool(virt)
                return self.error
        else:
            m = method
        return m

    def _GetVirtual_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            def m():
                c_instance = ct.c_int(self.instance)
                c_virt = ct.c_int(0)
                c_error = ct.c_int(0)
                method.restype = ct.c_int
                retval = method(ct.byref(c_virt), c_instance, ct.byref(c_error))
                self.error = c_error.value
                if retval == 0:
                    self.virtual = bool(c_virt.value)
                return self.error, self.virtual
        else:
            m = method
        return m

    def _GetDescription_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            def m():
                c_instance = ct.c_int(self.instance)
                c_buf = ct.create_string_buffer(255)
                c_bufsize = ct.sizeof(c_buf)
                c_error = ct.c_int(0)
                method.restype = ct.c_int
                retval = method(c_buf, c_bufsize, c_instance, ct.byref(c_error))
                self.error = c_error.value
                return self.error, c_buf.value
        else:
            m = method
        return m

    def _getTypeAndDLL(self, ini):
        self.config = configparser.ConfigParser()
        self.config.read(ini)
        self.confsections = self.config.sections()
        sec = fstrcmp('description', self.confsections, cutoff=0, ignorecase=True)[0]
        thetype = self.config.get(sec, "type")
        theDLL = self.config.get(sec, "driver")
        return (thetype, theDLL)

    def GetLastError(self):
        return self.error

    def GetLastErrorStr(self):
        return '|'.join([err for i, err in list(self.__class__._ErrorDict.items()) if ((self.error & 1 << i) != 0)])

    def _addAttributes(self):
        for post, klass in list(self.__class__._postfix.items()):
            ##            print self.__class__._postfix.items()
            ##            print dir(self)
            ##            stop
            # print '1',dir(self)
            # print dir(self.library)
            # print '\n',post, klass#, '\n',dir(self.library),'\n', "%s%s"%(self.prefix,post)
            try:
                setattr(self, "_%s" % klass, getattr(self.library, "%s%s" % (self.prefix, post)))
                ##setattr(self, "_%s"%klass, getattr(self.library, "%s%s"%(self.prefix,klass))) #MH
                # print '2',dir(self)
                # print 'oben:', klass
            except AttributeError:
                # print 'unten:', klass
                setattr(self, "_%s" % klass, getattr(self.library, "%s" % (klass)))
            setattr(self, "%s" % klass, getattr(self, "_%s_wrap" % klass)(getattr(self, "_%s" % klass)))


#################################################################
class NPort(Device):
    def __init__(self, **kw):
        super().__init__(**kw)

Antenna = Cable = NPort

class Amplifier(NPort):
    def __init__(self, **kw):
        super().__init__(**kw)

class Signalgenerator(Device):
    def __init__(self, **kw):
        super().__init__(**kw)

class Powermeter(Device):
    def __init__(self, **kw):
        super().__init__(**kw)

class Spectrumanalyzer(Powermeter):
    def __init__(self, **kw):
        super().__init__(**kw)

class Switch(Device):
    def __init__(self, **kw):
        super().__init__(**kw)

class Fieldprobe(Device):
    def __init__(self, **kw):
        super().__init__(**kw)

class Motorcontroller(Device):
    def __init__(self, **kw):
        super().__init__(**kw)

class Tuner(Device):
    def __init__(self, **kw):
        super().__init__(**kw)

class Step2port(NPort):
    def __init__(self, **kw):
        super().__init__(**kw)

class Vectornetworkanalyser(Device):
    def __init__(self, **kw):
        super().__init__(**kw)


class Receiver(Device):
    def __init__(self, **kw):
        super().__init__(**kw)

class VLISN(Device):
    def __init__(self, **kw):
        super().__init__(**kw)


class CONVERT(object):
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


def cbl_tst(ini):
    if ini is None:
        ini = format_block("""
                         [description]
                         DESCRIPTION = Just a Cable
                         TYPE = CABLE
                         VENDOR = TUD
                         SERIALNR = 
                         DEVICEID = 
                         DRIVER = nport.py

                         [INIT_VALUE]
                         FSTART = 0
                         FSTOP = 8e9
                         FSTEP = 0.0
                         NR_OF_CHANNELS =  1
                         VIRTUAL = 0

                         [CHANNEL_1]
                         NAME = S21
                         UNIT = dB
                         INTERPOLATION = LOG
                         FILE = io.StringIO(format_block('''
                                                                FUNIT: Hz
                                                                UNIT: powerratio
                                                                ABSERROR: [0.1, 1]
                                                                10 [1, 0]
                                                                20 [0.9, 40]
                                                                30 [0.8, 70]
                                                                40 [0.7, 120]
                                                                50 [0.6, 180]
                                                                60 [0.5, 260]
                                                                70 [0.4, 310]
                                                                80 [0.3, 10]
                                                                UNIT: dB
                                                                90 -10
                                            '''))
                         """)
        ini = io.StringIO(ini)

    cbl = Cable()
    err = cbl.Init(ini)
    ctx = scuq.ucomponents.Context()
    for freq in range(10, 100, 10):
        cbl.SetFreq(freq)
        err, uq = cbl.GetData(what='S21')
        val, unc, unit = ctx.value_uncertainty_unit(uq)
        print((freq, uq, abs(val), abs(unc), unit))


if __name__ == '__main__':
    import sys
    import io
    from mpylab.tools.util import format_block
    import scuq

    try:
        ini = sys.argv[1]
    except IndexError:
        ini = None
    cbl_tst(ini)
