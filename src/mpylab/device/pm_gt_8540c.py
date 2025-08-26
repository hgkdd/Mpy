# -*- coding: utf-8 -*-

import numpy as np
# import pyvisa.vpp43 as vpp43
from scuq import *

from mpylab.device.powermeter import POWERMETER as PWRMTR


# import pprint

def linav_dB(dbvals):
    """
    Input: sequence of dB-scaled values
    Output: dB-scaled lin-average of the input sequence
    
    Example: linav_dB([0,-10]) -> -0.301
    """
    linmean = np.mean(np.power(10., 0.1 * np.asarray(dbvals)))
    return 10 * np.log10(linmean)


def linav_lin(linvals):
    """
    Input: sequence of lin-scaled values
    Output: lin-scaled lin-average of the input sequence
    
    Example: linav_lin([0,-10]) -> -5
    """
    linmean = np.mean(np.asarray(linvals))
    return linmean


class POWERMETER(PWRMTR):
    """
    Driver for the Gigatronics 854X powermeter
    """

    def __init__(self):
        PWRMTR.__init__(self)
        self._internal_unit = 'dBm'
        self.linav = linav_dB
        self.ch_tup = ('', 'A', 'B')
        self._cmds = {'SetFreq': [("'%sE FR %s HZ'%(self.ch_tup[self.channel], freq)", None)],
                      'GetFreq': [],
                      'ZeroOn': [("'%sE ZE'%self.ch_tup[self.channel]", None)],
                      'ZeroOff': [],
                      'Quit': [],
                      'GetDescription': [('*IDN?', r'(?P<IDN>.*)')]}

    def _get_sensor_type(self):
        """
        return the type of the attached sensor as a string.
        """
        self._lock()
        cmd = "TEST EEPROM %s TYPE?" % self.ch_tup[self.channel]
        tmpl = '(?P<SENSOR>\\d+)'
        dct = self.query(cmd, tmpl)
        self._unlock()
        return dct['SENSOR']

    def Zero(self, state='on'):
        self.error = 0
        self._lock()
        self.error, _ = PWRMTR.Zero(self, state=state)
        self._unlock()
        return self.error, 0

    def Init(self, ini=None, channel=None):  # , N=10, trg_threshold=0):
        if channel is None:
            self.channel = 1
        else:
            self.channel = channel
        self.chsel = "AP"
        if self.channel != 1:
            self.chsel = "BP"
            self.channel = 2

        try:
            # read gpib address fom ini-file to register instance
            self.get_config(ini, self.channel)

            self.value = None
            self.error = PWRMTR.Init(self, ini, self.channel)  # run init from parent class
            self.dev.write("TR3")

            sec = 'channel_%d' % self.channel
            try:
                self.levelunit = self.conf[sec]['unit']
            except KeyError:
                self.levelunit = self._internal_unit
            self._cmds['Preset'] = [('PR', None)]

            # key, vals, actions
            presets = [('filter', [], [])]  # TODO: fill with information from ini-file

            for k, vals, actions in presets:
                # print k, vals, actions
                try:
                    v = self.conf[sec][k]
                    # print sec, k, v
                    if vals is None:  # no comparision
                        # print actions[0], self.convert.c2c(self.levelunit, self._internal_unit, float(v)), float(v), self.levelunit
                        # print eval(actions[0])
                        self._cmds['Preset'].append((eval(actions[0]), actions[1]))
                    else:
                        for idx, vi in enumerate(vals):
                            if v.lower() in vi:
                                self._cmds['Preset'].append(actions[idx])
                except KeyError:
                    pass

            dct = self._do_cmds('Preset', locals())
            self._update(dct)
            self.update_internal_unit()

            self._sensor = self._get_sensor_type()
            # time.sleep(.7)
        except:
            raise

        return self.error

    def update_internal_unit(self):
        # get internal unit
        tup = ('W', 'dBm', '%', 'dB')
        ans = self.dev.ask('%sP SM' % self.ch_tup[self.channel])
        ans = int(ans[-1])
        self._internal_unit = tup[ans]
        # Here, the appropriate average routine is set up
        if self._internal_unit in ['dB', 'dBm']:
            self.linav = linav_dB
        else:
            self.linav = linav_lin
        # self._fbuf_on()

    def Trigger(self):
        self.error = 0
        return self.error

    def _lock(self):
        # vpp43.lock(self.dev.vi, pyvisa.constants.AccessModes.exclusive_lock, 2000)
        self.dev.lock_excl(timeout=2000)

    def _unlock(self):
        # vpp43.unlock(self.dev.vi)
        self.dev.unlock()

    def GetData(self):
        self._lock()
        self.SetFreq(self.freq)
        self.dev.write(self.chsel)
        ans = self.dev.read()
        self._unlock()
        self.value = self.linav([float(ans)])
        swr_err = self.get_standard_mismatch_uncertainty()
        self.power = float(self.value)
        try:
            obj = quantities.Quantity(eval(self._internal_unit),
                                      ucomponents.UncertainInput(self.power, self.power * swr_err))
        except (AssertionError, NameError):
            self.power, self.unit = self.convert.c2scuq(self._internal_unit, float(self.power))
            obj = quantities.Quantity(self.unit,
                                      ucomponents.UncertainInput(self.power, self.power * swr_err))
        return self.error, obj  # TODO: include other uncertainties

    def GetDataNB(self, retrigger):
        self.err, v = self.GetData()
        if retrigger:
            self.Trigger()
        return self.error, v

    def SetFreq(self, freq):
        self.error = 0
        self.freq = freq
        self.error, freq = PWRMTR.SetFreq(self, freq)
        return self.error, freq

    def GetDescription(self):
        self.error = 0
        self._lock()
        self.error, des = PWRMTR.GetDescription(self)
        self._unlock()
        return self.error, des

    def Quit(self):
        self.error = 0
        return self.error


def test_init(cha):
    import io
    from mpylab.tools.util import format_block
    inst = POWERMETER()
    ini = format_block("""
                    [DESCRIPTION]
                    description: 'GigaTronics 8542C Universal Power Meter'
                    type:        'POWERMETER'
                    vendor:      'GigaTronics'
                    serialnr:
                    deviceid:
                    driver:

                    [Init_Value]
                    fstart: 100e3
                    fstop: 18e9
                    fstep: 1
                    gpib: 13
                    virtual: 0
                    nr_of_channels: 2

                    [Channel_1]
                    name: A
                    unit: dBm
                    filter: -1
                    #resolution: 
                    rangemode: auto
                    #manrange: 
                    swr1: 1.1
                    swr2: 1.1
                    trg_threshold: 0.5

                    [Channel_2]
                    name: B
                    unit: 'W'
                    swr1: 1.1
                    swr2: 1.1
                    """)
    ini = io.StringIO(ini)
    inst.Init(ini, cha)
    return inst


def main():
    import io
    from mpylab.tools.util import format_block
    from mpylab.device.powermeter_ui import UI as UI

    try:
        ini = sys.argv[1]
    except IndexError:
        ini = format_block("""
                        [DESCRIPTION]
                        description: 'GigaTronics 8542C Universal Power Meter'
                        type:        'POWERMETER'
                        vendor:      'GigaTronics'
                        serialnr:
                        deviceid:
                        driver:

                        [Init_Value]
                        fstart: 100e3
                        fstop: 18e9
                        fstep: 1
                        gpib: 13
                        virtual: 0
                        nr_of_channels: 2

                        [Channel_1]
                        name: A
                        unit: dBm
                        filter: -1
                        #resolution: 
                        rangemode: auto
                        #manrange: 
                        swr: 1.1
                        trg_threshold: 0.5

                        [Channel_2]
                        name: B
                        unit: 'W'
                        trg_threshold: 0.5
                        """)
        ini = io.StringIO(ini)

    pm = POWERMETER()
    ui = UI(pm, ini=ini)
    ui.configure_traits()


if __name__ == '__main__':
    #    main()
    import sys
    import time

    ch = int(sys.argv[1])
    pm1 = test_init(ch)
    pm1.SetFreq(50e6)
    time.sleep(5)

    # pm2=test_init(2)
    try:
        i = 0
        while True:
            pm1.Trigger()
            # pm2.Trigger()
            print((i, "PM%d" % ch, pm1.GetData()))
            i += 1
            # print "PM2", pm2.GetData()
    finally:
        pm1.Quit()
        # pm2.Quit()

    # for i in range(5):
    # pm1.Trigger()
    # print "PM1", pm1.GetData()
    # pm2.Trigger()
    # print "PM2", pm2.GetData()
    # pm2.Quit()
    # for i in range(5):
    # pm1.Trigger()
    # print "PM1", pm1.GetData()
    # pm2=test_init(2)
    # for i in range(5):
    # pm1.Trigger()
    # print "PM1", pm1.GetData()
    # pm2.Trigger()
    # print "PM2", pm2.GetData()
    time.sleep(5)
    # pm1.Quit()
    # pm2.Quit()
