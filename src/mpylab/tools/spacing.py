# -*- coding: iso-8859-1 -*-
"""This is :mod:`mpylab.tools.spacing`: routines returning sequences aka `range`

   :author: Hans Georg Krauthäuser (main author)
   :copyright: All rights reserved
   :license: no licence yet
"""

from math import log, ceil, floor, pow


def logspace(start, stop, factor=1.01, endpoint=0, precision=2):
    """Evenly spaced samples on a logarithmic scale.

       Returns evenly spaced samples from *start* to *stop*.  If
       *endpoint=1* then last sample is *stop* and *factor* is adjusted.
    """
    if factor < 1 and stop > start:
        return []
    try:
        nf = log(stop / start) / log(factor)
    except ArithmeticError:
        return []
    if endpoint:
        nf = ceil(nf)
        try:
            factor = pow((stop / start), 1 / nf)
        except ArithmeticError:
            return []
    lst = [round(start * factor ** i, precision) for i in range(int(floor(nf)) + 1)]
    return lst


def logspaceN(start, stop, number, endpoint=0, precision=2):
    """Evenly spaced samples on a logarithmic scale.

       Return *number* evenly spaced samples from start to stop.  If
       *endpoint=1* then last sample is *stop* and *factor* is adjusted.
    """
    if number < 1 and stop > start:
        return []
    if endpoint:
        nf = number
    else:
        nf = number + 1
    try:
        factor = pow(stop / start, 1.0 / (nf - 1))
    except ArithmeticError:
        return []
    lst = [round(start * factor ** i, precision) for i in range(number)]
    return lst


def linspace(start, stop, step, endpoint=0, precision=2):
    """Evenly spaced samples on a linear scale.

       Return evenly spaced samples from *start* to *stop*.  If
       *endpoint=1* then last sample is *stop* and *step* is adjusted.
    """
    if step < 0 and stop > start:
        return []
    try:
        nf = (stop - start) / step + 1
    except ArithmeticError:
        return []
    if endpoint:
        nf = floor(nf)
        try:
            step = (stop - start) / float(nf - 1)
        except ArithmeticError:
            return []
    lst = [round(start + step * i, precision) for i in range(int(floor(nf)))]
    return lst


def linspaceN(start, stop, number, endpoint=0, precision=2):
    """Evenly spaced samples on a linear scale.

       Return *number* evenly spaced samples from *start* to *stop*.  If
       *endpoint=1* then last sample is *stop* and *number* is adjusted.
    """
    if number < 1 and stop > start:
        return []
    if endpoint:
        nf = number
    else:
        nf = number + 1
    try:
        step = (stop - start) / float(nf - 1)
    except ArithmeticError:
        return []
    lst = [round(start + step * i, precision) for i in range(number)]
    return lst


def logspaceTab(start, end, ftab=None, nftab=None, endpoint=True):
    if nftab is None:
        nftab = [20, 15, 10, 20, 20]
    if ftab is None:
        ftab = [1, 3, 6, 10, 100, 1000]
    freqs = []
    s = ftab[0]
    finished = False
    for i, ft in enumerate(ftab[1:]):
        e = ft
        f = logspaceN(s, e, nftab[i], endpoint=False)
        while len(f) and f[-1] > end:  # More points as we need
            f.pop()
            finished = True
        freqs.extend(f)
        if finished:
            break
        s = e
    if endpoint and end not in freqs:
        freqs.append(end)
    for i, f in enumerate(freqs):
        if f >= start:
            break
    return freqs[i:]


def frange(limit1, limit2=None, increment=1.):
    """Range function that accepts floats (and integers).
    
       Usage::

           frange(-2, 2, 0.1)
           frange(10)
           frange(10, increment = 0.5)

       The returned value is a generator.  Use list(frange) for a list.
    """
    if limit2 is None:
        limit2, limit1 = limit1, 0.
    else:
        limit1 = float(limit1)
    count = int(ceil(limit2 - limit1) / increment)
    return (limit1 + n * increment for n in range(count))


def idxset(n, m):
    """returns a list of length *n* with equidistant elem of `range(m)`
    """
    if n <= 0:
        return []
    if n >= m:
        return list(range(m))
    step = 1.0 * m / n
    return [int(round(i * step)) for i in range(n)]
