# -*- coding: utf-8 -*-

import sys
import StringIO
import visa

from scuq import *
from mpy.device.powermeter import POWERMETER
#import pprint


class GT8540C(POWERMETER):
    def __init__(self):
        POWERMETER.__init__(self)
        self._internal_unit='dBm'
        self.ch_tup=('','A','B')
        self._cmds={'SetFreq':  [("'%sE FR %s HZ'%(self.ch_tup[self.channel], freq)", None)],
                    'GetFreq':  [],
                    'GetData':  [("'%sP'%self.ch_tup[self.channel]", r'(?P<power>%s)'%self._FP)],
                    'GetDataNB':  [("'%sP'%self.ch_tup[self.channel]", r'(?P<power>%s)'%self._FP)],
                    'Trigger': [],
                    'ZeroOn':  [("'%sE ZE'%self.ch_tup[self.channel]", None)],
                    'ZeroOff':  [],
                    'Quit':     [],
                    'GetDescription': [('*IDN?', r'(?P<IDN>.*)')]}

    def Init(self, ini=None, channel=None):
        #self.term_chars=visa.LF
        if channel is None:
            self.channel=1
        else:
            self.channel=channel
        self.error=POWERMETER.Init(self, ini, self.channel)
        sec='channel_%d'%self.channel
        try:
            self.levelunit=self.conf[sec]['unit']
        except KeyError:
            self.levelunit=self._internal_unit
            
        self._cmds['Preset']=[]
        # key, vals, actions
        presets=[]

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
        #get internal unit
        if self.dev:
            tup=('W','dBm','%','dB')
            ans=self.dev.ask('%sP SM'%self.ch_tup[self.channel])
            ans=int(ans[-1])
            self._internal_unit = tup[ans]
        
        #pprint.pprint(self._cmds)
        return self.error 
    

def main():
    from mpy.tools.util import format_block

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
                        unit: 'W'

                        [Channel_2]
                        name: B
                        unit: 'W'
                        """)
        

    fr=300e6

    pm1=GT8540C()
    pm2=GT8540C()
    err=pm1.Init(StringIO.StringIO(ini), 1)
    err=pm2.Init(StringIO.StringIO(ini), 2)

    err,freq=pm1.SetFreq(fr)
    err,freq=pm2.SetFreq(fr)

    while(True):
        err,lv1=pm1.GetData()
        err,lv2=pm2.GetData()
        print lv1, lv2
    err=pm1.Quit()
    err=pm2.Quit()
    
if __name__ == '__main__':
    main()
