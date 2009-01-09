# -*- coding: iso-8859-1 -*-
"""
Measure: Base class for other measure classes

Author: Prof. Dr. Hans Georg Krauthaeuser, hgk@ieee.org

Copyright (c) 2001-2008 All rights reserved
"""

import sys
import time
import types
import inspect
import cPickle
import gzip
import math

import device
import util


try:
    import pyTTS
    tts=pyTTS.Create()
    tts.SetVoiceByName('MSMary')
except:
    tts=None
    pass

class Measure(object):
    """
    Base class for measurements.
    """
    def wait(self, delay, dct, uihandler, intervall=0.1):
        """
        A wait function that can de interrupted.

        @type delay: number
        @param delay: seconds to wait
        @type dct: namespace
        @param dct: namespace used by uihandler (L{self.stdUserInterruptHandler})
        @type uihandler: callable
        @param uihandler: User-Interupt Handler
        @type intervall: number
        @param intervall: seconds to sllep between uihandler calls
        @rtype: None
        @return: None
        """
        start = time.time()
        delay = abs(delay)
        intervall = abs(intervall)
        while (time.time()-start < delay):
            uihandler(dct)
            time.sleep(intervall)

    def out(self, item):
        """
        Helper function for all output functions.
        Prints item recursively all in one line.
        item can be:
            - a dict of items
            - a list of items
            - a vector of items
            - SCUQ objects
            - or anything else (will be printed by 'print item,')

        @type item: object
        @param item: the opject to print
        @rtype: None
        @return: None
        """
        if hasattr(item, 'keys'):  # a dict
            print "{",
            for k in item.keys():
                print str(k)+":",
                self.out(item[k])
            print "}",
        elif hasattr(item,'get_v'): # MResult or CMResult
            print item,
        elif hasattr(item, 'sort'):  # a list
            print "[",
            for i in item:
                self.out(i)
            print "]",
        elif type(item) == type((1,)):  # a tuple
            print "(",
            for i in item:
                self.out(i)
            print ")",
        elif hasattr(item, 'append'): # vector
            print "(",
            for i in item:
                self.out(i)
            print ")",
        else:
            print item,
            
    def SetAutoSaveInterval (self, interval):
        """
        Set the intervall between auto save.

        @type intervall: number
        @param intervall: seconds between auto save
        @rtype: None
        @return: None
        """
        self.autosave_interval = interval
        
    def stdlogger(self, block):
        """
        The standard logger.
        Print block to self.logfile or to stdout (if self.logfile is None).
        if 'block' has attribute 'keys' (i.e. is a dict), the elements are
        processed with the local function L{out_block}. Else, the block is printed
        directly.

        @type block: object
        @param block: object to log
        @rtype: None
        @return: None
        """
        def out_block(b):
            """
            Helper function to log something.
            """
            if b.has_key('comment'):
                print repr(b['comment']),
            if b.has_key('parameter'):
                par = b['parameter']
                for des,p in par.items():
                    print des,
                    out_block(p)
                if b.has_key('value'):
                    item = b['value']
                else:
                    item = None
                self.out(item)
            sys.stdout.flush()
            
        stdout = sys.stdout
        if self.logfile is not None:
            sys.stdout = self.logfile
        try:
            if hasattr(block, 'keys'):
                for des in block.keys():
                    print util.tstamp(), des,
                    out_block(block[des])
                    print
            else:
                print block
        finally:
            sys.stdout=stdout


    def stdUserMessenger(self, msg="Are you ready?", but=["Ok","Quit"], level='', dct={}):
        """
        The standard (default) method to present messages to the user.
        The behaviour depends on the value of the parameter 'but'.
        If C{len(but)} (buttons are given) the funttions waits for a user answer.
        Else, the msg is presented only.

        the function also calls all additional logger functions given in C{self.logger} with 'msg'
        as argument.

        @type msg: string
        @param msg: message to display
        @type but: sequence of strings
        @param but: list of 'button' text
        @type level: string
        @param level: Mainly for future use.
                      If level is 'email', msc is send by email using fields from dct (L{util.send_email}).
        @type dct: dict
        @param dct: used for level == 'email': fields 'to', 'from', 'subject'
        @rtype: integer
        @return: with buttons: index of the selected button
                without buttons: -1
        """
        print msg
        for l in self.logger:
            l(msg)                
        if level in ['email']:
            try:
                send_email(to=dct['to'], fr=dct['from'], subj=dct['subject'], msg=msg)
            except KeyError:
                pass

        if len(but): # button(s) are given -> wait
            if not tts is None:
                tts.Speak(msg, pyTTS.tts_async)
            while True:
                key = util.keypress()
                for s in but:
                    if len(s):  # ignore empty 'buttons' 
                        if key in map(ord, s[0]+s[0].lower()):
                            if not tts is None:
                                tts.Speak(s, pyTTS.tts_purge_before_speak)
                            return but.index(s)
    #                    else:
    #                        if not tts is None:
    #                            tts.Speak('Default', pyTTS.tts_purge_before_speak)
    #                        return None
        else:
            return -1
    
    def stdUserInterruptTester(self):
        """
        The standard (default) user interrupt tester.
        Returns L{util.anykeyevent()}

        rtype: integer
        return: return value of L{util.anykeyevent()}
        """
        return util.anykeyevent()
        
    def setLogFile (self, name):
        """
        Tries to open a file with the given name with mode 'a+'
        If that fails, nothing will happen, else stdloogger will log to that file.

        @type name: string
        @param name: full name of the file to be used as logfile
        @rtype: None
        @return: None
        """
        log = None
        try:
            log = file(name, "a+")
        except:
            util.LogError (self.messenger)
        else:
            if self.logfile is not None:
                try:
                    self.logfile.close()
                except:
                    util.LogError (self.messenger)            

            self.logfilename=name
            self.logfile=log

    def setLogger(self, logger=None):
        """
        Setup the list of logger fuctions (C{self.logger})
        If C{logger is None}, C{self.stdlogger} is used.

        @type logger: None, callable, or sequence of callables
        @param logger: functions to log
        @rtype: None
        @return: None
        """
        if logger is None:
            self.logger = [self.stdlogger]
        elif type(logger) in [types.ListType, types.TupleType]:
            self.logger = [l for l in logger if callable(l)]
        else:
            if callable(logger):
                self.logger = [logger]

    def setMessenger(self, messenger):
        """
        Set function to present messages.

        @type messenger: callable
        @param messenger: the messenger (see L{self.stdUserMessenger})
        @rtype: None
        @return: None
        """
        if callable(messenger):
            self.messenger=messenger

    def setUserInterruptTester(self, tester):
        """
        Set function to test for user interrupt.

        @type tester: callable
        @param tester: the tester (see L{self.stdUserInterruptTester})
        @rtype: None
        @return: None
        """
        if callable(tester):
            self.UserInterruptTester=tester

    def setAutoSave(self, name):
        """
        Setter for the class attribute C{asname} (name of the auto save file).
        
        @type name: string
        @param name: file name oif the auto save file
        @rtype: None
        @return: None
        """
        self.asname = name

    def do_autosave(self):
        """
        Serialize 'self' using cPickle.

        The calling sequence assumed here is:
        
        script -> method of measurement class -> do_autosave

        Thus, the issued command in 'script' (grand parent of this method) is extracted and saved in C{self.ascmd}.
        This can be used to redo the command after a crash.

        @rtype: None
        @return: None
        """
        # we want to save the cmd that has been used
        # (in order to get all the calling parameters)
        try:
            self.autosave = True  # mark the state
            frame = inspect.currentframe()  # this function
            outerframes = inspect.getouterframes(frame)  # all outerframes
            caller = outerframes[1][0]  # the caller (parent)
##            cargs, cvarargs, ckwargs, clocals = inspect.getargvalues(caller)
##            print "DEBUG: cargs: %r cvarargs: %r ckwargs %r"%(cargs, cvarargs, ckwargs)
            ccframe = outerframes[2][0]  # the grand parent
            ccfname = outerframes[2][1]  # the name of the file of grand parent
            ccmodule = inspect.getmodule(ccframe) # get the module
            if ccfname == '<string>':    # we are in a 'recall-from-autosave run' (exec(cmd))
                pass   # self.ascmd already exist
            else:
                try:
                    slines, start = inspect.getsourcelines(ccmodule)
                except:
                    clen = 100
                else:
                    clen = len(slines)
                finfo = inspect.getframeinfo(ccframe, clen)
                theindex = finfo[4]
                lines = finfo[3]
                theline = lines[theindex]  # the current line
                cmd = theline
                # the command can be a multi line command
                # the idea here is to check if we can compile the line(s)
                for i in range(theindex-1, 0, -1):
                    line = lines[i]
                    try:
                        compile (cmd.lstrip(), '<string>', 'exec')
                    except SyntaxError:
                        cmd = line + cmd
                    else:
                        break
                self.ascmd = cmd.lstrip()
##                print "DEBUG: ascmd: %s"%self.ascmd 
##                for _arg in cargs:
##                    _argstr='%s=%r'%(_arg, clocals[_arg])
##                    print "DEBUG: argstr: %s"%_argstr 
##                if not ckwargs is None:
##                    try:
##                        ckwargs[0]
##                    except:
##                        ckwargs=(ckwargs,)
##                    for _kw in ckwargs:
##                        self.ascmd=self.ascmd.replace('**%s'%_kw, '**%s'%repr(clocals[_kw]))
            # now, we can serialize 'self'
            try:
                try:
                    if self.asname[-3:] == '.gz':  # gzip
                        pfile = gzip.open(self.asname,"wb")
                    else:
                        pfile = file(self.asname,"wb")   # regular pickle                     
                    cPickle.dump(self, pfile, 2)
                    self.lastautosave = time.time()
                except:
                    util.LogError (self.messenger)
            finally:
                try:
                    pfile.close()
                except:
                    util.LogError (self.messenger)            
                
        finally:        
            self.autosave = False
            del frame
            del outerframes
            del caller
            del ccframe
            del ccmodule

    def stdPreUserEvent(self):
        """
        Just calls L{util.unbuffer_stdin()}.
        See there...
        """
        util.unbuffer_stdin()

    def stdPostUserEvent(self):
        """
        Just calls L{util.restore_stdin()}
        See there...
        """
        util.restore_stdin()
        
    def doLeveling(self, leveling, mg, names, dct):
        """
        Perform leveling on the measurement graph.
        
        @type leveling: sequence
        @param leveling: sequence of dicts with leveling records. Each recors is a dict with keys 
        'conditions', 'actor', 'watch', 'nominal', 'reader', 'path', 'actor_min', and 'actor_max'.
        
        The meaning is:
            - condition: has to be True in order that this lewveling takes place. The condition is evaluated in the global namespace and in C{dct}.
            - actor: at the moment, this can only be a signalgenerator 'sg'
            - watch: the point in the graph to be monitored (e.g. antena input)
            - nominal: the desired value at watch
            - reader: the device reading the value for watch (e.g. forward poer meter)
            - path: Path between reader and watch
            - actor_min, actor_max: valid range for actor values
        @type mg: instance of L{device.mgraph}
        @partam mg: the measurement graph
        @type names: dict
        @param names: mapping between symbolic names and real names in the dot file
        @type dct: dict
        @param dct: namespace used for the evaluation of C{condition}  
        @rtype: L{SCUQ}
        @return: the level set at the actor 
        """
        for l in leveling:
            if eval(l['condition'], globals(), dct):
                actor = l['actor']
                watch = l['watch']
                nominal = l['nominal']
                reader = l['reader']
                path = l['path']
                ac_min = l['actor_min']
                ac_max = l['actor_max']

                if actor not in ['sg']:
                    self.messenger(util.tstamp()+" Only signal generator can be used as leveling actor.", [])
                    break
                for dev in [watch, reader]: 
                    if dev not in names:
                        self.messenger(util.tstamp()+" Device '%s' not found"%dev, [])
                        break
                c_level = device.UMDCMResult(complex(0.0,mg.zero(umddevice.UMD_dB)),umddevice.UMD_dB)
                for cpath in path:
                    if mg.find_shortest_path(names[cpath[0]],names[cpath[-1]]):
                        c_level *= mg.get_path_correction(names[cpath[0]],names[cpath[-1]], umddevice.UMD_dB)['total']
                    elif mg.find_shortest_path(names[cpath[-1]],names[cpath[0]]):
                        c_level /= mg.get_path_correction(names[cpath[-1]],names[cpath[0]], umddevice.UMD_dB)['total']
                    else:
                        self.messenger(util.tstamp()+" can't find path from %s tp %s (looked for both directions)."%(cpath[0],cpath[-1]), [])
                        break
                
                if ac_min == ac_max:
                    return self.setLevel(mg, names, ac_min)

                def __objective (x, mg=mg):
                    self.setLevel(mg, names, x)
                    actual = mg.Read([names[reader]])[names[reader]]
                    actual = device.UMDCMResult(actual)
                    cond, a, n = self.__TestLevelingCondition(actual, nominal, c_level)
                    return a-n

                l = util.secant_solve(__objective, ac_min, ac_max, nominal.get_u()-nominal.get_v(), 0.1)
                return self.setLevel(mg, names, l)
                #break  # only first true condition ie evaluated
        return None

    def setLevel(self, mg, names, l):
        sg = mg.nodes[names['sg']]['inst']
        # get unit for sg
        if mg.nodes[names['sg']].has_key('ch'):
            ch_sec = 'channel_' + str(mg.nodes['sg']['ch'])
        else:
            ch_sec = 'channel_1'
        sg_unit_str = mg.nodes[names['sg']]['inidic'][ch_sec]['unit']
        sg_unit = mg.UMD_UNITS[sg_unit_str.lower()]
        try:
            l = l.convert(sg_unit)
            l = l.get_v()
            try:
                l=l.real   # if complex -> ignore imaginary part
            except AttributeError:
                pass  # not a complex
        except AttributeError:
            pass   # not an MResult or CMResult
        is_save, message = mg.AmplifierProtect (names['sg'], names['a2'], l, sg_unit, typ='lasy')
        if not is_save:
            raise AmplifierProtectionError, message
        # set level
        lv = sg.SetLevel (l)
        #Create UMDCMResult with this level, unit
        level = device.UMDCMResult(complex(lv,mg.zero(sg_unit)), sg_unit)
        self.messenger(util.tstamp()+" Signal Generator set to %s"%(str(level)), [])
        return level

    def __TestLevelingCondition(self, actual, nominal, c_level):
        cond = True
        if hasattr(actual, "append"):  # vector
            for i in range(len(actual)):
                actual[i] *= c_level
                if hasattr(nominal[i].get_v(), 'mag'): # a complex
                    nominal[i] = nominal[i].mag()
                    actual[i] = actual[i].mag()
                actual[i] = actual[i].convert(nominal.unit)
                cond &= (nominal[i].get_l() <= actual[i].get_v() <= nominal[i].get_u())
        else:
            actual *= c_level
            if hasattr(nominal, 'mag'): # a complex
                nominal = nominal.mag()
            if hasattr(actual, 'mag'): # a complex
                actual = actual.mag()
            actual = actual.convert(nominal.unit)
            cond = (nominal.get_l() <= actual.get_v() <= nominal.get_u())
        return cond, actual.get_v(), nominal.get_v()


    def MakeDeslist(self, thedata, description):
        if description is None:
            deslist = thedata.keys()
        else:
            deslist = []
            if hasattr(description,'append'):
                #description is a list
                for des in description:
                    if thedata.has_key(des):
                        deslist.append(des)
            else:
                if thedata.has_key(description):
                    deslist.append(description)
        return deslist

    def MakeWhatlist (self, thedata, what):
        allwhat_withdupes = []
        for d in thedata.keys():
            # d: description
            allwhat_withdupes += thedata[d].keys()
        allwhat = []
        [allwhat.append(i) for i in allwhat_withdupes if not allwhat.count(i)]
    
        if what is None:
            whatlist = allwhat
        else:
            whatlist = []
            if hasattr(what,'append'):
                for w in what:
                    if w in allwhat:
                        whatlist.append(w)
            else:
                if what in allwhat:
                    whatlist.append(what)
        return whatlist

    def stdEUTStatusChecker(self, status):
        if status in ['ok', 'OK']:
            return True
        return False

class Error(Exception):
    """
    Base class for all exceptions of this module
    """
    pass

class AmplifierProtectionError(Error):
    def __init__ (self, message):
        self.message = message

##class UnintentionalRad(object):
##    twopi=2*math.pi
##    cvacuum=299792458
##    def __init__(self, min_radius):
##        self.a=min_radius
##    def ka(self, f):
##        return UnintentionalRad.twopi*f*self.a/UnintentionalRad.cvacuum
##    def chisq2fac(self, n):
##        return 0.577+math.log(n)+0.5/n
##
##class Dmax_uRad_OneCut(UnintentionalRad):
##    def __init__(self, min_radius):
##        super(Dmax_uRad_OneCut, self).__init__(min_radius)
##        self.a=min_radius
##    def n_ind(self, ka):
##        return 4*ka+2
##    def chisq2fac(self, n):
##        return super(Dmax_uRad_OneCut, self).chisq2fac(n)
##    def ka(self, f):
##        return super(Dmax_uRad_OneCut, self).ka(f)
##    def Dmax(self, f):
##        ka=self.ka(f)
##        if ka<1:
##            ka=1
##        return self.chisq2fac(self.n_ind(ka))
        
        
