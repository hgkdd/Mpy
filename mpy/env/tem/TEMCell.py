# -*- coding: ISO-8859-1 -*-
"""
TEMCell: Class for EMC measurements in TEM cells

Author: Dr. Hans Georg Krauthaeuser, hgk@ieee.org

Copyright (c) 2001-2005 All rights reserved
"""

import UMDMeasure
import umddevice
import umdutil
import math
import sys
import time
import scipy
import pprint

scipy_pkgs=('special',)
for p in scipy_pkgs:
    try:
        getattr(scipy,p)
    except AttributeError:
        scipy.pkgload(p)



AmplifierProtectionError=UMDMeasure.AmplifierProtectionError

class TEMCell(UMDMeasure.UMDMeasure):
    """A class for TEM-cell measurements 
    """
    eut_positions = (("xx'yy'zz'",       "xz'yx'zy'",       "xy'yz'zx'"),
                     ("xz'yy'z(-x')",    "x(-x')yz'zy'",    "xy'y(-x')zz'"),
                     ("x(-x')yy'z(-z')", "x(-z')y(-x')zy'", "xy'y(-z')z(-x')"),
                     ("x(-z')yy'zx'",    "xx'y(-z')zy'",    "xy'yx'z(-z')"))

    c0=2.99792458e8
    eta0=120*math.pi
    
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
        self.rawData_e0y = {}
        self.processedData_e0y = {}
        self.rawData_Immunity = {}
        self.processedData_Immunity = {}
        self.rawData_Emission = {}
        self.processedData_Emission = {}
        self.std_3_positions = TEMCell.eut_positions[0]
        self.std_12_positions = umdutil.flatten(TEMCell.eut_positions)

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
        # for 'old' pickle files
        if not hasattr(self, 'asname'):
            self.asname=None
            self.ascmd=None
            self.autosave = False
        if not hasattr(self, 'autosave_interval'):
            self.autosave_interval = 3600
            self.lastautosave = time.time()

    def __getstate__(self):
        odict = self.__dict__.copy()
        del odict['logfile']
        del odict['logger']
        del odict['messenger']
        del odict['UserInterruptTester']
        del odict['PreUserEvent']
        del odict['PostUserEvent']        
        return odict

    def __HandleUserInterrupt(self, dct, ignorelist=''):
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
            
            self.messenger(umdutil.tstamp()+" RF Off...", [])
            stat = mg.RFOff_Devices() # switch off after measure
            msg1 = """The measurement has been interrupted by the user.\nHow do you want to proceed?\n\nContinue: go ahead...\nSuspend: Quit devices, go ahead later after reinit...\nInteractive: Go to interactive mode...\nQuit: Quit measurement..."""
            but1 = ['Continue','Suspend','Interactive','Quit']
            answer = self.messenger(msg1, but1)
            #print answer
            if answer == but1.index('Quit'):
                self.messenger(umdutil.tstamp()+" measurment terminated by user.", [])
                raise UserWarning      # to reach finally statement
            elif answer == but1.index('Interactive'):
                umdutil.interactive("Press CTRL-Z plus Return to exit")
            elif answer == but1.index('Suspend'):
                self.messenger(umdutil.tstamp()+" measurment suspended by user.", [])
                stat = mg.Quit_Devices()                                
                msg2 = """Measurement is suspended.\n\nResume: Reinit and continue\nQuit: Quit measurement..."""
                but2 = ['Resume','Quit']
                answer = self.messenger(msg2, but2)
                if answer == but2.index('Resume'):
                    # TODO: check if init was successful
                    self.messenger(umdutil.tstamp()+" Init devices...", [])
                    stat = mg.Init_Devices()
                    self.messenger(umdutil.tstamp()+" ... Init returned with stat = %d"%stat, [])        
                    stat = mg.RFOff_Devices() # switch off
                    self.messenger(umdutil.tstamp()+" Zero devices...", [])
                    stat = mg.Zero_Devices()
                    if hassg:
                        try:
                            level = self.setLevel(mg, names, SGLevel)
                        except AmplifierProtectionError, _e:
                            self.messenger(umdutil.tstamp()+" Can not set signal generator level. Amplifier protection raised with message: %s"%_e.message, [])

                    # set frequency for all devices
                    (minf, maxf) = mg.SetFreq_Devices (f)
                    mg.EvaluateConditions()
                elif answer == but2.index('Quit'):
                    self.messenger(umdutil.tstamp()+" measurment terminated by user.", [])
                    raise UserWarning      # to reach finally statement
            self.messenger(umdutil.tstamp()+" RF On...", [])
            stat = mg.RFOn_Devices()   # switch on just before measure
            if hassg:
                level2 = self.doLeveling(leveling, mg, names, locals())
                if level2:
                    level=level2
            try:
                # wait delay seconds
                self.messenger(umdutil.tstamp()+" Going to sleep for %d seconds ..."%(delay), [])
                self.wait(delay, dct,self.__HandleUserInterrupt)
                self.messenger(umdutil.tstamp()+" ... back.", [])
            except:
                pass
            mg.NBTrigger(nblist)

    def Evaluate_Emission(self,
                          description='EUT',
                          e0y_description='Main EUT Pos',
                          use_e0y_GTEManalytical=None,
                          EUTpos=None,
                          Zc=50,
                          Dmax=3.0,
                          s=10,
                          hg=0.8,
                          RH=(1,4),
                          is_oats=None,
                          component='y',
                          evaluate3pos=None):
        self.messenger(umdutil.tstamp()+" Starting evaluation of emission measurement for description '%s' ..."%(description), [])
        if is_oats is None:
            is_oats=True
        self.Calculate_Prad(description=description,
                            e0y_description=e0y_description,
                            use_e0y_GTEManalytical=use_e0y_GTEManalytical,
                            EUTpos=EUTpos,
                            Zc=Zc,
                            component=component,
                            evaluate3pos=evaluate3pos)
        self.Calculate_Emax(description=description,
                            Zc=Zc,
                            Dmax=Dmax,
                            s=s,
                            hg=hg,
                            RH=RH,
                            is_oats=is_oats)
        #import pprint
        #pprint.pprint(self.processedData_Emission)
        self.messenger(umdutil.tstamp()+" End of evaluation of emission measurement for description '%s'."%(description), [])
                          

    def Calculate_Prad (self,
                        description='EUT',
                        e0y_description='Main EUT Pos',
                        use_e0y_GTEManalytical=None,
                        EUTpos=None,
                        Zc=50,
                        component='y',
                        evaluate3pos=None):
        self.messenger(umdutil.tstamp()+" Starting calulation of radiated power for description '%s' ..."%(description), [])
        comp_dct={'x': 0, 'y': 1, 'z': 2}
        component=component.lower()
        comp_index=comp_dct[component]
        if use_e0y_GTEManalytical:
            cell_width=EUTpos['cell_width']
            sep_height=EUTpos['sep_height']
            gap=EUTpos['gap']
            ypos=EUTpos['ypos']
            xpos=EUTpos['xpos']
            e0ygtem=self.e0y_GTEM_analytical(cell_width, sep_height, gap, ypos, x=xpos, Zc=Zc)
            def e0y(f):
                return e0ygtem
        else:
##          import pprint
##          pprint.pprint(self.processedData_e0y[e0y_description]['e0y'])
            e0y_xydict={}
            e0ydata=self.processedData_e0y[e0y_description]['e0y']
            e0yfreqs=e0ydata.keys()
            e0yfreqs.sort()
            for e0yf in e0yfreqs:
                e0y_xydict[e0yf]=e0ydata[e0yf][0][0][comp_index]
            e0y = umdutil.MResult_Interpol(e0y_xydict)
        if not callable(e0y):
            self.messenger(umdutil.tstamp()+" ERROR: e0y is not callable. Abording evaluation.", [])
            return None
        if not self.rawData_Emission.has_key(description):
            self.messenger(umdutil.tstamp()+" ERROR: description '%s' not found. Abording evaluation."%description, [])
            return None

            
        try:
            self.processedData_Emission[description]
        except KeyError:
            self.processedData_Emission[description] = {}
            
        self.processedData_Emission[description]['Prad'] = {}
        self.processedData_Emission[description]['Prad_noise'] = {}

        voltages = self.rawData_Emission[description]['voltage']
        noise=self.rawData_Emission[description]['noise']
        freqs = voltages.keys()
        freqs.sort()
        for f in freqs:
            self.processedData_Emission[description]['Prad'][f]={}
            self.processedData_Emission[description]['Prad_noise'][f]={}
            ports=voltages[f].keys()
            ports.sort()
            for port in ports:
                self.processedData_Emission[description]['Prad'][f][port]=[]
                self.processedData_Emission[description]['Prad_noise'][f][port]=[]
                data=voltages[f][port]
                ndata=noise[f][port]
                #import pprint
                #pprint.pprint(data)
                positions=data.keys()
                #print positions
                for k in range(len(data[positions[0]])):
                    maxv = umddevice.UMDMResult(-1, umddevice.UMD_V)
                    # find the max of all voltages
                    for p in positions:
                        if evaluate3pos and p not in self.std_3_positions:
                            continue
                        d=data[p][k]
                        vp=d['value'].convert(umddevice.UMD_V)
                        vp=vp.mag()
                        if vp.get_v() > maxv.get_v():
                            maxv = vp
                            maxp = p
                    for triple in TEMCell.eut_positions:
                        if maxp in triple:
                            orth_v = [data[p][k] for p in triple]
                            break
                    self.messenger(umdutil.tstamp()+"f=%e, Using positions '%r'"%(f,triple), [])
                    s2 = umddevice.UMDMResult(0,umddevice.UMD_dimensionless)
                    nd=ndata[0][k]['value'].mag().convert(umddevice.UMD_V)  # convert to common unit
                    nddl=nd.convert(umddevice.UMD_dimensionless)
                    ns2 = 3*nddl*nddl
                    ns2.unit=umddevice.UMD_dimensionless
                    #print nd,
                    for p in triple:
                        #print p, k, data[p][k]
                        d=data[p][k]['value'].mag().convert(umddevice.UMD_V)  # convert to common unit
                        #print d,
                        d.unit=umddevice.UMD_dimensionless  # yes, dirty, I know...
                        s2 += (d*d)
        ##            deltas = abs(0.5*(s.u+s.l)/2.0/s.v)
        ##            s.u=s.v+deltas
        ##            s.l=s.v-deltas
        ##            s.unit = umddevice.UMD_V
                    #print ns2, s2
                    k2 = (2*math.pi*f/TEMCell.c0)**2
                    e0y2=e0y(f)
                    e0y2.unit=umddevice.UMD_dimensionless
                    e0y2 *= e0y2
                    P0 = umddevice.UMDMResult(TEMCell.eta0/(3*math.pi*Zc)*k2, umddevice.UMD_dimensionless)
                    P0 = P0*s2/e0y2
                    P0.unit = umddevice.UMD_W
                    nP0 = umddevice.UMDMResult(TEMCell.eta0/(3*math.pi*Zc)*k2, umddevice.UMD_dimensionless)
                    nP0 = nP0*ns2/e0y2
                    nP0.unit = umddevice.UMD_W
                    self.messenger(umdutil.tstamp()+"f=%e, Prad: %s, Prad_noise: %s"%(f,str(P0),str(nP0)), [])
                    self.processedData_Emission[description]['Prad'][f][port].append(P0)
                    self.processedData_Emission[description]['Prad_noise'][f][port].append(nP0)
        self.messenger(umdutil.tstamp()+" Calulation of radiated power done.", [])

    
    def Calculate_Emax (self, description='EUT', Dmax=3.0, s=10, hg=0.8, RH=(1,4), rstep=None, Zc=50, is_oats=None):
        self.messenger(umdutil.tstamp()+" Starting calulation of maximum radiated E field for description '%s' ..."%(description), [])
        if is_oats is None:
            is_oats=True
        print self.processedData_Emission.keys()
        if not self.processedData_Emission[description].has_key('Prad'):
            self.Calculate_Prad (description=description, Zc=Zc)

        if not is_oats:
            gmax_f = umdutil.gmax_fs
            gmax_model="FAR"
        else:
            gmax_f = umdutil.gmax_oats
            gmax_model="OATS"
        self.processedData_Emission[description]['Assumed_Distance']=s
        self.processedData_Emission[description]['Gmax_Model']=gmax_model
        self.processedData_Emission[description]['Assumed_hg']=hg
        self.processedData_Emission[description]['Assumed_RH']=RH
        self.processedData_Emission[description]['Assumed_Zc']=Zc
        self.processedData_Emission[description]['Assumed_Directivity']={}
            
        dmax_f=Dmax
        ext=['', '_noise']
        for ex in ext:
            self.processedData_Emission[description]['Emax%s'%ex]={}
            Emax=self.processedData_Emission[description]['Emax%s'%ex]
            prad=self.processedData_Emission[description]['Prad%s'%ex]
            freqs=prad.keys()
            freqs.sort()
            for f in freqs:
                if callable(Dmax):
                    dmax_f=Dmax(f)
                self.processedData_Emission[description]['Assumed_Directivity'].setdefault(f,dmax_f)
                ports = prad[f].keys()
                ports.sort()
                for port in ports:
                    Emax[f]={}
                    for pr in prad[f][port]:
                        p0 = umddevice.UMDMResult(pr.convert(umddevice.UMD_W))
                        p0.unit=umddevice.UMD_dimensionless
                        gmax = gmax_f(f,rstep=rstep,s=s,hg=hg,RH=RH)
                        cc = dmax_f*TEMCell.eta0/(4*math.pi)
                        deltap0=0.5*(p0.get_u()+p0.get_l())
                        vv = math.sqrt(cc*p0.v)
                        ll = vv - abs(0.5/math.sqrt(cc/p0.v)*deltap0)
                        uu = vv + abs(0.5/math.sqrt(cc/p0.v)*deltap0)
                        t=umddevice.UMDMResult(vv, ll , uu, umddevice.UMD_dimensionless) 
                        Emax[f][port]=[]
                        dct={}
                        for _k, _val in gmax.items():
                            dct[_k]=t*_val
                            dct[_k].unit=umddevice.UMD_Voverm
                        dct['total'] = umdutil.MRmax(dct['v'],dct['h'])
                        Emax[f][port].append(dct)
                        self.messenger(umdutil.tstamp()+" f=%e, Emax%s=%r"%(f, ex, dct), [])
        self.messenger(umdutil.tstamp()+" Calculation of maximum radiated E field done.", [])
    
    def e0y_GTEM_analytical(self, a, h, g, y, x=0, Zc=50, max_m=10):
        sum=0.0
        for m in xrange(1,max_m+1,2):
            M=m*math.pi/a
            ch=math.cosh(M*y)
            c=math.cos(M*x)
            s=math.sin(M*a/2.0)
            j0=scipy.special.j0(M*g)
            sh=math.sinh(M*h)
            sum += ch*c*s*j0/sh
            #print "m: %d, ch: %e, c: %e, s: %s, j0: %e, sh: %e, sum: %e"%(m, ch, c, s, j0, sh, sum)
        sum*=4.0*math.sqrt(Zc)/a
        return umddevice.UMDMResult(sum, umddevice.UMD_VovermoversqrtW)

    def Measure_Emission (self,
                           description="EUT",
                           positions=None,
                           dotfile='gtem-emission.dot',
                           delay=1.0,
                           freqs=None,
                           receiverconf = None,
                           names={'port': ['port'],
                                  'receiver': ['analyzer']}):
        """
        Performs a emission measurement according to IEC 61000-4-20
        """
        if positions is None:
            positions=self.std_3_positions

        self.PreUserEvent()
        if self.autosave:
            self.messenger(umdutil.tstamp()+" Resume TEM cell emission measurement from autosave...", [])
        else:
            self.messenger(umdutil.tstamp()+" Start new TEM cell emission measurement...", [])

        self.rawData_Emission.setdefault(description, {})

        # number of ports
        nports = min(len(names['port']),len(names['receiver']))

        mg=umdutil.UMDMGraph(dotfile)
        ddict=mg.CreateDevices()
        #for k,v in ddict.items():
        #    globals()[k] = v

        self.messenger(umdutil.tstamp()+" Init devices...", [])
        err = mg.Init_Devices()
        if err: 
            self.messenger(umdutil.tstamp()+" ...faild with err %d"%(err), [])
            return err
        try:  
            self.messenger(umdutil.tstamp()+" ...done", [])
            if freqs is None:
                freqs = []

            if receiverconf is None:
                receiverconf = {}
            rcfreqs = receiverconf.keys()
            rcfreqs.sort()
            rcfreqs.reverse()

            # set up voltage, noise, ...
            voltage={}
            noise={}

            if self.autosave:
                noise=self.rawData_Emission[description]['noise'].copy()
                try:
                    voltage=self.rawData_Emission[description]['voltage'].copy()
                    eut_positions=voltage[0].keys()
                    positions=[_p for _p in positions if not _p in eut_positions]
                except KeyError:   # as after noise -> no voltages yet
                    pass
                msg = "List of remainung eut positions from autosave file:\n%r\n"%(positions)
                but = []
                self.messenger(msg, but)
            self.autosave=False
                
            msg = \
"""
Noise floor measurement.
Position EUT.
Switch EUT OFF.
Are you ready to start the measurement?

Start: start measurement.
Quit: quit measurement.
"""
            but = ["Start", "Quit"]
            answer = self.messenger(msg, but)
            if answer == but.index('Quit'):
                self.messenger(umdutil.tstamp()+" measurement terminated by user.", [])
                raise UserWarning      # to reach finally statement
            # loop freqs
            for f in freqs:
                self.messenger(umdutil.tstamp()+" Frequency %e Hz"%(f), [])
                mg.EvaluateConditions()
                # set frequency for all devices
                (minf, maxf) = mg.SetFreq_Devices (f)
                # configure receiver(s)
                for rf in rcfreqs:
                    if f >= rf:
                        break
                try:
                    conf = receiverconf[rf]
                except:
                    conf = {}
                rconf = mg.ConfReceivers(conf)
                self.messenger(umdutil.tstamp()+" Receiver configuration: %s"%str(rconf), [])
                    
                # cable corrections
                c_port_receiver = []
                for i in range(nports):
                    c_port_receiver.append(mg.get_path_correction(names['port'][i], names['receiver'][i], umddevice.UMD_dB))

                # ALL measurement start here
                block = {}
                nbresult = {} # dict for NB-Read results
                receiverlist=[]
                    
                for i in range(nports):
                    receiverlist.append(names['receiver'][i])

                # noise floor measurement..
                self.messenger(umdutil.tstamp()+" Starting noise floor measurement for f = %e Hz ..."%(f), [])
                mg.NBTrigger(receiverlist)
                # serial poll all devices in list
                olddevs = []
                while 1:
                    self.__HandleUserInterrupt(locals())    
                    nbresult = mg.NBRead(receiverlist, nbresult)
                    new_devs=[i for i in nbresult.keys() if i not in olddevs]
                    olddevs = nbresult.keys()[:]
                    if len(new_devs):
                        self.messenger(umdutil.tstamp()+" Got answer from: "+str(new_devs), [])                            
                    if len(nbresult)==len(receiverlist):
                        break
                for i in range(nports):
                    n = names['receiver'][i]
                    if nbresult.has_key(n):
                        # add path correction here
                        print n, nbresult[n]
                        PPort = umddevice.UMDCMResult(nbresult[n])
                        nn = 'Noise '+n
                        self.__addLoggerBlock(block, nn, 'Noise reading of the receiver for position %d'%i, nbresult[n], {})
                        self.__addLoggerBlock(block[nn]['parameter'], 'freq', 'the frequency [Hz]', f, {}) 
                        self.__addLoggerBlock(block, 'c_port_receiver'+str(i), 'Correction from port to receiver', c_port_receiver[i], {})
                        self.__addLoggerBlock(block['c_port_receiver'+str(i)]['parameter'], 'freq', 'the frequency [Hz]', f, {}) 
                        PPort /= c_port_receiver[i]['total']
                        self.__addLoggerBlock(block, nn+'_corrected', 'Noise: PPort/c_refant_receiver', PPort, {})
                        self.__addLoggerBlock(block[nn+'_corrected']['parameter'], 'freq', 'the frequency [Hz]', f, {}) 
                        noise = self.__insert_it (noise, PPort, None, None, f, i, 0)
                self.messenger(umdutil.tstamp()+" Noise floor measurement done.", [])

                for log in self.logger:
                    log(block)

                self.__HandleUserInterrupt(locals())    
                # END OF f LOOP
            lowBatList = mg.getBatteryLow_Devices()
            if len(lowBatList):
                self.messenger(umdutil.tstamp()+" WARNING: Low battery status detected for: %s"%(str(lowBatList)), [])
            self.rawData_Emission[description].update({'noise': noise})
            # autosave class instance
            if self.asname and (time.time()-self.lastautosave > self.autosave_interval):
                self.messenger(umdutil.tstamp()+" autosave ...", [])
                self.do_autosave()
                self.messenger(umdutil.tstamp()+" ... done", [])

            # NOISE MEASUREMENT finished

            
            # loop eut positions
            measured_eut_pos = []
            remain_eut_pos = list(positions)[:]
            while len(remain_eut_pos):
                msg =\
"""
EUT measurement.
Switch EUT ON.
Select EUT position.

"""
                but=[]
                for _i, _r in enumerate(remain_eut_pos):
                    msg += "%s: %s\n"%(umdutil.map2singlechar(_i),str(_r))
                    but.append(str(_i))
                msg += "Quit: quit measurement."
                but.append("Quit")
                answer = self.messenger(msg, but)
                if answer == but.index('Quit'):
                    self.messenger(umdutil.tstamp()+" measurement terminated by user.", [])
                    raise UserWarning      # to reach finally statement
                p = remain_eut_pos[answer]

                self.messenger(umdutil.tstamp()+" EUT position %r"%(p), [])
                # loop freqs
                for f in freqs:
                    self.messenger(umdutil.tstamp()+" Frequency %e Hz"%(f), [])
                    # switch if necessary
                    mg.EvaluateConditions()
                    # set frequency for all devices
                    (minf, maxf) = mg.SetFreq_Devices (f)
                    # configure receiver(s)
                    for rf in rcfreqs:
                        if f >= rf:
                            break
                    try:
                        conf = receiverconf[rf]
                    except:
                        conf = {}
                    rconf = mg.ConfReceivers(conf)
                    self.messenger(umdutil.tstamp()+" Receiver configuration: %s"%str(rconf), [])
                        
                    # cable corrections
                    c_port_receiver = []
                    for i in range(nports):
                        c_port_receiver.append(mg.get_path_correction(names['port'][i], names['receiver'][i], umddevice.UMD_dB))

                    # ALL measurement start here
                    block = {}
                    nbresult = {} # dict for NB-Read results
                    nblist = [] # list of devices for NB Reading
                        
                    for i in range(nports):
                        nblist.append(names['receiver'][i])

                    # wait delay seconds
                    time.sleep(0.5)   # minimum delay according -4-21
                    self.messenger(umdutil.tstamp()+" Going to sleep for %d seconds ..."%(delay), [])
                    self.wait(delay,locals(),self.__HandleUserInterrupt)
                    self.messenger(umdutil.tstamp()+" ... back.", [])

                        
                    # Trigger all devices in list
                    mg.NBTrigger(nblist)
                    # serial poll all devices in list
                    olddevs = []
                    while 1:
                        self.__HandleUserInterrupt(locals())    
                        nbresult = mg.NBRead(nblist, nbresult)
                        new_devs=[i for i in nbresult.keys() if i not in olddevs]
                        olddevs = nbresult.keys()[:]
                        if len(new_devs):
                            self.messenger(umdutil.tstamp()+" Got answer from: "+str(new_devs), [])                            
                        if len(nbresult)==len(nblist):
                            break
                    # print nbresult

                    # ports                
                    for i in range(nports):
                        n = names['receiver'][i]
                        if nbresult.has_key(n):
                            # add path correction here
                            PPort = umddevice.UMDCMResult(nbresult[n])
                            self.__addLoggerBlock(block, n, 'Reading of the receiver for position %d'%i, nbresult[n], {})
                            self.__addLoggerBlock(block[n]['parameter'], 'freq', 'the frequency [Hz]', f, {}) 
                            self.__addLoggerBlock(block[n]['parameter'], 'eutpos', 'EUT position', p, {}) 
                            self.__addLoggerBlock(block, 'c_port_receiver'+str(i), 'Correction from port to receiver', c_port_receiver[i], {})
                            self.__addLoggerBlock(block['c_port_receiver'+str(i)]['parameter'], 'freq', 'the frequency [Hz]', f, {}) 
                            PPort /= c_port_receiver[i]['total']
                            #print PPort
                            voltage = self.__insert_it (voltage, PPort, None, None, f, i, p)
                            self.__addLoggerBlock(block, n+'_corrected', 'PPort/c_port_receiver', PPort, {})
                            self.__addLoggerBlock(block[n]['parameter'], 'freq', 'the frequency [Hz]', f, {}) 
                            self.__addLoggerBlock(block[n]['parameter'], 'eutpos', 'EUT position', p, {}) 

                    for log in self.logger:
                        log(block)

                    self.__HandleUserInterrupt(locals())    
                    # END OF f LOOP
                lowBatList = mg.getBatteryLow_Devices()
                if len(lowBatList):
                    self.messenger(umdutil.tstamp()+" WARNING: Low battery status detected for: %s"%(str(lowBatList)), [])
                self.rawData_Emission[description].update({'voltage': voltage, 'mg': mg})
                # autosave class instance
                if self.asname and (time.time()-self.lastautosave > self.autosave_interval):
                    self.messenger(umdutil.tstamp()+" autosave ...", [])
                    self.do_autosave()
                    self.messenger(umdutil.tstamp()+" ... done", [])
                measured_eut_pos.append(p)
                remain_eut_pos.remove(p)
            #END OF p LOOP
                
        finally:
            # finally is executed if and if not an exception occur -> save exit
            self.messenger(umdutil.tstamp()+" Quit...", [])
            stat = mg.Quit_Devices()
        self.messenger(umdutil.tstamp()+" End of Emission mesurement. Status: %d"%stat, [])
        self.PostUserEvent()
        return stat

    def Measure_e0y(self,
                   description=None,
                   dotfile='gtem-e0y.dot',
                   delay=1.0,
                   freqs=None,
                   SGLevel=-20,
                   leveling=None,
                   names={'sg': 'sg',
                          'a1': 'a1',
                          'a2': 'a2',
                          'port': 'port',
                          'pmfwd': 'pm1',
                          'pmbwd': 'pm2',
                          'fp': ['fp1']}):
        """
        Performs determination of e0y according to IEC 61000-4-20
        """
        self.PreUserEvent()

        if self.autosave:
            self.messenger(umdutil.tstamp()+" Resume e0y calibration measurement from autosave...", [])
        else:
            self.messenger(umdutil.tstamp()+" Start new e0y calibration measurement...", [])

        if description is None:
            description="None"
            
        self.rawData_e0y.setdefault(description, {})

        if leveling is None:
            leveling = [{'condition': 'False',
                         'actor': None,
                         'actor_min': None,
                         'actor_max': None,
                         'watch': None,
                         'nominal': None,
                         'reader': None,
                         'path': None}]
                    
        # number of probes
        nprb = len(names['fp'])

        mg=umdutil.UMDMGraph(dotfile)
        ddict=mg.CreateDevices()
        for k,v in ddict.items():
            globals()[k] = v
            
        self.messenger(umdutil.tstamp()+" Init devices...", [])
        err = mg.Init_Devices()
        if err: 
            self.messenger(umdutil.tstamp()+" ...faild with err %d"%(err), [])
            return err
        try:  
            self.messenger(umdutil.tstamp()+" ...done", [])
            stat = mg.RFOff_Devices()
            self.messenger(umdutil.tstamp()+" Zero devices...", [])
            stat = mg.Zero_Devices()
            self.messenger(umdutil.tstamp()+" ...done", [])

            try:
                level = self.setLevel(mg, names, SGLevel)
            except AmplifierProtectionError, _e:
                self.messenger(umdutil.tstamp()+" Can not set signal generator level. Amplifier protection raised with message: %s"%_e.message, [])
                raise  # re raise to reach finaly clause
                
            # set up efields, ...
            efields={}
                
            if self.autosave:
                efields=self.rawData_e0y[description]['efield'].copy()
                
                edat = self.rawData_e0y[description]['efield']
                fr=edat.keys()
                freqs=[f for f in freqs if not f in fr]
                msg = "List of remaining frequencies:\n%r\n"%(freqs)
                but = []
                self.messenger(msg, but)
            self.autosave=False    

            stat = mg.RFOff_Devices()
            msg = """Position E field probes.\nAre you ready to start the measurement?\n\nStart: start measurement.\nQuit: quit measurement."""
            but = ["Start", "Quit"]
            answer = self.messenger(msg, but)
            if answer == but.index('Quit'):
                self.messenger(umdutil.tstamp()+" measurement terminated by user.", [])
                raise UserWarning      # to reach finally statement
            self.messenger(umdutil.tstamp()+" RF On...", [])
            stat = mg.RFOn_Devices()
            # loop freqs
            for f in freqs:
                self.messenger(umdutil.tstamp()+" Frequency %e Hz"%(f), [])
                # switch if necessary
                #print f
                mg.EvaluateConditions()
                # set frequency for all devices
                (minf, maxf) = mg.SetFreq_Devices (f)
                # cable corrections
                c_sg_amp = mg.get_path_correction(names['sg'], names['a1'], umddevice.UMD_dB)
                c_sg_port = mg.get_path_correction(names['sg'], names['port'], umddevice.UMD_dB)
                c_a2_pm1 = mg.get_path_correction(names['a2'], names['pmfwd'], umddevice.UMD_dB)
                c_a2_port = mg.get_path_correction(names['a2'], names['port'], umddevice.UMD_dB)
                c_port_pm2 = mg.get_path_correction(names['port'], names['pmbwd'], umddevice.UMD_dB)
                c_fp = 1.0

                # ALL measurement start here
                block = {}
                nbresult = {} # dict for NB-Read results
                nblist = [names['pmfwd'], names['pmbwd']] # list of devices for NB Reading
                # check for fwd pm
                if mg.nodes[names['pmfwd']]['inst']:
                    NoPmFwd = False  # ok
                else:  # no fwd pm
                    msg = umdutil.tstamp()+" WARNING: No fwd power meter. Signal generator output is used instead!"
                    answer = self.messenger(msg,[])
                    NoPmFwd = True

                for i in range(nprb):
                    nblist.append(names['fp'][i])
                #print "nblist:", nblist

                level2 = self.doLeveling(leveling, mg, names, locals())
                if level2:
                    level=level2

                # wait delay seconds
                self.messenger(umdutil.tstamp()+" Going to sleep for %d seconds ..."%(delay), [])
                self.wait(delay,locals(),self.__HandleUserInterrupt)
                self.messenger(umdutil.tstamp()+" ... back.", [])

                # Trigger all devices in list
                mg.NBTrigger(nblist)
                # serial poll all devices in list
                if NoPmFwd:
                    nbresult[names['pmfwd']] = level
                    nbresult[names['pmbwd']] = umddevice.UMDMResult(mg.zero(level.unit), level.get_unit())
                olddevs = []
                while 1:
                    self.__HandleUserInterrupt(locals())    
                    nbresult = mg.NBRead(nblist, nbresult)
                    new_devs=[i for i in nbresult.keys() if i not in olddevs]
                    olddevs = nbresult.keys()[:]
                    if len(new_devs):
                        self.messenger(umdutil.tstamp()+" Got answer from: "+str(new_devs), [])
                    if len(nbresult)==len(nblist):
                        break
                # print nbresult

                # pfwd
                n = names['pmfwd']
                if nbresult.has_key(n):
                    PFwd = umddevice.UMDCMResult(nbresult[n])
                    self.__addLoggerBlock(block, n, 'Reading of the fwd power meter', nbresult[n], {})
                    self.__addLoggerBlock(block[n]['parameter'], 'freq', 'the frequency [Hz]', f, {}) 
                    PFwd *= c_a2_port['total']
                    self.__addLoggerBlock(block, 'c_a2_port', 'Correction from amplifier output to port', c_a2_port, {})
                    self.__addLoggerBlock(block['c_a2_port']['parameter'], 'freq', 'the frequency [Hz]', f, {}) 
                    self.__addLoggerBlock(block, 'c_a2_pm1', 'Correction from amplifier output to fwd power meter', c_a2_pm1, {})
                    self.__addLoggerBlock(block['c_a2_pm1']['parameter'], 'freq', 'the frequency [Hz]', f, {}) 
                    PFwd /= c_a2_pm1['total']
                    self.__addLoggerBlock(block, n+'_corrected', 'Pfwd*c_a2_port/c_a2_pm1', PFwd, {})
                    self.__addLoggerBlock(block[n]['parameter'], 'freq', 'the frequency [Hz]', f, {}) 
                # pbwd
                n = names['pmbwd']
                if nbresult.has_key(n):
                    PBwd = umddevice.UMDCMResult(nbresult[n])
                    self.__addLoggerBlock(block, n, 'Reading of the bwd power meter', nbresult[n], {})
                    self.__addLoggerBlock(block[n]['parameter'], 'freq', 'the frequency [Hz]', f, {}) 
                    self.__addLoggerBlock(block, 'c_port_pm2', 'Correction from port to bwd power meter', c_port_pm2, {})
                    self.__addLoggerBlock(block['c_port_pm2']['parameter'], 'freq', 'the frequency [Hz]', f, {}) 
                    PBwd /= c_port_pm2['total']
                    self.__addLoggerBlock(block, n+'_corrected', 'Pbwd/c_port_pm2', PBwd, {})
                    self.__addLoggerBlock(block[n]['parameter'], 'freq', 'the frequency [Hz]', f, {}) 

                # e-field probes                
                # read field probes
                for i in range(nprb):
                    n = names['fp'][i]
                    if nbresult.has_key(n):
                        self.__addLoggerBlock(block, n, 'Reading of the e-field probe number %d'%i, nbresult[n], {})
                        self.__addLoggerBlock(block[n]['parameter'], 'freq', 'the frequency [Hz]', f, {}) 
                        efields = self.__insert_it (efields, nbresult[n], PFwd, PBwd, f, 0, 0)
                for log in self.logger:
                    log(block)

                self.__HandleUserInterrupt(locals())    
                # test for low battery
                lowBatList = mg.getBatteryLow_Devices()
                if len(lowBatList):
                    self.messenger(umdutil.tstamp()+" WARNING: Low battery status detected for: %s"%(str(lowBatList)), [])
                # autosave class instance
                if self.asname and (time.time()-self.lastautosave > self.autosave_interval):
                    self.messenger(umdutil.tstamp()+" autosave ...", [])
                    self.do_autosave()
                    self.messenger(umdutil.tstamp()+" ... done", [])
                # END OF f LOOP
            self.messenger(umdutil.tstamp()+" RF Off...", [])
            stat = mg.RFOff_Devices() # switch off after measure
            self.rawData_e0y[description].update({'efield': efields, 'mg': mg})
                
        finally:
            # finally is executed if and if not an exception occur -> save exit
            self.messenger(umdutil.tstamp()+" RF Off and Quit...", [])
            stat = mg.RFOff_Devices()
            stat = mg.Quit_Devices()
        self.messenger(umdutil.tstamp()+" End of e0y calibration. Status: %d"%stat, [])
        self.PostUserEvent()
        return stat

    def __insert_it(self, field, value, pf, pb, f, port, pos, dct=None):
        """
        Inserts a value in a field.
        field: '3D' dictionary of a list of dicts ;-)
        e.g.: efield[f][port][pos] is a list [{'value': vector of MResults, 'pfwd': CMResult, 'pwwd': CMResult}, ...]
        f: frequency (float)
        """
        field.setdefault(f, {})
        field[f].setdefault(port, {})
        field[f][port].setdefault(pos, [])
        field[f][port][pos].append({'value': value, 'pfwd': pf, 'pbwd': pb})
        if not dct is None:
            field[f][port][pos][-1].update(dct)        
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

    def OutputRawData_e0y (self, description=None, what=None, fname=None):
        thedata = self.rawData_e0y
        stdout = sys.stdout
        if fname:
            fp = file(fname,"w")
            sys.stdout = fp
        try:
            self.__OutputRawData(thedata, description, what)
        finally:
            try:
                fp.close()
            except:
                umdutil.LogError (self.messenger)            
            sys.stdout=stdout

    def OutputRawData_Emission (self, description=None, what=None, fname=None):
        thedata = self.rawData_Emission
        stdout = sys.stdout
        if fname:
            fp = file(fname,"w")
            sys.stdout = fp
        try:
            self.__OutputRawData(thedata, description, what)
        finally:
            try:
                fp.close()
            except:
                umdutil.LogError (self.messenger)            
            sys.stdout=stdout
        
    def __OutputRawData(self, thedata, description, what):
        deslist = self.MakeDeslist(thedata, description)
        whatlist = self.MakeWhatlist(thedata, what)
        for d in deslist:
            print "# Description:", d
            for w in whatlist:
                print "# ", w
                data = thedata[d][w]
                try:
                    freqs = data.keys()
                    freqs.sort()
                    for f in freqs:
                        pees = data[f].keys()
                        pees.sort()
                        for p in pees:
                            poses=data[f][p].keys()
                            poses.sort()
                            for pos in poses:
                                print "f:", f, "port:", p, "pos:", pos,
                                item = data[f][p][pos]
                                self.out(item)
                                print
                except:  # data has no keys
                    item = data
                    self.out(item)
                    print

    def OutputProcessedData_e0y (self, description=None, what=None, fname=None):
        thedata = self.processedData_e0y
        stdout = sys.stdout
        if fname:
            fp = file(fname,"w")
            sys.stdout = fp
        try:
            self.__OutputProcessedData(thedata, description, what)
        finally:
            try:
                fp.close()
            except:
                umdutil.LogError (self.messenger)            
            sys.stdout=stdout

    def OutputProcessedData_Emission (self, description=None, what=None, fname=None):
        thedata = self.processedData_Emission
        stdout = sys.stdout
        if fname:
            fp = file(fname,"w")
            sys.stdout = fp
        try:
            self.__OutputProcessedData(thedata, description, what)
        finally:
            try:
                fp.close()
            except:
                umdutil.LogError (self.messenger)            
            sys.stdout=stdout


    def __OutputProcessedData(self, thedata, description, what):
        deslist = self.MakeDeslist(thedata, description)
        whatlist = self.MakeWhatlist(thedata, what)
        for d in deslist:
            data = thedata[d]
            print "Description:", d
            for w in whatlist:
                if data.has_key(w):
                    print w, ":"
                    try:
                        freqs = data[w].keys()
                        freqs.sort()
                        for f in freqs:
                            print f,
                            item = data[w][f]
                            self.out (item)
                            print
                    except:
                        item=data[w]
                        self.out (item)
                        print

    def Evaluate_e0y(self, description=None):
            self.messenger(umdutil.tstamp()+" Start of evaluation of e0y calibration with description %s"%description, [])
            if not self.rawData_e0y.has_key(description):
                self.messenger(umdutil.tstamp()+" Description %s not found."%description, [])
                return -1
                
            efields = self.rawData_e0y[description]['efield']
            #pprint.pprint(efields)
            freqs = efields.keys()
            freqs.sort()
            print 'Freqs:', freqs

            self.processedData_e0y.setdefault(description,{})        
            self.processedData_e0y[description]['e0y']={}
            for f in freqs:
                self.processedData_e0y[description]['e0y'][f]={}
                e0yf=self.processedData_e0y[description]['e0y'][f]
                ports =efields[f].keys()
                ports.sort()
                print 'Ports:', ports
                for port in ports:
                    e0yf[port]=[]
                    for i in range(len(efields[f][port][0])):
                        ef = efields[f][port][0][i]['value']
                        pin = efields[f][port][0][i]['pfwd']
                        pin = pin.mag().convert(umddevice.UMD_W)
                        v = pin.get_v()
                        sqrtv=math.sqrt(v)
                        u = pin.get_u()
                        l = pin.get_l()
                        sqrtPInput = umddevice.UMDMResult(sqrtv, sqrtv+(u+l)/(2.0*sqrtv), sqrtv-(u+l)/(2.0*sqrtv), umddevice.UMD_sqrtW)
                        en = umddevice.stdVectorUMDMResult()
                        for k in range(len(ef)):
                            en.append(ef[k]/sqrtPInput)
                            print k, ef[k], pin, sqrtPInput, en[-1]
                        self.processedData_e0y[description]['e0y'][f][port].append(en)
            self.messenger(umdutil.tstamp()+" End of evaluation of e0y calibration", [])
            return 0
