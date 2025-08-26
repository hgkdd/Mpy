# -*- coding: utf-8 -*-
"""This is :mod:`mpylab.env.tem.TEMCell`.

   Provides :class:`mpylab.env.tem.TEMCell` for EMC measurements in TEM cells

   :author: Hans Georg Krauthäuser (main author)
   :copyright: All rights reserved
   :license: no licence yet
"""

import math
import time
import sys

import scipy
import scipy.special
# import pprint

from scuq.quantities import Quantity
from scuq.si import METER, OHM, WATT, SECOND, VOLT
from scuq.ucomponents import Context

from mpylab.env import Measure
from mpylab.tools import util, mgraph, interpol
from mpylab.tools.aunits import POWERRATIO, EFIELD
from mpylab.tools.log_freq import LogFreq


# from mpylab.tools.aunits import *


class TEMCell(Measure.Measure):
    """A class for TEM-cell measurements according to IEC 61000-4-20
    """
    eut_positions_emission = (("xx'yy'zz'", "xz'yx'zy'", "xy'yz'zx'"),
                              ("xz'yy'z(-x')", "x(-x')yz'zy'", "xy'y(-x')zz'"),
                              ("x(-x')yy'z(-z')", "x(-z')y(-x')zy'", "xy'y(-z')z(-x')"),
                              ("x(-z')yy'zx'", "xx'y(-z')zy'", "xy'yx'z(-z')"))

    eut_positions_immunity = {'v': ("xx'yy'zz'", "xz'yy'z(-x')", "x(-x')yy'z(-z')", "x(-z')yy'zx'"),
                              'h': ("xy'y(-x')zz'", "xy'y(-z')z(-x')", "xy'yx'z(-z')", "xy'yz'zx'")}

    c0 = Quantity(METER / SECOND, 2.99792458e8)
    eta0 = Quantity(OHM, 120 * math.pi)
    # k_factor is used in homogeneous area check
    # IEC 61000-4-20 set this to 1.15 but it is 1.150349...
    # we use the exact value
    k_factor = scipy.stats.norm.isf((1 - 0.75) / 2)

    def __init__(self):
        super().__init__()
        self.asname = None
        self.ascmd = None
        self.autosave = False
        self.autosave_interval = 3600
        self.lastautosave = time.time()
        self.logger = [self.stdlogger]
        self.logfile = None
        self.logfilename = None
        self.messenger = self.stdUserMessenger
        self.UserInterruptTester = self.stdUserInterruptTester
        self.PreUserEvent = self.stdPreUserEvent
        self.PostUserEvent = self.stdPostUserEvent
        self.rawData_e0y = {}
        self.processedData_e0y = {}
        self.rawData_Immunity = {}
        self.processedData_Immunity = {}
        self.rawData_Emission = {}
        self.processedData_Emission = {}
        self.std_3_positions = TEMCell.eut_positions_emission[0]
        self.std_12_positions = util.flatten(TEMCell.eut_positions_emission)
        self.std_positions_immunity = TEMCell.eut_positions_immunity

    def __setstate__(self, dct):
        if dct['logfilename'] is None:
            logfile = None
        else:
            logfile = open(dct['logfilename'], "a+")
        self.__dict__.update(dct)
        self.logfile = logfile
        self.messenger = self.stdUserMessenger
        self.logger = [self.stdlogger]
        self.UserInterruptTester = self.stdUserInterruptTester
        self.PreUserEvent = self.stdPreUserEvent
        self.PostUserEvent = self.stdPostUserEvent
        # for 'old' pickle files
        if not hasattr(self, 'asname'):
            self.asname = None
            self.ascmd = None
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

    def _HandleUserInterrupt(self, dct, ignorelist=''):
        key = self.UserInterruptTester()
        if key and not chr(key) in ignorelist:
            # empty key buffer
            _k = self.UserInterruptTester()
            while _k is not None:
                _k = self.UserInterruptTester()

            mg = dct['mg']
            names = dct['names']
            f = dct['f']
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
                            level = self.setLevel(mg, names, SGLevel)
                        except Measure.AmplifierProtectionError as _e:
                            self.messenger(
                                util.tstamp() + " Can not set signal generator level. Amplifier protection raised with message: %s" % _e.message,
                                [])

                    # set frequency for all devices
                    (minf, maxf) = mg.SetFreq_Devices(f)
                    mg.EvaluateConditions()
                elif answer == but2.index('Quit'):
                    self.messenger(util.tstamp() + " measurment terminated by user.", [])
                    raise UserWarning  # to reach finally statement
            self.messenger(util.tstamp() + " RF On...", [])
            stat = mg.RFOn_Devices()  # switch on just before measure
            if hassg:
                level2 = self.doLeveling(leveling, mg, names, locals())
                if level2:
                    level = level2
            try:
                # wait delay seconds
                self.messenger(util.tstamp() + " Going to sleep for %d seconds ..." % delay, [])
                self.wait(delay, dct, self._HandleUserInterrupt)
                self.messenger(util.tstamp() + " ... back.", [])
            except Exception:
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
                          RH=(1, 4),
                          is_oats=None,
                          component='y',
                          evaluate3pos=None):
        """Calculate the maximum radiated e field from a TEM-cell emission measurement.

           Parameters:
           
              - *description*: String to identify the emission measurement.
              - *e0y_description*: Strind to identify the data for e0y factor.
              - *use_e0y_GTEManalytical*: if `True`, use the analytical formula, see :meth:`e0y_GTEM_analytical`
              - *EUTPos*: Dictionary with keys
                 
                 - 'cell_width'
                 - 'sep_height'
                 - 'gap'
                 - 'ypos'
                 - 'xpos'
                 
                that are passed to :meth:`e0y_GTEM_analytical`
              - *Zc*: characteristic impedance in Ohms
              - *Dmax*: the maximum of the direktivity of the EUT.
              - *s*: Distance from the EUT in meters
              - *hg*: height over ground plane in meters
              - *RH*: range of the hight scan in meters
              - *is_oats*: if `True`, a ground plane is assumed, else free space
              - *component*: the field component that represents the y direction (probe orientation could have been diffeent)
              - *evaluate3pos*: evaluate only with respect to the first 3 standard position even if more (12) are available

           The function simply calls :meth:`Calculate_Prad` and :meth:`Calculate_Emax` with the appropriate arguments.
        """
        self.messenger(
            util.tstamp() + " Starting evaluation of emission measurement for description '%s' ..." % description, [])
        if is_oats is None:
            is_oats = True
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
        # import pprint
        # pprint.pprint(self.processedData_Emission)
        self.messenger(
            util.tstamp() + " End of evaluation of emission measurement for description '%s'." % description, [])

    def Calculate_Prad(self,
                       description='EUT',
                       e0y_description='Main EUT Pos',
                       use_e0y_GTEManalytical=None,
                       EUTpos=None,
                       Zc=50,
                       component='y',
                       evaluate3pos=None):
        """Calculate the total radiated power from a TEM-cell emission measurement.

           Parameters:
           
              - *description*: String to identify the emission measurement.
              - *e0y_description*: Strind to identify the data for e0y factor.
              - *use_e0y_GTEManalytical*: if `True`, use the analytical formula, see :meth:`e0y_GTEM_analytical`
              - *EUTPos*: Dictionary with keys
                 
                 - 'cell_width'
                 - 'sep_height'
                 - 'gap'
                 - 'ypos'
                 - 'xpos'
                 
                that are passed to :meth:`e0y_GTEM_analytical`
              - *Zc*: characteristic impedance
              - *component*: the field component that represents the y direction (probe orientation could have been diffeent)
              - *evaluate3pos*: evaluate only with respect to the first 3 standard position even if more (12) are available

           The reslults are appended to *self.processedData_Emission[description]['Prad'][f][port]* (radiated power) and
           *self.processedData_Emission[description]['Prad_noise'][f][port]* (radiated noise).
        """
        self.messenger(
            util.tstamp() + " Starting calulation of radiated power for description '%s' ..." % description, [])
        Zc = Quantity(OHM, Zc)
        comp_dct = {'x': 0, 'y': 1, 'z': 2}
        component = component.lower()
        comp_index = comp_dct[component]
        if use_e0y_GTEManalytical:
            cell_width = EUTpos['cell_width']
            sep_height = EUTpos['sep_height']
            gap = EUTpos['gap']
            ypos = EUTpos['ypos']
            xpos = EUTpos['xpos']
            e0ygtem = self.e0y_GTEM_analytical(cell_width, sep_height, gap, ypos, x=xpos, Zc=Zc)

            def e0y(f):
                return e0ygtem
        else:
            ##          import pprint
            ##          pprint.pprint(self.processedData_e0y[e0y_description]['e0y'])
            e0y_xydict = {}
            e0ydata = self.processedData_e0y[e0y_description]['e0y']
            e0yfreqs = list(e0ydata.keys())
            e0yfreqs.sort()
            for e0yf in e0yfreqs:
                e0y_xydict[e0yf] = e0ydata[e0yf][0][0][comp_index]
            e0y = interpol.UQ_interpol(e0y_xydict)
        if not callable(e0y):
            self.messenger(util.tstamp() + " ERROR: e0y is not callable. Abording evaluation.", [])
            return None
        if description not in self.rawData_Emission:
            self.messenger(util.tstamp() + " ERROR: description '%s' not found. Abording evaluation." % description, [])
            return None

        try:
            self.processedData_Emission[description]
        except KeyError:
            self.processedData_Emission[description] = {}

        self.processedData_Emission[description]['Prad'] = {}
        self.processedData_Emission[description]['Prad_noise'] = {}

        voltages = self.rawData_Emission[description]['voltage']
        noise = self.rawData_Emission[description]['noise']
        freqs = list(voltages.keys())
        freqs.sort()
        for f in freqs:
            self.processedData_Emission[description]['Prad'][f] = {}
            self.processedData_Emission[description]['Prad_noise'][f] = {}
            ports = list(voltages[f].keys())
            ports.sort()
            for port in ports:
                self.processedData_Emission[description]['Prad'][f][port] = []
                self.processedData_Emission[description]['Prad_noise'][f][port] = []
                data = voltages[f][port]
                ndata = noise[f][port]
                # import pprint
                # pprint.pprint(data)
                positions = list(data.keys())
                # print positions
                for k in range(len(data[positions[0]])):
                    maxv = Quantity(VOLT, -1)
                    # find the max of all voltages
                    for p in positions:
                        # only the 3 first positions should be evaluated and this pos is different
                        if evaluate3pos and p not in self.std_3_positions:
                            continue
                        d = data[p][k]
                        vp = d['value']
                        op = vp._unit.get_operator_to(VOLT)
                        vp = op.convert(vp)
                        vp = abs(vp)
                        if vp > maxv:
                            maxv = vp
                            maxp = p  # maxp holt the indey of the position where the mx was
                    for triple in TEMCell.eut_positions_emission:
                        if maxp in triple:
                            # orth_v = [data[p][k] for p in triple] # the orthogonal positions to be used
                            break
                    self.messenger(util.tstamp() + "f=%e, Using positions '%r'" % (f, triple), [])

                    ctx = Context()  # context for the evaluation of uncertainties
                    s2 = Quantity(VOLT * VOLT, 0)  # S^2
                    nd = abs(ndata[0][k]['value'])  # noise data
                    ns2 = 3 * nd ** 2  # V1^2+v2^2+v3^2=3*V1^2
                    for p in triple:  # loop over positions orth to position with the max value
                        # print p, k, data[p][k]
                        d = abs(data[p][k]['value'])
                        s2 += (d * d)
                    # print ns2, s2
                    k2 = (2 * math.pi * f / TEMCell.c0) ** 2  # k^2
                    e0y2 = e0y(f) ** 2  # e_0y^2

                    fac = TEMCell.eta0 / (3 * math.pi * Zc) * k2 / e0y2
                    P0 = fac * s2  # Prad
                    nP0 = fac * ns2  # Pnoise

                    self.messenger(util.tstamp() + "f=%e, Prad: %s, Prad_noise: %s" % (f, P0, nP0), [])
                    self.processedData_Emission[description]['Prad'][f][port].append(P0)
                    self.processedData_Emission[description]['Prad_noise'][f][port].append(nP0)
        self.messenger(util.tstamp() + " Calulation of radiated power done.", [])

    def Calculate_Emax(self, description='EUT', Dmax=3.0, s=10, hg=0.8, RH=(1, 4), rstep=None, Zc=50, is_oats=True):
        """This function estimates the maximum E field strength, as it would be expected from a OATS/FAR measurement, 
           from the total radiated power determined by :meth:`Calculate_Prad`. 

           Parameters:

              - *description*: String to identify the emission measurement.
              - *Dmax*: the maximum of the direktivity of the EUT.
              - *s*: Distance from the EUT in meters
              - *hg*: height over ground plane in meters
              - *RH*: range of the hight scan in meters
              - *rstep*: the step width of the hight scan used to calculate the max. Used in :meth:`mpylab.tools.util.gmax_oats`
              - *Zc*: characteristic impedance of the TEM cell in Ohms (forwarded to :meth:`Calculate_Prad`)
              - *is_oats*: if `True`, a ground plane is assumed, else free space

        """
        self.messenger(
            util.tstamp() + " Starting calulation of maximum radiated E field for description '%s' ..." % (description),
            [])
        if is_oats is None:
            is_oats = True
        # print self.processedData_Emission.keys()
        if 'Prad' not in self.processedData_Emission[description]:
            self.Calculate_Prad(description=description, Zc=Zc)

        if not is_oats:
            gmax_f = util.gmax_fs
            gmax_model = "FAR"
        else:
            gmax_f = util.gmax_oats
            gmax_model = "OATS"

        self.processedData_Emission[description]['Assumed_Distance'] = Quantity(METER, s)
        self.processedData_Emission[description]['Gmax_Model'] = gmax_model
        self.processedData_Emission[description]['Assumed_hg'] = Quantity(METER, hg)
        self.processedData_Emission[description]['Assumed_RH'] = tuple((Quantity(METER, r) for r in RH))
        self.processedData_Emission[description]['Assumed_Zc'] = Quantity(OHM, Zc)
        self.processedData_Emission[description]['Assumed_Directivity'] = {}

        dmax_f = Dmax
        ext = ['', '_noise']
        for ex in ext:
            self.processedData_Emission[description]['Emax%s' % ex] = {}
            Emax = self.processedData_Emission[description]['Emax%s' % ex]
            prad = self.processedData_Emission[description]['Prad%s' % ex]
            freqs = sorted(prad)  # sorted keys of dict prad
            for f in freqs:
                if callable(Dmax):
                    dmax_f = Dmax(f)
                self.processedData_Emission[description]['Assumed_Directivity'].setdefault(f, dmax_f)
                gmf = gmax_f(f, rstep=rstep, s=s, hg=hg, RH=RH)
                gmax = {'h': Quantity(1 / METER, gmf['h']),
                        'v': Quantity(1 / METER, gmf['v'])}
                ports = sorted(prad[f])
                for port in ports:
                    Emax[f] = {}
                    for pr in prad[f][port]:  # pr is a Quantity in WATT
                        cc = math.sqrt(dmax_f * TEMCell.eta0 / (4 * math.pi) * pr)
                        Emax[f][port] = []
                        dct = {}
                        for _k, _val in list(gmax.items()):
                            dct[_k] = cc * _val
                        dct['total'] = max(dct['v'], dct['h'])
                        Emax[f][port].append(dct)
                        self.messenger(util.tstamp() + " f=%e, Emax%s=%s (horiz.) %s (vert.) %s (total)" % (
                            f, ex, dct['h'], dct['v'], dct['total']), [])
        self.messenger(util.tstamp() + " Calculation of maximum radiated E field done.", [])

    def e0y_GTEM_analytical(self, a, h, g, y, x=0, Zc=50, max_m=10):
        """Calculate the factor $e_{0y}$ from the analytical formula given in 
           IEC 61000-4-20 (actually, it is from the PhD thesis of Michael Koch).
           
           Parameters:
           
              - *a*: cell width in meter
              - *h*: septum height in meter
              - *g*: gap width in meter
              - *y*: position of the EUT center from the floor in meter
              - *x*: position of the EUT center from the middle in meter
              - *Zc*: characteristic impedance of the waveguide in ohms
              - *max_m*: upper index of the series expansion
           
           
           .. figure:: gtem_e0y.png
           
           Cross section of a GTEM-cell.
           
        """
        sum = 0.0
        for m in range(1, max_m + 1, 2):
            M = m * math.pi / a
            ch = math.cosh(M * y)
            c = math.cos(M * x)
            s = math.sin(M * a / 2.0)
            j0 = scipy.special.j0(M * g)
            sh = math.sinh(M * h)
            sum += ch * c * s * j0 / sh
            # print "m: %d, ch: %e, c: %e, s: %s, j0: %e, sh: %e, sum: %e"%(m, ch, c, s, j0, sh, sum)
        sum *= 4.0 * math.sqrt(Zc) / a
        return Quantity(VOLT / METER / WATT.sqrt(), sum)

    def Measure_TEMMode_FieldUniformity_Validation_ConstPower(self,
                                                              description="GTEM",
                                                              distance=None,
                                                              positions=None,
                                                              dotfile='gtem-immunity.dot',
                                                              delay=0.0,
                                                              leveling=None,
                                                              freqs=None,
                                                              fwd_dbm=None,
                                                              SearchPaths=None,
                                                              names=None):
        """
        Performs an TEM Mode and Field Uniformity validation measurement according to IEC 61000-4-20.
        Here: Constant fwd Power method.

        Parameter:

           - *description*: key to identify the measurement in the result dictionary
           - *distance*: position of the uniform area in mm. In GTEM: counted from feed point
           - *positions*: a sequence of probe positions to be measured. Each position is a (x,y)-pair of probe positions (in mm)
           - *dotfile*: forwarded to :class:`mpylab.tools.mgraph.MGraph` to create the mearsurement graph.
           - *delay*: time in seconds to wait after setting the frequency before pulling date from the instruments
           - *freqs*: sequence of frequencies in Hz to use for the measurements.
           - *fwd_dbm*: forward power at feed point in dbm
           - *names*: dict with the mapping from internal names to dot-file names.
        """
        if names is None:
            names = {'sg': 'sg',
                     'a1': 'a1',
                     'a2': 'a2',
                     'tem': 'gtem',
                     'pmfwd': 'pm1',
                     'pmbwd': 'pm2'
                     }
        self.PreUserEvent()

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

        if positions is None:
            positions = self.std_positions_immunity

        if self.autosave:
            self.messenger(util.tstamp() + " Resume TEMCell immunity measurement from autosave...", [])
        else:
            self.messenger(util.tstamp() + " Start new TEMCell immunity measurement...", [])

        self.rawData_Immunity.setdefault(description, {})

        mg = mgraph.MGraph(dotfile)
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
                _fg = LogFreq(80e6, 1000e6, 1.01, True)
                freqs = [f for f in LogFreq.logspace]

            # set up voltage, noise, ...
            voltage = {}
            # loop eut positions
            measured_eut_pos = []
            remain_eut_pos = list(positions)[:]
            while len(remain_eut_pos):
                msg = \
                    """
EUT measurement.
Switch EUT ON.
Select EUT position.

"""
                but = []
                for _i, _r in enumerate(remain_eut_pos):
                    msg += "%s: %s\n" % (util.map2singlechar(_i), str(_r))
                    but.append(str(_i))
                msg += "Quit: quit measurement."
                but.append("Quit")
                answer = self.messenger(msg, but)
                if answer == but.index('Quit'):
                    self.messenger(util.tstamp() + " measurement terminated by user.", [])
                    raise UserWarning  # to reach finally statement
                p = remain_eut_pos[answer]

                self.messenger(util.tstamp() + " EUT position %r" % (p), [])
                # loop freqs
                for f in freqs:
                    self.messenger(util.tstamp() + " Frequency %e Hz" % (f), [])
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
                    except KeyError:
                        conf = {}
                    rconf = mg.ConfReceivers(conf)
                    self.messenger(util.tstamp() + " Receiver configuration: %s" % str(rconf), [])

                    # cable corrections
                    c_port_receiver = []
                    for i in range(nports):
                        c_port_receiver.append(
                            mg.get_path_correction(names['port'][i], names['receiver'][i], POWERRATIO))

                    # ALL measurement start here
                    block = {}
                    nbresult = {}  # dict for NB-Read results
                    nblist = []  # list of devices for NB Reading

                    for i in range(nports):
                        nblist.append(names['receiver'][i])

                    # wait delay seconds
                    # time.sleep(0.5)   # minimum delay according -4-21
                    self.messenger(util.tstamp() + " Going to sleep for %d seconds ..." % (delay), [])
                    self.wait(delay, locals(), self._HandleUserInterrupt)
                    self.messenger(util.tstamp() + " ... back.", [])

                    # Trigger all devices in list
                    mg.NBTrigger(nblist)
                    # serial poll all devices in list
                    olddevs = []
                    while 1:
                        self._HandleUserInterrupt(locals())
                        nbresult = mg.NBRead(nblist, nbresult)
                        new_devs = [i for i in list(nbresult.keys()) if i not in olddevs]
                        olddevs = list(nbresult.keys())[:]
                        if len(new_devs):
                            self.messenger(util.tstamp() + " Got answer from: " + str(new_devs), [])
                        if len(nbresult) == len(nblist):
                            break
                    # print nbresult

                    # ports
                    for i in range(nports):
                        n = names['receiver'][i]
                        if n in nbresult:
                            # add path correction here
                            PPort = nbresult[n]
                            self.__addLoggerBlock(block, n, 'Reading of the receiver for position %d' % i,
                                                  nbresult[n],
                                                  {})
                            self.__addLoggerBlock(block[n]['parameter'], 'freq', 'the frequency [Hz]', f, {})
                            self.__addLoggerBlock(block[n]['parameter'], 'eutpos', 'EUT position', p, {})
                            self.__addLoggerBlock(block, 'c_port_receiver' + str(i),
                                                  'Correction from port to receiver',
                                                  c_port_receiver[i], {})
                            self.__addLoggerBlock(block['c_port_receiver' + str(i)]['parameter'], 'freq',
                                                  'the frequency [Hz]', f, {})
                            PPort /= c_port_receiver[i]['total']
                            # print PPort
                            voltage = self.__insert_it(voltage, PPort, None, None, f, i, p)
                            self.__addLoggerBlock(block, n + '_corrected', 'PPort/c_port_receiver', PPort, {})
                            self.__addLoggerBlock(block[n]['parameter'], 'freq', 'the frequency [Hz]', f, {})
                            self.__addLoggerBlock(block[n]['parameter'], 'eutpos', 'EUT position', p, {})

                    for log in self.logger:
                        log(block)

                    self._HandleUserInterrupt(locals())
                    # END OF f LOOP
                lowBatList = mg.getBatteryLow_Devices()
                if len(lowBatList):
                    self.messenger(
                        util.tstamp() + " WARNING: Low battery status detected for: %s" % (str(lowBatList)),
                        [])
                self.rawData_Emission[description].update({'voltage': voltage, 'mg': mg})
                # autosave class instance
                if self.asname and (time.time() - self.lastautosave > self.autosave_interval):
                    self.messenger(util.tstamp() + " autosave ...", [])
                    self.do_autosave()
                    self.messenger(util.tstamp() + " ... done", [])
                measured_eut_pos.append(p)
                remain_eut_pos.remove(p)
            # END OF p LOOP

        finally:
            # finally is executed if and if not an exception occur -> save exit
            self.messenger(util.tstamp() + " Quit...", [])
            stat = mg.Quit_Devices()
        self.messenger(util.tstamp() + " End of Emission mesurement. Status: %d" % stat, [])
        self.PostUserEvent()
        return stat

    def Measure_Immunity(self,
                         description="EUT",
                         positions=None,
                         dotfile='gtem-immunity.dot',
                         delay=0.0,
                         calibration='cal',
                         kernel=(None, None),
                         leveling=None,
                         freqs=None,
                         SearchPaths=None,
                         names=None):
        """
        Performs an immunity measurement according to IEC 61000-4-20.

        Parameter:

           - *description*: key to identify the measurement in the result dictionary
           - *positions*: a sequence of EUT positions to be measured. Each position is a string characterizing the orientation
             of the cell coordinate system (without prime) relative to the EUT coordinate system.
             A standard choice is to align the z-axis in the
             direction of wave propagation, the y-axis parallel to the E-field (vertical) and the x-axis parallel to
             the H-field. The centre of the EUT is placed at (x = 0,y,z) with x = 0 in the middle of the
             septum. A local "primed" coordinate system (x', y', z') is assigned to the EUT. Position `xx'yy'zz'`
             aligns x' with x, y' with y, and z' with z. Position `xz'yx'zy'` is obtained by
             simply permuting the primed EUT axes: x' to y, y' to z, and z' to x. This is equivalent to two
             90° rotations of the EUT. Position `xy'yz'zx'` is obtained by a further permutation: x' to z, y' to x, z' to y.
             IEC 61000-4-20 defines two standard setups: vertical and horizontal polarization (see below).

              4 vertical positions (:attr:`std_vertical_positions`)::

                     ("xx'yy'zz'",       "xz'yy'z(-x')",       "x(-x')yy'z(-z')",   "x(-z')yy'zx'")

              .. figure:: pos-vert.png

              Vertical standard orientations.

              4 horizontal positions (:attr:`std_horizontal_positions`)::

                       ("xy'y(-x')zz'", "xy'y(-z')z(-x')", "xy'yx'z(-z')", "xy'yz'zx'")

              .. figure:: pos-vert.png

              Horizontal standard orientations.

           - *dotfile*: forwarded to :class:`mpylab.tools.mgraph.MGraph` to create the mearsurement graph.
           - *delay*: time in seconds to wait after setting the frequency before pulling date from the instruments
           - *freqs*: sequence of frequencies in Hz to use for the measurements.
           - *names*: dict with the mapping from internal names to dot-file names.
        """
        if names is None:
            names = {'sg': 'sg',
                     'a1': 'a1',
                     'a2': 'a2',
                     'tem': 'gtem',
                     'pmfwd': 'pm1',
                     'pmbwd': 'pm2'
                     }
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

        if positions is None:
            positions = self.std_positions_immunity

        if self.autosave:
            self.messenger(util.tstamp() + " Resume TEMCell immunity measurement from autosave...", [])
        else:
            self.messenger(util.tstamp() + " Start new TEMCell immunity measurement...", [])

        self.rawData_Immunity.setdefault(description, {})

        mg = mgraph.MGraph(dotfile)
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
                _fg = LogFreq(80e6, 1000e6, 1.01, True)
                freqs = [f for f in LogFreq.logspace]

            # set up voltage, noise, ...
            voltage = {}
            # loop eut positions
            measured_eut_pos = []
            remain_eut_pos = list(positions)[:]
            while len(remain_eut_pos):
                msg = \
                    """
EUT measurement.
Switch EUT ON.
Select EUT position.

"""
                but = []
                for _i, _r in enumerate(remain_eut_pos):
                    msg += "%s: %s\n" % (util.map2singlechar(_i), str(_r))
                    but.append(str(_i))
                msg += "Quit: quit measurement."
                but.append("Quit")
                answer = self.messenger(msg, but)
                if answer == but.index('Quit'):
                    self.messenger(util.tstamp() + " measurement terminated by user.", [])
                    raise UserWarning  # to reach finally statement
                p = remain_eut_pos[answer]

                self.messenger(util.tstamp() + " EUT position %r" % (p), [])
                # loop freqs
                for f in freqs:
                    self.messenger(util.tstamp() + " Frequency %e Hz" % (f), [])
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
                    except KeyError:
                        conf = {}
                    rconf = mg.ConfReceivers(conf)
                    self.messenger(util.tstamp() + " Receiver configuration: %s" % str(rconf), [])

                    # cable corrections
                    c_port_receiver = []
                    for i in range(nports):
                        c_port_receiver.append(
                            mg.get_path_correction(names['port'][i], names['receiver'][i], POWERRATIO))

                    # ALL measurement start here
                    block = {}
                    nbresult = {}  # dict for NB-Read results
                    nblist = []  # list of devices for NB Reading

                    for i in range(nports):
                        nblist.append(names['receiver'][i])

                    # wait delay seconds
                    # time.sleep(0.5)   # minimum delay according -4-21
                    self.messenger(util.tstamp() + " Going to sleep for %d seconds ..." % (delay), [])
                    self.wait(delay, locals(), self._HandleUserInterrupt)
                    self.messenger(util.tstamp() + " ... back.", [])

                    # Trigger all devices in list
                    mg.NBTrigger(nblist)
                    # serial poll all devices in list
                    olddevs = []
                    while 1:
                        self._HandleUserInterrupt(locals())
                        nbresult = mg.NBRead(nblist, nbresult)
                        new_devs = [i for i in list(nbresult.keys()) if i not in olddevs]
                        olddevs = list(nbresult.keys())[:]
                        if len(new_devs):
                            self.messenger(util.tstamp() + " Got answer from: " + str(new_devs), [])
                        if len(nbresult) == len(nblist):
                            break
                    # print nbresult

                    # ports
                    for i in range(nports):
                        n = names['receiver'][i]
                        if n in nbresult:
                            # add path correction here
                            PPort = nbresult[n]
                            self.__addLoggerBlock(block, n, 'Reading of the receiver for position %d' % i,
                                                  nbresult[n],
                                                  {})
                            self.__addLoggerBlock(block[n]['parameter'], 'freq', 'the frequency [Hz]', f, {})
                            self.__addLoggerBlock(block[n]['parameter'], 'eutpos', 'EUT position', p, {})
                            self.__addLoggerBlock(block, 'c_port_receiver' + str(i),
                                                  'Correction from port to receiver',
                                                  c_port_receiver[i], {})
                            self.__addLoggerBlock(block['c_port_receiver' + str(i)]['parameter'], 'freq',
                                                  'the frequency [Hz]', f, {})
                            PPort /= c_port_receiver[i]['total']
                            # print PPort
                            voltage = self.__insert_it(voltage, PPort, None, None, f, i, p)
                            self.__addLoggerBlock(block, n + '_corrected', 'PPort/c_port_receiver', PPort, {})
                            self.__addLoggerBlock(block[n]['parameter'], 'freq', 'the frequency [Hz]', f, {})
                            self.__addLoggerBlock(block[n]['parameter'], 'eutpos', 'EUT position', p, {})

                    for log in self.logger:
                        log(block)

                    self._HandleUserInterrupt(locals())
                    # END OF f LOOP
                lowBatList = mg.getBatteryLow_Devices()
                if len(lowBatList):
                    self.messenger(
                        util.tstamp() + " WARNING: Low battery status detected for: %s" % (str(lowBatList)),
                        [])
                self.rawData_Emission[description].update({'voltage': voltage, 'mg': mg})
                # autosave class instance
                if self.asname and (time.time() - self.lastautosave > self.autosave_interval):
                    self.messenger(util.tstamp() + " autosave ...", [])
                    self.do_autosave()
                    self.messenger(util.tstamp() + " ... done", [])
                measured_eut_pos.append(p)
                remain_eut_pos.remove(p)
            # END OF p LOOP

        finally:
            # finally is executed if and if not an exception occur -> save exit
            self.messenger(util.tstamp() + " Quit...", [])
            stat = mg.Quit_Devices()
        self.messenger(util.tstamp() + " End of Emission mesurement. Status: %d" % stat, [])
        self.PostUserEvent()
        return stat

    def Measure_Emission(self,
                         description="EUT",
                         positions=None,
                         dotfile='gtem-emission.dot',
                         delay=0.0,
                         freqs=None,
                         receiverconf=None,
                         names=None):
        """
        Performs a emission measurement according to IEC 61000-4-20.

        Parameter:

           - *description*: key to identify the measurement in the result dictionary
           - *positions*: a sequence of EUT positions to be measured. Each position is a string characterizing the orientation
             of the cell coordinate system (without prime) relative to the EUT coordinate system.
             A standard choice is to align the z-axis in the
             direction of wave propagation, the y-axis parallel to the E-field (vertical) and the x-axis parallel to
             the H-field. The centre of the EUT is placed at (x = 0,y,z) with x = 0 in the middle of the
             septum. A local "primed" coordinate system (x', y', z') is assigned to the EUT. Position `xx'yy'zz'`
             aligns x' with x, y' with y, and z' with z. Position `xz'yx'zy'` is obtained by
             simply permuting the primed EUT axes: x' to y, y' to z, and z' to x. This is equivalent to two
             90° rotations of the EUT. Position `xy'yz'zx'` is obtained by a further permutation: x' to z, y' to x, z' to y.
             IEC 61000-4-21 defines two standard setups: with the 3 positions `("xx'yy'zz'", "xz'yx'zy'", "xy'yz'zx'")`, or with 12
             positions (see below).

              3 standart positions (:attr:`std_3_positions`)::

                     ("xx'yy'zz'",       "xz'yx'zy'",       "xy'yz'zx'")

              .. figure:: pos3.png

              First three standard orientations.

              12 standard positions (:attr:`std_12_positions`)::

                       ("xx'yy'zz'",       "xz'yx'zy'",       "xy'yz'zx'",
                        "xz'yy'z(-x')",    "x(-x')yz'zy'",    "xy'y(-x')zz'",
                        "x(-x')yy'z(-z')", "x(-z')y(-x')zy'", "xy'y(-z')z(-x')",
                        "x(-z')yy'zx'",    "xx'y(-z')zy'",    "xy'yx'z(-z')")


              .. figure:: pos12.png

              12 standard orientations.

           - *dotfile*: forwarded to :class:`mpylab.tools.mgraph.MGraph` to create the mearsurment graph.
           - *delay*: time in seconds to wait after setting the frequencie before pulling date from the instruments
           - *freqs*: sequence of frequencies in Hz to use for the measurements.
           - *receiverconf*: forwarded to :meth:`mpylab.tools.mgraph.MGraph.ConfReceivers`
           - *names*: dict with the mapping from internal names to dot-file names.

               The dict has to have keys 'port' and 'receivers'. The corresponding values are sequences of equal length giving the
               names of the ports and of the receivers in the dot-file. For a GTEM the length of this lists is one.
               For a Crawford cell it would be two.

        """
        if names is None:
            names = {'port': ['port'],
                     'receiver': ['analyzer']}
        if positions is None:
            positions = self.std_3_positions

        self.PreUserEvent()
        if self.autosave:
            self.messenger(util.tstamp() + " Resume TEM cell emission measurement from autosave...", [])
        else:
            self.messenger(util.tstamp() + " Start new TEM cell emission measurement...", [])

        self.rawData_Emission.setdefault(description, {})

        # number of ports
        nports = min(len(names['port']), len(names['receiver']))

        mg = mgraph.MGraph(dotfile)
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

            # set up voltage, noise, ...
            voltage = {}
            noise = {}

            if self.autosave:
                noise = self.rawData_Emission[description]['noise'].copy()
                try:
                    voltage = self.rawData_Emission[description]['voltage'].copy()
                    eut_positions = list(voltage[0].keys())
                    positions = [_p for _p in positions if not _p in eut_positions]
                except KeyError:  # as after noise -> no voltages yet
                    pass
                msg = "List of remainung eut positions from autosave file:\n%r\n" % (positions)
                but = []
                self.messenger(msg, but)
            self.autosave = False

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
                self.messenger(util.tstamp() + " measurement terminated by user.", [])
                raise UserWarning  # to reach finally statement
            # loop freqs
            for f in freqs:
                self.messenger(util.tstamp() + " Frequency %e Hz" % (f), [])
                mg.EvaluateConditions()
                # set frequency for all devices
                (minf, maxf) = mg.SetFreq_Devices(f)
                # configure receiver(s)
                for rf in rcfreqs:  # rcfreqs are the keys of the conf dict in reverse order
                    if f >= rf:
                        break
                try:
                    conf = receiverconf[rf]
                except IndexError:
                    conf = {}
                rconf = mg.ConfReceivers(conf)
                self.messenger(util.tstamp() + " Receiver configuration: %s" % rconf, [])

                # cable corrections
                c_port_receiver = []
                for i in range(nports):
                    c_port_receiver.append(
                        mg.get_path_correction(names['port'][i], names['receiver'][i], POWERRATIO))

                # ALL measurement start here
                block = {}
                nbresult = {}  # dict for NB-Read results
                receiverlist = []

                for i in range(nports):
                    receiverlist.append(names['receiver'][i])

                # noise floor measurement..
                self.messenger(util.tstamp() + " Starting noise floor measurement for f = %e Hz ..." % (f), [])
                mg.NBTrigger(receiverlist)
                # serial poll all devices in list
                olddevs = []
                while 1:
                    self._HandleUserInterrupt(locals())
                    nbresult = mg.NBRead(receiverlist, nbresult)
                    new_devs = [i for i in list(nbresult.keys()) if i not in olddevs]
                    olddevs = list(nbresult.keys())[:]
                    if len(new_devs):
                        self.messenger(util.tstamp() + " Got answer from: " + str(new_devs), [])
                    if len(nbresult) == len(receiverlist):
                        break
                for i in range(nports):
                    n = names['receiver'][i]
                    if n in nbresult:
                        # add path correction here
                        # print n, nbresult[n]
                        PPort = nbresult[n]
                        nn = 'Noise ' + n
                        self.__addLoggerBlock(block, nn, 'Noise reading of the receiver for position %d' % i,
                                              nbresult[n], {})
                        self.__addLoggerBlock(block[nn]['parameter'], 'freq', 'the frequency [Hz]', f, {})
                        self.__addLoggerBlock(block, 'c_port_receiver' + str(i), 'Correction from port to receiver',
                                              c_port_receiver[i], {})
                        self.__addLoggerBlock(block['c_port_receiver' + str(i)]['parameter'], 'freq',
                                              'the frequency [Hz]', f, {})
                        PPort /= c_port_receiver[i]['total']
                        self.__addLoggerBlock(block, nn + '_corrected', 'Noise: PPort/c_refant_receiver', PPort, {})
                        self.__addLoggerBlock(block[nn + '_corrected']['parameter'], 'freq', 'the frequency [Hz]',
                                              f,
                                              {})
                        noise = self.__insert_it(noise, PPort, None, None, f, i, 0)
                self.messenger(util.tstamp() + " Noise floor measurement done.", [])

                for log in self.logger:
                    log(block)

                self._HandleUserInterrupt(locals())
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

            # loop eut positions
            measured_eut_pos = []
            remain_eut_pos = list(positions)[:]
            while len(remain_eut_pos):
                msg = \
                    """
EUT measurement.
Switch EUT ON.
Select EUT position.

"""
                but = []
                for _i, _r in enumerate(remain_eut_pos):
                    msg += "%s: %s\n" % (util.map2singlechar(_i), str(_r))
                    but.append(str(_i))
                msg += "Quit: quit measurement."
                but.append("Quit")
                answer = self.messenger(msg, but)
                if answer == but.index('Quit'):
                    self.messenger(util.tstamp() + " measurement terminated by user.", [])
                    raise UserWarning  # to reach finally statement
                p = remain_eut_pos[answer]

                self.messenger(util.tstamp() + " EUT position %r" % (p), [])
                # loop freqs
                for f in freqs:
                    self.messenger(util.tstamp() + " Frequency %e Hz" % (f), [])
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
                    except KeyError:
                        conf = {}
                    rconf = mg.ConfReceivers(conf)
                    self.messenger(util.tstamp() + " Receiver configuration: %s" % str(rconf), [])

                    # cable corrections
                    c_port_receiver = []
                    for i in range(nports):
                        c_port_receiver.append(
                            mg.get_path_correction(names['port'][i], names['receiver'][i], POWERRATIO))

                    # ALL measurement start here
                    block = {}
                    nbresult = {}  # dict for NB-Read results
                    nblist = []  # list of devices for NB Reading

                    for i in range(nports):
                        nblist.append(names['receiver'][i])

                    # wait delay seconds
                    # time.sleep(0.5)   # minimum delay according -4-21
                    self.messenger(util.tstamp() + " Going to sleep for %d seconds ..." % (delay), [])
                    self.wait(delay, locals(), self._HandleUserInterrupt)
                    self.messenger(util.tstamp() + " ... back.", [])

                    # Trigger all devices in list
                    mg.NBTrigger(nblist)
                    # serial poll all devices in list
                    olddevs = []
                    while 1:
                        self._HandleUserInterrupt(locals())
                        nbresult = mg.NBRead(nblist, nbresult)
                        new_devs = [i for i in list(nbresult.keys()) if i not in olddevs]
                        olddevs = list(nbresult.keys())[:]
                        if len(new_devs):
                            self.messenger(util.tstamp() + " Got answer from: " + str(new_devs), [])
                        if len(nbresult) == len(nblist):
                            break
                    # print nbresult

                    # ports
                    for i in range(nports):
                        n = names['receiver'][i]
                        if n in nbresult:
                            # add path correction here
                            PPort = nbresult[n]
                            self.__addLoggerBlock(block, n, 'Reading of the receiver for position %d' % i,
                                                  nbresult[n],
                                                  {})
                            self.__addLoggerBlock(block[n]['parameter'], 'freq', 'the frequency [Hz]', f, {})
                            self.__addLoggerBlock(block[n]['parameter'], 'eutpos', 'EUT position', p, {})
                            self.__addLoggerBlock(block, 'c_port_receiver' + str(i),
                                                  'Correction from port to receiver',
                                                  c_port_receiver[i], {})
                            self.__addLoggerBlock(block['c_port_receiver' + str(i)]['parameter'], 'freq',
                                                  'the frequency [Hz]', f, {})
                            PPort /= c_port_receiver[i]['total']
                            # print PPort
                            voltage = self.__insert_it(voltage, PPort, None, None, f, i, p)
                            self.__addLoggerBlock(block, n + '_corrected', 'PPort/c_port_receiver', PPort, {})
                            self.__addLoggerBlock(block[n]['parameter'], 'freq', 'the frequency [Hz]', f, {})
                            self.__addLoggerBlock(block[n]['parameter'], 'eutpos', 'EUT position', p, {})

                    for log in self.logger:
                        log(block)

                    self._HandleUserInterrupt(locals())
                    # END OF f LOOP
                lowBatList = mg.getBatteryLow_Devices()
                if len(lowBatList):
                    self.messenger(
                        util.tstamp() + " WARNING: Low battery status detected for: %s" % (str(lowBatList)),
                        [])
                self.rawData_Emission[description].update({'voltage': voltage, 'mg': mg})
                # autosave class instance
                if self.asname and (time.time() - self.lastautosave > self.autosave_interval):
                    self.messenger(util.tstamp() + " autosave ...", [])
                    self.do_autosave()
                    self.messenger(util.tstamp() + " ... done", [])
                measured_eut_pos.append(p)
                remain_eut_pos.remove(p)
            # END OF p LOOP

        finally:
            # finally is executed if and if not an exception occur -> save exit
            self.messenger(util.tstamp() + " Quit...", [])
            stat = mg.Quit_Devices()
        self.messenger(util.tstamp() + " End of Emission mesurement. Status: %d" % stat, [])
        self.PostUserEvent()
        return stat

    def Measure_e0y(self,
                    description=None,
                    dotfile='gtem-e0y.dot',
                    delay=1.0,
                    freqs=None,
                    SGLevel=-20,
                    leveling=None,
                    names=None):
        """
        Performs determination of e0y according to IEC 61000-4-20.

        Parameters:

           - *description*: key to identify the measurement in the result dictionary
           - *dotfile*: forwarded to :class:`mpylab.tools.mgraph.MGraph` to create the mearsurment graph.
           - *delay*: time in seconds to wait after setting the frequency before pulling date from the instruments
           - *freqs*: sequence of frequencies in Hz to use for the measurements.
           - *SGLevel*: signal generator power level in dBm.
           - *leveling*: If leveling is `None` it is initialized with::

                leveling = [{'condition': 'False',
                             'actor': None,
                             'actor_min': None,
                             'actor_max': None,
                             'watch': None,
                             'nominal': None,
                             'reader': None,
                             'path': None}]

           - *names*: dict with the mapping from internal names to dot-file names.

               The dict has to have keys 
               
                 - 'sg': signalgenerator
                 - 'a1': amplifier input port
                 - 'a2': amplifier output port
                 - 'port': TEM cell feeding
                 - 'pmfwd': forward power meter
                 - 'pmbwd': backward power meter
                 - 'fp': list of field probes
               
               The corresponding values give the 
               names in the dot-file.
 
        """
        if names is None:
            names = {'sg': 'sg',
                     'a1': 'a1',
                     'a2': 'a2',
                     'port': 'port',
                     'pmfwd': 'pm1',
                     'pmbwd': 'pm2',
                     'fp': ['fp1']}
        self.PreUserEvent()

        if self.autosave:
            self.messenger(util.tstamp() + " Resume e0y calibration measurement from autosave...", [])
        else:
            self.messenger(util.tstamp() + " Start new e0y calibration measurement...", [])

        if description is None:
            description = "None"

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

        mg = mgraph.MGraph(dotfile)
        ddict = mg.CreateDevices()
        for k, v in list(ddict.items()):
            globals()[k] = v

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
                level = self.setLevel(mg, names, SGLevel)
            except Measure.AmplifierProtectionError as _e:
                self.messenger(
                    util.tstamp() + " Can not set signal generator level. Amplifier protection raised with message: %s" % _e.message,
                    [])
                raise  # re raise to reach finaly clause

            # set up efields, ...
            efields = {}

            if self.autosave:
                efields = self.rawData_e0y[description]['efield'].copy()

                edat = self.rawData_e0y[description]['efield']
                fr = list(edat.keys())
                freqs = [f for f in freqs if f not in fr]
                msg = "List of remaining frequencies:\n%r\n" % (freqs)
                but = []
                self.messenger(msg, but)
            self.autosave = False

            stat = mg.RFOff_Devices()
            msg = """Position E field probes.\nAre you ready to start the measurement?\n\nStart: start measurement.\nQuit: quit measurement."""
            but = ["Start", "Quit"]
            answer = self.messenger(msg, but)
            if answer == but.index('Quit'):
                self.messenger(util.tstamp() + " measurement terminated by user.", [])
                raise UserWarning  # to reach finally statement
            self.messenger(util.tstamp() + " RF On...", [])
            stat = mg.RFOn_Devices()
            # loop freqs
            for f in freqs:
                self.messenger(util.tstamp() + " Frequency %e Hz" % (f), [])
                # switch if necessary
                # print f
                mg.EvaluateConditions()
                # set frequency for all devices
                (minf, maxf) = mg.SetFreq_Devices(f)
                # cable corrections
                c_sg_amp = mg.get_path_correction(names['sg'], names['a1'], POWERRATIO)
                c_sg_port = mg.get_path_correction(names['sg'], names['port'], POWERRATIO)
                c_a2_pm1 = mg.get_path_correction(names['a2'], names['pmfwd'], POWERRATIO)
                c_a2_port = mg.get_path_correction(names['a2'], names['port'], POWERRATIO)
                c_port_pm2 = mg.get_path_correction(names['port'], names['pmbwd'], POWERRATIO)
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
                # print "nblist:", nblist

                level2 = self.doLeveling(leveling, mg, names, locals())
                if level2:
                    level = level2

                # wait delay seconds
                self.messenger(util.tstamp() + " Going to sleep for %d seconds ..." % (delay), [])
                self.wait(delay, locals(), self._HandleUserInterrupt)
                self.messenger(util.tstamp() + " ... back.", [])

                # Trigger all devices in list
                mg.NBTrigger(nblist)
                # serial poll all devices in list
                if NoPmFwd:
                    nbresult[names['pmfwd']] = level
                    nbresult[names['pmbwd']] = Quantity(level._unit, 0)
                olddevs = []
                while 1:
                    self._HandleUserInterrupt(locals())
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
                    PFwd *= c_a2_port['total']
                    self.__addLoggerBlock(block, 'c_a2_port', 'Correction from amplifier output to port', c_a2_port, {})
                    self.__addLoggerBlock(block['c_a2_port']['parameter'], 'freq', 'the frequency [Hz]', f, {})
                    self.__addLoggerBlock(block, 'c_a2_pm1', 'Correction from amplifier output to fwd power meter',
                                          c_a2_pm1, {})
                    self.__addLoggerBlock(block['c_a2_pm1']['parameter'], 'freq', 'the frequency [Hz]', f, {})
                    PFwd /= c_a2_pm1['total']
                    self.__addLoggerBlock(block, n + '_corrected', 'Pfwd*c_a2_port/c_a2_pm1', PFwd, {})
                    self.__addLoggerBlock(block[n]['parameter'], 'freq', 'the frequency [Hz]', f, {})
                    # pbwd
                n = names['pmbwd']
                if n in nbresult:
                    PBwd = nbresult[n]
                    self.__addLoggerBlock(block, n, 'Reading of the bwd power meter', nbresult[n], {})
                    self.__addLoggerBlock(block[n]['parameter'], 'freq', 'the frequency [Hz]', f, {})
                    self.__addLoggerBlock(block, 'c_port_pm2', 'Correction from port to bwd power meter', c_port_pm2,
                                          {})
                    self.__addLoggerBlock(block['c_port_pm2']['parameter'], 'freq', 'the frequency [Hz]', f, {})
                    PBwd /= c_port_pm2['total']
                    self.__addLoggerBlock(block, n + '_corrected', 'Pbwd/c_port_pm2', PBwd, {})
                    self.__addLoggerBlock(block[n]['parameter'], 'freq', 'the frequency [Hz]', f, {})

                    # e-field probes
                # read field probes
                for i in range(nprb):
                    n = names['fp'][i]
                    if n in nbresult:
                        self.__addLoggerBlock(block, n, 'Reading of the e-field probe number %d' % i, nbresult[n], {})
                        self.__addLoggerBlock(block[n]['parameter'], 'freq', 'the frequency [Hz]', f, {})
                        efields = self.__insert_it(efields, nbresult[n], PFwd, PBwd, f, 0, 0)
                for log in self.logger:
                    log(block)

                self._HandleUserInterrupt(locals())
                # test for low battery
                lowBatList = mg.getBatteryLow_Devices()
                if len(lowBatList):
                    self.messenger(util.tstamp() + " WARNING: Low battery status detected for: %s" % (str(lowBatList)),
                                   [])
                # autosave class instance
                if self.asname and (time.time() - self.lastautosave > self.autosave_interval):
                    self.messenger(util.tstamp() + " autosave ...", [])
                    self.do_autosave()
                    self.messenger(util.tstamp() + " ... done", [])
                # END OF f LOOP
            self.messenger(util.tstamp() + " RF Off...", [])
            stat = mg.RFOff_Devices()  # switch off after measure
            self.rawData_e0y[description].update({'efield': efields, 'mg': mg})

        finally:
            # finally is executed if and if not an exception occur -> save exit
            self.messenger(util.tstamp() + " RF Off and Quit...", [])
            stat = mg.RFOff_Devices()
            stat = mg.Quit_Devices()
        self.messenger(util.tstamp() + " End of e0y calibration. Status: %d" % stat, [])
        self.PostUserEvent()
        return stat

    def Measure_Uniformity_TEMModeVerfication_constant_field(self,
                                                             description=None,
                                                             dotfile='gtem-uniformity.dot',
                                                             delay=1.0,
                                                             freqs=None,
                                                             EFieldStrength=None,
                                                             SGLevel=-20,
                                                             leveling=None,
                                                             names=None):
        """
        Performs uniformity and TEM verification according to IEC 61000-4-20.
        This routine uses the constant field method.

        Parameters:

           - *description*: key to identify the measurement in the result dictionary
           - *dotfile*: forwarded to :class:`mpylab.tools.mgraph.MGraph` to create the mearsurement graph.
           - *delay*: time in seconds to wait after setting the frequency before pulling date from the instruments
           - *freqs*: sequence of frequencies in Hz to use for the measurements.
           - *EFieldStrength*: iterable of desired field strength values. If None it is seit to [1]
           - *SGLevel*: initial signal generator level
           - *leveling*: If leveling is `None` it is initialized with::

                leveling = [{'condition': 'False',
                             'actor': None,
                             'actor_min': None,
                             'actor_max': None,
                             'watch': None,
                             'nominal': None,
                             'reader': None,
                             'path': None}]

           - *names*: dict with the mapping from internal names to dot-file names.

               The dict has to have keys

                 - 'sg': signalgenerator
                 - 'a1': amplifier input port
                 - 'a2': amplifier output port
                 - 'port': TEM cell feeding
                 - 'pmfwd': forward power meter
                 - 'pmbwd': backward power meter
                 - 'fp': list of field probes

               The corresponding values give the
               names in the dot-file.

        """
        if names is None:
            names = {'sg': 'sg',
                     'a1': 'a1',
                     'a2': 'a2',
                     'port': 'port',
                     'pmfwd': 'pm1',
                     'pmbwd': 'pm2',
                     'fp': ['fp1']}
        self.PreUserEvent()

        if EFieldStrength is None:
            EFieldStrength = [1.0]

        if self.autosave:
            self.messenger(util.tstamp() + " Resume e0y calibration measurement from autosave...", [])
        else:
            self.messenger(util.tstamp() + " Start new e0y calibration measurement...", [])

        if description is None:
            description = "None"

        self.rawData_Uniformity_TEMModeVerfication_constant_field.setdefault(description, {})

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

        mg = mgraph.MGraph(dotfile)
        ddict = mg.CreateDevices()
        for k, v in list(ddict.items()):
            globals()[k] = v

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
                level = self.setLevel(mg, names, SGLevel)
            except Measure.AmplifierProtectionError as _e:
                self.messenger(
                    util.tstamp() + " Can not set signal generator level. Amplifier protection raised with message: %s" % _e.message,
                    [])
                raise  # re raise to reach finaly clause

            # set up efields, power
            efields = {}
            fwd_power = {}
            bwd_power = {}
            # HIER

            if self.autosave:
                efields = self.rawData_Uniformity_TEMModeVerfication_constant_field[description]['efield'].copy()

                edat = self.rawData_Uniformity_TEMModeVerfication_constant_field[description]['efield']
                fr = list(edat.keys())
                freqs = [f for f in freqs if f not in fr]
                msg = "List of remaining frequencies:\n%r\n" % (freqs)
                but = []
                self.messenger(msg, but)
            self.autosave = False

            stat = mg.RFOff_Devices()
            msg = """Position E field probes.\nAre you ready to start the measurement?\n\nStart: start measurement.\nQuit: quit measurement."""
            but = ["Start", "Quit"]
            answer = self.messenger(msg, but)
            if answer == but.index('Quit'):
                self.messenger(util.tstamp() + " measurement terminated by user.", [])
                raise UserWarning  # to reach finally statement
            self.messenger(util.tstamp() + " RF On...", [])
            stat = mg.RFOn_Devices()
            # loop freqs
            for f in freqs:
                self.messenger(util.tstamp() + " Frequency %e Hz" % (f), [])
                # switch if necessary
                # print f
                mg.EvaluateConditions()
                # set frequency for all devices
                (minf, maxf) = mg.SetFreq_Devices(f)
                # cable corrections
                c_sg_amp = mg.get_path_correction(names['sg'], names['a1'], POWERRATIO)
                c_sg_port = mg.get_path_correction(names['sg'], names['port'], POWERRATIO)
                c_a2_pm1 = mg.get_path_correction(names['a2'], names['pmfwd'], POWERRATIO)
                c_a2_port = mg.get_path_correction(names['a2'], names['port'], POWERRATIO)
                c_port_pm2 = mg.get_path_correction(names['port'], names['pmbwd'], POWERRATIO)
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
                # print "nblist:", nblist

                level2 = self.doLeveling(leveling, mg, names, locals())
                if level2:
                    level = level2

                # wait delay seconds
                self.messenger(util.tstamp() + " Going to sleep for %d seconds ..." % (delay), [])
                self.wait(delay, locals(), self._HandleUserInterrupt)
                self.messenger(util.tstamp() + " ... back.", [])

                # Trigger all devices in list
                mg.NBTrigger(nblist)
                # serial poll all devices in list
                if NoPmFwd:
                    nbresult[names['pmfwd']] = level
                    nbresult[names['pmbwd']] = Quantity(level._unit, 0)
                olddevs = []
                while 1:
                    self._HandleUserInterrupt(locals())
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
                    PFwd *= c_a2_port['total']
                    self.__addLoggerBlock(block, 'c_a2_port', 'Correction from amplifier output to port', c_a2_port, {})
                    self.__addLoggerBlock(block['c_a2_port']['parameter'], 'freq', 'the frequency [Hz]', f, {})
                    self.__addLoggerBlock(block, 'c_a2_pm1', 'Correction from amplifier output to fwd power meter',
                                          c_a2_pm1, {})
                    self.__addLoggerBlock(block['c_a2_pm1']['parameter'], 'freq', 'the frequency [Hz]', f, {})
                    PFwd /= c_a2_pm1['total']
                    self.__addLoggerBlock(block, n + '_corrected', 'Pfwd*c_a2_port/c_a2_pm1', PFwd, {})
                    self.__addLoggerBlock(block[n]['parameter'], 'freq', 'the frequency [Hz]', f, {})
                    # pbwd
                n = names['pmbwd']
                if n in nbresult:
                    PBwd = nbresult[n]
                    self.__addLoggerBlock(block, n, 'Reading of the bwd power meter', nbresult[n], {})
                    self.__addLoggerBlock(block[n]['parameter'], 'freq', 'the frequency [Hz]', f, {})
                    self.__addLoggerBlock(block, 'c_port_pm2', 'Correction from port to bwd power meter', c_port_pm2,
                                          {})
                    self.__addLoggerBlock(block['c_port_pm2']['parameter'], 'freq', 'the frequency [Hz]', f, {})
                    PBwd /= c_port_pm2['total']
                    self.__addLoggerBlock(block, n + '_corrected', 'Pbwd/c_port_pm2', PBwd, {})
                    self.__addLoggerBlock(block[n]['parameter'], 'freq', 'the frequency [Hz]', f, {})

                    # e-field probes
                # read field probes
                for i in range(nprb):
                    n = names['fp'][i]
                    if n in nbresult:
                        self.__addLoggerBlock(block, n, 'Reading of the e-field probe number %d' % i, nbresult[n], {})
                        self.__addLoggerBlock(block[n]['parameter'], 'freq', 'the frequency [Hz]', f, {})
                        efields = self.__insert_it(efields, nbresult[n], PFwd, PBwd, f, 0, 0)
                for log in self.logger:
                    log(block)

                self._HandleUserInterrupt(locals())
                # test for low battery
                lowBatList = mg.getBatteryLow_Devices()
                if len(lowBatList):
                    self.messenger(util.tstamp() + " WARNING: Low battery status detected for: %s" % (str(lowBatList)),
                                   [])
                # autosave class instance
                if self.asname and (time.time() - self.lastautosave > self.autosave_interval):
                    self.messenger(util.tstamp() + " autosave ...", [])
                    self.do_autosave()
                    self.messenger(util.tstamp() + " ... done", [])
                # END OF f LOOP
            self.messenger(util.tstamp() + " RF Off...", [])
            stat = mg.RFOff_Devices()  # switch off after measure
            self.rawData_Uniformity_TEMModeVerfication_constant_field[description].update({'efield': efields, 'mg': mg})

        finally:
            # finally is executed if and if not an exception occur -> save exit
            self.messenger(util.tstamp() + " RF Off and Quit...", [])
            stat = mg.RFOff_Devices()
            stat = mg.Quit_Devices()
        self.messenger(util.tstamp() + " End of e0y calibration. Status: %d" % stat, [])
        self.PostUserEvent()
        return stat

    def __insert_it(self, field, value, pf, pb, f, port, pos, dct=None):
        """
        Inserts a value in a field.
        field: '3D' dictionary of a list of dicts ;-)
        e.g.: efield[f][port][pos] is a list [{'value': vector of Quantities, 'pfwd': Quantity, 'pwwd': Quantity}, ...]
        f: frequency (float)
        """
        field.setdefault(f, {})
        field[f].setdefault(port, {})
        field[f][port].setdefault(pos, [])
        field[f][port][pos].append({'value': value, 'pfwd': pf, 'pbwd': pb})
        if not dct is None:
            field[f][port][pos][-1].update(dct)
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

    def OutputRawData_e0y(self, description=None, what=None, fname=None):
        thedata = self.rawData_e0y
        stdout = sys.stdout
        if fname:
            fp = open(fname, "w")
            sys.stdout = fp
        try:
            self.__OutputRawData(thedata, description, what)
        finally:
            try:
                fp.close()
            except:
                util.LogError(self.messenger)
            sys.stdout = stdout

    def OutputRawData_Emission(self, description=None, what=None, fname=None):
        thedata = self.rawData_Emission
        stdout = sys.stdout
        if fname:
            fp = open(fname, "w")
            sys.stdout = fp
        try:
            self.__OutputRawData(thedata, description, what)
        finally:
            try:
                fp.close()
            except:
                util.LogError(self.messenger)
            sys.stdout = stdout

    def __OutputRawData(self, thedata, description, what):
        deslist = self.MakeDeslist(thedata, description)
        whatlist = self.MakeWhatlist(thedata, what)
        for d in deslist:
            print("# Description:", d)
            for w in whatlist:
                print("# ", w)
                data = thedata[d][w]
                try:
                    freqs = list(data.keys())
                    freqs.sort()
                    for f in freqs:
                        pees = list(data[f].keys())
                        pees.sort()
                        for p in pees:
                            poses = list(data[f][p].keys())
                            poses.sort()
                            for pos in poses:
                                print("f:", f, "port:", p, "pos:", pos, end=' ')
                                item = data[f][p][pos]
                                self.out(item)
                                print()
                except KeyError:  # data has no keys
                    item = data
                    self.out(item)
                    print()

    def OutputProcessedData_e0y(self, description=None, what=None, fname=None):
        thedata = self.processedData_e0y
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

    def __OutputProcessedData(self, thedata, description, what):
        deslist = self.MakeDeslist(thedata, description)
        whatlist = self.MakeWhatlist(thedata, what)
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

    def Evaluate_e0y(self, description=None):
        """
        """
        self.messenger(util.tstamp() + " Start of evaluation of e0y calibration with description %s" % description, [])
        if description not in self.rawData_e0y:
            self.messenger(util.tstamp() + " Description %s not found." % description, [])
            return -1

        efields = self.rawData_e0y[description]['efield']
        # pprint.pprint(efields)
        freqs = list(efields.keys())
        freqs.sort()
        # print 'Freqs:', freqs

        self.processedData_e0y.setdefault(description, {})
        self.processedData_e0y[description]['e0y'] = {}
        for f in freqs:
            self.processedData_e0y[description]['e0y'][f] = {}
            e0yf = self.processedData_e0y[description]['e0y'][f]
            ports = list(efields[f].keys())
            ports.sort()
            # print 'Ports:', ports
            for port in ports:
                e0yf[port] = []
                for i in range(len(efields[f][port][0])):
                    ef = efields[f][port][0][i]['value']
                    pin = efields[f][port][0][i]['pfwd']
                    pin = abs(pin)  # pin.mag().convert(umddevice.UMD_W)
                    sqrtPInput = math.sqrt(pin)
                    en = []
                    for k in range(len(ef)):
                        en.append(ef[k] / sqrtPInput)
                        # print k, ef[k], pin, sqrtPInput, en[-1]
                    self.processedData_e0y[description]['e0y'][f][port].append(en)
        self.messenger(util.tstamp() + " End of evaluation of e0y calibration", [])
        return 0


class stdImmunityKernel:
    def __init__(self, field, freqs, positions, messenger, UIHandler, lcls, dwell, keylist='sS'):
        self.field = field
        self.freqs = freqs
        self.positions = positions
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
        for pol in 'vh':
            for pos in self.positions[pol]:
                has_pos = pos in self.in_as
                if has_pos:
                    continue
                ret.append(('LoopMarker', '', {}))
                ret.append(('position', '', {'position': pos}))
                ret.append(('rf', '', {'rfon': 1}))
                for f in self.freqs:
                    ret.append(('freq', '', {'freq': f}))
                    ret.append(('efield', '', {'efield': self.field}))
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
    def __init__(self, instance, cal='cal'):
        self.fail = False
        if cal not in instance.processedData_ImmunityCal:
            self.fail = True
        self.E_mean = util.MResult_Interpol(instance.processedData_ImmunityCal[cal]['E_mean'].copy())

    def __call__(self, f=None, power=None):
        if f is None:
            return None
        if power is None:
            return None
        e_mean = self.E_mean(f)  # .convert(umddevice.UMD_VovermoversqrtW)
        etest2 = power * e_mean * e_mean
        etest_v = math.sqrt(etest2)
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
    def __init__(self, instance, cal='cal'):
        self.fail = False
        self.instance = instance
        if cal not in instance.processedData_ImmunityCal:
            self.fail = True
        self.E_mean = util.MResult_Interpol(instance.processedData_MainCal[cal]['E_mean'].copy())

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
        e_mean = self.E_mean(f)  # .convert(umddevice.UMD_VovermoversqrtW)
        # self.instance.messenger("DEBUG TestPower: f: %e, etest: %r, enorm: %r, clf: %r"%(f,etest,enorm,clf), [])
        # enorm.unit=umddevice.UMD_dimensionless
        E = etest  # .get_v()
        e = e_mean  # .get_v()
        power_v = (E / e) ** 2

        # dE = 0.5*(etest.get_u()-etest.get_l())
        # dc = 0.5*(clf.get_u()-clf.get_l())
        # de = 0.5*(enorm.get_u()-enorm.get_l())

        # dp = E/(e*c) * math.sqrt((2*dE/e)**2
        #                       + (2*E*de/(e*e))**2
        #                       + (E*dc/(e*math.sqrt(c)))**2)
        power = power_v
        # self.instance.messenger("DEBUG TestPower: f: %e, power: %r"%(f,power), [])
        return power
