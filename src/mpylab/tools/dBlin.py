from numpy import log10, power, array, any, ndarray

def lin2dB(dBfac=None, sifac=None):
    """
    e.g. W2dBm = lin2dB(10,1000)
    """
    if dBfac is None:
        dBfac = 10
    if sifac is None:
        sifac = 1.0

    def m(inp):
        if type(inp) in (int, float):
            inp = [inp]
        if not isinstance(inp, ndarray):
            inp = array(inp, dtype=float)
        ans = dBfac * log10(inp * sifac)
        if ans.size == 1:
            return ans[0]
        else:
            return ans

    return m


def dB2lin(dBfac=None, sifac=None):
    """
    e.g. dBm2W = dB2lin(10,1e-3)
    """
    if dBfac is None:
        dBfac = 10
    if sifac is None:
        sifac = 1.0

    def m(inp):
        if type(inp) in (int, float):
            inp = [inp]
        if not isinstance(inp, ndarray):
            inp = array(inp, dtype=float)
        ans = power(inp / float(dBfac), 10) * sifac
        if ans.size == 1:
            return ans[0]
        else:
            return ans

    return m

W2dBm = lin2dB(10, 1e3)
dBm2W = dB2lin(10,1e-3)

mW2dBm = lin2dB(10, 1)
dBm2mW = dB2lin(10,1)

V2dBuV = lin2dB(20,1e6)
dBuV2V = dB2lin(20,1e-6)

uV2dBuV = lin2dB(20,1)
dBuV2uV = dB2lin(20,1)

if __name__ == '__main__':
    val_Watt = 1e-3
    list_Watt = [-1, 1, 1e-3, 1e-4, 1e-5, 1e-6, 1e-7, 1e-8, 1e-9]

    print(W2dBm(val_Watt))
    print(W2dBm(list_Watt))
