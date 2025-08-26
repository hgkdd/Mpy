# -*- coding: iso-8859-1 -*-
"""This is :mod:`mpylab.tools.interpol`.

   Provides interpolation routines

   :author: Hans Georg Krauthäuser (main author)
   :copyright: All rights reserved
   :license: no licence yet
"""
import cmath
import math
import scipy
import scipy.interpolate
from numpy import nan_to_num
from scuq import *


def _arg(obj):
    """Return the angle of *obj* in the complex plane (in radians). If *obj* does not provide attributes 
       `imag` and `real`, `0` ist returned. Else, it returns `math.atan2(obj.imag,obj.real)`.
    """
    try:
        phi = math.atan2(obj.imag, obj.real)  # complex
    except AttributeError:
        # real
        phi = 0
    return phi


def unwrap(dct, arg=None):
    """Phase unwrapping of values in dictionary *dct*.

       *dct* is a `dict` with keys that can be sorted (frequencies). The values are typically complex values representing e.g. S-parameters.

       If *arg* is given, it is expected to be a callable with a signature like :meth:`math.atan2` that
       returns the argument (phase) of the objects in *dct*.

       The function returns a 3-tuple of lists with the sorted keys, the magnitude, and the phase of the values.
    """
    if arg is None:
        arg = _arg
    freqs = sorted(dct.keys())
    # print dct

    unwrapped = ([], [], [])
    dang = 0
    q = dct[freqs[0]]
    phik = arg(q)
    for k, f in enumerate(freqs[:-1]):
        # print f, ang, dang, phik
        unwrapped[0].append(f)
        unwrapped[1].append(abs(dct[f]))
        unwrapped[2].append(phik)
        try:
            q = dct[freqs[k + 1]] / dct[f]
            q = nan_to_num(q)
            dang = arg(q)
        except ZeroDivisionError:
            dang = 0

        phik = phik + dang
    f = freqs[-1]
    unwrapped[0].append(f)
    unwrapped[1].append(abs(dct[f]))
    unwrapped[2].append(phik)
    # return tuple of list: f mag ang sorted fy f
    return unwrapped


class cplx_interpol(object):
    """Interpolation routine for a *dct* with complex values. *type* is not yet used. Phase is unwrapped using :meth:`unwrap`

       Example::

          In [1]: from interpol import *
          You should use UTF-8 instead of mac-roman as encoding, or the SI units won't display correctly

          In [2]: freqs=[p*1e6 for p in range(16)]

          In [3]: phis=[p*math.pi/16 for p in range(16)]

          In [4]: vals=[complex(math.cos(p),math.sin(p)) for p in phis]

          In [5]: dct=dict((v for v in zip(freqs,vals)))

          In [6]: cinter=cplx_interpol(dct)

          In [7]: abs(cinter(5e5))
          Out[8]: 1.0

          In [9]: math.atan2(cinter(5e5).imag, cinter(5e5).real)
          Out[9]: 0.098174770424681035
       
    """

    def __init__(self, dct, typ=None):
        self.dct = dct
        self.unwrapped = unwrap(dct)
        _x, _y, _z = self.unwrapped
        self.magipol = scipy.interpolate.interp1d(_x, _y)
        self.phaseipol = scipy.interpolate.interp1d(_x, _z)

    def __call__(self, f):
        m = float(self.magipol(f))
        p = float(self.phaseipol(f))
        c = m * cmath.exp(1j * p)
        if c.imag == 0:
            return c.real
        else:
            return c


class UQ_interpol(object):
    """Interpolation routine for a *dct* with uncertain quantities as values. 
       *type* is not yet used. :meth:`cplx_interpol` is used to interpolate complex values.

       Example::
       
          from mpylab.tools.interpol import *
          import numpy
          import scuq

          freqs=[p*1e6 for p in range(16)]
          phis=[p*math.pi/16 for p in range(16)]
          vals=[complex(math.cos(p),math.sin(p)) for p in phis]
          dct=dict((v for v in zip(freqs,vals)))
          cinter=cplx_interpol(dct)
          print "Complex interpolation:"
          print cinter(5e5)
          print

          uqvals=[scuq.quantities.Quantity(scuq.si.VOLT,v) for v in vals]
          dct2=dict((v for v in zip(freqs,uqvals)))
          uqinter=UQ_interpol(dct2)
          print "SCUQ interpolation:"
          print uqinter(5e5)

    """

    def __init__(self, dct, typ=None):
        self.dct = dct
        self.vdct = {}
        self.edct = {}
        ctx = ucomponents.Context()
        for f, d in list(self.dct.items()):
            self.vdct[f], self.edct[f], self.unit = ctx.value_uncertainty_unit(d)
        self.vi = cplx_interpol(self.vdct)
        self.ei = cplx_interpol(self.edct)

    def __call__(self, f):
        val = self.vi(f)
        err = self.ei(f)
        ret = quantities.Quantity(self.unit, ucomponents.UncertainInput(val, err))
        return ret


if __name__ == '__main__':
    N = 50
    dm = 0.05
    da = 70
    data = {}
    for i in range(1, N):
        data[i] = i * dm * cmath.exp(1j * math.radians(i * da))
        print((i, data[i].real, data[i].imag))
    print()
    print()

    ci = cplx_interpol(data)
    for i in range(10, 9 * N):
        j = i * 0.1
        d = ci(j)
        print((j, d.real, d.imag))
