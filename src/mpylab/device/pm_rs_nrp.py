# -*- coding: utf-8 -*-

"""mpylab.device.pm_rs_nrp module."""
import time
from copy import deepcopy
from scuq import *
from mpylab.device.powermeter import POWERMETER as PWRMTR


class POWERMETER(PWRMTR):
    """
    Driver for the R&S NRP
    """
    conftmpl = deepcopy(PWRMTR.conftmpl)

    def __init__(self, **kw):
        PWRMTR.__init__(self, **kw)
        self._internal_unit = 'dBm'
        self._data_ = 0
        self.sensor = {}
        self._cmds = {'SetFreq': [],
                      'GetFreq': [],
                      'Trigger': [],
                      'ZeroOn': [],
                      'ZeroOff': [],
                      'Quit': [],
                      'Unit': [('UNIT{channel:d}:POW {unit}', None)],
                      'GetDescription': [('*IDN?', r'(?P<IDN>.*)')]}

    def _build_channel_cmds(self):
        self._cmds.update({
            'SetFreq': [(f'SENS{self.channel:d}:FREQ:CW {{freq:f}}', None)],
            'GetFreq': [(f'SENS{self.channel:d}:FREQ:CW?', rf'(?P<freq>{self._FP})')],
            'Trigger': [(f'INIT{self.channel:d}:IMM', None)],
            'ZeroOn': [(f'CAL{self.channel:d}:ZERO:AUTO ON', None)],
            'ZeroOff': [(f'CAL{self.channel:d}:ZERO:AUTO OFF', None)],
        })

    # def Zero(self, state='on'):
    # self.error=0
    # return self.error,0

    def Init(self, ini=None, channel=None):
        """Init method."""
        if channel is None:
            self.channel = 1
        else:
            self.channel = channel
        self._build_channel_cmds()
        masks = (2, 4, 8, 16)
        self.mask = masks[self.channel - 1]
        self.error = PWRMTR.Init(self, ini, self.channel)

        sec = f'channel_{self.channel}'
        try:
            self.levelunit = self.conf[sec]['unit']
        except KeyError:
            self.levelunit = self._internal_unit
        self._cmds['Preset'] = [('*RST', None),  # reset of device.
                                (f"INIT{self.channel}:CONT OFF", None),  # Selects either single-shot
                                (f"SENS{self.channel}:AVER:STAT OFF", None),  # deactivation of filter
                                (f"UNIT{self.channel}:POW DBM", None)]

        presets = [('filter', [], [])]  # TODO: fill with information from ini-file
        self._apply_presets(presets, sec)
        dct = self._do_cmds('Preset', locals())
        self._update(dct)
        return self.error

    def InitSen(self, channel=None):
        """InitSen method."""
        channel = channel
        dct = self.query("SYST:SENS{channel}:INFO?", r'(?P<inf>.*)')
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

        dct = self.query(f"FETCH{self.channel}?", rf'(?P<val>{self._FP})')  # The last valid result
        v = float(dct['val'])  # is returned.
        swr_err = self.get_standard_mismatch_uncertainty()
        self.power = v
        dct = self.query(f"UNIT{self.channel}:POW?", r'(?P<unit>.*)')  # Ask for the unit of
        self._internal_unit = dct['unit']  # the measured values.
        power_value = self.power
        iu = self._internal_unit
        if isinstance(iu, str):
            power_value, power_unit = self.convert.c2scuq(iu, power_value)  # iu ist a str 'dbm', ...
        elif isinstance(iu, units.Unit):  # iu is a scuq unit
            power_unit = iu
        else:
            raise TypeError(f"_internal_unit must be str or scuq Unit, got {type(iu).__name__}: {iu!r}")

        obj = quantities.Quantity(power_unit,
                                  ucomponents.UncertainInput(power_value, power_value * swr_err))
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
                dct = self.query(f"FETCH{self.channel}?", rf'(?P<val>{self._FP})')  # The last valid result
                v = float(dct['val'])  # is returned.
                swr_err = self.get_standard_mismatch_uncertainty()
                self.power = v
                dct = self.query(f"UNIT{self.channel}:POW?", r'(?P<unit>.*)')  # Ask for the unit of
                self._internal_unit = dct['unit']  # the measured values.

                power_value = self.power
                iu = self._internal_unit
                if isinstance(iu, str):
                    power_value, power_unit = self.convert.c2scuq(iu, power_value)  # iu ist a str 'dbm', ...
                elif isinstance(iu, units.Unit):  # iu is a scuq unit
                    power_unit = iu
                else:
                    raise TypeError(f"_internal_unit must be str or scuq Unit, got {type(iu).__name__}: {iu!r}")

                obj = quantities.Quantity(power_unit,
                                          ucomponents.UncertainInput(power_value, power_value * swr_err))
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
            dct = self.query(f"FETCH{self.channel}?", rf'(?P<val>{self._FP})')  # The last valid result
            v = float(dct['val'])  # is returned.
            swr_err = self.get_standard_mismatch_uncertainty()
            self.power = v
            dct = self.query(f"UNIT{self.channel}:POW?", r'(?P<unit>.*)')  # Ask for the unit of
            self._internal_unit = dct['unit']  # the measured values.

        power_value = self.power
        iu = self._internal_unit
        if isinstance(iu, str):
            power_value, power_unit = self.convert.c2scuq(iu, power_value)  # iu ist a str 'dbm', ...
        elif isinstance(iu, units.Unit):  # iu is a scuq unit
            power_unit = iu
        else:
            raise TypeError(f"_internal_unit must be str or scuq Unit, got {type(iu).__name__}: {iu!r}")

        obj = quantities.Quantity(power_unit,
                                  ucomponents.UncertainInput(power_value, power_value * swr_err))

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
        dct = self.query(f"UNIT{self.channel}:POW?", r'(?P<unit>.*)')
        self._internal_unit = dct['unit']
        return val, self._internal_unit

        #                                  /

    def Unit(self, ch, unit):  # Selects the output unit          |      DBM, W,
        """Unit method."""
        channel = ch  # for the measured power values.   |      DBUV
        unit = unit  # \
        self.write("UNIT{channel}:POW {unit}")
        self._internal_unit = unit
        return


def test_init(ch):
    """test_init function."""
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
    """main function."""
    import io
    import sys
    from mpylab.tools.util import format_block
    from mpylab.device.powermeter_ui import PowerMeterWidget as UI

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
