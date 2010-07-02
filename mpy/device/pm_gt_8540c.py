# -*- coding: utf-8 -*-

import sys
import StringIO
import visa

from scuq import *
from mpy.device.powermeter2c import POWERMETER as PWRMTR
#import pprint


class POWERMETER(PWRMTR):
    def __init__(self):
        PWRMTR.__init__(self)
        self._internal_unit='dBm'
        self.ch_tup=('','A','B')
        self._cmds={'SetFreq':  [("'%sE FR %s HZ'%(self.ch_tup[self.channel], freq)", None)],
                    'GetFreq':  [],
                    'GetData':  [("'%sP'%self.ch_tup[self.channel]", r'(?P<power>%s)'%self._FP)],
                    'GetDataNB':  [("'%sP'%self.ch_tup[self.channel]", r'(?P<power>%s)'%self._FP)],
                    'Trigger': [('TR2', None)],
                    'ZeroOn':  [("'%sE ZE'%self.ch_tup[self.channel]", None)],
                    'ZeroOff':  [],
                    'Quit':     [],
                    'GetDescription': [('*IDN?', r'(?P<IDN>.*)')]}

    def GetData(self):
        self.error, power=super(POWERMETER, self).GetData()
        #relerr=self._calc_rel_err(power)
        #power=quantities.Quantity(power._unit, ucomponents.UncertainInput(power._value, power._value*0.01))
        return self.error, power

    def Zero(self, state='on'):
        self.error, stat=super(POWERMETER, self).Zero(state)
        complete=False
        while not complete:
            ans=self.dev.ask('*STB?')
            #print ans
            complete=int(ans) & 0b10
        return self.error, stat
        
    def _get_sensor_type(self):
        """
        return the type of the attached sensor as a string.
        """
        cmd="TEST EEPROM %s TYPE?"%self.ch_tup[self.channel]
        tmpl='(?P<SENSOR>\\d+)'
        dct=self.query(cmd, tmpl)
        return dct['SENSOR']
        
    def Init(self, ini=None, channel=None):
        #self.term_chars=visa.LF
        if channel is None:
            self.channel=1
        else:
            self.channel=channel
        self.error=PWRMTR.Init(self, ini, self.channel)
        sec='channel_%d'%self.channel
        try:
            self.levelunit=self.conf[sec]['unit']
        except KeyError:
            self.levelunit=self._internal_unit
        
        self._sensor=self._get_sensor_type()
        
        self._cmds['Preset']=[('PR', None),
                              ('TR3', None),
                              ('self.Zero()', None)]
        # key, vals, actions
        presets=[('filter', [], [])]

        for k, vals, actions in presets:
            #print k, vals, actions
            try:
                v=self.conf[sec][k]
                #print sec, k, v
                if (vals is None):  # no comparision
                    #print actions[0], self.convert.c2c(self.levelunit, self._internal_unit, float(v)), float(v), self.levelunit
                    #print eval(actions[0])
                    self._cmds['Preset'].append((eval(actions[0]),actions[1]))
                else:
                    for idx,vi in enumerate(vals):
                        if v.lower() in vi:
                            self._cmds['Preset'].append(actions[idx])
            except KeyError:
                pass
        dct=self._do_cmds('Preset', locals())
        self._update(dct)
        self.update_internal_unit()        
        #pprint.pprint(self._cmds)
        return self.error 

    def update_internal_unit(self):
        #get internal unit
        if self.dev:
            tup=('W','dBm','%','dB')
            ans=self.dev.ask('%sP SM'%self.ch_tup[self.channel])
            ans=int(ans[-1])
            self._internal_unit=tup[ans]

def main():
    import StringIO
    from mpy.tools.util import format_block
    from mpy.device.powermeter_ui import UI as UI

    try:
        ini=sys.argv[1]
    except IndexError:
        ini=format_block("""
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
        ini=StringIO.StringIO(ini)

    pm=POWERMETER()	
    ui=UI(pm,ini=ini)
    ui.configure_traits()
    
if __name__ == '__main__':
    main()
