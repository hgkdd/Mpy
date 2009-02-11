# -*- coding: iso-8859-1 -*-
"""
MSC: class for MSC measurements

Author: Dr. Hans Georg Krauthaeuser, hgk@ieee.org

Copyright (c) 2001-2005 All rights reserved
Note: rpy and R are GPLed
...
Form the R FAQ:
2.11 Can I use R for commercial purposes?

R is released under the GNU General Public License (GPL).
If you have any questions regarding the legality of using R
in any particular situation you should bring it up with your legal counsel.
We are in no position to offer legal advice.

It is the opinion of the R Core Team that one can use
R for commercial purposes (e.g., in business or in consulting).
The GPL, like all Open Source licenses, permits all and any use of the package.
It only restricts distribution of R or of other programs containing code from R. This is made clear in clause 6 (“No Discrimination Against Fields of Endeavor”)
of the Open Source Definition:

    The license must not restrict anyone from making use of the
    program in a specific field of endeavor. For example, it may not restrict
    the program from being used in a business, or from being
    used for genetic research. 

It is also explicitly stated in clause 0 of the GPL, which says in part

    Activities other than copying, distribution and modification are
    not covered by this License; they are outside its scope. The act
    of running the Program is not restricted, and the output from the
    Program is covered only if its contents constitute a work based on
    the Program. 

Most add-on packages, including all recommended ones, also explicitly
allow commercial use in this way. A few packages are restricted
to “non-commercial use”; you should contact the author to clarify whether
these may be used or seek the advice of your legal counsel.

None of the discussion in this section constitutes legal advice. The R Core Team does not provide legal advice under any circumstances. 
...

So, my understanding is that I can use it.
"""
from __future__ import division
import math
import sys
import time
import rpy
import scipy
import pprint

scipy_pkgs=('interpolate','optimize')
for p in scipy_pkgs:
    try:
        getattr(scipy,p)
    except AttributeError:
        scipy.pkgload(p)


from mpy.device import device
from mpy.tools import util
from mpy.env import Measure


#from win32com.client import Dispatch
#import sys

#def toSVG(data, filename):
#    graphViz=Dispatch("WINGRAPHVIZ.dot")
##    f=open(filename,'r')
##    data = f.read()
##    f.close()
#    img=graphViz.toSVG(data)
#    f=open(str(filename),'w')
#    f.write(img)
#    f.close()

AmplifierProtectionError=Measure.AmplifierProtectionError

class MSC(Measure.Measure):
    """A class for MSC measurements 
    """
    def __init__(self):
        super(MSC, self).__init__()
        self.TPosCmp = self.stdTPosCmp
        self.rawData_MainCal = {}
        self.processedData_MainCal = {}
        self.rawData_EUTCal = {}
        self.processedData_EUTCal = {}
        self.rawData_Immunity = {}
        self.processedData_Immunity = {}
        self.rawData_Emission = {}
        self.processedData_Emission = {}
        self.rawData_AutoCorr = {}
        self.processedData_AutoCorr = {}
        self.std_Standard='IEC 61000-4-21'

    def __setstate__(self, dct):
        super(MSC, self).__setstate__(dct)
        self.TPosCmp = self.stdTPosCmp

    def __getstate__(self):
        odict = super(MSC, self).__getstate__()
        del odict['TPosCmp']
        return odict

    def __insert_it(self, field, value, pf, pb, f, t, p, dct=None):
        """
        Inserts a value in a field.
        field: '3D' dictionary of a list of dicts ;-)
        e.g.: efield[f][t][p] is a list [{'value': vector of MResults, 'pfwd': CMResult, 'pwwd': CMResult}, ...]
        f: frequency (float), t: tuner pos '[15, 180, ...]', p: position (int)
        for t: the key is repr(t)
        """
        field.setdefault(f, {})
        field[f].setdefault(repr(t), {})
        field[f][repr(t)].setdefault(p,[])
        field[f][repr(t)][p].append({'value': value, 'pfwd': pf, 'pbwd': pb})
        if not dct is None:
            field[f][repr(t)][p][-1].update(dct)        
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


    def Measure_MainCal (self,
                           description="empty",
                           dotfile='msc-calibration.dot',
                           delay=1.0,
                           FStart=150e6,
                           FStop=1e9,
                           SGLevel=-20,
                           leveling=None,
                           ftab=[3,6,10,100,1000],
                           nftab=[20,15,10,20,20],
                           ntuntab=[[50,18,12,12,12]],
                           tofftab=[[7,14,28,28,28]],
                           nprbpostab=[8,8,8,8,8],
                           nrefantpostab=[8,8,8,8,8],
                           names={'sg': 'sg',
                                  'a1': 'a1',
                                  'a2': 'a2',
                                  'ant': 'ant',
                                  'pmfwd': 'pm1',
                                  'pmbwd': 'pm2',
                                  'fp': ['fp1','fp2','fp3','fp4','fp5','fp6','fp7','fp8'], 
                                  'tuner': ['tuner1'],
                                  'refant': ['refant1'],
                                  'pmref': ['pmref1']}):
        """Performs a msc main calibration according to IEC 61000-4-21
        """
        self.pre_user_event()

        if self.autosave:
            self.messenger(umdutil.tstamp()+" Resume main calibration measurement from autosave...", [])
        else:
            self.messenger(umdutil.tstamp()+" Start new main calibration measurement...", [])

        self.rawData_MainCal.setdefault(description, {})

        if leveling is None:
            leveling = [{'condition': 'False',
                         'actor': None,
                         'actor_min': None,
                         'actor_max': None,
                         'watch': None,
                         'nominal': None,
                         'reader': None,
                         'path': None}]
                    
        # number of probes, ref-antenna and tuners
        nprb = len(names['fp'])
        nrefant = min(len(names['refant']),len(names['pmref']))
        ntuner = min(len(ntuntab),len(tofftab),len(names['tuner']))

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
            stat = mg.RFOff_Devices()
            self.messenger(umdutil.tstamp()+" Zero devices...", [])
            stat = mg.Zero_Devices()
            self.messenger(umdutil.tstamp()+" ...done", [])

            try:
                level = self.set_level(mg, names, SGLevel)
            except AmplifierProtectionError, _e:
                self.messenger(umdutil.tstamp()+" Can not set signal generator level. Amplifier protection raised with message: %s"%_e.message, [])
                raise  # re raise to reach finaly clause
                
            # list of frequencies
            freqs = umdutil.logspaceTab(FStart,FStop,ftab,nftab,endpoint=True)
            PrbPosCounter ={}
            RefAntPosCounter ={}
            #calculate numbrer of required probe positions for each freq
            positions={}
            hasDupes = []
            for f in freqs:
                findex = umdutil.getIndex(f, [_f*FStart for _f in ftab])
                #print f, findex
                PrbPosCounter[f] = nprbpostab[findex]   # number of positions to measure for this freq
                RefAntPosCounter[f] = nrefantpostab[findex]   # number of positions (ref ant)
                if positions.has_key(findex):
                    continue
                positions[findex]=[]
                for tunerindex in range(ntuner):
                    positions[findex].append( [tunerposindex*tofftab[tunerindex][findex] for tunerposindex in range(ntuntab[tunerindex][findex])])
                positions[findex] = umdutil.combinations(positions[findex])
                hasDupes += positions[findex]
            noDupes = []
            [noDupes.append(_i) for _i in hasDupes if not noDupes.count(_i)]
            alltpos = noDupes   # unique and sorted
            #determine max number of probe pos
            prbposleft = maxnprbpos = max(nprbpostab)
            #determine max number of ref ant pos
            refantposleft = maxnrefantpos = max(nrefantpostab)

            # set up efields, ...
            efields={}
            prefant={}
            noise={}
            etaTx = {}
            etaRx = {}
            as_i={'prbposleft': prbposleft,
                                'refantposleft': refantposleft,
                                'LastMeasuredFreq': None,
                                'LastMeasuredTpos': None}
            if self.autosave:
                efields=self.rawData_MainCal[description]['efield'].copy()
                prefant=self.rawData_MainCal[description]['pref'].copy()
                noise=self.rawData_MainCal[description]['noise'].copy()
                
                as_i=self.autosave_info.copy()
                try:
                    as_i['LastMeasuredTpos']=as_i['LastMeasuredTPos']  # Greding special (black magic)
                except KeyError:
                    pass
                prbposleft=as_i['prbposleft']
                refantposleft=as_i['refantposleft']
                if 'PrbPosCounter' in as_i:
                    PrbPosCounter=as_i['PrbPosCounter'].copy()
                if 'RefAntPosCounter' in as_i:
                    RefAntPosCounter=as_i['RefAntPosCounter'].copy()

##                
##                edat = self.rawData_MainCal[description]['efield']
##                epees = []
##                for f in edat.keys():
##                    count = 1e300
##                    for t in edat[f].keys():
##                        count = min(count,len(edat[f][t]))
##                        [epees.append(_i) for _i in edat[f][t].keys() if not epees.count(_i)]
##                    PrbPosCounter[f]-=count
##                prbposleft -= len(epees)
##                rdat = self.rawData_MainCal[description]['pref']
##                rpees = []
##                for f in rdat.keys():
##                    count = 1e300
##                    for t in rdat[f].keys():
##                        count = min(count,len(rdat[f][t]))
##                        [rpees.append(_i) for _i in rdat[f][t].keys() if not rpees.count(_i)]
##                    RefAntPosCounter[f]-=count
##                refantposleft -= len(rpees)
                
##                msg = "List of probe positions from autosave file:\n%s\nList of ref antenna positions from autosave file:\n%s\n"%(str(epees), str(rpees))
                msg = "List of probe positions from autosave file:\n%s\nList of ref antenna positions from autosave file:\n%s\n"%(str(range(maxnprbpos-max(0,prbposleft))), str(range(maxnrefantpos-max(0,refantposleft))))
                but = []
                self.messenger(msg, but)
            self.autosave=False    
            # for all probe/refant positions
            while prbposleft > 0 or refantposleft > 0:
                stat = mg.RFOff_Devices()
                msg = """Position E field probes and reference antenna...\nAre you ready to start the measurement?\n\nStart: start measurement.\nQuit: quit measurement."""
                but = ["Start", "Quit"]
                answer = self.messenger(msg, but)
                if answer == but.index('Quit'):
                    self.messenger(umdutil.tstamp()+" measurement terminated by user.", [])
                    raise UserWarning      # to reach finally statement
                p = maxnprbpos - prbposleft + 1 # current probe pos 
                pra = maxnrefantpos - refantposleft + 1 # current refant pos
                # loop tuner positions
                for t in alltpos:
                    ast=as_i['LastMeasuredTpos']
                    if ast:
                        if alltpos[-1]==ast:
                            pass
                        elif alltpos.index(t)<=alltpos.index(ast):
                            continue
                    as_i['LastMeasuredTpos']=None
                    self.messenger(umdutil.tstamp()+" Tuner position %s"%(repr(t)), [])
                    # position tuners
                    self.messenger(umdutil.tstamp()+" Move tuner(s)...", [])
                    for i in range(ntuner):
                        TPos = umddevice.UMDMResult(t[i], umddevice.UMD_deg)
                        IsPos = ddict[names['tuner'][i]].Goto (TPos, 0)
                    self.messenger(umdutil.tstamp()+" ...done", [])
                    # loop freqs
                    for f in freqs:
                        asf=as_i['LastMeasuredFreq']
                        if asf:
                            if (freqs[-1]==asf) and not (alltpos[-1]==ast):
                                pass
                            elif (freqs[-1]==asf) and (alltpos[-1]==ast):
                                for fr in freqs:
                                    RefAntPosCounter[fr] -= nrefant
                                    PrbPosCounter[fr] -= nprb                    
                            elif freqs.index(f)<=freqs.index(asf):
                                continue
                        as_i['LastMeasuredFreq']=None
                        self.messenger(umdutil.tstamp()+" Frequency %e Hz"%(f), [])
                        findex = umdutil.getIndex(f, [_i*FStart for _i in ftab])
                        if t not in positions[findex]:   # pos t is not for this freq
                            self.messenger(umdutil.tstamp()+" Skipping tuner position", [])
                            continue
                        # switch if necessary
                        #print f
                        mg.EvaluateConditions()
                        # set frequency for all devices
                        (minf, maxf) = mg.SetFreq_Devices (f)
                        # cable corrections
                        c_sg_amp = mg.get_path_correction(names['sg'], names['a1'], umddevice.UMD_dB)
                        c_sg_ant = mg.get_path_correction(names['sg'], names['ant'], umddevice.UMD_dB)
                        c_a2_pm1 = mg.get_path_correction(names['a2'], names['pmfwd'], umddevice.UMD_dB)
                        c_a2_ant = mg.get_path_correction(names['a2'], names['ant'], umddevice.UMD_dB)
                        c_ant_pm2 = mg.get_path_correction(names['ant'], names['pmbwd'], umddevice.UMD_dB)
                        c_refant_pmref = []
                        for i in range(nrefant):
                            c_refant_pmref.append(mg.get_path_correction(names['refant'][i], names['pmref'][i], umddevice.UMD_dB))
                        c_fp = 1.0
                        if not etaTx.has_key(f):
                            eta = mg.GetAntennaEfficiency(names['ant'])
                            self.messenger(umdutil.tstamp()+" Eta_Tx for f = %e Hz is %s"%(f,str(eta)), [])
                            etaTx = self.__insert_it (etaTx, eta, None, None, f, t, 0)
                        if not etaRx.has_key(f):
                            for i in range(nrefant):
                                eta = mg.GetAntennaEfficiency(names['refant'][i])
                                self.messenger(umdutil.tstamp()+" Eta_Rx(%d) for f = %e Hz is %s"%(i,f,str(eta)), [])
                                etaRx = self.__insert_it (etaRx, eta, None, None, f, t, i)


                        # ALL measurement start here
                        block = {}
                        nbresult = {} # dict for NB-Read results
                        pmreflist=[]
                        nblist = [names['pmfwd'], names['pmbwd']] # list of devices for NB Reading
                        # check for fwd pm
                        if mg.nodes[names['pmfwd']]['inst']:
                            NoPmFwd = False  # ok
                        else:  # no fwd pm
                            msg = umdutil.tstamp()+" WARNING: No fwd power meter. Signal generator output is used instead!"
                            answer = self.messenger(msg,[])
                            NoPmFwd = True

                        for i in range(nrefant):
                            if RefAntPosCounter[f] < i+1:
                                break
                            nblist.append(names['pmref'][i])
                            pmreflist.append(names['pmref'][i])
                        for i in range(nprb):
                            if PrbPosCounter[f] < i+1:
                                break
                            nblist.append(names['fp'][i])

                        # noise floor measurement..
                        if not noise.has_key(f):
                            self.messenger(umdutil.tstamp()+" Starting noise floor measurement for f = %e Hz ..."%(f), [])
                            mg.NBTrigger(pmreflist)
                            # serial poll all devices in list
                            olddevs = []
                            while 1:
                                self.__HandleUserInterrupt(locals())    
                                nbresult = mg.NBRead(pmreflist, nbresult)
                                new_devs=[i for i in nbresult.keys() if i not in olddevs]
                                olddevs = nbresult.keys()[:]
                                if len(new_devs):
                                    self.messenger(umdutil.tstamp()+" Got answer from: "+str(new_devs), [])                            
                                if len(nbresult)==len(pmreflist):
                                    break
                            for i in range(nrefant):
                                n = names['pmref'][i]
                                if nbresult.has_key(n):
                                    # add path correction here
                                    PRef = umddevice.UMDCMResult(nbresult[n])
                                    nn = 'Noise '+n
                                    self.__addLoggerBlock(block, nn, 'Noise reading of the receive antenna power meter for position %d'%i, nbresult[n], {})
                                    self.__addLoggerBlock(block[nn]['parameter'], 'freq', 'the frequency [Hz]', f, {}) 
                                    self.__addLoggerBlock(block, 'c_refant_pmref'+str(i), 'Correction from ref antenna feed to ref power meter', c_refant_pmref[i], {})
                                    self.__addLoggerBlock(block['c_refant_pmref'+str(i)]['parameter'], 'freq', 'the frequency [Hz]', f, {}) 
                                    PRef /= c_refant_pmref[i]['total']
                                    self.__addLoggerBlock(block, nn+'_corrected', 'Noise: Pref/c_refant_pmref', PRef, {})
                                    self.__addLoggerBlock(block[nn+'_corrected']['parameter'], 'freq', 'the frequency [Hz]', f, {}) 
                                    self.__addLoggerBlock(block[nn+'_corrected']['parameter'], 'tunerpos', 'tuner position', t, {}) 
                                    noise = self.__insert_it (noise, PRef, None, None, f, t, i)
                            self.messenger(umdutil.tstamp()+" Noise floor measurement done.", [])


                        self.messenger(umdutil.tstamp()+" RF On...", [])
                        stat = mg.RFOn_Devices()   # switch on just before measure

                        level2 = self.do_leveling(leveling, mg, names, locals())
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
                            self.__addLoggerBlock(block[n]['parameter'], 'tunerpos', 'tuner position', t, {}) 
                            PFwd *= c_a2_ant['total']
                            self.__addLoggerBlock(block, 'c_a2_ant', 'Correction from amplifier output to antenna', c_a2_ant, {})
                            self.__addLoggerBlock(block['c_a2_ant']['parameter'], 'freq', 'the frequency [Hz]', f, {}) 
                            self.__addLoggerBlock(block, 'c_a2_pm1', 'Correction from amplifier output to fwd power meter', c_a2_pm1, {})
                            self.__addLoggerBlock(block['c_a2_pm1']['parameter'], 'freq', 'the frequency [Hz]', f, {}) 
                            PFwd /= c_a2_pm1['total']
                            self.__addLoggerBlock(block, n+'_corrected', 'Pfwd*c_a2_ant/c_a2_pm1', PFwd, {})
                            self.__addLoggerBlock(block[n]['parameter'], 'freq', 'the frequency [Hz]', f, {}) 
                            self.__addLoggerBlock(block[n]['parameter'], 'tunerpos', 'tuner position', t, {}) 
                        # pbwd
                        n = names['pmbwd']
                        if nbresult.has_key(n):
                            PBwd = umddevice.UMDCMResult(nbresult[n])
                            self.__addLoggerBlock(block, n, 'Reading of the bwd power meter', nbresult[n], {})
                            self.__addLoggerBlock(block[n]['parameter'], 'freq', 'the frequency [Hz]', f, {}) 
                            self.__addLoggerBlock(block[n]['parameter'], 'tunerpos', 'tuner position', t, {}) 
                            self.__addLoggerBlock(block, 'c_ant_pm2', 'Correction from antenna feed to bwd power meter', c_ant_pm2, {})
                            self.__addLoggerBlock(block['c_ant_pm2']['parameter'], 'freq', 'the frequency [Hz]', f, {}) 
                            PBwd /= c_ant_pm2['total']
                            self.__addLoggerBlock(block, n+'_corrected', 'Pbwd/c_ant_pm2', PBwd, {})
                            self.__addLoggerBlock(block[n]['parameter'], 'freq', 'the frequency [Hz]', f, {}) 
                            self.__addLoggerBlock(block[n]['parameter'], 'tunerpos', 'tuner position', t, {}) 

                        # ref-ant                
                        for i in range(nrefant):
                            if RefAntPosCounter[f] < i+1:
                                break
                            n = names['pmref'][i]
                            if nbresult.has_key(n):
                                # add path correction here
                                PRef = umddevice.UMDCMResult(nbresult[n])
                                self.__addLoggerBlock(block, n, 'Reading of the receive antenna power meter for position %d'%i, nbresult[n], {})
                                self.__addLoggerBlock(block[n]['parameter'], 'freq', 'the frequency [Hz]', f, {}) 
                                self.__addLoggerBlock(block[n]['parameter'], 'tunerpos', 'tuner position', t, {}) 
                                self.__addLoggerBlock(block, 'c_refant_pmref'+str(i), 'Correction from ref antenna feed to ref power meter', c_refant_pmref[i], {})
                                self.__addLoggerBlock(block['c_refant_pmref'+str(i)]['parameter'], 'freq', 'the frequency [Hz]', f, {}) 
                                PRef /= c_refant_pmref[i]['total']
                                prefant = self.__insert_it (prefant, PRef, PFwd, PBwd, f, t, pra+i-1)
                                self.__addLoggerBlock(block, n+'_corrected', 'Pref/c_refant_pmref', PRef, {})
                                self.__addLoggerBlock(block[n]['parameter'], 'freq', 'the frequency [Hz]', f, {}) 
                                self.__addLoggerBlock(block[n]['parameter'], 'tunerpos', 'tuner position', t, {}) 

                        # e-field probes                
                        # read field probes
                        for i in range(nprb):
                            if PrbPosCounter[f] < i+1:
                                break
                            n = names['fp'][i]
                            if nbresult.has_key(n):
                                self.__addLoggerBlock(block, n, 'Reading of the e-field probe for position %d'%i, nbresult[n], {})
                                self.__addLoggerBlock(block[n]['parameter'], 'freq', 'the frequency [Hz]', f, {}) 
                                self.__addLoggerBlock(block[n]['parameter'], 'tunerpos', 'tuner position', t, {}) 
                                efields = self.__insert_it (efields, nbresult[n], PFwd, PBwd, f, t, p+i-1)
                        for log in self.logger:
                            log(block)

                        self.__HandleUserInterrupt(locals())    
                        self.messenger(umdutil.tstamp()+" RF Off...", [])
                        stat = mg.RFOff_Devices() # switch off after measure

                        self.rawData_MainCal[description].update({'efield': efields,
                                                                  'pref': prefant,
                                                                  'noise': noise,
                                                                  'etaTx': etaTx,
                                                                  'etaRx': etaRx,
                                                                  'mg': mg})
                        self.autosave_info={'prbposleft': prbposleft,
                                            'refantposleft': refantposleft,
                                            'LastMeasuredFreq': f,
                                            'LastMeasuredTpos': t,
                                            'PrbPosCounter': PrbPosCounter.copy(),
                                            'RefAntPosCounter': RefAntPosCounter.copy()}
                        # autosave class instance
                        if self.asname and (time.time()-self.lastautosave > self.autosave_interval):
                            self.messenger(umdutil.tstamp()+" autosave ...", [])
                            self.do_autosave()
                            self.messenger(umdutil.tstamp()+" ... done", [])

                        # END OF f LOOP
                    # test for low battery
                    lowBatList = mg.getBatteryLow_Devices()
                    if len(lowBatList):
                        self.messenger(umdutil.tstamp()+" WARNING: Low battery status detected for: %s"%(str(lowBatList)), [])
                #END OF t LOOP
##                self.rawData_MainCal[description].update({'efield': efields, 'pref': prefant, 'noise': noise, 'etaTx': etaTx, 'etaRx': etaRx, 'mg': mg})
##                # autosave class instance
##                if self.asname and (time.time()-self.lastautosave > self.autosave_interval):
##                    self.messenger(umdutil.tstamp()+" autosave ...", [])
##                    self.do_autosave()
##                    self.messenger(umdutil.tstamp()+" ... done", [])
##
                # decrease counter
                for f in freqs:
                    PrbPosCounter[f] -= nprb             
                    RefAntPosCounter[f] -= nrefant             
                prbposleft -= nprb
                refantposleft -= nrefant
            # END OF p LOOP
        #    print efields

                
        finally:
            # finally is executed if and if not an exception occur -> save exit
            self.messenger(umdutil.tstamp()+" RF Off and Quit...", [])
            stat = mg.RFOff_Devices()
            stat = mg.Quit_Devices()
        self.messenger(umdutil.tstamp()+" End of msc main calibration. Status: %d"%stat, [])
        self.post_user_event()
        return stat


    def Measure_Autocorrelation (self,
                           description="empty",
                           dotfile='testgr.dot',
                           delay=1.0,
                           SGLevel=-20,
                           leveling=None,
                           freqs=None,
                           toffsets=[1],
                           ntunerpos=[360],     
                           names={'sg': 'sg',
                                  'a1': 'a1',
                                  'a2': 'a2',
                                  'ant': 'ant',
                                  'pmfwd': 'pm1',
                                  'pmbwd': 'pm2',
                                  'fp': ['fp1','fp2','fp3','fp4','fp5', 'fp6','fp7','fp8'], 
                                  'tuner': ['tuner1']}):
        """Performs a msc autocorrelation measurement
        """
        self.pre_user_event()
        if self.autosave:
            self.messenger(umdutil.tstamp()+" Resume autocorrelation measurement from autosave...", [])
        else:
            self.messenger(umdutil.tstamp()+" Start new autocorrelation measurement...", [])
        self.rawData_AutoCorr.setdefault(description, {})

        if leveling is None:
            leveling = [{'condition': 'False',
                         'actor': None,
                         'actor_min': None,
                         'actor_max': None,
                         'watch': None,
                         'nominal': None,
                         'reader': None,
                         'path': None}]
                    
        # number of probes, ref-antenna and tuners
        nprb = len(names['fp'])
        ntuner = min(len(toffsets),len(ntunerpos),len(names['tuner']))

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
            stat = mg.RFOff_Devices()
            self.messenger(umdutil.tstamp()+" Zero devices...", [])
            stat = mg.Zero_Devices()
            self.messenger(umdutil.tstamp()+" ...done", [])
            try:
                level = self.set_level(mg, names, SGLevel)
            except AmplifierProtectionError, _e:
                self.messenger(umdutil.tstamp()+" Can not set signal generator level. Amplifier protection raised with message: %s"%_e.message, [])
                raise  # re raise to reach finaly clause
            if freqs is None:
                self.messenger(umdutil.tstamp()+" msc autocorrelation measurment terminated. No frequencies given.", [])
                raise UserWarning      # to reach finally statement

            positions = []
            for tunerindex in range(ntuner):
                positions.append( [tunerposindex*toffsets[tunerindex] for tunerposindex in range(ntunerpos[tunerindex])])
            positions = umdutil.combinations(positions)
            alltpos = positions   # unique and sorted
            # set up efields, ...
            efields={}
            if self.autosave:
                efields=self.rawData_AutoCorr[description]['efield'].copy()
                tlen = 1e300
                for f in efields.keys():
                    tees = efields[f].keys()
                    if len(tees)<tlen:
                        tlen=len(tees)
                        tf = f
                try:
                    tees = efields[tf].keys()
                except:
                    tees=[]
                for t in tees:
                    try:
                        alltpos.remove(eval(t))
                    except:
                        umdutil.LogError (self.messenger)
                msg = "List of tuner positions from autosave file:\n%s\n"%(str(tees))
                but = []
                self.messenger(msg, but)
            self.autosave=False    
                
            stat = mg.RFOff_Devices()
            msg = """Are you ready to start the measurement?\n\nStart: start measurement.\nQuit: quit measurement."""
            but = ["Start", "Quit"]
            answer = self.messenger(msg, but)
            if answer == but.index('Quit'):
                self.messenger(umdutil.tstamp()+" measurement terminated by user.", [])
                raise UserWarning      # to reach finally statement
            # loop tuner positions
            for t in alltpos:
                self.messenger(umdutil.tstamp()+" Tuner position %s"%(repr(t)), [])
                # position tuners
                self.messenger(umdutil.tstamp()+" Move tuner(s)...", [])
                for i in range(ntuner):
                    TPos = umddevice.UMDMResult(t[i], umddevice.UMD_deg)
                    IsPos = ddict[names['tuner'][i]].Goto (TPos, 0)
                self.messenger(umdutil.tstamp()+" ...done", [])
                # loop freqs
                for f in freqs:
                    self.messenger(umdutil.tstamp()+" Frequency %e Hz"%(f), [])
                    # switch if necessary
                    mg.EvaluateConditions()
                    # set frequency for all devices
                    (minf, maxf) = mg.SetFreq_Devices (f)
                    # cable corrections
                    c_sg_amp = mg.get_path_correction(names['sg'], names['a1'], umddevice.UMD_dB)
                    c_sg_ant = mg.get_path_correction(names['sg'], names['ant'], umddevice.UMD_dB)
                    c_a2_pm1 = mg.get_path_correction(names['a2'], names['pmfwd'], umddevice.UMD_dB)
                    c_a2_ant = mg.get_path_correction(names['a2'], names['ant'], umddevice.UMD_dB)
                    c_ant_pm2 = mg.get_path_correction(names['ant'], names['pmbwd'], umddevice.UMD_dB)
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

                    self.messenger(umdutil.tstamp()+" RF On...", [])
                    stat = mg.RFOn_Devices()   # switch on just before measure

                    level2 = self.do_leveling(leveling, mg, names, locals())
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
                        self.__addLoggerBlock(block[n]['parameter'], 'tunerpos', 'tuner position', t, {}) 
                        PFwd *= c_a2_ant['total']
                        self.__addLoggerBlock(block, 'c_a2_ant', 'Correction from amplifier output to antenna', c_a2_ant, {})
                        self.__addLoggerBlock(block['c_a2_ant']['parameter'], 'freq', 'the frequency [Hz]', f, {}) 
                        self.__addLoggerBlock(block, 'c_a2_pm1', 'Correction from amplifier output to fwd power meter', c_a2_pm1, {})
                        self.__addLoggerBlock(block['c_a2_pm1']['parameter'], 'freq', 'the frequency [Hz]', f, {}) 
                        PFwd /= c_a2_pm1['total']
                        self.__addLoggerBlock(block, n+'_corrected', 'Pfwd*c_a2_ant/c_a2_pm1', PFwd, {})
                        self.__addLoggerBlock(block[n]['parameter'], 'freq', 'the frequency [Hz]', f, {}) 
                        self.__addLoggerBlock(block[n]['parameter'], 'tunerpos', 'tuner position', t, {}) 
                    # pbwd
                    n = names['pmbwd']
                    if nbresult.has_key(n):
                        PBwd = umddevice.UMDCMResult(nbresult[n])
                        self.__addLoggerBlock(block, n, 'Reading of the bwd power meter', nbresult[n], {})
                        self.__addLoggerBlock(block[n]['parameter'], 'freq', 'the frequency [Hz]', f, {}) 
                        self.__addLoggerBlock(block[n]['parameter'], 'tunerpos', 'tuner position', t, {}) 
                        self.__addLoggerBlock(block, 'c_ant_pm2', 'Correction from antenna feed to bwd power meter', c_ant_pm2, {})
                        self.__addLoggerBlock(block['c_ant_pm2']['parameter'], 'freq', 'the frequency [Hz]', f, {}) 
                        PBwd /= c_ant_pm2['total']
                        self.__addLoggerBlock(block, n+'_corrected', 'Pbwd/c_ant_pm2', PBwd, {})
                        self.__addLoggerBlock(block[n]['parameter'], 'freq', 'the frequency [Hz]', f, {}) 
                        self.__addLoggerBlock(block[n]['parameter'], 'tunerpos', 'tuner position', t, {}) 


                    # e-field probes                
                    # read field probes
                    for i in range(nprb):
                        n = names['fp'][i]
                        if nbresult.has_key(n):
                            self.__addLoggerBlock(block, n, 'Reading of the e-field probe for position %d'%i, nbresult[n], {})
                            self.__addLoggerBlock(block[n]['parameter'], 'freq', 'the frequency [Hz]', f, {}) 
                            self.__addLoggerBlock(block[n]['parameter'], 'tunerpos', 'tuner position', t, {}) 
                            efields = self.__insert_it (efields, nbresult[n], PFwd, PBwd, f, t, i)
                    for log in self.logger:
                        log(block)

                    self.__HandleUserInterrupt(locals())    
                    self.messenger(umdutil.tstamp()+" RF Off...", [])
                    stat = mg.RFOff_Devices() # switch off after measure
                    # END OF f LOOP
                lowBatList = mg.getBatteryLow_Devices()
                if len(lowBatList):
                    self.messenger(umdutil.tstamp()+" WARNING: Low battery status detected for: %s"%(str(lowBatList)), [])
                self.rawData_AutoCorr[description].update({'efield': efields, 'tpos': alltpos, 'mg': mg})
                # autosave class instance
                if self.asname and (time.time()-self.lastautosave > self.autosave_interval):
                    self.messenger(umdutil.tstamp()+" autosave ...", [])
                    self.do_autosave()
                    self.messenger(umdutil.tstamp()+" ... done", [])

            #END OF t LOOP
                
        finally:
            # finally is executed if and if not an exception occur -> save exit
            self.messenger(umdutil.tstamp()+" RF Off and Quit...", [])
            stat = mg.RFOff_Devices()
            stat = mg.Quit_Devices()
        self.messenger(umdutil.tstamp()+" End of msc autocorelation measurement. Status: %d"%stat, [])
        self.post_user_event()
        return stat

    def __HandleUserInterrupt(self, dct, ignorelist='', handler=None):
        if callable(handler):
            return handler(dct,ignorelist=ignorelist)
        else:
            return self.stdUserInterruptHandler(dct,ignorelist=ignorelist)
    
    def stdUserInterruptHandler(self, dct, ignorelist=''):
        key = self.user_interrupt_tester() 
        if key and not chr(key) in ignorelist:
            # empty key buffer
            _k = self.user_interrupt_tester()
            while not _k is None:
                _k = self.user_interrupt_tester()

            mg = dct['mg']
            names = dct['names']
            f = dct['f']
            t = dct['t']
            ddict=dct['ddict']
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
                            level = self.set_level(mg, names, SGLevel)
                        except AmplifierProtectionError, _e:
                            self.messenger(umdutil.tstamp()+" Can not set signal generator level. Amplifier protection raised with message: %s"%_e.message, [])

                    # set frequency for all devices
                    (minf, maxf) = mg.SetFreq_Devices (f)
                    mg.EvaluateConditions()
                    # position tuners
                    if not t is None:
                        self.messenger(umdutil.tstamp()+" Move tuner(s)...", [])
                        for i in range(len(names['tuner'])):
                            TPos = umddevice.UMDMResult(t[i], umddevice.UMD_deg)
                            IsPos = ddict[names['tuner'][i]].Goto (TPos, 0)
                        self.messenger(umdutil.tstamp()+" ...done", [])
                elif answer == but2.index('Quit'):
                    self.messenger(umdutil.tstamp()+" measurment terminated by user.", [])
                    raise UserWarning      # to reach finally statement
            self.messenger(umdutil.tstamp()+" RF On...", [])
            stat = mg.RFOn_Devices()   # switch on just before measure
            if hassg:
                level2 = self.do_leveling(leveling, mg, names, locals())
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

    def Measure_EUTCal (self,
                           description="EUT",
                           dotfile='msc-calibration.dot',
                           delay=1.0,
                           freqs=None,
                           SGLevel=-20,
                            leveling=None,
                           calibration = 'empty',
                           names={'sg': 'sg',
                                  'a1': 'a1',
                                  'a2': 'a2',
                                  'ant': 'ant',
                                  'pmfwd': 'pm1',
                                  'pmbwd': 'pm2',
                                  'tuner': ['tuner1'],
                                  'refant': ['refant1'],
                                  'pmref': ['pmref1']}):
        """Performs a msc EUT calibration according to IEC 61000-4-21
        """

        self.pre_user_event()
        if self.autosave:
            self.messenger(umdutil.tstamp()+" Resume EUT calibration measurement from autosave...", [])
        else:
            self.messenger(umdutil.tstamp()+" Start new EUT calibration measurement...", [])

        self.rawData_EUTCal.setdefault(description, {})

        if leveling is None:
            leveling = [{'condition': 'False',
                         'actor': None,
                         'actor_min': None,
                         'actor_max': None,
                         'watch': None,
                         'nominal': None,
                         'reader': None,
                         'path': None}]
                            
        # number of probes, ref-antenna and tuners
        nprb = 0
        if names.has_key('fp'):   # default is no fieldprobes
            nprb = len(names['fp'])
        nrefant = min(len(names['refant']),len(names['pmref']))
        ntuner = len(names['tuner'])

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
            stat = mg.RFOff_Devices()
            self.messenger(umdutil.tstamp()+" Zero devices...", [])
            stat = mg.Zero_Devices()
            self.messenger(umdutil.tstamp()+" ...done", [])
            # set level
            try:
                level = self.set_level(mg, names, SGLevel)
            except AmplifierProtectionError, _e:
                self.messenger(umdutil.tstamp()+" Can not set signal generator level. Amplifier protection raised with message: %s"%_e.message, [])
                raise  # re raise to reach finaly clause
            # list of frequencies
            if freqs is None:
                freqs = []

            if self.rawData_MainCal.has_key(calibration):
                alltpos = self.GetAllTPos (calibration)            
            else:
                self.messenger(umdutil.tstamp()+" Error: Calibration '%s' not found."%calibration, [])
                return -1
            # set up efields, ...
            efields={}
            prefant={}
            noise={}
            etaTx = {}
            etaRx = {}

            if self.autosave:
                efields=self.rawData_EUTCal[description]['efield'].copy()
                prefant=self.rawData_EUTCal[description]['pref'].copy()
                noise=self.rawData_EUTCal[description]['noise'].copy()
                etaTx=self.rawData_EUTCal[description]['etaTx'].copy()
                etaRx=self.rawData_EUTCal[description]['etaRx'].copy()
                #
                # we have to loop over all tuner positions and
                # check if we have all freqs for this tpos
                # if complete -> remove from alltpos and add to tees 
                tees=[]
                for f in freqs:
                    measured_tpos = prefant[f].keys()
                    for t in alltpos:
                        if not self.UseTunerPos (calibration, f, t):
                            continue
                        # at this point f,t is a pair that should be measured
                        # we have to check if it was not
                        if str(t) not in measured_tpos:  # t has not been measured for this f
                            if not t in tees:  # dont append twice 
                                tees.append(t)
                        
                for t in tees:
                    try:
                        alltpos.remove(tt)
                    except:
                        umdutil.LogError (self.messenger)            
                msg = "List of tuner positions from autosave file:\n%s\nRemaining tuner positions:\n%s\n"%(str(tees),str(alltpos))
                but = []
                self.messenger(msg, but)
            self.autosave=False    
                
            stat = mg.RFOff_Devices()
            msg = """Position E field probes and reference antenna...\nAre you ready to start the measurement?\n\nStart: start measurement.\nQuit: quit measurement."""
            but = ["Start", "Quit"]
            answer = self.messenger(msg, but)
            if answer == but.index('Quit'):
                self.messenger(umdutil.tstamp()+" measurement terminated by user.", [])
                raise UserWarning      # to reach finally statement
            
            # loop tuner positions
            for t in alltpos:
                self.messenger(umdutil.tstamp()+" Tuner position %s"%(repr(t)), [])
                # position tuners
                self.messenger(umdutil.tstamp()+" Move tuner(s)...", [])
                for i in range(ntuner):
                    TPos = umddevice.UMDMResult(t[i], umddevice.UMD_deg)
                    IsPos = ddict[names['tuner'][i]].Goto (TPos, 0)
                self.messenger(umdutil.tstamp()+" ...done", [])
                # loop freqs
                for f in freqs:
                    self.messenger(umdutil.tstamp()+" Frequency %e Hz"%(f), [])
                    if not self.UseTunerPos (calibration, f, t):
                        self.messenger(umdutil.tstamp()+" Skipping tuner position", [])
                        continue
                    # switch if necessary
                    mg.EvaluateConditions()
                    # set frequency for all devices
                    (minf, maxf) = mg.SetFreq_Devices (f)
                    # cable corrections
                    c_sg_amp = mg.get_path_correction(names['sg'], names['a1'], umddevice.UMD_dB)
                    c_sg_ant = mg.get_path_correction(names['sg'], names['ant'], umddevice.UMD_dB)
                    c_a2_pm1 = mg.get_path_correction(names['a2'], names['pmfwd'], umddevice.UMD_dB)
                    c_a2_ant = mg.get_path_correction(names['a2'], names['ant'], umddevice.UMD_dB)
                    c_ant_pm2 = mg.get_path_correction(names['ant'], names['pmbwd'], umddevice.UMD_dB)
                    c_refant_pmref = []
                    for i in range(nrefant):
                        c_refant_pmref.append(mg.get_path_correction(names['refant'][i], names['pmref'][i], umddevice.UMD_dB))
                    c_fp = 1.0
                    if not etaTx.has_key(f):
                        eta = mg.GetAntennaEfficiency(names['ant'])
                        self.messenger(umdutil.tstamp()+" Eta_Tx for f = %e Hz is %s"%(f,str(eta)), [])
                        etaTx = self.__insert_it (etaTx, eta, None, None, f, t, 0)
                    if not etaRx.has_key(f):
                        for i in range(nrefant):
                            eta = mg.GetAntennaEfficiency(names['refant'][i])
                            self.messenger(umdutil.tstamp()+" Eta_Rx(%d) for f = %e Hz is %s"%(i,f,str(eta)), [])
                            etaRx = self.__insert_it (etaRx, eta, None, None, f, t, i)
                        

                    # ALL measurement start here
                    block = {}
                    nbresult = {} # dict for NB-Read results
                    pmreflist=[]
                    nblist = [names['pmfwd'], names['pmbwd']] # list of devices for NB Reading
                    # check for fwd pm
                    if mg.nodes[names['pmfwd']]['inst']:
                        NoPmFwd = False  # ok
                    else:  # no fwd pm
                        msg = umdutil.tstamp()+" WARNING: No fwd power meter. Signal generator output is used instead!"
                        answer = self.messenger(msg,[])
                        NoPmFwd = True
                        
                    for i in range(nrefant):
                        nblist.append(names['pmref'][i])
                        pmreflist.append(names['pmref'][i])
                    for i in range(nprb):
                        nblist.append(names['fp'][i])

                    # noise floor measurement..
                    if not noise.has_key(f):
                        self.messenger(umdutil.tstamp()+" Starting noise floor measurement for f = %e Hz ..."%(f), [])
                        mg.NBTrigger(pmreflist)
                        # serial poll all devices in list
                        olddevs = []
                        while 1:
                            self.__HandleUserInterrupt(locals())    
                            nbresult = mg.NBRead(pmreflist, nbresult)
                            new_devs=[i for i in nbresult.keys() if i not in olddevs]
                            olddevs = nbresult.keys()[:]
                            if len(new_devs):
                                self.messenger(umdutil.tstamp()+" Got answer from: "+str(new_devs), [])                            
                            if len(nbresult)==len(pmreflist):
                                break
                        for i in range(nrefant):
                            n = names['pmref'][i]
                            if nbresult.has_key(n):
                                # add path correction here
                                PRef = umddevice.UMDCMResult(nbresult[n])
                                nn = 'Noise '+n
                                self.__addLoggerBlock(block, nn, 'Noise reading of the receive antenna power meter for position %d'%i, nbresult[n], {})
                                self.__addLoggerBlock(block[nn]['parameter'], 'freq', 'the frequency [Hz]', f, {}) 
                                self.__addLoggerBlock(block, 'c_refant_pmref'+str(i), 'Correction from ref antenna feed to ref power meter', c_refant_pmref[i], {})
                                self.__addLoggerBlock(block['c_refant_pmref'+str(i)]['parameter'], 'freq', 'the frequency [Hz]', f, {}) 
                                PRef /= c_refant_pmref[i]['total']
                                self.__addLoggerBlock(block, nn+'_corrected', 'Noise: Pref/c_refant_pmref', PRef, {})
                                self.__addLoggerBlock(block[nn+'_corrected']['parameter'], 'freq', 'the frequency [Hz]', f, {}) 
                                self.__addLoggerBlock(block[nn+'_corrected']['parameter'], 'tunerpos', 'tuner position', t, {}) 
                                noise = self.__insert_it (noise, PRef, None, None, f, t, i)
                        self.messenger(umdutil.tstamp()+" Noise floor measurement done.", [])

                    self.messenger(umdutil.tstamp()+" RF On...", [])
                    stat = mg.RFOn_Devices()   # switch on just before measure

                    level2 = self.do_leveling(leveling, mg, names, locals())
                    if level2:
                        level=level2

                    # wait delay seconds
                    self.messenger(umdutil.tstamp()+" Going to sleep for %d seconds ..."%(delay), [])
                    self.wait(delay,locals(),self.__HandleUserInterrupt)
                    self.messenger(umdutil.tstamp()+" ... back.", [])

                        
                    # Trigger all devices in list
                    self.messenger(umdutil.tstamp()+" Send trigger to %s ..."%(str(nblist)), [])
                    mg.NBTrigger(nblist)
                    self.messenger(umdutil.tstamp()+" ... back.", [])
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
                        self.__addLoggerBlock(block[n]['parameter'], 'tunerpos', 'tuner position', t, {}) 
                        PFwd *= c_a2_ant['total']
                        self.__addLoggerBlock(block, 'c_a2_ant', 'Correction from amplifier output to antenna', c_a2_ant, {})
                        self.__addLoggerBlock(block['c_a2_ant']['parameter'], 'freq', 'the frequency [Hz]', f, {}) 
                        self.__addLoggerBlock(block, 'c_a2_pm1', 'Correction from amplifier output to fwd power meter', c_a2_pm1, {})
                        self.__addLoggerBlock(block['c_a2_pm1']['parameter'], 'freq', 'the frequency [Hz]', f, {}) 
                        PFwd /= c_a2_pm1['total']
                        self.__addLoggerBlock(block, n+'_corrected', 'Pfwd*c_a2_ant/c_a2_pm1', PFwd, {})
                        self.__addLoggerBlock(block[n]['parameter'], 'freq', 'the frequency [Hz]', f, {}) 
                        self.__addLoggerBlock(block[n]['parameter'], 'tunerpos', 'tuner position', t, {}) 
                    # pbwd
                    n = names['pmbwd']
                    if nbresult.has_key(n):
                        PBwd = umddevice.UMDCMResult(nbresult[n])
                        self.__addLoggerBlock(block, n, 'Reading of the bwd power meter', nbresult[n], {})
                        self.__addLoggerBlock(block[n]['parameter'], 'freq', 'the frequency [Hz]', f, {}) 
                        self.__addLoggerBlock(block[n]['parameter'], 'tunerpos', 'tuner position', t, {}) 
                        self.__addLoggerBlock(block, 'c_ant_pm2', 'Correction from antenna feed to bwd power meter', c_ant_pm2, {})
                        self.__addLoggerBlock(block['c_ant_pm2']['parameter'], 'freq', 'the frequency [Hz]', f, {}) 
                        PBwd /= c_ant_pm2['total']
                        self.__addLoggerBlock(block, n+'_corrected', 'Pbwd/c_ant_pm2', PBwd, {})
                        self.__addLoggerBlock(block[n]['parameter'], 'freq', 'the frequency [Hz]', f, {}) 
                        self.__addLoggerBlock(block[n]['parameter'], 'tunerpos', 'tuner position', t, {}) 

                    # ref-ant                
                    for i in range(nrefant):
                        n = names['pmref'][i]
                        if nbresult.has_key(n):
                            # add path correction here
                            PRef = umddevice.UMDCMResult(nbresult[n])
                            self.__addLoggerBlock(block, n, 'Reading of the receive antenna power meter for position %d'%i, nbresult[n], {})
                            self.__addLoggerBlock(block[n]['parameter'], 'freq', 'the frequency [Hz]', f, {}) 
                            self.__addLoggerBlock(block[n]['parameter'], 'tunerpos', 'tuner position', t, {}) 
                            self.__addLoggerBlock(block, 'c_refant_pmref'+str(i), 'Correction from ref antenna feed to ref power meter', c_refant_pmref[i], {})
                            self.__addLoggerBlock(block['c_refant_pmref'+str(i)]['parameter'], 'freq', 'the frequency [Hz]', f, {}) 
                            PRef /= c_refant_pmref[i]['total']
                            prefant = self.__insert_it (prefant, PRef, PFwd, PBwd, f, t, i)
                            self.__addLoggerBlock(block, n+'_corrected', 'Pref/c_refant_pmref', PRef, {})
                            self.__addLoggerBlock(block[n]['parameter'], 'freq', 'the frequency [Hz]', f, {}) 
                            self.__addLoggerBlock(block[n]['parameter'], 'tunerpos', 'tuner position', t, {}) 

                    # e-field probes                
                    # read field probes
                    for i in range(nprb):
                        n = names['fp'][i]
                        if nbresult.has_key(n):
                            self.__addLoggerBlock(block, n, 'Reading of the e-field probe for position %d'%i, nbresult[n], {})
                            self.__addLoggerBlock(block[n]['parameter'], 'freq', 'the frequency [Hz]', f, {}) 
                            self.__addLoggerBlock(block[n]['parameter'], 'tunerpos', 'tuner position', t, {}) 
                            efields = self.__insert_it (efields, nbresult[n], PFwd, PBwd, f, t, i)
                    for log in self.logger:
                        log(block)

                    self.__HandleUserInterrupt(locals())    
                    self.messenger(umdutil.tstamp()+" RF Off...", [])
                    stat = mg.RFOff_Devices() # switch off after measure
                    # END OF f LOOP
                lowBatList = mg.getBatteryLow_Devices()
                if len(lowBatList):
                    self.messenger(umdutil.tstamp()+" WARNING: Low battery status detected for: %s"%(str(lowBatList)), [])
                self.rawData_EUTCal[description].update({'efield': efields, 'pref': prefant, 'noise': noise, 'etaTx': etaTx, 'etaRx': etaRx, 'mg': mg})
                # autosave class instance
                if self.asname and (time.time()-self.lastautosave > self.autosave_interval):
                    self.messenger(umdutil.tstamp()+" autosave ...", [])
                    self.do_autosave()
                    self.messenger(umdutil.tstamp()+" ... done", [])
            #END OF t LOOP
                
        finally:
            # finally is executed if and if not an exception occur -> save exit
            self.messenger(umdutil.tstamp()+" RF Off and Quit...", [])
            stat = mg.RFOff_Devices()
            stat = mg.Quit_Devices()
        self.messenger(umdutil.tstamp()+" End of EUT main calibration. Status: %d"%stat, [])
        self.post_user_event()
        return stat

    def Measure_Immunity (self,
                          description="EUT",
                          dotfile='msc-immunity.dot',
                          calibration='empty',
                          kernel=(None,None),
                          leveling=None,
                          freqs=None,
                          names={'sg': 'sg',
                                  'a1': 'a1',
                                  'a2': 'a2',
                                  'ant': 'ant',
                                  'fp': [], 
                                  'pmfwd': 'pm1',
                                  'pmbwd': 'pm2',
                                  'tuner': ['tuner1'],
                                  'refant': ['refant1'],
                                  'pmref': ['pmref1']}):
        """Performs a msc immunity measurement according to IEC 61000-4-21
        """

        self.pre_user_event()
        if kernel[0] is None:
            if kernel[1] is None:
                kernel=(stdImmunityKernel,{'field': umddevice.UMDMResult(10, umddevice.UMD_Voverm),
                                            'dwell': 1,
                                            'keylist': 'sS'})
            else:
                kernel=(stdImmunityKernel,kernel[1])

        if freqs is None:
            freqs = []
        if leveling is None:
            leveling = [{'condition': 'False',
                         'actor': None,
                         'actor_min': None,
                         'actor_max': None,
                         'watch': None,
                         'nominal': None,
                         'reader': None,
                         'path': None}]
     
        if self.autosave:
            self.messenger(umdutil.tstamp()+" Resume MSC immunity measurement from autosave...", [])
        else:
            self.messenger(umdutil.tstamp()+" Start new MSC immunity measurement...", [])

        self.rawData_Immunity.setdefault(description, {})

        # number of ref-antenna and tuners
        nrefant = min(len(names['refant']),len(names['pmref']))
        ntuner = len(names['tuner'])
        nprb = len(names['fp'])

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

            if self.rawData_MainCal.has_key(calibration):
                alltpos = self.GetAllTPos (calibration)            
            else:
                self.messenger(umdutil.tstamp()+" Error: Calibration '%s' not found."%calibration, [])
                return -1
            if not self.processedData_EUTCal.has_key(description):
                self.messenger(umdutil.tstamp()+" Warning: EUT-Calibration '%s' not found. CLF = 1 will be used."%calibration, [])
            # set up prefant ...
            prefant={}
            efields = {}
            noise={}
            eutstat={}
            in_as={}

            if self.autosave:
                prefant=self.rawData_Immunity[description]['pref'].copy()
                efields=self.rawData_Immunity[description]['efield'].copy()
                noise=self.rawData_Immunity[description]['noise'].copy()
                eutstat=self.rawData_Immunity[description]['eutstatus'].copy()
                eutfreqs=eutstat.keys()
                nfreqs=len(eutfreqs)
                min_tpos=1e300
                max_tpos=-1
                for f in eutfreqs:
                    tpos=eutstat[f].keys()
                    in_as[f]={}
                    for t in tpos:
                        testfieldlist = [item['testfield'] for item in eutstat[f][t][0]]
                        in_as[f][t]=testfieldlist
                    min_tpos=min(min_tpos,len(tpos))
                    max_tpos=max(max_tpos,len(tpos))

                msg = "Number of frequencies: %d\nMin of tuner positions: %d\nMaximum of tuner positions: %d\n"%(nfreqs,min_tpos,max_tpos)
                but = []
                self.messenger(msg, but)
            self.autosave=False
                
            msg = "EUT immunity measurement.\nPosition reference antenna and EUT.\nSwitch EUT ON.\nAre you ready to start the measurement?\n\nStart: start measurement.\nQuit: quit measurement."
            but = ["Start", "Quit"]
            answer = self.messenger(msg, but)
            if answer == but.index('Quit'):
                self.messenger(umdutil.tstamp()+" measurement terminated by user.", [])
                raise UserWarning      # to reach finally statement
            
            tposdict={}
            for f in freqs:
                tposdict[f]=[t for t in alltpos if self.UseTunerPos (calibration, f, t)]

            etest=TestField(self,maincal=calibration,eutcal=description)
            ptest=TestPower(self,maincal=calibration,eutcal=description)
            kpardict={'tp': tposdict,
                      'messenger': self.messenger,
                      'UIHandler': None,
                      'locals': locals()}
            kpardict.update(kernel[1])
            kern = (kernel[0])(**kpardict)
            if kpardict['UIHandler'] is None:
                UIHandler=self.stdUserInterruptHandler
            else:
                UIHandler=getattr(kern, kpardict['UIHandler'], None)
            if not callable(UIHandler):
                UIHandler=self.stdUserInterruptHandler

            f=None
            t=None
            p=None
            RFon=False
            level = None
            testfield=None
            
            self.lastautosave=time.time()
            
            dispatchtable=('finished',
                           'freq',
                           'tuner',
                           'rf',
                           'efield',
                           'modulation',
                           'measure',
                           'eut',
                           'autosave')
            # test until break
            stat=0
            finished=False
            try:
                ignorekeys=kernel[1]['keylist']
            except:
                ignorekeys=''
            while not finished:
                cmd, msg, dct = kern.test(stat)
                if cmd is None:
                    stat=0
                    continue
                cmd=cmd.lower()
                self.messenger(umdutil.tstamp()+' Got cmd: %s, msg: %s, dct: %s'%(cmd, msg, pprint.pformat(dct)), [])
                if len(msg):
                    self.messenger(umdutil.tstamp()+" %s"%(msg), [])
                if cmd in ['finished']:
                    finished=True
                    stat = 0
                elif cmd in ['autosave']:
                    # autosave class instance
                    if self.asname and (time.time()-self.lastautosave > self.autosave_interval):
                        self.messenger(umdutil.tstamp()+" autosave ...", [])
                        self.do_autosave()
                        self.messenger(umdutil.tstamp()+" ... done", [])
                    stat=0
                elif cmd in ['freq']:
                    f = dct['freq']
                    self.messenger(umdutil.tstamp()+" Frequency %e Hz"%(f), [])
                    # switch if necessary
                    mg.EvaluateConditions()
                    # set frequency for all devices
                    (minf, maxf) = mg.SetFreq_Devices (f)
                    # cable corrections
                    c_sg_amp = mg.get_path_correction(names['sg'], names['a1'], umddevice.UMD_dB)
                    c_sg_ant = mg.get_path_correction(names['sg'], names['ant'], umddevice.UMD_dB)
                    c_a2_pm1 = mg.get_path_correction(names['a2'], names['pmfwd'], umddevice.UMD_dB)
                    c_a2_ant = mg.get_path_correction(names['a2'], names['ant'], umddevice.UMD_dB)
                    c_ant_pm2 = mg.get_path_correction(names['ant'], names['pmbwd'], umddevice.UMD_dB)
                    c_refant_pmref = []
                    for i in range(nrefant):
                        c_refant_pmref.append(mg.get_path_correction(names['refant'][i], names['pmref'][i], umddevice.UMD_dB))
                    c_fp = 1.0
                    #print "Got all Cable corrections"
                    #for i in range(nrefant):
                    #    print c_refant_pmref[i]

                    
                    # check for fwd pm
                    #print mg.nodes.keys()
                    if mg.nodes[names['pmfwd']]['inst']:
                        NoPmFwd = False  # ok
                    else:  # no fwd pm
                        msg = umdutil.tstamp()+" WARNING: No fwd power meter. Signal generator output is used instead!"
                        answer = self.messenger(msg,[])
                        NoPmFwd = True

                    
                    pmreflist=[]
                    nblist = [names['pmfwd'], names['pmbwd']] # list of devices for NB Reading
                    for i in range(nrefant):
                        nblist.append(names['pmref'][i])
                        pmreflist.append(names['pmref'][i])
                    for i in range(nprb):
                        nblist.append(names['fp'][i])

                    #print "NBList: ", nblist
                    # noise floor measurement..
                    if not noise.has_key(f):
                        self.messenger(umdutil.tstamp()+" Starting noise floor measurement for f = %e Hz ..."%(f), [])
                        if RFon:
                            mg.RFOff_Devices()
                        # ALL measurement start here
                        block = {}
                        mg.NBTrigger(pmreflist)
                        # serial poll all devices in list
                        olddevs = []
                        nbresult={}
                        while 1:
                            self.__HandleUserInterrupt(locals(), handler=UIHandler)    
                            nbresult = mg.NBRead(pmreflist, nbresult)
                            new_devs=[i for i in nbresult.keys() if i not in olddevs]
                            olddevs = nbresult.keys()[:]
                            if len(new_devs):
                                self.messenger(umdutil.tstamp()+" Got answer from: "+str(new_devs), [])                            
                            if len(nbresult)==len(pmreflist):
                                break
                        for i in range(nrefant):
                            n = names['pmref'][i]
                            if nbresult.has_key(n):
                                # add path correction here
                                PRef = umddevice.UMDCMResult(nbresult[n])
                                nn = 'Noise '+n
                                self.__addLoggerBlock(block, nn, 'Noise reading of the receive antenna power meter for position %d'%i, nbresult[n], {})
                                self.__addLoggerBlock(block[nn]['parameter'], 'freq', 'the frequency [Hz]', f, {}) 
                                self.__addLoggerBlock(block, 'c_refant_pmref'+str(i), 'Correction from ref antenna feed to ref power meter', c_refant_pmref[i], {})
                                self.__addLoggerBlock(block['c_refant_pmref'+str(i)]['parameter'], 'freq', 'the frequency [Hz]', f, {}) 
                                PRef /= c_refant_pmref[i]['total']
                                self.__addLoggerBlock(block, nn+'_corrected', 'Noise: Pref/c_refant_pmref', PRef, {})
                                self.__addLoggerBlock(block[nn+'_corrected']['parameter'], 'freq', 'the frequency [Hz]', f, {}) 
                                self.__addLoggerBlock(block[nn+'_corrected']['parameter'], 'tunerpos', 'tuner position', t, {}) 
                                noise = self.__insert_it (noise, PRef, None, None, f, t, i)
                        for log in self.logger:
                            log(block)
                        if RFon:
                            mg.RFOn_Devices()
                        self.messenger(umdutil.tstamp()+" Noise floor measurement done.", [])
                        stat = 0
                elif cmd in ['tuner']:
                    t = dct['tunerpos']
                    if type(t) != type([]):
                        t = [t]
                    self.messenger(umdutil.tstamp()+" Tuner position %s"%(repr(t)), [])
                    # position tuners
                    self.messenger(umdutil.tstamp()+" Move tuner(s)...", [])
                    for i,ti in enumerate(t):
                        TPos = umddevice.UMDMResult(ti, umddevice.UMD_deg)
                        IsPos = ddict[names['tuner'][i]].Goto(TPos, 0)
                    self.messenger(umdutil.tstamp()+" ...done", [])
                    stat = 0
                elif cmd in ['rf']:
                    rfon = dct['rfon']
                    if rfon == 1:
                        self.messenger(umdutil.tstamp()+' Switching RF On.', [])
                        mg.RFOn_Devices()
                        time.sleep(1)
                        RFon=True
                    else:
                        self.messenger(umdutil.tstamp()+' Switching RF Off.', [])
                        mg.RFOff_Devices()
                        RFon=False
                    stat = 0
                elif cmd in ['efield']:
                    efield = dct['efield']
                    if efield in ['max', 'Max', 'MAX']:
                        efield = self.getMaxE(mg,names,f,etest)
                        self.messenger("DEBUG: MaxEField: %s"%str(efield), [])
                    testfield=efield
                    power = umddevice.UMDCMResult(ptest(f, efield))
                    sgpower = power / c_sg_ant['total']
                    self.messenger("DEBUG: power: %s, c_sg_ant: %s, sgpower: %s"%(str(power), str(c_sg_ant['total']), str(sgpower)),[])
                    olevel=level
                    try:
                        level = self.set_level(mg,names,sgpower)
                    except AmplifierProtectionError, _e:
                        self.messenger(umdutil.tstamp()+" Can not set signal generator level. Amplifier protection raised with message: %s"%_e.message, [])
                        level=olevel
                        stat = 'AmplifierProtectionError'
                    else:
                        stat= 0
                elif cmd in ['modulation']:
                    stat=0
                elif cmd in ['measure']:
                    # Trigger all devices in list
                    block = {}
                    mg.NBTrigger(nblist)
                    # serial poll all devices in list
                    if NoPmFwd:
                        nbresult[names['pmfwd']] = level
                        nbresult[names['pmbwd']] = umddevice.UMDMResult(mg.zero(level.unit), level.get_unit())
                    olddevs = []
                    nbresult={}
                    while 1:
                        self.__HandleUserInterrupt(locals(), handler=UIHandler)    
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
                        self.__addLoggerBlock(block[n]['parameter'], 'tunerpos', 'tuner position', t, {}) 
                        PFwd *= c_a2_ant['total']
                        self.__addLoggerBlock(block, 'c_a2_ant', 'Correction from amplifier output to antenna', c_a2_ant, {})
                        self.__addLoggerBlock(block['c_a2_ant']['parameter'], 'freq', 'the frequency [Hz]', f, {}) 
                        self.__addLoggerBlock(block, 'c_a2_pm1', 'Correction from amplifier output to fwd power meter', c_a2_pm1, {})
                        self.__addLoggerBlock(block['c_a2_pm1']['parameter'], 'freq', 'the frequency [Hz]', f, {}) 
                        PFwd /= c_a2_pm1['total']
                        self.__addLoggerBlock(block, n+'_corrected', 'Pfwd*c_a2_ant/c_a2_pm1', PFwd, {})
                        self.__addLoggerBlock(block[n]['parameter'], 'freq', 'the frequency [Hz]', f, {}) 
                        self.__addLoggerBlock(block[n]['parameter'], 'tunerpos', 'tuner position', t, {}) 
                    # pbwd
                    n = names['pmbwd']
                    if nbresult.has_key(n):
                        PBwd = umddevice.UMDCMResult(nbresult[n])
                        self.__addLoggerBlock(block, n, 'Reading of the bwd power meter', nbresult[n], {})
                        self.__addLoggerBlock(block[n]['parameter'], 'freq', 'the frequency [Hz]', f, {}) 
                        self.__addLoggerBlock(block[n]['parameter'], 'tunerpos', 'tuner position', t, {}) 
                        self.__addLoggerBlock(block, 'c_ant_pm2', 'Correction from antenna feed to bwd power meter', c_ant_pm2, {})
                        self.__addLoggerBlock(block['c_ant_pm2']['parameter'], 'freq', 'the frequency [Hz]', f, {}) 
                        PBwd /= c_ant_pm2['total']
                        self.__addLoggerBlock(block, n+'_corrected', 'Pbwd/c_ant_pm2', PBwd, {})
                        self.__addLoggerBlock(block[n]['parameter'], 'freq', 'the frequency [Hz]', f, {}) 
                        self.__addLoggerBlock(block[n]['parameter'], 'tunerpos', 'tuner position', t, {}) 

                    # ref-ant                
                    for i in range(nrefant):
                        n = names['pmref'][i]
                        if nbresult.has_key(n):
                            # add path correction here
                            PRef = umddevice.UMDCMResult(nbresult[n])
                            self.__addLoggerBlock(block, n, 'Reading of the receive antenna power meter for position %d'%i, nbresult[n], {})
                            self.__addLoggerBlock(block[n]['parameter'], 'freq', 'the frequency [Hz]', f, {}) 
                            self.__addLoggerBlock(block[n]['parameter'], 'tunerpos', 'tuner position', t, {}) 
                            self.__addLoggerBlock(block, 'c_refant_pmref'+str(i), 'Correction from ref antenna feed to ref power meter', c_refant_pmref[i], {})
                            self.__addLoggerBlock(block['c_refant_pmref'+str(i)]['parameter'], 'freq', 'the frequency [Hz]', f, {}) 
                            PRef /= c_refant_pmref[i]['total']
                            prefant = self.__insert_it (prefant, PRef, PFwd, PBwd, f, t, i)
                            self.__addLoggerBlock(block, n+'_corrected', 'Pref/c_refant_pmref', PRef, {})
                            self.__addLoggerBlock(block[n]['parameter'], 'freq', 'the frequency [Hz]', f, {}) 
                            self.__addLoggerBlock(block[n]['parameter'], 'tunerpos', 'tuner position', t, {}) 

                    # e-field probes                
                    # read field probes
                    for i in range(nprb):
                        n = names['fp'][i]
                        if nbresult.has_key(n):
                            self.__addLoggerBlock(block, n, 'Reading of the e-field probe for position %d'%i, nbresult[n], {})
                            self.__addLoggerBlock(block[n]['parameter'], 'freq', 'the frequency [Hz]', f, {}) 
                            self.__addLoggerBlock(block[n]['parameter'], 'tunerpos', 'tuner position', t, {}) 
                            efields = self.__insert_it (efields, nbresult[n], PFwd, PBwd, f, t, i)

                    #print "vorm logger"
                    for log in self.logger:
                        log(block)
                    #print "hinterm logger"
                    lowBatList = mg.getBatteryLow_Devices()
                    #print "hinter 'getBatteryLow'"
                    if len(lowBatList):
                        self.messenger(umdutil.tstamp()+" WARNING: Low battery status detected for: %s"%(str(lowBatList)), [])
                    #print "vor update"
                    self.rawData_Immunity[description].update({'efield': efields, 'pref': prefant, 'noise': noise, 'mg': mg})                
                    #print "hinter update"
                    stat = 0
                    #print "End of 'measure'"
                elif cmd in ['eut']:
                    eutstatus = dct['eutstatus']
                    pf = prefant[f][repr(t)][0][-1]['pfwd']
                    pb = prefant[f][repr(t)][0][-1]['pbwd']
                    eutstat = self.__insert_it (eutstat, eutstatus, pf, pb, f, t, 0, {'testfield': testfield})
                    self.rawData_Immunity[description].update({'eutstatus': eutstat, 'mg': mg})
                    stat = 0
                else:
                    stat=-1
                    self.messenger(umdutil.tstamp()+" WARNING: Got unknown command '%s'. Command must be one of %s"%(cmd,str(dispatchtable)), [])
                
                self.__HandleUserInterrupt(locals(),ignorelist=ignorekeys, handler=UIHandler)
            #end of while loop
                
        finally:
            # finally is executed if and if not an exception occur -> save exit
            self.messenger(umdutil.tstamp()+" RF Off and Quit...", [])
            stat = mg.RFOff_Devices()
            stat = mg.Quit_Devices()
        self.messenger(umdutil.tstamp()+" End of Immunity mesurement. Status: %d"%stat, [])
        self.post_user_event()
        return stat
                          

    def getMaxE(self, mg, names, f, etest):
        start=names['sg']
        ends=[names['ant'],names['pmfwd'],names['pmbwd']]
        maxstart=None
        allpaths=[]
        for end in ends:
            allpaths.extend(mg.find_all_paths(start, end))
        for path in allpaths:
            edges = []
            for i in range(len(path)-1):
                left  = path[i]
                right = path[i+1]
                edges.append((left,right,mg.graph[left][right]))
            for left,right,edge in edges:
                try:
                    attribs = mg.nodes[edge['dev']]
                except KeyError:
                    continue
                if attribs['inst'] is None:
                    continue
                err = 0
                if (attribs.has_key('isActive') and attribs['isActive']):
                    dev=attribs['inst']
                    cmds = ['getData', 'GetData']
                    stat = -1
                    for cmd in cmds:
                        #print hasattr(dev, cmd)
                        if hasattr(dev, cmd):
                            # at the moment, we only check for MAXIN
                            what = ['MAXIN'] #['MAXIN', 'MAXFWD', 'MAXBWD']
                            for w in what:
                                result = umddevice.UMDCMResult()
                                stat = 0
                                try:
                                    stat = getattr(dev, cmd)(result, w)
                                except AttributeError:
                                    # function not callable
                                    #print "attrErr"
                                    continue 
                                if stat != 0:
                                    #print stat
                                    continue
                                # ok we have a value that can be checked
                                corr = mg.get_path_correction(start, left, umddevice.UMD_dB)
                                sglevel = result / corr['total']
                                sglevel = sglevel.mag()
                                #print "DEBUG: Node %s limits sglevel to %s"%(left,str(sglevel)) 
                                if maxstart:
                                    maxstart=min(maxstart,sglevel)
                                else:
                                    maxstart=umddevice.UMDMResult(sglevel)
            
        pathcorr=mg.get_path_correction(start, names['ant'], umddevice.UMD_dB)
        pfwd=maxstart*pathcorr['total'].mag()
        Emax = etest(f,pfwd)
        return Emax
        
##        
##        for n,attribs in mg.nodes.items():
##            print "DEBUG: Node %s"%n
##            if attribs['inst'] is None:
##                print "DEBUG: no attrib 'inst'"
##                continue  # not a real device
##            if not (attribs.has_key('isActive') and attribs['isActive']):
##                print "DEBUG: not active"
##                continue
##            # a real, device
##            if not mg.find_path(start, n):
##                print "DEBUG: no path from %s to %s"%(start, n)
##                continue
##            # ok, there is a connection to our start node
##            stat = -1
##            dev = attribs['inst']
##            for cmd in ['getData', 'GetData']:
##                if hasattr(dev, cmd):
##                    # at the moment, we only check for MAXIN
##                    what = ['MAXIN'] #['MAXIN', 'MAXFWD', 'MAXBWD']
##                    for w in what:
##                        result = umddevice.UMDCMResult()
##                        stat = 0
##                        try:
##                            stat = getattr(dev, cmd)(result, w)
##                        except (AttributeError,TypeError):
##                            # function not callable, what not supported
##                            #print "attrErr"
##                            print "DEBUG: failed to get 'MAXIN'"
##                            continue 
##                        if stat != 0:
##                            #print stat
##                            continue
##                        # ok we have a value that can be checked
##                        corr = mg.get_path_correction(start, n, umddevice.UMD_dB)
##                        print "DEBUG: node %s is limiting, corr = "%n, corr
##
##                        sglevel = result / corr['total']
##                        sglevel = sglevel.mag()
##                        print "DEBUG: Node %s limits sglevel to %s"%(n,str(sglevel)) 
##                        if maxstart:
##                            maxstart=min(maxstart,sglevel)
##                        else:
##                            maxstart=umddevice.UMDMResult(sglevel,sglevel.unit)
##            
##            pathcorr=mg.get_path_correction(start, end, umddevice.UMD_dB)
##            pfwd=maxstart*pathcorr['total'].mag()
##            Emax = etest(f,pfwd)
##        return Emax

    def Measure_Emission (self,
                           description="EUT",
                           dotfile='msc-emission.dot',
                            calibration = 'empty',
                           delay=1.0,
                           freqs=None,
                          receiverconf = None,
                           names={'tuner': ['tuner1'],
                                   'refant': ['refant1'],
                                  'receiver': ['saref1']}):
        """Performs a msc emission measurement according to IEC 61000-4-21
        """

        self.pre_user_event()
        if self.autosave:
            self.messenger(umdutil.tstamp()+" Resume MSC emission measurement from autosave...", [])
        else:
            self.messenger(umdutil.tstamp()+" Start new MSC emission measurement...", [])

        self.rawData_Emission.setdefault(description, {})

        # number of ref-antenna and tuners
        nrefant = min(len(names['refant']),len(names['receiver']))
        ntuner = len(names['tuner'])

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

            if self.rawData_MainCal.has_key(calibration):
                alltpos = self.GetAllTPos (calibration)            
            else:
                self.messenger(umdutil.tstamp()+" Error: Calibration '%s' not found."%calibration, [])
                return -1
            # set up prefant, noise, ...
            prefant={}
            noise={}

            if self.autosave:
                try:
                    prefant=self.rawData_Emission[description]['pref'].copy()
                except KeyError:   # as after noise -> no pref yet
                    pass
                noise=self.rawData_Emission[description]['noise'].copy()
                # we have to loop over all tuner positions and
                # check if we have all freqs for this tpos
                # if complete -> remove from alltpos and add to tees 
                tees=[]
                for f in freqs:
                    try:
                        measured_tpos = prefant[f].keys()
                    except KeyError:
                        measured_tpos = []
                    for t in alltpos:
                        if not self.UseTunerPos (calibration, f, t):
                            continue
                        # at this point f,t is a pair that should be measured
                        # we have to check if it was not
                        if str(t) not in measured_tpos:  # t has not been measured for this f
                            if not t in tees:  # dont append twice 
                                tees.append(t)
                        
                for t in tees:
                    try:
                        alltpos.remove(t)
                    except:
                        umdutil.LogError (self.messenger)            
                msg = "List of tuner positions from autosave file:\n%s\nRemaining tuner positions:\n%s\n"%(str(tees),str(alltpos))
                but = []
                self.messenger(msg, but)

##                tlen = 1e300
##                for f in prefant.keys():
##                    tees = prefant[f].keys()
##                    if len(tees)<tlen:
##                        tlen=len(tees)
##                        tf = f
##                try:
##                    tees = prefant[tf].keys()
##                except:
##                    tees=[]
##                for t in tees:
##                    try:
##                        alltpos.remove(t)
##                    except:
##                        umdutil.LogError (self.messenger)            
##                msg = "List of tuner positions from autosave file:\n%s\n"%(str(tees))
##                but = []
##                self.messenger(msg, but)
                
            if not self.autosave:  # if we come from autosave noise has already been measured
                self.autosave=False    
                msg = \
"""
Noise floor measurement.
Position reference antenna(s) and EUT.
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
                try:
                    t = alltpos[0]
                except IndexError:
                    t = [0]
                for f in freqs:
                    if f in noise.keys():
                        continue
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
                    c_refant_receiver = []
                    for i in range(nrefant):
                        c_refant_receiver.append(mg.get_path_correction(names['refant'][i], names['receiver'][i], umddevice.UMD_dB))

                    # ALL measurement start here
                    block = {}
                    nbresult = {} # dict for NB-Read results
                    receiverlist=[]
                        
                    for i in range(nrefant):
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
                    for i in range(nrefant):
                        n = names['receiver'][i]
                        if nbresult.has_key(n):
                            # add path correction here
                            PRef = umddevice.UMDCMResult(nbresult[n])
                            nn = 'Noise '+n
                            self.__addLoggerBlock(block, nn, 'Noise reading of the receive antenna receiver for position %d'%i, nbresult[n], {})
                            self.__addLoggerBlock(block[nn]['parameter'], 'freq', 'the frequency [Hz]', f, {}) 
                            self.__addLoggerBlock(block, 'c_refant_receiver'+str(i), 'Correction from ref antenna feed to ref receiver', c_refant_receiver[i], {})
                            self.__addLoggerBlock(block['c_refant_receiver'+str(i)]['parameter'], 'freq', 'the frequency [Hz]', f, {}) 
                            PRef /= c_refant_receiver[i]['total']
                            self.__addLoggerBlock(block, nn+'_corrected', 'Noise: Pref/c_refant_receiver', PRef, {})
                            self.__addLoggerBlock(block[nn+'_corrected']['parameter'], 'freq', 'the frequency [Hz]', f, {}) 
                            self.__addLoggerBlock(block[nn+'_corrected']['parameter'], 'tunerpos', 'tuner position', t, {}) 
                            noise = self.__insert_it (noise, PRef, None, None, f, t, i)
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
            self.autosave=False    


            msg = \
"""
EUT measurement.
Position reference antenna(s) and EUT.
Switch EUT ON.
Are you ready to start the measurement?

Start: start measurement.
Quit: quit measurement.
"""
            but = ["Start", "Quit"]
            answer = self.messenger(msg, but)
            if answer == but.index('Quit'):
                self.messenger(umdutil.tstamp()+" measurement terminated by user.", [])
                raise UserWarning      # to reach finally statement
            
            # loop tuner positions
            for t in alltpos:
                self.messenger(umdutil.tstamp()+" Tuner position %s"%(repr(t)), [])
                # position tuners
                self.messenger(umdutil.tstamp()+" Move tuner(s)...", [])
                for i in range(ntuner):
                    TPos = umddevice.UMDMResult(t[i], umddevice.UMD_deg)
                    IsPos = ddict[names['tuner'][i]].Goto (TPos, 0)
                self.messenger(umdutil.tstamp()+" ...done", [])
                # loop freqs
                for f in freqs:
                    self.messenger(umdutil.tstamp()+" Frequency %e Hz"%(f), [])
                    if not self.UseTunerPos (calibration, f, t):
                        self.messenger(umdutil.tstamp()+" Skipping tuner position", [])
                        continue
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
                    c_refant_receiver = []
                    for i in range(nrefant):
                        c_refant_receiver.append(mg.get_path_correction(names['refant'][i], names['receiver'][i], umddevice.UMD_dB))

                    # ALL measurement start here
                    block = {}
                    nbresult = {} # dict for NB-Read results
                    nblist = [] # list of devices for NB Reading
                        
                    for i in range(nrefant):
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

                    # ref-ant                
                    for i in range(nrefant):
                        n = names['receiver'][i]
                        if nbresult.has_key(n):
                            # add path correction here
                            PRef = umddevice.UMDCMResult(nbresult[n])
                            self.__addLoggerBlock(block, n, 'Reading of the receive antenna receiver for position %d'%i, nbresult[n], {})
                            self.__addLoggerBlock(block[n]['parameter'], 'freq', 'the frequency [Hz]', f, {}) 
                            self.__addLoggerBlock(block[n]['parameter'], 'tunerpos', 'tuner position', t, {}) 
                            self.__addLoggerBlock(block, 'c_refant_receiver'+str(i), 'Correction from ref antenna feed to ref receiver', c_refant_receiver[i], {})
                            self.__addLoggerBlock(block['c_refant_receiver'+str(i)]['parameter'], 'freq', 'the frequency [Hz]', f, {}) 
                            PRef /= c_refant_receiver[i]['total']
                            prefant = self.__insert_it (prefant, PRef, None, None, f, t, i)
                            self.__addLoggerBlock(block, n+'_corrected', 'Pref/c_refant_receiver', PRef, {})
                            self.__addLoggerBlock(block[n]['parameter'], 'freq', 'the frequency [Hz]', f, {}) 
                            self.__addLoggerBlock(block[n]['parameter'], 'tunerpos', 'tuner position', t, {}) 

                    for log in self.logger:
                        log(block)

                    self.__HandleUserInterrupt(locals())    
                    # END OF f LOOP
                lowBatList = mg.getBatteryLow_Devices()
                if len(lowBatList):
                    self.messenger(umdutil.tstamp()+" WARNING: Low battery status detected for: %s"%(str(lowBatList)), [])
                self.rawData_Emission[description].update({'pref': prefant, 'mg': mg})
                # autosave class instance
                if self.asname and (time.time()-self.lastautosave > self.autosave_interval):
                    self.messenger(umdutil.tstamp()+" autosave ...", [])
                    self.do_autosave()
                    self.messenger(umdutil.tstamp()+" ... done", [])
            #END OF t LOOP
                
        finally:
            # finally is executed if and if not an exception occur -> save exit
            self.messenger(umdutil.tstamp()+" Quit...", [])
            stat = mg.Quit_Devices()
        self.messenger(umdutil.tstamp()+" End of Emission mesurement. Status: %d"%stat, [])
        self.post_user_event()
        return stat

    def GetAllTPos (self, description):
        try:
            data = self.rawData_MainCal[description]['efield']
        except:
            return []
        freqs = data.keys()
        freqs.sort()
        ntuner = len(eval(data[freqs[0]].keys()[0]))   # ;-)
        pos = []
        for n in range(ntuner):
            pos.append([])
        for f in freqs:
            for n in range(ntuner):
                lst = [eval(data[f].keys()[i])[n] for i in range(len(data[f].keys()))]
                for l in lst:
                    if l not in pos[n]:
                        pos[n].append(l)
        for p in pos:
            p.sort()
        alltpos = umdutil.combinations (pos)
        return alltpos

    def UseTunerPos (self, description, f, t):
        try:
            data = self.rawData_MainCal[description]['efield']
        except:
            return False
        freqs = data.keys()
        freqs.sort()
        freqs.reverse()
        for fi in freqs:
            if f>= fi:
                break
        tlist = data[fi].keys()
        if str(t) in tlist:
            return True
        else:
            return False

    def OutputRawData_MainCal (self, description=None, what=None, fname=None):
        thedata = self.rawData_MainCal
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

    def OutputRawData_AutoCorr (self, description=None, what=None, fname=None):
        thedata = self.rawData_AutoCorr
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
##        # fuers praktikum
##        deslist = self.__MakeDeslist(thedata, description)
##        whatlist = self.__MakeWhatlist(thedata, what)
##        for d in deslist:
##            print "# Description:", d
##            for w in ['efield']:
##                print "# ", w
##                data = thedata[d][w]
##                freqs = data.keys()
##                tees = self.rawData_AutoCorr[d]['tpos']
##                pees = data[freqs[0]][str(tees[0])].keys()
##                for f in freqs:
##                    for p in pees:
##                        name = str(d)+'-'+str(w)+'-'+ str(f)
##                        name = name + '-prb' + str(p) + '.dat'
##                        out = file(name, 'w+')
##                        for t in tees:
##                            out.write(str(t[0])+'\t'+str(data[f][str(t)][p][0]['value'][0].get_v())+'\t'+str(data[f][str(t)][p][0]['value'][1].get_v())+'\t'+str(data[f][str(t)][p][0]['value'][2].get_v())+'\n')
##                        out.close()

    def OutputRawData_EUTCal (self, description=None, what=None, fname=None):
        thedata = self.rawData_EUTCal
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

    def OutputRawData_Immunity (self, description=None, what=None, fname=None):
        thedata = self.rawData_Immunity
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
        deslist = self.make_deslist(thedata, description)
        whatlist = self.make_whatlist(thedata, what)
        for d in deslist:
            print "# Description:", d
            for w in whatlist:
                print "# ", w
                data = thedata[d][w]
                try:
                    freqs = data.keys()
                    freqs.sort()
                    for f in freqs:
                        tees = data[f].keys()
                        tees.sort()
                        for t in tees:
                            pees = data[f][t].keys()
                            pees.sort()
                            for p in pees:
                                print "f:", f,"t:", t, "p:", p,
                                item = data[f][t][p]
                                self.out(item)
                                print
                except:  # data has no keys
                    item = data
                    self.out(item)
                    print
                        
    def OutputProcessedData_MainCal (self, description=None, what=None, fname=None):
        thedata = self.processedData_MainCal
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

    def OutputProcessedData_EUTCal (self, description=None, what=None, fname=None):
        thedata = self.processedData_EUTCal
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

    def OutputProcessedData_AutoCorr (self, description=None, what=None, fname=None):
        thedata = self.processedData_AutoCorr
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

    def OutputProcessedData_Immunity (self, description=None, what=None, fname=None):
        thedata = self.processedData_Immunity
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
        deslist = self.make_deslist(thedata, description)
        whatlist = self.make_whatlist(thedata, what)
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
            

    def GetKeys_MainCal(self):
        return self.processedData_MainCal.keys()

    def GetFreqs_MainCal(self, description):
        if self.rawData_MainCal.has_key(description):
            freqs = self.rawData_MainCal[description]['efield'].keys()
            freqs.sort()
            return freqs
        else:
            return []

    def getStandard(self, s=None):
        if s is None:
            s=self.std_Standard
        ls=s.lower()
        if 'iec' in ls or '21' in ls:
            return 'IEC 61000-4-21'
        elif 'rtca' in ls or '160' in ls:
            return 'RTCA DO160E'
        elif 'mil' in ls or '461' in ls:
            return 'MILSTD 461E'
        else:
            return self.std_Standard

    def MaxtoAvET2(self):
        t=[1,2,3,4,5,9,10,12,18,20,24,30,36,40,45,60,90,120,180,400,1000]
        r=[1,1.313,1.499,1.630,1.732,1.957,2,2.08,2.25,2.3,2.38,2.47,2.54,2.59,2.64,2.76,2.92,3.04,3.2,3.6,3.97]
        return scipy.interpolate.interp1d(t,r)

    def Evaluate_MainCal(self, description="empty", standard=None):
        standard = self.getStandard(standard)
        self.messenger(umdutil.tstamp()+" Start of evaluation of main calibration with description %s"%description, [])
        if not self.rawData_MainCal.has_key(description):
            self.messenger(umdutil.tstamp()+" Description %s not found."%description, [])
            return -1
            
        zeroPR = umddevice.UMDMResult(0.0,umddevice.UMD_powerratio)
        zeroVm = umddevice.UMDMResult(0.0,umddevice.UMD_Voverm)            
        zeroVmoversqrtW = umddevice.UMDMResult(0.0,umddevice.UMD_VovermoversqrtW)            

        efields = self.rawData_MainCal[description]['efield']
        pref = self.rawData_MainCal[description]['pref']
        freqs = efields.keys()
        freqs.sort()

        self.processedData_MainCal.setdefault(description,{})
        self.processedData_MainCal[description]['Standard_Used']=standard
        self.processedData_MainCal[description]['PMaxRec']={}
        self.processedData_MainCal[description]['PAveRec']={}
        self.processedData_MainCal[description]['PInputForEField']={}
        self.processedData_MainCal[description]['PInputForRecAnt']={}
        self.processedData_MainCal[description]['PInputVarationForEField']={}
        self.processedData_MainCal[description]['PInputVarationForRecAnt']={}
        self.processedData_MainCal[description]['ACF'] = {}
        self.processedData_MainCal[description]['IL'] = {}
        self.processedData_MainCal[description]['EMax']={}
        self.processedData_MainCal[description]['EMaxT']={}
        self.processedData_MainCal[description]['Enorm']={}
        self.processedData_MainCal[description]['EnormT']={}
        self.processedData_MainCal[description]['EnormTmax2']={} # normalized averaged squared Magnitude of Efield cal (DO160 20.6.3.3) 
        self.processedData_MainCal[description]['EnormAveXYZ']={}
        self.processedData_MainCal[description]['EnormAve']={}
        self.processedData_MainCal[description]['EnormTAve']={}
        self.processedData_MainCal[description]['SigmaXYZ']={}
        self.processedData_MainCal[description]['Sigma24']={}
        self.processedData_MainCal[description]['SigmaXYZ_dB'] = {}
        self.processedData_MainCal[description]['Sigma24_dB'] = {}
        # the evaluation has to be done for all frequencies
        for f in freqs:
            tees = efields[f].keys() #tuner positions
            pees = efields[f][tees[0]].keys() #e-field probe positions
            prees = pref[f][tees[0]].keys() #ref antenna positions
            tees.sort()
            pees.sort()
            prees.sort()
            ntees = len(tees)
            npees = len(pees)
            nprees = len(prees)
            # EMaxL EMaxTL, PInputL and PInputVariation
            # are all dicts with key=e-field probe pos
            # and items are lists (because values in raw data are lists allready)
            EMaxL = {}  # for R components
            EMaxTL = {} # same for total field
            PInputEL = {} #input for a certain field strength
            PInputVariationEL = {} # max to min ratio
            for p in pees:  # positions in the room, keys for the dicts
                EMax = umddevice.stdVectorUMDMResult()
                for k in range(3):  # x,y,z
                    EMax.append(zeroVm)
                EMaxT=zeroVm
                PInput = umddevice.UMDMResult(0.0, umddevice.UMD_W)
                PInputMin = umddevice.UMDMResult(1.0e10, umddevice.UMD_W)
                PInputMax = umddevice.UMDMResult(0.0, umddevice.UMD_W)
                InCounter = 0
                for t in tees:  # tuner positions-> max values with respect to tuner
                    for i in range(len(efields[f][t][p])): #typically, len=1
                        ef = efields[f][t][p][i]['value'] # x,y,z vector
                        #import pprint
                        #pprint.pprint(ef)
                        #print len(ef), ef[0], ef[1], ef[2]
                        for k in range(3): # max for each component
                            EMax[k] = umdutil.MRmax(EMax[k], ef[k].convert(umddevice.UMD_Voverm))
                        et=umdutil.MR_RSS(ef) # max of rss (E_T)
                        EMaxT=umdutil.MRmax(EMaxT, et.convert(umddevice.UMD_Voverm))
                        
                        pf = efields[f][t][p][i]['pfwd'].convert(umddevice.UMD_W)
                        pf = pf.mag()
                        PInputMin = umdutil.MRmin(PInputMin, pf) # min  
                        PInputMax = umdutil.MRmax(PInputMax, pf) # max
                        PInput += pf # av 
                        InCounter += 1
                PInput /= InCounter
                EMaxL[p]=EMax  # for each probe pos: Max over tuner positions
                EMaxTL[p]=EMaxT
                PInputVariation = PInputMax / PInputMin
                PInputEL[p]=PInput
                PInputVariationEL[p] = PInputVariation

            # receive antenna calibration
            PMaxRecL = {}  # again, keys are the positions and values are lists
            PAveRecL = {}
            PInputAL = {}
            PInputVariationAL = {}
            for p in prees:   # ref antenna positions -> keys
                PMaxRec = umddevice.UMDMResult(0.0, umddevice.UMD_W)
                PAveRec = umddevice.UMDMResult(0.0, umddevice.UMD_W)
                RecCounter = 0
                PInput = umddevice.UMDMResult(0.0, umddevice.UMD_W)
                PInputMin = umddevice.UMDMResult(1.0e10, umddevice.UMD_W)
                PInputMax = umddevice.UMDMResult(0.0, umddevice.UMD_W)
                InCounter = 0
                for t in tees:
                    try:
                        pref[f][t][p]
                    except KeyError:
                        pref[f][t][p]=pref[f][t][0][:]
                    for i in range(len(pref[f][t][p])):
                        pr = pref[f][t][p][i]['value'].convert(umddevice.UMD_W)
                        pr = pr.mag()
                        PMaxRec = umdutil.MRmax(PMaxRec, pr) 
                        PAveRec += pr
                        RecCounter += 1
                        pf = pref[f][t][p][i]['pfwd'].convert(umddevice.UMD_W)
                        pf = pf.mag()
                        PInputMin = umdutil.MRmin(PInputMin, pf) 
                        PInputMax = umdutil.MRmax(PInputMax, pf) 
                        PInput += pf
                        InCounter += 1
                PAveRec  /= RecCounter
                PMaxRecL[p]=PMaxRec
                PAveRecL[p]=PAveRec    # for each receive antenna pos: Max and Av over tuner positions
                PInput  /=InCounter
                PInputVariation = PInputMax / PInputMin
                PInputAL[p]=PInput
                PInputVariationAL[p] = PInputVariation
                    
                
            self.processedData_MainCal[description]['PMaxRec'][f]=PMaxRecL.copy()
            self.processedData_MainCal[description]['PAveRec'][f]=PAveRecL.copy()
            self.processedData_MainCal[description]['PInputForEField'][f]=PInputEL.copy()
            self.processedData_MainCal[description]['PInputForRecAnt'][f]=PInputAL.copy()
            self.processedData_MainCal[description]['PInputVarationForEField'][f]=PInputVariationEL.copy()
            self.processedData_MainCal[description]['PInputVarationForRecAnt'][f]=PInputVariationAL.copy()
            self.processedData_MainCal[description]['EMax'][f]=EMaxL.copy()
            self.processedData_MainCal[description]['EMaxT'][f]=EMaxTL.copy()

            # calc ACF and IL
            IL = zeroPR
            for pos,Pmax in PMaxRecL.items():            
                IL += Pmax/PInputAL[pos]
            IL /= len(PMaxRecL.keys())
            ACF = zeroPR
            for pos,Pav in PAveRecL.items():            
                ACF += Pav/PInputAL[pos]
            ACF /= len(PAveRecL.keys())
            self.processedData_MainCal[description]['ACF'][f] = ACF
            self.processedData_MainCal[description]['IL'][f] = IL

            Avxyz = umddevice.stdVectorUMDMResult()
            for k in range(3):
                Avxyz.append(zeroVmoversqrtW)
            self.processedData_MainCal[description]['Enorm'][f]={}
            self.processedData_MainCal[description]['EnormT'][f]={}
            for pos,Em in EMaxL.items():
                pin = self.processedData_MainCal[description]['PInputForEField'][f][pos] 
                v = pin.get_v()
                sqrtv=math.sqrt(v)
                u = pin.get_u()
                l = pin.get_l()
                sqrtPInput = umddevice.UMDMResult(sqrtv, sqrtv+(u-l)/(4.0*sqrtv), sqrtv-(u-l)/(4.0*sqrtv), umddevice.UMD_sqrtW)
                en = umddevice.stdVectorUMDMResult()
                for k in range(len(Em)):
                    en.append(Em[k]/sqrtPInput)
                    Avxyz[k] += en[k]
                self.processedData_MainCal[description]['Enorm'][f][pos]=en
            AvT = zeroVmoversqrtW
            for pos,Em in EMaxTL.items():
                pin = self.processedData_MainCal[description]['PInputForEField'][f][pos] 
                v = pin.get_v()
                sqrtv=math.sqrt(v)
                u = pin.get_u()
                l = pin.get_l()
                sqrtPInput = umddevice.UMDMResult(sqrtv, sqrtv+(u-l)/(4.0*sqrtv), sqrtv-(u-l)/(4.0*sqrtv), umddevice.UMD_sqrtW)
                en=Em/sqrtPInput
                self.processedData_MainCal[description]['EnormT'][f][pos]=en
                AvT+=en
            AvT /= len(EMaxTL)
            Av24 = zeroVmoversqrtW
            for k in range(3):
                Avxyz[k] /= len(EMaxL.keys())
                Av24 += Avxyz[k]
            Av24 /= 3.0
            self.processedData_MainCal[description]['EnormAveXYZ'][f]=Avxyz
            self.processedData_MainCal[description]['EnormAve'][f]=Av24
            self.processedData_MainCal[description]['EnormTAve'][f]=AvT
            enorm = self.processedData_MainCal[description]['Enorm'][f]
            Sxyz = umddevice.stdVectorUMDMResult()
            list24 = []
            for k in range(3):
                lst = [enorm[p][k] for p in enorm.keys()]
                list24+=lst
                S = umdutil.CalcSigma(lst, Avxyz[k])
                Sxyz.append(S)            
            S24 = umdutil.CalcSigma(list24, Av24)
            
            self.processedData_MainCal[description]['SigmaXYZ'][f]=Sxyz
            self.processedData_MainCal[description]['Sigma24'][f]=S24
            SdBxyz = umddevice.stdVectorUMDMResult()
            for k in range(3):
                SdBxyz.append(((Sxyz[k]+Avxyz[k])/Avxyz[k]).convert(umddevice.UMD_dB))
            SdB24 = ((S24+Av24)/Av24).convert(umddevice.UMD_dB)
            self.processedData_MainCal[description]['SigmaXYZ_dB'][f] = SdBxyz
            self.processedData_MainCal[description]['Sigma24_dB'][f] = SdB24

        self.messenger(umdutil.tstamp()+" End of evaluation of main calibration", [])
        return 0

    def Evaluate_Emission(self, 
                          description="EUT", 
                          empty_cal="empty", 
                          loaded_cal="loaded", 
                          EUT_cal="EUT", 
                          interpolation = 'linxliny', 
                          distance = 10, 
                          directivity= 1.7,
                          hg=0.8,
                          RH=(0.8,0.8),
                          isoats=None):
        if isoats==None:
            isoats=False
        if isoats:
            gmax=umdutil.gmax_oats
            gmax_model="OATS"
        else:
            gmax=umdutil.gmax_fs
            gmax_model="FAR"
        dmax_f=directivity

        EUTrawData=self.rawData_EUTCal
        EUTprocData=self.processedData_EUTCal
            

        self.messenger(umdutil.tstamp()+" Start of evaluation of emission measurement with description %s"%description, [])
        if not self.rawData_Emission.has_key(description):
            self.messenger(umdutil.tstamp()+" Description %s not found."%description, [])
            return -1
        if not self.rawData_MainCal.has_key(empty_cal):
            self.messenger(umdutil.tstamp()+" Empty chamber cal not found. Description: %s"%empty_cal, [])
            return -1
        if not self.rawData_MainCal.has_key(loaded_cal):
            self.messenger(umdutil.tstamp()+" Loaded chamber cal not found. Description: %s"%loaded_cal, [])
            return -1
        if not EUTrawData.has_key(EUT_cal):
            self.messenger(umdutil.tstamp()+" EUT cal not found. Description: %s"%EUT_cal, [])
            return -1
	
        zeroPR = umddevice.UMDMResult(0.0,umddevice.UMD_powerratio)
        
        pref = self.rawData_Emission[description]['pref']
        noise= self.rawData_Emission[description]['noise']
        freqs = pref.keys()
        freqs.sort()

        # check loading
        empty_loaded = empty_cal +','+loaded_cal
        if not self.processedData_MainCal.has_key(empty_loaded):
            self.CalculateLoading_MainCal(empty_cal=empty_cal, loaded_cal=loaded_cal)
        maxload = self.processedData_MainCal[empty_loaded]['Loading']
        empty_eut = empty_cal +','+EUT_cal
        if not EUTprocData.has_key(empty_eut):
            self.CalculateLoading_EUTCal(empty_cal=empty_cal, eut_cal=EUT_cal, freqs=freqs)
        eutload = EUTprocData[empty_eut]['Loading']

        
        #cal_freqs = self.rawData_MainCal[empty_cal]['efield'].keys().sort()
        #maxload_org = maxload.values()
        maxload_inter = umdutil.InterpolateMResults(maxload, freqs, interpolation)

        etaTx_org = {}
        etaTx = self.rawData_MainCal[empty_cal]['etaTx']
        for f in etaTx.keys():
            t = etaTx[f].keys()[0]
            p = etaTx[f][t].keys()[0]
            for ei in etaTx[f][t][p]:
                if not ei['value'] is None:
                    break
            etaTx_org[f]=ei['value']
        etaTx_inter = umdutil.InterpolateMResults(etaTx_org, freqs, interpolation)

        il_org = self.processedData_MainCal[empty_cal]['IL']
        il_inter = umdutil.InterpolateMResults(il_org, freqs, interpolation)

        #eutcal_freqs = self.processedData_EUTCal[EUT_cal]['CCF'].keys()
        ccf = EUTprocData[EUT_cal]['CCF']
        clf = EUTprocData[EUT_cal]['CLF']
        ccf_inter = umdutil.InterpolateMResults(ccf, freqs, interpolation)
        clf_inter = umdutil.InterpolateMResults(clf, freqs, interpolation)

        relload={}
        for i,f in enumerate(freqs):
            relload[f]=eutload[f]/maxload_inter[i]

        self.processedData_Emission.setdefault(description,{})        
        self.processedData_Emission[description]['PMaxRec']={}
        self.processedData_Emission[description]['PAveRec']={}
        self.processedData_Emission[description]['PRad_from_CCF']={}
        self.processedData_Emission[description]['PRad_from_CLF']={}
        self.processedData_Emission[description]['ERad_from_CCF']={}
        self.processedData_Emission[description]['ERad_from_CLF']={}
        self.processedData_Emission[description]['PRad_noise']={}
        self.processedData_Emission[description]['ERad_noise']={}
        self.processedData_Emission[description]['Asumed_Directivity']={}
        self.processedData_Emission[description]['Gmax_Model']=gmax_model
        self.processedData_Emission[description]['Assumed_hg']=hg
        self.processedData_Emission[description]['Assumed_RH']=RH
        self.processedData_Emission[description]['Asumed_Distance']=umddevice.UMDMResult(distance,umddevice.UMD_m)
        self.processedData_Emission[description]['RelLoading']=relload.copy()
        
        for i,f in enumerate(freqs):
            if callable(directivity):
                dmax_f=directivity(f)
            self.processedData_Emission[description]['Asumed_Directivity'][f]=umddevice.UMDMResult(dmax_f,umddevice.UMD_powerratio)
            i = freqs.index(f)
            tees = pref[f].keys()
            prees = pref[f][tees[0]].keys()
            tees.sort()
            prees.sort()   
            ntees = len(tees)
            nprees = len(prees)

            npr = noise[f][tees[0]][prees[0]][0]['value'].convert(umddevice.UMD_W)
            npr = npr.mag()
            npr *= etaTx_inter[i]/ccf_inter[i]
            npr = npr.convert(umddevice.UMD_W)
            gmax_f=gmax(f,s=distance,hg=hg,RH=RH)
            #print gmax_f['h'], gmax_f['v']
            gm=max(gmax_f['h'], gmax_f['v'])
            neccf_v = math.sqrt(dmax_f*npr.get_v()*30)*gm
            neccf_u = math.sqrt(dmax_f*npr.get_u()*30)*gm
            #print dmax_f*npr.get_l()*30
            neccf_l = math.sqrt(max(0,dmax_f*npr.get_l()*30))*gm
            nERad = umddevice.UMDMResult(neccf_v, neccf_u, neccf_l, umddevice.UMD_Voverm)
            self.processedData_Emission[description]['PRad_noise'][f]=npr
            self.processedData_Emission[description]['ERad_noise'][f]=nERad

            PMaxRecL = {}
            PAveRecL = {}
            PRadCCFL={}
            PRadCLFL={}
            ERadCCFL={}
            ERadCLFL={}
            for p in prees:
                PMaxRec = umddevice.UMDMResult(0.0, umddevice.UMD_W)
                PAveRec = umddevice.UMDMResult(0.0, umddevice.UMD_W)
                RecCounter = 0
                for t in tees:
                    for k in range(len(pref[f][t][p])):
                        pr = pref[f][t][p][k]['value'].convert(umddevice.UMD_W)
                        pr = pr.mag()
                        PMaxRec = umdutil.MRmax(PMaxRec, pr)        
                        PAveRec += pr
                        RecCounter += 1
                PAveRec /= RecCounter
                PMaxRecL[p]=PMaxRec
                PAveRecL[p]=PAveRec    # for each receive antenna pos: Max and Av over tuner positions
                PRadCCFL[p]=PAveRec*etaTx_inter[i]/ccf_inter[i]
                PRadCLFL[p]=PMaxRec*etaTx_inter[i]/(clf_inter[i]*il_inter[i])
                prccf = PRadCCFL[p].convert(umddevice.UMD_W)
                prclf = PRadCLFL[p].convert(umddevice.UMD_W)
                eccf_v = math.sqrt(dmax_f*prccf.get_v()*30)*gm
                eccf_u = math.sqrt(dmax_f*prccf.get_u()*30)*gm
                eccf_l = math.sqrt(max(0,dmax_f*prccf.get_l()*30))*gm
                ERadCCFL[p] = umddevice.UMDMResult(eccf_v, eccf_u, eccf_l, umddevice.UMD_Voverm)
                eclf_v = math.sqrt(dmax_f*prclf.get_v()*30)*gm
                eclf_u = math.sqrt(dmax_f*prclf.get_u()*30)*gm
                eclf_l = math.sqrt(max(0,dmax_f*prclf.get_l()*30))*gm
                ERadCLFL[p] = umddevice.UMDMResult(eclf_v, eclf_u, eclf_l, umddevice.UMD_Voverm)
                
            self.processedData_Emission[description]['PMaxRec'][f]=PMaxRecL.copy()
            self.processedData_Emission[description]['PAveRec'][f]=PAveRecL.copy()
            self.processedData_Emission[description]['PRad_from_CCF'][f]=PRadCCFL.copy()
            self.processedData_Emission[description]['PRad_from_CLF'][f]=PRadCLFL.copy()
            self.processedData_Emission[description]['ERad_from_CCF'][f]=ERadCCFL.copy()
            self.processedData_Emission[description]['ERad_from_CLF'][f]=ERadCLFL.copy()
            

        self.messenger(umdutil.tstamp()+" End of evaluation of emission measurement", [])
        return 0

    def Evaluate_Immunity(self,
                          description="EUT",
                          empty_cal="empty",
                          loaded_cal="loaded",
                          EUT_cal="EUT",
                          EUT_OK=None,
                          interpolation = 'linxliny'):
        self.messenger(umdutil.tstamp()+" Start of evaluation of immunity measurement with description %s"%description, [])
        if not self.rawData_Immunity.has_key(description):
            self.messenger(umdutil.tstamp()+" Description %s not found."%description, [])
            return -1
        if not self.rawData_MainCal.has_key(empty_cal):
            self.messenger(umdutil.tstamp()+" Empty chamber cal not found. Description: %s"%empty_cal, [])
            return -1
        if not self.rawData_MainCal.has_key(loaded_cal):
            self.messenger(umdutil.tstamp()+" Loaded chamber cal not found. Description: %s"%loaded_cal, [])
            return -1
        if not self.rawData_EUTCal.has_key(EUT_cal):
            self.messenger(umdutil.tstamp()+" WARNING: EUT cal not found. Description: %s"%EUT_cal, [])
            EUT_cal=None

        if EUT_OK==None:
            EUT_OK = self.std_eut_status_checker

        zeroPR = umddevice.UMDMResult(0.0,umddevice.UMD_powerratio)
        
        testfield_from_pfwd = TestField(self, maincal=empty_cal, eutcal=EUT_cal)
        
        pref = self.rawData_Immunity[description]['pref']
        eut = self.rawData_Immunity[description]['eutstatus']
        freqs = pref.keys()
        freqs.sort()

        # check loading
        empty_loaded = empty_cal +','+loaded_cal
        if not self.processedData_MainCal.has_key(empty_loaded):
            self.CalculateLoading_MainCal(empty_cal=empty_cal, loaded_cal=loaded_cal)
        maxload = self.processedData_MainCal[empty_loaded]['Loading']
        maxload_inter = umdutil.MResult_Interpol(maxload, interpolation)

        relload={}
        if EUT_cal:
            empty_eut = empty_cal +','+EUT_cal
            if not self.processedData_EUTCal.has_key(empty_eut):
                self.CalculateLoading_EUTCal(empty_cal=empty_cal, eut_cal=EUT_cal, freqs=freqs)
            eutload = self.processedData_EUTCal[empty_eut]['Loading']
            eutload_inter = umdutil.MResult_Interpol(eutload, interpolation)
            #clf = self.processedData_EUTCal[EUT_cal]['CLF']
            #clf_inter = umdutil.InterpolateMResults(clf, freqs, interpolation)
            for f in freqs:
                relload[f]=eutload_inter[f]/maxload_inter[f]

        self.processedData_Immunity.setdefault(description,{})        
        self.processedData_Immunity[description]['PMaxRec']={}
        self.processedData_Immunity[description]['PAveRec']={}
        self.processedData_Immunity[description]['RelLoading']=relload.copy()
        self.processedData_Immunity[description]['EUTImmunityThreshold']={}
        
        for i,f in enumerate(freqs):
            tees = pref[f].keys()
            prees = pref[f][tees[0]].keys()
            tees.sort()
            prees.sort()   

            ntees = len(tees)
            nprees = len(prees)

            PMaxRecL = {}
            PAveRecL = {}
            for p in prees:
                PMaxRec = umddevice.UMDMResult(0.0, umddevice.UMD_W)
                PAveRec = umddevice.UMDMResult(0.0, umddevice.UMD_W)
                RecCounter = 0
                for t in tees:
                    for val in pref[f][t][p]:
                        pr = val['value'].convert(umddevice.UMD_W)
                        pr = pr.mag()
                        PMaxRec = umdutil.MRmax(PMaxRec, pr)        
                        PAveRec += pr
                        RecCounter += 1
                PAveRec /= RecCounter
                PMaxRecL[p]=PMaxRec
                PAveRecL[p]=PAveRec    # for each receive antenna pos: Max and Av over tuner positions
            
            self.processedData_Immunity[description]['PMaxRec'][f]=PMaxRecL.copy()
            self.processedData_Immunity[description]['PAveRec'][f]=PAveRecL.copy()

        eutfreqs = eut.keys()
        eutfreqs.sort()
        for f in eutfreqs:
            thres = []
            tees = eut[f].keys()
            tees.sort()
            real_tf = None
            for t in tees:
                pees = eut[f][t].keys()
                pees.sort()
                for p in pees:
                    for val in eut[f][t][p]:
                        try:
                            eutstat = val['value']
                            testfield = val['testfield']
                            pfwd=val['pfwd']
                            real_tf = testfield_from_pfwd(f,pfwd)
                            if not EUT_OK(eutstat):
                                thres.append({'TestField': testfield, 'Field from Pfwd': real_tf, 'EUT': eutstat})
                        except:
                            raise
            if not len(thres):
                thres.append({'TestField': testfield, 'Field from Pfwd': real_tf, 'EUT': 'Maximum testfield reached'})
                        
            self.processedData_Immunity[description]['EUTImmunityThreshold'][f]=thres[:]

        self.messenger(umdutil.tstamp()+" End of evaluation of Immunity measurement", [])
        return 0



    def stdTPosCmp (self, t1, t2):
        # t is a list of tuner pos: ['[0,...]', '[10,...]', ...]
        # eval strings first..
        try:
            t1 = eval(t1)
        except TypeError:
            pass
        try:
            t2 = eval(t2)
        except TypeError:
            pass
        d1 = sum(t1)
        d2 = sum(t2)
        return cmp(d1,d2)

    def Evaluate_AutoCorr(self,
                          description="empty",
                          lag=None,
                          alpha=0.05,
                          rho=0.44,
                          rho0=None,
                          skip=None,
                          every=1,
                          offset=0):            
        if skip is None:
            skip = []
        self.messenger(umdutil.tstamp()+" Start of evaluation of autocorrelation measurement with description %s"%description, [])
        if not self.rawData_AutoCorr.has_key(description):
            self.messenger(umdutil.tstamp()+" Description %s not found."%description, [])
            return -1
        self.processedData_AutoCorr.setdefault(description,{})        
            
        efields = self.rawData_AutoCorr[description]['efield']
        tpos = self.rawData_AutoCorr[description]['tpos']
        tpos.sort(self.TPosCmp)   # possibly plug in other cmp routine
        freqs = efields.keys()
        freqs.sort()

        if not 'DistributuionOfr'in skip:
            self.messenger(umdutil.tstamp()+" Calculating pdf and cdf of the autocorrelation coefficient ...", [])
            r, psi ,cpsi = umdutil.CalcPsi(len(tpos),rho)
            self.messenger(umdutil.tstamp()+" ... done.", [])
            self.processedData_AutoCorr[description]['DistributuionOfr']={}
            self.processedData_AutoCorr[description]['DistributuionOfr']['n']=len(tpos)
            self.processedData_AutoCorr[description]['DistributuionOfr']['r']=r[:]
            self.processedData_AutoCorr[description]['DistributuionOfr']['pdf']=psi[:]
            self.processedData_AutoCorr[description]['DistributuionOfr']['cdf']=cpsi[:]
            self.processedData_AutoCorr[description]['DistributuionOfr']['rho']=rho
            self.messenger(umdutil.tstamp()+" Calculating critical limit of the autocorelation coeficient rho0 ...", [])
            rho0 = umdutil.CalcRho0(r, cpsi, alpha)
            self.processedData_AutoCorr[description]['DistributuionOfr']['rho0']=rho0[alpha]
            self.messenger(umdutil.tstamp()+" ...done.", [])
            self.messenger(umdutil.tstamp()+" N=%d, alpha=%f, rho0=%f"%(len(tpos),alpha,rho0[alpha]), [])
        

        self.processedData_AutoCorr[description]['TunerPositions']=tpos[:]            
        if not 'AutoCorrelation' in skip:
            self.processedData_AutoCorr[description]['AutoCorrelation']={}
        if not 'NIndependentBoundaries' in skip:
            self.processedData_AutoCorr[description]['NIndependentBoundaries']={}
        if not 'Statistic' in skip:
            rpy.r.library('ctest')
            ray=umdutil.RayleighDist()
            self.processedData_AutoCorr[description]['Statistic']={}
        for _i,f in filter(lambda (_i,_f): not (_i+offset)%every, enumerate(freqs)):
            try:
                lagf=lag(f)
            except:
                lagf=lag
            if not 'AutoCorrelation' in skip:
                self.messenger(umdutil.tstamp()+" Calculating autocorrelation f = %e"%f, [])
                self.processedData_AutoCorr[description]['AutoCorrelation'][f]={}
                ac_f = self.processedData_AutoCorr[description]['AutoCorrelation'][f]
                pees = efields[f][str(tpos[0])].keys()
                for p in pees:
                    self.messenger(umdutil.tstamp()+" p = %d"%p, [])
                    ac_f[p]={}
                    for k in range(len(efields[f][str(tpos[0])][p][0]['value'])):
                        self.messenger(umdutil.tstamp()+" k = %d"%k, [])
                        ees = []
                        for t in tpos:
                            ees.append(efields[f][str(t)][p][0]['value'][k])
                        self.messenger(umdutil.tstamp()+" Calculating autocorrelation ...", [])
                        r=umdutil.autocorr(ees,lagf,cyclic=True)
                        self.messenger(umdutil.tstamp()+" ...done", [])
                        ac_f[p][k]=r[:]
                self.messenger(umdutil.tstamp()+" ...done", [])
            if not 'NIndependentBoundaries' in skip:
                self.messenger(umdutil.tstamp()+" Calculating Number of Independent Boundaries f = %e"%f, [])
                self.processedData_AutoCorr[description]['NIndependentBoundaries'][f]={}
                ac_f = self.processedData_AutoCorr[description]['AutoCorrelation'][f]
                nib_f = self.processedData_AutoCorr[description]['NIndependentBoundaries'][f]
                pees = efields[f][str(tpos[0])].keys()
                for p in pees:
                    self.messenger(umdutil.tstamp()+" p = %d"%p, [])
                    nib_f[p]={}
                    for k in range(len(efields[f][str(tpos[0])][p][0]['value'])):
                        self.messenger(umdutil.tstamp()+" k = %d"%k, [])
                        nib_f[p][k]=None
                        for i,_v in enumerate(ac_f[p][k]):
                            try:
                                ri=_v.get_v()
                            except:
                                ri=_v
                            if ri < rho0[alpha]:
                                # interpolation
                                m=ri-ac_f[p][k][i-1].get_v()  # i=0 can not happen
                                b=ri-m*i
                                try:
                                    iinter=(rho0[alpha]-b)/m
                                except ZeroDivisionError:
                                    iinter = 1.0*i
                                nib_f[p][k] = len(tpos)/iinter   # division by zero can not happen because r[i] = 1 and rho0<=1
                                #print f*1.0,p,k,r[i]*1.0,i,nib_f[p][k]
                                self.messenger(umdutil.tstamp()+" f=%e, p=%d, k=%d, r=%s, lag=%f, Nindependent=%f"%(f*1.0,p,k,str(_v),iinter,nib_f[p][k]), [])
                                break
                self.messenger(umdutil.tstamp()+" ...done", [])
            if not 'Statistic' in skip:
                self.messenger(umdutil.tstamp()+" Calculating statistic f = %e"%f, [])
                self.processedData_AutoCorr[description]['Statistic'][f]={}
                s_f = self.processedData_AutoCorr[description]['Statistic'][f]
                ees24={}
                pees = efields[f][str(tpos[0])].keys()
                for p in pees:
                    self.messenger(umdutil.tstamp()+" p = %d"%p, [])
                    s_f[p]={}
                    for k in range(len(efields[f][str(tpos[0])][p][0]['value'])):
                        self.messenger(umdutil.tstamp()+" k = %d"%k, [])
                        # now, we have to redure the data set accoreding the result of the autocorr evaluation
                        ntotal = len(tpos)
                        try:
                            n_ind = self.processedData_AutoCorr[description]['NIndependentBoundaries'][f][p][k]
                        except:
                            self.messenger(umdutil.tstamp()+" WARNING: No of independent boundaries not found. Using all boundaries.",[])
                            n_ind = ntotal   # fall back
                        # use autocor information
                        posidx = umdutil.idxset(int(n_ind), len(tpos))
                        ees = []
                        for i,t in enumerate(tpos):
                            evalue=efields[f][str(t)][p][0]['value'][k].convert(umddevice.UMD_Voverm).get_v()
                            ees24.setdefault(str(t),[]).append(evalue)
                            if i in posidx:
                                ees.append(evalue)
                        ees.sort()      # values only, no ebars, unit is V/m
                        s_f[p][k]={}
                        ss=s_f[p][k]
                        ss['n']=n_ind
                        hist=rpy.r.hist(ees,plot=False) # dict with keys: density, equidist, breaks, intensities, counts, xname, mids
                        ss['hist']=hist.copy()
                        e_cdf = rpy.r.ecdf(ees)
                        ss['samples']=ees[:]
                        ss['ecdf']=e_cdf(ees)[:]
                        # cost function for the fit
                        cost=umdutil.Chi2Cost(ees,ss['ecdf'],ray.cdf)
                        s_fit=abs(scipy.optimize.brent(cost,brack=(ees[0],ees[-1])))
                        ss['fitted_shape']=s_fit
                        ss['cdf-fit']=[ray.cdf(e,s_fit) for e in ees]
                        # calc estimates for cho2-test
                        estimates=[]
                        for i in range(len(hist['counts'])):
                            estimates.append(ray.cdf(hist['breaks'][i+1],s_fit)-ray.cdf(hist['breaks'][i],s_fit))
                        result_chi2 = rpy.r.chisq_test(hist['counts'],p=estimates)
                        ss['p-chisquare']=result_chi2['p.value']
                        result_ks = rpy.r.ks_test(ss['ecdf'], ss['cdf-fit'], exact=1)
                        ss['p-KS']=result_ks['p.value']
                        #
                        # try different                        
                        #
                        ss['p-values_disttest']={}
                        for n_ind in range(len(tpos),2,-1):
                            posidx = umdutil.idxset(n_ind, len(tpos))
                            ees = []
                            for i,t in enumerate(tpos):
                                if i in posidx:
                                    ees.append(efields[f][str(t)][p][0]['value'][k].convert(umddevice.UMD_Voverm).get_v())
                            ees.sort()      # values only, no ebars, unit is V/m
                            hist=rpy.r.hist(ees,plot=False) # dict with keys: density, equidist, breaks, intensities, counts, xname, mids
                            e_cdf = rpy.r.ecdf(ees)
                            # cost function for the fit
                            cost=umdutil.Chi2Cost(ees,e_cdf(ees),ray.cdf)
                            s_fit=abs(scipy.optimize.brent(cost,brack=(ees[0],ees[-1])))
                            estimates=[]
                            for i in range(len(hist['counts'])):
                                estimates.append(ray.cdf(hist['breaks'][i+1],s_fit)-ray.cdf(hist['breaks'][i],s_fit))
                            result_chi2 = rpy.r.chisq_test(hist['counts'],p=estimates)
                            cdffit=[ray.cdf(e,s_fit) for e in ees]
                            result_ks = rpy.r.ks_test(e_cdf(ees), cdffit, exact=1)
                            ss['p-values_disttest'][n_ind]={'chisq': result_chi2['p.value'], 'KS': result_ks['p.value']}
#                            print n_ind, result_chi2['p.value'], result_ks['p.value']
#                            if result_chi2['p.value'] > 0.05 and result_ks['p.value'] > 0.05:
#                                self.messenger(umdutil.tstamp()+" "%(n_ind+1, result_ks['p.value'], result_chi2['p.value']))
#                                break
                            
                        ss['hist_disttest']=hist.copy()
                        ss['samples_disttest']=ees[:]
                        ss['ecdf_disttest']=e_cdf(ees)[:]
                        ss['fitted_shape_disttest']=s_fit
                        ss['cdf-fit_disttest']=cdffit
                        ss['p-chisquare_disttest']=result_chi2['p.value']
                        ss['p-KS_disttest']=result_ks['p.value']
                        self.messenger(umdutil.tstamp()+" f=%e, p=%d, k=%d, p_ks_disttest=%e, p_chi2-disttest=%e"%(f*1.0,p,k,ss['p-KS_disttest'],ss['p-chisquare_disttest']), [])                     
                # now we try with all 24 e-field vals for one freq
                ss=s_f[0][0]
                ss['p-values_disttest24']={}
                for n_ind in range(len(tpos),2,-1):
                    posidx = umdutil.idxset(n_ind, len(tpos))
                    ees = []
                    for i,t in enumerate(tpos):
                        if i in posidx:
                            ees.extend(ees24[str(t)])
                    ees.sort()      # values only, no ebars, unit is V/m
                    hist=rpy.r.hist(ees,plot=False) # dict with keys: density, equidist, breaks, intensities, counts, xname, mids
                    e_cdf = rpy.r.ecdf(ees)
                    # cost function for the fit
                    cost=umdutil.Chi2Cost(ees,e_cdf(ees),ray.cdf)
                    s_fit=abs(scipy.optimize.brent(cost,brack=(ees[0],ees[-1])))
                    estimates=[]
                    for i in range(len(hist['counts'])):
                        estimates.append(ray.cdf(hist['breaks'][i+1],s_fit)-ray.cdf(hist['breaks'][i],s_fit))
                    result_chi2 = rpy.r.chisq_test(hist['counts'],p=estimates)
                    cdffit=[ray.cdf(e,s_fit) for e in ees]
                    result_ks = rpy.r.ks_test(e_cdf(ees), cdffit, exact=1)
                    ss['p-values_disttest24'][n_ind]={'chisq': result_chi2['p.value'], 'KS': result_ks['p.value']}
                    
                ss['hist_disttest24']=hist.copy()
                ss['samples_disttest24']=ees[:]
                ss['ecdf_disttest24']=e_cdf(ees)[:]
                ss['fitted_shape_disttest24']=s_fit
                ss['cdf-fit_disttest24']=cdffit
                ss['p-chisquare_disttest24']=result_chi2['p.value']
                ss['p-KS_disttest24']=result_ks['p.value']
                self.messenger(umdutil.tstamp()+" f=%e, p_ks_disttest24=%e, p_chi2-disttest24=%e"%(f*1.0,ss['p-KS_disttest24'],ss['p-chisquare_disttest24']), [])
       
                self.messenger(umdutil.tstamp()+" ...done", [])

        self.messenger(umdutil.tstamp()+" End of evaluation of autocorrelation measurement", [])
        return 0        

    def Evaluate_EUTCal(self, description="EUT", calibration="empty"):
        self.messenger(umdutil.tstamp()+" Start of evaluation of EUT calibration with description %s"%description, [])
        if not self.rawData_EUTCal.has_key(description):
            self.messenger(umdutil.tstamp()+" Description %s not found."%description, [])
            return -1
        if not self.rawData_MainCal.has_key(calibration):
            self.messenger(umdutil.tstamp()+" Calibration %s not found."%calibration, [])
            return -1
            
        zeroPR = umddevice.UMDMResult(0.0,umddevice.UMD_powerratio)
        zeroVm = umddevice.UMDMResult(0.0,umddevice.UMD_Voverm)            
        zeroVmoversqrtW = umddevice.UMDMResult(0.0,umddevice.UMD_VovermoversqrtW)            

        efields = self.rawData_EUTCal[description]['efield']
        pref = self.rawData_EUTCal[description]['pref']
        noise = self.rawData_EUTCal[description]['noise']
        freqs = pref.keys()
        freqs.sort()

        self.processedData_EUTCal.setdefault(description,{})        
        self.processedData_EUTCal[description]['PMaxRec']={}
        self.processedData_EUTCal[description]['PAveRec']={}
        self.processedData_EUTCal[description]['PInputForEField']={}
        self.processedData_EUTCal[description]['PInputForRecAnt']={}
        self.processedData_EUTCal[description]['PInputVarationForEField']={}
        self.processedData_EUTCal[description]['PInputVarationForRecAnt']={}
        self.processedData_EUTCal[description]['CCF'] = {}
        self.processedData_EUTCal[description]['CLF'] = {}
        self.processedData_EUTCal[description]['CCF_from_PMaxRec'] = {}
        self.processedData_EUTCal[description]['CLF_from_PMaxRec'] = {}
        self.processedData_EUTCal[description]['EMax']={}
        self.processedData_EUTCal[description]['Enorm']={}
        self.processedData_EUTCal[description]['EnormAveXYZ']={}
        self.processedData_EUTCal[description]['EnormAve']={}
        self.processedData_EUTCal[description]['SigmaXYZ']={}
        self.processedData_EUTCal[description]['Sigma24']={}
        self.processedData_EUTCal[description]['SigmaXYZ_dB'] = {}
        self.processedData_EUTCal[description]['Sigma24_dB'] = {}
        for f in freqs:
            tees = pref[f].keys()
            pees = []
            if efields.has_key(f):
                pees = efields[f][tees[0]].keys()
            prees = pref[f][tees[0]].keys()
            tees.sort()
            pees.sort()
            prees.sort()
            ntees = len(tees)
            npees = len(pees)
            nprees = len(prees)

            EMaxL = {}
            PInputEL = {}
            PInputVariationEL = {}
            for p in pees:
                EMax = umddevice.stdVectorUMDMResult()
                for k in range(3):
                    EMax.append(zeroVm)
                PInput = umddevice.UMDMResult(0.0, umddevice.UMD_W)
                PInputMin = umddevice.UMDMResult(1.0e10, umddevice.UMD_W)
                PInputMax = umddevice.UMDMResult(0.0, umddevice.UMD_W)
                InCounter = 0
                for t in tees:
                    for i in range(len(efields[f][t][p])):
                        ef = efields[f][t][p][i]['value']
                        for k in range(3):
                            EMax[k] = umdutil.MRmax(EMax[k], ef[k].convert(umddevice.UMD_Voverm))
                        pf = efields[f][t][p][i]['pfwd'].convert(umddevice.UMD_W)
                        pf = pf.mag()
                        PInputMin = umdutil.MRmin(PInputMin, pf) 
                        PInputMax = umdutil.MRmax(PInputMax, pf) 
                        PInput += pf
                        InCounter += 1
                EMaxL[p]=EMax  # for each probe pos: Max over tuner positions
                PInput /= InCounter
                PInputVariation = PInputMax / PInputMin
                PInputEL[p]=PInput
                PInputVariationEL[p] = PInputVariation

            PMaxRecL = {}
            PAveRecL = {}
            PInputAL = {}
            PInputVariationAL = {}
            for p in prees:
                PMaxRec = umddevice.UMDMResult(0.0, umddevice.UMD_W)
                PAveRec = umddevice.UMDMResult(0.0, umddevice.UMD_W)
                RecCounter = 0
                PInput = umddevice.UMDMResult(0.0, umddevice.UMD_W)
                PInputMin = umddevice.UMDMResult(1.0e10, umddevice.UMD_W)
                PInputMax = umddevice.UMDMResult(0.0, umddevice.UMD_W)
                InCounter = 0
                for t in tees:
                    for i in range(len(pref[f][t][p])):
                        pr = pref[f][t][p][i]['value'].convert(umddevice.UMD_W)
                        pr = pr.mag()
                        PMaxRec = umdutil.MRmax(PMaxRec, pr)        
                        PAveRec += pr
                        RecCounter += 1
                        pf = pref[f][t][p][i]['pfwd'].convert(umddevice.UMD_W)
                        pf = pf.mag()
                        PInputMin = umdutil.MRmin(PInputMin, pf) 
                        PInputMax = umdutil.MRmax(PInputMax, pf) 
                        PInput += pf
                        InCounter += 1
                PAveRec /= RecCounter
                PMaxRecL[p]=PMaxRec
                PAveRecL[p]=PAveRec    # for each receive antenna pos: Max and Av over tuner positions
                PInput /= InCounter
                PInputVariation = PInputMax / PInputMin
                PInputAL[p]=PInput
                PInputVariationAL[p] = PInputVariation
                    
                
            self.processedData_EUTCal[description]['PMaxRec'][f]=PMaxRecL.copy()
            self.processedData_EUTCal[description]['PAveRec'][f]=PAveRecL.copy()
            self.processedData_EUTCal[description]['PInputForEField'][f]=PInputEL.copy()
            self.processedData_EUTCal[description]['PInputForRecAnt'][f]=PInputAL.copy()
            self.processedData_EUTCal[description]['PInputVarationForEField'][f]=PInputVariationEL.copy()
            self.processedData_EUTCal[description]['PInputVarationForRecAnt'][f]=PInputVariationAL.copy()
            self.processedData_EUTCal[description]['EMax'][f]=EMaxL.copy()

            # calc CCF and CCF_from_PMaxRec
            CCF_from_PMaxRec = zeroPR
            for pos,Pmax in PMaxRecL.items():            
                CCF_from_PMaxRec += Pmax/PInputAL[pos]
            CCF_from_PMaxRec /= len(PMaxRecL.keys())
            CCF = zeroPR
            for pos,Pav in PAveRecL.items():            
                CCF += Pav/PInputAL[pos]
            CCF /= len(PAveRecL.keys())
            self.processedData_EUTCal[description]['CCF_from_PMaxRec'][f] = CCF_from_PMaxRec
            self.processedData_EUTCal[description]['CCF'][f] = CCF

            if npees > 0:
                Avxyz = umddevice.stdVectorUMDMResult()
                for k in range(3):
                    Avxyz.append(zeroVmoversqrtW)
                self.processedData_EUTCal[description]['Enorm'][f]={}
                for pos,Em in EMaxL.items():
                    pin = self.processedData_EUTCal[description]['PInputForEField'][f][pos] 
                    v = pin.get_v()
                    sqrtv=math.sqrt(v)
                    u = pin.get_u()
                    l = pin.get_l()
                    sqrtPInput = umddevice.UMDMResult(sqrtv, sqrtv+(u-l)/(4.0*sqrtv), sqrtv-(u-l)/(4.0*sqrtv), umddevice.UMD_sqrtW)
                    en = umddevice.stdVectorUMDMResult()
                    for k in range(len(Em)):
                        en.append(Em[k]/sqrtPInput)
                        Avxyz[k] += en[k]
                    self.processedData_EUTCal[description]['Enorm'][f][pos]=en
                Av24 = zeroVmoversqrtW
                for k in range(3):
                    Avxyz[k] /= len(EMaxL.keys())
                    Av24 += Avxyz[k]
                Av24 /= 3.0
                self.processedData_EUTCal[description]['EnormAveXYZ'][f]=Avxyz
                self.processedData_EUTCal[description]['EnormAve'][f]=Av24
                enorm = self.processedData_EUTCal[description]['Enorm'][f]
                Sxyz = umddevice.stdVectorUMDMResult()
                list24 = []
                for k in range(3):
                    lst = [enorm[p][k] for p in enorm.keys()]
                    list24+=lst
                    S = umdutil.CalcSigma(lst, Avxyz[k])
                    try:
                        Sxyz.append(S)
                    except:
                        umdutil.LogError (self.messenger)            
                try:
                    S24 = umdutil.CalcSigma(list24, Av24)
                except:
                    S24 = None
                
                self.processedData_EUTCal[description]['SigmaXYZ'][f]=Sxyz
                self.processedData_EUTCal[description]['Sigma24'][f]=S24
                SdBxyz = umddevice.stdVectorUMDMResult()
                for k in range(3):
                    try:
                        SdBxyz.append(((Sxyz[k]+Avxyz[k])/Avxyz[k]).convert(umddevice.UMD_dB))
                    except:
                        umdutil.LogError (self.messenger)            
                try:
                    SdB24 = ((S24+Av24)/Av24).convert(umddevice.UMD_dB)
                except:
                    SdB24 = None
                self.processedData_EUTCal[description]['SigmaXYZ_dB'][f] = SdBxyz
                self.processedData_EUTCal[description]['Sigma24_dB'][f] = SdB24
            else:  # no efield data available
                self.processedData_EUTCal[description]['Enorm'][f]=None
                self.processedData_EUTCal[description]['EnormAveXYZ'][f]=None
                self.processedData_EUTCal[description]['EnormAve'][f]=None
                self.processedData_EUTCal[description]['SigmaXYZ'][f]=None
                self.processedData_EUTCal[description]['Sigma24'][f]=None
                self.processedData_EUTCal[description]['SigmaXYZ_dB'][f] = None
                self.processedData_EUTCal[description]['Sigma24_dB'][f] = None
                

        acf = self.processedData_MainCal[calibration]['ACF']
        il = self.processedData_MainCal[calibration]['IL']
        ccf = self.processedData_EUTCal[description]['CCF']
        ccfPMax = self.processedData_EUTCal[description]['CCF_from_PMaxRec']
        self.processedData_EUTCal[description]['CLF'] = self.__CalcLoading(ccf, acf, freqs,'linxliny')             
        self.processedData_EUTCal[description]['CLF_from_PMaxRec'] = self.__CalcLoading(ccfPMax, il, freqs,'linxliny')             
        self.messenger(umdutil.tstamp()+" End of evaluation of EUT calibration", [])
        return 0

    def CalculateLoading_MainCal (self, empty_cal='empty', loaded_cal='loaded', freqs=None, interpolation='linxliny'):
        """Calculate the chamber loading from processed data (MainCal)
        If freqs is None, freqs are taken fron first ACF and second ACF is interpolated
        Else both are interpolated
        """
        if (not self.processedData_MainCal.has_key(empty_cal))\
           or (not self.processedData_MainCal.has_key(loaded_cal)):
            # one of the keys not present
            return -1
        des = str(empty_cal+','+loaded_cal)
        acf1=self.processedData_MainCal[empty_cal]['ACF']
        acf2=self.processedData_MainCal[loaded_cal]['ACF']
        self.processedData_MainCal.setdefault(des, {})
        self.processedData_MainCal[des]['Loading']=self.__CalcLoading(acf1,acf2,freqs,interpolation)
        return 0

    def CalculateLoading_EUTCal (self, empty_cal='empty', eut_cal='EUT', freqs=None, interpolation='linxliny'):
        """Calculate the chamber loading from processed data (MainCal)
        If freqs is None, freqs are taken fron first ACF and second ACF is interpolated
        Else both are interpolated
        """
        if (not self.processedData_MainCal.has_key(empty_cal))\
           or (not self.processedData_EUTCal.has_key(eut_cal)):
            # one of the keys not present
            return -1
        des = str(empty_cal+','+eut_cal)
        acf1=self.processedData_MainCal[empty_cal]['ACF']
        acf2=self.processedData_EUTCal[eut_cal]['CCF']
        self.processedData_EUTCal.setdefault(des, {})
        self.processedData_EUTCal[des]['Loading']=self.__CalcLoading(acf1,acf2,freqs,interpolation)
        return 0

    def __CalcLoading(self, acf1, acf2, freqs, interpolation):
        """Calculate the chamber loading from processed data
        If freqs is None, freqs are taken fron first ACF and second ACF is interpolated
        Else both are interpolated
        """
        if freqs is None:
            freqs = acf1.keys()
        ldict={}
        cf1 = umdutil.MResult_Interpol(acf1,interpolation)
        cf2 = umdutil.MResult_Interpol(acf2,interpolation)
        for f in freqs:
            loading = cf1(f)/cf2(f)            
            ldict[f]=loading
        return ldict

class stdImmunityKernel:
    def __init__(self, field, tp, messenger, UIHandler, locals, dwell, keylist='sS'):
        self.field=field
        self.tp=tp
        self.messenger=messenger
        self.UIHandler=UIHandler
        self.callerlocals=locals
        try:
            self.in_as=self.callerlocals['in_as']
        except KeyError:
            self.in_as={}
        self._testplan = self._makeTestPlan()
        self.dwell = dwell
        self.keylist = keylist
    def _makeTestPlan(self):
        ret = []
        freqs = self.tp.keys()
        freqs.sort()
        for f in freqs:
            has_f=self.in_as.has_key(f)
            if has_f:
                continue
            ret.append(('LoopMarker', '', {}))
            ret.append(('freq', '', {'freq': f}))
            ret.append(('efield', '', {'efield': self.field}))
            for t in self.tp[f]:
                ret.append(('tuner', '', {'tunerpos': t[:]}))
                ret.append(('rf', '', {'rfon': 1}))
                ret.append(('measure', '', {}))
                ret.append(('eut', None, None)) 
                ret.append(('rf', '', {'rfon': 0}))
            ret.append(('autosave', '', {}))
        ret.append(('finished', '', {}))
        ret.reverse()
        return ret
        
    def test (self, stat):
        if stat == 'AmplifierProtectionError':
            # last command failed due to Amplifier Protection
            # look for 'LoopMarker' and continue there
            while True:
                cmd = self._testplan.pop()
                if cmd[0] in ('LoopMarker', 'finished'): 
                    break
        else:
            cmd = self._testplan.pop()
            
        #overread LoopMarker        
        while cmd[0]=='LoopMarker':
            cmd = self._testplan.pop()
                
        if cmd[0] == 'eut':
            start = time.time()
            intervall = 0.01
            while (time.time()-start < self.dwell):
                key = umdutil.anykeyevent()
                if (0<=key<=255) and chr(key) in self.keylist:
                    cmd=('eut', 'User event.', {'eutstatus': 'Marked by user'})
                    break
                
                time.sleep(intervall)
                cmd=('eut', '', {'eutstatus': 'OK'})
        return cmd
                            
class TestField:
    def __init__(self, instance, maincal='empty', eutcal=None):
        self.fail=False
        if not instance.processedData_MainCal.has_key(maincal):
            self.fail=True
        if eutcal and not instance.rawData_EUTCal.has_key(eutcal):
            self.fail=True
        self.Enorm=umdutil.MResult_Interpol(instance.processedData_MainCal[maincal]['EnormAve'].copy())
        try:
            self.clf=umdutil.MResult_Interpol(instance.processedData_EUTCal[eutcal]['CLF'].copy())
        except:
            self.clf=(lambda _f: umddevice.UMDMResult(1,umddevice.UMD_powerratio))
        
    def __call__(self, f=None, power=None):
        if f is None:
            return None
        if power is None:
            return None
        try:
            power = power.convert(umddevice.UMD_W)
        except:
            power = umddevice.UMDMResult(power,umddevice.UMD_W)
        power = power.mag()
        power.unit=umddevice.UMD_dimensionless   # sqrt(W) is not implemented yet
        enorm = self.Enorm(f).convert(umddevice.UMD_VovermoversqrtW)
        enorm.unit=umddevice.UMD_dimensionless
        clf=self.clf(f).convert(umddevice.UMD_powerratio)
        #print power
        #print clf
        #print enorm
        etest2 = power * clf * enorm * enorm                    
        etest_v = math.sqrt(etest2.get_v())
        dp = 0.5*(power.get_u()-power.get_l())
        dc = 0.5*(clf.get_u()-clf.get_l())
        de = 0.5*(enorm.get_u()-enorm.get_l())
        # TODO: Check for ZeroDivision Error
        try:
            det = math.sqrt((0.5*math.sqrt(clf.get_v()/power.get_v())*enorm.get_v()*dp)**2
                        +(0.5*math.sqrt(power.get_v()/clf.get_v())*enorm.get_v()*dc)**2
                        +(math.sqrt(power.get_v()*clf.get_v()*de))**2)
        except ZeroDivisionError:
            det = 0.0
        etest_u=etest_v+det
        etest_l=etest_v-det
        return umddevice.UMDMResult(etest_v,etest_u,etest_l,umddevice.UMD_Voverm)

class TestPower:
    def __init__(self, instance, maincal='empty', eutcal=None):
        self.fail=False
        self.instance=instance
        if not instance.processedData_MainCal.has_key(maincal):
            self.fail=True
        if eutcal and not instance.rawData_EUTCal.has_key(eutcal):
            self.fail=True
        self.Enorm=umdutil.MResult_Interpol(instance.processedData_MainCal[maincal]['EnormAve'].copy())
        try:
            self.clf=umdutil.MResult_Interpol(instance.processedData_EUTCal[eutcal]['CLF'].copy())
        except:
            self.clf=(lambda _f: umddevice.UMDMResult(1,umddevice.UMD_powerratio)) 
        
    def __call__(self, f=None, etest=None):
        if f is None:
            return None
        if etest is None:
            return None
        try:
            etest = etest()
        except TypeError:
            pass
        try:
            etest = etest.convert(umddevice.UMD_Voverm)
        except AttributeError:
            etest = umddevice.UMDMResult(etest,umddevice.UMD_Voverm)
        #etest.unit=umddevice.UMD_dimensionless   # (V/m)**2 is not implemented yet
        enorm = self.Enorm(f).convert(umddevice.UMD_VovermoversqrtW)
        clf=self.clf(f).convert(umddevice.UMD_powerratio)
        #self.instance.messenger("DEBUG TestPower: f: %e, etest: %r, enorm: %r, clf: %r"%(f,etest,enorm,clf), [])
        enorm.unit=umddevice.UMD_dimensionless
        E = etest.get_v()
        e = enorm.get_v()
        c = clf.get_v()
        power_v = (E/e)**2 / c

        dE = 0.5*(etest.get_u()-etest.get_l())
        dc = 0.5*(clf.get_u()-clf.get_l())
        de = 0.5*(enorm.get_u()-enorm.get_l())
        
        dp = E/(e*c) * math.sqrt((2*dE/e)**2
                               + (2*E*de/(e*e))**2
                               + (E*dc/(e*math.sqrt(c)))**2)            
        power = umddevice.UMDMResult(power_v,power_v+dp,power_v-dp,umddevice.UMD_W)
        #self.instance.messenger("DEBUG TestPower: f: %e, power: %r"%(f,power), [])
        return power
