import time
import sys
import numpy as np
from scipy.interpolate import interp1d
from scipy.optimize import fmin

from scuq import quantities,si,units
from mpy.env.Measure import Measure
from mpy.tools.mgraph import MGraph
from mpy.tools.aunits import POWERRATIO

def dBm2W (v):
    return 10**(v*0.1)*0.001
def W2dBm (v):
    return 10*np.log10(v*1000)

class AmplifierTest(Measure):
    def __init__(self):
        self.asname=None
        self.ascmd=None
        self.autosave = False
        self.autosave_interval = 3600
        self.lastautosave = time.time()
        self.logger=[self.stdlogger]
        self.logfile=None
        self.logfilename=None
        self.messenger=self.stdUserMessenger
        self.UserInterruptTester=self.stdUserInterruptTester
        self.PreUserEvent=self.stdPreUserEvent
        self.PostUserEvent=self.stdPostUserEvent        
        self.rawData= {}
        self.processedData = {}

    def __setstate__(self, dct):
        if dct['logfilename'] is None:
            logfile = None
        else:
            logfile = file(dct['logfilename'], "a+")
        self.__dict__.update(dct)
        self.logfile = logfile
        self.messenger=self.stdUserMessenger
        self.logger=[self.stdlogger]
        self.UserInterruptTester=self.stdUserInterruptTester
        self.PreUserEvent=self.stdPreUserEvent
        self.PostUserEvent=self.stdPostUserEvent        

    def __getstate__(self):
        odict = self.__dict__.copy()
        del odict['logfile']
        del odict['logger']
        del odict['messenger']
        del odict['UserInterruptTester']
        del odict['PreUserEvent']
        del odict['PostUserEvent']        
        return odict

    def Measure (self, description="AmplifierTest",
                       dotfile='amplifier.dot',
                       delay=0.2,
                       freqs=None,
                       levels=None,
                       names={'sg': 'sg',
                               'amp_in': 'amp_in',
                               'amp_out': 'amp_out',
                               'pm_fwd': 'pm1',
                               'pm_bwd': 'pm2',
                               'output': 'gtem'}):
        """
        Performs an amplifier test measurement.

        Parameter:
     
           - *description*: key to identify the measurement in the result dictionary
           - *dotfile*: forwarded to :class:`mpy.tools.mgraph.MGraph` to create the mearsurment graph.
           - *delay*: time in seconds to wait after setting the frequencie before pulling date from the instruments
           - *freqs*: sequence of frequencies in Hz to use for the measurements.
           - *names*: dict with the mapping from internal names to dot-file names.

               The dict has to have keys 'sg', 'amp_in', 'amp_out', 'pm_fwd', 'pm_bwd' and 'output'. 
        """

        self.PreUserEvent()
        if self.autosave:
            self.messenger(util.tstamp()+" Resume amplifier test measurement from autosave...", [])
        else:
            self.messenger(util.tstamp()+" Start new amplifier test measurement...", [])

        self.rawData.setdefault(description, {})

        mg=mgraph.MGraph(dotfile, names)
        instrumentation=mg.CreateDevices()

        self.messenger(util.tstamp()+" Init devices...", [])
        err = mg.Init_Devices()
        if err: 
            self.messenger(util.tstamp()+" ...faild with err %d"%(err), [])
            return err
        try:  
            self.messenger(util.tstamp()+" ...done", [])
            if freqs is None:
                freqs = []

            # set up pin, pout, ...
            sg_pout={}
            amp_pin={}
            amp_pout={}

            if self.autosave:
                sg_pout=self.rawData[description]['sg_pout'].copy()
                amp_pin=self.rawData[description]['amp_pin'].copy()
                amp_pout=self.rawData[description]['amp_pout'].copy()
            self.autosave=False
                
            msg = \
"""
Amplifier test measurement.
Are you ready to start the measurement?

Start: start measurement.
Quit: quit measurement.
"""
            but = ["Start", "Quit"]
            answer = self.messenger(msg, but)
            if answer == but.index('Quit'):
                self.messenger(util.tstamp()+" measurement terminated by user.", [])
                raise UserWarning      # to reach finally statement

            readlist=[ mg.get_gname(dev) for dev in ('pm_fwd','pm_bwd') ] 
            # loop freqs
            for f in freqs:
                self.messenger(util.tstamp()+" Frequency %e Hz"%(f), [])
                mg.EvaluateConditions()
                # set frequency for all devices
                (minf, maxf) = mg.SetFreq_Devices(f)
                # cable corrections
                c_sg_amp  = mg.get_path_correction(mg.name.sg, mg.name.amp_in, POWERRATIO)
                c_amp_out = mg.get_path_correction(mg.name.amp_out, mg.name.output, POWERRATIO)
                c_amp_pm1 = mg.get_path_correction(mg.name.amp_out, mg.name.pm_fwd, POWERRATIO)
                c_amp_pm2 = mg.get_path_correction(mg.name.amp_out, mg.name.pm_bwd, POWERRATIO)

                # ALL measurement start here
                block = {}
                nbresult = {} # dict for NB-Read results

                # measurement..
                self.messenger(util.tstamp()+" Starting amplifier test measurement for f = %e Hz ..."%(f), [])
      
                mg.RFOn_Devices()
                for counter, lv in enumerate(levels):
                    sg.SetLevel(lv)
                    time.sleep(delay)
                    
                    mg.NBTrigger(readlist)
                    results=mg.Read(readlist)
        
                    pfwd=results[mg.name.pm_fwd]
                    pbwd=results[mg.name.pm_bwd]
                    pin=(lv*c_sg_amp).reduce_to(si.WATT)
                    pout=(pfwd/c_amp_pm1).reduce_to(si.WATT)
                    pgtem=(pout*c_amp_out).reduce_to(si.WATT)
                
                    self.__addLoggerBlock(block, 'sg_pout_%d'%counter, 'Amplifier test sg level reading', lv, {})
                    self.__addLoggerBlock(block['sg_pout_%d'%counter]['parameter'], 'freq', 'the frequency [Hz]', f, {}) 
                    self.__addLoggerBlock(block, 'pfwd_%d'%counter, 'Fwd power meter reading reading', pfwd, {})
                    self.__addLoggerBlock(block['pfwd_%d'%counter]['parameter'], 'freq', 'the frequency [Hz]', f, {}) 
                    self.__addLoggerBlock(block['pfwd_%d'%counter]['parameter'], 'lv', 'sg level', lv, {}) 
                    self.__addLoggerBlock(block, 'pbwd_%d'%counter, 'Bwd power meter reading reading', pbwd, {})
                    self.__addLoggerBlock(block['pbwd_%d'%counter]['parameter'], 'freq', 'the frequency [Hz]', f, {}) 
                    self.__addLoggerBlock(block['pbwd_%d'%counter]['parameter'], 'lv', 'sg level', lv, {}) 
                    self.__addLoggerBlock(block, 'c_sg_amp', 'Correction from sg to amp', c_sg_amp, {})
                    self.__addLoggerBlock(block['c_sg_amp']['parameter'], 'freq', 'the frequency [Hz]', f, {}) 
                    self.__addLoggerBlock(block, 'c_amp_pm1', 'Correction from amp to pm1', c_amp_pm1, {})
                    self.__addLoggerBlock(block['c_amp_pm1']['parameter'], 'freq', 'the frequency [Hz]', f, {}) 
                    self.__addLoggerBlock(block, 'c_amp_pm2', 'Correction from amp to pm2', c_amp_pm1, {})
                    self.__addLoggerBlock(block['c_amp_pm2']['parameter'], 'freq', 'the frequency [Hz]', f, {}) 
                    self.__addLoggerBlock(block, 'c_amp_out', 'Correction from amp to out', c_amp_pm1, {})
                    self.__addLoggerBlock(block['c_amp_out']['parameter'], 'freq', 'the frequency [Hz]', f, {}) 
 
                    self.__addLoggerBlock(block, 'amp_pin_%d'%counter, 'Amplifier test input level reading', pin, {})
                    self.__addLoggerBlock(block['amp_pin_%d'%counter]['parameter'], 'freq', 'the frequency [Hz]', f, {}) 
                    self.__addLoggerBlock(block['amp_pin_%d'%counter]['parameter'], 'lv', 'sg level', lv, {}) 
                    self.__addLoggerBlock(block,'amp_pout_%d'%counter, 'Amplifier test output level reading', pout, {})
                    self.__addLoggerBlock(block['amp_pout_%d'%counter]['parameter'], 'freq', 'the frequency [Hz]', f, {}) 
                    self.__addLoggerBlock(block['amp_pout_%d'%counter]['parameter'], 'lv', 'sg level', lv, {}) 

                    sg_pout = self.__insert_it (lv, counter, None, None, f, 0, 0)
                    amp_pin = self.__insert_it (pin, counter, None, None, f, lv, 0)
                    amp_pout = self.__insert_it (pout, counter, None, None, f, lv, 0)
                mg.RFOff_Devices()
                self.messenger(util.tstamp()+" Amplifier test measurement done.", [])
                for log in self.logger:
                    log(block)

                self._HandleUserInterrupt(locals())    
                # END OF f LOOP
            lowBatList = mg.getBatteryLow_Devices()
            if len(lowBatList):
                self.messenger(util.tstamp()+" WARNING: Low battery status detected for: %s"%(str(lowBatList)), [])

            self.rawData[description].update({'sg_pout': sg_pout})
            self.rawData[description].update({'amp_pin': amp_pin})
            self.rawData[description].update({'amp_pout': amp_pout})

            # autosave class instance
            if self.asname and (time.time()-self.lastautosave > self.autosave_interval):
                self.messenger(util.tstamp()+" autosave ...", [])
                self.do_autosave()
                self.messenger(util.tstamp()+" ... done", [])

            # Amplifier test finished

                
        finally:
            # finally is executed if and if not an exception occur -> save exit
            self.messenger(util.tstamp()+" Quit...", [])
            stat = mg.Quit_Devices()
        self.messenger(util.tstamp()+" End of Amplifier test Measurement. Status: %d"%stat, [])
        self.PostUserEvent()
        return stat


if __name__ == '__main__':
    import cPickle as pickle
    from numpy import linspace
    from scuq.quantity import Quantity
    from scuq.units.si import WATT
    
    def get_gain_compression (pin, pout, small_signal_factor=10):
        pin_ss=[pi for pi in pin if pi <= pin[0]*small_signal_factor]
        pout_ss = pout[:len(pin_ss)]
        gain, offset = np.polyfit(pin_ss, pout_ss, 1)
        ideal = lambda pin: offset+gain*pin
        orig = interp1d(pin, pout)
        c1func = lambda pin: ideal(pin)/orig(pin)-1.259
        c3func = lambda pin: ideal(pin)/orig(pin)-1.995
        pinc1 = fmin(c1func, pin[0])
        pinc3 = fmin(c3func, pinc1)
        pountc1=orig(pinc1)
        poutc3=orig(pinc3)
        return gain, offset, pinc1, poutc1, pinc3, poutc3
    
    dot='gtem-immunity.dot'
    # keys: names in program, values: names in graph
    names={'sg': 'sg',
           'amp_in': 'amp_in',
           'amp_out': 'amp_out',
           'pm_fwd': 'pm1',
           'pm_bwd': 'pm2',
           'output': 'gtem'}

    AT = AmplifierTest()
    AT.Measure(description="IFI SMX25 Band1",
               dotfile=dot,
               names=names,
               freqs=linspace(10e3,200e6,10),
               levels=[Quantity(WATT, dBm2W(dBmval)) for dBmval in linspace(-30, 0, 3)])
    pickle.dump (AT, file('out.p', 'wb'), 2)