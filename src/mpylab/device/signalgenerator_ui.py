# -*- coding: utf-8 -*-

import io
# from mpylab.device.signalgenerator import SIGNALGENERATOR
import traits.api as tapi
from traits.etsconfig.api import ETSConfig
ETSConfig.toolkit = "wx"
import traitsui.api as tuiapi
import traitsui.menu as tuim
from scuq.quantities import Quantity
from mpylab.tools.util import format_block
from mpylab.device.device import CONVERT

conv = CONVERT()

std_ini = format_block("""
                [DESCRIPTION]
                description: SG template
                type:        SIGNALGENERATOR
                vendor:      some company
                serialnr:    SN12345
                deviceid:    internal ID
                driver:      dummy.py

                [Init_Value]
                fstart: 100e6
                fstop: 18e9
                fstep: 1
                gpib: 15
                virtual: 0

                [Channel_1]
                name: RFOut
                level: -100
                unit: 'dBm'
                outpoutstate: 0
                """)
std_ini = io.StringIO(std_ini)


class UI(tapi.HasTraits):
    RF_on = tapi.Str('RF unknown')
    RF = tapi.Button('RF On/Off')
    Init = tapi.Button()
    INI = tapi.Str()
    FREQ = tapi.Float()
    LEVEL = tapi.Range(-100., 0.)
    AM = tapi.Button('AM On/Off')
    AM_on = tapi.Str('AM is Off')
    AMFREQ = tapi.Float(1000)
    AMDEPTH = tapi.Range(0., 1.0, 0.8)
    AMWAVE = tapi.Enum(('SINE', 'SQUARE', 'TRIANGLE'))
    AMSOURCE = tapi.Enum(('INT1', 'INT2', 'EXT1', 'EXT2'))

    PM = tapi.Button('PM On/Off')
    PM_on = tapi.Str('PM is Off')
    PMFREQ = tapi.Float(1000)
    PMWIDTH = tapi.Float(100e-6)
    PMDELAY = tapi.Float(0)
    PMPOL = tapi.Enum(('NORMAL', 'INVERTED'))
    PMSOURCE = tapi.Enum(('INT', 'EXT1', 'EXT2'))

    LFOUT = tapi.Enum(('OFF', 'ON'))
    int_unit = 'dBm'

    def __init__(self, instance, ini=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.sg = instance
        if not ini:
            ini = std_ini
        self.ini = ini
        self.INI = ini.read()

    def _Init_fired(self):
        ini = io.StringIO(self.INI)
        self.sg.Init(ini)
        self.RF_is_on = (self.sg.conf['channel_1']['outputstate'] in ('1', 'on'))
        self.AM_is_on = False
        self.PM_is_on = False
        self.level = self.sg.conf['channel_1']['level']
        self.unit = self.sg.conf['channel_1']['unit']
        self.level = conv.c2c(self.unit, self.int_unit, self.level)
        self.LEVEL = self.level
        self.amfreq = 1e3
        self.amdepth = 0.8
        self.amwave = 'SINE'
        self.amsource = 'INT1'
        self.lfout = 'Off'
        self.pmfreq = 1000
        self.pmwith = 100e-6
        self.pmdelay = 0
        self.pmsource = 'INT'
        self.pmpol = 'NORMAL'

        self.update_rf()

    def _RF_fired(self):
        self.RF_is_on = not (self.RF_is_on)
        if self.RF_is_on:
            self.sg.RFOn()
        else:
            self.sg.RFOff()
        self.update_rf()

    def _AM_fired(self):
        self.AM_is_on = not (self.AM_is_on)
        if self.AM_is_on:
            self.sg.AMOn()
        else:
            self.sg.AMOff()
        self.update_am()

    def _PM_fired(self):
        self.PM_is_on = not (self.PM_is_on)
        if self.PM_is_on:
            self.sg.PMOn()
        else:
            self.sg.PMOff()
        self.update_pm()

    def _FREQ_changed(self):
        self.sg.SetFreq(self.FREQ)

    def _LEVEL_changed(self):
        self.level = self.LEVEL
        lv, unit = conv.c2scuq(self.int_unit, self.level)
        self.sg.SetLevel(Quantity(unit, lv))

    def _AMFREQ_changed(self):
        self.amfreq = self.AMFREQ
        self.sg.ConfAM(self.amsource, self.amfreq, self.amdepth, self.amwave, self.lfout)

    def _AMDEPTH_changed(self):
        self.amdepth = self.AMDEPTH
        self.sg.ConfAM(self.amsource, self.amfreq, self.amdepth, self.amwave, self.lfout)

    def _AMWAVE_changed(self):
        self.amwave = self.AMWAVE
        self.sg.ConfAM(self.amsource, self.amfreq, self.amdepth, self.amwave, self.lfout)

    def _AMSOURCE_changed(self):
        self.amsource = self.AMSOURCE
        self.sg.ConfAM(self.amsource, self.amfreq, self.amdepth, self.amwave, self.lfout)

    def _LFOUT_changed(self):
        self.lfout = self.LFOUT
        self.sg.ConfAM(self.amsource, self.amfreq, self.amdepth, self.amwave, self.lfout)

    def _PMFREQ_changed(self):
        self.pmfreq = self.PMFREQ
        self.sg.ConfPM(self.pmsource, self.pmfreq, self.pmpol, self.pmwidth, self.pmdelay)

    def _PMSOURCE_changed(self):
        self.pmsource = self.PMSOURCE
        self.sg.ConfPM(self.pmsource, self.pmfreq, self.pmpol, self.pmwidth, self.pmdelay)

    def _PMWIDTH_changed(self):
        self.pmwidth = self.PMWIDTH
        self.sg.ConfPM(self.pmsource, self.pmfreq, self.pmpol, self.pmwidth, self.pmdelay)

    def _PMPOL_changed(self):
        self.pmpol = self.PMPOL
        self.sg.ConfPM(self.pmsource, self.pmfreq, self.pmpol, self.pmwidth, self.pmdelay)

    def _PMDELAY_changed(self):
        self.pmdelay = self.PMDELAY
        self.sg.ConfPM(self.pmsource, self.pmfreq, self.pmpol, self.pmwidth, self.pmdelay)

    def update_rf(self):
        if self.RF_is_on:
            self.RF_on = 'RF is On'
        else:
            self.RF_on = 'RF is Off'

    def update_am(self):
        if self.AM_is_on:
            self.AM_on = 'AM is On'
        else:
            self.AM_on = 'AM is Off'

    def update_pm(self):
        if self.PM_is_on:
            self.PM_on = 'PM is On'
        else:
            self.PM_on = 'PM is Off'

    RF_grp = tuiapi.Group(tuiapi.Item('RF_on', show_label=False, style='readonly'),
                          tuiapi.Item('RF', show_label=False),
                          label='RF')
    INI_grp = tuiapi.Group(tuiapi.Item('INI', style='custom', springy=True, width=500, height=200, show_label=False),
                           tuiapi.Item('Init', show_label=False),
                           label='Ini')
    FREQ_grp = tuiapi.Group(tuiapi.Item('FREQ'), label='Freq')
    LEVEL_grp = tuiapi.Group(tuiapi.Item('LEVEL'), label='Level')
    AM_grp = tuiapi.Group(tuiapi.Item('AMSOURCE'),
                          tuiapi.Item('AMFREQ'),
                          tuiapi.Item('AMDEPTH'),
                          tuiapi.Item('AMWAVE'),
                          tuiapi.Item('LFOUT'),
                          tuiapi.Item('AM_on', show_label=False, style='readonly'),
                          tuiapi.Item('AM', show_label=False), label='AM')
    PM_grp = tuiapi.Group(tuiapi.Item('PMSOURCE'),
                          tuiapi.Item('PMFREQ'),
                          tuiapi.Item('PMWIDTH'),
                          tuiapi.Item('PMDELAY'),
                          tuiapi.Item('PMPOL'),
                          tuiapi.Item('PM_on', show_label=False, style='readonly'),
                          tuiapi.Item('PM', show_label=False), label='PM')

    traits_view = tuiapi.View(tuiapi.Group(
        tuiapi.Group(INI_grp, FREQ_grp, LEVEL_grp, AM_grp, PM_grp, layout='tabbed'),
        RF_grp, layout='normal'), title="Signalgenerator", buttons=[tuim.CancelButton])
