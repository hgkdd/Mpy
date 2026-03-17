# -*- coding: utf-8 -*-
"""
This is :mod:`mpylab.tools.statistic`.

   :author: Hans Georg Krauthäuser (main author)

   :license: GPLv3 or higher
"""
import statistics
import numpy
from collections.abc import MutableSequence, Sequence
from itertools import chain

from scuq import qexceptions


def summation(x):
    """
    A scuq.Quantity aware summation function.

    Parameter:
        - *x*: a sequence

    Returns:
        The sum of elements in *x*
    """
    return sum(x[1:], start=x[0])  # we use first element as 'zero' and add only rest

def mean(x):    # , zero=0.0):
    """
    Compute the mean value of an iterable (scuq.Quantity aware).
    """
    mu = summation(x)
    return mu / len(x)

def variance(x):
    """
    Compute the variance of an iterable (scuq.Quantity aware).
    """
    n = len(x)
    if n < 2:  # variace undefined
        raise RuntimeError("Not enough data to compute variance.")
    mu = mean(x)
    var = summation([(xi-mu)**2 for xi in x]) / (n - 1)
    return var

def stddev(x):
    """
    Compute the standard deviation of an iterable (scuq.Quantity aware).
    """
    v = variance(x)
    return numpy.sqrt(v)

def covariance(x,y):
    """
    Compute the covariance of two iterable (scuq.Quantity aware).
    """
    n = len(x)
    m = len(y)
    if n != m:
        raise RuntimeError("Sequences shall have same length to compute covariance.")
    if n < 2:  # covariance undefined
        raise RuntimeError("Not enough data to compute covariance.")
    mux = mean(x)
    muy = mean(y)
    covar = summation([(xi-mux)*(yi-muy) for xi,yi in zip(x,y)]) / (n - 1)
    return covar

def correlation(x, y):
    """
    Compute the correlation of two iterable (scuq.Quantity aware).
    """
    covar = covariance(x,y)
    varx = variance(x)
    vary = variance(y)
    r = covar / numpy.sqrt(varx * vary)
    return r

def autocorrelation(x, maxlag=None, cyclic=True):
    """
    Compute the autocorrelation function of an iterable (scuq.Quantity aware).
    """
    if not isinstance(x, MutableSequence):
        return None
    n = len(x)
    if maxlag is None:
        maxlag = n
    xx = list(chain(x, x))  # this is to ensure cyclic behaviour
    result = []
    for i in range(maxlag + 1):
        if cyclic:
            # r = numpy.corrcoef(x, xx[i:i+lag])[0, 1]
            r = correlation(x, xx[i:i + maxlag])
        else:
            if i >= maxlag-1:
                break
            # r = numpy.corrcoef(x[:n-i], x[i:])[0, 1]
            r = correlation(x[:n-i], x[i:])
        result.append(r)
    return result

def linstat_dB(dbvals, fac=10):
    """
    Input: dbvals sequence of dB-scaled values
    fac: float, defaults to 10; sometimes 20 may be used

    Output: dB-scaled lin-average of the input sequence, upper_std, lower_std

    Example: linav_dB([0,-10]) -> -2.5963, 3.339, 445.9, linav_dB([0,-10], fac=20) -> -3.633, 4.78, 11.52
    """
    vals = [v/fac for v in dbvals]
    linmean = mean(numpy.power(10., vals))
    linstd = stddev(numpy.power(10., vals))
    upper = linmean + linstd
    lower = linmean - linstd
    lower = max(numpy.nextafter(numpy.float32(0), numpy.float32(1)), lower)   # values below zero cannot be convertet to dB
    mean_dB = fac * numpy.log10(linmean)
    upper_dB = fac * numpy.log10(upper)
    lower_dB = fac * numpy.log10(lower)
    upper_std = upper_dB - mean_dB
    lower_std = mean_dB - lower_dB
    return mean_dB, upper_std, lower_std


def linstat_lin(linvals):
    """
    Input: sequence of lin-scaled values
    Output: lin-scaled lin-average and lin-standart deviation of the input sequence

    Example: linstat_lin([0,-10]) -> -5, 7.07
    """
    linmean = mean(linvals)
    linstd = stddev(linvals)
    #linmean = statistics.mean(linvals)
    #linstd = statistics.stdev(linvals)
    return linmean, linstd


if __name__ == "__main__":
    from scuq.quantities import Quantity
    from scuq.ucomponents import UncertainInput
    from scuq.si import VOLT
    x = [1, 2, 3, 4, 5]

    qx = [Quantity(VOLT, UncertainInput(_x, _x*0.1)) for _x in x]

    for cy in [True, False]:
        print(f'Cyclic: {cy}:')
        print(f'autocorrelation (number): {autocorrelation(x, cyclic=cy)}')
        print(f'autocorrelation (Quantity): {autocorrelation(qx, cyclic=cy)}')

    print(linstat_lin([0, -10]))
    print(linstat_dB([0, -10]))
    print(linstat_dB([0, -10], fac=20))
