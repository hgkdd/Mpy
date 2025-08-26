# -*- coding: utf-8 -*-
"""
MSC: class for MSC measurements

Author: Dr. Hans Georg Krauthaeuser, hgk@ieee.org

Copyright (c) 2001-2022 All rights reserved
"""

import os
import pprint
import shutil
import sys
import time

# import rpy
import numpy
import scipy
import scipy.interpolate
import scipy.optimize
import scipy.stats
from scuq.quantities import Quantity
from scuq.si import WATT, METER
from scuq.ucomponents import Context

from mpylab.env import Measure
from mpylab.tools import util, mgraph, spacing, distributions, correlation
from mpylab.tools.aunits import POWERRATIO, EFIELD, EFIELDPNORM

# from win32com.client import Dispatch
# import sys

# def toSVG(data, filename):
#    graphViz=Dispatch("WINGRAPHVIZ.dot")
#    f=open(filename,'r')
#    data = f.read()
#    f.close()
#    img=graphViz.toSVG(data)
#    f=open(str(filename),'w')
#    f.write(img)
#    f.close()

AmplifierProtectionError = Measure.AmplifierProtectionError


def cmp(a, b):
    return (a > b) - (a < b)


def test_for_rayleigh(ees):
    n_ees = len(ees)
    hist, bins = numpy.histogram(ees)
    low_range = bins.min()
    binsize = (bins.max() - low_range) / (bins.size - 1)
    # hist_area = sum(hist) * binsize
    # nhist = [_h / hist_area for _h in hist]
    e_cdf = distributions.ECDF(ees)
    loc, scale = scipy.stats.rayleigh.fit(ees, floc=0)
    ray_fit = scipy.stats.rayleigh(loc=loc, scale=scale)
    cdf_fit = ray_fit.cdf(ees)
    # calc estimates for chi2-test
    estimates = []
    _l = low_range
    for _h in bins[1:]:
        estimates.append(ray_fit.cdf(_h) - ray_fit.cdf(_l))
        _l = _h
    factor = sum(hist) / sum(estimates)
    estimates = [_e * factor for _e in estimates]
    cs, p_cs = scipy.stats.chisquare(hist, f_exp=estimates)
    # print(p_cs)
    ks, p_ks = scipy.stats.ks_2samp(e_cdf(ees), cdf_fit)
    # print(p_ks)
    return hist, bins, e_cdf, ray_fit, p_cs, p_ks


class MSC(Measure.Measure):
    """
    A class for Mode Stirred Chamber measurements

    The following main functions are defined:
    Measure_MainCal -> Performs a msc main calibration according to IEC 61000-4-21
    Measure_Autocorrelation -> Performs a msc autocorrelation measurement
    Measure_EUTCal -> Performs a msc EUT calibration according to IEC 61000-4-21
    Measure_Immunity -> Performs a msc immunity measurement according to IEC 61000-4-21
    getMaxE -> Determine maximum E-field strength
    Measure_Emission -> Performs a msc emission measurement according to IEC 61000-4-21
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
        self.std_Standard = 'IEC 61000-4-21'

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
        field[f][repr(t)].setdefault(p, [])
        field[f][repr(t)][p].append({'value': value, 'pfwd': pf, 'pbwd': pb})
        if dct is not None:
            field[f][repr(t)][p][-1].update(dct)
        return field

    def __addLoggerBlock(self, parent, key, comment, val, parameter):
        """
        Helper function to add a block for the logger function(s).
        parent must be a dict
        key is used as key
        parent[key] results in a dict like {'comment' comment, 'value': val, 'parameter': parameter}
        parameter should be a dict of the same form as parent or an empty dict
        """
        parent[key] = {}
        parent[key]['comment'] = comment
        parent[key]['value'] = val
        parent[key]['parameter'] = parameter

    def Measure_MainCal(self,
                        description="empty",
                        dotfile='msc-calibration.dot',
                        delay=1.0,
                        LUF=250e6,
                        FStart=150e6,
                        FStop=1e9,
                        InputLevel=None,
                        leveler=None,
                        leveler_par=None,
                        ftab=None,
                        nftab=None,
                        ntuntab=None,
                        tofftab=None,
                        nprbpostab=None,
                        nrefantpostab=None,
                        SearchPaths=None,
                        names=None):
        """Performs a msc main calibration according to IEC 61000-4-21
        """
        if names is None:
            names = {'sg': 'sg',
                     'a1': 'a1',
                     'a2': 'a2',
                     'ant': 'ant',
                     'pmfwd': 'pm1',
                     'pmbwd': 'pm2',
                     'fp': ['fp1', 'fp2', 'fp3', 'fp4', 'fp5', 'fp6', 'fp7', 'fp8'],
                     'tuner': ['tuner1'],
                     'refant': ['refant1'],
                     'pmref': ['pmref1']}
        if nrefantpostab is None:
            nrefantpostab = [8, 8, 8, 8, 8]
        if nprbpostab is None:
            nprbpostab = [8, 8, 8, 8, 8]
        if tofftab is None:
            tofftab = [[7, 14, 28, 28, 28]]
        if ntuntab is None:
            ntuntab = [[50, 18, 12, 12, 12]]
        if nftab is None:
            nftab = [20, 15, 10, 20, 20]
        if ftab is None:
            ftab = [1, 3, 6, 10, 100, 1000]
        ctx = Context()
        self.PreUserEvent()
        ftab = LUF * numpy.array(ftab)

        if self.autosave:
            self.messenger(util.tstamp() + " Resume main calibration measurement from autosave...", [])
        else:
            self.messenger(util.tstamp() + " Start new main calibration measurement...", [])

        self.rawData_MainCal.setdefault(description, {})

        # number of probes, ref-antenna and tuners
        nprb = len(names['fp'])
        nrefant = min(len(names['refant']), len(names['pmref']))
        ntuner = min(len(ntuntab), len(tofftab), len(names['tuner']))

        mg = mgraph.MGraph(dotfile, themap=names.copy(), SearchPaths=SearchPaths)

        if leveler is None:
            self.leveler = mgraph.Leveler
        else:
            self.leveler = leveler
        if leveler_par is None:
            self.leveler_par = {'mg': mg,
                                'actor': mg.name.sg,
                                'output': mg.name.ant,
                                'lpoint': mg.name.ant,
                                'observer': mg.name.pmfwd,
                                'pin': None,
                                'datafunc': None,
                                'min_actor': None}
        else:
            self.leveler_par = leveler_par
        if InputLevel is None:
            self.InputLevel = Quantity(WATT, 1e-3)  # 1 mW default
        else:
            self.InputLevel = InputLevel

        leveler_inst = None

        ddict = mg.CreateDevices()  # ddict -> instrumentation
        # for k,v in ddict.items():
        #    globals()[k] = v

        self.messenger(util.tstamp() + " Init devices...", [])
        err = mg.Init_Devices()
        if err:
            self.messenger(util.tstamp() + " ...faild with err %d" % (err), [])
            return err
        try:
            self.messenger(util.tstamp() + " ...done", [])
            stat = mg.RFOff_Devices()
            self.messenger(util.tstamp() + " Zero devices...", [])
            stat = mg.Zero_Devices()
            self.messenger(util.tstamp() + " ...done", [])

            # list of frequencies
            freqs = spacing.logspaceTab(FStart, FStop, ftab, nftab, endpoint=True)

            PrbPosCounter = {}
            RefAntPosCounter = {}
            # calculate numbrer of required probe positions for each freq
            positions = {}
            hasDupes = []
            for f in freqs:
                findex = util.getIndex(f, ftab) - 1
                # print f, findex
                PrbPosCounter[f] = nprbpostab[findex]  # number of positions to measure for this freq
                RefAntPosCounter[f] = nrefantpostab[findex]  # number of positions (ref ant)
                if findex in positions:
                    continue
                positions[findex] = []
                for tunerindex in range(ntuner):
                    positions[findex].append([tunerposindex * tofftab[tunerindex][findex] for tunerposindex in
                                              range(ntuntab[tunerindex][findex])])
                positions[findex] = util.combinations(positions[findex])
                # collection of all tuner positions
                hasDupes += positions[findex]
            # remove duplicate tuner pos entries...
            noDupes = []
            [noDupes.append(_i) for _i in hasDupes if not noDupes.count(_i)]
            alltpos = noDupes  # unique and sorted
            # determine max number of probe pos
            prbposleft = maxnprbpos = max(nprbpostab)
            # determine max number of ref ant pos
            refantposleft = maxnrefantpos = max(nrefantpostab)

            # set up efields, ...
            efields = {}
            prefant = {}
            noise = {}
            etaTx = {}
            etaRx = {}
            # for autosave: autosave_info
            as_i = {'prbposleft': prbposleft,  # remaining probe positions
                    'refantposleft': refantposleft,  # remaining ref ant positions
                    'LastMeasuredFreq': None,  # last freq measure before auto save
                    'LastMeasuredTpos': None}  # last tuner position measured before auto save
            # restore from auto save
            if self.autosave:  # self.autosave is set True in Measure.do_autosave, i.e. instance was created from autosave pickle file
                # copy raw data
                efields = self.rawData_MainCal[description]['efield'].copy()
                prefant = self.rawData_MainCal[description]['pref'].copy()
                noise = self.rawData_MainCal[description]['noise'].copy()
                # autosave info record
                as_i = self.autosave_info.copy()
                # number of probe positions and ref ant positions not yet measured
                prbposleft = as_i['prbposleft']
                refantposleft = as_i['refantposleft']
                # if 'PrbPosCounter' in as_i:
                PrbPosCounter = as_i['PrbPosCounter'].copy()
                # if 'RefAntPosCounter' in as_i:
                RefAntPosCounter = as_i['RefAntPosCounter'].copy()

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
                msg = ("List of probe positions from autosave file:\n"
                       "%s\n"
                       "List of ref antenna positions from autosave file:\n"
                       "%s\n" % (list(range(1, maxnprbpos - max(0, prbposleft) + 1)),
                                 list(range(1, maxnrefantpos - max(0, refantposleft) + 1))))
                but = []
                self.messenger(msg, but)
            self.autosave = False  # reset auto save flag
            ##################################################
            # for all probe/refant positions
            ##################################################
            while prbposleft > 0 or refantposleft > 0:  # positions are count down
                stat = mg.RFOff_Devices()
                p = maxnprbpos - prbposleft + 1  # current probe pos
                pra = maxnrefantpos - refantposleft + 1  # current refant pos
                msg = ("Position E field probes (%d to %d) and reference antenna (%d to %d) ...\n"
                       "Are you ready to start the measurement?\n\n"
                       "Start: start measurement.\n"
                       "Quit: perform autosave and quit measurement." % (p, p + nprb - 1, pra, pra + nrefant - 1))
                but = ["Start", "Quit"]
                answer = self.messenger(msg, but)
                if answer == but.index('Quit'):
                    self.messenger(util.tstamp() + " measurement terminated by user.", [])
                    # perform autosave
                    self.autosave_info = {'prbposleft': prbposleft,
                                          'refantposleft': refantposleft,
                                          'LastMeasuredFreq': freqs[-1],
                                          'LastMeasuredTpos': alltpos[-1],
                                          'PrbPosCounter': PrbPosCounter.copy(),
                                          'RefAntPosCounter': RefAntPosCounter.copy()}
                    if self.asname:
                        self.messenger(util.tstamp() + " autosave ...", [])
                        basename, extension = os.path.splitext(self.asname)
                        try:
                            # save the autosave file
                            shutil.copyfile(self.asname,
                                            "%s-%s.p" % (basename, time.strftime("%Y-%m-%d_%H_%M_%S", time.gmtime())))
                        except IOError:  # no src or dst not writeble (should not happen)
                            pass  # ignore
                        self.do_autosave()
                        self.messenger(util.tstamp() + " ... done", [])
                    raise UserWarning  # to reach finally statement
                ##############################################
                # loop tuner positions
                ################################################
                for t in alltpos:
                    ast = as_i['LastMeasuredTpos']
                    if ast:  # True: instance from auto save pickle file
                        if alltpos[-1] == ast:  # don't remember why this is useful ?????
                            pass  # special case for last tuner position ?????
                        elif alltpos.index(t) < alltpos.index(ast):  # tuner pos already measured
                            continue  # next t-pos
                    as_i['LastMeasuredTpos'] = None  # reset flag
                    self.messenger(util.tstamp() + " Tuner position %r" % t, [])
                    # position tuners
                    self.messenger(util.tstamp() + " Move tuner(s)...", [])
                    for i, tname in enumerate(names['tuner']):
                        TPos = t[i]
                        IsPos = ddict[tname].Goto(TPos)
                    self.messenger(util.tstamp() + " ...done", [])
                    ########################################################
                    # loop freqs
                    ########################################################
                    for f in freqs:
                        asf = as_i['LastMeasuredFreq']
                        if asf:
                            if (freqs[-1] == asf) and not (alltpos[-1] == ast):
                                pass  # last freq measured but not for last t-pos
                            elif (freqs[-1] == asf) and (alltpos[-1] == ast):  # last freq for last t-pos measured
                                for fr in freqs:  # count down Pos Counters
                                    RefAntPosCounter[fr] -= nrefant
                                    PrbPosCounter[fr] -= nprb
                            elif freqs.index(f) <= freqs.index(asf):
                                continue  # f already measured -> next freq
                        as_i['LastMeasuredFreq'] = None  # reset flag
                        self.messenger(util.tstamp() + " Frequency %e Hz" % (f), [])
                        findex = util.getIndex(f, ftab) - 1
                        if t not in positions[findex]:  # pos t is not for this freq
                            self.messenger(util.tstamp() + " Skipping tuner position", [])
                            continue
                        # switch if necessary
                        # print f
                        mg.EvaluateConditions()
                        # set frequency for all devices
                        (minf, maxf) = mg.SetFreq_Devices(f)

                        # cable corrections
                        c_sg_amp = mg.get_path_correction(mg.name.sg, mg.name.a1, POWERRATIO)
                        c_sg_ant = mg.get_path_correction(mg.name.sg, mg.name.ant, POWERRATIO)
                        c_a2_pm1 = mg.get_path_correction(mg.name.a2, mg.name.pmfwd, POWERRATIO)
                        c_a2_ant = mg.get_path_correction(mg.name.a2, mg.name.ant, POWERRATIO)
                        c_ant_pm2 = mg.get_path_correction(mg.name.ant, mg.name.pmbwd, POWERRATIO)
                        c_refant_pmref = []
                        for i in range(nrefant):
                            c_refant_pmref.append(
                                mg.get_path_correction(names['refant'][i], names['pmref'][i], POWERRATIO))
                        c_fp = 1.0
                        if f not in etaTx:
                            eta = mg.GetAntennaEfficiency(mg.name.ant)
                            self.messenger(util.tstamp() + " Eta_Tx for f = %e Hz is %s" % (f, str(eta)), [])
                            etaTx = self.__insert_it(etaTx, eta, None, None, f, t, 0)
                        if f not in etaRx:
                            for i in range(nrefant):
                                eta = mg.GetAntennaEfficiency(names['refant'][i])
                                self.messenger(util.tstamp() + " Eta_Rx(%d) for f = %e Hz is %s" % (i, f, str(eta)), [])
                                etaRx = self.__insert_it(etaRx, eta, None, None, f, t, i)

                        # ALL measurement start here
                        block = {}
                        nbresult = {}  # dict for NB-Read results
                        pmreflist = []
                        nblist = [mg.name.pmfwd, mg.name.pmbwd]  # list of devices for NB Reading
                        # check for fwd pm
                        if mg.nodes[mg.name.pmfwd]['inst']:
                            NoPmFwd = False  # ok
                        else:  # no fwd pm
                            msg = util.tstamp() + " WARNING: No fwd power meter. Signal generator output is used instead!"
                            answer = self.messenger(msg, [])
                            NoPmFwd = True

                        for i in range(nrefant):
                            if RefAntPosCounter[f] < i + 1:
                                break
                            nblist.append(names['pmref'][i])
                            pmreflist.append(names['pmref'][i])
                        for i in range(nprb):
                            if PrbPosCounter[f] < i + 1:
                                break
                            nblist.append(names['fp'][i])

                        # noise floor measurement..
                        if f not in noise:
                            self.messenger(util.tstamp() + " Starting noise floor measurement for f = %e Hz ..." % (f),
                                           [])
                            mg.NBTrigger(pmreflist)
                            # serial poll all devices in list
                            olddevs = []
                            while 1:
                                self.__HandleUserInterrupt(locals())
                                nbresult = mg.NBRead(pmreflist, nbresult)
                                new_devs = [i for i in list(nbresult.keys()) if i not in olddevs]
                                olddevs = list(nbresult.keys())[:]
                                if len(new_devs):
                                    self.messenger(util.tstamp() + " Got answer from: " + str(new_devs), [])
                                if len(nbresult) == len(pmreflist):
                                    break
                            for i in range(nrefant):
                                n = names['pmref'][i]
                                if n in nbresult:
                                    # add path correction here
                                    PRef = nbresult[n]
                                    nn = 'Noise ' + n
                                    self.__addLoggerBlock(block, nn,
                                                          'Noise reading of the receive antenna power meter for position %d' % i,
                                                          nbresult[n], {})
                                    self.__addLoggerBlock(block[nn]['parameter'], 'freq', 'the frequency [Hz]', f, {})
                                    self.__addLoggerBlock(block, 'c_refant_pmref' + str(i),
                                                          'Correction from ref antenna feed to ref power meter',
                                                          c_refant_pmref[i], {})
                                    self.__addLoggerBlock(block['c_refant_pmref' + str(i)]['parameter'], 'freq',
                                                          'the frequency [Hz]', f, {})
                                    PRef = (abs((PRef / c_refant_pmref[i]).reduce_to(WATT))).eval()
                                    self.__addLoggerBlock(block, nn + '_corrected', 'Noise: Pref/c_refant_pmref', PRef,
                                                          {})
                                    self.__addLoggerBlock(block[nn + '_corrected']['parameter'], 'freq',
                                                          'the frequency [Hz]', f, {})
                                    self.__addLoggerBlock(block[nn + '_corrected']['parameter'], 'tunerpos',
                                                          'tuner position', t, {})
                                    noise = self.__insert_it(noise, PRef, None, None, f, t, i)
                            self.messenger(util.tstamp() + " Noise floor measurement done.", [])

                        self.messenger(util.tstamp() + " RF On...", [])
                        stat = mg.RFOn_Devices()  # switch on just before measure
                        if not leveler_inst:
                            leveler_inst = self.leveler(**self.leveler_par)

                        # try:
                        level = leveler_inst.adjust_level(self.InputLevel)
                        # except AmplifierProtectionError, _e:
                        #    self.messenger(util.tstamp()+" Can not set signal generator level. Amplifier protection raised with message: %s"%_e.message, [])
                        #    raise  # re raise to reach finaly clause

                        # level2 = self.do_leveling(leveling, mg, names, locals())
                        # if level2:
                        #    level=level2

                        # wait delay seconds
                        self.messenger(util.tstamp() + " Going to sleep for %d seconds ..." % (delay), [])
                        self.wait(delay, locals(), self.__HandleUserInterrupt)
                        self.messenger(util.tstamp() + " ... back.", [])

                        # Trigger all devices in list
                        mg.NBTrigger(nblist)
                        # serial poll all devices in list
                        if NoPmFwd:
                            nbresult[mg.name.pmfwd] = level
                            nbresult[mg.name.pmbwd] = Quantity(WATT, 0.0)
                        olddevs = []
                        while 1:
                            self.__HandleUserInterrupt(locals())
                            nbresult = mg.NBRead(nblist, nbresult)
                            new_devs = [i for i in list(nbresult.keys()) if i not in olddevs]
                            olddevs = list(nbresult.keys())[:]
                            if len(new_devs):
                                self.messenger(util.tstamp() + " Got answer from: " + str(new_devs), [])
                            if len(nbresult) == len(nblist):
                                break
                        # print nbresult

                        # pfwd
                        n = mg.name.pmfwd
                        if n in nbresult:
                            PFwd = nbresult[n]
                            self.__addLoggerBlock(block, n, 'Reading of the fwd power meter', nbresult[n], {})
                            self.__addLoggerBlock(block[n]['parameter'], 'freq', 'the frequency [Hz]', f, {})
                            self.__addLoggerBlock(block[n]['parameter'], 'tunerpos', 'tuner position', t, {})
                            PFwd = (abs((PFwd * c_a2_ant).reduce_to(WATT))).eval()
                            self.__addLoggerBlock(block, 'c_a2_ant', 'Correction from amplifier output to antenna',
                                                  c_a2_ant, {})
                            self.__addLoggerBlock(block['c_a2_ant']['parameter'], 'freq', 'the frequency [Hz]', f, {})
                            self.__addLoggerBlock(block, 'c_a2_pm1',
                                                  'Correction from amplifier output to fwd power meter', c_a2_pm1, {})
                            self.__addLoggerBlock(block['c_a2_pm1']['parameter'], 'freq', 'the frequency [Hz]', f, {})
                            PFwd = (abs((PFwd / c_a2_pm1).reduce_to(WATT))).eval()
                            self.__addLoggerBlock(block, n + '_corrected', 'Pfwd*c_a2_ant/c_a2_pm1', PFwd, {})
                            self.__addLoggerBlock(block[n]['parameter'], 'freq', 'the frequency [Hz]', f, {})
                            self.__addLoggerBlock(block[n]['parameter'], 'tunerpos', 'tuner position', t, {})
                            # pbwd
                        n = mg.name.pmbwd
                        if n in nbresult:
                            PBwd = nbresult[n]
                            self.__addLoggerBlock(block, n, 'Reading of the bwd power meter', nbresult[n], {})
                            self.__addLoggerBlock(block[n]['parameter'], 'freq', 'the frequency [Hz]', f, {})
                            self.__addLoggerBlock(block[n]['parameter'], 'tunerpos', 'tuner position', t, {})
                            self.__addLoggerBlock(block, 'c_ant_pm2', 'Correction from antenna feed to bwd power meter',
                                                  c_ant_pm2, {})
                            self.__addLoggerBlock(block['c_ant_pm2']['parameter'], 'freq', 'the frequency [Hz]', f, {})
                            PBwd = (abs((PBwd / c_ant_pm2).reduce_to(WATT))).eval()
                            self.__addLoggerBlock(block, n + '_corrected', 'Pbwd/c_ant_pm2', PBwd, {})
                            self.__addLoggerBlock(block[n]['parameter'], 'freq', 'the frequency [Hz]', f, {})
                            self.__addLoggerBlock(block[n]['parameter'], 'tunerpos', 'tuner position', t, {})

                            # ref-ant
                        for i in range(nrefant):
                            if RefAntPosCounter[f] < i + 1:
                                break
                            n = names['pmref'][i]
                            if n in nbresult:
                                # add path correction here
                                PRef = nbresult[n]
                                self.__addLoggerBlock(block, n,
                                                      'Reading of the receive antenna power meter for position %d' % i,
                                                      nbresult[n], {})
                                self.__addLoggerBlock(block[n]['parameter'], 'freq', 'the frequency [Hz]', f, {})
                                self.__addLoggerBlock(block[n]['parameter'], 'tunerpos', 'tuner position', t, {})
                                self.__addLoggerBlock(block, 'c_refant_pmref' + str(i),
                                                      'Correction from ref antenna feed to ref power meter',
                                                      c_refant_pmref[i], {})
                                self.__addLoggerBlock(block['c_refant_pmref' + str(i)]['parameter'], 'freq',
                                                      'the frequency [Hz]', f, {})
                                PRef = (abs((PRef / c_refant_pmref[i]).reduce_to(WATT))).eval()
                                prefant = self.__insert_it(prefant, PRef, PFwd, PBwd, f, t, pra + i - 1)
                                self.__addLoggerBlock(block, n + '_corrected', 'Pref/c_refant_pmref', PRef, {})
                                self.__addLoggerBlock(block[n]['parameter'], 'freq', 'the frequency [Hz]', f, {})
                                self.__addLoggerBlock(block[n]['parameter'], 'tunerpos', 'tuner position', t, {})

                                # e-field probes
                        # read field probes
                        for i in range(nprb):
                            if PrbPosCounter[f] < i + 1:
                                break
                            n = names['fp'][i]
                            if n in nbresult:
                                self.__addLoggerBlock(block, n, 'Reading of the e-field probe for position %d' % i,
                                                      nbresult[n], {})
                                self.__addLoggerBlock(block[n]['parameter'], 'freq', 'the frequency [Hz]', f, {})
                                self.__addLoggerBlock(block[n]['parameter'], 'tunerpos', 'tuner position', t, {})
                                efields = self.__insert_it(efields, [_.eval() for _ in nbresult[n]], PFwd, PBwd, f, t,
                                                           p + i - 1)
                        for log in self.logger:
                            log(block)

                        self.__HandleUserInterrupt(locals())
                        self.messenger(util.tstamp() + " RF Off...", [])
                        stat = mg.RFOff_Devices()  # switch off after measure

                        self.rawData_MainCal[description].update({'efield': efields,
                                                                  'pref': prefant,
                                                                  'noise': noise,
                                                                  'etaTx': etaTx,
                                                                  'etaRx': etaRx,
                                                                  'mg': mg})
                        self.autosave_info = {'prbposleft': prbposleft,
                                              'refantposleft': refantposleft,
                                              'LastMeasuredFreq': f,
                                              'LastMeasuredTpos': t,
                                              'PrbPosCounter': PrbPosCounter.copy(),
                                              'RefAntPosCounter': RefAntPosCounter.copy()}
                        # autosave class instance
                        if self.asname and (time.time() - self.lastautosave > self.autosave_interval):
                            self.messenger(util.tstamp() + " autosave ...", [])
                            self.do_autosave()
                            self.messenger(util.tstamp() + " ... done", [])
                        leveler_inst = None
                        # END OF f LOOP

                    # test for low battery
                    lowBatList = mg.getBatteryLow_Devices()
                    if len(lowBatList):
                        self.messenger(
                            util.tstamp() + " WARNING: Low battery status detected for: %s" % (str(lowBatList)), [])
                # END OF t LOOP
                ##                self.rawData_MainCal[description].update({'efield': efields, 'pref': prefant, 'noise': noise, 'etaTx': etaTx, 'etaRx': etaRx, 'mg': mg})
                ##                # autosave class instance
                ##                if self.asname and (time.time()-self.lastautosave > self.autosave_interval):
                ##                    self.messenger(util.tstamp()+" autosave ...", [])
                ##                    self.do_autosave()
                ##                    self.messenger(util.tstamp()+" ... done", [])
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
            leveler_inst = None

            # finally is executed if and if not an exception occur -> save exit
            self.messenger(util.tstamp() + " RF Off and Quit...", [])
            stat = mg.RFOff_Devices()
            stat = mg.Quit_Devices()
        self.messenger(util.tstamp() + " End of msc main calibration. Status: %d" % stat, [])
        self.PostUserEvent()
        return stat

    def Measure_Autocorrelation(self,
                                description="empty",
                                dotfile='testgr.dot',
                                delay=1.0,
                                SGLevel=-20,
                                leveling=None,
                                freqs=None,
                                toffsets=None,
                                ntunerpos=None,
                                SearchPaths=None,
                                names=None):
        """Performs a msc autocorrelation measurement
        """
        if names is None:
            names = {'sg': 'sg',
                     'a1': 'a1',
                     'a2': 'a2',
                     'ant': 'ant',
                     'pmfwd': 'pm1',
                     'pmbwd': 'pm2',
                     'fp': ['fp1', 'fp2', 'fp3', 'fp4', 'fp5', 'fp6', 'fp7', 'fp8'],
                     'tuner': ['tuner1']}
        if ntunerpos is None:
            ntunerpos = [360]
        if toffsets is None:
            toffsets = [1]
        self.PreUserEvent()
        if self.autosave:
            self.messenger(util.tstamp() + " Resume autocorrelation measurement from autosave...", [])
        else:
            self.messenger(util.tstamp() + " Start new autocorrelation measurement...", [])
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
        ntuner = min(len(toffsets), len(ntunerpos), len(names['tuner']))

        mg = mgraph.MGraph(dotfile, themap=names, SearchPaths=SearchPaths)
        ddict = mg.CreateDevices()
        # for k,v in ddict.items():
        #    globals()[k] = v

        self.messenger(util.tstamp() + " Init devices...", [])
        err = mg.Init_Devices()
        if err:
            self.messenger(util.tstamp() + " ...faild with err %d" % (err), [])
            return err
        try:
            self.messenger(util.tstamp() + " ...done", [])
            stat = mg.RFOff_Devices()
            self.messenger(util.tstamp() + " Zero devices...", [])
            stat = mg.Zero_Devices()
            self.messenger(util.tstamp() + " ...done", [])
            try:
                level = self.set_level(mg, SGLevel)
            except AmplifierProtectionError as _e:
                self.messenger(
                    util.tstamp() + " Can not set signal generator level. Amplifier protection raised with message: %s" % _e.message,
                    [])
                raise  # re raise to reach finaly clause
            if freqs is None:
                self.messenger(util.tstamp() + " msc autocorrelation measurment terminated. No frequencies given.", [])
                raise UserWarning  # to reach finally statement

            positions = []
            for tunerindex in range(ntuner):
                positions.append(
                    [tunerposindex * toffsets[tunerindex] for tunerposindex in range(ntunerpos[tunerindex])])
            positions = util.combinations(positions)
            alltpos = positions  # unique and sorted
            # set up efields, ...
            efields = {}
            if self.autosave:
                efields = self.rawData_AutoCorr[description]['efield'].copy()
                tlen = 1e300
                for f in list(efields.keys()):
                    tees = list(efields[f].keys())
                    if len(tees) < tlen:
                        tlen = len(tees)
                        tf = f
                try:
                    tees = list(efields[tf].keys())
                except AttributeError:
                    tees = []
                for t in tees:
                    try:
                        alltpos.remove(eval(t))
                    except ValueError:
                        util.LogError(self.messenger)
                msg = "List of tuner positions from autosave file:\n%s\n" % (str(tees))
                but = []
                self.messenger(msg, but)
            self.autosave = False

            stat = mg.RFOff_Devices()
            msg = """Are you ready to start the measurement?\n\nStart: start measurement.\nQuit: quit measurement."""
            but = ["Start", "Quit"]
            answer = self.messenger(msg, but)
            if answer == but.index('Quit'):
                self.messenger(util.tstamp() + " measurement terminated by user.", [])
                raise UserWarning  # to reach finally statement
            # loop tuner positions
            for t in alltpos:
                self.messenger(util.tstamp() + " Tuner position %s" % (repr(t)), [])
                # position tuners
                self.messenger(util.tstamp() + " Move tuner(s)...", [])
                for i in range(ntuner):
                    TPos = t[i]
                    IsPos = ddict[names['tuner'][i]].Goto(TPos)
                self.messenger(util.tstamp() + " ...done", [])
                # loop freqs
                for f in freqs:
                    self.messenger(util.tstamp() + " Frequency %e Hz" % (f), [])
                    # switch if necessary
                    mg.EvaluateConditions()
                    # set frequency for all devices
                    (minf, maxf) = mg.SetFreq_Devices(f)
                    # cable corrections
                    c_sg_amp = mg.get_path_correction(names['sg'], names['a1'], POWERRATIO)
                    c_sg_ant = mg.get_path_correction(names['sg'], names['ant'], POWERRATIO)
                    c_a2_pm1 = mg.get_path_correction(names['a2'], names['pmfwd'], POWERRATIO)
                    c_a2_ant = mg.get_path_correction(names['a2'], names['ant'], POWERRATIO)
                    c_ant_pm2 = mg.get_path_correction(names['ant'], names['pmbwd'], POWERRATIO)
                    c_fp = 1.0

                    # ALL measurement start here
                    block = {}
                    nbresult = {}  # dict for NB-Read results
                    nblist = [names['pmfwd'], names['pmbwd']]  # list of devices for NB Reading
                    # check for fwd pm
                    if mg.nodes[names['pmfwd']]['inst']:
                        NoPmFwd = False  # ok
                    else:  # no fwd pm
                        msg = util.tstamp() + " WARNING: No fwd power meter. Signal generator output is used instead!"
                        answer = self.messenger(msg, [])
                        NoPmFwd = True

                    for i in range(nprb):
                        nblist.append(names['fp'][i])

                    self.messenger(util.tstamp() + " RF On...", [])
                    stat = mg.RFOn_Devices()  # switch on just before measure

                    level2 = self.do_leveling(leveling, mg, names, locals())
                    if level2:
                        level = level2

                    # wait delay seconds
                    self.messenger(util.tstamp() + " Going to sleep for %d seconds ..." % (delay), [])
                    self.wait(delay, locals(), self.__HandleUserInterrupt)
                    self.messenger(util.tstamp() + " ... back.", [])

                    # Trigger all devices in list
                    mg.NBTrigger(nblist)
                    # serial poll all devices in list
                    if NoPmFwd:
                        nbresult[names['pmfwd']] = level
                        nbresult[names['pmbwd']] = Quantity(WATT, 0.0)
                    olddevs = []
                    while 1:
                        self.__HandleUserInterrupt(locals())
                        nbresult = mg.NBRead(nblist, nbresult)
                        new_devs = [i for i in list(nbresult.keys()) if i not in olddevs]
                        olddevs = list(nbresult.keys())[:]
                        if len(new_devs):
                            self.messenger(util.tstamp() + " Got answer from: " + str(new_devs), [])
                        if len(nbresult) == len(nblist):
                            break
                    # print nbresult

                    # pfwd
                    n = names['pmfwd']
                    if n in nbresult:
                        PFwd = nbresult[n]
                        self.__addLoggerBlock(block, n, 'Reading of the fwd power meter', nbresult[n], {})
                        self.__addLoggerBlock(block[n]['parameter'], 'freq', 'the frequency [Hz]', f, {})
                        self.__addLoggerBlock(block[n]['parameter'], 'tunerpos', 'tuner position', t, {})
                        PFwd = PFwd * c_a2_ant
                        self.__addLoggerBlock(block, 'c_a2_ant', 'Correction from amplifier output to antenna',
                                              c_a2_ant, {})
                        self.__addLoggerBlock(block['c_a2_ant']['parameter'], 'freq', 'the frequency [Hz]', f, {})
                        self.__addLoggerBlock(block, 'c_a2_pm1', 'Correction from amplifier output to fwd power meter',
                                              c_a2_pm1, {})
                        self.__addLoggerBlock(block['c_a2_pm1']['parameter'], 'freq', 'the frequency [Hz]', f, {})
                        PFwd = PFwd / c_a2_pm1
                        self.__addLoggerBlock(block, n + '_corrected', 'Pfwd*c_a2_ant/c_a2_pm1', PFwd, {})
                        self.__addLoggerBlock(block[n]['parameter'], 'freq', 'the frequency [Hz]', f, {})
                        self.__addLoggerBlock(block[n]['parameter'], 'tunerpos', 'tuner position', t, {})
                        # pbwd
                    n = names['pmbwd']
                    if n in nbresult:
                        PBwd = nbresult[n]
                        self.__addLoggerBlock(block, n, 'Reading of the bwd power meter', nbresult[n], {})
                        self.__addLoggerBlock(block[n]['parameter'], 'freq', 'the frequency [Hz]', f, {})
                        self.__addLoggerBlock(block[n]['parameter'], 'tunerpos', 'tuner position', t, {})
                        self.__addLoggerBlock(block, 'c_ant_pm2', 'Correction from antenna feed to bwd power meter',
                                              c_ant_pm2, {})
                        self.__addLoggerBlock(block['c_ant_pm2']['parameter'], 'freq', 'the frequency [Hz]', f, {})
                        PBwd = PBwd / c_ant_pm2
                        self.__addLoggerBlock(block, n + '_corrected', 'Pbwd/c_ant_pm2', PBwd, {})
                        self.__addLoggerBlock(block[n]['parameter'], 'freq', 'the frequency [Hz]', f, {})
                        self.__addLoggerBlock(block[n]['parameter'], 'tunerpos', 'tuner position', t, {})

                        # e-field probes
                    # read field probes
                    for i in range(nprb):
                        n = names['fp'][i]
                        if n in nbresult:
                            self.__addLoggerBlock(block, n, 'Reading of the e-field probe for position %d' % i,
                                                  nbresult[n], {})
                            self.__addLoggerBlock(block[n]['parameter'], 'freq', 'the frequency [Hz]', f, {})
                            self.__addLoggerBlock(block[n]['parameter'], 'tunerpos', 'tuner position', t, {})
                            efields = self.__insert_it(efields, nbresult[n], PFwd, PBwd, f, t, i)
                    for log in self.logger:
                        log(block)

                    self.__HandleUserInterrupt(locals())
                    self.messenger(util.tstamp() + " RF Off...", [])
                    stat = mg.RFOff_Devices()  # switch off after measure
                    # END OF f LOOP
                lowBatList = mg.getBatteryLow_Devices()
                if len(lowBatList):
                    self.messenger(util.tstamp() + " WARNING: Low battery status detected for: %s" % (str(lowBatList)),
                                   [])
                self.rawData_AutoCorr[description].update({'efield': efields, 'tpos': alltpos, 'mg': mg})
                # autosave class instance
                if self.asname and (time.time() - self.lastautosave > self.autosave_interval):
                    self.messenger(util.tstamp() + " autosave ...", [])
                    self.do_autosave()
                    self.messenger(util.tstamp() + " ... done", [])

            # END OF t LOOP

        finally:
            # finally is executed if and if not an exception occur -> save exit
            self.messenger(util.tstamp() + " RF Off and Quit...", [])
            stat = mg.RFOff_Devices()
            stat = mg.Quit_Devices()
        self.messenger(util.tstamp() + " End of msc autocorelation measurement. Status: %d" % stat, [])
        self.PostUserEvent()
        return stat

    def __HandleUserInterrupt(self, dct, ignorelist='', handler=None):
        if callable(handler):
            return handler(dct, ignorelist=ignorelist)
        else:
            return self.stdUserInterruptHandler(dct, ignorelist=ignorelist)

    def stdUserInterruptHandler(self, dct, ignorelist=''):
        key = self.UserInterruptTester()
        if key and not chr(key) in ignorelist:
            # empty key buffer
            _k = self.UserInterruptTester()
            while _k is not None:
                _k = self.UserInterruptTester()

            mg = dct['mg']
            names = dct['names']
            f = dct['f']
            t = dct['t']
            ddict = dct['ddict']
            try:
                SGLevel = dct['SGLevel']
                leveling = dct['leveling']
            except KeyError:
                hassg = False
            else:
                hassg = True
            try:
                delay = dct['delay']
            except KeyError:
                pass
            try:
                nblist = dct['nblist']
            except KeyError:
                nblist = []

            self.messenger(util.tstamp() + " RF Off...", [])
            stat = mg.RFOff_Devices()  # switch off after measure
            msg1 = """The measurement has been interrupted by the user.\nHow do you want to proceed?\n\nContinue: go ahead...\nSuspend: Quit devices, go ahead later after reinit...\nInteractive: Go to interactive mode...\nQuit: Quit measurement..."""
            but1 = ['Continue', 'Suspend', 'Interactive', 'Quit']
            answer = self.messenger(msg1, but1)
            # print answer
            if answer == but1.index('Quit'):
                self.messenger(util.tstamp() + " measurment terminated by user.", [])
                raise UserWarning  # to reach finally statement
            elif answer == but1.index('Interactive'):
                util.interactive(obj=self, banner="Press CTRL-D (Linux,MacOS) or CTRL-Z (Windows) plus Return to exit")
            elif answer == but1.index('Suspend'):
                self.messenger(util.tstamp() + " measurment suspended by user.", [])
                stat = mg.Quit_Devices()
                msg2 = """Measurement is suspended.\n\nResume: Reinit and continue\nQuit: Quit measurement..."""
                but2 = ['Resume', 'Quit']
                answer = self.messenger(msg2, but2)
                if answer == but2.index('Resume'):
                    # TODO: check if init was successful
                    self.messenger(util.tstamp() + " Init devices...", [])
                    stat = mg.Init_Devices()
                    self.messenger(util.tstamp() + " ... Init returned with stat = %d" % stat, [])
                    stat = mg.RFOff_Devices()  # switch off
                    self.messenger(util.tstamp() + " Zero devices...", [])
                    stat = mg.Zero_Devices()
                    if hassg:
                        try:
                            level = self.set_level(mg, SGLevel)
                        except AmplifierProtectionError as _e:
                            self.messenger(
                                util.tstamp() + " Can not set signal generator level. Amplifier protection raised with message: %s" % _e.message,
                                [])

                    # set frequency for all devices
                    (minf, maxf) = mg.SetFreq_Devices(f)
                    mg.EvaluateConditions()
                    # position tuners
                    if t is not None:
                        self.messenger(util.tstamp() + " Move tuner(s)...", [])
                        for i in range(len(names['tuner'])):
                            TPos = t[i]
                            IsPos = ddict[names['tuner'][i]].Goto(TPos)
                        self.messenger(util.tstamp() + " ...done", [])
                elif answer == but2.index('Quit'):
                    self.messenger(util.tstamp() + " measurment terminated by user.", [])
                    raise UserWarning  # to reach finally statement
            self.messenger(util.tstamp() + " RF On...", [])
            stat = mg.RFOn_Devices()  # switch on just before measure
            if hassg:
                level2 = self.do_leveling(leveling, mg, names, locals())
                if level2:
                    level = level2
            try:
                # wait delay seconds
                self.messenger(util.tstamp() + " Going to sleep for %d seconds ..." % delay, [])
                self.wait(delay, dct, self.__HandleUserInterrupt)
                self.messenger(util.tstamp() + " ... back.", [])
            except ValueError:
                pass
            mg.NBTrigger(nblist)

    def Measure_EUTCal(self,
                       description="EUT",
                       dotfile='msc-calibration.dot',
                       delay=1.0,
                       freqs=None,
                       SGLevel=-20,
                       leveling=None,
                       calibration='empty',
                       SearchPaths=None,
                       names=None):
        """Performs a msc EUT calibration according to IEC 61000-4-21
        """

        if names is None:
            names = {'sg': 'sg',
                     'a1': 'a1',
                     'a2': 'a2',
                     'ant': 'ant',
                     'pmfwd': 'pm1',
                     'pmbwd': 'pm2',
                     'tuner': ['tuner1'],
                     'refant': ['refant1'],
                     'pmref': ['pmref1']}
        self.PreUserEvent()
        if self.autosave:
            self.messenger(util.tstamp() + " Resume EUT calibration measurement from autosave...", [])
        else:
            self.messenger(util.tstamp() + " Start new EUT calibration measurement...", [])

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
        if 'fp' in names:  # default is no fieldprobes
            nprb = len(names['fp'])
        nrefant = min(len(names['refant']), len(names['pmref']))
        ntuner = len(names['tuner'])

        mg = mgraph.MGraph(dotfile, themap=names, SearchPaths=SearchPaths)
        ddict = mg.CreateDevices()
        # for k,v in ddict.items():
        #    globals()[k] = v

        self.messenger(util.tstamp() + " Init devices...", [])
        err = mg.Init_Devices()
        if err:
            self.messenger(util.tstamp() + " ...faild with err %d" % (err), [])
            return err
        try:
            self.messenger(util.tstamp() + " ...done", [])
            stat = mg.RFOff_Devices()
            self.messenger(util.tstamp() + " Zero devices...", [])
            stat = mg.Zero_Devices()
            self.messenger(util.tstamp() + " ...done", [])
            # set level
            try:
                level = self.set_level(mg, SGLevel)
            except AmplifierProtectionError as _e:
                self.messenger(
                    util.tstamp() + " Can not set signal generator level. Amplifier protection raised with message: %s" % _e.message,
                    [])
                raise  # re raise to reach finaly clause
            # list of frequencies
            if freqs is None:
                freqs = []

            if calibration in self.rawData_MainCal:
                alltpos = self.GetAllTPos(calibration)
            else:
                self.messenger(util.tstamp() + " Error: Calibration '%s' not found." % calibration, [])
                return -1
            # set up efields, ...
            efields = {}
            prefant = {}
            noise = {}
            etaTx = {}
            etaRx = {}

            if self.autosave:
                efields = self.rawData_EUTCal[description]['efield'].copy()
                prefant = self.rawData_EUTCal[description]['pref'].copy()
                noise = self.rawData_EUTCal[description]['noise'].copy()
                etaTx = self.rawData_EUTCal[description]['etaTx'].copy()
                etaRx = self.rawData_EUTCal[description]['etaRx'].copy()
                #
                # we have to loop over all tuner positions and
                # check if we have all freqs for this tpos
                # if complete -> remove from alltpos and add to tees
                tees = []
                for f in freqs:
                    measured_tpos = list(prefant[f].keys())
                    for t in alltpos:
                        if not self.UseTunerPos(calibration, f, t):
                            continue
                        # at this point f,t is a pair that should be measured
                        # we have to check if it was not
                        if str(t) not in measured_tpos:  # t has not been measured for this f
                            if t not in tees:  # dont append twice
                                tees.append(t)

                for t in tees:
                    try:
                        alltpos.remove(t)
                    except ValueError:
                        util.LogError(self.messenger)
                msg = "List of tuner positions from autosave file:\n%s\nRemaining tuner positions:\n%s\n" % (
                    str(tees), str(alltpos))
                but = []
                self.messenger(msg, but)
            self.autosave = False

            stat = mg.RFOff_Devices()
            msg = """Position E field probes and reference antenna...\nAre you ready to start the measurement?\n\nStart: start measurement.\nQuit: quit measurement."""
            but = ["Start", "Quit"]
            answer = self.messenger(msg, but)
            if answer == but.index('Quit'):
                self.messenger(util.tstamp() + " measurement terminated by user.", [])
                raise UserWarning  # to reach finally statement

            # loop tuner positions
            for t in alltpos:
                self.messenger(util.tstamp() + " Tuner position %s" % (repr(t)), [])
                # position tuners
                self.messenger(util.tstamp() + " Move tuner(s)...", [])
                for i in range(ntuner):
                    TPos = t[i]
                    IsPos = ddict[names['tuner'][i]].Goto(TPos)
                self.messenger(util.tstamp() + " ...done", [])
                # loop freqs
                for f in freqs:
                    self.messenger(util.tstamp() + " Frequency %e Hz" % (f), [])
                    if not self.UseTunerPos(calibration, f, t):
                        self.messenger(util.tstamp() + " Skipping tuner position", [])
                        continue
                    # switch if necessary
                    mg.EvaluateConditions()
                    # set frequency for all devices
                    (minf, maxf) = mg.SetFreq_Devices(f)
                    # cable corrections
                    c_sg_amp = mg.get_path_correction(names['sg'], names['a1'], POWERRATIO)
                    c_sg_ant = mg.get_path_correction(names['sg'], names['ant'], POWERRATIO)
                    c_a2_pm1 = mg.get_path_correction(names['a2'], names['pmfwd'], POWERRATIO)
                    c_a2_ant = mg.get_path_correction(names['a2'], names['ant'], POWERRATIO)
                    c_ant_pm2 = mg.get_path_correction(names['ant'], names['pmbwd'], POWERRATIO)
                    c_refant_pmref = []
                    for i in range(nrefant):
                        c_refant_pmref.append(mg.get_path_correction(names['refant'][i], names['pmref'][i], POWERRATIO))
                    c_fp = 1.0
                    if f not in etaTx:
                        eta = mg.GetAntennaEfficiency(names['ant'])
                        self.messenger(util.tstamp() + " Eta_Tx for f = %e Hz is %s" % (f, str(eta)), [])
                        etaTx = self.__insert_it(etaTx, eta, None, None, f, t, 0)
                    if f not in etaRx:
                        for i in range(nrefant):
                            eta = mg.GetAntennaEfficiency(names['refant'][i])
                            self.messenger(util.tstamp() + " Eta_Rx(%d) for f = %e Hz is %s" % (i, f, str(eta)), [])
                            etaRx = self.__insert_it(etaRx, eta, None, None, f, t, i)

                    # ALL measurement start here
                    block = {}
                    nbresult = {}  # dict for NB-Read results
                    pmreflist = []
                    nblist = [names['pmfwd'], names['pmbwd']]  # list of devices for NB Reading
                    # check for fwd pm
                    if mg.nodes[names['pmfwd']]['inst']:
                        NoPmFwd = False  # ok
                    else:  # no fwd pm
                        msg = util.tstamp() + " WARNING: No fwd power meter. Signal generator output is used instead!"
                        answer = self.messenger(msg, [])
                        NoPmFwd = True

                    for i in range(nrefant):
                        nblist.append(names['pmref'][i])
                        pmreflist.append(names['pmref'][i])
                    for i in range(nprb):
                        nblist.append(names['fp'][i])

                    # noise floor measurement..
                    if f not in noise:
                        self.messenger(util.tstamp() + " Starting noise floor measurement for f = %e Hz ..." % (f), [])
                        mg.NBTrigger(pmreflist)
                        # serial poll all devices in list
                        olddevs = []
                        while 1:
                            self.__HandleUserInterrupt(locals())
                            nbresult = mg.NBRead(pmreflist, nbresult)
                            new_devs = [i for i in list(nbresult.keys()) if i not in olddevs]
                            olddevs = list(nbresult.keys())[:]
                            if len(new_devs):
                                self.messenger(util.tstamp() + " Got answer from: " + str(new_devs), [])
                            if len(nbresult) == len(pmreflist):
                                break
                        for i in range(nrefant):
                            n = names['pmref'][i]
                            if n in nbresult:
                                # add path correction here
                                PRef = nbresult[n]
                                nn = 'Noise ' + n
                                self.__addLoggerBlock(block, nn,
                                                      'Noise reading of the receive antenna power meter for position %d' % i,
                                                      nbresult[n], {})
                                self.__addLoggerBlock(block[nn]['parameter'], 'freq', 'the frequency [Hz]', f, {})
                                self.__addLoggerBlock(block, 'c_refant_pmref' + str(i),
                                                      'Correction from ref antenna feed to ref power meter',
                                                      c_refant_pmref[i], {})
                                self.__addLoggerBlock(block['c_refant_pmref' + str(i)]['parameter'], 'freq',
                                                      'the frequency [Hz]', f, {})
                                PRef = PRef / c_refant_pmref[i]
                                self.__addLoggerBlock(block, nn + '_corrected', 'Noise: Pref/c_refant_pmref', PRef, {})
                                self.__addLoggerBlock(block[nn + '_corrected']['parameter'], 'freq',
                                                      'the frequency [Hz]', f, {})
                                self.__addLoggerBlock(block[nn + '_corrected']['parameter'], 'tunerpos',
                                                      'tuner position', t, {})
                                noise = self.__insert_it(noise, PRef, None, None, f, t, i)
                        self.messenger(util.tstamp() + " Noise floor measurement done.", [])

                    self.messenger(util.tstamp() + " RF On...", [])
                    stat = mg.RFOn_Devices()  # switch on just before measure

                    level2 = self.do_leveling(leveling, mg, names, locals())
                    if level2:
                        level = level2

                    # wait delay seconds
                    self.messenger(util.tstamp() + " Going to sleep for %d seconds ..." % (delay), [])
                    self.wait(delay, locals(), self.__HandleUserInterrupt)
                    self.messenger(util.tstamp() + " ... back.", [])

                    # Trigger all devices in list
                    self.messenger(util.tstamp() + " Send trigger to %s ..." % (str(nblist)), [])
                    mg.NBTrigger(nblist)
                    self.messenger(util.tstamp() + " ... back.", [])
                    # serial poll all devices in list
                    if NoPmFwd:
                        nbresult[names['pmfwd']] = level
                        nbresult[names['pmbwd']] = Quantity(WATT, 0.0)
                    olddevs = []
                    while 1:
                        self.__HandleUserInterrupt(locals())
                        nbresult = mg.NBRead(nblist, nbresult)
                        new_devs = [i for i in list(nbresult.keys()) if i not in olddevs]
                        olddevs = list(nbresult.keys())[:]
                        if len(new_devs):
                            self.messenger(util.tstamp() + " Got answer from: " + str(new_devs), [])
                        if len(nbresult) == len(nblist):
                            break
                    # print nbresult

                    # pfwd
                    n = names['pmfwd']
                    if n in nbresult:
                        PFwd = nbresult[n]
                        self.__addLoggerBlock(block, n, 'Reading of the fwd power meter', nbresult[n], {})
                        self.__addLoggerBlock(block[n]['parameter'], 'freq', 'the frequency [Hz]', f, {})
                        self.__addLoggerBlock(block[n]['parameter'], 'tunerpos', 'tuner position', t, {})
                        PFwd = PFwd * c_a2_ant
                        self.__addLoggerBlock(block, 'c_a2_ant', 'Correction from amplifier output to antenna',
                                              c_a2_ant, {})
                        self.__addLoggerBlock(block['c_a2_ant']['parameter'], 'freq', 'the frequency [Hz]', f, {})
                        self.__addLoggerBlock(block, 'c_a2_pm1', 'Correction from amplifier output to fwd power meter',
                                              c_a2_pm1, {})
                        self.__addLoggerBlock(block['c_a2_pm1']['parameter'], 'freq', 'the frequency [Hz]', f, {})
                        PFwd = PFwd / c_a2_pm1
                        self.__addLoggerBlock(block, n + '_corrected', 'Pfwd*c_a2_ant/c_a2_pm1', PFwd, {})
                        self.__addLoggerBlock(block[n]['parameter'], 'freq', 'the frequency [Hz]', f, {})
                        self.__addLoggerBlock(block[n]['parameter'], 'tunerpos', 'tuner position', t, {})
                        # pbwd
                    n = names['pmbwd']
                    if n in nbresult:
                        PBwd = nbresult[n]
                        self.__addLoggerBlock(block, n, 'Reading of the bwd power meter', nbresult[n], {})
                        self.__addLoggerBlock(block[n]['parameter'], 'freq', 'the frequency [Hz]', f, {})
                        self.__addLoggerBlock(block[n]['parameter'], 'tunerpos', 'tuner position', t, {})
                        self.__addLoggerBlock(block, 'c_ant_pm2', 'Correction from antenna feed to bwd power meter',
                                              c_ant_pm2, {})
                        self.__addLoggerBlock(block['c_ant_pm2']['parameter'], 'freq', 'the frequency [Hz]', f, {})
                        PBwd = PBwd / c_ant_pm2
                        self.__addLoggerBlock(block, n + '_corrected', 'Pbwd/c_ant_pm2', PBwd, {})
                        self.__addLoggerBlock(block[n]['parameter'], 'freq', 'the frequency [Hz]', f, {})
                        self.__addLoggerBlock(block[n]['parameter'], 'tunerpos', 'tuner position', t, {})

                        # ref-ant
                    for i in range(nrefant):
                        n = names['pmref'][i]
                        if n in nbresult:
                            # add path correction here
                            PRef = nbresult[n]
                            self.__addLoggerBlock(block, n,
                                                  'Reading of the receive antenna power meter for position %d' % i,
                                                  nbresult[n], {})
                            self.__addLoggerBlock(block[n]['parameter'], 'freq', 'the frequency [Hz]', f, {})
                            self.__addLoggerBlock(block[n]['parameter'], 'tunerpos', 'tuner position', t, {})
                            self.__addLoggerBlock(block, 'c_refant_pmref' + str(i),
                                                  'Correction from ref antenna feed to ref power meter',
                                                  c_refant_pmref[i], {})
                            self.__addLoggerBlock(block['c_refant_pmref' + str(i)]['parameter'], 'freq',
                                                  'the frequency [Hz]', f, {})
                            PRef = PRef / c_refant_pmref[i]
                            prefant = self.__insert_it(prefant, PRef, PFwd, PBwd, f, t, i)
                            self.__addLoggerBlock(block, n + '_corrected', 'Pref/c_refant_pmref', PRef, {})
                            self.__addLoggerBlock(block[n]['parameter'], 'freq', 'the frequency [Hz]', f, {})
                            self.__addLoggerBlock(block[n]['parameter'], 'tunerpos', 'tuner position', t, {})

                            # e-field probes
                    # read field probes
                    for i in range(nprb):
                        n = names['fp'][i]
                        if n in nbresult:
                            self.__addLoggerBlock(block, n, 'Reading of the e-field probe for position %d' % i,
                                                  nbresult[n], {})
                            self.__addLoggerBlock(block[n]['parameter'], 'freq', 'the frequency [Hz]', f, {})
                            self.__addLoggerBlock(block[n]['parameter'], 'tunerpos', 'tuner position', t, {})
                            efields = self.__insert_it(efields, nbresult[n], PFwd, PBwd, f, t, i)
                    for log in self.logger:
                        log(block)

                    self.__HandleUserInterrupt(locals())
                    self.messenger(util.tstamp() + " RF Off...", [])
                    stat = mg.RFOff_Devices()  # switch off after measure
                    # END OF f LOOP
                lowBatList = mg.getBatteryLow_Devices()
                if len(lowBatList):
                    self.messenger(util.tstamp() + " WARNING: Low battery status detected for: %s" % (str(lowBatList)),
                                   [])
                self.rawData_EUTCal[description].update(
                    {'efield': efields, 'pref': prefant, 'noise': noise, 'etaTx': etaTx, 'etaRx': etaRx, 'mg': mg})
                # autosave class instance
                if self.asname and (time.time() - self.lastautosave > self.autosave_interval):
                    self.messenger(util.tstamp() + " autosave ...", [])
                    self.do_autosave()
                    self.messenger(util.tstamp() + " ... done", [])
            # END OF t LOOP

        finally:
            # finally is executed if and if not an exception occur -> save exit
            self.messenger(util.tstamp() + " RF Off and Quit...", [])
            stat = mg.RFOff_Devices()
            stat = mg.Quit_Devices()
        self.messenger(util.tstamp() + " End of EUT main calibration. Status: %d" % stat, [])
        self.PostUserEvent()
        return stat

    def Measure_Immunity(self,
                         description="EUT",
                         dotfile='msc-immunity.dot',
                         calibration='empty',
                         kernel=(None, None),
                         leveling=None,
                         freqs=None,
                         SearchPaths=None,
                         names=None):
        """Performs a msc immunity measurement according to IEC 61000-4-21
        """

        if names is None:
            names = {'sg': 'sg',
                     'a1': 'a1',
                     'a2': 'a2',
                     'ant': 'ant',
                     'fp': [],
                     'pmfwd': 'pm1',
                     'pmbwd': 'pm2',
                     'tuner': ['tuner1'],
                     'refant': ['refant1'],
                     'pmref': ['pmref1']}
        self.PreUserEvent()
        if kernel[0] is None:
            if kernel[1] is None:
                kernel = (stdImmunityKernel, {'field': Quantity(EFIELD, 10),
                                              'dwell': 1,
                                              'keylist': 'sS'})
            else:
                kernel = (stdImmunityKernel, kernel[1])

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
            self.messenger(util.tstamp() + " Resume MSC immunity measurement from autosave...", [])
        else:
            self.messenger(util.tstamp() + " Start new MSC immunity measurement...", [])

        self.rawData_Immunity.setdefault(description, {})

        # number of ref-antenna and tuners
        nrefant = min(len(names['refant']), len(names['pmref']))
        ntuner = len(names['tuner'])
        nprb = len(names['fp'])

        mg = mgraph.MGraph(dotfile, themap=names, SearchPaths=SearchPaths)
        ddict = mg.CreateDevices()
        # for k,v in ddict.items():
        #    globals()[k] = v

        self.messenger(util.tstamp() + " Init devices...", [])
        err = mg.Init_Devices()
        if err:
            self.messenger(util.tstamp() + " ...faild with err %d" % (err), [])
            return err
        try:
            self.messenger(util.tstamp() + " ...done", [])

            if calibration in self.rawData_MainCal:
                alltpos = self.GetAllTPos(calibration)
            else:
                self.messenger(util.tstamp() + " Error: Calibration '%s' not found." % calibration, [])
                return -1
            if description not in self.processedData_EUTCal:
                self.messenger(
                    util.tstamp() + " Warning: EUT-Calibration '%s' not found. CLF = 1 will be used." % calibration, [])
            # set up prefant ...
            prefant = {}
            efields = {}
            noise = {}
            eutstat = {}
            in_as = {}

            if self.autosave:
                prefant = self.rawData_Immunity[description]['pref'].copy()
                efields = self.rawData_Immunity[description]['efield'].copy()
                noise = self.rawData_Immunity[description]['noise'].copy()
                eutstat = self.rawData_Immunity[description]['eutstatus'].copy()
                eutfreqs = list(eutstat.keys())
                nfreqs = len(eutfreqs)
                min_tpos = 1e300
                max_tpos = -1
                for f in eutfreqs:
                    tpos = list(eutstat[f].keys())
                    in_as[f] = {}
                    for t in tpos:
                        testfieldlist = [item['testfield'] for item in eutstat[f][t][0]]
                        in_as[f][t] = testfieldlist
                    min_tpos = min(min_tpos, len(tpos))
                    max_tpos = max(max_tpos, len(tpos))

                msg = "Number of frequencies: %d\nMin of tuner positions: %d\nMaximum of tuner positions: %d\n" % (
                    nfreqs, min_tpos, max_tpos)
                but = []
                self.messenger(msg, but)
            self.autosave = False

            msg = "EUT immunity measurement.\nPosition reference antenna and EUT.\nSwitch EUT ON.\nAre you ready to start the measurement?\n\nStart: start measurement.\nQuit: quit measurement."
            but = ["Start", "Quit"]
            answer = self.messenger(msg, but)
            if answer == but.index('Quit'):
                self.messenger(util.tstamp() + " measurement terminated by user.", [])
                raise UserWarning  # to reach finally statement

            tposdict = {}
            for f in freqs:
                tposdict[f] = [t for t in alltpos if self.UseTunerPos(calibration, f, t)]

            etest = TestField(self, maincal=calibration, eutcal=description)
            ptest = TestPower(self, maincal=calibration, eutcal=description)
            kpardict = {'tp': tposdict,
                        'messenger': self.messenger,
                        'UIHandler': None,
                        'locals': locals()}
            kpardict.update(kernel[1])
            kern = (kernel[0])(**kpardict)
            if kpardict['UIHandler'] is None:
                UIHandler = self.stdUserInterruptHandler
            else:
                UIHandler = getattr(kern, kpardict['UIHandler'], None)
            if not callable(UIHandler):
                UIHandler = self.stdUserInterruptHandler

            f = None
            t = None
            p = None
            RFon = False
            level = None
            testfield = None

            self.lastautosave = time.time()

            dispatchtable = ('finished',
                             'freq',
                             'tuner',
                             'rf',
                             'efield',
                             'modulation',
                             'measure',
                             'eut',
                             'autosave')
            # test until break
            stat = 0
            finished = False
            try:
                ignorekeys = kernel[1]['keylist']
            except KeyError:
                ignorekeys = ''
            while not finished:
                cmd, msg, dct = kern.test(stat)
                if cmd is None:
                    stat = 0
                    continue
                cmd = cmd.lower()
                self.messenger(util.tstamp() + ' Got cmd: %s, msg: %s, dct: %s' % (cmd, msg, pprint.pformat(dct)), [])
                if len(msg):
                    self.messenger(util.tstamp() + " %s" % (msg), [])
                if cmd in ['finished']:
                    finished = True
                    stat = 0
                elif cmd in ['autosave']:
                    # autosave class instance
                    if self.asname and (time.time() - self.lastautosave > self.autosave_interval):
                        self.messenger(util.tstamp() + " autosave ...", [])
                        self.do_autosave()
                        self.messenger(util.tstamp() + " ... done", [])
                    stat = 0
                elif cmd in ['freq']:
                    f = dct['freq']
                    self.messenger(util.tstamp() + " Frequency %e Hz" % (f), [])
                    # switch if necessary
                    mg.EvaluateConditions()
                    # set frequency for all devices
                    (minf, maxf) = mg.SetFreq_Devices(f)
                    # cable corrections
                    c_sg_amp = mg.get_path_correction(names['sg'], names['a1'], POWERRATIO)
                    c_sg_ant = mg.get_path_correction(names['sg'], names['ant'], POWERRATIO)
                    c_a2_pm1 = mg.get_path_correction(names['a2'], names['pmfwd'], POWERRATIO)
                    c_a2_ant = mg.get_path_correction(names['a2'], names['ant'], POWERRATIO)
                    c_ant_pm2 = mg.get_path_correction(names['ant'], names['pmbwd'], POWERRATIO)
                    c_refant_pmref = []
                    for i in range(nrefant):
                        c_refant_pmref.append(mg.get_path_correction(names['refant'][i], names['pmref'][i], POWERRATIO))
                    c_fp = 1.0
                    # print "Got all Cable corrections"
                    # for i in range(nrefant):
                    #    print c_refant_pmref[i]

                    # check for fwd pm
                    # print mg.nodes.keys()
                    if mg.nodes[names['pmfwd']]['inst']:
                        NoPmFwd = False  # ok
                    else:  # no fwd pm
                        msg = util.tstamp() + " WARNING: No fwd power meter. Signal generator output is used instead!"
                        answer = self.messenger(msg, [])
                        NoPmFwd = True

                    pmreflist = []
                    nblist = [names['pmfwd'], names['pmbwd']]  # list of devices for NB Reading
                    for i in range(nrefant):
                        nblist.append(names['pmref'][i])
                        pmreflist.append(names['pmref'][i])
                    for i in range(nprb):
                        nblist.append(names['fp'][i])

                    # print "NBList: ", nblist
                    # noise floor measurement..
                    if f not in noise:
                        self.messenger(util.tstamp() + " Starting noise floor measurement for f = %e Hz ..." % (f), [])
                        if RFon:
                            mg.RFOff_Devices()
                        # ALL measurement start here
                        block = {}
                        mg.NBTrigger(pmreflist)
                        # serial poll all devices in list
                        olddevs = []
                        nbresult = {}
                        while 1:
                            self.__HandleUserInterrupt(locals(), handler=UIHandler)
                            nbresult = mg.NBRead(pmreflist, nbresult)
                            new_devs = [i for i in list(nbresult.keys()) if i not in olddevs]
                            olddevs = list(nbresult.keys())[:]
                            if len(new_devs):
                                self.messenger(util.tstamp() + " Got answer from: " + str(new_devs), [])
                            if len(nbresult) == len(pmreflist):
                                break
                        for i in range(nrefant):
                            n = names['pmref'][i]
                            if n in nbresult:
                                # add path correction here
                                PRef = nbresult[n]
                                nn = 'Noise ' + n
                                self.__addLoggerBlock(block, nn,
                                                      'Noise reading of the receive antenna power meter for position %d' % i,
                                                      nbresult[n], {})
                                self.__addLoggerBlock(block[nn]['parameter'], 'freq', 'the frequency [Hz]', f, {})
                                self.__addLoggerBlock(block, 'c_refant_pmref' + str(i),
                                                      'Correction from ref antenna feed to ref power meter',
                                                      c_refant_pmref[i], {})
                                self.__addLoggerBlock(block['c_refant_pmref' + str(i)]['parameter'], 'freq',
                                                      'the frequency [Hz]', f, {})
                                PRef = PRef / c_refant_pmref[i]
                                self.__addLoggerBlock(block, nn + '_corrected', 'Noise: Pref/c_refant_pmref', PRef, {})
                                self.__addLoggerBlock(block[nn + '_corrected']['parameter'], 'freq',
                                                      'the frequency [Hz]', f, {})
                                self.__addLoggerBlock(block[nn + '_corrected']['parameter'], 'tunerpos',
                                                      'tuner position', t, {})
                                noise = self.__insert_it(noise, PRef, None, None, f, t, i)
                        for log in self.logger:
                            log(block)
                        if RFon:
                            mg.RFOn_Devices()
                        self.messenger(util.tstamp() + " Noise floor measurement done.", [])
                        stat = 0
                elif cmd in ['tuner']:
                    t = dct['tunerpos']
                    if type(t) != type([]):
                        t = [t]
                    self.messenger(util.tstamp() + " Tuner position %s" % (repr(t)), [])
                    # position tuners
                    self.messenger(util.tstamp() + " Move tuner(s)...", [])
                    for i, ti in enumerate(t):
                        TPos = ti
                        IsPos = ddict[names['tuner'][i]].Goto(TPos)
                    self.messenger(util.tstamp() + " ...done", [])
                    stat = 0
                elif cmd in ['rf']:
                    rfon = dct['rfon']
                    if rfon == 1:
                        self.messenger(util.tstamp() + ' Switching RF On.', [])
                        mg.RFOn_Devices()
                        time.sleep(1)
                        RFon = True
                    else:
                        self.messenger(util.tstamp() + ' Switching RF Off.', [])
                        mg.RFOff_Devices()
                        RFon = False
                    stat = 0
                elif cmd in ['efield']:
                    efield = dct['efield']
                    if efield in ['max', 'Max', 'MAX']:
                        efield = self.getMaxE(mg, names, f, etest)
                        self.messenger("DEBUG: MaxEField: %s" % str(efield), [])
                    testfield = efield
                    power = ptest(f, efield)
                    sgpower = power / c_sg_ant
                    self.messenger(
                        "DEBUG: power: %s, c_sg_ant: %s, sgpower: %s" % (str(power), str(c_sg_ant), str(sgpower)), [])
                    olevel = level
                    try:
                        level = self.set_level(mg, sgpower)
                    except AmplifierProtectionError as _e:
                        self.messenger(
                            util.tstamp() + " Can not set signal generator level. Amplifier protection raised with message: %s" % _e.message,
                            [])
                        level = olevel
                        stat = 'AmplifierProtectionError'
                    else:
                        stat = 0
                elif cmd in ['modulation']:
                    stat = 0
                elif cmd in ['measure']:
                    # Trigger all devices in list
                    block = {}
                    mg.NBTrigger(nblist)
                    # serial poll all devices in list
                    if NoPmFwd:
                        nbresult[names['pmfwd']] = level
                        nbresult[names['pmbwd']] = Quantity(WATT, 0.0)
                    olddevs = []
                    nbresult = {}
                    while 1:
                        self.__HandleUserInterrupt(locals(), handler=UIHandler)
                        nbresult = mg.NBRead(nblist, nbresult)
                        new_devs = [i for i in list(nbresult.keys()) if i not in olddevs]
                        olddevs = list(nbresult.keys())[:]
                        if len(new_devs):
                            self.messenger(util.tstamp() + " Got answer from: " + str(new_devs), [])
                        if len(nbresult) == len(nblist):
                            break
                    # print nbresult

                    # pfwd
                    n = names['pmfwd']
                    if n in nbresult:
                        PFwd = nbresult[n]
                        self.__addLoggerBlock(block, n, 'Reading of the fwd power meter', nbresult[n], {})
                        self.__addLoggerBlock(block[n]['parameter'], 'freq', 'the frequency [Hz]', f, {})
                        self.__addLoggerBlock(block[n]['parameter'], 'tunerpos', 'tuner position', t, {})
                        PFwd = PFwd * c_a2_ant
                        self.__addLoggerBlock(block, 'c_a2_ant', 'Correction from amplifier output to antenna',
                                              c_a2_ant, {})
                        self.__addLoggerBlock(block['c_a2_ant']['parameter'], 'freq', 'the frequency [Hz]', f, {})
                        self.__addLoggerBlock(block, 'c_a2_pm1', 'Correction from amplifier output to fwd power meter',
                                              c_a2_pm1, {})
                        self.__addLoggerBlock(block['c_a2_pm1']['parameter'], 'freq', 'the frequency [Hz]', f, {})
                        PFwd = PFwd / c_a2_pm1
                        self.__addLoggerBlock(block, n + '_corrected', 'Pfwd*c_a2_ant/c_a2_pm1', PFwd, {})
                        self.__addLoggerBlock(block[n]['parameter'], 'freq', 'the frequency [Hz]', f, {})
                        self.__addLoggerBlock(block[n]['parameter'], 'tunerpos', 'tuner position', t, {})
                        # pbwd
                    n = names['pmbwd']
                    if n in nbresult:
                        PBwd = nbresult[n]
                        self.__addLoggerBlock(block, n, 'Reading of the bwd power meter', nbresult[n], {})
                        self.__addLoggerBlock(block[n]['parameter'], 'freq', 'the frequency [Hz]', f, {})
                        self.__addLoggerBlock(block[n]['parameter'], 'tunerpos', 'tuner position', t, {})
                        self.__addLoggerBlock(block, 'c_ant_pm2', 'Correction from antenna feed to bwd power meter',
                                              c_ant_pm2, {})
                        self.__addLoggerBlock(block['c_ant_pm2']['parameter'], 'freq', 'the frequency [Hz]', f, {})
                        PBwd = PBwd / c_ant_pm2
                        self.__addLoggerBlock(block, n + '_corrected', 'Pbwd/c_ant_pm2', PBwd, {})
                        self.__addLoggerBlock(block[n]['parameter'], 'freq', 'the frequency [Hz]', f, {})
                        self.__addLoggerBlock(block[n]['parameter'], 'tunerpos', 'tuner position', t, {})

                        # ref-ant
                    for i in range(nrefant):
                        n = names['pmref'][i]
                        if n in nbresult:
                            # add path correction here
                            PRef = nbresult[n]
                            self.__addLoggerBlock(block, n,
                                                  'Reading of the receive antenna power meter for position %d' % i,
                                                  nbresult[n], {})
                            self.__addLoggerBlock(block[n]['parameter'], 'freq', 'the frequency [Hz]', f, {})
                            self.__addLoggerBlock(block[n]['parameter'], 'tunerpos', 'tuner position', t, {})
                            self.__addLoggerBlock(block, 'c_refant_pmref' + str(i),
                                                  'Correction from ref antenna feed to ref power meter',
                                                  c_refant_pmref[i], {})
                            self.__addLoggerBlock(block['c_refant_pmref' + str(i)]['parameter'], 'freq',
                                                  'the frequency [Hz]', f, {})
                            PRef = PRef / c_refant_pmref[i]
                            prefant = self.__insert_it(prefant, PRef, PFwd, PBwd, f, t, i)
                            self.__addLoggerBlock(block, n + '_corrected', 'Pref/c_refant_pmref', PRef, {})
                            self.__addLoggerBlock(block[n]['parameter'], 'freq', 'the frequency [Hz]', f, {})
                            self.__addLoggerBlock(block[n]['parameter'], 'tunerpos', 'tuner position', t, {})

                            # e-field probes
                    # read field probes
                    for i in range(nprb):
                        n = names['fp'][i]
                        if n in nbresult:
                            self.__addLoggerBlock(block, n, 'Reading of the e-field probe for position %d' % i,
                                                  nbresult[n], {})
                            self.__addLoggerBlock(block[n]['parameter'], 'freq', 'the frequency [Hz]', f, {})
                            self.__addLoggerBlock(block[n]['parameter'], 'tunerpos', 'tuner position', t, {})
                            efields = self.__insert_it(efields, nbresult[n], PFwd, PBwd, f, t, i)

                    # print "vorm logger"
                    for log in self.logger:
                        log(block)
                    # print "hinterm logger"
                    lowBatList = mg.getBatteryLow_Devices()
                    # print "hinter 'getBatteryLow'"
                    if len(lowBatList):
                        self.messenger(
                            util.tstamp() + " WARNING: Low battery status detected for: %s" % (str(lowBatList)), [])
                    # print "vor update"
                    self.rawData_Immunity[description].update(
                        {'efield': efields, 'pref': prefant, 'noise': noise, 'mg': mg})
                    # print "hinter update"
                    stat = 0
                    # print "End of 'measure'"
                elif cmd in ['eut']:
                    eutstatus = dct['eutstatus']
                    pf = prefant[f][repr(t)][0][-1]['pfwd']
                    pb = prefant[f][repr(t)][0][-1]['pbwd']
                    eutstat = self.__insert_it(eutstat, eutstatus, pf, pb, f, t, 0, {'testfield': testfield})
                    self.rawData_Immunity[description].update({'eutstatus': eutstat, 'mg': mg})
                    stat = 0
                else:
                    stat = -1
                    self.messenger(util.tstamp() + " WARNING: Got unknown command '%s'. Command must be one of %s" % (
                        cmd, str(dispatchtable)), [])

                self.__HandleUserInterrupt(locals(), ignorelist=ignorekeys, handler=UIHandler)
            # end of while loop

        finally:
            # finally is executed if and if not an exception occur -> save exit
            self.messenger(util.tstamp() + " RF Off and Quit...", [])
            stat = mg.RFOff_Devices()
            stat = mg.Quit_Devices()
        self.messenger(util.tstamp() + " End of Immunity mesurement. Status: %d" % stat, [])
        self.PostUserEvent()
        return stat

    def getMaxE(self, mg, names, f, etest, rfac=None):
        #        start=names['sg']
        #        ends=[names['ant'],names['pmfwd'],names['pmbwd']]
        #        maxstart=None
        #        allpaths=[]
        #        for end in ends:
        #            allpaths.extend(mg.find_all_paths(start, end))
        #        for path in allpaths:
        #            edges = []
        #            for i in range(len(path)-1):
        #                left  = path[i]
        #                right = path[i+1]
        #                edges.append((left,right,mg.graph[left][right]))
        #            for left,right,edge in edges:
        #                try:
        #                    attribs = mg.nodes[edge['dev']]
        #                except KeyError:
        #                    continue
        #                if attribs['inst'] is None:
        #                    continue
        #                err = 0
        #                if (attribs.has_key('isActive') and attribs['isActive']):
        #                    dev=attribs['inst']
        #                    cmds = ['getData', 'GetData']
        #                    stat = -1
        #                    for cmd in cmds:
        #                        #print hasattr(dev, cmd)
        #                        if hasattr(dev, cmd):
        #                            # at the moment, we only check for MAXIN
        #                            what = ['MAXIN'] #['MAXIN', 'MAXFWD', 'MAXBWD']
        #                            for w in what:
        #                                stat = 0
        #                                try:
        #                                    stat, result = getattr(dev, cmd)(w)
        #                                except AttributeError:
        #                                    # function not callable
        #                                    #print "attrErr"
        #                                    continue
        #                                if stat != 0:
        #                                    #print stat
        #                                    continue
        #                                # ok we have a value that can be checked
        #                                corr = mg.get_path_correction(start, left)
        #                                sglevel = result / corr
        #                                sglevel = sglevel.mag()
        #                                #print "DEBUG: Node %s limits sglevel to %s"%(left,str(sglevel))
        #                                if maxstart:
        #                                    maxstart=min(maxstart,sglevel)
        #                                else:
        #                                    maxstart=umddevice.UMDMResult(sglevel)
        #
        sglv = mg.MaxSafe
        pathcorr = mg.get_path_correction(mg.name.start, mg.name.ant, POWERRATIO)
        pfwd = sglv * pathcorr
        Emax = etest(f, pfwd)
        if rfac is None:  # assume 1dB compression -> rfac=0.891  (1/ 10**(1/20))
            rfac = 0.891
        return rfac * Emax

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
    ##                        sglevel = result / corr
    ##                        sglevel = sglevel.mag()
    ##                        print "DEBUG: Node %s limits sglevel to %s"%(n,str(sglevel))
    ##                        if maxstart:
    ##                            maxstart=min(maxstart,sglevel)
    ##                        else:
    ##                            maxstart=umddevice.UMDMResult(sglevel,sglevel.unit)
    ##
    ##            pathcorr=mg.get_path_correction(start, end, umddevice.UMD_dB)
    ##            pfwd=maxstart*pathcorr.mag()
    ##            Emax = etest(f,pfwd)
    ##        return Emax

    def Measure_Emission(self,
                         description="EUT",
                         dotfile='msc-emission.dot',
                         calibration='empty',
                         delay=1.0,
                         freqs=None,
                         receiverconf=None,
                         SearchPaths=None,
                         names=None):
        """Performs a msc emission measurement according to IEC 61000-4-21
        """

        if names is None:
            names = {'tuner': ['tuner1'],
                     'refant': ['refant1'],
                     'receiver': ['saref1']}
        self.PreUserEvent()
        if self.autosave:
            self.messenger(util.tstamp() + " Resume MSC emission measurement from autosave...", [])
        else:
            self.messenger(util.tstamp() + " Start new MSC emission measurement...", [])

        self.rawData_Emission.setdefault(description, {})

        # number of ref-antenna and tuners
        nrefant = min(len(names['refant']), len(names['receiver']))
        ntuner = len(names['tuner'])

        mg = mgraph.MGraph(dotfile, themap=names, SearchPaths=SearchPaths)
        ddict = mg.CreateDevices()
        # for k,v in ddict.items():
        #    globals()[k] = v

        self.messenger(util.tstamp() + " Init devices...", [])
        err = mg.Init_Devices()
        if err:
            self.messenger(util.tstamp() + " ...faild with err %d" % (err), [])
            return err
        try:
            self.messenger(util.tstamp() + " ...done", [])
            if freqs is None:
                freqs = []

            if receiverconf is None:
                receiverconf = {}
            rcfreqs = list(receiverconf.keys())
            rcfreqs.sort()
            rcfreqs.reverse()

            if calibration in self.rawData_MainCal:
                alltpos = self.GetAllTPos(calibration)
            else:
                self.messenger(util.tstamp() + " Error: Calibration '%s' not found." % calibration, [])
                return -1
            # set up prefant, noise, ...
            prefant = {}
            noise = {}

            if self.autosave:
                try:
                    prefant = self.rawData_Emission[description]['pref'].copy()
                except KeyError:  # as after noise -> no pref yet
                    pass
                noise = self.rawData_Emission[description]['noise'].copy()
                # we have to loop over all tuner positions and
                # check if we have all freqs for this tpos
                # if complete -> remove from alltpos and add to tees
                tees = []
                for f in freqs:
                    try:
                        measured_tpos = list(prefant[f].keys())
                    except KeyError:
                        measured_tpos = []
                    for t in alltpos:
                        if not self.UseTunerPos(calibration, f, t):
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
                        util.LogError(self.messenger)
                msg = "List of tuner positions from autosave file:\n%s\nRemaining tuner positions:\n%s\n" % (
                    str(tees), str(alltpos))
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
                self.autosave = False
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
                    self.messenger(util.tstamp() + " measurement terminated by user.", [])
                    raise UserWarning  # to reach finally statement
                # loop freqs
                try:
                    t = alltpos[0]
                except IndexError:
                    t = [0]
                for f in freqs:
                    if f in list(noise.keys()):
                        continue
                    self.messenger(util.tstamp() + " Frequency %e Hz" % (f), [])
                    mg.EvaluateConditions()
                    # set frequency for all devices
                    (minf, maxf) = mg.SetFreq_Devices(f)
                    # configure receiver(s)
                    for rf in rcfreqs:
                        if f >= rf:
                            break
                    try:
                        conf = receiverconf[rf]
                    except:
                        conf = {}
                    rconf = mg.ConfReceivers(conf)
                    self.messenger(util.tstamp() + " Receiver configuration: %s" % str(rconf), [])

                    # cable corrections
                    c_refant_receiver = []
                    for i in range(nrefant):
                        c_refant_receiver.append(
                            mg.get_path_correction(names['refant'][i], names['receiver'][i], POWERRATIO))

                    # ALL measurement start here
                    block = {}
                    nbresult = {}  # dict for NB-Read results
                    receiverlist = []

                    for i in range(nrefant):
                        receiverlist.append(names['receiver'][i])

                    # noise floor measurement..
                    self.messenger(util.tstamp() + " Starting noise floor measurement for f = %e Hz ..." % (f), [])
                    mg.NBTrigger(receiverlist)
                    # serial poll all devices in list
                    olddevs = []
                    while 1:
                        self.__HandleUserInterrupt(locals())
                        nbresult = mg.NBRead(receiverlist, nbresult)
                        new_devs = [i for i in list(nbresult.keys()) if i not in olddevs]
                        olddevs = list(nbresult.keys())[:]
                        if len(new_devs):
                            self.messenger(util.tstamp() + " Got answer from: " + str(new_devs), [])
                        if len(nbresult) == len(receiverlist):
                            break
                    for i in range(nrefant):
                        n = names['receiver'][i]
                        if n in nbresult:
                            # add path correction here
                            PRef = nbresult[n]
                            nn = 'Noise ' + n
                            self.__addLoggerBlock(block, nn,
                                                  'Noise reading of the receive antenna receiver for position %d' % i,
                                                  nbresult[n], {})
                            self.__addLoggerBlock(block[nn]['parameter'], 'freq', 'the frequency [Hz]', f, {})
                            self.__addLoggerBlock(block, 'c_refant_receiver' + str(i),
                                                  'Correction from ref antenna feed to ref receiver',
                                                  c_refant_receiver[i], {})
                            self.__addLoggerBlock(block['c_refant_receiver' + str(i)]['parameter'], 'freq',
                                                  'the frequency [Hz]', f, {})
                            PRef = abs((PRef / c_refant_receiver[i]).reduce_to(WATT))
                            self.__addLoggerBlock(block, nn + '_corrected', 'Noise: Pref/c_refant_receiver', PRef, {})
                            self.__addLoggerBlock(block[nn + '_corrected']['parameter'], 'freq', 'the frequency [Hz]',
                                                  f, {})
                            self.__addLoggerBlock(block[nn + '_corrected']['parameter'], 'tunerpos', 'tuner position',
                                                  t, {})
                            noise = self.__insert_it(noise, PRef, None, None, f, t, i)
                    self.messenger(util.tstamp() + " Noise floor measurement done.", [])

                    for log in self.logger:
                        log(block)

                    self.__HandleUserInterrupt(locals())
                    # END OF f LOOP
                lowBatList = mg.getBatteryLow_Devices()
                if len(lowBatList):
                    self.messenger(util.tstamp() + " WARNING: Low battery status detected for: %s" % (str(lowBatList)),
                                   [])
                self.rawData_Emission[description].update({'noise': noise})
                # autosave class instance
                if self.asname and (time.time() - self.lastautosave > self.autosave_interval):
                    self.messenger(util.tstamp() + " autosave ...", [])
                    self.do_autosave()
                    self.messenger(util.tstamp() + " ... done", [])

                # NOISE MEASUREMENT finished
            self.autosave = False

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
                self.messenger(util.tstamp() + " measurement terminated by user.", [])
                raise UserWarning  # to reach finally statement

            # loop tuner positions
            for t in alltpos:
                self.messenger(util.tstamp() + " Tuner position %s" % (repr(t)), [])
                # position tuners
                self.messenger(util.tstamp() + " Move tuner(s)...", [])
                for i in range(ntuner):
                    TPos = t[i]
                    IsPos = ddict[names['tuner'][i]].Goto(TPos)
                self.messenger(util.tstamp() + " ...done", [])
                # loop freqs
                for f in freqs:
                    self.messenger(util.tstamp() + " Frequency %e Hz" % (f), [])
                    if not self.UseTunerPos(calibration, f, t):
                        self.messenger(util.tstamp() + " Skipping tuner position", [])
                        continue
                    # switch if necessary
                    mg.EvaluateConditions()
                    # set frequency for all devices
                    (minf, maxf) = mg.SetFreq_Devices(f)
                    # configure receiver(s)
                    for rf in rcfreqs:
                        if f >= rf:
                            break
                    try:
                        conf = receiverconf[rf]
                    except:
                        conf = {}
                    rconf = mg.ConfReceivers(conf)
                    self.messenger(util.tstamp() + " Receiver configuration: %s" % str(rconf), [])

                    # cable corrections
                    c_refant_receiver = []
                    for i in range(nrefant):
                        c_refant_receiver.append(
                            mg.get_path_correction(names['refant'][i], names['receiver'][i], POWERRATIO))

                    # ALL measurement start here
                    block = {}
                    nbresult = {}  # dict for NB-Read results
                    nblist = []  # list of devices for NB Reading

                    for i in range(nrefant):
                        nblist.append(names['receiver'][i])

                    # wait delay seconds
                    time.sleep(0.5)  # minimum delay according -4-21
                    self.messenger(util.tstamp() + " Going to sleep for %d seconds ..." % (delay), [])
                    self.wait(delay, locals(), self.__HandleUserInterrupt)
                    self.messenger(util.tstamp() + " ... back.", [])

                    # Trigger all devices in list
                    mg.NBTrigger(nblist)
                    # serial poll all devices in list
                    olddevs = []
                    while 1:
                        self.__HandleUserInterrupt(locals())
                        nbresult = mg.NBRead(nblist, nbresult)
                        new_devs = [i for i in list(nbresult.keys()) if i not in olddevs]
                        olddevs = list(nbresult.keys())[:]
                        if len(new_devs):
                            self.messenger(util.tstamp() + " Got answer from: " + str(new_devs), [])
                        if len(nbresult) == len(nblist):
                            break
                    # print nbresult

                    # ref-ant
                    for i in range(nrefant):
                        n = names['receiver'][i]
                        if n in nbresult:
                            # add path correction here
                            PRef = nbresult[n]
                            self.__addLoggerBlock(block, n,
                                                  'Reading of the receive antenna receiver for position %d' % i,
                                                  nbresult[n], {})
                            self.__addLoggerBlock(block[n]['parameter'], 'freq', 'the frequency [Hz]', f, {})
                            self.__addLoggerBlock(block[n]['parameter'], 'tunerpos', 'tuner position', t, {})
                            self.__addLoggerBlock(block, 'c_refant_receiver' + str(i),
                                                  'Correction from ref antenna feed to ref receiver',
                                                  c_refant_receiver[i], {})
                            self.__addLoggerBlock(block['c_refant_receiver' + str(i)]['parameter'], 'freq',
                                                  'the frequency [Hz]', f, {})
                            PRef = PRef / c_refant_receiver[i]
                            prefant = self.__insert_it(prefant, PRef, None, None, f, t, i)
                            self.__addLoggerBlock(block, n + '_corrected', 'Pref/c_refant_receiver', PRef, {})
                            self.__addLoggerBlock(block[n]['parameter'], 'freq', 'the frequency [Hz]', f, {})
                            self.__addLoggerBlock(block[n]['parameter'], 'tunerpos', 'tuner position', t, {})

                    for log in self.logger:
                        log(block)

                    self.__HandleUserInterrupt(locals())
                    # END OF f LOOP
                lowBatList = mg.getBatteryLow_Devices()
                if len(lowBatList):
                    self.messenger(util.tstamp() + " WARNING: Low battery status detected for: %s" % (str(lowBatList)),
                                   [])
                self.rawData_Emission[description].update({'pref': prefant, 'mg': mg})
                # autosave class instance
                if self.asname and (time.time() - self.lastautosave > self.autosave_interval):
                    self.messenger(util.tstamp() + " autosave ...", [])
                    self.do_autosave()
                    self.messenger(util.tstamp() + " ... done", [])
            # END OF t LOOP

        finally:
            # finally is executed if and if not an exception occur -> save exit
            self.messenger(util.tstamp() + " Quit...", [])
            stat = mg.Quit_Devices()
        self.messenger(util.tstamp() + " End of Emission mesurement. Status: %d" % stat, [])
        self.PostUserEvent()
        return stat

    def GetAllTPos(self, description):
        try:
            data = self.rawData_MainCal[description]['efield']
        except:
            return []
        freqs = list(data.keys())
        freqs.sort()
        ntuner = len(eval(list(data[freqs[0]].keys())[0]))  # ;-)
        pos = []
        for n in range(ntuner):
            pos.append([])
        for f in freqs:
            for n in range(ntuner):
                lst = [eval(list(data[f].keys())[i])[n] for i in range(len(list(data[f].keys())))]
                for l in lst:
                    if l not in pos[n]:
                        pos[n].append(l)
        for p in pos:
            p.sort()
        alltpos = util.combinations(pos)
        return alltpos

    def UseTunerPos(self, description, f, t):
        try:
            data = self.rawData_MainCal[description]['efield']
        except:
            return False
        freqs = list(data.keys())
        freqs.sort()
        freqs.reverse()
        for fi in freqs:
            if f >= fi:
                break
        tlist = list(data[fi].keys())
        if str(t) in tlist:
            return True
        else:
            return False

    def OutputRawData_MainCal(self, description=None, what=None, fname=None):
        thedata = self.rawData_MainCal
        stdout = sys.stdout
        fp = None
        if fname:
            fp = open(fname, "w")
            sys.stdout = fp
        try:
            self.__OutputRawData(thedata, description, what)
        finally:
            try:
                if fp:
                    fp.close()
            except:
                util.LogError(self.messenger)
            sys.stdout = stdout

    def OutputRawData_Emission(self, description=None, what=None, fname=None):
        thedata = self.rawData_Emission
        stdout = sys.stdout
        fp = None
        if fname:
            fp = open(fname, "w")
            sys.stdout = fp
        try:
            self.__OutputRawData(thedata, description, what)
        finally:
            try:
                if fp:
                    fp.close()
            except:
                util.LogError(self.messenger)
            sys.stdout = stdout

    def OutputRawData_AutoCorr(self, description=None, what=None, fname=None):
        thedata = self.rawData_AutoCorr
        stdout = sys.stdout
        fp = None
        if fname:
            fp = open(fname, "w")
            sys.stdout = fp
        try:
            self.__OutputRawData(thedata, description, what)
        finally:
            try:
                if fp:
                    fp.close()
            except:
                util.LogError(self.messenger)
            sys.stdout = stdout

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

    def OutputRawData_EUTCal(self, description=None, what=None, fname=None):
        thedata = self.rawData_EUTCal
        stdout = sys.stdout
        fp = None
        if fname:
            fp = open(fname, "w")
            sys.stdout = fp
        try:
            self.__OutputRawData(thedata, description, what)
        finally:
            try:
                if fp:
                    fp.close()
            except:
                util.LogError(self.messenger)
            sys.stdout = stdout

    def OutputRawData_Immunity(self, description=None, what=None, fname=None):
        thedata = self.rawData_Immunity
        stdout = sys.stdout
        fp = None
        if fname:
            fp = open(fname, "w")
            sys.stdout = fp
        try:
            self.__OutputRawData(thedata, description, what)
        finally:
            try:
                if fp:
                    fp.close()
            except:
                util.LogError(self.messenger)
            sys.stdout = stdout

    def __OutputRawData(self, thedata, description, what):
        deslist = self.make_deslist(thedata, description)
        whatlist = self.make_whatlist(thedata, what)
        for d in deslist:
            print("# Description:", d)
            for w in whatlist:
                print("# ", w)
                data = thedata[d][w]
                try:
                    freqs = list(data.keys())
                    freqs.sort()
                    for f in freqs:
                        tees = list(data[f].keys())
                        tees.sort()
                        for t in tees:
                            pees = list(data[f][t].keys())
                            pees.sort()
                            for p in pees:
                                print("f:", f, "t:", t, "p:", p, end=' ')
                                item = data[f][t][p]
                                self.out(item)
                                print()
                except:  # data has no keys
                    item = data
                    self.out(item)
                    print()

    def OutputProcessedData_MainCal(self, description=None, what=None, fname=None):
        thedata = self.processedData_MainCal
        stdout = sys.stdout
        if fname:
            fp = open(fname, "w")
            sys.stdout = fp
        try:
            self.__OutputProcessedData(thedata, description, what)
        finally:
            try:
                fp.close()
            except:
                util.LogError(self.messenger)
            sys.stdout = stdout

    def OutputProcessedData_Emission(self, description=None, what=None, fname=None):
        thedata = self.processedData_Emission
        stdout = sys.stdout
        if fname:
            fp = open(fname, "w")
            sys.stdout = fp
        try:
            self.__OutputProcessedData(thedata, description, what)
        finally:
            try:
                fp.close()
            except:
                util.LogError(self.messenger)
            sys.stdout = stdout

    def OutputProcessedData_EUTCal(self, description=None, what=None, fname=None):
        thedata = self.processedData_EUTCal
        stdout = sys.stdout
        if fname:
            fp = open(fname, "w")
            sys.stdout = fp
        try:
            self.__OutputProcessedData(thedata, description, what)
        finally:
            try:
                fp.close()
            except:
                util.LogError(self.messenger)
            sys.stdout = stdout

    def OutputProcessedData_AutoCorr(self, description=None, what=None, fname=None):
        thedata = self.processedData_AutoCorr
        stdout = sys.stdout
        if fname:
            fp = open(fname, "w")
            sys.stdout = fp
        try:
            self.__OutputProcessedData(thedata, description, what)
        finally:
            try:
                fp.close()
            except:
                util.LogError(self.messenger)
            sys.stdout = stdout

    def OutputProcessedData_Immunity(self, description=None, what=None, fname=None):
        thedata = self.processedData_Immunity
        stdout = sys.stdout
        if fname:
            fp = open(fname, "w")
            sys.stdout = fp
        try:
            self.__OutputProcessedData(thedata, description, what)
        finally:
            try:
                fp.close()
            except:
                util.LogError(self.messenger)
            sys.stdout = stdout

    def __OutputProcessedData(self, thedata, description, what):
        deslist = self.make_deslist(thedata, description)
        whatlist = self.make_whatlist(thedata, what)
        for d in deslist:
            data = thedata[d]
            print("Description:", d)
            for w in whatlist:
                if w in data:
                    print(w, ":")
                    try:
                        freqs = list(data[w].keys())
                        freqs.sort()
                        for f in freqs:
                            print(f, end=' ')
                            item = data[w][f]
                            self.out(item)
                            print()
                    except:
                        item = data[w]
                        self.out(item)
                        print()

    def GetKeys_MainCal(self):
        return list(self.processedData_MainCal.keys())

    def GetFreqs_MainCal(self, description):
        if description in self.rawData_MainCal:
            freqs = list(self.rawData_MainCal[description]['efield'].keys())
            freqs.sort()
            return freqs
        else:
            return []

    def getStandard(self, s=None):
        if s is None:
            s = self.std_Standard
        ls = s.lower()
        if 'iec' in ls or '21' in ls:
            return 'IEC 61000-4-21'
        elif 'rtca' in ls or '160' in ls:
            return 'RTCA DO160E'
        elif 'mil' in ls or '461' in ls:
            return 'MILSTD 461E'
        else:
            return self.std_Standard

    def MaxtoAvET2(self):
        t = [1, 2, 3, 4, 5, 9, 10, 12, 18, 20, 24, 30, 36, 40, 45, 60, 90, 120, 180, 400, 1000]
        r = [1, 1.313, 1.499, 1.630, 1.732, 1.957, 2, 2.08, 2.25, 2.3, 2.38, 2.47, 2.54, 2.59, 2.64, 2.76, 2.92, 3.04,
             3.2, 3.6, 3.97]
        return scipy.interpolate.interp1d(t, r)

    def Evaluate_MainCal(self, description="empty", standard=None, freqs=None):
        ctx = Context()
        standard = self.getStandard(standard)
        self.messenger(util.tstamp() + " Start of evaluation of main calibration with description %s" % description, [])
        if description not in self.rawData_MainCal:
            self.messenger(util.tstamp() + " Description %s not found." % description, [])
            return -1

        if not freqs:
            freqs = list(self.rawData_MainCal[description]['efield'].keys())
        freqs.sort()

        # shortcuts to raw data
        efields = self.rawData_MainCal[description]['efield']
        pref = self.rawData_MainCal[description]['pref']

        self.processedData_MainCal.setdefault(description, {})
        self.processedData_MainCal[description]['Standard_Used'] = standard
        self.processedData_MainCal[description]['PMaxRec'] = {}
        self.processedData_MainCal[description]['PAveRec'] = {}
        self.processedData_MainCal[description]['PInputForEField'] = {}
        self.processedData_MainCal[description]['PInputForRecAnt'] = {}
        self.processedData_MainCal[description]['PInputVarationForEField'] = {}
        self.processedData_MainCal[description]['PInputVarationForRecAnt'] = {}
        self.processedData_MainCal[description]['ACF'] = {}
        self.processedData_MainCal[description]['IL'] = {}
        self.processedData_MainCal[description]['EMax'] = {}
        self.processedData_MainCal[description]['EMaxT'] = {}
        self.processedData_MainCal[description]['Enorm'] = {}
        self.processedData_MainCal[description]['EnormT'] = {}
        self.processedData_MainCal[description][
            'EnormTmax2'] = {}  # normalized averaged squared Magnitude of Efield cal (DO160 20.6.3.3)
        self.processedData_MainCal[description]['EnormAveXYZ'] = {}
        self.processedData_MainCal[description]['EnormAve'] = {}
        self.processedData_MainCal[description]['EnormTAve'] = {}
        self.processedData_MainCal[description]['SigmaXYZ'] = {}
        self.processedData_MainCal[description]['Sigma24'] = {}
        self.processedData_MainCal[description]['SigmaXYZ_dB'] = {}
        self.processedData_MainCal[description]['Sigma24_dB'] = {}
        # the evaluation has to be done for all frequencies
        for f in freqs:
            self.messenger(util.tstamp() + " Frequency: %.2f ..." % f, [])
            # print
            # print f,
            tees = list(efields[f].keys())  # tuner positions
            pees = list(efields[f][tees[0]].keys())  # e-field probe positions
            prees = list(pref[f][tees[0]].keys())  # ref antenna positions
            # tees.sort()
            pees.sort()
            prees.sort()
            ntees = len(tees)
            npees = len(pees)
            nprees = len(prees)
            # EMaxL EMaxTL, PInputL and PInputVariation
            # are all dicts with key=e-field probe pos
            # and items are lists (because values in raw data are lists allready)
            EMaxL = {}  # for R components
            EMaxTL = {}  # same for total field
            PInputEL = {}  # input for a certain field strength
            PInputVariationEL = {}  # max to min ratio
            for p in pees:  # positions in the room, keys for the dicts
                # print p,
                EMax = []
                for k in (0, 1, 2):  # x,y,z
                    EMax.append(Quantity(EFIELD, 0.0))  # for each p init EMax with (0 V/m, 0 V/m, 0 V/m)
                EMaxT = Quantity(EFIELD, 0.0)
                PInput = Quantity(WATT, 0.0)
                PInputMin = Quantity(WATT, 1.0e10)
                PInputMax = Quantity(WATT, 0.0)
                InCounter = 0
                for t in tees:  # tuner positions-> max values with respect to tuner
                    # print t,
                    # try:
                    #    efields[f][t][p]
                    # except KeyError:
                    #    efields[f][t][p]=efields[f][t][0]   # TO BE REMOVED
                    for efli in efields[f][t][p]:  # typically, len=1
                        ef = efli['value']  # x,y,z vector
                        # import pprint
                        # pprint.pprint(ef)
                        # print len(ef), ef[0], ef[1], ef[2]
                        for k in (0, 1, 2):  # max for each component
                            # print EMax[k], ef[k], '->',
                            EMax[k] = max(EMax[k], ef[k])
                            # print EMax[k]
                        # print "EMax", EMax
                        et = numpy.sqrt(sum([e * e for e in ef], Quantity(EFIELD, 0.0) ** 2))  # max of rss (E_T)
                        EMaxT = max(EMaxT, et)

                        pf = efli['pfwd']
                        PInputMin = min(PInputMin, pf)  # min
                        PInputMax = max(PInputMax, pf)  # max
                        PInput += pf  # av
                        InCounter += 1
                # print
                # print EMax
                PInput /= InCounter
                EMaxL[p] = [_.eval() for _ in EMax]  # for each probe pos: Max over tuner positions
                EMaxTL[p] = EMaxT.eval()
                PInputVariation = (PInputMax / PInputMin).eval()
                PInputEL[p] = PInput.eval()
                PInputVariationEL[p] = PInputVariation

            # receive antenna calibration
            PMaxRecL = {}  # again, keys are the positions and values are lists
            PAveRecL = {}
            PInputAL = {}
            PInputVariationAL = {}
            for p in prees:  # ref antenna positions -> keys
                PMaxRec = Quantity(WATT, 0.0)
                PAveRec = Quantity(WATT, 0.0)
                RecCounter = 0
                PInput = Quantity(WATT, 0.0)
                PInputMin = Quantity(WATT, 1.0e10)
                PInputMax = Quantity(WATT, 0.0)
                InCounter = 0
                for t in tees:
                    try:
                        pref[f][t][p]
                    except KeyError:
                        pref[f][t][p] = pref[f][t][0][:]
                    for i in range(len(pref[f][t][p])):
                        pr = pref[f][t][p][i]['value']
                        # pr = pr.mag()
                        PMaxRec = max(PMaxRec, pr)
                        PAveRec += pr
                        RecCounter += 1
                        pf = pref[f][t][p][i]['pfwd']
                        # pf = pf.mag()
                        PInputMin = min(PInputMin, pf)
                        PInputMax = max(PInputMax, pf)
                        PInput += pf
                        InCounter += 1
                PAveRec /= RecCounter
                PMaxRecL[p] = PMaxRec.eval()
                PAveRecL[p] = PAveRec.eval()  # for each receive antenna pos: Max and Av over tuner positions
                PInput /= InCounter
                PInputVariation = (PInputMax / PInputMin).eval()
                PInputAL[p] = PInput.eval()
                PInputVariationAL[p] = PInputVariation

            self.processedData_MainCal[description]['PMaxRec'][f] = PMaxRecL.copy()
            self.processedData_MainCal[description]['PAveRec'][f] = PAveRecL.copy()
            self.processedData_MainCal[description]['PInputForEField'][f] = PInputEL.copy()
            self.processedData_MainCal[description]['PInputForRecAnt'][f] = PInputAL.copy()
            self.processedData_MainCal[description]['PInputVarationForEField'][f] = PInputVariationEL.copy()
            self.processedData_MainCal[description]['PInputVarationForRecAnt'][f] = PInputVariationAL.copy()
            self.processedData_MainCal[description]['EMax'][f] = EMaxL.copy()
            self.processedData_MainCal[description]['EMaxT'][f] = EMaxTL.copy()

            # calc ACF and IL
            IL = Quantity(POWERRATIO, 0.0)
            for pos, Pmax in list(PMaxRecL.items()):
                IL = IL + Quantity(POWERRATIO, 1.0) * Pmax / PInputAL[pos]
            IL = (IL / len(list(PMaxRecL.keys()))).eval()
            ACF = Quantity(POWERRATIO, 0.0)
            for pos, Pav in list(PAveRecL.items()):
                ACF = ACF + Quantity(POWERRATIO, 1.0) * Pav / PInputAL[pos]
            ACF = (ACF / len(list(PAveRecL.keys()))).eval()
            self.processedData_MainCal[description]['ACF'][f] = ACF
            self.processedData_MainCal[description]['IL'][f] = IL

            Avxyz = [Quantity(EFIELDPNORM, 0.0) for _ in (1, 2, 3)]  # umddevice.stdVectorUMDMResult()
            self.processedData_MainCal[description]['Enorm'][f] = {}
            self.processedData_MainCal[description]['EnormT'][f] = {}
            for pos, Em in list(EMaxL.items()):
                pin = self.processedData_MainCal[description]['PInputForEField'][f][pos]
                v = numpy.sqrt(pin)
                # sqrtv=math.sqrt(v)
                # u = pin.get_u()
                # l = pin.get_l()
                sqrtPInput = v  # umddevice.UMDMResult(sqrtv, sqrtv+(u-l)/(4.0*sqrtv), sqrtv-(u-l)/(4.0*sqrtv), umddevice.UMD_sqrtW)
                en = [_e_ / sqrtPInput for _e_ in Em]  # umddevice.stdVectorUMDMResult()
                for k, _en_ in enumerate(en):
                    Avxyz[k] += _en_
                self.processedData_MainCal[description]['Enorm'][f][pos] = [_.eval() for _ in en]
            Npos = len(list(EMaxL.keys()))
            Avxyz = [_a_ / float(Npos) for _a_ in Avxyz]
            AvT = Quantity(EFIELDPNORM, 0.0)
            for pos, Em in list(EMaxTL.items()):
                pin = self.processedData_MainCal[description]['PInputForEField'][f][pos]
                v = numpy.sqrt(pin)
                # sqrtv=math.sqrt(v)
                # u = pin.get_u()
                # l = pin.get_l()
                sqrtPInput = v  # umddevice.UMDMResult(sqrtv, sqrtv+(u-l)/(4.0*sqrtv), sqrtv-(u-l)/(4.0*sqrtv), umddevice.UMD_sqrtW)
                en = Em / sqrtPInput
                self.processedData_MainCal[description]['EnormT'][f][pos] = en.eval()
                AvT += en
            AvT /= float(len(EMaxTL))
            Av24 = Quantity(EFIELDPNORM, 0.0)
            for k in (0, 1, 2):
                Av24 += Avxyz[k]
            Av24 /= 3.0
            Avxyz = self.processedData_MainCal[description]['EnormAveXYZ'][f] = [_.eval() for _ in Avxyz]
            Av24 = self.processedData_MainCal[description]['EnormAve'][f] = Av24.eval()
            AvT = self.processedData_MainCal[description]['EnormTAve'][f] = AvT.eval()
            enorm = self.processedData_MainCal[description]['Enorm'][f]
            Sxyz = []  # umddevice.stdVectorUMDMResult()
            list24 = []
            for k in (0, 1, 2):
                lst = [enorm[p][k] for p in list(enorm.keys())]
                list24 = list24 + lst
                S = util.CalcSigma(lst, Avxyz[k])
                Sxyz.append(S.eval())
            S24 = util.CalcSigma(list24, Av24).eval()

            self.processedData_MainCal[description]['SigmaXYZ'][f] = [_.eval() for _ in Sxyz]
            self.processedData_MainCal[description]['Sigma24'][f] = S24.eval()
            SdBxyz = [20 * numpy.log10((Sxyz[k] + Avxyz[k]) / Avxyz[k]) for k in
                      (0, 1, 2)]  # umddevice.stdVectorUMDMResult()
            SdB24 = 20 * numpy.log10((S24 + Av24) / Av24)
            self.processedData_MainCal[description]['SigmaXYZ_dB'][f] = [_.eval() for _ in SdBxyz]
            self.processedData_MainCal[description]['Sigma24_dB'][f] = SdB24.eval()

        self.messenger(util.tstamp() + " End of evaluation of main calibration", [])
        return 0

    def Evaluate_Emission(self,
                          description="EUT",
                          empty_cal="empty",
                          loaded_cal="loaded",
                          EUT_cal="EUT",
                          interpolation='linxliny',
                          distance=10,
                          directivity=1.7,
                          hg=0.8,
                          RH=(0.8, 0.8),
                          isoats=None):
        if isoats is None:
            isoats = False
        if isoats:
            gmax = util.gmax_oats
            gmax_model = "OATS"
        else:
            gmax = util.gmax_fs
            gmax_model = "FAR"
        dmax_f = directivity

        EUTrawData = self.rawData_EUTCal
        EUTprocData = self.processedData_EUTCal

        self.messenger(util.tstamp() + " Start of evaluation of emission measurement with description %s" % description,
                       [])
        if description not in self.rawData_Emission:
            self.messenger(util.tstamp() + " Description %s not found." % description, [])
            return -1
        if empty_cal not in self.rawData_MainCal:
            self.messenger(util.tstamp() + " Empty chamber cal not found. Description: %s" % empty_cal, [])
            return -1
        if loaded_cal not in self.rawData_MainCal:
            self.messenger(util.tstamp() + " Loaded chamber cal not found. Description: %s" % loaded_cal, [])
            return -1
        if EUT_cal not in EUTrawData:
            self.messenger(util.tstamp() + " EUT cal not found. Description: %s" % EUT_cal, [])
            return -1

        # zeroPR = Quantity (POWERRATIO, 0.0)

        pref = self.rawData_Emission[description]['pref']
        noise = self.rawData_Emission[description]['noise']
        freqs = list(pref.keys())
        freqs.sort()

        # check loading
        empty_loaded = empty_cal + ',' + loaded_cal
        if empty_loaded not in self.processedData_MainCal:
            self.CalculateLoading_MainCal(empty_cal=empty_cal, loaded_cal=loaded_cal)
        maxload = self.processedData_MainCal[empty_loaded]['Loading']
        empty_eut = empty_cal + ',' + EUT_cal
        if empty_eut not in EUTprocData:
            self.CalculateLoading_EUTCal(empty_cal=empty_cal, eut_cal=EUT_cal, freqs=freqs)
        eutload = EUTprocData[empty_eut]['Loading']

        # cal_freqs = self.rawData_MainCal[empty_cal]['efield'].keys().sort()
        # maxload_org = maxload.values()
        maxload_inter = util.InterpolateMResults(maxload, freqs, interpolation)

        etaTx_org = {}
        etaTx = self.rawData_MainCal[empty_cal]['etaTx']
        for f in list(etaTx.keys()):
            t = list(etaTx[f].keys())[0]
            p = list(etaTx[f][t].keys())[0]
            for ei in etaTx[f][t][p]:
                if not ei['value'] is None:
                    break
            etaTx_org[f] = ei['value']
        etaTx_inter = util.InterpolateMResults(etaTx_org, freqs, interpolation)

        il_org = self.processedData_MainCal[empty_cal]['IL']
        il_inter = util.InterpolateMResults(il_org, freqs, interpolation)

        # eutcal_freqs = self.processedData_EUTCal[EUT_cal]['CCF'].keys()
        ccf = EUTprocData[EUT_cal]['CCF']
        clf = EUTprocData[EUT_cal]['CLF']
        ccf_inter = util.InterpolateMResults(ccf, freqs, interpolation)
        clf_inter = util.InterpolateMResults(clf, freqs, interpolation)

        relload = {}
        for i, f in enumerate(freqs):
            relload[f] = eutload[f] / maxload_inter(i)

        self.processedData_Emission.setdefault(description, {})
        self.processedData_Emission[description]['PMaxRec'] = {}
        self.processedData_Emission[description]['PAveRec'] = {}
        self.processedData_Emission[description]['PRad_from_CCF'] = {}
        self.processedData_Emission[description]['PRad_from_CLF'] = {}
        self.processedData_Emission[description]['ERad_from_CCF'] = {}
        self.processedData_Emission[description]['ERad_from_CLF'] = {}
        self.processedData_Emission[description]['PRad_noise'] = {}
        self.processedData_Emission[description]['ERad_noise'] = {}
        self.processedData_Emission[description]['Asumed_Directivity'] = {}
        self.processedData_Emission[description]['Gmax_Model'] = gmax_model
        self.processedData_Emission[description]['Assumed_hg'] = hg
        self.processedData_Emission[description]['Assumed_RH'] = RH
        self.processedData_Emission[description]['Asumed_Distance'] = Quantity(METER, distance)
        self.processedData_Emission[description]['RelLoading'] = relload.copy()

        for i, f in enumerate(freqs):
            if callable(directivity):
                dmax_f = directivity(f)
            self.processedData_Emission[description]['Asumed_Directivity'][f] = Quantity(POWERRATIO, dmax_f)
            i = freqs.index(f)
            tees = list(pref[f].keys())
            prees = list(pref[f][tees[0]].keys())
            tees.sort()
            prees.sort()
            ntees = len(tees)
            nprees = len(prees)

            npr = noise[f][tees[0]][prees[0]][0]  # ['value'].convert(umddevice.UMD_W)
            # npr = npr.mag()
            npr = npr * etaTx_inter(i) / ccf_inter(i)
            # npr = npr.convert(umddevice.UMD_W)
            gmax_f = gmax(f, s=distance, hg=hg, RH=RH)
            # print gmax_f['h'], gmax_f['v']
            gm = max(gmax_f['h'], gmax_f['v'])
            neccf_v = numpy.sqrt(dmax_f * npr * 30) * gm
            # neccf_u = math.sqrt(dmax_f*npr.get_u()*30)*gm
            # print dmax_f*npr.get_l()*30
            # neccf_l = math.sqrt(max(0,dmax_f*npr.get_l()*30))*gm
            nERad = neccf_v
            self.processedData_Emission[description]['PRad_noise'][f] = npr
            self.processedData_Emission[description]['ERad_noise'][f] = nERad

            PMaxRecL = {}
            PAveRecL = {}
            PRadCCFL = {}
            PRadCLFL = {}
            ERadCCFL = {}
            ERadCLFL = {}
            for p in prees:
                PMaxRec = Quantity(WATT, 0.0)
                PAveRec = Quantity(WATT, 0.0)
                RecCounter = 0
                for t in tees:
                    for k in range(len(pref[f][t][p])):
                        pr = pref[f][t][p][k]  # ['value'].convert(umddevice.UMD_W)
                        # pr = pr.mag()
                        PMaxRec = max(PMaxRec, pr)
                        PAveRec += pr
                        RecCounter += 1
                PAveRec /= RecCounter
                PMaxRecL[p] = PMaxRec
                PAveRecL[p] = PAveRec  # for each receive antenna pos: Max and Av over tuner positions
                PRadCCFL[p] = PAveRec * etaTx_inter(i) / ccf_inter(i)
                PRadCLFL[p] = PMaxRec * etaTx_inter(i) / (clf_inter(i) * il_inter(i))
                prccf = PRadCCFL[p]  # .convert(umddevice.UMD_W)
                prclf = PRadCLFL[p]  # .convert(umddevice.UMD_W)
                eccf_v = numpy.sqrt(dmax_f * prccf * 30) * gm
                # eccf_u = math.sqrt(dmax_f*prccf.get_u()*30)*gm
                # eccf_l = math.sqrt(max(0,dmax_f*prccf.get_l()*30))*gm
                ERadCCFL[p] = eccf_v
                eclf_v = numpy.sqrt(dmax_f * prclf * 30) * gm
                # eclf_u = math.sqrt(dmax_f*prclf.get_u()*30)*gm
                # eclf_l = math.sqrt(max(0,dmax_f*prclf.get_l()*30))*gm
                ERadCLFL[p] = eclf_v

            self.processedData_Emission[description]['PMaxRec'][f] = PMaxRecL.copy()
            self.processedData_Emission[description]['PAveRec'][f] = PAveRecL.copy()
            self.processedData_Emission[description]['PRad_from_CCF'][f] = PRadCCFL.copy()
            self.processedData_Emission[description]['PRad_from_CLF'][f] = PRadCLFL.copy()
            self.processedData_Emission[description]['ERad_from_CCF'][f] = ERadCCFL.copy()
            self.processedData_Emission[description]['ERad_from_CLF'][f] = ERadCLFL.copy()

        self.messenger(util.tstamp() + " End of evaluation of emission measurement", [])
        return 0

    def Evaluate_Immunity(self,
                          description="EUT",
                          empty_cal="empty",
                          loaded_cal="loaded",
                          EUT_cal="EUT",
                          EUT_OK=None,
                          interpolation='linxliny'):
        self.messenger(util.tstamp() + " Start of evaluation of immunity measurement with description %s" % description,
                       [])
        if description not in self.rawData_Immunity:
            self.messenger(util.tstamp() + " Description %s not found." % description, [])
            return -1
        if empty_cal not in self.rawData_MainCal:
            self.messenger(util.tstamp() + " Empty chamber cal not found. Description: %s" % empty_cal, [])
            return -1
        if loaded_cal not in self.rawData_MainCal:
            self.messenger(util.tstamp() + " Loaded chamber cal not found. Description: %s" % loaded_cal, [])
            return -1
        if EUT_cal not in self.rawData_EUTCal:
            self.messenger(util.tstamp() + " WARNING: EUT cal not found. Description: %s" % EUT_cal, [])
            EUT_cal = None

        if EUT_OK is None:
            EUT_OK = self.std_eut_status_checker

        # zeroPR = Quantity (POWERRATIO, 0.0)

        testfield_from_pfwd = TestField(self, maincal=empty_cal, eutcal=EUT_cal)

        pref = self.rawData_Immunity[description]['pref']
        eut = self.rawData_Immunity[description]['eutstatus']
        freqs = list(pref.keys())
        freqs.sort()

        # check loading
        empty_loaded = empty_cal + ',' + loaded_cal
        if empty_loaded not in self.processedData_MainCal:
            self.CalculateLoading_MainCal(empty_cal=empty_cal, loaded_cal=loaded_cal)
        maxload = self.processedData_MainCal[empty_loaded]['Loading']
        maxload_inter = util.InterpolateMResults([maxload[_f] for _f in freqs], freqs, interpolation)

        relload = {}
        if EUT_cal:
            empty_eut = empty_cal + ',' + EUT_cal
            if empty_eut not in self.processedData_EUTCal:
                self.CalculateLoading_EUTCal(empty_cal=empty_cal, eut_cal=EUT_cal, freqs=freqs)
            eutload = self.processedData_EUTCal[empty_eut]['Loading']
            eutload_inter = util.InterpolateMResults([eutload[_f] for _f in freqs], freqs, interpolation)
            # clf = self.processedData_EUTCal[EUT_cal]['CLF']
            # clf_inter = umdutil.InterpolateMResults(clf, freqs, interpolation)
            for f in freqs:
                relload[f] = eutload_inter(f) / maxload_inter(f)

        self.processedData_Immunity.setdefault(description, {})
        self.processedData_Immunity[description]['PMaxRec'] = {}
        self.processedData_Immunity[description]['PAveRec'] = {}
        self.processedData_Immunity[description]['RelLoading'] = relload.copy()
        self.processedData_Immunity[description]['EUTImmunityThreshold'] = {}

        for i, f in enumerate(freqs):
            tees = list(pref[f].keys())
            prees = list(pref[f][tees[0]].keys())
            tees.sort()
            prees.sort()

            ntees = len(tees)
            nprees = len(prees)

            PMaxRecL = {}
            PAveRecL = {}
            for p in prees:
                PMaxRec = Quantity(WATT, 0.0)
                PAveRec = Quantity(WATT, 0.0)
                RecCounter = 0
                for t in tees:
                    for val in pref[f][t][p]:
                        pr = val['value']  # .convert(umddevice.UMD_W)
                        # pr = pr.mag()
                        PMaxRec = max(PMaxRec, pr)
                        PAveRec += pr
                        RecCounter += 1
                PAveRec /= RecCounter
                PMaxRecL[p] = PMaxRec
                PAveRecL[p] = PAveRec  # for each receive antenna pos: Max and Av over tuner positions

            self.processedData_Immunity[description]['PMaxRec'][f] = PMaxRecL.copy()
            self.processedData_Immunity[description]['PAveRec'][f] = PAveRecL.copy()

        eutfreqs = list(eut.keys())
        eutfreqs.sort()
        for f in eutfreqs:
            thres = []
            tees = list(eut[f].keys())
            tees.sort()
            real_tf = None
            for t in tees:
                pees = list(eut[f][t].keys())
                pees.sort()
                for p in pees:
                    for val in eut[f][t][p]:
                        try:
                            eutstat = val['value']
                            testfield = val['testfield']
                            pfwd = val['pfwd']
                            real_tf = testfield_from_pfwd(f, pfwd)
                            if not EUT_OK(eutstat):
                                thres.append({'TestField': testfield, 'Field from Pfwd': real_tf, 'EUT': eutstat})
                        except:
                            raise
            if not len(thres):
                thres.append({'TestField': testfield, 'Field from Pfwd': real_tf, 'EUT': 'Maximum testfield reached'})

            self.processedData_Immunity[description]['EUTImmunityThreshold'][f] = thres[:]

        self.messenger(util.tstamp() + " End of evaluation of Immunity measurement", [])
        return 0

    @staticmethod
    def stdTPosCmp(t1, t2):
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
        return cmp(d1, d2)

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
        self.messenger(
            util.tstamp() + " Start of evaluation of autocorrelation measurement with description %s" % description, [])
        if description not in self.rawData_AutoCorr:
            self.messenger(util.tstamp() + " Description %s not found." % description, [])
            return -1
        self.processedData_AutoCorr.setdefault(description, {})

        efields = self.rawData_AutoCorr[description]['efield']
        tpos = self.rawData_AutoCorr[description]['tpos']
        tpos.sort(self.TPosCmp)  # possibly plug in other cmp routine
        freqs = list(efields.keys())
        freqs.sort()

        if 'DistributuionOfr' not in skip:
            self.messenger(util.tstamp() + " Calculating pdf and cdf of the autocorrelation coefficient ...", [])
            r, psi, cpsi = util.CalcPsi(len(tpos), rho)
            self.messenger(util.tstamp() + " ... done.", [])
            self.processedData_AutoCorr[description]['DistributuionOfr'] = {}
            self.processedData_AutoCorr[description]['DistributuionOfr']['n'] = len(tpos)
            self.processedData_AutoCorr[description]['DistributuionOfr']['r'] = r[:]
            self.processedData_AutoCorr[description]['DistributuionOfr']['pdf'] = psi[:]
            self.processedData_AutoCorr[description]['DistributuionOfr']['cdf'] = cpsi[:]
            self.processedData_AutoCorr[description]['DistributuionOfr']['rho'] = rho
            self.messenger(util.tstamp() + " Calculating critical limit of the autocorelation coeficient rho0 ...", [])
            rho0 = util.CalcRho0(r, cpsi, alpha)
            self.processedData_AutoCorr[description]['DistributuionOfr']['rho0'] = rho0[alpha]
            self.messenger(util.tstamp() + " ...done.", [])
            self.messenger(util.tstamp() + " N=%d, alpha=%f, rho0=%f" % (len(tpos), alpha, rho0[alpha]), [])

        self.processedData_AutoCorr[description]['TunerPositions'] = tpos[:]
        if not 'AutoCorrelation' in skip:
            self.processedData_AutoCorr[description]['AutoCorrelation'] = {}
        if not 'NIndependentBoundaries' in skip:
            self.processedData_AutoCorr[description]['NIndependentBoundaries'] = {}
        if 'Statistic' not in skip:
            # rpy.r.library('ctest')
            ray = distributions.RayleighDist()  # this is scipy.stats.rayleigh()
            self.processedData_AutoCorr[description]['Statistic'] = {}
        # for _i, f in [_i__f for _i__f in enumerate(freqs) if not (_i__f[0] + offset) % every]:
        for f in freqs[offset::every]:
            try:
                lagf = lag(f)  # lag defaults to None, but might be a function returning lag(f) or a const value
            except TypeError:  # not callable
                lagf = lag
            if 'AutoCorrelation' not in skip:
                self.messenger(util.tstamp() + " Calculating autocorrelation f = %e" % f, [])
                self.processedData_AutoCorr[description]['AutoCorrelation'][f] = {}
                ac_f = self.processedData_AutoCorr[description]['AutoCorrelation'][f]
                pees = efields[f][str(tpos[0])].keys()
                for p in pees:
                    self.messenger(util.tstamp() + " p = %d" % p, [])
                    ac_f[p] = {}
                    for k, _e in enumerate(efields[f][str(tpos[0])][p][0]['value']):
                        self.messenger(util.tstamp() + " k = %d" % k, [])
                        ees = []
                        for t in tpos:
                            ees.append(efields[f][str(t)][p][0]['value'][k])
                        self.messenger(util.tstamp() + " Calculating autocorrelation ...", [])
                        r = correlation.autocorr(ees, lagf, cyclic=True)
                        self.messenger(util.tstamp() + " ...done", [])
                        ac_f[p][k] = r[:]
                self.messenger(util.tstamp() + " ...done", [])
            if 'NIndependentBoundaries' not in skip:
                self.messenger(util.tstamp() + " Calculating Number of Independent Boundaries f = %e" % f, [])
                self.processedData_AutoCorr[description]['NIndependentBoundaries'][f] = {}
                ac_f = self.processedData_AutoCorr[description]['AutoCorrelation'][f]
                nib_f = self.processedData_AutoCorr[description]['NIndependentBoundaries'][f]
                pees = efields[f][str(tpos[0])].keys()
                for p in pees:
                    self.messenger(util.tstamp() + " p = %d" % p, [])
                    nib_f[p] = {}
                    for k, _e in enumerate(efields[f][str(tpos[0])][p][0]['value']):
                        self.messenger(util.tstamp() + " k = %d" % k, [])
                        nib_f[p][k] = None
                        for i, _v in enumerate(ac_f[p][k]):
                            ri = _v
                            if ri < rho0[alpha]:
                                # interpolation
                                m = ri - ac_f[p][k][i - 1]  # .get_v()  # i=0 can not happen
                                b = ri - m * i
                                try:
                                    iinter = (rho0[alpha] - b) / m
                                except ZeroDivisionError:
                                    iinter = 1.0 * i
                                nib_f[p][k] = len(
                                    tpos) / iinter  # division by zero can not happen because r[i] = 1 and rho0<=1
                                # print f*1.0,p,k,r[i]*1.0,i,nib_f[p][k]
                                self.messenger(util.tstamp() + " f=%e, p=%d, k=%d, r=%s, lag=%f, Nindependent=%f" % (
                                    f * 1.0, p, k, str(_v), iinter, nib_f[p][k]), [])
                                break
                self.messenger(util.tstamp() + " ...done", [])
            if 'Statistic' not in skip:
                self.messenger(util.tstamp() + " Calculating statistic f = %e" % f, [])
                self.processedData_AutoCorr[description]['Statistic'][f] = {}
                s_f = self.processedData_AutoCorr[description]['Statistic'][f]
                ees24 = {}  # 24 = 8 positions x 3 axis
                pees = efields[f][str(tpos[0])].keys()
                for p in pees:
                    self.messenger(util.tstamp() + " p = %d" % p, [])
                    s_f[p] = {}
                    for k, _e in enumerate(efields[f][str(tpos[0])][p][0]['value']):
                        self.messenger(util.tstamp() + " k = %d" % k, [])
                        # now, we have to redure the data set according the result of the autocorr evaluation
                        ntotal = len(tpos)
                        try:
                            n_ind = self.processedData_AutoCorr[description]['NIndependentBoundaries'][f][p][k]
                        except (KeyError, IndexError):
                            self.messenger(
                                util.tstamp() + " WARNING: No of independent boundaries not found. Using all boundaries.",
                                [])
                            n_ind = ntotal  # fall back
                        # use autocor information
                        posidx = spacing.idxset(int(n_ind), len(tpos))
                        ees = []
                        for i, t in enumerate(tpos):
                            evalue = efields[f][str(t)][p][0]['value'][k]  # .convert(umddevice.UMD_Voverm).get_v()
                            ees24.setdefault(str(t), []).append(evalue)
                            if i in posidx:
                                ees.append(evalue)
                        ees.sort()  # values only, no ebars, unit is V/m
                        s_f[p][k] = {}
                        ss = s_f[p][k]
                        ss['n'] = n_ind
                        hist, bins, e_cdf, ray_fit, p_cs, p_ks = test_for_rayleigh(ees)
                        ss['hist'] = (hist, bins)
                        ss['samples'] = ees[:]
                        ss['ecdf'] = e_cdf(ees)[:]
                        ss['fitted_shape'] = ray_fit.scale
                        ss['cdf-fit'] = ray_fit.cdf(ees)
                        ss['p-chisquare'] = p_cs
                        ss['p-KS'] = p_ks
                        #
                        # try different:
                        # not based on autocorelation estimate for n_ind
                        # -> just try for every number of tuner positions
                        #
                        ss['p-values_disttest'] = {}
                        for n_ind in range(len(tpos), 2, -1):
                            posidx = spacing.idxset(n_ind, len(tpos))
                            ees = []
                            for i, t in enumerate(tpos):
                                if i in posidx:
                                    ees.append(efields[f][str(t)][p][0]['value'][k])
                            ees.sort()  # values only, no ebars, unit is V/m
                            hist, bins, e_cdf, ray_fit, p_cs, p_ks = test_for_rayleigh(ees)
                            ss['p-values_disttest'][n_ind] = {'chisq': p_cs, 'KS': p_ks}
                            # print(n_ind + 1, p_cs, p_ks)
                            if p_cs > 0.05 and p_ks > 0.05:  # has to be tested; KS seems to be more reliable
                                self.messenger(util.tstamp() + " Nind: %d p_cs: %f p_ks: %f"%(n_ind + 1, p_cs, p_ks))
                                break
                        ss['hist_disttest'] = (hist, bins)
                        ss['samples_disttest'] = ees[:]
                        ss['ecdf_disttest'] = e_cdf(ees)[:]
                        ss['fitted_shape_disttest'] = ray_fit.scale
                        ss['cdf-fit_disttest'] = ray_fit.cdf(ees)
                        ss['p-chisquare_disttest'] = p_cs
                        ss['p-KS_disttest'] = p_ks

                        self.messenger(
                            util.tstamp() + " f=%e, p_ks=%d, p_cs=%d, p_ks_disttest=%e, p_chi2-disttest=%e" % (
                                f * 1.0, ss['p-KS'], ss['p-chisquare'], ss['p-KS_disttest'],
                                ss['p-chisquare_disttest']), [])
                        # now we try with all 24 e-field vals for one freq
                ss = s_f[0][0]
                ss['p-values_disttest24'] = {}
                for n_ind in range(len(tpos), 2, -1):
                    posidx = spacing.idxset(n_ind, len(tpos))
                    ees = []
                    for i, t in enumerate(tpos):
                        if i in posidx:
                            ees.extend(ees24[str(t)])
                    ees.sort()  # values only, no ebars, unit is V/m
                    hist, bins, e_cdf, ray_fit, p_cs, p_ks = test_for_rayleigh(ees)
                    ss['p-values_disttest24'][n_ind] = {'chisq': p_cs, 'KS': p_ks}
                    # print(n_ind + 1, p_cs, p_ks)
                    if p_cs > 0.05 and p_ks > 0.05:  # has to be tested; KS seems to be more reliable
                        self.messenger(util.tstamp() + " Nind: %d p_cs: %f p_ks: %f"%(n_ind + 1, p_cs, p_ks))
                        break
                ss['hist_disttest24'] = (hist, bins)
                ss['samples_disttest24'] = ees[:]
                ss['ecdf_disttest24'] = e_cdf(ees)[:]
                ss['fitted_shape_disttest24'] = ray_fit.scale
                ss['cdf-fit_disttest24'] = ray_fit.cdf(ees)
                ss['p-chisquare_disttest24'] = p_cs
                ss['p-KS_disttest24'] = p_ks
                self.messenger(util.tstamp() + " f=%e, p_ks_disttest24=%e, p_chi2-disttest24=%e" % (
                    f * 1.0, ss['p-KS_disttest24'], ss['p-chisquare_disttest24']), [])

                self.messenger(util.tstamp() + " ...done", [])

        self.messenger(util.tstamp() + " End of evaluation of autocorrelation measurement", [])
        return 0

    def Evaluate_EUTCal(self, description="EUT", calibration="empty"):
        self.messenger(util.tstamp() + " Start of evaluation of EUT calibration with description %s" % description, [])
        if description not in self.rawData_EUTCal:
            self.messenger(util.tstamp() + " Description %s not found." % description, [])
            return -1
        if calibration not in self.rawData_MainCal:
            self.messenger(util.tstamp() + " Calibration %s not found." % calibration, [])
            return -1

        # zeroPR = Quantity(POWERRATIO, 0.0)
        # zeroVm = Quantity(EFIELD, 0.0)
        # Quantity(EFIELDPNORM,0.0) = Quantity (EFIELDPNORM, 0.0)

        efields = self.rawData_EUTCal[description]['efield']
        pref = self.rawData_EUTCal[description]['pref']
        noise = self.rawData_EUTCal[description]['noise']
        freqs = list(pref.keys())
        freqs.sort()

        self.processedData_EUTCal.setdefault(description, {})
        self.processedData_EUTCal[description]['PMaxRec'] = {}
        self.processedData_EUTCal[description]['PAveRec'] = {}
        self.processedData_EUTCal[description]['PInputForEField'] = {}
        self.processedData_EUTCal[description]['PInputForRecAnt'] = {}
        self.processedData_EUTCal[description]['PInputVarationForEField'] = {}
        self.processedData_EUTCal[description]['PInputVarationForRecAnt'] = {}
        self.processedData_EUTCal[description]['CCF'] = {}
        self.processedData_EUTCal[description]['CLF'] = {}
        self.processedData_EUTCal[description]['CCF_from_PMaxRec'] = {}
        self.processedData_EUTCal[description]['CLF_from_PMaxRec'] = {}
        self.processedData_EUTCal[description]['EMax'] = {}
        self.processedData_EUTCal[description]['Enorm'] = {}
        self.processedData_EUTCal[description]['EnormAveXYZ'] = {}
        self.processedData_EUTCal[description]['EnormAve'] = {}
        self.processedData_EUTCal[description]['SigmaXYZ'] = {}
        self.processedData_EUTCal[description]['Sigma24'] = {}
        self.processedData_EUTCal[description]['SigmaXYZ_dB'] = {}
        self.processedData_EUTCal[description]['Sigma24_dB'] = {}
        for f in freqs:
            tees = list(pref[f].keys())
            pees = []
            if f in efields:
                pees = list(efields[f][tees[0]].keys())
            prees = list(pref[f][tees[0]].keys())
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
                EMax = [Quantity(EFIELD, 0.0) for k in (0, 1, 2)]
                PInput = Quantity(WATT, 0.0)
                PInputMin = Quantity(WATT, 1.0e10)
                PInputMax = Quantity(WATT, 0.0)
                InCounter = 0
                for t in tees:
                    for i in range(len(efields[f][t][p])):
                        ef = efields[f][t][p][i]['value']
                        for k in range(3):
                            EMax[k] = max(EMax[k], ef[k])
                        pf = efields[f][t][p][i]['pfwd']
                        # pf = pf.mag()
                        PInputMin = min(PInputMin, pf)
                        PInputMax = max(PInputMax, pf)
                        PInput += pf
                        InCounter += 1
                EMaxL[p] = EMax  # for each probe pos: Max over tuner positions
                PInput /= InCounter
                PInputVariation = PInputMax / PInputMin
                PInputEL[p] = PInput
                PInputVariationEL[p] = PInputVariation

            PMaxRecL = {}
            PAveRecL = {}
            PInputAL = {}
            PInputVariationAL = {}
            for p in prees:
                PMaxRec = Quantity(WATT, 0.0)
                PAveRec = Quantity(WATT, 0.0)
                RecCounter = 0
                PInput = Quantity(WATT, 0.0)
                PInputMin = Quantity(WATT, 1.0e10)
                PInputMax = Quantity(WATT, 0.0)
                InCounter = 0
                for t in tees:
                    for i in range(len(pref[f][t][p])):
                        pr = pref[f][t][p][i]['value']
                        # pr = pr.mag()
                        PMaxRec = max(PMaxRec, pr)
                        PAveRec += pr
                        RecCounter += 1
                        pf = pref[f][t][p][i]['pfwd']
                        # pf = pf.mag()
                        PInputMin = min(PInputMin, pf)
                        PInputMax = max(PInputMax, pf)
                        PInput += pf
                        InCounter += 1
                PAveRec /= RecCounter
                PMaxRecL[p] = PMaxRec
                PAveRecL[p] = PAveRec  # for each receive antenna pos: Max and Av over tuner positions
                PInput /= InCounter
                PInputVariation = PInputMax / PInputMin
                PInputAL[p] = PInput
                PInputVariationAL[p] = PInputVariation

            self.processedData_EUTCal[description]['PMaxRec'][f] = PMaxRecL.copy()
            self.processedData_EUTCal[description]['PAveRec'][f] = PAveRecL.copy()
            self.processedData_EUTCal[description]['PInputForEField'][f] = PInputEL.copy()
            self.processedData_EUTCal[description]['PInputForRecAnt'][f] = PInputAL.copy()
            self.processedData_EUTCal[description]['PInputVarationForEField'][f] = PInputVariationEL.copy()
            self.processedData_EUTCal[description]['PInputVarationForRecAnt'][f] = PInputVariationAL.copy()
            self.processedData_EUTCal[description]['EMax'][f] = EMaxL.copy()

            # calc CCF and CCF_from_PMaxRec
            CCF_from_PMaxRec = Quantity(POWERRATIO, 0.0)
            for pos, Pmax in list(PMaxRecL.items()):
                CCF_from_PMaxRec += Pmax / PInputAL[pos]
            CCF_from_PMaxRec /= len(list(PMaxRecL.keys()))
            CCF = Quantity(POWERRATIO, 0.0)
            for pos, Pav in list(PAveRecL.items()):
                CCF += Pav / PInputAL[pos]
            CCF /= len(list(PAveRecL.keys()))
            self.processedData_EUTCal[description]['CCF_from_PMaxRec'][f] = CCF_from_PMaxRec
            self.processedData_EUTCal[description]['CCF'][f] = CCF

            if npees > 0:
                Avxyz = [Quantity(EFIELDPNORM, 0.0)] * 3
                self.processedData_EUTCal[description]['Enorm'][f] = {}
                for pos, Em in list(EMaxL.items()):
                    pin = self.processedData_EUTCal[description]['PInputForEField'][f][pos]
                    v = pin  # .get_v()
                    sqrtv = numpy.sqrt(v)
                    # u = pin.get_u()
                    # l = pin.get_l()
                    sqrtPInput = sqrtv
                    en = []
                    for k, em in enumerate(Em):
                        en.append(em / sqrtPInput)
                        Avxyz[k] += em
                    self.processedData_EUTCal[description]['Enorm'][f][pos] = en
                Av24 = Quantity(EFIELDPNORM, 0.0)
                for k in range(3):
                    Avxyz[k] /= len(list(EMaxL.keys()))
                    Av24 += Avxyz[k]
                Av24 /= 3.0
                self.processedData_EUTCal[description]['EnormAveXYZ'][f] = Avxyz
                self.processedData_EUTCal[description]['EnormAve'][f] = Av24
                enorm = self.processedData_EUTCal[description]['Enorm'][f]
                Sxyz = []
                list24 = []
                for k in range(3):
                    lst = [enorm[p][k] for p in list(enorm.keys())]
                    list24 += lst
                    S = util.CalcSigma(lst, Avxyz[k])
                    try:
                        Sxyz.append(S)
                    except:
                        util.LogError(self.messenger)
                try:
                    S24 = util.CalcSigma(list24, Av24)
                except:
                    S24 = None

                self.processedData_EUTCal[description]['SigmaXYZ'][f] = Sxyz
                self.processedData_EUTCal[description]['Sigma24'][f] = S24
                SdBxyz = []
                for k in range(3):
                    try:
                        SdBxyz.append((20 * numpy.log10((Sxyz[k] + Avxyz[k]) / Avxyz[k])).eval())
                    except:
                        util.LogError(self.messenger)
                try:
                    SdB24 = (20 * (numpy.log10(S24 + Av24) / Av24)).eval()
                except:
                    SdB24 = None
                self.processedData_EUTCal[description]['SigmaXYZ_dB'][f] = SdBxyz
                self.processedData_EUTCal[description]['Sigma24_dB'][f] = SdB24
            else:  # no efield data available
                self.processedData_EUTCal[description]['Enorm'][f] = None
                self.processedData_EUTCal[description]['EnormAveXYZ'][f] = None
                self.processedData_EUTCal[description]['EnormAve'][f] = None
                self.processedData_EUTCal[description]['SigmaXYZ'][f] = None
                self.processedData_EUTCal[description]['Sigma24'][f] = None
                self.processedData_EUTCal[description]['SigmaXYZ_dB'][f] = None
                self.processedData_EUTCal[description]['Sigma24_dB'][f] = None

        acf = self.processedData_MainCal[calibration]['ACF']
        il = self.processedData_MainCal[calibration]['IL']
        ccf = self.processedData_EUTCal[description]['CCF']
        ccfPMax = self.processedData_EUTCal[description]['CCF_from_PMaxRec']
        self.processedData_EUTCal[description]['CLF'] = self.__CalcLoading(ccf, acf, freqs, 'linxliny')
        self.processedData_EUTCal[description]['CLF_from_PMaxRec'] = self.__CalcLoading(ccfPMax, il, freqs, 'linxliny')
        self.messenger(util.tstamp() + " End of evaluation of EUT calibration", [])
        return 0

    def CalculateLoading_MainCal(self, empty_cal='empty', loaded_cal='loaded', freqs=None, interpolation='linxliny'):
        """Calculate the chamber loading from processed data (MainCal)
        If freqs is None, freqs are taken fron first ACF and second ACF is interpolated
        Else both are interpolated
        """
        if (empty_cal not in self.processedData_MainCal) \
                or (loaded_cal not in self.processedData_MainCal):
            # one of the keys not present
            return -1
        des = str(empty_cal + ',' + loaded_cal)
        acf1 = self.processedData_MainCal[empty_cal]['ACF']
        acf2 = self.processedData_MainCal[loaded_cal]['ACF']
        self.processedData_MainCal.setdefault(des, {})
        self.processedData_MainCal[des]['Loading'] = self.__CalcLoading(acf1, acf2, freqs, interpolation)
        return 0

    def CalculateLoading_EUTCal(self, empty_cal='empty', eut_cal='EUT', freqs=None, interpolation='linxliny'):
        """Calculate the chamber loading from processed data (MainCal)
        If freqs is None, freqs are taken fron first ACF and second ACF is interpolated
        Else both are interpolated
        """
        if (empty_cal not in self.processedData_MainCal) \
                or (eut_cal not in self.processedData_EUTCal):
            # one of the keys not present
            return -1
        des = str(empty_cal + ',' + eut_cal)
        acf1 = self.processedData_MainCal[empty_cal]['ACF']
        acf2 = self.processedData_EUTCal[eut_cal]['CCF']
        self.processedData_EUTCal.setdefault(des, {})
        self.processedData_EUTCal[des]['Loading'] = self.__CalcLoading(acf1, acf2, freqs, interpolation)
        return 0

    def __CalcLoading(self, acf1, acf2, freqs, interpolation):
        """Calculate the chamber loading from processed data
        If freqs is None, freqs are taken fron first ACF and second ACF is interpolated
        Else both are interpolated
        """
        if freqs is None:
            freqs = list(acf1.keys())
        ldict = {}
        cf1 = util.MResult_Interpol(acf1, interpolation)
        cf2 = util.MResult_Interpol(acf2, interpolation)
        for f in freqs:
            loading = cf1(f) / cf2(f)
            ldict[f] = loading
        return ldict


class stdImmunityKernel:
    def __init__(self, field, tp, messenger, UIHandler, lcls, dwell, keylist='sS'):
        self.field = field
        self.tp = tp
        self.messenger = messenger
        self.UIHandler = UIHandler
        self.callerlocals = lcls
        try:
            self.in_as = self.callerlocals['in_as']
        except KeyError:
            self.in_as = {}
        self._testplan = self._makeTestPlan()
        self.dwell = dwell
        self.keylist = keylist

    def _makeTestPlan(self):
        ret = []
        freqs = list(self.tp.keys())
        freqs.sort()
        for f in freqs:
            has_f = f in self.in_as
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

    def test(self, stat):
        if stat == 'AmplifierProtectionError':
            # last command failed due to Amplifier Protection
            # look for 'LoopMarker' and continue there
            while True:
                cmd = self._testplan.pop()
                if cmd[0] in ('LoopMarker', 'finished'):
                    break
        else:
            cmd = self._testplan.pop()

        # overread LoopMarker
        while cmd[0] == 'LoopMarker':
            cmd = self._testplan.pop()

        if cmd[0] == 'eut':
            start = time.time()
            intervall = 0.01
            while (time.time() - start < self.dwell):
                key = util.anykeyevent()
                if (0 <= key <= 255) and chr(key) in self.keylist:
                    cmd = ('eut', 'User event.', {'eutstatus': 'Marked by user'})
                    break

                time.sleep(intervall)
                cmd = ('eut', '', {'eutstatus': 'OK'})
        return cmd


class TestField:
    def __init__(self, instance, maincal='empty', eutcal=None):
        self.fail = False
        if maincal not in instance.processedData_MainCal:
            self.fail = True
        if eutcal and eutcal not in instance.rawData_EUTCal:
            self.fail = True
        self.Enorm = util.MResult_Interpol(instance.processedData_MainCal[maincal]['EnormAve'].copy())
        try:
            self.clf = util.MResult_Interpol(instance.processedData_EUTCal[eutcal]['CLF'].copy())
        except:
            self.clf = (lambda _f: Quantity(POWERRATIO, 1.0))

    def __call__(self, f=None, power=None):
        if f is None:
            return None
        if power is None:
            return None
        # try:
        #    power = power.convert(umddevice.UMD_W)
        # except:
        #    power = umddevice.UMDMResult(power,umddevice.UMD_W)
        # power = power.mag()
        # power.unit=umddevice.UMD_dimensionless   # sqrt(W) is not implemented yet
        enorm = self.Enorm(f)  # .convert(umddevice.UMD_VovermoversqrtW)
        # enorm.unit=umddevice.UMD_dimensionless
        clf = self.clf(f)  # .convert(umddevice.UMD_powerratio)
        # print power
        # print clf
        # print enorm
        etest2 = power * clf * enorm * enorm
        etest_v = numpy.sqrt(etest2)
        # dp = 0.5*(power.get_u()-power.get_l())
        # dc = 0.5*(clf.get_u()-clf.get_l())
        # de = 0.5*(enorm.get_u()-enorm.get_l())
        # TODO: Check for ZeroDivision Error
        # try:
        #    det = math.sqrt((0.5*math.sqrt(clf.get_v()/power.get_v())*enorm.get_v()*dp)**2
        #                +(0.5*math.sqrt(power.get_v()/clf.get_v())*enorm.get_v()*dc)**2
        #                +(math.sqrt(power.get_v()*clf.get_v()*de))**2)
        # except ZeroDivisionError:
        #    det = 0.0
        # etest_u=etest_v+det
        # etest_l=etest_v-det
        return etest_v


class TestPower:
    def __init__(self, instance, maincal='empty', eutcal=None):
        self.fail = False
        self.instance = instance
        if maincal not in instance.processedData_MainCal:
            self.fail = True
        if eutcal and eutcal not in instance.rawData_EUTCal:
            self.fail = True
        self.Enorm = util.MResult_Interpol(instance.processedData_MainCal[maincal]['EnormAve'].copy())
        try:
            self.clf = util.MResult_Interpol(instance.processedData_EUTCal[eutcal]['CLF'].copy())
        except:
            self.clf = (lambda _f: Quantity(POWERRATIO, 1.0))

    def __call__(self, f=None, etest=None):
        if f is None:
            return None
        if etest is None:
            return None
        try:
            etest = etest()
        except TypeError:
            pass
        # try:
        #    etest = etest.convert(umddevice.UMD_Voverm)
        # except AttributeError:
        #    etest = umddevice.UMDMResult(etest,umddevice.UMD_Voverm)
        # etest.unit=umddevice.UMD_dimensionless   # (V/m)**2 is not implemented yet
        enorm = self.Enorm(f)  # .convert(umddevice.UMD_VovermoversqrtW)
        clf = self.clf(f)  # .convert(umddevice.UMD_powerratio)
        # self.instance.messenger("DEBUG TestPower: f: %e, etest: %r, enorm: %r, clf: %r"%(f,etest,enorm,clf), [])
        # enorm.unit=umddevice.UMD_dimensionless
        E = etest  # .get_v()
        e = enorm  # .get_v()
        c = clf  # .get_v()
        power_v = (E / e) ** 2 / c

        # dE = 0.5*(etest.get_u()-etest.get_l())
        # dc = 0.5*(clf.get_u()-clf.get_l())
        # de = 0.5*(enorm.get_u()-enorm.get_l())

        # dp = E/(e*c) * math.sqrt((2*dE/e)**2
        #                       + (2*E*de/(e*e))**2
        #                       + (E*dc/(e*math.sqrt(c)))**2)            
        power = power_v
        # self.instance.messenger("DEBUG TestPower: f: %e, power: %r"%(f,power), [])
        return power
