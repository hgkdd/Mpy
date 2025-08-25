import numpy
from collections.abc import Iterable


def isiterable(obj):
    try:
        _ = iter(obj)
        return True
    except TypeError:
        return False
    # return isinstance(obj, Iterable)


def mean(x):  # , zero=0.0):
    # will work with more data types then statistics.mean ...
    mu = sum(x)  # , zero)
    return mu / len(x)


def autocorr(x, lag=None, cyclic=True):
    if not isiterable(x):
        return None
    if lag is None:
        lag = len(x)
    #    if isinstance(x[0], Quantity):
    #        unit=x[0].unit
    #        z = Quantity(unit, 0.0)
    #        one = Quantity(unit, 1.0)
    #    else:
    #        z = 0.0
    #        one = 1.0
    r = [1.0]
    # calc mean
    mu = mean(x)
    # xi-mu for all elements
    x = [xi - mu for xi in x]
    var = sum([xi ** 2 for xi in x])
    # dublicate
    y = x[:]
    for l in range(1, lag):
        # remove lag elements from the beginning of y
        elem = y.pop(0)
        # append removed items to the end if cyclic
        if cyclic:
            y.append(elem)
        else:
            # make x the same length as y
            x.pop()
        # calc r
        try:
            ri = sum([xi * yi for xi, yi in zip(x, y)]) / var
        except ZeroDivisionError:
            ri = 1.0
        r.append(ri)
    return r


def autocorr2(x, lag=None, cyclic=True):
    if not isiterable(x):
        return None
    if lag is None:
        lag = len(x)
    #    if hasattr(x[0],'get_v'): # is MResult or CMresult
    #        z = umddevice.UMDMResult(0.0, umddevice.UMD_dimensionless)
    #        one = umddevice.UMDMResult(1.0, umddevice.UMD_dimensionless)
    #        for _x in x:
    #            _x.unit = umddevice.UMD_dimensionless
    #    else:
    #        z = 0.0
    #        one = 1.0
    r = [1.0]
    # calc mean
    mu = sum(x) / len(x)
    # xi-mu for all elements
    # x = map (lambda xi: xi-mu, x)
    # var = sum(map(lambda xi:xi*xi, x), z)
    # var = scipy.stats.cov(x)
    var = numpy.cov(x)
    # dublicate
    y = x[:]
    for l in range(1, lag):
        # remove lag elements from the beginning of y
        elem = y.pop(0)
        # append removed items to the end if cyclic
        if cyclic:
            y.append(elem)
        else:
            # make x the same length as y
            x.pop()
        # calc r
        try:
            ri = sum([xi * yi for xi, yi in zip(x, y)]) / var
        except ZeroDivisionError:
            ri = 1.0
        r.append(ri)
    return r
