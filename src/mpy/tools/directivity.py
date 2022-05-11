# -*- coding: iso-8859-1 -*-

import math


class UnintentionalRad(object):
    twopi = 2 * math.pi
    cvacuum = 299792458

    def __init__(self, min_radius):
        self.a = min_radius

    def ka(self, f):
        return UnintentionalRad.twopi * f * self.a / UnintentionalRad.cvacuum

    def chisq2fac(self, n):
        return 0.577 + math.log(n) + 0.5 / n


class Dmax_uRad_OneCut(UnintentionalRad):
    def __init__(self, min_radius):
        super(Dmax_uRad_OneCut, self).__init__(min_radius)
        self.a = min_radius

    @staticmethod
    def n_ind(ka):
        return 4 * ka + 2

    def chisq2fac(self, n):
        return super(Dmax_uRad_OneCut, self).chisq2fac(n)

    def ka(self, f):
        return super(Dmax_uRad_OneCut, self).ka(f)

    def Dmax(self, f):
        ka = self.ka(f)
        if ka < 1:
            ka = 1
        return self.chisq2fac(self.n_ind(ka))


if __name__ == '__main__':
    pass
