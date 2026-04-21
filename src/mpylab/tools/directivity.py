# -*- coding: utf-8 -*-
"""
This is :mod:`mpylab.tools.directivity``.

   Provides the class UnintentionalRad and Dmax_uRad_OneCut
   see: https://ieeexplore.ieee.org/document/5715864

   :author: Hans Georg Krauthäuser (main author)

   :license: GPLv3 or higher
"""

import math
from numpy import euler_gamma  # Euler-Mascheroni-Constant

class UnintentionalRad():
    twopi = 2 * math.pi
    cvacuum = 299792458   # vacuum speed of light in m/s

    def __init__(self, min_radius):
        """
        Constructor: min_radius is the minimum radius of a sphere enclosing the unintentional radiator -> physical size
        """
        self.a = min_radius

    def ka(self, f):
        """
        wavevector times physical size -> electrical size a freq f: ka = 2pi f/c a = omega/c a
        """
        return UnintentionalRad.twopi * f * self.a / UnintentionalRad.cvacuum

    def chisq2fac(self, n):
        r"""
        returns \sum_{i=0}^n 1/i \aprox 0.577 + ln(n) + 1/2n
        see: https://ieeexplore.ieee.org/document/5715864
        """
        if n < 100:
            return sum(1/i for i in range(1, n+1))
        return euler_gamma + math.log(n) + 0.5 / n


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
