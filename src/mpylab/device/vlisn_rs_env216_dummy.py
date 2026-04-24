# -*- coding: utf-8 -*-
"""mpylab.device.vlisn_rs_env216_dummy module."""
from mpylab.device.vlisn import VLISN as VL
from mpylab.tools.util import case_insensitive_string_compare

class VLISN(VL):
    """
    V-Type LISN device R&S ENV216 dummy driver
    """
    conftmpl = VL.conftmpl

    def __init__(self, **kw):
        VL.__init__(self, **kw)

    def Init(self, ini=None, channel=None):
        """Init method."""
        self.path = None
        super().Init(ini=ini, channel=channel)
        return self.error

    def SetPath(self, path):
        """SetPath method."""
        self.error = 0
        # self.path = None
        for _path in ('L', 'N'):
            if case_insensitive_string_compare(path[0], _path):
                if self.path != _path:
                    self.path = _path
                break
        if self.path is None:
            raise RuntimeError("V-LISN: Path has to be in ('L', 'N')")
        return self.GetPath()

def main():
    """main function."""
    import sys
    import io
    from mpylab.tools.util import format_block
    from mpylab.tools.spacing import linspaceN
    import scuq

    try:
        ini = sys.argv[1]
    except IndexError:
        ini = format_block("""
                         [description]
                         DESCRIPTION = R&S ENV216 V-Type LISN
                         TYPE = VLISN
                         VENDOR = Rohde&Schwarz
                         SERIALNR = 
                         DEVICEID = 
                         DRIVER = vlisn_rs_env216.py

                         [INIT_VALUE]
                         FSTART = 9e3
                         FSTOP = 30e6
                         FSTEP = 0.0
                         NR_OF_CHANNELS =  1
                         PATH = L
                         VIRTUAL = 0

                         [CHANNEL_1]
                         NAME = S21
                         UNIT = dB
                         INTERPOLATION = LIN
                         FILE = io.StringIO(format_block('''
                                                                FUNIT: Hz
                                                                UNIT: dB
                                                                RELERROR: 0
                                                                9e3 -10
                                                                30e6 -10
                                            '''))
                         """)
        ini = io.StringIO(ini)

    lisn = VLISN()
    err = lisn.Init(ini)
    ctx = scuq.ucomponents.Context()
    for path in ('L', 'N'):
        err, p = lisn.SetPath(path)
        print(f"Path set to {p}")
        for freq in linspaceN(9e3, 30e6, 10, endpoint=True):
            lisn.SetFreq(freq)
            err, uq = lisn.GetData(what='S21')
            val, unc, unit = ctx.value_uncertainty_unit(uq)
            print(freq, uq, abs(val), abs(unc), unit)


if __name__ == '__main__':
    main()
