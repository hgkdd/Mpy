# -*- coding: utf-8 -*-
import time
import StringIO
from scuq import *
from mpy.device.powermeter import POWERMETER as PWRMTR
    
class POWERMETER(PWRMTR):
    """
    Driver for the R&S NRP
    """
    def __init__(self, **kw):
        PWRMTR.__init__(self, **kw)
        self._internal_unit='dBm'

        self._cmds={'SetFreq':  [("'SENS%d:FREQ:CW %f HZ'%(self.channel, freq)", None)],
                    'GetFreq':  [("'SENS%d:FREQ:CW?'%(self.channel)", r'(?P<freq>%s)'%self._FP)],
                    'Trigger': [("'INIT%d:IMM'%(self.channel)", None)],
                    'ZeroOn':  [],
                    'ZeroOff':  [],
                    'Quit':     [],
                    'GetDescription': [('*IDN?', r'(?P<IDN>.*)')]}

    def Zero(self, state='on'):
        self.error=0
        return self.error,0
        
    def Init(self, ini=None, channel=None):
        #self.term_chars=visa.LF
        if channel is None:
            self.channel=1
        else:
            self.channel=channel
        masks=(2,4,8,16)
        self.mask=masks[self.channel-1]

        self.error=PWRMTR.Init(self, ini, self.channel)

        sec='channel_%d'%self.channel
        try:
            self.levelunit=self.conf[sec]['unit']
        except KeyError:
            self.levelunit=self._internal_unit
            
        self._cmds['Preset']=[("INIT%d:CONT OFF"%self.channel, None),
                              ("SENS%d:AVER:STAT OFF"%self.channel, None)]
        #self._cmds['Preset'].append(('self.Zero("on")', None))  # Zero Channel
            
        # key, vals, actions
        presets=[('filter', [], [])]   # TODO: fill with information from ini-file

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
        return self.error 
        
    def GetData(self):
        self.Trigger()
        finished=False
        while not finished:
            time.sleep(.01)
            dct=self.query("STAT:OPER:MEAS:SUMM:COND?", r'(?P<stat>.*)')
            stat=int(dct['stat'])
            if not (stat & self.mask):
                finished=True

        dct=self.query("FETCH%d?"%self.channel, r'(?P<val>%s)'%self._FP)
        v=float(dct['val'])
        swr_err=self.get_standard_mismatch_uncertainty()
        self.power=v
        dct=self.query("UNIT%d:POW?"%self.channel, r'(?P<unit>.*)')
        self._internal_unit=dct['unit']
        
        try:
            obj=quantities.Quantity(eval(self._internal_unit), 
                                    ucomponents.UncertainInput(self.power, self.power*swr_err))
        except (AssertionError, NameError):
            self.power,self.unit=self.convert.c2scuq(self._internal_unit, float(self.power))
            obj=quantities.Quantity(self.unit, 
                                    ucomponents.UncertainInput(self.power, self.power*swr_err))
        return self.error, obj  # TODO: include other uncertainties
        
    def GetDataNB(self, retrigger):
        self.err, v = self.GetData()
        if retrigger:
            self.Trigger()
        return self.error, v


def test_init(ch):
    import StringIO
    from mpy.tools.util import format_block
    inst=POWERMETER()
    ini=format_block("""
                    [DESCRIPTION]
                    description: 'Rohde&Schwarz NRP Power Meter'
                    type:        'POWERMETER'
                    vendor:      'RHode&Schwarz'
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
                    swr1: 1.1
                    swr2: 1.1

                    [Channel_2]
                    name: B
                    unit: 'W'
                    """)
    ini=StringIO.StringIO(ini)
    inst.Init(ini,ch)
    return inst
            
def main():
    import StringIO
    from mpy.tools.util import format_block
    from mpy.device.powermeter_ui import UI as UI

    try:
        ini=sys.argv[1]
    except IndexError:
        ini=format_block("""
                        [DESCRIPTION]
                        description: 'Rohde&Schwarz NRP Power Meter'
                        type:        'POWERMETER'
                        vendor:      'RHode&Schwarz'
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
        ini=StringIO.StringIO(ini)

    pm=POWERMETER()	
    ui=UI(pm,ini=ini)
    ui.configure_traits()
    
if __name__ == '__main__':
#    main()
    pm1=test_init(1)
    #pm2=test_init(2)
    pm1.SetFreq(10e6)
    for i in range(5):
        pm1.Trigger()
        print "PM1", pm1.GetData()
     #   pm2.Trigger()
     #   print "PM2", pm2.GetData()
    #pm2.Quit()
#    for i in range(5):
#        pm1.Trigger()
#        print "PM1", pm1.GetData()
    #pm2=test_init(2)
#    for i in range(5):
#        pm1.Trigger()
#        print "PM1", pm1.GetData()
#        pm2.Trigger()
#        print "PM2", pm2.GetData()
    #time.sleep(5)
    pm1.Quit()
#    pm2.Quit()
