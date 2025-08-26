# -*- coding: utf-8 -*-

import io

import traits.api as tapi
from traits.etsconfig.api import ETSConfig

ETSConfig.toolkit = "wx"
import traitsui.api as tuiapi
import traitsui.menu as tuim

from mpylab.tools.util import format_block
from mpylab.device.device import CONVERT

conv = CONVERT()

std_ini = format_block("""
                [DESCRIPTION]
                description: 'FP TEMPLATE'
                type:        'FIELDPROBE'
                vendor:      'Some Vendor'
                serialnr:
                deviceid:
                driver:

                [Init_Value]
                fstart: 3e6
                fstop: 18e9
                fstep: 0
                gpib: 4
                virtual: 0

                [Channel_1]
                name: EField
                unit: Voverm
                """)
std_ini = io.StringIO(std_ini)


class UI(tapi.HasTraits):
    CHANNEL = tapi.Int(1)
    Init = tapi.Button()
    INI = tapi.Str()
    TRIGGER = tapi.Button('Trigger')
    FREQ = tapi.Float(1e6)
    POWER = tapi.Str()

    def __init__(self, instance, ini=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.dev = instance
        if not ini:
            ini = std_ini
        self.ini = ini
        self.INI = ini.read()

    def _Init_fired(self):
        ini = io.StringIO(self.INI)
        self.ch = self.CHANNEL
        self.dev.Init(ini, self.ch)
        self.unit = self.dev.conf['channel_%d' % self.ch]['unit']
        self._FREQ_changed()

    def _TRIGGER_fired(self):
        self.dev.Trigger()
        err, data = self.dev.GetData()
        # ctx=Context()
        # v,e,u=ctx.value_uncertainty_unit(data)
        # self.POWER=str(10*log10(v*1000))
        self.POWER = str(data)

    def _FREQ_changed(self):
        self.pm.SetFreq(self.FREQ)

    def _CHANNEL_changed(self):
        self.pm.Quit()
        self._Init_fired()

    POWER_grp = tuiapi.Group(tuiapi.Item('POWER'), label='Power')

    INI_grp = tuiapi.Group(tuiapi.Item('INI', style='custom', springy=True, width=500, height=200, show_label=False),
                           tuiapi.Item('CHANNEL'),
                           tuiapi.Item('Init', show_label=False),
                           label='Ini')
    FREQ_grp = tuiapi.Group(tuiapi.Item('FREQ'), label='Freq')
    # LEVEL_grp=tuiapi.Group(tuiapi.Item('LEVEL'), label='Level')

    traits_view = tuiapi.View(tuiapi.Group(
        tuiapi.Group(INI_grp, FREQ_grp, layout='tabbed'),
        tuiapi.Item('TRIGGER'),
        POWER_grp, layout='normal'), title="Fieldprobe", buttons=[tuim.CancelButton])
