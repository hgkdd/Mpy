# -*- coding: utf-8 -*-

import time
from scuq import *
from mpylab.device.powermeter import POWERMETER as PWRMTR


class POWERMETER(PWRMTR):
    """
    Driver for the R&S NRP
    """

    def __init__(self):
        super().__init__()
        self._internal_unit = 'dBm'
        self._data_ = 0
        self.sensor = {}
        self._cmds = {'SetFreq': [("'SENS%d:FREQ:CW %f '%(self.channel, freq)", None)],
                      'GetFreq': [("'SENS%d:FREQ:CW?'%(self.channel)", r'(?P<freq>%s)' % self._FP)],
                      'Trigger': [("'INIT%d:IMM'%(self.channel)", None)],
                      'ZeroOn': [("'CAL%d:ZERO:AUTO ON'%(self.channel)", None)],
                      'ZeroOff': [("'CAL%d:ZERO:AUTO OFF'%(self.channel)", None)],
                      'Quit': [],
                      'Unit': [("'UNIT%d:POW %s'%(channel,unit)", None)],
                      'GetDescription': [('*IDN?', r'(?P<IDN>.*)')]}

    # def Zero(self, state='on'):
    # self.error=0
    # return self.error,0

    def Init(self, ini=None, channel=None):
        if channel is None:
            self.channel = 1
        else:
            self.channel = channel
        masks = (2, 4, 8, 16)
        self.mask = masks[self.channel - 1]
        self.error = PWRMTR.Init(self, ini, self.channel)

        sec = 'channel_%d' % self.channel
        try:
            self.levelunit = self.conf[sec]['unit']
        except KeyError:
            self.levelunit = self._internal_unit
        self._cmds['Preset'] = [('*RST', None),  # reset of device.
                                ("INIT%d:CONT OFF" % self.channel, None),  # Selects either single-shot
                                ("SENS%d:AVER:STAT OFF" % self.channel, None),  # deactivation of filter
                                ("UNIT%d:POW DBM" % self.channel, None)]

        presets = [('filter', [], [])]  # TODO: fill with information from ini-file
        for k, vals, actions in presets:
            try:
                v = self.conf[sec][k]
                if vals is None:  # no comparision
                    # print actions[0], self.convert.c2c(self.levelunit, self._internal_unit, float(v)), float(v), self.levelunit
                    self._cmds['Preset'].append((eval(actions[0]), actions[1]))
                else:
                    for idx, vi in enumerate(vals):
                        if v.lower() in vi:
                            self._cmds['Preset'].append(actions[idx])
            except KeyError:
                pass

        dct = self._do_cmds('Preset', locals())
        self._update(dct)
        return self.error

    def InitSen(self, channel=None):
        channel = channel
        dct = self.query("SYST:SENS%d:INFO?" % channel, r'(?P<inf>.*)')
        tmp = dct['inf']
        tmp = tmp.split('","')
        tmpt = tmp[0].split('"')
        tmp[0] = tmpt[1]

        for i in range(0, len(tmp) - 1):
            tmp1 = tmp[i]
            tmp2 = tmp1.split(':')
            dct1 = {tmp2[0]: tmp2[1]}
            self.sensor.update(dct1)
        # print self.sensor['Manufacturer']

        return

    def GetData(self):
        """
        Read a power measurement from the instrument.
        
        ``(self.error, obj)`` is returned where ``obj`` is a instance of 
        :class:`scuq.quantities.Quantity`.
        """
        self.Trigger()
        finished = False
        while not finished:
            time.sleep(.01)
            dct = self.query("STAT:OPER:MEAS:SUMM:COND?", r'(?P<stat>.*)')  # Ask for whether a measurement
            stat = int(dct['stat'])  # was started or completed since
            if not (stat & self.mask):
                finished = True

        dct = self.query("FETCH%d?" % self.channel, r'(?P<val>%s)' % self._FP)  # The last valid result
        v = float(dct['val'])  # is returned.
        swr_err = self.get_standard_mismatch_uncertainty()
        self.power = v
        dct = self.query("UNIT%d:POW?" % self.channel, r'(?P<unit>.*)')  # Ask for the unit of
        self._internal_unit = dct['unit']  # the measured values.

        try:
            obj = quantities.Quantity(eval(self._internal_unit),
                                      ucomponents.UncertainInput(self.power, self.power * swr_err))
        except (AssertionError, NameError):
            self.power, self.unit = self.convert.c2scuq(self._internal_unit, float(self.power))
            obj = quantities.Quantity(self.unit,
                                      ucomponents.UncertainInput(self.power, self.power * swr_err))
        return self.error, obj  # TODO: include other uncertainties

    def GetDataNB(self, retrigger=None):
        """
        Non-blocking version of :meth:`GetData`.
        
        This function returns ``(-1, None)`` until the answer from the device is available.
        Then``self.error, obj)``.
        
        If *retrigger* is ``True`` or ``'on'``, the device is triggered for a new measurment after the measurement has been 
        red.
        """

        dct = self.query("STAT:OPER:MEAS:SUMM:COND?", r'(?P<stat>.*)')  # Answer if the sensor* ist measuring or
        stat = int(dct['stat'])  # it has data.
        retrigger = retrigger
        if retrigger == 'True':
            retrigger = 1
        elif retrigger == 'on':
            retrigger = 1
        else:
            retrigger = 0

        if not ((stat & self.mask) | self._data_):  # When the sensor not measuring, it starts
            self.Trigger()  # one measuring.
            time.sleep(.01)
            dct = self.query("STAT:OPER:MEAS:SUMM:COND?", r'(?P<stat>.*)')
            stat = int(dct['stat'])
            if not (stat & self.mask):
                dct = self.query("FETCH%d?" % self.channel, r'(?P<val>%s)' % self._FP)  # The last valid result
                v = float(dct['val'])  # is returned.
                swr_err = self.get_standard_mismatch_uncertainty()
                self.power = v
                dct = self.query("UNIT%d:POW?" % self.channel, r'(?P<unit>.*)')  # Ask for the unit of
                self._internal_unit = dct['unit']  # the measured values.

                try:
                    obj = quantities.Quantity(eval(self._internal_unit),
                                              ucomponents.UncertainInput(self.power, self.power * swr_err))
                except (AssertionError, NameError):
                    self.power, self.unit = self.convert.c2scuq(self._internal_unit, float(self.power))
                    obj = quantities.Quantity(self.unit,
                                              ucomponents.UncertainInput(self.power, self.power * swr_err))
                if retrigger:
                    self.Trigger()
                    self._data_ = 1
                else:
                    self._data_ = 0
                return self.error, obj
            else:
                self._data_ = 1
                self.error = -1
                obj = None
                return self.error, obj

        else:
            dct = self.query("FETCH%d?" % self.channel, r'(?P<val>%s)' % self._FP)  # The last valid result
            v = float(dct['val'])  # is returned.
            swr_err = self.get_standard_mismatch_uncertainty()
            self.power = v
            dct = self.query("UNIT%d:POW?" % self.channel, r'(?P<unit>.*)')  # Ask for the unit of
            self._internal_unit = dct['unit']  # the measured values.

        try:
            obj = quantities.Quantity(eval(self._internal_unit),
                                      ucomponents.UncertainInput(self.power, self.power * swr_err))
        except (AssertionError, NameError):
            self.power, self.unit = self.convert.c2scuq(self._internal_unit, float(self.power))
            obj = quantities.Quantity(self.unit,
                                      ucomponents.UncertainInput(self.power, self.power * swr_err))
        if retrigger:
            self.Trigger()
            self._data_ = 1
        else:
            self._data_ = 0
        return self.error, obj  # TODO: include other uncertainties

    def Reset(self):
        """
        Reset of device.
        Sets the device to the defined default state
        """
        self.error = 0
        self.write('*RST')
        return self.error

    def SelfTestQuery(self):
        """
        It makes a selftest.  
        
        Return: self.error = 0  no error found
                self.error = 1 an error has occurred 
        """
        self.error = 0
        dct = self.query('*TST?', r'(?P<test>.*)')
        test = int(dct['test'])
        self.error = test
        return self.error

    def MEAS(self):
        """
        it makes only a one measuring
        """
        self.error = 0
        dct = self.query('MEAS?', r'(?P<val>.*)')
        val = float(dct['val'])
        dct = self.query("UNIT%d:POW?" % self.channel, r'(?P<unit>.*)')
        self._internal_unit = dct['unit']
        return val, self._internal_unit

        #                                  /

    def Unit(self, ch, unit):  # Selects the output unit          |      DBM, W,
        channel = ch  # for the measured power values.   |      DBUV
        unit = unit  # \
        self.write("UNIT%d:POW %s" % (channel, unit))
        self._internal_unit = unit
        return


def test_init(ch):
    import io
    from mpylab.tools.util import format_block

    ini = format_block("""
                    [DESCRIPTION]
                    description: 'Rohde&Schwarz NRP Power Meter'
                    type:        'POWERMETER'
                    vendor:      'Rohde&Schwarz'
                    serialnr:
                    deviceid:
                    driver: pm_rs_nrp.py

                    [Init_Value]
                    fstart: 10e6
                    fstop: 18e9
                    fstep: 0
                    gpib: 22
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

                    [Channel_2]
                    name: B
                    unit: 'W'
                    """)

    ini = io.StringIO(ini)
    inst = POWERMETER()
    inst.Init(ini, ch)
    return inst


def main():
    import io
    import sys
    from mpylab.tools.util import format_block
    from mpylab.device.powermeter_ui import UI as UI

    try:
        ini = sys.argv[1]
    except IndexError:
        ini = format_block("""
                        [DESCRIPTION]
                        description: 'Rohde&Schwarz NRP Power Meter'
                        type:        'POWERMETER'
                        vendor:      'Rohde&Schwarz'
                        serialnr:
                        deviceid:
                        driver: pm_rs_nrp.py

                        [Init_Value]
                        fstart: 10e6
                        fstop: 18e9
                        fstep: 0
                        gpib: 21
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

                        [Channel_2]
                        name: B
                        unit: 'W'
                        """)

    ini = io.StringIO(ini)

    pm = POWERMETER()
    ui = UI(pm, ini=ini)
    ui.configure_traits()
    # pm.Init(ini,ch)
    return pm


if __name__ == '__main__':
    import sys
    main()
    sys.exit()
    pm1 = test_init(1)
    # pm1.update_internal_unit(None,'DB')
    pm1.InitSen(1)
    print((pm1.GetDataNB()))
    print((pm1.GetDataNB()))
    print((pm1.GetDataNB('True')))
    print((pm1.GetDataNB()))
    # pm1.Zero()
    # print pm1.Reset()
    # print pm1.SetFreq(10.0)
    # for i in range(3):
    # print pm1.MEAS()
    # print pm1.GetDescription()
    # print pm1.SelfTestQuery()
    # print "PM1", pm1.GetData()
    # print pm1._cmds
    # print 'ini fertig'
    # pm2=test_init(2)
    # pm1.SetFreq(10e2)######
    # for i in range(3):
    # pm1.Trigger()
    # print "PM1", pm1.GetData()
    # pm1.GetData()
    #   pm2.Trigger()
    #   print "PM2", pm2.GetData()
    # pm2.Quit()
    #    for i in range(5):
    #        pm1.Trigger()
    #        print "PM1", pm1.GetData()
    # pm2=test_init(2)
    #    for i in range(5):
    #        pm1.Trigger()
    #        print "PM1", pm1.GetData()
    #        pm2.Trigger()
    #        print "PM2", pm2.GetData()
    # time.sleep(5)
    pm1.Quit()
#    pm2.Quit()
