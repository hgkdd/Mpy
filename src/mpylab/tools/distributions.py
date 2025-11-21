# -*- coding: utf-8 -*-
"""
This is :mod:`mpylab.tools.distributions`.

   Provides :class:`mpylab.tools.distributions.RayleighDist` for Rayleigh distributions.

   :author: Hans Georg Krauthäuser (main author)

   :license: GPLv3 or higher
"""


import numpy as np
from numpy.typing import ArrayLike
from scipy.interpolate import interp1d
from scipy.stats import rayleigh, chisquare, kstest


class RayleighDist:
    """
    Rayleigh distribution
    """

    def __init__(self, loc: float = 0, scale: float = 1) -> None:
        """
        Constructor. A frozen distribution object is created

        Parameters:
            - *loc*: float, optional, location parameter, shift along the x-axis, default = 0
            - *scale*: float, optional, scale parameter, spread of the distribution, default = 1
        """
        self.loc = loc
        self.scale = scale
        self.dist = rayleigh(loc=loc, scale=scale)  # make a frozen distribution object
        self.mean = self.dist.mean()   # mean
        self.std = self.dist.std()     # standard variation
        self.entropy = self.dist.entropy() # (differential) entropy of the rv
        self.median = self.dist.median()   # median
        self.variance = self.dist.var()   # variance
        self.skew, self.kurtosis = self.dist.stats(moments='sk')  # skew, kortosis
        self.mode = loc + scale

    def pdf(self, x: ArrayLike) -> object:
        """
        Rayleigh probability density function (pdf); loc and scale are given with the constructor

        Parameter:
            - *x*: array-like, support

        Return:
            - *pdf*: a scipy.stats.rayleigh.pdf object
        """
        return self.dist.pdf(x)

    def cdf(self, x: ArrayLike) -> object:
        """
        Rayleigh probability function (cdf); loc and scale are given with the constructor

        Parameter:
            - *x*: array-like, support

        Return:
            - *cdf*: a scipy.stats.rayleigh.cdf object
        """
        return self.dist.cdf(x)

    def rvs(self, size: int=1, random_state: int | None | object=None) -> ArrayLike:
        """
        Draw samples from this distribution

        Parameters:
            - *size*: number of samples to draw, default 1
            - *random_state*: random state object, default None see https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.rv_continuous.random_state.html#scipy.stats.rv_continuous.random_state
        """
        return self.dist.rvs(size=size, random_state=random_state)


def ECDF(seq: list[float]) -> object:
    """
    Calculate the Empirical Cumulated Distribution Function (ecdf) from a sequence 'seq'.

    A scipy interpolation object is returned.
    """
    N = len(seq)
    sseq = np.sort(seq)
    ecdf = np.linspace(1. / N, 1, N)
    return interp1d(sseq, ecdf, bounds_error=False)


# class Chi2Cost:
#     def __init__(self, x, y, f):
#         self.x = x[:]
#         try:
#             self.y = y[:]
#         except TypeError:   # may be an interp1d object
#             xx = np.sort(x)
#             self.y = [y(_x) for _x in xx]
#         self.xy = list(zip(self.x, self.y))
#         self.f = f
#
#     def __call__(self, par):
#         _sum = sum([(y - self.f(x, par)) ** 2 for x, y in self.xy])
#         return _sum

def fit_rayleigh(data: ArrayLike) -> tuple[float, float]:
    """
    Fit a rayleigh distribution to data

    Parameters:
        - *data*: array-like, data to fit, data are samples assumed to be rayleigh distributed

    Return:
        - *loc*, *scale*: tuple, location and scale parameters
    """
    loc, scale = rayleigh.fit(data)
    return loc, scale

def ks_test(data: ArrayLike | callable, cdf: ArrayLike | callable ) -> float:
    """
    Performs the Kolmogorov-Smirnov test for goodness of fit.

    Parameters:
        - *data*: array-like | callable, rv to test
        - *cdf*: array-like | callable, cdf to test against

    H0 = The sample is drawn from the reference distribution

    p-value is the probability of obtaining test results at least as extreme as the result actually observed, under the assumption that the null hypothesis is correct.
    A very small p-value means that such an extreme observed outcome would be very unlikely under the null hypothesis.

    small p (p<0.05, p<0.01) -> data is not drawn from cdf

    Results:
        - *p*: p-value for the test (probability that the sample is drawn from the reference distribution)
    """
    kstestresult = kstest(data, cdf)
    return kstestresult.pvalue

def chi2_test(data: ArrayLike | callable, cdf: callable) -> float:
    """
    Performs a Chisquare test for the expected counts for the reference distribution (cdf) and those from the observed distribution (data).

    Parameters:
        - *data*: array-like | callable, rv to test
        - *cdf*: array-like | callable, cdf to test against

    H0 = There are no differences between the classes in observed and expected distribution

    p-value is the probability of obtaining test results at least as extreme as the result actually observed, under the assumption that the null hypothesis is correct.
    A very small p-value means that such an extreme observed outcome would be very unlikely under the null hypothesis.

    small p (p<0.05, p<0.01) -> data is not drawn from cdf

    Results:
        - *p*: p-value for the test (probability that the sample is drawn from the reference distribution)
    """
    c, b = np.histogram(data)   # make histogram, c = counts
    ct = np.diff(cdf(b)) * np.sum(c)  # expected counts
    c2t = chisquare(c, ct, ddof=2)
    return c2t.pvalue


def test_for_rayleigh(ees: ArrayLike) -> tuple[ArrayLike, ArrayLike, object, object, float, float]:
    n_ees = len(ees)
    hist, bins = np.histogram(ees)
    low_range = bins.min()
    binsize = (bins.max() - low_range) / (bins.size - 1)
    # hist_area = sum(hist) * binsize
    # nhist = [_h / hist_area for _h in hist]
    e_cdf = ECDF(ees)
    loc, scale = rayleigh.fit(ees, floc=0)
    ray_fit = rayleigh(loc=loc, scale=scale)
    cdf_fit = ray_fit.cdf(ees)
    # calc estimates for chi2-test
    estimates = []
    _l = low_range
    for _h in bins[1:]:
        estimates.append(ray_fit.cdf(_h) - ray_fit.cdf(_l))
        _l = _h
    factor = sum(hist) / sum(estimates)
    estimates = [_e * factor for _e in estimates]
    cs, p_cs = chisquare(hist, f_exp=estimates)
    # print(p_cs)
    p_ks = ks_test(e_cdf, cdf_fit)
    # print(p_ks)
    return hist, bins, e_cdf, ray_fit, p_cs, p_ks
