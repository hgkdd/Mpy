# -*- coding: utf-8 -*-

import StringIO
import enthought.traits.api as tapi
import enthought.traits.ui.api as tuiapi
import enthought.traits.ui.menu as tuim

from scuq.quantities import Quantity
from mpy.tools.util import format_block
from mpy.device.device import CONVERT

conv=CONVERT()

std_ini=format_block("""
                [DESCRIPTION]
                description: PM template
                type:        POWERMETER
                vendor:      some company
                serialnr:    SN12345
                deviceid:    internal ID
                driver:      dummy.py

                [Init_Value]
                fstart: 100e3
                fstop: 18e9
                fstep: 1
                gpib: 13
                virtual: 0
                nr_of_channels: 2

                [Channel_1]
                name: A
                unit: 'W'

                [Channel_2]
                name: B
                unit: 'W'
                """)
std_ini=StringIO.StringIO(std_ini)


class UI(tapi.HasTraits):
    CHANNEL=tapi.Int(1)
    Init=tapi.Button()
    INI=tapi.Str()
    TRIGGER=tapi.Button('Trigger')
    FREQ=tapi.Float(1e6)
    
    def __init__(self, instance, ini=None):
        self.pm=instance
        if not ini:
            ini=std_ini
        self.ini=ini
        self.INI=ini.read()
    
    def _Init_fired(self):
        ini=StringIO.StringIO(self.INI)
        self.ch=self.CHANNEL
        self.pm.Init(ini,self.ch)
        self.unit=self.pm.conf['channel_%d'%self.ch]['unit']
        self._FREQ_changed()

    def _TRIGGER_fired(self):
        self.pm.Trigger()
            
    def _FREQ_changed(self):
        self.pm.SetFreq(self.FREQ)
        
    def _CHANNEL_changed(self):
        self.pm.Quit()
        self._Init_fired()
                        
    RF_grp=tuiapi.Group(tuiapi.Item('RF_on', show_label=False,style='readonly'), 
                        tuiapi.Item('RF', show_label=False),
                        label='RF')
    INI_grp=tuiapi.Group(tuiapi.Item('INI', style='custom',springy=True,width=500,height=200,show_label=False),
                         tuiapi.Item('Init', show_label=False),
                         label='Ini')
    FREQ_grp=tuiapi.Group(tuiapi.Item('FREQ'),label='Freq')
    LEVEL_grp=tuiapi.Group(tuiapi.Item('LEVEL'), label='Level')
    
    traits_view=tuiapi.View(tuiapi.Group(
                                tuiapi.Group(INI_grp, FREQ_grp, LEVEL_grp,layout='tabbed'),  
                                RF_grp, layout='normal'), title="Powermeter", buttons=[tuim.CancelButton])
