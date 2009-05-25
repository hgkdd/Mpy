# -*- coding: iso-8859-1 -*-
"""Measure: Base class for other measure classes
Author: Prof. Dr. Hans Georg Krauthaeuser, hgk@ieee.org
Copyright (c) 2001-2009: All rights reserved
"""

import sys
import os
import time
import cPickle
import gzip
import re
import tempfile

from mpy.device import device
from mpy.tools import util,calling
import scuq as uq

try:
    import pyTTS
    __tts=pyTTS.Create()
    __tts.SetVoiceByName('MSMary')
except:
    __tts=None
    pass

class Measure(object):
    """Base class for measurements.
    """
    def __init__(self):
        self.asname=None
        self.ascmd=None
        self.autosave = False
        self.autosave_interval = 3600
        self.lastautosave = time.time()
        self.logger=[self.std_logger]
        self.logfile=None
        self.logfilename=None
        self.messenger=self.std_user_messenger
        self.user_interrupt_tester=self.std_user_interrupt_tester
        self.pre_user_event=self.std_pre_user_event
        self.post_user_event=self.std_post_user_event        

    def __setstate__(self, dct):
        if dct['logfilename'] is None:
            logfile = None
        else:
            logfile = file(dct['logfilename'], "a+")
        self.__dict__.update(dct)
        self.logfile = logfile
        self.messenger=self.std_user_messenger
        self.logger=[self.std_logger]
        self.user_interrupt_tester=self.std_user_interrupt_tester
        self.pre_user_event=self.std_pre_user_event
        self.post_user_event=self.std_post_user_event        

    def __getstate__(self):
        odict = self.__dict__.copy()
        del odict['logfile']
        del odict['logger']
        del odict['messenger']
        del odict['user_interrupt_tester']
        del odict['pre_user_event']
        del odict['post_user_event']        
        return odict

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
        if hasattr(item, 'keys'):  # a dict like object
            print "{",
            for k in item.keys():
                print str(k)+":",
                self.out(item[k])
            print "}",
        elif hasattr(item, 'index'):  # a list like object
            print "[",
            for i in item:
                self.out(i)
            print "]",
        elif util.issequence(item):  # other sequence 
            print "(",
            for i in item:
                self.out(i)
            print ")",
        else:
            print item,
            
    def set_autosave_interval (self, interval):
        """
        Set the intervall between auto save.

        @type intervall: number
        @param intervall: seconds between auto save
        @rtype: None
        @return: None
        """
        self.autosave_interval = interval
        
    def std_logger(self, block):
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
            assert hasattr(b, 'keys'), "Argument b has to be a dict."
            try:
                print repr(b['comment']),
            except KeyError:
                pass
            try:
                par = b['parameter']
                for des,p in par.iteritems():
                    print des,
                    out_block(p)
                try:
                    item = b['value']
                except KeyError:
                    item = None
                self.out(item)
            except KeyError:
                pass
            sys.stdout.flush()
            
        stdout = sys.stdout #save stdout
        if self.logfile is not None:
            sys.stdout = self.logfile
        try:
            try:
                for des,bd in block.iteritems():
                    print util.tstamp(), des,
                    out_block(bd)
                    print # New Line
            except AttributeError:
                print block
        finally:
            sys.stdout=stdout #restore stdout


    def std_user_messenger(self, msg="Are you ready?", but=["Ok","Quit"], level='', dct={}):
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
        If level is 'email', msg is send by email using fields from dct (L{util.send_email}).
        
        @type dct: dict
        @param dct: used for level == 'email': fields 'to', 'from', 'subject'
        @rtype: integer
        @return: with buttons: index of the selected button
                without buttons: -1
        """
        print msg
        for l in self.logger:
            l(msg)                
        if level in ('email',):
            try:
                send_email(to=dct['to'], fr=dct['from'], subj=dct['subject'], msg=msg)
            except KeyError:
                util.LogError(self.messenger)

        if len(but): # button(s) are given -> wait
            if __tts:
                __tts.Speak(msg, pyTTS.tts_async)
            while True:
                key=chr(util.keypress())
                key=key.lower()
                for s in but:
                    if s.startswith(key):
                        if __tts:
                            __tts.Speak(s, pyTTS.tts_purge_before_speak)
                        return but.index(s)
        else:
            return -1
    
    def std_user_interrupt_tester(self):
        """
        The standard (default) user interrupt tester.
        Returns L{util.anykeyevent()}

        rtype: integer
        return: return value of L{util.anykeyevent()}
        """
        return util.anykeyevent()
        
    def set_logfile (self, name):
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
            log = open (name, "a+")
        except IOError:
            util.LogError (self.messenger)
        else:
            if self.logfile is not None:
                try:
                    self.logfile.close()
                except IOError:
                    util.LogError (self.messenger)            

            self.logfilename=name
            self.logfile=log

    def set_logger(self, logger=None):
        """
        Setup the list of logger fuctions (C{self.logger})
        If C{logger is None}, C{self.std_logger} is used.

        @type logger: None, callable, or sequence of callables
        @param logger: functions to log
        @rtype: None
        @return: None
        """
        if logger is None:
            logger = [self.std_logger]
        logger=util.flatten(logger) # ensure flat list
        self.logger = [l for l in logger if callable(l)]

    def set_messenger(self, messenger):
        """
        Set function to present messages.

        @type messenger: callable
        @param messenger: the messenger (see L{self.std_user_messenger})
        @rtype: None
        @return: None
        """
        if callable(messenger):
            self.messenger=messenger

    def set_user_interrupt_tester(self, tester):
        """
        Set function to test for user interrupt.

        @type tester: callable
        @param tester: the tester (see L{self.std_user_interrupt_tester})
        @rtype: None
        @return: None
        """
        if callable(tester):
            self.user_interrupt_tester=tester

    def set_autosave(self, name):
        """
        Setter for the class attribute C{asname} (name of the auto save file).
        
        @type name: string
        @param name: file name oif the auto save file
        @rtype: None
        @return: None
        """
        self.asname = name

    def do_autosave(self, name_or_obj=None, depth=None, prefixes=None):
        """
        Serialize 'self' using cPickle.

        Assuming a calling sequence like so:
        
        script -> method of measurement class -> do_autosave

        depth = 1 (default) will set C{self.ascmd} to the command issued in the script.
        If depth is to large, the outermost command is used.

        Thus, the issued command in 'script' is extracted and saved in C{self.ascmd}.
        This can be used to redo the command after a crash.

        @rtype: None
        @return: None
        """
        if depth is None:
            depth=1
        if name_or_obj is None:
            name_or_obj=getattr(self, 'asname', None)

        # we want to save the cmd that has been used
        # (in order to get all the calling parameters)
        try:
            self.autosave = True  # mark the state
            calling_sequence = calling.get_calling_sequence(prefixes=prefixes)
            calling_sequence=[cs for cs in calling_sequence if cs != '<string>']
            #print calling_sequence
            try:
                self.ascmd=calling_sequence[depth]
            except IndexError:
                self.ascmd=calling_sequence[-1]
            if self.ascmd.startswith('exec'):
                print self.ascmd
                self.ascmd = str(re.match( r'exec.*\(.*[\'\"](.*)[\'\"].*\)', self.ascmd ).groups()[0]) # extrace arg of exec

            # now, we can serialize 'self'
            pfile=None
            if isinstance(name_or_obj, basestring):   # it's a string (filename)
                try:
                    if name_or_obj.endswith(('.gz','.zip')):  # gzip
                        pfile = gzip.open(self.asname,"wb")
                    else:
                        pfile = open(self.asname,"wb")   # regular pickle                     
                except IOError:
                    util.LogError (self.messenger)
            elif hasattr(name_or_obj, 'write'):  # file-like object
                pfile=name_or_obj
            if pfile is None:
                fd, fname=tempfile.mkstemp(suffix='.p', prefix='autosave', dir='.', text=False)
                pfile=os.fdopen(fd, 'wb')
            #print pfile, type(pfile)

                
            try:
                try:
                    cPickle.dump(self, pfile, 2)
                    self.lastautosave = time.time()
                except IOError:
                    util.LogError (self.messenger)
            finally:
                try:
                    pfile.close()
                except IOError:
                    util.LogError (self.messenger)            
        finally:
            self.autosave = False

        #print self.ascmd
                
    def std_pre_user_event(self):
        """
        Just calls L{util.unbuffer_stdin()}.
        See there...
        """
        util.unbuffer_stdin()

    def std_post_user_event(self):
        """
        Just calls L{util.restore_stdin()}
        See there...
        """
        util.restore_stdin()
        
    def do_leveling(self, leveling, mg, names, dct):
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
                    return self.set_level(mg, names, ac_min)

                def __objective (x, mg=mg):
                    self.set_level(mg, names, x)
                    actual = mg.Read([names[reader]])[names[reader]]
                    actual = device.UMDCMResult(actual)
                    cond, a, n = self.__test_leveling_condition(actual, nominal, c_level)
                    return a-n

                l = util.secant_solve(__objective, ac_min, ac_max, nominal.get_u()-nominal.get_v(), 0.1)
                return self.set_level(mg, names, l)
                #break  # only first true condition ie evaluated
        return None

    def set_level(self, mg, names, l):
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

    def __test_leveling_condition(self, actual, nominal, c_level):
        cond = True
        actual = util.flatten(actual)  # ensure lists
        nominal= util.flatten(nominal)
        for ac,nom in zip(actual,nominal):
            ac *= c_level
            if hasattr(nom.get_v(), 'mag'): # a complex
                nom = nom.mag()
                ac = ac.mag()
            ac = ac.convert(nominal.unit)
            cond &= (nom.get_l() <= ac.get_v() <= nom.get_u())
        return cond, actual.get_v(), nominal.get_v()

    def make_deslist(self, thedata, description):
        if description is None:
            description = []
        if util.issequence(description): # a sequence
            deslist = [des for des in description if des in thedata]
        else:
            if description in thedata:
                deslist=[description]
            else:
                deslist=[]
        return deslist

    def make_whatlist (self, thedata, what):
        allwhat_withdupes = util.flatten([v.keys() for v in thedata.itervalues()])
        allwhat=list(set(allwhat_withdupes))

        if what is None:
            whatlist = allwhat
        else:
            whatlist = []
            what=util.flatten(what)
            whatlist = [w for w in what if w in allwhat]
        return whatlist

    def std_eut_status_checker(self, status):
        return status in ['ok', 'OK']

class Error(Exception):
    """
    Base class for all exceptions of this module
    """
    pass

class AmplifierProtectionError(Error):
    def __init__ (self, message):
        self.message = message

        
        
