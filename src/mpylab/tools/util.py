# -*- coding: iso-8859-1 -*-
"""This is :mod:`mpylab.tools.util`: all sort of utilities. 

   :author: Hans Georg Krauthäuser (main author)
   :copyright: All rights reserved
   :license: no licence yet
"""

import fnmatch
import inspect
import math
import os
import re
import sys
import time
import traceback
import smtplib
from email.message import EmailMessage

import numpy as np
import scipy
import scipy.special
import scipy.stats
import scipy.integrate
from scipy.interpolate import interp1d
from scuq.quantities import Quantity
from scipy.optimize import root_scalar
from collections.abc import Sequence

from mpylab.tools.get_char import getch
from mpylab.tools.kbhit import kbhit

c = 2.99792458e8
mu0 = 4 * math.pi * 1e-7
eps0 = 1.0 / (mu0 * c * c)
pi = math.pi


def anykeyevent():
    """
    Detects a key or function key pressed and returns its ascii or scancode.
    """
    if kbhit():
        a = ord(getch())
        # print "anykeyevent:", a
        if a == 0 or a == 224:
            b = ord(getch())
            x = a + (b * 256)
            return x
        else:
            return a
    # print "anykeyevent:", None
    return None


def keypress():
    """Waits for the user to press a key. Returns the ascii code 
       for the key pressed or zero for a function key pressed.
    """
    while 1:
        a = ord(getch())  # get first byte of keyscan code
        if a == 0 or a == 224:  # is it a function key?
            getch()  # discard second byte of key scan code
            return 0  # return 0
        else:
            return a  # else return ascii code
    return None


def funkeypress():
    """
    Waits for the user to press any key including function keys. Returns 
    the ascii code for the key or the scancode for the function key.
    """
    while 1:
        a = ord(getch())  # get first byte of keyscan code
        if a == 0 or a == 224:  # is it a function key?
            b = ord(getch())  # get next byte of key scan code
            x = a + (b * 256)  # cook it.
            return x  # return cooked scancode
        else:
            return a  # else return ascii code
    return None


def getIndex(val, tab):
    """ 
    returns the index so that val is between tab[index-1], tab[index].
    tab is a sorted list
    """
    if len(tab) == 0:
        return -1
    incr = tab[-1] > tab[0]  # increasing
    if incr:
        # list of all items in tab <= val
        l = [t for t in tab if val >= t]
        # l=filter(lambda t: val >= t, tab)
    else:
        # list of all items in tab >= val
        l = [t for t in tab if val <= t]
        # l=filter(lambda t: val <= t, tab)
    if not len(l):
        index = 0
    else:
        try:
            index = tab.index(l[-1]) + 1
        except AttributeError:
            index = np.where(tab == l[-1])[0][0] + 1

    try:
        tab[index]
    except KeyError:
        index = None
    return index


def combinations(L):
    N = len(L)
    if N == 0:
        return []
    elif N == 1:
        return [L[0][i:i + 1] for i in range(0, len(L[0]))]
    else:
        return [L[0][i:i + 1] + subcomb for i in range(0, len(L[0])) for subcomb in combinations(L[1:])]


def LookForUserInterrupt():
    # look for user interupt
    if anykeyevent():
        print("Execution interrupted by user.")
        print("Press any key when ready to measure or 'q' to quit.")
        if keypress() in list(map(ord, 'qQ')):
            return True
    return None


def secant_solve(f, x1, x2, ftol, xtol):
    sol = root_scalar(f, method='secant', x0=x1, x1=x2, rtol=ftol, xtol=xtol)
    return sol.root
    # f1 = f(x1)
    # if abs(f1) <= ftol:
    #     return x1  # already effectively zero
    # f2 = f(x2)
    # if abs(f2) <= ftol:
    #     return x2  # already effectively zero
    # while abs(x2 - x1) > xtol:
    #     slope = (f2 - f1) / (x2 - x1)
    #     if slope == 0:
    #         return None
    #     #      sys.stderr.write("Division by 0 due to vanishing slope - exit!\n")
    #     #      sys.exit(1)
    #     x3 = x2 - f2 / slope  # the new approximate zero
    #     f3 = f(x3)  # and its function value
    #     if abs(f3) <= ftol:
    #         break
    #     x1, f1 = x2, f2  # copy x2,f2 to x1,f1
    #     x2, f2 = x3, f3  # copy x3,f3 to x2,f2
    # return x3


def mean(x, zero=0.0):
    mu = sum(x, zero)
    return mu / len(x)


def interactive(obj=None, banner=None):
    import code

    if obj is None:
        ns = vars()
    else:
        ns = vars(obj)

    code.interact(banner=banner, local=ns)


def tstamp():
    return time.strftime('%c (%Z)')


class OutputError:
    def __init__(self):
        self.clear()

    def write(self, obj):
        self.values.append(obj)

    def readlines(self, lines=None):
        if (lines is None) or (lines > len(self.values)):
            lines = len(self.values)
        ret = self.values[:lines]
        return ret

    def readline(self):
        if self.__lcount__ > len(self.values):
            return []
        self.__lcount__ += 1
        return self.values[self.__lcount__ - 1]

    def seek(self, count=0):
        count = min(count, len(self.values))
        self.__lcount__ = count

    def clear(self):
        self.values = []
        self.__lcount__ = 0


def LogError(Messenger):
    out = OutputError()
    (ErrorType, ErrorValue, ErrorTB) = sys.exc_info()
    traceback.print_exc(ErrorTB, out)
    error = out.readlines()
    for err in error:
        err = err.replace('\n', '; ')
    err_msg = "%s ***Error: %s" % (tstamp(), ''.join(error))
    Messenger(msg=err_msg, but=[])


def removefrom(obj, pat):
    if re.search(pat, str(type(obj))) is not None:
        # the obj itself matchs the pattern -> remove it
        del obj
        return

    if type(obj) in (str,):
        return

    # a dict?
    try:
        for k, v in list(obj.items()):
            if re.search(pat, str(type(v))) is not None:
                del obj[k]
            else:
                removefrom(v, pat)
        return
    except:
        pass
    # a sequence
    try:
        for o in obj:
            removefrom(o, pat)
        return
    except:
        pass
    return


def issequence(a):
    # return issequence(a, Sequence) and not isinstance(a, str)
    return hasattr(a, '__iter__') and not isinstance(a, str)


def flatten(a):
    if not issequence(a):
        return [a]  # be sure to return a list
    if len(a) == 0:
        return []
    return flatten(a[0]) + flatten(a[1:])


def send_email(to=None, fr=None, subj='a message from mpylab.util', msg=''):
    if not (to and fr):
        return
    m = EmailMessage()
    m.set_content(msg)

    msg['Subject'] = subj
    msg['From'] = fr
    msg['To'] = to

    try:
        # Send the message via our own SMTP server.
        s = smtplib.SMTP('localhost')
        s.send_message(msg)
        s.quit()
    except:
        pass


def get_var_from_nearest_outerframe(varstr):
    __frame = inspect.currentframe()
    __outerframes = inspect.getouterframes(__frame)
    var = None
    for of in __outerframes:
        # print "outerframe is:"
        # print of
        for name, value in list(of[0].f_locals.items()) + list(of[0].f_globals.items()):
            # look for the name
            if name == varstr:
                # print "found name %s"%varstr
                # print "value:", value
                var = value
                break
            # perhaps its in a dictionary
            try:
                var = value[varstr]
                # print "found key %s in dict with name %s"%(varstr,name)
                # print "value:", var
                break
            except (KeyError, TypeError, AttributeError, IndexError, ValueError):
                continue
        if var:
            # print "got it!"
            break
    del __outerframes
    del __frame
    if not var:
        # print "not found!"
        pass
    return var


def map2singlechar(i):
    tup = tuple("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz")
    try:
        return tup[i]
    except IndexError:
        return str(i)


def format_block(block, nlspaces=0):
    """Format the given block of text, trimming leading/trailing
    empty lines and any leading whitespace that is common to all lines.
    The purpose is to let us list a code block as a multiline,
    triple-quoted Python string, taking care of
    indentation concerns."""

    import re

    # separate block into lines
    lines = str(block).split('\n')

    # remove leading/trailing empty lines
    while lines and not lines[0]:
        del lines[0]
    while lines and not lines[-1]:
        del lines[-1]

    # look at first line to see how much indentation to trim
    ws = re.match(r'\s*', lines[0]).group(0)
    if ws:
        lines = [x.replace(ws, '', 1) for x in lines]

    # remove leading/trailing blank lines (after leading ws removal)
    # we do this again in case there were pure-whitespace lines
    while lines and not lines[0]:
        del lines[0]
    while lines and not lines[-1]:
        del lines[-1]

    # account for user-specified leading spaces
    flines = ['%s%s' % (' ' * nlspaces, line) for line in lines]

    return '\n'.join(flines) + '\n'


def gmax_oats(f, rstep=None, s=10, hg=0.8, RH=(1, 4)):
    """Compute the geometry factor g_max for horizontal and vertical polarization for a dipole over a plane, 
       perfectly conducting ground (OATS) according to equation A.7 of IEC 61000-4-20.

       Parameters:
       
          - *f*: frequency in meters
          - *rstep*: the step width of the hight scan used to calculate the max. If *rstep* is `None`, a value 
            of a tenth of the wavelength ist used.
          - *s*: Distance from the EUT in meters
          - *hg*: height over ground plane in meters
          - *RH*: range of the hight scan in meters

       The function returns dictionary with keys 'h' and 'v' containing the g_max factors (as floats, unit is 1/m).
    """
    s2 = s * s
    c0 = 2.99792458e8
    k0 = (2 * math.pi * f / c0)
    if rstep is None:
        rstep = c0 / f * 0.1  # lambda/10
    rh = RH[0]
    gmaxh = 0.0
    gmaxv = 0.0
    while rh <= RH[1]:
        r1 = math.sqrt(s2 + (rh - hg) ** 2)
        r2 = math.sqrt(s2 + (rh + hg) ** 2)
        r12 = r1 * r1
        r22 = r2 * r2
        r13 = r12 * r1
        r23 = r22 * r2
        r16 = r13 * r13
        r26 = r23 * r23
        gh = 1.0 / (r1 * r2) * math.sqrt(r12 + r22 + 2 * r1 * r2 * math.cos(k0 * (r2 - r1)))
        gv = s2 / (r13 * r23) * math.sqrt(r16 + r26 + 2 * r13 * r23 * math.cos(k0 * (r2 - r1)))
        gmaxh = max(gmaxh, gh)
        gmaxv = max(gmaxv, gv)
        rh += rstep
    return {'h': gmaxh, 'v': gmaxv}


def gmax_fs(f, rstep=None, s=10, hg=0.8, RH=(0.8, 0.8)):
    """Compute the geometry factor g_max for horizontal and vertical polarization for a dipole in free space (FAR).

       Parameters:
       
          - *f*: frequency in meters (not used in the function)
          - *rstep*: the step width of the hight scan used to calculate the max. (not used in the function) 
          - *s*: Distance from the EUT in meters
          - *hg*: height over ground plane in meters
          - *RH*: range of the hight scan in meters. The source is assumed to be at the lower end of this range.

       The function returns dictionary with keys 'h' and 'v' containing the g_max factors (as floats, unit is 1/m).
    """
    r = math.sqrt(s * s + (RH[0] - hg) ** 2)
    ret = 1.0 / r
    return {'h': ret, 'v': ret}


def isiterable(obj):
    try:
        iter(obj)
        return True
    except TypeError:
        return False


def extrap1d(interpolator):
    """
    Interpolation with linear exprapolation
    """
    xs = interpolator.x
    ys = interpolator.y

    def pointwise(x):
        if x < xs[0]:
            return min(ys[0], ys[0] + (x - xs[0]) * (ys[1] - ys[0]) / (xs[1] - xs[0]))
        elif x > xs[-1]:
            return max(ys[-1], ys[-1] + (x - xs[-1]) * (ys[-1] - ys[-2]) / (xs[-1] - xs[-2]))
        else:
            return interpolator(x)

    def ufunclike(xs):
        if not hasattr(xs, '__iter__'):
            xs = [xs]
        return np.array(list(map(pointwise, np.array(xs))))

    return ufunclike


def locate(pattern, paths=None):
    '''Locate all files matching supplied filename pattern in and below
    supplied root directory.'''
    # print pattern, paths
    if paths is None:
        paths = [os.getcwd()]
    for root in paths:
        for path, dirs, files in os.walk(os.path.abspath(root)):
            for filename in fnmatch.filter(files, pattern):
                yield os.path.join(path, filename)


def CalcSigma(lst, av=None):
    n = len(lst)
    try:
        unit = lst[0]._unit
        zero = Quantity(unit, 0.0)
    except AttributeError:
        zero = 0.0

    if av is None:
        av = sum(lst, zero) / float(n)
    s2 = sum([(x - av) * (x - av) for x in lst], zero * zero) / float(n - 1)
    try:
        s = s2.sqrt()
    except AttributeError:
        s = math.sqrt(s2)
    return s


def InterpolateMResults(y, x, interpolation=None):
    if interpolation is None:
        interpolation = 'linxliny'
    if 'logx' in interpolation:
        x = np.log10(x)
    if 'logy' in interpolation:
        y = np.log10(y)
    inter = interp1d(x, y)
    return inter


def MResult_Interpol(dct, interpolation):
    x = sorted(dct.keys())
    y = [dct[xi] for xi in x]
    return InterpolateMResults(y, x, interpolation)


def CalcPsi(n, rho, eps=0.01):
    def calc_psi_int(r, n, rho):
        def kern(x):
            return x ** (n - 2) / ((1 - rho * r * x) ** (n - 1) * math.sqrt(1 - x * x))

        fac = (n - 2) / math.pi * (1 - rho ** 2) ** (0.5 * (n - 1)) * (1 - r ** 2) ** (0.5 * (n - 4))
        return np.integrate.quad(kern, 0, 1)[0] * fac

    def calc_psi_exact(r, n, rho):
        ga = scipy.special.gamma
        tmp = ga(n - 0.5)
        if np.isfinite(tmp):
            gafac = ga(n - 1) / tmp
        else:
            gafac = 1.0 / math.sqrt(n - 0.5) * (1 + 3.0 / (8 * n - 4))
        psi = (n - 2) / math.sqrt(2 * math.pi) * gafac \
              * math.pow(1 - r * r, 0.5 * (n - 4)) * math.pow(1 - rho * rho, 0.5 * (n - 1)) \
              * math.pow(1 - rho * r, 1.5 - n) * scipy.special.hyp2f1(0.5, 0.5, n - 0.5, 0.5 * (1 + rho * r))
        return psi

    def calc_psi_norm_transform(r, n, rho):
        def atanh(x):
            if x < -0.99:
                return -1e300
            elif x > 0.99:
                return 1e300
            else:
                return 0.5 * math.log((1 + x) / (1 - x))

        s = math.sqrt(1.0 / (n - 3))
        mu = atanh(rho)
        z = atanh(r)
        psi = scipy.stats.norm.pdf(z, mu, s)
        return psi

    def calc_psi(r, n, rho):
        # return calc_psi_int(r,n,rho)
        try:
            return calc_psi_exact(r, n, rho)
        except OverflowError:
            return calc_psi_norm_transform(r, n, rho)

    psi = []
    psi2 = []
    r = []
    cpsi = []
    for i in range(int(2.0 / eps + 1)):
        r.append(round(-1.0 + i * eps, 3))
        psi.append(calc_psi(r[i], n, rho))
        cpsi.append(scipy.integrate.quad(calc_psi, -1, r[-1], (n, rho))[0])
    # tmp = scipy.integrate.cumtrapz(psi,r).tolist()
    # cpsi.extend(tmp)
    factor = 1.0 / cpsi[-1]
    # print factor
    psi = [x * factor for x in psi]
    cpsi = [x * factor for x in cpsi]
    # print r[-1], cpsi[-1]
    return r, psi, cpsi


def CalcRho0(r, cpsi, alpha):
    if not hasattr(alpha, 'sort'):
        alpha = [alpha]
    alpha.sort()
    f = interp1d(cpsi, r)  # the inverse of the cum integral
    dct = {}
    for a in alpha:
        rho0 = f(a)
        dct[a] = rho0.tolist()[0]
    return dct
