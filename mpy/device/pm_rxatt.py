# -*- coding: utf-8 -*-

import re
import math
from mpy.tools.Configuration import Configuration,strbool,fstrcmp
from scuq import *
from mpy.device import device
from mpy.device.powermeter import POWERMETER as PWRMTR
from mpy.tools.util import locate


class POWERMETER(PWRMTR):
    conftmpl=PWRMTR.conftmpl
    conftmpl['description']['pmini'] = str

    _FP=r'[-+]?(\d+(\.\d*)?|\d*\.\d+)([eE][-+]?\d+)?'
        
    def __init__(self, **kw):
        self.SearchPaths=kw.get('SearchPaths', ['.'])
        if self.SearchPaths == None:
            self.SearchPaths=['.']
        self.pm_instance = None
        self.freq= None
        self.power=None
        self.unit=None
        self._internal_unit='dBm'

    def __getattr__(self, name):
        try:
            return getattr(self.pm_instance, name)
        except AtributeError:
            raise AttributeError, name
        
    def Init(self, ininame, ch=1):
        self.conf=Configuration(ininame, self.conftmpl)
        pmini=self.conf['description']['pmini']
        pmini=locate(pmini, paths=self.SearchPaths).next()
        self.pm_instance=getattr(device, 'Powermeter')(SearchPaths=self.SearchPaths)
        stat = self.pm_instance.Init(pmini, ch)
        return stat

    def GetData(self):
        self.error, obj = self.pm_instance.GetData()
        return self.error, obj

    def GetDataNB(self, retrigger):
        self.error, obj = self.pm_instance.GetDataNB(retrigger)
        return self.error, obj


if __name__ == '__main__':
    pass