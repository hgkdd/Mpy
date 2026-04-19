# -*- coding: utf-8 -*-

from mpylab.device.driver import DRIVER
from mpylab.tools.configuration import strbool
from mpylab.tools.regular_expressions import FP


class MOTORCONTROLLER(DRIVER):
    """
    Parent class for all py-drivers for motor controllers.

    The parent class is :class:`mpylab.device.driver.DRIVER`.
    """

    conftmpl = {'description':
                    {'description': str,
                     'type': str,
                     'vendor': str,
                     'serialnr': str,
                     'deviceid': str,
                     'driver': str},
                'init_value':
                    {'gpib': int,
                     'virtual': strbool},
                'channel_%d':
                    {'name': str,
                     'unit': str}}

    # regular expression for a Fixed Point value in the raw string notation
    # this is the same as %e,%E,%f,%F known from scanf
    _FP = FP


    def __init__(self, SearchPaths=None):
        DRIVER.__init__(self, SearchPaths=SearchPaths)
        self._cmds = {'Goto': [("GOTO {to} DEG", None)],
                      'GetState': [('STATE?', rf'POS (?P<pos>{self._FP}) DEG, DIR (?P<dir>\d+)')],
                      'SetSpeed': [("'SPEED {speed}'", None)],
                      'GetSpeed': [('SPEED?', rf'SPEED (?P<speed>{self._FP})')],
                      'Move': [("MOVE {direction}", None)],
                      'Quit': [('QUIT', None)],
                      'GetDescription': [('*IDN?', r'(?P<IDN>.*)')]}
        self.unit = None
        self._internal_unit = 'deg'


if __name__ == '__main__':
    import sys

    try:
        ini = sys.argv[1]
    except IndexError:
        ini = None

    dev = MOTORCONTROLLER()
    dev.Init(ini)
    if not ini:
        dev.SetVirtual(False)

    err, des = dev.GetDescription()
    # print "Description: %s"%des

    for pos in [100]:
        print(f"Set pos to {pos}")
        err, rpos = dev.SetPos(pos)
        if err == 0:
            print(f"Pos set to {rpos}")
        else:
            print("Error setting pos")

    dev.Quit()
