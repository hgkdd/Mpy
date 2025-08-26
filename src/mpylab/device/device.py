# -*- coding: utf-8 -*-
from importlib import import_module
import configparser
import os
import math
from functools import cmp_to_key

import numpy
import time
from mpylab.tools.Configuration import fstrcmp
from mpylab.tools.aunits import *
import mpylab.tools.umd_types as umd_types
from scuq import ucomponents, quantities

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

    def Init(self, ininame, channel=None):
        if channel is None:
            channel = 1
        self.channel = channel
        tmpfiles = []
        if hasattr(ininame, 'read'):  # file like object
            import tempfile
            import configparser
            import io
            from mpylab.tools.util import format_block
            cp = configparser.ConfigParser()
            cp.read_file(ininame)
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
            tmpf = tempfile.NamedTemporaryFile()
            tmpfiles.append(tmpf)
            cp.write(tmpf)
            tmpf.flush()
            self.ininame = tmpf.name
        else:
            try:
                self.ininame = os.path.normpath(ininame)
                open(self.ininame, 'r')  # try to open the file
            except (IOError, AttributeError):
                raise "Unable to open '%s' for read." % self.ininame

        # get instrument type and name of DLL from ini-file
        (self.TypeOfInstrument, self.DLLname) = self._getTypeAndDLL(self.ininame)
        self.TypeOfInstrument = self.TypeOfInstrument.lower()
        try:
            # fuzzy type matching...
            best_type_guess = fstrcmp(self.TypeOfInstrument,
                                      self.__class__._types,
                                      n=1,
                                      cutoff=0,
                                      ignorecase=True)[0]
        except IndexError:
            raise 'Instrument type %s from file %s not in list of valid instrument types: %r' % (self.TypeOfInstrument,
                                                                                                 ininame,
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
            mod = __import__('mpylab.device.'+DLLbasename, globals(), locals(), fromlist=[None])
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
        ret = self._lib_Init(self.ininame, channel=channel)
        for tt in tmpfiles:
            tt.close()
        # update self.virtual
        self.GetVirtual()
        return ret

    def _Init_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            # method return for CVI case
            def m(ininame=None, channel=None):
                if ininame is None:
                    c_ininame = ct.c_char_p(self.ininame)
                else:
                    c_ininame = ct.c_char_p(ininame)
                if channel is None:
                    c_channel = ct.c_int(self.channel)
                else:
                    c_channel = ct.c_int(channel)
                c_instance = ct.c_int(0)
                c_error = ct.c_int(0)
                method.restype = ct.c_int
                retval = method(c_ininame, c_channel, ct.byref(c_instance), ct.byref(c_error))
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

    def _getTypeAndDLL(self, ininame):
        self.config = configparser.ConfigParser()
        self.config.read(ininame)
        self.confsections = self.config.sections()
        sec = fstrcmp('description', self.confsections, n=1, cutoff=0, ignorecase=True)[0]
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
    # additional functions for this instrument type
    _postfix = {"setFreq": "SetFreq",
                "getData": "GetData"}

    def __init__(self, **kw):
        # call parent init
        Device.__init__(self, **kw)

    def Init(self, ininame, channel=None):
        if channel is None:
            channel = 1
        # load DLL or pyd (etc), register wrappers for common methods
        ret = Device.Init(self, ininame, channel)

        # register additional wrappers
        self._addAttributes()
        return ret

    def _SetFreq_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            def m(freq):
                c_instance = ct.c_int(self.instance)
                c_freq = ct.c_double(freq)
                c_error = ct.c_int(0)
                method.restype = ct.c_double
                retval = method(c_freq, c_instance, ct.byref(c_error))
                self.error = c_error.value
                return self.error, retval
        else:
            m = method
        return m

    def _GetData_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            def m(what):
                c_instance = ct.c_int(self.instance)
                c_error = ct.c_int(0)
                c_data = umd_types.UMD_DCMRESULT()
                c_what = ct.c_char_p(what)
                method.restype = ct.c_int
                retval = method(ct.byref(c_data), c_what, c_instance, ct.byref(c_error))
                self.error = c_error.value
                if not self.error:
                    obj = self.cdata_to_obj(c_data)

                else:
                    obj = None

                return self.error, obj
        else:
            m = method
        return m


Antenna = Cable = NPort


#################################################################
class Amplifier(NPort):
    # additional functions for this instrument type
    _postfix = {"setState": "SetState"}

    def __init__(self, **kw):
        # call parent init
        NPort.__init__(self, **kw)
        Amplifier._postfix.update(NPort._postfix)
        # print Amplifier._postfix
        # print NPort._postfix

    def Init(self, ininame, channel=None):
        # load DLL or pyd (etc), register wrappers for common methods
        ret = NPort.Init(self, ininame, channel)

        # register additional wrappers
        self._addAttributes()
        return ret

    def _SetState_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            def m(what):
                MODES = ['POFF', 'PON', 'STANDBY', 'OPERATE']
                whatguess = fstrcmp(what, MODES, n=1, cutoff=0, ignorecase=True)[0]
                c_instance = ct.c_int(self.instance)
                c_what = ct.c_int(MODES.index(whatguess))
                c_error = ct.c_int(0)
                method.restype = ct.c_int
                retval = method(c_what, c_instance, ct.byref(c_error))
                self.error = c_error.value
                return self.error, retval
        else:
            m = method
        return m

    def POn(self):
        return self.SetState('PON')

    def POff(self):
        return self.SetState('POff')

    def Operate(self):
        return self.SetState('OPERATE')

    def Standby(self):
        return self.SetState('STANDBY')


#################################################################
class Signalgenerator(Device):
    _postfix = {"setRFFreq": "SetFreq",
                "setRFLevel": "SetLevel",
                "setRFstate": "SetState",
                "ConfAM": "ConfAM",
                "ConfPM": "ConfPM",
                "AM": "SetAM",
                "PM": "SetPM"}

    def __init__(self, **kw):
        # call parent init
        Device.__init__(self, **kw)
        self.Z = quantities.Quantity(si.OHM, 50)
        self.levelunit = None

    def Init(self, ininame, channel=None):
        if channel == None:
            channel = 1

        ret = Device.Init(self, ininame, channel)
        sec = fstrcmp('CHANNEL_%d' % channel, self.confsections, n=1, cutoff=0, ignorecase=True)[0]
        self.levelunit = self.config.get(sec, 'unit')

        # register additional wrappers
        self._addAttributes()
        return ret

    def _SetFreq_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            def m(freq):
                c_instance = ct.c_int(self.instance)
                c_freq = ct.c_double(freq)
                c_error = ct.c_int(0)
                method.restype = ct.c_double
                retval = method(c_freq, c_instance, ct.byref(c_error))
                self.error = c_error.value
                return self.error, retval
        else:
            m = method
        return m

    def _SetLevel_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            # accept SCUQ quantity for the level
            def m(level):
                # the unit of level is given in the ini file for dll drivers
                # -> convert to correct unit here
                lv, unit = self.convert.scuq2c(level.__unit__, self.levelunit, level.__value__)
                c_level = ct.c_double(lv)
                c_instance = ct.c_int(self.instance)
                c_error = ct.c_int(0)
                method.restype = ct.c_double
                retval = method(c_level, c_instance, ct.byref(c_error))
                self.error = c_error.value
                return self.error, retval
        else:
            m = method
        return m

    def _SetState_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            def m(state):
                MODES = ['OFF', 'ON']
                guess = fstrcmp(state, MODES, n=1, cutoff=0, ignorecase=True)[0]
                try:
                    c_state = ct.c_int(MODES.index(guess))  # off->0, On->1
                except ValueError:
                    # be save
                    c_state = ct.c_int(0)
                    self.error = self._Errors['Warning']
                c_instance = ct.c_int(self.instance)
                c_error = ct.c_int(0)
                method.restype = ct.c_int
                retval = method(c_state, c_instance, ct.byref(c_error))
                self.error |= c_error.value
                return self.error, retval
        else:
            m = method
        return m

    def _ConfAM_wrap(self, method):  # XXX TODO: Anpassen; wie ConfPM
        if isinstance(method, ct._CFuncPtr):
            def m(source, freq, depth, waveform, LFOut):
                pars = ((source, ('INT1', 'INT2', 'EXT1', 'EXT2', 'EXT_AC', 'EXT_DC',
                                  'TWOTONE_AC', 'TWOTONE_DC', 'OFF'), ct.c_int),
                        (waveform, ('SINE', 'SQUARE', 'TRIANGLE',
                                    'NOISE', 'SAWTOOTH'), ct.c_int),
                        (LFOut, ('OFF', 'ON'), ct.c_int))
                for (par, MD, tp) in pars:
                    guess = fstrcmp(par, MD, n=1, cutoff=0, ignorecase=True)[0]
                    globals()['c_%s' % par] = eval('%s(MD.index(guess))' % (tp))
                c_freq = ct.c_double(freq)
                c_depth = ct.c_int(depth)  # in %
                c_error = ct.c_int(0)
                method.restype = ct.c_int
                c_instance = ct.c_int(self.instance)
                retval = method(c_source, c_freq, c_depth, c_waveform, c_LFOut, c_instance, ct.byref(c_error))
                self.error = c_error.value
                return self.error, retval
        else:
            m = method
        return m

    def _ConfPM_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            def m(source, freq, pol, width, delay):
                pars = (('source', source, ['INT', 'EXT1', 'EXT2', 'OFF'], 'ct.c_int'),
                        ('pol', pol, ['NORMAL', 'INVERTED'], 'ct.c_int'))
                for (name, par, MD, tp) in pars:
                    guess = fstrcmp(par, MD, n=1, cutoff=0, ignorecase=True)[0]
                    ##print MD.index(guess),'%s(MD.index(guess))'%tp
                    globals()['c_%s' % name] = eval('%s(MD.index(guess))' % tp)
                    ##print 'wert:',globals()['c_%s'%par]
                c_freq = ct.c_double(freq)
                c_width = ct.c_double(width)
                c_delay = ct.c_double(delay)
                c_instance = ct.c_int(self.instance)
                c_error = ct.c_int(0)
                method.restype = ct.c_int
                retval = method(c_source, c_freq, c_pol, c_width, c_delay, c_instance, ct.byref(c_error))
                self.error = c_error.value
                return self.error, retval
        else:
            m = method
        return m

    def _SetAM_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            def m(state):
                MODES = ['OFF', 'ON']
                guess = fstrcmp(state, MODES, n=1, cutoff=0, ignorecase=True)[0]
                try:
                    c_state = ct.c_int(MODES.index(guess))  # off->0, On->1
                except ValueError:
                    # be save
                    c_state = ct.c_int(0)
                    self.error = self._Errors['Warning']
                c_instance = ct.c_int(self.instance)
                c_error = ct.c_int(0)
                method.restype = ct.c_int
                retval = method(c_state, c_instance, ct.byref(c_error))
                self.error = c_error.value
                return self.error, retval
        else:
            m = method
        return m

    def _SetPM_wrap(self, method):  # nur PM(1)
        if isinstance(method, ct._CFuncPtr):
            def m(state):
                MODES = ['OFF', 'ON']
                guess = fstrcmp(state, MODES, n=1, cutoff=0, ignorecase=True)[0]
                try:
                    c_state = ct.c_int(MODES.index(guess))  # off->0, On->1
                except ValueError:
                    # be save
                    c_state = ct.c_int(0)
                    self.error = self._Errors['Warning']
                c_instance = ct.c_int(self.instance)
                c_error = ct.c_int(0)
                method.restype = ct.c_int
                retval = method(c_state, c_instance, ct.byref(c_error))
                self.error = c_error.value
                return self.error, retval
        else:
            m = method
        return m

    def RFOn(self):
        return self.SetState('ON')

    def RFOff(self):
        return self.SetState('OFF')

    def AMOn(self):
        return self.SetAM('ON')

    def AMOff(self):
        return self.SetAM('OFF')

    def PMOn(self):
        return self.SetPM('ON')

    def PMOff(self):
        return self.SetPM('OFF')


#################################################################
class Powermeter(Device):
    _postfix = {"Zero": "Zero",
                "setFreq": "SetFreq",
                "getDataNB": "GetDataNB",
                "getData": "GetData",
                "Trigger": "Trigger"}

    def __init__(self, **kw):
        Device.__init__(self, **kw)

    def Init(self, ininame, channel=None):
        if channel is None:
            channel = 1
        ret = Device.Init(self, ininame, channel)
        # register additional wrappers
        self._addAttributes()
        return ret

    def _SetFreq_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            def m(freq):
                c_instance = ct.c_int(self.instance)
                c_freq = ct.c_double(freq)
                c_error = ct.c_int(0)
                method.restype = ct.c_double
                retval = method(c_freq, c_instance, ct.byref(c_error))
                self.error = c_error.value
                return self.error, retval
        else:
            m = method
        return m

    def _Zero_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            def m(state=None):
                if state is None:
                    state = 'On'
                MODES = ['OFF', 'ON']
                guess = fstrcmp(state, MODES, n=1, cutoff=0, ignorecase=True)[0]
                try:
                    c_state = ct.c_int(MODES.index(guess))  # off->0, On->1
                except ValueError:
                    # safe: do Zero
                    c_state = ct.c_int(1)
                    self.error = self._Errors['Warning']
                c_instance = ct.c_int(self.instance)
                c_error = ct.c_int(0)
                method.restype = ct.c_int
                retval = method(c_state, c_instance, ct.byref(c_error))
                self.error = c_error.value
                return self.error, retval
        else:
            def m(state=None):
                if state is None:
                    state = 'On'
                return method(state)
        return m

    def _GetDataNB_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            def m(retrigger=None):
                if retrigger is None:
                    retrigger = 'Off'
                MODES = ['OFF', 'ON']
                guess = fstrcmp(retrigger, MODES, n=1, cutoff=0, ignorecase=True)[0]
                try:
                    c_retrigger = ct.c_int(MODES.index(guess))  # off->0, On->1
                except ValueError:
                    # save: do not retrigger
                    c_retrigger = ct.c_int(0)
                    self.error = self._Errors['Warning']
                c_instance = ct.c_int(self.instance)
                c_error = ct.c_int(0)
                c_data = umd_types.UMD_DCMRESULT()
                method.restype = ct.c_int
                retval = method(ct.byref(c_data), c_retrigger, c_instance, ct.byref(c_error))
                self.error = c_error.value
                if not self.error and retval == 0:
                    obj = self.cdata_to_obj(c_data)
                else:
                    obj = None
                return self.error, obj
        else:
            def m(retrigger=None):
                if retrigger is None:
                    retrigger = 'Off'
                return method(retrigger)
        return m

    def _GetData_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            def m():
                c_instance = ct.c_int(self.instance)
                c_error = ct.c_int(0)
                c_data = umd_types.UMD_DMRESULT()
                method.restype = ct.c_int
                retval = method(ct.byref(c_data), c_instance, ct.byref(c_error))
                self.error = c_error.value
                if not self.error and retval == 0:
                    obj = self.cdata_to_obj(c_data)
                else:
                    obj = None
                return self.error, obj
        else:
            m = method
        return m

    def _Trigger_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            def m():
                c_instance = ct.c_int(self.instance)
                c_error = ct.c_int(0)
                method.restype = ct.c_int
                retval = method(c_instance, ct.byref(c_error))
                self.error = c_error.value
                return self.error, retval
        else:
            m = method
        return m


#################################################################
class Spectrumanalyzer(Powermeter):
    _postfix_list = ("SetCenterFreq", "GetCenterFreq",
                     "SetSpan", "GetSpan", "SetStartFreq",
                     "GetStartFreq", "SetStopFreq", "GetStopFreq",
                     "SetRBW", "GetRBW", "SetVBW", "GetVBW",
                     "SetRefLevel", "GetRefLevel", "SetAtt", "GetAtt",
                     "SetAttAuto", "SetPreAmp", "GetPreAmp", "SetDetector",
                     "GetDetector", "SetTraceMode", "GetTraceMode", "SetTrace", "GetTrace",
                     "SetSweepCount", "GetSweepCount", "SetSweepTime",
                     "GetSweepTime", "GetSpectrum", "GetSpectrumNB",
                     "SetTriggerMode", "SetTriggerDelay", "SetWindow", "SetSweepPoints", "GetSweepPoints")
    _postfix = dict(list(zip(_postfix_list, _postfix_list)))  # spelling was OK

    def __init__(self, **kw):
        Powermeter.__init__(self, **kw)
        Spectrumanalyzer._postfix.update(Powermeter._postfix)
        self.levelunit = None

    def Init(self, ininame, channel=None):
        if channel is None:
            channel = 1
        ret = Powermeter.Init(self, ininame, channel)
        # self.levelunit=self.config.get('channel_%d'%channel,'unit')
        sec = fstrcmp('CHANNEL_%d' % channel, self.confsections, n=1, cutoff=0, ignorecase=True)[0]
        self.levelunit = self.config.get(sec, 'unit')  # MH
        # register additional wrappers
        self._addAttributes()
        return ret

    def _SetCenterFreq_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            def m(freq):
                c_freq = ct.c_double(freq)
                c_instance = ct.c_int(self.instance)
                c_error = ct.c_int(0)
                method.restype = ct.c_double
                retval = method(c_freq, c_instance, ct.byref(c_error))
                self.error = c_error.value
                return self.error, retval
        else:
            m = method
        return m

    def _GetCenterFreq_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            def m():
                c_instance = ct.c_int(self.instance)
                c_error = ct.c_int(0)
                method.restype = ct.c_double
                retval = method(c_instance, ct.byref(c_error))
                self.error = c_error.value
                return self.error, retval
        else:
            m = method
        return m

    def _SetSpan_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            def m(span):
                c_span = ct.c_double(span)
                c_instance = ct.c_int(self.instance)
                c_error = ct.c_int(0)
                method.restype = ct.c_double
                retval = method(c_span, c_instance, ct.byref(c_error))
                self.error = c_error.value
                return self.error, retval
        else:
            m = method
        return m

    def _GetSpan_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            def m():
                c_instance = ct.c_int(self.instance)
                c_error = ct.c_int(0)
                method.restype = ct.c_double
                retval = method(c_instance, ct.byref(c_error))
                self.error = c_error.value
                return self.error, retval
        else:
            m = method
        return m

    def _SetStartFreq_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            def m(start):
                c_instance = ct.c_int(self.instance)
                c_start = ct.c_double(start)
                c_error = ct.c_int(0)
                method.restype = ct.c_double
                retval = method(c_start, c_instance, ct.byref(c_error))
                self.error = c_error.value
                return self.error, retval
        else:
            m = method
        return m

    def _GetStartFreq_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            def m():
                c_instance = ct.c_int(self.instance)
                c_error = ct.c_int(0)
                method.restype = ct.c_double
                retval = method(c_instance, ct.byref(c_error))
                self.error = c_error.value
                return self.error, retval
        else:
            m = method
        return m

    def _SetStopFreq_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            def m(stop):
                c_instance = ct.c_int(self.instance)
                c_stop = ct.c_double(stop)
                c_error = ct.c_int(0)
                method.restype = ct.c_double
                retval = method(c_stop, c_instance, ct.byref(c_error))
                self.error = c_error.value
                return self.error, retval
        else:
            m = method
        return m

    def _GetStopFreq_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            def m():
                c_instance = ct.c_int(self.instance)
                c_error = ct.c_int(0)
                method.restype = ct.c_double
                retval = method(c_instance, ct.byref(c_error))
                self.error = c_error.value
                return self.error, retval
        else:
            m = method
        return m

    def _SetRBW_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            def m(rbw):
                c_instance = ct.c_int(self.instance)
                c_rbw = ct.c_double(rbw)
                c_error = ct.c_int(0)
                method.restype = ct.c_double
                retval = method(c_rbw, c_instance, ct.byref(c_error))
                self.error = c_error.value
                return self.error, retval
        else:
            m = method
        return m

    def _GetRBW_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            def m():
                c_instance = ct.c_int(self.instance)
                c_error = ct.c_int(0)
                method.restype = ct.c_double
                retval = method(c_instance, ct.byref(c_error))
                self.error = c_error.value
                return self.error, retval
        else:
            m = method
        return m

    def _SetVBW_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            def m(vbw):
                c_instance = ct.c_int(self.instance)
                c_vbw = ct.c_double(vbw)
                c_error = ct.c_int(0)
                method.restype = ct.c_double
                retval = method(c_vbw, c_instance, ct.byref(c_error))
                self.error = c_error.value
                return self.error, retval
        else:
            m = method
        return m

    def _GetVBW_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            def m():
                c_instance = ct.c_int(self.instance)
                c_error = ct.c_int(0)
                method.restype = ct.c_double
                retval = method(c_instance, ct.byref(c_error))
                self.error = c_error.value
                return self.error, retval
        else:
            m = method
        return m

    def _SetRefLevel_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            def m(rl):
                # the unit of level is given in the ini file for dll drivers
                # -> convert to correct unit here
                lv, unit = self.convert.scuq2c(rl.__unit__, self.levelunit, rl.__value__)
                c_rl = ct.c_double(lv)
                c_unit = ct.c_int(unit)
                c_instance = ct.c_int(self.instance)
                c_error = ct.c_int(0)
                method.restype = ct.c_double
                retval = method(c_rl, c_unit, c_instance, ct.byref(c_error))
                self.error = c_error.value
                return self.error, retval
        else:
            m = method
        return m

    def _GetRefLevel_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            def m():
                c_instance = ct.c_int(self.instance)
                c_error = ct.c_int(0)
                method.restype = ct.c_double
                retval = method(c_instance, ct.byref(c_error))
                self.error = c_error.value
                if not self.error:
                    rl, unit = self.convert.c2scuq(self.levelunit, retval)
                    obj = quantities.Quantity(unit, rl)
                return self.error, obj
        else:
            m = method
        return m

    def _SetAtt_wrap(self, method):
        # Attenuation
        if isinstance(method, ct._CFuncPtr):
            def m(att):
                c_instance = ct.c_int(self.instance)
                c_att = ct.c_double(att)
                c_error = ct.c_int(0)
                method.restype = ct.c_double
                retval = method(c_att, c_instance, ct.byref(c_error))
                self.error = c_error.value
                return self.error, retval
        else:
            m = method
        return m

    def _GetAtt_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            def m():
                c_instance = ct.c_int(self.instance)
                c_error = ct.c_int(0)
                method.restype = ct.c_double
                retval = method(c_instance, ct.byref(c_error))
                self.error = c_error.value
                return self.error, retval
        else:
            m = method
        return m

    def _SetAttAuto_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            def m(mode):
                MODES = ['NORMAL', 'LOWNOISE', 'LOWDIST']
                guess = fstrcmp(mode, MODES, n=1, cutoff=0, ignorecase=True)[0]
                try:
                    c_mode = ct.c_int(MODES.index(guess))
                except ValueError:
                    # be save
                    c_mode = ct.c_int(0)
                    self.error = self._Errors['Warning']
                c_instance = ct.c_int(self.instance)
                c_error = ct.c_int(0)
                method.restype = ct.c_int
                retval = method(c_mode, c_instance, ct.byref(c_error))
                self.error = c_error.value
                return self.error, retval
        else:
            m = method
        return m

    def _SetPreAmp_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            def m(amplification):
                c_amplification = ct.c_double(amplification)
                c_error = ct.c_int(0)
                c_instance = ct.c_int(self.instance)
                method.restype = ct.c_double
                retval = method(c_amplification, c_instance, ct.byref(c_error))
                self.error = c_error.value
                return self.error, retval
        else:
            m = method
        return m

    def _GetPreAmp_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            def m():
                c_instance = ct.c_int(self.instance)
                c_error = ct.c_int(0)
                method.restype = ct.c_double
                retval = method(c_instance, ct.byref(c_error))
                self.error = c_error.value
                return self.error, retval
        else:
            m = method
        return m

    def _SetDetector_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            def m(det):
                MODES = ['AUTOSELECT', 'AUTOPEAK', 'MAXPEAK', 'MINPEAK',
                         'SAMPLE', 'RMS', 'AVERAGE', 'DET_QPEAK']
                guess = fstrcmp(det, MODES, n=1, cutoff=0, ignorecase=True)[0]
                try:
                    c_det = ct.c_int(MODES.index(guess))
                except ValueError:
                    # be save
                    c_det = ct.c_int(0)
                    self.error = self._Errors['Warning']

                c_instance = ct.c_int(self.instance)
                c_error = ct.c_int(0)
                method.restype = ct.c_int
                retval = method(c_det, c_instance, ct.byref(c_error))
                self.error = c_error.value
                return self.error, retval
        else:
            m = method
        return m

    def _GetDetector_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            def m():
                MODES = ['AUTOSELECT', 'AUTOPEAK', 'MAXPEAK', 'MINPEAK',
                         'SAMPLE', 'RMS', 'AVERAGE', 'DET_QPEAK']
                c_instance = ct.c_int(self.instance)
                c_error = ct.c_int(0)
                method.restype = ct.c_int
                retval = method(c_instance, ct.byref(c_error))
                self.error = c_error.value
                return self.error, MODES[retval]
        else:
            m = method
        return m

    def _SetTraceMode_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            def m(tr):
                MODES = ['WRITE', 'VIEW', 'AVERAGE', 'BLANK',
                         'MAXHOLD', 'MINHOLD']
                guess = fstrcmp(tr, MODES, n=1, cutoff=0, ignorecase=True)[0]
                try:
                    c_tr = ct.c_int(MODES.index(guess))
                except ValueError:
                    # be save
                    c_tr = ct.c_int(0)
                    self.error = self._Errors['Warning']
                c_instance = ct.c_int(self.instance)
                c_error = ct.c_int(0)
                method.restype = ct.c_int
                retval = method(c_tr, c_instance, ct.byref(c_error))
                self.error = c_error.value
                return self.error, retval
        else:
            m = method
        return m

    def _GetTraceMode_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            def m():
                MODES = ['WRITE', 'VIEW', 'AVERAGE', 'BLANK',
                         'MAXHOLD', 'MINHOLD']
                c_instance = ct.c_int(self.instance)
                c_error = ct.c_int(0)
                method.restype = ct.c_int
                retval = method(c_instance, ct.byref(c_error))
                self.error = c_error.value
                return self.error, MODES[retval]
        else:
            m = method
        return m

    def _SetTrace_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            def m(tr):
                c_instance = ct.c_int(self.instance)
                c_tr = ct.c_int(tr)
                c_error = ct.c_int(0)
                method.restype = ct.c_int
                retval = method(c_tr, c_instance, ct.byref(c_error))
                self.error = c_error.value
                return self.error, retval
        else:
            m = method
        return m

    def _GetTrace_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            def m():
                c_instance = ct.c_int(self.instance)
                c_error = ct.c_int(0)
                method.restype = ct.c_int
                retval = method(c_instance, ct.byref(c_error))
                self.error = c_error.value
                return self.error, retval
        else:
            m = method
        return m

    def _SetSweepCount_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            def m(count):
                c_instance = ct.c_int(self.instance)
                c_count = ct.c_int(count)
                c_error = ct.c_int(0)
                method.restype = ct.c_int
                retval = method(c_count, c_instance, ct.byref(c_error))
                self.error = c_error.value
                return self.error, retval
        else:
            m = method
        return m

    def _GetSweepCount_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            def m():
                c_instance = ct.c_int(self.instance)
                c_error = ct.c_int(0)
                method.restype = ct.c_int
                retval = method(c_instance, ct.byref(c_error))
                self.error = c_error.value
                return self.error, retval
        else:
            m = method
        return m

    def _SetSweepTime_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            def m(st):
                c_instance = ct.c_int(self.instance)
                c_st = ct.c_double(st)
                c_error = ct.c_int(0)
                method.restype = ct.c_double
                retval = method(c_st, c_instance, ct.byref(c_error))
                self.error = c_error.value
                return self.error, retval
        else:
            m = method
        return m

    def _GetSweepTime_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            def m():
                c_instance = ct.c_int(self.instance)
                c_error = ct.c_int(0)
                method.restype = ct.c_double
                retval = method(c_instance, ct.byref(c_error))
                self.error = c_error.value
                return self.error, retval
        else:
            m = method
        return m

    def _GetSpectrum_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            def m(ndata):
                c_instance = ct.c_int(self.instance)
                c_error = ct.c_int(0)
                c_ndata = ct.c_int(5001)
                c_vec_type = umd_types.UMD_DMRESULT * 5001
                c_vec = c_vec_type()
                method.restype = ct.c_int
                retval = method(ct.byref(c_vec), c_ndata, c_instance, ct.byref(c_error))
                self.error = c_error.value
                if not self.error:
                    c_unit = c_vec[0].unit
                    # print max([c_vec[i].v for i in range(retval)])
                    vals, unit = self.convert.c2scuq(c_unit, [c_vec[i].v for i in range(retval)])
                    # print max(vals)
                    ls, unit = self.convert.c2scuq(c_unit, [c_vec[i].l for i in range(retval)])
                    us, unit = self.convert.c2scuq(c_unit, [c_vec[i].u for i in range(retval)])
                    nv = numpy.array(vals)
                    nl = numpy.array(ls)
                    nu = numpy.array(us)
                    sigs = (nu - nl) * 0.5
                    obj = quantities.Quantity(unit, ucomponents.UncertainInput(nv, sigs))
                else:
                    obj = None
                return self.error, obj
        else:
            m = method
        return m

    def _GetSpectrumNB_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            def m(retrigger=None):
                if retrigger is None:
                    retrigger = 'OFF'
                MODES = ['OFF', 'ON']
                guess = fstrcmp(retrigger, MODES, n=1, cutoff=0, ignorecase=True)[0]
                try:
                    c_retrigger = ct.c_int(MODES.index(guess))  # off->0, On->1
                except ValueError:
                    # save: do not retrigger
                    c_retrigger = ct.c_int(0)
                    self.error = self._Errors['Warning']

                c_instance = ct.c_int(self.instance)
                c_error = ct.c_int(0)
                c_ndata = ct.c_int(5001)
                c_vec = umd_types.UMD_DMRESULT * 5001
                method.restype = ct.c_int
                retval = method(ct.byref(c_vec), c_ndata, c_retrigger, c_instance, ct.byref(c_error))
                self.error = c_error.value
                if not self.error:
                    c_unit = c_vec[0].u.value
                    vals, unit = self.convert.c2scuq(c_unit, [c_vec[i].v.value for i in range(retval)])
                    ls, unit = self.convert.c2scuq(c_unit, [c_vec[i].l.value for i in range(retval)])
                    us, unit = self.convert.c2scuq(c_unit, [c_vec[i].u.value for i in range(retval)])
                    nv = numpy.array(vals)
                    nl = numpy.array(ls)
                    nu = numpy.array(us)
                    sigs = (nu - nl) * 0.5
                    obj = quantities.Quantity(unit, ucomponents.UncertainInput(nv, sigs))
                else:
                    obj = None
                return self.error, obj
        else:
            def m(retrigger):
                if retrigger is None:
                    retrigger = 'OFF'
                return method(retrigger)
        return m

    def _SetTriggerMode_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            def m(mode):
                MODES = ['FREE', 'VIDEO', 'EXTERNAL']
                modeguess = fstrcmp(mode, MODES, n=1, cutoff=0, ignorecase=True)[0]
                c_mode = ct.c_int(MODES.index(modeguess))
                c_instance = ct.c_int(self.instance)
                c_error = ct.c_int(0)
                method.restype = ct.c_int
                retval = method(c_mode, c_instance, ct.byref(c_error))
                self.error = c_error.value
                return self.error, retval
        else:
            m = method
        return m

    def _SetTriggerDelay_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            def m(delay):  # delay in seconds
                c_delay = ct.c_double(delay)
                c_instance = ct.c_int(self.instance)
                c_error = ct.c_int(0)
                method.restype = ct.c_int
                retval = method(c_delay, c_instance, ct.byref(c_error))
                self.error = c_error.value
                return self.error, retval
        else:
            m = method
        return m

    def _SetWindow_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            def m(window):  # window 1,2,...
                c_window = ct.c_int(window)
                c_instance = ct.c_int(self.instance)
                c_error = ct.c_int(0)
                method.restype = ct.c_int
                retval = method(c_window, c_instance, ct.byref(c_error))
                self.error = c_error.value
                return self.error, retval
        else:
            m = method
        return m

    def _SetSweepPoints_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            raise NotImplementedError
        else:
            m = method
        return m

    def _GetSweepPoints_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            raise NotImplementedError
        else:
            m = method
        return m


#################################################################
class Switch(Device):
    _postfix = {"SwitchTo": "SwitchTo",
                "getSWState": "GetSwitchState",
                "getNrSWStates": "GetNrSWStates",
                "getMask": "GetMask",
                "getStatList": "GetStatList",
                "getChannelName": "GetChannelName",
                "getNrSWDev": "GetNrSWDev",
                "setQuitMode": "SetQuitMode"}

    def __init__(self, **kw):
        # call parent init
        Device.__init__(self, **kw)

    def Init(self, ininame, channel=None):
        if channel is None:
            channel = 1
        ret = Device.Init(self, ininame, channel)
        # register additional wrappers
        self._addAttributes()
        return ret

    def _SwitchTo_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            def m(channel):
                c_instance = ct.c_int(self.instance)
                c_channel = ct.c_int(channel)
                c_error = ct.c_int(0)
                method.restype = ct.c_int
                retval = method(c_channel, c_instance, ct.byref(c_error))
                self.error = c_error.value
                return self.error, retval
        else:
            m = method
        return m

    def _GetSWState_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            def m():
                c_instance = ct.c_int(self.instance)
                c_channel = ct.c_int()
                c_val = ct.c_int()
                c_error = ct.c_int(0)
                method.restype = ct.c_int
                retval = method(ct.byref(c_channel), ct.byref(c_val), c_instance, ct.byref(c_error))
                self.error = c_error.value
                if not self.error and retval == 0:
                    return self.error, c_channel.value, c_val.value
                else:
                    return self.error, None, None
        else:
            m = method
        return m

    def _GetNrSWStates_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            def m():
                c_instance = ct.c_int(self.instance)
                c_states = ct.c_int()
                c_error = ct.c_int(0)
                method.restype = ct.c_int
                retval = method(ct.byref(c_states), c_instance, ct.byref(c_error))
                self.error = c_error.value
                return self.error, c_states.value
        else:
            m = method
        return m

    def _GetMask_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            def m():
                c_instance = ct.c_int(self.instance)
                c_mask = ct.c_int()
                c_error = ct.c_int(0)
                method.restype = ct.c_int
                retval = method(ct.byref(c_mask), c_instance, ct.byref(c_error))
                self.error = c_error.value
                return self.error, c_mask.value
        else:
            m = method
        return m

    def _GetStatList_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            def m():
                c_instance = ct.c_int(self.instance)
                c_states = umd_types.UMDListTypeStr100()
                c_error = ct.c_int(0)
                method.restype = ct.c_int
                retval = method(ct.byref(c_states), c_instance, ct.byref(c_error))
                self.error = c_error.value
                obj = None
                if not self.error:
                    obj = [c_states.elem.value]
                    next = c_states.next.value
                    while next:
                        obj.append(next.contents.elem.value)
                        next = next.contents.next.value
                return self.error, obj
        else:
            m = method
        return m

    def _GetChannelName_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            def m():
                c_instance = ct.c_int(self.instance)
                c_name = ct.c_char * 255
                c_error = ct.c_int(0)
                method.restype = ct.c_int
                retval = method(ct.byref(c_name), c_instance, ct.byref(c_error))
                self.error = c_error.value
                return self.error, c_name.value
        else:
            m = method
        return m

    def _GetNrSWDev_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            def m():
                c_instance = ct.c_int(self.instance)
                c_nr_sw_dev = ct.c_int()
                c_error = ct.c_int(0)
                method.restype = ct.c_int
                retval = method(ct.byref(c_nr_sw_dev), c_instance, ct.byref(c_error))
                self.error = c_error.value
                return self.error, c_nr_sw_dev.value
        else:
            m = method
        return m

    def _setQuitMode_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            def m(mode):
                MODES = ["LATCHING", "NON_LATCHING"]
                guess = fstrcmp(mode, MODES, n=1, cutoff=0, ignorecase=True)[0]
                try:
                    c_mode = ct.c_int(MODES.index(guess))
                except ValueError:
                    c_mode = ct.c_int(0)  # Latching
                    self.error = self._Errors['Warning']

                c_instance = ct.c_int(self.instance)
                c_error = ct.c_int(0)
                method.restype = ct.c_int
                retval = method(c_mode, c_instance, ct.byref(c_error))
                self.error = c_error.value
                return self.error, retval
        else:
            m = method
        return m

    #################################################################


class Fieldprobe(Device):
    _postfix = {"Zero": "Zero",
                "setFreq": "SetFreq",
                "getData": "GetData",
                "getDataNB": "GetDataNB",
                "Trigger": "Trigger",
                "getBatteryState": "GetBatteryState",
                "GetWaveform": "GetWaveform"}

    def __init__(self, **kw):
        # call parent init
        Device.__init__(self, **kw)

    def Init(self, ininame, channel=None):
        if channel is None:
            channel = 1
        ret = Device.Init(self, ininame, channel)
        # register additional wrappers
        self._addAttributes()
        return ret

    def _SetFreq_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            def m(freq):
                c_instance = ct.c_int(self.instance)
                c_freq = ct.c_double(freq)
                c_error = ct.c_int(0)
                method.restype = ct.c_double
                retval = method(c_freq, c_instance, ct.byref(c_error))
                self.error = c_error.value
                return self.error, retval
        else:
            m = method
        return m

    def _Zero_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            def m(state=None):
                if state is None:
                    state = 'On'
                MODES = ['OFF', 'ON']
                guess = fstrcmp(state, MODES, n=1, cutoff=0, ignorecase=True)[0]
                try:
                    c_state = ct.c_int(MODES.index(guess))  # off->0, On->1
                except ValueError:
                    # safe: do Zero
                    c_state = ct.c_int(1)
                    self.error = self._Errors['Warning']
                c_instance = ct.c_int(self.instance)
                c_error = ct.c_int(0)
                method.restype = ct.c_int
                retval = method(c_state, c_instance, ct.byref(c_error))
                self.error = c_error.value
                return self.error, retval
        else:
            def m(state=None):
                if state is None:
                    state = 'On'
                return method(state)
        return m

    def _GetDataNB_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            def m(retrigger=None):
                if retrigger is None:
                    retrigger = 'Off'
                MODES = ['OFF', 'ON']
                guess = fstrcmp(retrigger, MODES, n=1, cutoff=0, ignorecase=True)[0]
                try:
                    c_retrigger = ct.c_int(MODES.index(guess))  # off->0, On->1
                except ValueError:
                    # save: do not retrigger
                    c_retrigger = ct.c_int(0)
                    self.error = self._Errors['Warning']
                c_transmission = umd_types.UMD_FIELD_DMRESULT()
                method.restype = ct.c_int
                c_instance = ct.c_int(self.instance)
                c_error = ct.c_int(0)
                retval = method(ct.byref(c_transmission), c_retrigger, c_instance, ct.byref(c_error))
                self.error = c_error.value
                if not self.error and retval == 0:
                    obj = self.cdata_to_obj(c_transmission)
                else:
                    obj = None
                return self.error, obj
        else:
            def m(retrigger=None):
                if retrigger is None:
                    retrigger = 'Off'
                return method(retrigger)
        return m

    def _GetData_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            def m():
                c_transmission = umd_types.UMD_FIELD_DMRESULT()
                method.restype = ct.c_int
                c_instance = ct.c_int(self.instance)
                c_error = ct.c_int(0)
                retval = method(ct.byref(c_transmission), c_instance, ct.byref(c_error))
                self.error = c_error.value
                if not self.error and retval == 0:
                    obj = self.cdata_to_obj(c_transmission)
                else:
                    obj = None
                return self.error, obj
        else:
            m = method
        return m

    def _Trigger_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            def m():
                c_instance = ct.c_int(self.instance)
                c_error = ct.c_int(0)
                method.restype = ct.c_int
                retval = method(c_instance, ct.byref(c_error))
                self.error = c_error.value
                return self.error, retval
        else:
            m = method
        return m

    def _GetBatteryState_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            def m():
                MODES = ['BATTERY OK', 'BATTERY LOW']
                c_instance = ct.c_int(self.instance)
                c_error = ct.c_int(0)
                c_state = ct.c_int(0)  # (state)
                method.restype = ct.c_int
                retval = method(ct.byref(c_state), c_instance, ct.byref(c_error))
                # retval = method(c_instance, ct.byref(c_error))
                print((c_state.value))
                self.error = c_error.value
                return self.error, retval
        else:
            m = method
        return m

    def _GetWaveform_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            def m():
                return -1, None, None, None
        else:
            m = method
        return m
#################################################################
class Motorcontroller(Device):
    _postfix = {"goto": "Goto",
                "getState": "GetState",
                "setSpeed": "SetSpeed",
                "getSpeed": "GetSpeed",
                "move": "Move"}

    def __init__(self, **kw):
        # call parent init
        Device.__init__(self, **kw)
        self.posunit = None

    def Init(self, ininame, channel=None):
        if channel is None:
            channel = 1
        ret = Device.Init(self, ininame, channel)
        sec = fstrcmp('CHANNEL_%d' % channel, self.confsections, n=1, cutoff=0, ignorecase=True)[0]
        self.posunit = self.config.get(sec, 'unit')

        # register additional wrappers
        self._addAttributes()
        return ret

    def _Goto_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            def m(pos, dir):
                try:
                    s_pos = pos.__value__.get_value()
                    s_sig = pos.__value__.get_uncertainty()
                except AttributeError:
                    s_pos = pos.__value__
                    s_sig = 0

                c_p, unit = self.convert.scuq2c(pos.__unit__, self.posunit, s_pos)
                c_s, unit = self.convert.scuq2c(pos.__unit__, self.posunit, s_sig)

                c_pos = umd_types.UMD_MRESULT()
                c_pos.v = c_p
                c_pos.u = c_p + c_s
                c_pos.l = c_p - c_s
                c_pos.u = unit

                # fill c_pos from pos
                c_dir = ct.c_int(dir)
                c_error = ct.c_int(0)
                c_instance = ct.c_int(self.instance)
                method.restype = umd_types.UMD_MRESULT()
                retval = method(c_pos, c_dir, c_instance, ct.byref(c_error))
                self.error = c_error.value
                if not self.error:
                    obj = self.cdata_to_obj(retval)
                else:
                    obj = None
                return self.error, obj
        else:
            m = method
        return m

    def _GetState_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            def m():
                c_instance = ct.c_int(self.instance)
                c_pos = umd_types.UMD_MRESULT()
                c_dir = ct.c_double(dir)
                c_error = ct.c_int(0)
                method.restype = ct.c_int
                retval = method(ct.byref(c_pos), ct.byref(c_dir), c_instance, ct.byref(c_error))
                self.error = c_error.value
                if not self.error and retval == 0:
                    obj = self.cdata_to_obj(c_pos)
                else:
                    obj = None
                return self.error, obj, c_dir.value
        else:
            m = method
        return m

    def _SetSpeed_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            def m(speed):
                c_instance = ct.c_int(self.instance)
                c_speed = ct.c_double(speed)
                c_error = ct.c_int(0)
                method.restype = ct.c_int
                retval = method(c_speed, c_instance, ct.byref(c_error))
                self.error = c_error.value
                return self.error, retval
        else:
            m = method
        return m

    def _GetSpeed_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            def m(speed):
                c_instance = ct.c_int(self.instance)
                c_speed = ct.c_double(speed)
                c_error = ct.c_int(0)
                method.restype = ct.c_int
                retval = method(ct.byref(c_speed), c_instance, ct.byref(c_error))
                self.error = c_error.value
                return self.error, c_speed.value
        else:
            m = method
        return m

    def _Move_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            def m(dir):
                c_instance = ct.c_int(self.instance)
                c_dir = ct.c_int(dir)
                c_error = ct.c_int(0)
                method.restype = ct.c_int
                retval = method(c_dir, c_instance, ct.byref(c_error))
                self.error = c_error.value
                return self.error, retval
        else:
            m = method
        return m

    #################################################################


class Tuner(Device):
    _postfix = {"setFreq": "SetFreq",
                "setPos": "SetPos",
                "getPos": "GetPos",
                "nextPos": "NextPos"}

    def __init__(self, **kw):
        # call parent init
        Device.__init__(self, **kw)

    def Init(self, ininame, channel=None):
        ret = Device.Init(self, ininame, channel)

        # register additional wrappers
        self._addAttributes()
        return ret

    def _SetFreq_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            def m(freq):
                c_instance = ct.c_int(self.instance)
                c_freq = ct.c_double(freq)
                c_error = ct.c_int(0)
                method.restype = ct.c_double
                retval = method(c_freq, c_instance, ct.byref(c_error))
                self.error = c_error.value
                return self.error, retval
        else:
            m = method
        return m

    def _SetPos_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            def m(p):
                c_instance = ct.c_int(self.instance)
                c_p = ct.c_int(p)
                c_error = ct.c_int(0)
                method.restype = ct.c_int
                retval = method(c_p, c_instance, ct.byref(c_error))
                self.error = c_error.value
                return self.error, retval
        else:
            m = method
        return m

    def _GetPos_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            def m():
                c_instance = ct.c_int(self.instance)
                EightResults = umd_types.UMD_MRESULT * 8  # Eight is hard coded in the DLL driver
                c_p = EightResults()
                c_error = ct.c_int(0)
                method.restype = ct.c_int
                retval = method(ct.byref(c_p), c_instance, ct.byref(c_error))
                obj = [self.cdata_to_obj(co) for co in c_p]
                self.error = c_error.value
                return self.error, obj
        else:
            m = method
        return m

    def _NextPos_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            def m():
                c_instance = ct.c_int(self.instance)
                c_error = ct.c_int(0)
                method.restype = ct.c_int
                retval = method(c_instance, ct.byref(c_error))
                self.error = c_error.value
                return self.error, retval
        else:
            m = method
        return m

    #################################################################


class Step2port(NPort):
    # additional functions for this instrument type
    _postfix = {"getNominal": "GetNominal",
                "getNStates": "GetNStates",
                "SwitchTo": "SwitchTo"}

    def __init__(self, **kw):
        # call parent init
        NPort.__init__(self, **kw)
        Step2port._postfix.update(NPort._postfix)
        self.chunit = None

    def Init(self, ininame, channel=None):
        # load DLL or pyd (etc), register wrappers for common methods
        ret = NPort.Init(self, ininame, channel)
        sec = fstrcmp('CHANNEL_%d' % channel, self.confsections, n=1, cutoff=0, ignorecase=True)[0]
        self.chunit = self.config.get(sec, 'unit')

        # register additional wrappers
        self._addAttributes()
        return ret

    def _GetNominal_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            def m(state, what):
                c_nominal_r = ct.c_double()
                c_nominal_i = ct.c_double()
                c_what = ct.c_char_p(what)
                c_state = ct.c_int(state)
                c_error = ct.c_int(0)
                c_instance = ct.c_int(self.instance)
                method.restype = ct.c_int
                retval = method(ct.byref(c_nominal_r), ct.byref(c_nominal_i), c_what, c_state, c_instance,
                                ct.byref(c_error))
                self.error = c_error.value
                if not self.error and retval == 0:
                    s_val, s_unit = self.convert.c2scuq(self.chunit, complex(c_nominal_r.value, c_nominal_i.value))
                    obj = quantities.Quantity(s_unit, s_val)
                else:
                    obj = None
                return self.error, obj
        else:
            m = method
        return m

    def _GetNStates_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            def m():
                c_instance = ct.c_int(self.instance)
                c_nstates = ct.c_int()
                c_error = ct.c_int(0)
                method.restype = ct.c_int
                retval = method(ct.byref(c_nstates), c_instance, ct.byref(c_error))
                self.error = c_error.value
                return self.error, c_nstates.value
        else:
            m = method
        return m

    def _SwitchTo_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            def m(state):
                c_instance = ct.c_int(self.instance)
                c_state = ct.c_int(state)
                c_error = ct.c_int(0)
                method.restype = ct.c_int
                retval = method(c_state, c_instance, ct.byref(c_error))
                self.error = c_error.value
                return self.error, retval
        else:
            m = method
        return m

    #################################################################


class Vectornetworkanalyser(Device):
    _postfix = {'SetCenterFreq': 'SetCenterFreq',
                'GetCenterFreq': 'GetCenterFreq',
                'SetSpan': 'SetSpan',
                'GetSpan': 'GetSpan',
                'SetStartFreq': 'SetStartFreq',
                'GetStartFreq': 'GetStartFreq',
                'SetStopFreq': 'SetStopFreq',
                'GetStopFreq': 'GetStopFreq',
                'SetRBW': 'SetRBW',
                'GetRBW': 'GetRBW',
                'SetRefLevel': 'SetRefLevel',
                'GetRefLevel': 'GetRefLevel',
                'SetDivisionValue': 'SetDivisionValue',
                'GetDivisionValue': 'GetDivisionValue',

                # ???
                # 'SetTraceMode': 'SetTraceMode',
                # 'GetTraceMode': 'GetTraceMode',

                'SetTrace': 'SetTrace',
                'GetTrace': 'GetTrace',
                'DelTrace': 'DelTrace',
                'SetSparameter': 'SetSparameter',
                'GetSparameter': 'GetSparameter',
                'SetChannel': 'SetChannel',
                'DelChannel': 'DelChannel',
                'GetChannel': 'GetChannel',
                'SetSweepType': 'SetSweepType',
                'GetSweepType': 'GetSweepType',
                'SetSweepCount': 'SetSweepCount',
                'GetSweepCount': 'GetSweepCount',
                'NewSweepCount': 'NewSweepCount',
                'SetSweepPoints': 'SetSweepPoints',
                'GetSweepPoints': 'GetSweepPoints',
                'SetSingelSweep': 'SetSingelSweep',
                'GetSingelSweep': 'GetSingelSweep',
                'GetSpectrum': 'GetSpectrum',
                'GetSpectrumNB': 'GetSpectrumNB',
                'SetTriggerMode': 'SetTriggerMode',
                'GetTriggerMode': 'GetTriggerMode',
                'SetTriggerDelay': 'SetTriggerDelay',
                'GetTriggerDelay': 'GetTriggerDelay',
                'SetWindow': 'SetWindow',
                'DelWindow': 'DelWindow',
                'Quit': 'Quit',
                'GetDescription': 'GetDescription',

                "Trigger": "SetTriggerMode",
                "getData": "GetTrace",
                "getDataNB": "GetTraceNB"}

    def __init__(self, **kw):
        # call parent init
        Device.__init__(self, **kw)

    def Init(self, ininame, channel=None):
        if channel is None:
            channel = 1
        ret = Device.Init(self, ininame, channel)

        # register additional wrappers
        self._addAttributes()
        return ret

    def _GetTriggerDelay_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            raise NotImplementedError
        else:
            m = method
        return m

    def _DelChannel_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            raise NotImplementedError
        else:
            m = method
        return m

    def _SetSweepType_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            raise NotImplementedError
        else:
            m = method
        return m

    def _DelTrace_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            raise NotImplementedError
        else:
            m = method
        return m

    def _GetSpectrum_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            raise NotImplementedError
        else:
            m = method
        return m

    def _SetChannel_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            raise NotImplementedError
        else:
            m = method
        return m

    def _GetDivisionValue_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            raise NotImplementedError
        else:
            m = method
        return m

    def _DelWindow_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            raise NotImplementedError
        else:
            m = method
        return m

    def _GetRBW_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            raise NotImplementedError
        else:
            m = method
        return m

    def _GetSweepType_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            raise NotImplementedError
        else:
            m = method
        return m

    def _GetTriggerMode_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            raise NotImplementedError
        else:
            m = method
        return m

    def _GetSparameter_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            raise NotImplementedError
        else:
            m = method
        return m

    def _SetTriggerDelay_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            raise NotImplementedError
        else:
            m = method
        return m

    def _GetSpectrumNB_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            raise NotImplementedError
        else:
            m = method
        return m

    def _GetSweepCount_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            raise NotImplementedError
        else:
            m = method
        return m

    def _SetRefLevel_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            raise NotImplementedError
        else:
            m = method
        return m

    def _SetStopFreq_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            raise NotImplementedError
        else:
            m = method
        return m

    def _SetSweepCount_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            raise NotImplementedError
        else:
            m = method
        return m

    def _SetSparameter_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            raise NotImplementedError
        else:
            m = method
        return m

    def _Quit_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            raise NotImplementedError
        else:
            m = method
        return m

    def _SetSweepPoints_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            raise NotImplementedError
        else:
            m = method
        return m

    def _SetStartFreq_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            raise NotImplementedError
        else:
            m = method
        return m

    def _GetCenterFreq_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            raise NotImplementedError
        else:
            m = method
        return m

    def _GetStopFreq_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            raise NotImplementedError
        else:
            m = method
        return m

    def _GetTraceMode_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            raise NotImplementedError
        else:
            m = method
        return m

    def _NewSweepCount_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            raise NotImplementedError
        else:
            m = method
        return m

    def _SetSpan_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            raise NotImplementedError
        else:
            m = method
        return m

    def _GetDescription_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            raise NotImplementedError
        else:
            m = method
        return m

    def _SetCenterFreq_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            raise NotImplementedError
        else:
            m = method
        return m

    def _SetTriggerMode_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            raise NotImplementedError
        else:
            m = method
        return m

    def _SetWindow_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            raise NotImplementedError
        else:
            m = method
        return m

    def _GetRefLevel_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            raise NotImplementedError
        else:
            m = method
        return m

    def _SetTrace_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            raise NotImplementedError
        else:
            m = method
        return m

    def _SetTraceMode_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            raise NotImplementedError
        else:
            m = method
        return m

    def _GetStartFreq_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            raise NotImplementedError
        else:
            m = method
        return m

    def _GetSweepPoints_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            raise NotImplementedError
        else:
            m = method
        return m

    def _SetDivisionValue_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            raise NotImplementedError
        else:
            m = method
        return m

    def _SetSingelSweep_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            raise NotImplementedError
        else:
            m = method
        return m

    def _GetTrace_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            raise NotImplementedError
        else:
            m = method
        return m

    def _SetRBW_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            raise NotImplementedError
        else:
            m = method
        return m

    def _GetChannel_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            raise NotImplementedError
        else:
            m = method
        return m

    def _GetSpan_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            raise NotImplementedError
        else:
            m = method
        return m

    def _GetSingelSweep_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            raise NotImplementedError
        else:
            m = method
        return m

    def _Trigger_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            def m():
                c_instance = ct.c_int(self.instance)
                c_error = ct.c_int(0)
                method.restype = ct.c_int
                retval = method(c_instance, ct.byref(c_error))
                self.error = c_error.value
                return self.error, retval
        else:
            m = method
        return m

    def _GetTrace_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            def m(freq, what, rows, points, size):  # TODO
                c_instance = ct.c_int(self.instance)
                c_error = ct.c_int(0)
                c_data = umd_types.UMD_CMRESULT()
                c_freq = ct.c_double(freq)
                c_what = ct.c_char(what)
                c_rows = ct.c_int(rows)
                c_points = ct.c_int(points)
                c_size = ct.c_int(size)
                method.restype = ct.c_int
                retval = method(ct.byref(c_data), c_freq, c_what, c_rows, c_points, c_size, c_instance,
                                ct.byref(c_error))
                self.error = c_error.value
                ##                if not self.error:
                ##                    obj=self.cdata_to_obj(c_data)
                ##
                ##                else:
                ##                    obj=None

                return self.error, c_data
        else:
            m = method
        return m

    def _GetTraceNB_wrap(self, method):
        if isinstance(method, ct._CFuncPtr):
            def m(freq, what, rows, points, size, ret_stat):  # TODO
                c_instance = ct.c_int(self.instance)
                c_error = ct.c_int(0)
                c_data = umd_types.UMD_CMRESULT()
                c_freq = ct.c_double(freq)
                c_what = ct.c_char(what)
                c_rows = ct.c_int(rows)
                c_points = ct.c_int(points)
                c_size = ct.c_int(size)
                c_ret_stat = ct.c_int(ret_stat)
                method.restype = ct.c_int
                retval = method(ct.byref(c_data), c_freq, c_what, c_rows, c_points, c_size, c_ret_stat, c_instance,
                                ct.byref(c_error))
                self.error = c_error.value
                ##                if not self.error:
                ##                    obj=self.cdata_to_obj(c_data)
                ##
                ##                else:
                ##                    obj=None

                return self.error, c_data
        else:
            m = method
        return m


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
        fuguess = fstrcmp(fromunit, self.cunits, n=1, cutoff=0, ignorecase=True)[0]
        tuguess = fstrcmp(tounit, self.cunits, n=1, cutoff=0, ignorecase=True)[0]
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
        guess = fstrcmp(Cunit, self.cunits, n=1, cutoff=0, ignorecase=True)[0]
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
        guess = fstrcmp(Cunit, self.cunits, n=1, cutoff=0, ignorecase=True)[0]
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
                         VENDOR =UMD
                         SERIALNR = 
                         DEVICEID = 
                         DRIVER = mpylab.device.nport.py

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
