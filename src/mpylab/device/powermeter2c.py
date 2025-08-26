# -*- coding: utf-8 -*-

import time
from mpylab.device.powermeter import POWERMETER as PM


class POWERMETER(PM):
    instances = {}

    def __init__(self):
        POWERMETER.conftmpl['channel_%d'].setdefault('trg_threshold', float)
        PM.__init__(self)
        self.lasttrigger = None
        self.istriggered = False

    def Init(self, ininame=None, channel=None):
        self.error = PM.Init(self, ininame=ininame, channel=channel)
        self.ch = channel
        self.trg_threshold = self.conf['channel_%d' % channel]['trg_threshold']
        self.gpib = self.conf['init_value']['gpib']
        virtual = self.conf['init_value'].get('virtual', False)
        if self.gpib and not virtual:  # ignore virtual instruments
            key = self._hash()  # here: gbib_ch
            if key in POWERMETER.instances:
                raise RuntimeWarning("2Ch Powermeter: Instance allready in use: %s" % key)
            POWERMETER.instances.setdefault(key, self)  # register this instance
        return self.error

    def Trigger(self):
        """
        Trigger the instrument. The Trigger is send only if no trigger was send from an othe instance 'inst' of the same instrument
        within (now-self.trg_threshold) and now.
        """
        now = time.time()
        for inst in self._crossref():
            if inst.lasttrigger and (now - inst.lasttrigger) <= self.trg_threshold:
                # print "do not send trigger from %d_%d"%(self.gpib,self.ch)
                self.istriggered = True
                self.error = 0
                break
        else:
            # print "send trigger from %d_%d"%(self.gpib,self.ch)
            self.error = PM.Trigger(self)
            self.istriggered = True
            self.lasttrigger = time.time()
            self.xrefdata = None
        return self.error

    def GetData(self):
        now = time.time()
        for inst in self._crossref():
            if inst.lasttrigger and (now - inst.lasttrigger) <= self.trg_threshold:
                mine = self.xrefdata
                self.error = 0
                break
        else:
            self.error, obj = PM.GetData(self)
            mine = obj[self.ch]
            self.istriggered = False
            for inst in self._crossref():
                inst._setxrefdata(obj[inst.ch])
        return self.error, mine

    def GetDataNB(self, retrigger):
        self.error, obj = PM.GetDataNB(self, retrigger)

    def Quit(self):
        PM.Quit(self)
        del POWERMETER.instances[self._hash()]  # remove this instance

    def _hash(self):
        return "%s_%s" % (self.gpib, self.ch)

    def _crossref(self):
        """
        return a list of instances with same gpib but different ch than 'self'
        """
        instances = []
        for key, val in list(POWERMETER.instances.items()):
            g, c = list(map(int, key.split('_')))
            if g == self.gpib and c != self.ch:
                instances.append(val)
        return instances

    def _setxrefdata(self, data):
        self.xrefdata = data
