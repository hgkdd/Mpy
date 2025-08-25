import numpy as np
import scipy
import scipy.stats
import scipy.interpolate


class RayleighDist:
    def __init__(self):
        self.dist = scipy.stats.rayleigh

    def pdf(self, r, s):
        # s = 1.0*s
        # return self.chi.pdf(r/s)/s
        return self.dist.pdf(r, scale=s)

    def cdf(self, r, s):
        return self.dist.cdf(r, scale=s)

    def mean(self, s):
        return self.dist.mean(scale=s)

    def variance(self, s):
        return self.dist.var(scale=s)

    def mode(self, s):
        # position of the max of pdf
        # return s*self.chi.mode()  # actually, this is s
        return s

    def median(self, s):
        return self.dist.median(scale=s)

    def rv(self, s, n=1):
        return self.dist.rvs(scale=s, size=n)


def ECDF(seq):
    """
    Calculate the Empirical Cumulated Distribution Function (ecdf) from a sequence 'seq'.

    A scipy interpolation object is returned.
    """
    N = len(seq)
    sseq = np.sort(seq)
    ecdf = np.linspace(1. / N, 1, N)
    return scipy.interpolate.interp1d(sseq, ecdf, bounds_error=False)


class Chi2Cost:
    def __init__(self, x, y, f):
        self.x = x[:]
        try:
            self.y = y[:]
        except TypeError:   # may be an interp1d object
            xx = np.sort(x)
            self.y = [y(_x) for _x in xx]
        self.xy = list(zip(self.x, self.y))
        self.f = f

    def __call__(self, par):
        _sum = sum([(y - self.f(x, par)) ** 2 for x, y in self.xy])
        return _sum
