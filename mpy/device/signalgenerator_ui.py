# -*- coding: utf-8 -*-

import StringIO
#from mpy.device.signalgenerator import SIGNALGENERATOR
import enthought.traits.api as tapi
import enthought.traits.ui.api as tuiapi
import enthought.traits.ui.menu as tuim

from mpy.tools.util import format_block

std_ini=format_block("""
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
std_ini=StringIO.StringIO(std_ini)



class UI(tapi.HasTraits):
    RF_on=tapi.Str('RF unknown')
    RF=tapi.Button('RF On/Off')
    Init=tapi.Button()
    INI=tapi.Str()
    FREQ=tapi.Float()
    
    def __init__(self, instance, ini=None):
        self.sg=instance
        if not ini:
            ini=std_ini
        self.ini=ini
        self.INI=ini.read()
    
    def _Init_fired(self):
        ini=StringIO.StringIO(self.INI)
        self.sg.Init(ini)
        self.RF_is_on=(self.sg.conf['channel_1']['outputstate'] in ('1','on'))
        self.update_rf()

    def _RF_fired(self):
        self.RF_is_on=not(self.RF_is_on)
        if self.RF_is_on:
            self.sg.RFOn()
        else:
            self.sg.RFOff()
        self.update_rf()
            
    def _FREQ_fired(self):
        self.sg.SetFreq(self.FREQ)
            
    def update_rf(self):
        if self.RF_is_on:
            self.RF_on='RF is On'
        else:
            self.RF_on='RF is Off'
            
    RF_grp=tuiapi.Group(tuiapi.Item('RF_on', show_label=False,style='readonly'), 
                        tuiapi.Item('RF', show_label=False),
                        label='RF')
    INI_grp=tuiapi.Group(tuiapi.Item('INI', style='custom',springy=True,width=500,height=500,show_label=False),
                         tuiapi.Item('Init', show_label=False),
                         label='Ini')
    FREQ_grp=tuiapi.Group(tuiapi.Item('FREQ'),label='Freq')
    
    traits_view=tuiapi.View(tuiapi.Group(
                                tuiapi.Group(INI_grp, FREQ_grp,layout='tabbed'), 
                                RF_grp, layout='normal'), title="Signalgenerator", buttons=[tuim.CancelButton])