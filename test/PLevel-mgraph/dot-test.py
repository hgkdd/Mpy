import time
import sys
import numpy as np
from scipy.interpolate import interp1d
from scipy.optimize import fmin

from scuq import quantities,si,units
from mpy.env.Measure import Measure
from mpy.tools.mgraph import MGraph
from mpy.tools.aunits import POWERRATIO
from mpy.tools import util

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
            logfile = open(dct['logfilename'], "a+")
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

    def _HandleUserInterrupt(self, dct, ignorelist=''):
        key = self.UserInterruptTester() 
        if key and not chr(key) in ignorelist:
            # empty key buffer
            _k = self.UserInterruptTester()
            while not _k is None:
                _k = self.UserInterruptTester()

            mg = dct['mg']
            names = dct['names']
            f = dct['f']
            try:
                SGLevel=dct['SGLevel'] 
                leveling = dct['leveling']
            except:
                hassg = False
            else:
                hassg = True
            try:
                delay=dct['delay']
            except KeyError:
                pass
            try:
                nblist = dct['nblist']
            except KeyError:
                nblist=[]
            
            self.messenger(util.tstamp()+" RF Off...", [])
            stat = mg.RFOff_Devices() # switch off after measure
            msg1 = """The measurement has been interrupted by the user.\nHow do you want to proceed?\n\nContinue: go ahead...\nSuspend: Quit devices, go ahead later after reinit...\nInteractive: Go to interactive mode...\nQuit: Quit measurement..."""
            but1 = ['Continue','Suspend','Interactive','Quit']
            answer = self.messenger(msg1, but1)
            #print answer
            if answer == but1.index('Quit'):
                self.messenger(util.tstamp()+" measurment terminated by user.", [])
                raise UserWarning      # to reach finally statement
            elif answer == but1.index('Interactive'):
                util.interactive("Press CTRL-Z plus Return to exit")
            elif answer == but1.index('Suspend'):
                self.messenger(util.tstamp()+" measurment suspended by user.", [])
                stat = mg.Quit_Devices()                                
                msg2 = """Measurement is suspended.\n\nResume: Reinit and continue\nQuit: Quit measurement..."""
                but2 = ['Resume','Quit']
                answer = self.messenger(msg2, but2)
                if answer == but2.index('Resume'):
                    # TODO: check if init was successful
                    self.messenger(util.tstamp()+" Init devices...", [])
                    stat = mg.Init_Devices()
                    self.messenger(util.tstamp()+" ... Init returned with stat = %d"%stat, [])        
                    stat = mg.RFOff_Devices() # switch off
                    self.messenger(util.tstamp()+" Zero devices...", [])
                    stat = mg.Zero_Devices()
                    if hassg:
                        try:
                            level = self.setLevel(mg, names, SGLevel)
                        except AmplifierProtectionError as _e:
                            self.messenger(util.tstamp()+" Can not set signal generator level. Amplifier protection raised with message: %s"%_e.message, [])

                    # set frequency for all devices
                    (minf, maxf) = mg.SetFreq_Devices (f)
                    mg.EvaluateConditions()
                elif answer == but2.index('Quit'):
                    self.messenger(util.tstamp()+" measurment terminated by user.", [])
                    raise UserWarning      # to reach finally statement
            self.messenger(util.tstamp()+" RF On...", [])
            stat = mg.RFOn_Devices()   # switch on just before measure
            if hassg:
                level2 = self.doLeveling(leveling, mg, names, locals())
                if level2:
                    level=level2
            try:
                # wait delay seconds
                self.messenger(util.tstamp()+" Going to sleep for %d seconds ..."%(delay), [])
                self.wait(delay, dct,self._HandleUserInterrupt)
                self.messenger(util.tstamp()+" ... back.", [])
            except:
                pass
            mg.NBTrigger(nblist)

        
        
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

        mg=MGraph(dotfile, names)
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
                    instrumentation.sg.SetLevel(lv)
                    time.sleep(delay)
                    
                    mg.NBTrigger(readlist)
                    results=mg.Read(readlist)
        
                    pfwd=results[mg.name.pm_fwd]
                    pbwd=results[mg.name.pm_bwd]
                    pin=(lv*c_sg_amp).reduce_to(si.WATT)
                    pout=(pfwd/c_amp_pm1).reduce_to(si.WATT)
                    pgtem=(pout*c_amp_out).reduce_to(si.WATT)
                
                    self.__addLoggerBlock(block, 'sg_pout_%d', 'Amplifier test sg level reading', lv, {})
                    self.__addLoggerBlock(block['sg_pout_%d']['parameter'], 'freq', 'the frequency [Hz]', f, {}) 
                    self.__addLoggerBlock(block, 'pfwd_%d', 'Fwd power meter reading reading', pfwd, {})
                    self.__addLoggerBlock(block['pfwd_%d']['parameter'], 'freq', 'the frequency [Hz]', f, {}) 
                    self.__addLoggerBlock(block['pfwd_%d']['parameter'], 'lv', 'sg level', lv, {}) 
                    self.__addLoggerBlock(block, 'pbwd_%d', 'Bwd power meter reading reading', pbwd, {})
                    self.__addLoggerBlock(block['pbwd_%d']['parameter'], 'freq', 'the frequency [Hz]', f, {}) 
                    self.__addLoggerBlock(block['pbwd_%d']['parameter'], 'lv', 'sg level', lv, {}) 
                    self.__addLoggerBlock(block, 'c_sg_amp', 'Correction from sg to amp', c_sg_amp, {})
                    self.__addLoggerBlock(block['c_sg_amp']['parameter'], 'freq', 'the frequency [Hz]', f, {}) 
                    self.__addLoggerBlock(block, 'c_amp_pm1', 'Correction from amp to pm1', c_amp_pm1, {})
                    self.__addLoggerBlock(block['c_amp_pm1']['parameter'], 'freq', 'the frequency [Hz]', f, {}) 
                    self.__addLoggerBlock(block, 'c_amp_pm2', 'Correction from amp to pm2', c_amp_pm2, {})
                    self.__addLoggerBlock(block['c_amp_pm2']['parameter'], 'freq', 'the frequency [Hz]', f, {}) 
                    self.__addLoggerBlock(block, 'c_amp_out', 'Correction from amp to out', c_amp_out, {})
                    self.__addLoggerBlock(block['c_amp_out']['parameter'], 'freq', 'the frequency [Hz]', f, {}) 
 
                    self.__addLoggerBlock(block, 'amp_pin_%d', 'Amplifier test input level reading', pin, {})
                    self.__addLoggerBlock(block['amp_pin_%d']['parameter'], 'freq', 'the frequency [Hz]', f, {}) 
                    self.__addLoggerBlock(block['amp_pin_%d']['parameter'], 'lv', 'sg level', lv, {}) 
                    self.__addLoggerBlock(block,'amp_pout_%d', 'Amplifier test output level reading', pout, {})
                    self.__addLoggerBlock(block['amp_pout_%d']['parameter'], 'freq', 'the frequency [Hz]', f, {}) 
                    self.__addLoggerBlock(block['amp_pout_%d']['parameter'], 'lv', 'sg level', lv, {}) 

                    sg_pout = self.__insert_it (sg_pout, lv, pfwd, pbwd, f, lv)
                    amp_pin = self.__insert_it (amp_pin, lv, pfwd, pbwd, f, lv)
                    amp_pout = self.__insert_it (amp_pout, lv, pfwd, pbwd, f, lv)
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

    def __insert_it(self, field, value, pf, pb, f, sglv, dct=None):
        """
        Inserts a value in a field.
        field: '3D' dictionary of a list of dicts ;-)
        e.g.: amp_pout[f][sglv] is a list [{'value': vector of Quantities, 'pfwd': Quantity, 'pbwd': Quantity}, ...]
        f: frequency (float)
        """
        field.setdefault(f, {})
        field[f].setdefault(repr(sglv), [])
        field[f][repr(sglv)].append({'value': value, 'pfwd': pf, 'pbwd': pb})
        if not dct is None:
            field[f][repr(sglv)][-1].update(dct)
        return field

    def __addLoggerBlock (self, parent, key, comment, val, parameter):
        """
        Helper function to add a block for the logger function(s).
        parent must be a dict
        key is used as key
        parent[key] results in a dict like {'comment' comment, 'value': val, 'parameter': parameter}
        parameter should be a dict of the same form as parent or an empty dict
        """
        parent[key]={}
        parent[key]['comment']=comment
        parent[key]['value']=val
        parent[key]['parameter']=parameter

        

if __name__ == '__main__':
    import pickle as pickle
    from numpy import linspace
    from scuq.quantities import Quantity
    from scuq.si import WATT
    
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
    AT.set_logfile('at.log')
    AT.Measure(description="IFI SMX25 Band1",
               dotfile=dot,
               names=names,
               freqs=linspace(10e3,200e6,10),
               levels=[Quantity(WATT, dBm2W(dBmval)) for dBmval in linspace(-30, 0, 3)])
    pickle.dump (AT, open('at.p', 'wb'), 2)