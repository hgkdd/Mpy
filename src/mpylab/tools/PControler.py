import numpy
import scipy.interpolate
import scipy.stats


def extrap1d(interpolator):
    xs = interpolator.x
    ys = interpolator.y

    def pointwise(x):
        if x < xs[0]:
            return min(ys[0], ys[0] + (x - xs[0]) * (ys[1] - ys[0]) / (xs[1] - xs[0]))
        elif x > xs[-1]:
            return max(ys[-1], ys[-1] + (x - xs[-1]) * (ys[-1] - ys[-2]) / (xs[-1] - xs[-2]))
        else:
            return interpolator(x)

    def ufunclike(xs):
        if not hasattr(xs, '__iter__'):
            xs = [xs]
        return numpy.array(list(map(pointwise, numpy.array(xs))))

    return ufunclike


class Rapp(object):
    def __init__(self, g, Ps, S, PinMax=1e-3, noise_loc=1.0, noise_sc=0.5):
        self.g = g
        self.Ps = Ps
        self.S = S
        self.S2 = 2 * S
        self.PinMax = PinMax
        self.noise = scipy.stats.norm(loc=noise_loc, scale=noise_sc)

    def Pout(self, Pin):
        u = self.g * Pin
        S2 = self.S2
        Po = u / (1 + (u / self.Ps) ** S2) ** (1. / S2)
        try:
            N = self.noise.rvs(len(Po))
        except TypeError:
            N = self.noise.rvs()
        return numpy.maximum(0, Po + N)


class SG(object):
    def __init__(self):
        pass

    def SetLevel(self, lv):
        print(("SG:", lv))


class Leveler(object):
    def __init__(self, sg, amp, pin=None):
        """
        sg: object providing sg.SetLevel(lv) lv: float
        amp: object providing amp.Pout(pin); amp.PinMax
        """
        self.sg = sg
        self.amp = amp
        self.Out = amp.Pout
        self.samples = {}
        if pin is None:
            pin = [1e-7, 1e-6]
        self.add_samples(pin)
        self.update_interpol()

    def add_samples(self, pin):
        if not hasattr(pin, '__iter__'):
            pin = [pin]
        for pi in pin:
            if pi > self.amp.PinMax:
                continue
            self.sg.SetLevel(pi)
            self.samples[pi] = self.Out(pi)
        self.update_interpol()

    def update_interpol(self):
        x = sorted(self.samples)
        y = [self.samples[xi] for xi in x]
        self.interp = scipy.interpolate.interp1d(x, y)
        self.extrap = extrap1d(self.interp)
        self.i_interp = scipy.interpolate.interp1d(y, x)
        self.i_extrap = extrap1d(self.i_interp)

    def adjust_level(self, soll, maxiter=10, relerr=0.01):
        self.add_samples(soll / self.amp.g)
        self.x = []
        self.y = []
        for i in range(maxiter):
            pin = min(self.i_extrap(soll)[0], self.amp.PinMax)
            self.add_samples(pin)
            pout = self.samples[pin]
            re = abs(pout - soll) / soll
            self.x.append(pin)
            self.y.append(pout)
            print((i, pin, pout, soll, re))
            if re <= relerr:
                break
            if (pin == self.amp.PinMax) and (pout <= soll):
                break
        return pin, pout


if __name__ == '__main__':
    import sys
    import scipy
    import pylab as pl

    soll = float(sys.argv[1])
    amp = Rapp(1e5, 100., 1., PinMax=2e-2, noise_loc=1, noise_sc=0.2)
    sg = SG()
    # pin=scipy.linspace(0,2e-3,100)
    # pout=amp.Pout(pin)
    # print pout
    regler = Leveler(sg, amp)
    # regler.add_samples([1e-5,1e-4,1e-3])
    # print regler.samples
    # interp=regler.extrap
    # print interp(2e-2), amp.Pout(2e-2)
    regler.adjust_level(soll, maxiter=10)
    sampx = list(regler.samples.keys())
    sampy = list(regler.samples.values())
    x = numpy.linspace(min(sampx), 2 * max(sampx), 100)
    y = amp.Pout(x)
    pl.plot(regler.x, regler.y, 'ro', sampx, sampy, 'bx', x, y, 'k-')
    pl.show()
