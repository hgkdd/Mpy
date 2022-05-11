import numpy
import scipy.optimize


class control(object):
    """ """

    def __init__(self, actual_reader, setter, initial, abstol, maxorder=2):
        self.reader = actual_reader
        self.setter = setter
        self.initial = initial
        self.abstol = abstol
        self.maxorder = maxorder

    def set_cntrl_val(self, cntrl):
        self.setter(cntrl)
        actual = self.reader()
        return actual

    def do_cntrl(self, nominal, initial=None):
        if not initial:
            initial = self.initial
        cntrl_points = initial[:]
        act_points = [self.set_cntrl_val(cntrl) for cntrl in initial]
        guess = self.guess(cntrl_points, act_points, nominal)
        actual = self.set_cntrl_val(guess)
        while abs(actual - nominal) > self.abstol:
            cntrl_points.append(guess)
            act_points.append(actual)
            guess = self.guess(cntrl_points, act_points, nominal)
            actual = self.set_cntrl_val(guess)
        return guess, actual

    def guess(self, cntrl, act, nominal):
        order = min(self.maxorder, len(cntrl) - 1)  # for two points use linear fit
        poly = numpy.polyfit(act, cntrl, order)
        poly = numpy.poly1d(poly)
        theguess = poly(nominal)
        return theguess


class control_rapp(object):
    """ """

    def __init__(self, actual_reader, setter, initial, abstol):
        self.reader = actual_reader
        self.setter = setter
        self.initial = initial
        self.abstol = abstol
        self.p = 1
        self.g = 1
        self.sat = 20

    def set_cntrl_val(self, cntrl):
        self.setter(cntrl)
        actual = self.reader()
        return actual

    def do_cntrl(self, nominal, initial=None):
        if not initial:
            initial = self.initial
        cntrl_points = initial[:]
        act_points = [self.set_cntrl_val(cntrl) for cntrl in initial]
        guess = self.guess(cntrl_points, act_points, nominal)
        actual = self.set_cntrl_val(guess)
        while abs(actual - nominal) > self.abstol:
            cntrl_points.append(guess)
            act_points.append(actual)
            guess = self.guess(cntrl_points, act_points, nominal)
            actual = self.set_cntrl_val(guess)
            print(guess, actual)
        return guess, actual

    def guess(self, cntrl, act, nominal):
        def rapp(par, x):
            g, p, sat = par
            pp = 2 * p
            return g * x / numpy.power((1 + numpy.power(g * x / sat, pp)), (1. / pp))

        def errfunc(p, x, y):
            return rapp(p, x) - y  # Distance to the target function

        # errfunc = lambda p, x, y: rapp(p, x) - y  # Distance to the target function

        def rapp_min(x):
            rpp = rapp((self.p, self.g, self.sat), x)
            return rpp - nominal

        p0 = [self.p, self.g, self.sat]  # Initial guess for the parameters
        (self.p, self.g, self.sat), success = scipy.optimize.leastsq(errfunc, p0[:], args=(cntrl, act))
        print(self.p, self.g, self.sat)
        theguess = scipy.optimize.fsolve(rapp_min, act[-1])
        return theguess


if __name__ == '__main__':
    import scipy.interpolate
    import pylab


    class data(object):
        def __init__(self, data):
            self.data = data
            self.xsteps = []
            self.ysteps = []

        def setter(self, x):
            self.level = x
            # print x,' -> ',
            self.xsteps.append(x)
            return x

        def getter(self):
            ac = float(self.data(self.level))
            # print ac
            self.ysteps.append(ac)
            return ac


    # the data
    x = numpy.arange(101)
    # y=numpy.sqrt(x)
    y = 1. / (0.1 / x + 1. / 20)

    xy = scipy.interpolate.interp1d(x, y, bounds_error=False, fill_value=y[-1])
    D = data(xy)
    C = control_rapp(D.getter, D.setter, [0, 1, 3], 0.5)
    # for nom in numpy.arange(1,15,0.5):
    nom = y[-2]
    print(C.do_cntrl(nom))
    pylab.plot(x, y, 'r--', D.xsteps, D.ysteps, 'bo')
    pylab.show()
