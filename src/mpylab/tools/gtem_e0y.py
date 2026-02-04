from numpy import pi, exp, sin, cos, array, sum, sqrt, sinh, cosh, arange
from scipy.special import j0

from mpylab.tools.spacing import linspace

def e0y(a: float,
        h: float,
        g: float,
        x: float = 0,
        y: float | None = None,
        Zc: float = 50,
        max_m: int =1000):
    """
    Analytic implementation of the GTEM field factor

    :param a: total cell width at position z
    :param h: septum height at position z
    :param g: septum gap at position z
    :param x: x position (0: middel of cell)
    :param y: y position (0: bottom of cell)
    :param Zc: characteristic impedance
    :param max_m: maximum index for sum
    """
    if y is None:
        y = h/2
    M = array(range(1,max_m,2)) * pi/a
    _coth = (exp(-M*(h-y))+exp(-M*(h+y))) / (1-exp(-2*M*h)) # _coth = cosh(M*y) / sinh(M*h)
    _cos = cos(M*x)
    _sin = sin(M*0.5*a)
    _j0 = j0(M*g)
    _x = _coth * _cos * _sin * _j0
    _sum = sum(_x)
    return 4*sqrt(Zc) / a * _sum


if __name__ == '__main__':
    import matplotlib.pyplot as plt
    x = 0
    y = 0.5
    Zc = 50
    max_m = 10000

    zmin = 0.1
    zmax = 7
    zstep = 0.1
    zs = linspace(zmin, zmax, zstep)

    def a(z):
        return 3.009/5.9 * z

    def g(z):
        return 0.536/5.9 * z

    def h(z):
        return 1.5/5.9 * z

    ees = []
    for _z in zs:
        ees.append(e0y(a(_z), h(_z), g(_z)))

    fig, ax = plt.subplots()
    ax.loglog(zs, ees)
    ax.loglog(zs, [28/_z for _z in zs])
    ax.set_title("GTEM e_0y")
    ax.set_xlabel("z / m")
    ax.set_ylabel("e_0y / V/m/sqrt(W)")
    ax.grid(True)
    fig.show()

#    print(e0y(a(5.9), h(5.9), g(5.9)))

