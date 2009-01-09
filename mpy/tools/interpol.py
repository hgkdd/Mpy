import cmath
import math
import scipy
scipy.pkgload('interpolate')
from scuq import *

def unwrap(dct, arg=None):
    """Phase unwrapping of values in dictionary dct.
    """
    if arg==None: 
        arg=_arg
    freqs=sorted(dct.keys())
    #print dct

    unwrapped=([],[],[])
    dang=0
    q=dct[freqs[0]]
    phik=arg(q)
    for k,f in enumerate(freqs[:-1]):
        #print f, ang, dang, phik
        unwrapped[0].append(f)
        unwrapped[1].append(abs(dct[f]))
        unwrapped[2].append(phik)
        try:
            q=dct[freqs[k+1]]/dct[f]
            dang=arg(q)
        except ZeroDivisionError:
            dang=0
        
        phik=phik+dang
    f=freqs[-1]
    unwrapped[0].append(f)
    unwrapped[1].append(abs(dct[f]))
    unwrapped[2].append(phik)
    # return tuple of list: f mag ang sorted fy f
    return unwrapped

def _arg(obj):
    """Return the angle of 'obj' in the complex plane (in rad).
    """
    try:
        phi=math.atan2(obj.imag,obj.real)  # complex
    except AttributeError:
        # real
        phi=0   
    return phi

class cplx_interpol(object):
    def __init__(self, dct, type=None):
        self.dct=dct
        self.unwrapped=unwrap(dct)
        _x,_y,_z=self.unwrapped
        self.magipol=scipy.interpolate.interp1d(_x,_y)
        self.phaseipol=scipy.interpolate.interp1d(_x,_z)

    def __call__(self, f):
        m=self.magipol(f)[0]
        p=self.phaseipol(f)[0]
        c=m*cmath.exp(1j*p)
        if c.imag==0:
            return c.real
        else:
            return c
        
class UQ_interpol(object):
    def __init__(self, dct, type=None):
        self.dct=dct
        self.vdct={}
        self.edct={}
        ctx=ucomponents.Context()
        for f in self.dct:
            d=self.dct[f]
            self.vdct[f],self.edct[f],self.unit=ctx.value_uncertainty_unit(d)
        self.vi=cplx_interpol(self.vdct)
        self.ei=cplx_interpol(self.edct)
        
    def __call__(self, f):
        val=self.vi(f)
        err=self.ei(f)
        ret=quantities.Quantity(self.unit, ucomponents.UncertainInput(val,err))
        return ret

if __name__ == '__main__':
    N=50
    dm=0.05
    da=70
    data={}
    for i in range(1,N):
        data[i]=i*dm*cmath.exp(1j*math.radians(i*da))
        print i, data[i].real, data[i].imag
    print
    print

    ci=cplx_interpol(data)
    for i in range(10,9*N):
        j=i*0.1
        d=ci(j)
        print j, d.real, d.imag
        
        
    
