# -*- coding: utf-8 -*-
"""This is :mod:`mpylab.tools.sin_fit`.

   Provides a sinus fit function

   :author: Hans Georg Krauthäuser (main author)

   :license: GPL-3 or higher
"""

from numpy import array, argmax, std, mean, pi, sin, max
from numpy.fft import fftfreq, fft
from scipy.optimize import curve_fit

def fit_sin(tt, yy):
    """
    Fit sin to the input time sequence, and return fitting
    parameters *amp*, *omega*, *phase*, *offset*, *freq*, *period* and *fitfunc*
    """
    tt = array(tt)
    yy = array(yy)
    ff = fftfreq(len(tt), (tt[1]-tt[0]))   # assume uniform spacing
    Fyy = abs(fft(yy))
    guess_freq = abs(ff[argmax(Fyy[1:])+1])   # excluding the zero frequency "peak", which is related to offset
    guess_amp = std(yy) * 2.**0.5
    guess_offset = mean(yy)
    guess = array([guess_amp, 2.*pi*guess_freq, 0., guess_offset])

    def sinfunc(t, A, w, p, c):
        return A * sin(w*t + p) + c

    popt, pcov = curve_fit(sinfunc, tt, yy, p0=guess)
    A, w, p, c = popt
    f = w/(2.*pi)
    fitfunc = lambda t: A * sin(w*t + p) + c
    return {"amp": A, "omega": w, "phase": p, "offset": c, "freq": f, "period": 1./f, "fitfunc": fitfunc, "maxcov": max(pcov), "rawres": (guess,popt,pcov)}

if __name__ == "__main__":
    import numpy as np
    from matplotlib import pyplot as plt
    t = np.linspace(-10, 10, 1000, endpoint=True)
    freq = 0.21
    phase = 1.2345
    omega = np.pi*2*freq
    amp = 1.876
    rndm = 2 * np.random.rand(len(t)) - 1
    prct = 0.8
    u = amp * (np.sin(omega*t + phase) + prct * rndm)
    dct = fit_sin(t, u)
    print(dct)
    fit = dct["fitfunc"](t)
    plt.plot(t, u)
    plt.plot(t, fit)

    plt.show()
