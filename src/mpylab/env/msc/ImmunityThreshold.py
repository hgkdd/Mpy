# -*- coding: utf-8 -*-
"""This is :mod:`mpylab.env.msc.ImmunityThreshold`.

   Provides :class:`mpylab.env.msc.ImmunityThreshold` for EMC measurements in MSC were the threshold is searched

   :author: Hans Georg Krauthäuser (main author)

   :license: GPLv3 or higher
"""

import time
from typing import Any, Iterable, Callable
from mpylab.tools import util
from mpylab.tools.aunits import EFIELD
from mpylab.device import driver
from scuq.si import VOLT, METER
from scuq.quantities import Quantity


class FieldLst:
    """
    A callable list of field strength values
    """

    def __init__(self, lst: Iterable[float]) -> None:
        """
        Constructor of :class:`FieldLst`.

        Parameter:
            - *lst* (list[float]): list of field strength values
        """

        self.field = lst  # the list of field strength values to be used sequentially
        self._index = 0  # start with first element in list

    def __call__(self) -> float | None:
        """
        Return the field strength value and increase index for next call. Return None if list is exhausted.
        """

        curent_index = self._index
        self._index += 1
        try:
            return self.field[curent_index]
        except IndexError:
            return None

    def next_freq(self, max_last: int = -5) -> float | None:
        """
        Indicate switch to next frequency and return field strength value or None if list is exhausted.

        Parameter:
        *max_last*: maximum number of field strength values to test for this frequency (default: 5)
        """

        self._next = max(0, self._next - max_last)    # go max_last back in list but keep it ge 0
        return self.field[self._next]  # return the first value for this freq


class ImmunityKernel_Thres:
    """
    Class for EMC radiated immunity testing. Aims to find the susceptibility threshold by increasing the field strength
    """

    def __init__(self, messenger: Callable[[str, Iterable[str] | None, str, dict[Any, Any] | None], int],
                 UIHandler: Callable[[None], int | None],
                 locals: dict[str, Any],
                 dwell: float,
                 keylist: str = 'sS',
                 tp: dict[float, list[Any]] | None = None,
                 field: list[float] | None = None,
                 testfreqs: list[float] | None = None):
        """
        Class for EMC radiated immunity testing. Aims to find the susceptibility threshold by increasing the field strength.

           Parameters:

              - *messenger*: callable, see :meth:`mpylab.env.Measure.Measure.stdUserMessenger()`
              - *UIHandler*: callable, see :meth:`mpylab.env.Measure.Measure.stdUserInterruptTester()`
              - *locals*: :class:`dict` used for local variable scope
              - *dwell*: dwell time in seconds for each frequency
              - *keylist*: string with list of characters to mark an eut status
              - *tp*: :class:`dict`, keys: frequencies, values: :class:`list` tuner positions, can be nested for multiple tuners
              - *field*: list, field strength values
              - *testfreqs*: list or None, if given: test frequencies, otherwise keys of tp are used

           Return value: None
        """

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
            # TODO: self.eut[p]['dev'] = emc300.emc300(port=p - 1)  # TODO: adjust fieldprobe
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

    def _make_inner_block(self, f: float) -> None:
        """
        Make the list of commands used for each frequency.
        """

        ret2 = []
        ret2.append(('efield', '', {'efield': self.field}))    # the field strength values
        if not self.tp is None:  # tuned mode
            for t in self.tp[f]:    # tuner position(s) for this frequency
                ret2.append(('tuner', '', {'tunerpos': t[:]}))   # for all tuner positions
                ret2.append(('rf', '', {'rfon': 1}))   # switch rf on
                ret2.append(('measure', '', {}))  # perform measurement
                ret2.append(('eut', None, None))  # get eut status
                ret2.append(('rf', '', {'rfon': 0}))  # switch rf off
        else:  # stirred mode, tuner is running, rf is ON
            ret2.append(('measure', '', {}))   # perform measurement
            ret2.append(('eut', None, None)) # get eut status
        self._innerblock = ret2

    def _makeTestPlan(self) -> list[tuple[str, str, dict[str, Any] | None]]:
        """
        Make the test plan. Test plan is a stack (list) of commands.
        """

        ret = []
        if self.tp is None:
            freqs = self.testfreqs[:]   # if we don't have dict with tuner positions -> take frequencies from testfreqs
        else:
            freqs = list(self.tp.keys())  # otherwise, we use the keys of that dict
        freqs.sort() # run sg in order
        for f in freqs:
            ret.append(('LoopMarker', '', {}))     # mark beginning of freq loop
            ret.append(('freq', '', {'freq': f}))  # set freq
            if self.tp is None:   # stirring
                ret.append(('rf', '', {'rfon': 1}))   # rf on for stirr mode
            ret.append(('InnerBlock', '', {}))  # make inner block for this freq
            if self.tp is None: # stirring
                ret.append(('rf', '', {'rfon': 0}))  # rf off in stirrimg mode
        ret.append(('finished', '', {}))
        ret.reverse()   # we reverse the plan. Thus, LAST element ist next command; easier...
        return ret

    def test(self, stat: str):
        """
        Perform the test according to test plan.

        Parameter:
            - *stat*: string, at the moment, only 'AmplifierProtectionError' is used. If called with this status -> go to next frequency.
        """

        if stat == 'AmplifierProtectionError':   # we got an AmpliferProtectionError before -> do not proceed -> go to next freq instead
            self.goto_next_freq = True

        if self.goto_next_freq:
            cmd = self.__goto_next_freq()  # returns 'LoopMarker' or 'finished'
        elif not self._search_thres: # initially False; is set True in inner loop
            cmd = self._testplan.pop()   # remember: testplan is reversed -> LAST element is next command
        else:
            cmd = (None, "", {})  # we are in the inner loop

        # overread LoopMarker
        while cmd[0] == 'LoopMarker':
            cmd = self._testplan.pop()  # next cmd after LoopMarker

        if cmd[0] == 'InnerBlock':      # new inner block
            self._search_thres = True   # set flag
            self._innerblockindex = 0   # reset index of cmd in inner block

        if self._search_thres:   # we are in an inner block (not necessarily new)
            if self._innerblockindex >= len(self._innerblock):
                self._innerblockindex = 0  # reset index: start new inner block -> next E-field
            cmd = self._innerblock[self._innerblockindex]
            self._innerblockindex += 1

        if cmd[0] == 'eut':   # get eut status
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
        elif cmd[0] == 'efield':  # adjust field
            fld = self.field()   # a call to the FieldList
            if fld:
                cmd = ('efield', '', {'efield': Quantity(EFIELD, fld)})
            else:
                # fld is None if no more field vals in the list
                self.goto_next_freq = True
                cmd = (None, "", {})
        elif cmd[0] == 'freq':   # set freq
            f = cmd[2]['freq']
            self._make_inner_block(f)
        return cmd

    def __goto_next_freq(self) -> tuple[str, str, dict[str, Any]] | None:
        """Pop from test plan until 'LoopMarker == 'finished' read.

        Sets EUT Status for all ports to 'ok' (self.eut[p]['ok'] = True)

        Returns 'LoopMarker' od 'finished' cmd.
        """

        self.goto_next_freq = False  # set flag
        for p in self.ports:    # self.ports -> ports for EUT monitoring
            theprobe = self.eut[p]
            dev = theprobe['dev']
            dev.reset()
            ans = dev.getSenType()
            if ans == dev.sensor:
                self.eut[p]['ok'] = True
        f = self.field.next_freq()
        ##        for _e in self.eut.values():
        ##            _e.SetFreq(f)
        self._search_thres = False  # set flag
        self._innerblockindex = 0  # begin of inner block
        # look for 'LoopMarker' and continue there
        while True:
            cmd = self._testplan.pop()
            if cmd[0] in ('LoopMarker', 'finished'):
                break
        return cmd    # is LoopMarker or finished
