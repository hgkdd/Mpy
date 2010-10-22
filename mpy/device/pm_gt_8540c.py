# -*- coding: utf-8 -*-

import sys
import time
from collections import defaultdict, namedtuple
import numpy as np
import StringIO
import visa
from scuq import *
from mpy.device.powermeter import POWERMETER as PWRMTR

#import pprint

def linav_dB(dbvals):
    """
    Input: sequence of dB-scaled values
    Output: dB-scaled lin-average of the input sequence
    
    Example: linav_dB([0,-10]) -> -0.301
    """
    linmean=np.mean(np.power(10., 0.1*dbvals))
    return 10*np.log10(linmean)

def linav_lin(linvals):
    """
    Input: sequence of lin-scaled values
    Output: lin-scaled lin-average of the input sequence
    
    Example: linav_lin([0,-10]) -> -5
    """
    linmean=np.mean(linvals)
    return linmean


CH_INST=namedtuple('CH_INST', ['master', 'slave'])    
    
class POWERMETER(PWRMTR):
    """
    Driver for the Gigatronics 854X powermeter
    """
    registry=defaultdict(lambda: CH_INST)
    lasttrigger=None
    def __init__(self):
        PWRMTR.__init__(self)
        self.master=False
        self.other=None
        self._internal_unit='dBm'
        self.linav=linav_dB
        self.ch_tup=('','A','B')
        self._cmds={'SetFreq':  [("'%sE FR %s HZ'%(self.ch_tup[self.channel], freq)", None)],
                    'GetFreq':  [],
                    'ZeroOn':  [("'%sE ZE'%self.ch_tup[self.channel]", None)],
                    'ZeroOff':  [],
                    'Quit':     [],
                    'GetDescription': [('*IDN?', r'(?P<IDN>.*)')]}

    def _get_sensor_type(self):
        """
        return the type of the attached sensor as a string.
        """
        self._fbuf_off()
        cmd="TEST EEPROM %s TYPE?"%self.ch_tup[self.channel]
        tmpl='(?P<SENSOR>\\d+)'
        dct=self.query(cmd, tmpl)
        self._fbuf_on()
        return dct['SENSOR']

    def _fbuf_on(self):
        self.write('FBUF PRE GET BUFFER %d'%self.N)
    def _fbuf_off(self):
        self.write('FBUF OFF')

    def Zero(self, state='on'):
        self.error=0
        self._fbuf_off()
        self.error,_= PWRMTR.Zero(self, state=state)
        self._fbuf_on()
        return self.error,0

    def _register(self):
        R=POWERMETER.registry[self.reghash]
        if isinstance(R.master, POWERMETER):   # master already registered for this gpib address
            if isinstance(R.slave, POWERMETER): # slave allready registered
                raise UserWarning('Already two instances for GPIB Address in use.')
                return -1
            else:
                R.slave=self # register as slave
                self.master=False
                self.other=R.master
                self.other.other=self
                self.read=self.other.read
                self.write=self.other.write
                self.query=self.other.query
        else:  # no master registered
            R.master=self
            self.master=True
            if isinstance(R.slave, POWERMETER):
                self.other=R.slave  # strange. should not happen!!
                self.other.other=self
            else:
                self.other=None
                self.other=None
        #print
        #print "Register:"
        #print "Master:", R.master, "Slave:", R.slave
        #print self, self.master, self.other
        return 0
                
    def _deregister(self):
        R=POWERMETER.registry[self.reghash]
        if self.master:  # deregister master
            if not self.other:  # no other instance present
                R.master=None
            else:
                self.other.other=None
                self.other.master=True
                R.master=self.other
                R.slave=None
        else: # deregister slave
            self.other.other=None
            R.slave=None
        #print
        #print "Deregister:"
        #print "Master:", R.master, "Slave:", R.slave
        #print self, self.master, self.other
        
    def Init(self, ini=None, channel=None, N=10, trg_threshold=0):
        self.N=N
        self.trg_threshold=trg_threshold
        #self.term_chars=visa.LF
        if channel is None:
            self.channel=1
        else:
            self.channel=channel

        try:    
            # read gpib address fom ini-file to register instance
            self.get_config(ini, channel)
            if self.conf['init_value']['virtual']:
                self.reghash=-1
            else:
                self.reghash=self.conf['init_value']['gpib']   # key for the class-registry

            self.error=self._register()   # registzer this instance

            self.value=None        
            if self.master:
                self.error=PWRMTR.Init(self, ini, self.channel)  # run init from parent class
            else:
                self.dev=self.other.dev  # use physical device of master
                self.error=0

            sec='channel_%d'%self.channel
            try:
                self.levelunit=self.conf[sec]['unit']
            except KeyError:
                self.levelunit=self._internal_unit
            
            
            if self.master:
                self._cmds['Preset']=[('PR', None)]
            else:
                self._cmds['Preset']=[]
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
            self.update_internal_unit()

            self._sensor=self._get_sensor_type()
            time.sleep(.7)
            
            #self._fbuf_on()
        except:
            #raise
            self._deregister()
            raise
            
        #pprint.pprint(self._cmds)
        return self.error 

    def update_internal_unit(self):
        #get internal unit
        self._fbuf_off()
        tup=('W','dBm','%','dB')
        ans=self.dev.ask('%sP SM'%self.ch_tup[self.channel])
        ans=int(ans[-1])
        self._internal_unit=tup[ans]
        # in fbuf mode several data are returned. GetData returs the average of this data.
        # Here, the appropriate average routine is set up
        if self._internal_unit in ['dB','dBm']:
            self.linav=linav_dB
        else:
            self.linav=linav_lin
        self._fbuf_on()
                
    def Trigger(self):
        self.error=0
        if self._data_valid() and self.value:
            return
        time.sleep(0.1)
        self.write('FBUF DUMP')
        POWERMETER.lasttrigger=time.time()
        buf=self.read('(?P<A>.*)')['A']
        values=np.array([float(d) for d in buf.split(',')])
        #print values
        if self.channel==1:
            self.value=self.linav(values[:self.N])
            if self.other and self.other._data_valid():
                self.other.value=self.linav(values[self.N:])
        else:
            self.value=self.linav(values[self.N:])
            if self.other and self.other._data_valid():
                self.other.value=self.linav(values[:self.N])
        time.sleep(0.1)
        return self.error
        
    def GetData(self):
        v=self.value
        swr_err=self.get_standard_mismatch_uncertainty()
        #print v
        self.power=float(v)
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
            self.Trigger
        return self.error, v

    def _data_valid(self):
        if POWERMETER.lasttrigger:
            now=time.time()
            return (now-POWERMETER.lasttrigger)<=self.trg_threshold
        else:
            return False

    def SetFreq(self, freq):
        self.error=0
        self._fbuf_off()
        self.error, freq = PWRMTR.SetFreq(self, freq)
        self._fbuf_on()
        return self.error, freq

    def GetDescription(self):
        self.error=0
        self._fbuf_off()
        self.error, des = PWRMTR.GetDescription(self)
        self._fbuf_on()
        return self.error, des
            
    def Quit(self):
        self.error=0
        if not self.other:
            self._fbuf_off()
        self._deregister()    
        return self.error

def test_init(ch):
    import StringIO
    from mpy.tools.util import format_block
    inst=POWERMETER()
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
#    main()
    pm1=test_init(1)
    pm2=test_init(2)
    for i in range(5):
        pm1.Trigger()
        print "PM1", pm1.GetData()
        pm2.Trigger()
        print "PM2", pm2.GetData()
    pm2.Quit()
    for i in range(5):
        pm1.Trigger()
        print "PM1", pm1.GetData()
    pm2=test_init(2)
    for i in range(5):
        pm1.Trigger()
        print "PM1", pm1.GetData()
        pm2.Trigger()
        print "PM2", pm2.GetData()
    #time.sleep(5)
    pm1.Quit()
    pm2.Quit()
