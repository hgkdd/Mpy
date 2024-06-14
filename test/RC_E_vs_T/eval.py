import sys
import random
from itertools import combinations
import pickle as pickle
import matplotlib.pyplot as pl
import numpy as np
import scipy as sp
from scuq import *
from scipy.interpolate import interp1d
import scipy.stats as stats


def random_combination(iterable, r):
    "Random selection from itertools.combinations(iterable, r)"
    pool = tuple(iterable)
    n = len(pool)
    indices = sorted(random.sample(list(range(n)), r))
    return tuple(pool[i] for i in indices)


def ECDF(seq):
    """
    Calculate the Empirical Cumuated Distribution Function (ecdf) from a sequence 'seq'.

    A scipy interpolation object is returned.
    """
    N = len(seq)
    sseq = sp.sort(seq)
    ecdf = sp.linspace(1. / N, 1, N)
    return interp1d(sseq, ecdf, bounds_error=False)


class SAMPLES(object):
    def __init__(self, dct):
        self.dct = dct
        self.freqs = sorted(dct.keys())
        tpos = sorted(dct[self.freqs[0]].keys())

        completed_tp = set(tpos)
        for f in self.freqs:
            t = set([a for a in list(dct[f].keys()) if dct[f][a] != None])
            completed_tp = completed_tp.intersection(t)
        self.ctp = sorted(list(completed_tp))
        self.Ntp = len(self.ctp)
        self.Nfreq = len(self.freqs)
        self.Ncomponents = len(dct[self.freqs[0]][self.ctp[0]])

    def average_over_tp(self, tpos, freqs, normalize=True):
        # initialize a list of arrays for the averaged samples
        components = [sp.zeros(len(freqs)) for _ in range(self.Ncomponents)]
        for tp in tpos:
            for i, c in enumerate(components):
                c = c + sp.array([self.dct[f][tp][i].get_expectation_value_as_float() for f in freqs])
        components = [c / float(self.Ntp) for c in components]
        if normalize:
            components = [c / np.mean(c) for c in components]
        return components

    def ecdf(self, tpos, freqs, normalize=True):
        allsamples = [[] for _ in range(self.Ncomponents)]
        for f in freqs:
            for tp in tpos:
                for i, sa in enumerate(allsamples):
                    sa.append(self.dct[f][tp][i].get_expectation_value_as_float())
        for i, sa in enumerate(allsamples):
            sa = np.array(sa)
            if normalize:
                # print np.mean(sa)
                sa = sa / np.mean(sa)
            allsamples[i] = sa

        ecdfs = []
        for sa in allsamples:
            ecdfs.append(ECDF(sa))
        return ecdfs


if __name__ == '__main__':
    import matplotlib.pyplot as pl

    infile = sys.argv[1]
    dct = pickle.load(open(infile, 'rb'))

    ray = stats.rayleigh(loc=0, scale=1)

    S = SAMPLES(dct)
    enorm = np.linspace(0, 3, 100)

    ecdfs_all = S.ecdf(S.ctp, S.freqs, normalize=True)
    for i in range(S.Ncomponents):
        pl.plot(enorm, ecdfs_all[i](enorm), linewidth=3)
    ecdfs_t0 = S.ecdf((S.ctp[0],), S.freqs, normalize=True)
    for i in range(S.Ncomponents):
        pl.plot(enorm, ecdfs_t0[i](enorm), '--')
    ecdfs_f0 = S.ecdf(S.ctp, (S.freqs[0],), normalize=True)
    for i in range(S.Ncomponents):
        pl.plot(enorm, ecdfs_f0[i](enorm))
    pl.plot(enorm, ray.cdf(enorm), linewidth=5)

    pl.show()

# def mean_samples (dct, tpos, normalize=True):
# freqs = sorted(dct.keys())
# Nfreq=len(freqs)
# x=sp.zeros(Nfreq)
# y=sp.zeros(Nfreq)
# z=sp.zeros(Nfreq)
# for tp in tpos:
# x=x+sp.array([dct[f][tp][0].get_expectation_value_as_float() for f in freqs])
# y=y+sp.array([dct[f][tp][1].get_expectation_value_as_float() for f in freqs])
# z=z+sp.array([dct[f][tp][2].get_expectation_value_as_float() for f in freqs])
# x=x/float(len(tpos))
# y=y/float(len(tpos))
# z=z/float(len(tpos))
# if normalize:
# x=x/np.mean(x)
# y=y/np.mean(y)
# z=z/np.mean(z)
# return x,y,z


# def var_vs_offset (dct):
# varx=[]
# vary=[]
# varz=[]
# for other in ctp:
# x,y,z = mean_samples(dct, (0,other))
# varx.append(np.var(x))
# vary.append(np.var(y))
# varz.append(np.var(z))
# pl.plot(ctp, varx/varx1)
# pl.plot(ctp, vary/vary1)
# pl.plot(ctp, varz/varz1)
# pl.grid()

# def get_tpos (dct):    
# pass

# if __name__ == '__main__':
# infile = sys.argv[1]
# dct=pickle.load(open(infile, 'rb'))

# freqs = sorted(dct.keys())
# tpos = sorted(dct[freqs[0]].keys())

# completed_tp=set(tpos)
# for f in freqs:
# t=set([a for a in dct[f].keys() if dct[f][a] != None])
# completed_tp=completed_tp.intersection(t)
# ctp=sorted(list(completed_tp))
# Ntp=len(completed_tp)
# print Ntp
# print completed_tp
# Nfreq=len(freqs)

# ray=stats.rayleigh(loc=0.0, scale=1)
# x1,y1,z1=mean_samples(dct, (0,))
# varx1=np.var(x1)
# vary1=np.var(y1)
# varz1=np.var(z1)
# xN,yN,zN=mean_samples(dct, completed_tp)
# varxN=np.var(xN)
# varyN=np.var(yN)
# varzN=np.var(zN)
# print varx1/varxN, vary1/varyN, vary1/varyN

# N=10
# varxE=varx1/N
# varyE=vary1/N
# varzE=varz1/N
# zielx=1e300
# ziely=1e300
# zielz=1e300
# zielA=1e300
# var=np.var
# if False:
# while True: #for i in range(10000):
# for comb in combinations(ctp, N):
# comb=random_combination(ctp, N)
# x,y,z = mean_samples(dct, comb)
# varx.append(np.var(x))
# vary.append(np.var(y))
# varz.append(np.var(z))
# zx=abs(var(x)-varxE)
# zy=abs(var(y)-varyE)
# zz=abs(var(z)-varzE)
# zA=zx+zy+zz
# if zx < zielx:
# zielx=zx
# bestx = comb
# fl=True
# if zy < ziely:
# ziely=zy
# besty = comb
# fl=True
# if zz < zielz:
# zielz=zz
# bestz = comb
# fl=True
# if zA < zielA:
# zielA=zA
# bestA = comb
# fl=True
# if fl:
# print bestx, besty, bestz, bestA
# fl=False

# if True:
# varx=[]
# vary=[]
# varz=[]
# for other in ctp:
# x,y,z = mean_samples(dct, (other,), normalize=False)
# varx.append(np.mean(x))
# vary.append(np.mean(y))
# varz.append(np.mean(z))
# x1,y1,z1=mean_samples(dct, (200,))
# varx1=np.var(x1)
# vary1=np.var(y1)
# varz1=np.var(z1)

# pl.plot(ctp, varx/varx1)
# pl.plot(ctp, vary/vary1)
# pl.plot(ctp, varz/varz1)
# pl.plot(ctp, varx)
# pl.plot(ctp, vary)
# pl.plot(ctp, varz)
# pl.grid()
# if False:
# x,y,z = mean_samples(dct, ctp)
# ecdfx = ECDF(x)
# ecdfy = ECDF(y)
# ecdfz = ECDF(z)
# ex = sp.linspace(0, 2, 100)
# pl.grid()
# pl.plot(ex, ecdfx(ex))
# pl.plot(ex, ecdfy(ex))
# pl.plot(ex, ecdfz(ex))
# pl.plot(ex, ray.cdf(ex))
# gau=stats.norm(loc=1.0, scale=np.sqrt(1./8))
# pl.plot(ex, gau.cdf(ex))
# pl.plot(range(Nfreq), y)
# pl.plot(range(Nfreq), z)
# pl.show()
