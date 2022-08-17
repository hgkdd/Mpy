import numpy
import scipy
import scipy.interpolate
import scipy.optimize
import scipy.stats
from scuq.quantities import Quantity
from scuq.si import WATT, METER
from scuq.ucomponents import Context

from mpy.env import Measure
from mpy.tools import util, mgraph, spacing, distributions, correlation
from mpy.tools.aunits import *

from numpy.random import default_rng

import matplotlib.pyplot as plt

rng = default_rng()
ray = distributions.RayleighDist()


if __name__ == "__main__":
    print(util.tstamp() + " Calculating statistic " , [])
    ees24 = {}  # 24 = 8 positions x 3 axis
    pees = [1,2,3,4,5,6,7,8]
    tpos = list(range(360))[::10]
    for p in pees:
        print(util.tstamp() + " p = %d" % p, [])
        #s_f[p] = {}
        for k in [0,1,2]:   # x,y,z
            print(util.tstamp() + " k = %d" % k, [])
            # now, we have to redure the data set according the result of the autocorr evaluation
            ntotal = len(tpos)
            n_ind = ntotal  # fall back
            # use autocor information
            posidx = spacing.idxset(int(n_ind), len(tpos))
            ees = []
            for i, t in enumerate(tpos):
                evalue = rng.rayleigh(scale=10, size=None)
                # evalue = efields[f][str(t)][p][0]['value'][k]  # .convert(umddevice.UMD_Voverm).get_v()
                ees24.setdefault(str(t), []).append(evalue)
                if i in posidx:
                    ees.append(evalue)
            ees.sort()  # values only, no ebars, unit is V/m
            n_ees = len(ees)
            hist, bins = numpy.histogram(ees)
            low_range = bins.min()
            binsize = (bins.max() - low_range) / (bins.size - 1)
            hist_area = sum(hist) * binsize
            nhist = [_h / hist_area for _h in hist]
            e_cdf = distributions.ECDF(ees)
            loc, scale = scipy.stats.rayleigh.fit(ees,floc=0)
            ray_fit = scipy.stats.rayleigh(loc=loc, scale=scale)
            cdf_fit = ray_fit.cdf(ees)
            # calc estimates for chi2-test
            estimates = []
            _l = low_range
            for _h in bins[1:]:
                estimates.append(ray_fit.cdf(_h) - ray_fit.cdf(_l))
                _l = _h
            factor = sum(hist) / sum(estimates)
            estimates = [_e*factor for _e in estimates]
            cs, p_cs = scipy.stats.chisquare(hist, f_exp=estimates)
            # ss['p-chisquare'] = p_cs
            print(p_cs)
            ks, p_ks = scipy.stats.ks_2samp(e_cdf(ees), cdf_fit)
            # ss['p-KS'] = p_ks
            print(p_ks)
            xx = range(30)
            plt.plot(sorted(ees), [e_cdf(_e) for _e in sorted(ees)])
            plt.plot(xx, ray_fit.cdf(xx))
            plt.plot(ees, cdf_fit)
            plt.show()
            plt.hist(ees, bins=bins, density=True)
            plt.plot(xx, ray_fit.pdf(xx))
            plt.show()
    print(util.tstamp() + " ...done", [])
