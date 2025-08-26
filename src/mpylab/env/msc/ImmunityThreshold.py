# -*- coding: utf-8 -*-
import time
from mpylab.tools import util
from mpylab.device import driver
from scuq.si import VOLT, METER
from scuq.quantities import Quantity
import pprint
# import emc300

Volt_over_Meter = VOLT / METER


class FieldLst:
    def __init__(self, lst):
        self.field = lst
        self._next = 0

    def __call__(self):
        ret = self._next
        self._next += 1
        try:
            return self.field[ret]
        except IndexError:
            return None

    def next_freq(self):
        self._next = max(0, self._next - 5)    # TODO: why "-5"
        return self.field[self._next]


class ImmunityKernel_Thres:
    def __init__(self, messenger, UIHandler, locals, dwell, keylist='sS', tp=None, field=None, testfreqs=None):
        self.field = field
        self.testfreqs = testfreqs
        self.goto_next_freq = False
        self.mg = locals['mg']
        if self.field is None:
            self.field = FieldLst(list(range(10, 110, 10)))
        if not callable(self.field):
            self.field = FieldLst(self.field)
        self.tp = tp
        self.messenger = messenger
        self.UIHandler = UIHandler
        self.callerlocals = locals
        self._testplan = self._makeTestPlan()
        self._innerblock = None
        self.dwell = dwell
        self.keylist = keylist
        self._search_thres = False
        self._innerblockindex = 0
        ##        self.eutinifn=['M:\\umd-config\\largeMSC\\ini\\umd-narda-emc300-narda-new.ini',
        ##                       'M:\\umd-config\\largeMSC\\ini\\umd-narda-emc300-1-real.ini',
        ##                       'M:\\umd-config\\largeMSC\\ini\\umd-narda-emc300-2-real.ini',
        ##                       'M:\\umd-config\\largeMSC\\ini\\umd-narda-emc300-4-real.ini',
        ##                       'M:\\umd-config\\largeMSC\\ini\\umd-narda-emc300-5-real.ini',
        ##                       'M:\\umd-config\\largeMSC\\ini\\umd-narda-emc300-6-real.ini',
        ##                       'M:\\umd-config\\largeMSC\\ini\\umd-narda-emc300-7-real.ini',
        ##                       'M:\\umd-config\\largeMSC\\ini\\umd-narda-emc300-8-real.ini']
        self.ports = list(range(3, 11))
        self.eut = {}
        testtime = 100
        for p in self.ports:
            self.eut[p] = {}
            self.eut[p]['dev'] = emc300.emc300(port=p - 1)  # TODO: adjust fieldprobe
            self.eut[p]['ok'] = True
            self.eut[p]['failed_at_cur_freq'] = False

    ##        for _i,_n in enumerate(self.eutinifn):
    ##            self.eut[_i]=umddevice.UMDFieldprobe()
    ##            self.eut[_i].Init(_n, 1)
    ##            self.eut[_i].SetFreq(100e6)
    # print "Testplan:"
    # pprint.pprint(self._testplan)
    # print "inner Block:"
    # pprint.pprint(self._innerblock)

    def _make_inner_block(self, f):
        ret2 = []
        ret2.append(('efield', '', {'efield': self.field}))
        if not self.tp is None:  # tuned mode
            for t in self.tp[f]:
                ret2.append(('tuner', '', {'tunerpos': t[:]}))
                ret2.append(('rf', '', {'rfon': 1}))
                ret2.append(('measure', '', {}))
                ret2.append(('eut', None, None))
                ret2.append(('rf', '', {'rfon': 0}))
        else:  # stirred mode
            ret2.append(('measure', '', {}))
            ret2.append(('eut', None, None))
        self._innerblock = ret2

    def _makeTestPlan(self):
        ret = []
        if self.tp is None:
            freqs = self.testfreqs[:]
        else:
            freqs = list(self.tp.keys())
        freqs.sort()
        for f in freqs:
            ret.append(('LoopMarker', '', {}))
            ret.append(('freq', '', {'freq': f}))
            if self.tp is None:
                ret.append(('rf', '', {'rfon': 1}))
            ret.append(('InnerBlock', '', {}))
            if self.tp is None:
                ret.append(('rf', '', {'rfon': 0}))
        ret.append(('finished', '', {}))
        ret.reverse()
        return ret

    def test(self, stat):
        if stat == 'AmplifierProtectionError':
            self.goto_next_freq = True

        if self.goto_next_freq:
            cmd = self.__goto_next_freq()
        elif not self._search_thres:
            cmd = self._testplan.pop()
        else:
            cmd = (None, "", {})  # we are in the inner loop

        # overread LoopMarker
        while cmd[0] == 'LoopMarker':
            cmd = self._testplan.pop()

        if cmd[0] == 'InnerBlock':
            self._search_thres = True
            self._innerblockindex = 0

        if self._search_thres:
            if self._innerblockindex >= len(self._innerblock):
                self._innerblockindex = 0  # reset index: start new inner block -> next E-field
            cmd = self._innerblock[self._innerblockindex]
            self._innerblockindex += 1

        if cmd[0] == 'eut':
            start = time.time()
            intervall = 0.01
            self.messenger(util.tstamp() + " Start EUT checking...", [])
            self.messenger(util.tstamp() + " Press %s to set user event" % str(self.keylist), [])
            dct = {}
            while time.time() - start < self.dwell:
                key = util.anykeyevent()
                if key and chr(key) in self.keylist:
                    self.messenger(util.tstamp() + " Got user event while EUT checking.", [])
                    cmd = ('eut', 'User event.', {'eutstatus': 'Marked by user'})
                    self.goto_next_freq = True
                    return cmd
                ##                self.eutval=umddevice.stdVectorUMDMResult()
                ##                for _i,_e in self.eut.items():
                ##                    if not _i in dct.keys():    # only if this eut was ok before
                ##                        _e.Trigger()
                ##                        stat = _e.getData(self.eutval)
                ##                        if stat != 0:
                ##                            dct[_i] = 'stat=%s'%str(stat)
                for p in self.ports:
                    theprobe = self.eut[p]
                    if theprobe['ok']:
                        dev = theprobe['dev']
                        ans = dev.getSenType()
                        if ans != dev.sensor:
                            print(('FAIL on COM %d' % p))
                            theprobe['ok'] = False
                            dct[p] = 'EUT Failure. Sensor = %r' % ans
                time.sleep(intervall)
            if len(dct):
                self.messenger(util.tstamp() + " EUT failure with: %r" % (dct), [])
                cmd = ('eut', 'stat!=0', {'eutstatus': dct.copy()})
                if len(dct) == len(self.ports):
                    self.goto_next_freq = True
                self.messenger(util.tstamp() + " RFOff ...", [])
                self.mg.RFOff_Devices()
                notok = list(dct.keys())
                while len(notok):
                    # util.wait(1, self.callerlocals, self.UIHandler)
                    self.callerlocals['self'].wait(1, self.callerlocals, self.UIHandler)
                    self.messenger(util.tstamp() + " EUTs not ok: %r" % notok, [])
                    for p in self.ports:
                        if p in notok:
                            theprobe = self.eut[p]
                            dev = theprobe['dev']
                            dev.reset()
                            ans = dev.getSenType()
                            if ans == dev.sensor:
                                notok.remove(p)
                ##                    for _i,_e in self.eut.items():
                ##                        if _i in notok:    # only check euts that are not ok
                ##                            _e.Trigger()
                ##                            stat = _e.getData(self.eutval)
                ##                            if stat == 0:
                ##                                notok.remove(_i)
                self.messenger(util.tstamp() + " All EUTs OK.", [])
            else:
                self.messenger(util.tstamp() + " All EUTs OK.", [])
                cmd = ('eut', '', {'eutstatus': 'OK'})
            self.messenger(util.tstamp() + " ... EUT checking done.", [])
        elif cmd[0] == 'efield':
            fld = self.field()
            if fld:
                cmd = ('efield', '', {'efield': Quantity(Volt_over_Meter, fld)})
            else:
                # fld is None if no more field vals in the list
                self.goto_next_freq = True
                cmd = (None, "", {})
        elif cmd[0] == 'freq':
            f = cmd[2]['freq']
            self._make_inner_block(f)
        return cmd

    def __goto_next_freq(self):
        self.goto_next_freq = False
        for p in self.ports:
            theprobe = self.eut[p]
            dev = theprobe['dev']
            dev.reset()
            ans = dev.getSenType()
            if ans == dev.sensor:
                self.eut[p]['ok'] = True
        f = self.field.next_freq()
        ##        for _e in self.eut.values():
        ##            _e.SetFreq(f)
        self._search_thres = False
        self._innerblockindex = 0
        # look for 'LoopMarker' and continue there
        while True:
            cmd = self._testplan.pop()
            if cmd[0] in ('LoopMarker', 'finished'):
                break
        return cmd
