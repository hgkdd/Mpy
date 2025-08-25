# -*- coding: utf-8 -*-

import ctypes as ct

WORD = ct.c_ushort


class SYSTEMTIME(ct.Structure):
    _fields_ = [('wYear', WORD),
                ('wMonth', WORD),
                ('wDayOfWeek', WORD),
                ('wDay', WORD),
                ('wHour', WORD),
                ('wMinute', WORD),
                ('wSecond', WORD),
                ('wMilliseconds', WORD)]


UMD_DREAL = ct.c_double
UMD_REAL = ct.c_float


class UMD_COMPLEX(ct.Structure):
    _fields_ = [('r', UMD_REAL), ('i', UMD_REAL)]

    def __mul__(self, other):
        result = UMD_COMPLEX()
        result.r = self.r * other
        result.i = self.i * other
        return result

    def _abs(self):
        result = (self.r ** 2 + self.i ** 2) ** 0.5
        return result


class UMD_DCOMPLEX(ct.Structure):
    _fields_ = [('r', UMD_DREAL), ('i', UMD_DREAL)]

    def __mul__(self, other):
        result = UMD_COMPLEX()
        result.r = self.r * other
        result.i = self.i * other
        return result

    def _abs(self):
        result = (self.r ** 2 + self.i ** 2) ** 0.5
        return result


class UMD_MRESULT(ct.Structure):
    _fields_ = [('v', UMD_REAL),
                ('l', UMD_REAL),
                ('u', UMD_REAL),
                ('t', SYSTEMTIME),
                ('unit', ct.c_int)]


class UMD_DMRESULT(ct.Structure):
    _fields_ = [('v', UMD_DREAL),
                ('l', UMD_DREAL),
                ('u', UMD_DREAL),
                ('t', SYSTEMTIME),
                ('unit', ct.c_int)]


class UMD_CMRESULT(ct.Structure):
    _fields_ = [('v', UMD_COMPLEX),
                ('l', UMD_COMPLEX),
                ('u', UMD_COMPLEX),
                ('t', SYSTEMTIME),
                ('unit', ct.c_int)]


class UMD_DCMRESULT(ct.Structure):
    _fields_ = [('v', UMD_DCOMPLEX),
                ('l', UMD_DCOMPLEX),
                ('u', UMD_DCOMPLEX),
                ('t', SYSTEMTIME),
                ('unit', ct.c_int)]


class UMD_DTRIPPEL(ct.Structure):
    _fields_ = [('v', UMD_DREAL),
                ('l', UMD_DREAL),
                ('u', UMD_DREAL)]


class UMD_FIELD_DMRESULT(ct.Structure):
    _fields_ = [('x', UMD_DTRIPPEL),
                ('y', UMD_DTRIPPEL),
                ('z', UMD_DTRIPPEL),
                ('r', UMD_DTRIPPEL),
                ('t', SYSTEMTIME),
                ('unit', ct.c_int)]


class UMDListTypeStr100(ct.Structure):
    pass


UMDListTypeStr100._fields_ = [('elem', ct.c_char * 100),
                              ('next', ct.POINTER(UMDListTypeStr100))]
