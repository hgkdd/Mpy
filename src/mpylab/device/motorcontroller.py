# -*- coding: utf-8 -*-

from mpylab.device.driver import DRIVER
from mpylab.tools.Configuration import strbool


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
    _FP = r'[-+]?(\d+(\.\d*)?|\d*\.\d+)([eE][-+]?\d+)?'

    # defintion from http://docs.python.org/library/re.html
    # _FP=r'[-+]?(\d+(\.\d*)?|\.\d+)([eE][-+]?\d+)?'

    def __init__(self):
        DRIVER.__init__(self)
        self._cmds = {'Goto': [("'GOTO %s DEG'%to", None)],
                      'GetState': [('STATE?', r'POS (?P<pos>%s) DEG, DIR (?P<dir>\d+)' % (self._FP))],
                      'SetSpeed': [("'SPEED %s'%(speed)", None)],
                      'GetSpeed': [('SPEED?', r'SPEED (?P<speed>%s)' % (self._FP))],
                      'Move': [("'MOVE %d'%direction", None)],
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
        print(("Set pos to %e" % pos))
        err, rpos = dev.SetPos(pos)
        if err == 0:
            print(("Pos set to %e" % rpos))
        else:
            print("Error setting pos")

    dev.Quit()
