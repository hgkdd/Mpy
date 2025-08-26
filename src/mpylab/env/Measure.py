# -*- coding: utf-8 -*-
"""This is :mod:`mpylab.env.Measure` with :class:`mpylab.env.Measure.Measure` being the base class for e.g. :class:`mpylab.env.msc.MSC.MSC`

   :author: Hans Georg Krauthäuser (main author)
   :copyright: All rights reserved
   :license: no licence yet
"""

import gzip
import os
import pickle
import sys
import tempfile
import time

try:
    import mpylab.tools.unixcrt as crt
except ImportError:
    class CRT:
        def unbuffer_stdin(self):
            pass

        def restore_stdin(self):
            pass

    crt = CRT()

from mpylab.tools import util, calling
from scuq.quantities import Quantity
from scuq.si import WATT

try:
    import pyttsx3
    _tts = pyttsx3.init()
    _tts.setProperty('volume', 1.0)
    vs = _tts.getProperty('voices')
    for v in vs:
        if 'en_GB' in v.languages:  # take first british speaker
            _tts.setProperty('voice', v.id)
            break
    #import festival
    #festival.execCommand("(voice_en1_mbrola)")
    #_tts = festival
    #_tts.say = _tts.sayText
    #def __runAndWait():
    #    pass
    #_tts.runAndWait = __runAndWait
except ImportError:
    #festival = None
    pyttsx3 = None
    _tts = None


class Measure(object):
    """Base class for measurements.
    """

    def __init__(self, SearchPaths=None):
        """constructor"""
        if SearchPaths is None:
            SearchPaths = [os.getcwd()]
        self.SearchPaths = SearchPaths
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

    def __setstate__(self, dct):
        """used instead of __init__ when instance is created from pickle file"""
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

    def __getstate__(self):
        """prepare a dict for pickling"""
        odict = self.__dict__.copy()
        del odict['logfile']
        del odict['logger']
        del odict['messenger']
        del odict['UserInterruptTester']
        del odict['PreUserEvent']
        del odict['PostUserEvent']
        return odict

    def wait(self, delay, dct, uitester, intervall=0.1):
        """A wait function that can de interrupted.

           - *delay*: seconds to wait
           - *dct*: namespace used by uitester (:meth:`Measure.stdUserInterruptTester`)
           - *uitester*: User-Interupt Tester
           - *intervall*: seconds to sllep between uitester calls

           Return: *None*
        """
        start = time.time()
        delay = abs(delay)
        intervall = abs(intervall)
        while time.time() - start < delay:
            uitester(dct)
            time.sleep(intervall)

    def out(self, item):
        """Helper function for all output functions.
           
           Prints *item* recursively all in one line.
           
           The parameter *item* can be:

              - a :class:`dict` of items (`hasattr(item, 'keys')==True`)
              - a :class:`list` of items (`hasattr(item, 'index')==True`)
              - a sequence of items (using :meth:`mpylab.tools.util.issequence`)
              - or anything else (will be printed via `print item,`)

           The return value is `None`.
        """
        if hasattr(item, 'keys'):  # a dict like object
            print("{", end=' ')
            for k in list(item.keys()):
                print(str(k) + ":", end=' ')
                self.out(item[k])
            print("}", end=' ')
        elif hasattr(item, 'append'):  # a list like object
            print("[", end=' ')
            for i in item:
                self.out(i)
            print("]", end=' ')
        elif util.issequence(item):  # other sequence 
            print("(", end=' ')
            for i in item:
                self.out(i)
            print(")", end=' ')
        else:
            print(item, end=' ')

    def set_autosave_interval(self, interval):
        """Set the intervall between auto save.

           *intervall*: seconds between auto save

           This method returns `None`.
        """
        self.autosave_interval = interval

    def stdlogger(self, block, *args):
        """The standard method to write messages to log file.

           Print *block* to `self.logfile` or to `stdout` (if `self.logfile` is `None`).
           If *block* has attribute `keys` (i.e. is a :class:`dict`), the elements are
           processed with the local function :meth:`out_block`. Else, the block is printed
           directly.

           Parameter *block*: object to log

           Return value: `None`
        """

        def out_block(b):
            """Helper function to log something.
            """
            assert hasattr(b, 'keys'), "Argument b has to be a dict."
            try:
                print(repr(b['comment']), end=' ')
            except KeyError:
                pass
            try:
                par = b['parameter']
                for des, p in par.items():
                    print(des, end=' ')
                    out_block(p)
                try:
                    item = b['value']
                except KeyError:
                    item = None
                self.out(item)
            except KeyError:
                pass
            sys.stdout.flush()

        stdout = sys.stdout  # save stdout
        if self.logfile is not None:
            sys.stdout = self.logfile
        try:
            try:
                for des, bd in block.items():
                    print(util.tstamp(), des, end=' ')
                    out_block(bd)
                    print()  # New Line
            except AttributeError:
                print(block)
        finally:
            sys.stdout = stdout  # restore stdout

    def stdUserMessenger(self, msg="Are you ready?", but=None, level='', dct=None):
        """The standard (default) method to present messages to the user.

           The behaviour depends on the value of the parameter *but*.
           If `len(but)` (buttons are given) the funttions waits for a user answer.
           Else, the *msg* is presented only.

           The function also calls all additional logger functions given in `self.logger` with the same arguments.

           Parameters:

              - *msg*: message to display
              - *but*: sequence with the text strings of the buttons
              - *level*: to indicate something (not used in the standard logger)
              - *dct*: a :class:`dict` with further parameters (not used in the standard logger)
        
           Return value: the index of the selected button (starting from `0`), or `-1` if `len(but)` is `False`.
        """
        if but is None:
            but = ["Ok", "Quit"]
        if dct is None:
            dct = {}
        print(msg)
        for l in self.logger:
            l(msg, but, level, dct)
        if level in ('email',):
            try:
                util.send_email(to=dct['to'], fr=dct['from'], subj=dct['subject'], msg=msg)
            except (NameError, KeyError):
                util.LogError(self.messenger)

        if len(but):  # button(s) are given -> wait
            if _tts:
                _tts.say(msg)
                _tts.runAndWait()
            while True:
                key = chr(util.keypress())
                key = key.lower()
                for s in but:
                    if s.lower().startswith(key):
                        if _tts:
                            _tts.say(s)  # , pyTTS.tts_purge_before_speak)
                            _tts.runAndWait()
                        return but.index(s)
        else:
            return -1

    @staticmethod
    def stdUserInterruptTester():
        """The standard (default) user interrupt tester.

           Returns return value of :meth:`mpylab.util.anykeyevent()`
        """
        return util.anykeyevent()

    def set_logfile(self, name):
        """Tries to open a file with the given name with mode `'a+'`.
           If this fails, nothing will happen, else :meth:`stdloogger` will log to this file.

           Parameter *name*: full qualified name of the file to be used as logfile

           Return: `None`
        """
        import unicodedata
        import string
        import re
        validFilenameChars = "-_.() %s%s" % (string.ascii_letters, string.digits)

        def slugify(value, allow_unicode=False):
            """
            Taken from https://github.com/django/django/blob/master/django/utils/text.py
            Convert to ASCII if 'allow_unicode' is False. Convert spaces or repeated
            dashes to single dashes. Remove characters that aren't alphanumerics,
            underscores, or hyphens. Convert to lowercase. Also strip leading and
            trailing whitespace, dashes, and underscores.
            """
            value = str(value)
            if allow_unicode:
                value = unicodedata.normalize('NFKC', value)
            else:
                value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
            value = re.sub(r'[^\w\s-]', '', value.lower())
            return re.sub(r'[-\s]+', '-', value).strip('-_')

        def removeDisallowedFilenameChars(filename):
            try:
                cleanedFilename = unicodedata.normalize('NFKD', filename).encode('ASCII', 'ignore')
            except TypeError:
                cleanedFilename = unicodedata.normalize('NFKD', str(filename)).encode('ASCII', 'ignore')
            return ''.join(c for c in cleanedFilename if c in validFilenameChars)

        log = None
        # name = removeDisallowedFilenameChars(name)
        name = slugify(name)
        try:
            log = open(name, "a+")
        except IOError:
            util.LogError(self.messenger)
        else:
            if self.logfile is not None:
                try:
                    self.logfile.close()
                except IOError:
                    util.LogError(self.messenger)

            self.logfilename = name
            self.logfile = log

    def set_logger(self, logger=None):
        """Set up the list of logger fuctions (`self.logger`).

           If `logger is None`, :meth:`stdlogger` is used.

           Parameter *logger*: list of functions called to log events
        
           Return: *None*
        """
        if logger is None:
            logger = [self.stdlogger]
        logger = util.flatten(logger)  # ensure flat list
        self.logger = [l for l in logger if callable(l)]

    def set_messenger(self, messenger):
        """Set function to present messages.

           Parameter *messenger*: the messenger (see :meth:`stdUserMessenger`)

           Return: *None*
        """
        if callable(messenger):
            self.messenger = messenger

    def set_user_interrupt_Tester(self, tester):
        """Set function to test for user interrupt.

           Parameter *tester*: the user interrupt Tester (see :meth:`stdUserInterruptTester`)

           Return: *None*
        """
        if callable(tester):
            self.UserInterruptTester = tester

    def set_autosave(self, name):
        """Setter for the class attribute *asname* (name of the auto save file).
        
           Parameter *name*: file name oif the auto save file

           Return: *None*
        """
        self.asname = name

    def do_autosave(self, name_or_obj=None, depth=None, prefixes=None):
        """Serialize *self* using :mod:`pickle`.

           Assuming a calling sequence like so::
        
              script -> method of measurement class -> do_autosave

           `depth = 1` (default) will set *self.ascmd* to the command issued in the script.
           
           If depth is too large, the outermost command is used.

           Thus, the issued command in *script* is extracted and saved in *self.ascmd*.
           This can be used to redo the command after a crash.

           Return: *None*
        """
        if depth is None:
            depth = 1
        if name_or_obj is None:
            name_or_obj = getattr(self, 'asname', None)

        # we want to save the cmd that has been used
        # (in order to get all the calling parameters)
        try:
            self.autosave = True  # mark the state
            calling_sequence = calling.get_calling_sequence(prefixes=prefixes)
            calling_sequence = [cs for cs in calling_sequence if cs != '<string>']
            # print calling_sequence
            try:
                ascmd = calling_sequence[depth]
            except IndexError:
                ascmd = calling_sequence[-1]
            if ascmd.startswith('exec'):
                # print self.ascmd
                ascmd = ascmd[ascmd.index('(') + 1: ascmd.rindex(')')].strip()  # part between brackets
                var = util.get_var_from_nearest_outerframe(ascmd)
                if var:
                    ascmd = var
            self.ascmd = ascmd
            # print "Measure.py; 363:", self.ascmd
            # now, we can serialize 'self'
            pfile = None
            if isinstance(name_or_obj, str):  # it's a string (filename)
                try:
                    if name_or_obj.endswith(('.gz', '.zip')):  # gzip
                        pfile = gzip.open(self.asname, "wb")
                    else:
                        pfile = open(self.asname, "wb")  # regular pickle
                except IOError:
                    util.LogError(self.messenger)
            elif hasattr(name_or_obj, 'write'):  # file-like object
                pfile = name_or_obj
            if pfile is None:
                fd, fname = tempfile.mkstemp(suffix='.p', prefix='autosave', dir='.', text=False)
                pfile = os.fdopen(fd, 'wb')
            # print pfile, type(pfile)

            try:
                try:
                    pickle.dump(self, pfile, 2)
                    self.lastautosave = time.time()
                except IOError:
                    util.LogError(self.messenger)
            finally:
                try:
                    pfile.close()
                except IOError:
                    util.LogError(self.messenger)
        finally:
            self.autosave = False

        # print self.ascmd

    @staticmethod
    def stdPreUserEvent():
        """Just calls :meth:`mpylab.tools.unixcrt.unbuffer_stdin()`.
           See there...
        """
        crt.unbuffer_stdin()

    @staticmethod
    def stdPostUserEvent():
        """Just calls :meth:`mpylab.tools.unixcrt.restore_stdin()`
           See there...
        """
        crt.restore_stdin()

    # def do_leveling(self, leveling, mg, names, dct):
    # """Perform leveling on the measurement graph.

    # - *leveling*: sequence of dicts with leveling records. Each record is a dict with keys
    # 'conditions', 'actor', 'watch', 'nominal', 'reader', 'path', 'actor_min', and 'actor_max'.

    # The meaning is:

    # - condition: has to be True in order that this lewveling takes place. The condition is evaluated in the global namespace and in C{dct}.
    # - actor: at the moment, this can only be a signalgenerator 'sg'
    # - watch: the point in the graph to be monitored (e.g. antena input)
    # - nominal: the desired value at watch
    # - reader: the device reading the value for watch (e.g. forward poer meter)
    # - path: Path between reader and watch
    # - actor_min, actor_max: valid range for actor values

    # - *mg*: the measurement graph
    # - *names*: mapping between symbolic names and real names in the dot file
    # - *dct*: namespace used for the evaluation of *condition*

    # Return: the level set at the actor
    # """
    # for l in leveling:
    # if eval(l['condition'], globals(), dct):
    # actor = l['actor']
    # watch = l['watch']
    # nominal = l['nominal']
    # reader = l['reader']
    # path = l['path']
    # ac_min = l['actor_min']
    # ac_max = l['actor_max']

    # if actor not in ['sg']:
    # self.messenger(util.tstamp()+" Only signal generator can be used as leveling actor.", [])
    # break
    # for dev in [watch, reader]:
    # if dev not in names:
    # self.messenger(util.tstamp()+" Device '%s' not found"%dev, [])
    # break
    # c_level = device.UMDCMResult(complex(0.0,mg.zero(umddevice.UMD_dB)),umddevice.UMD_dB)
    # for cpath in path:
    # if mg.find_shortest_path(names[cpath[0]],names[cpath[-1]]):
    # c_level *= mg.get_path_correction(names[cpath[0]],names[cpath[-1]], umddevice.UMD_dB)['total']
    # elif mg.find_shortest_path(names[cpath[-1]],names[cpath[0]]):
    # c_level /= mg.get_path_correction(names[cpath[-1]],names[cpath[0]], umddevice.UMD_dB)['total']
    # else:
    # self.messenger(util.tstamp()+" can't find path from %s tp %s (looked for both directions)."%(cpath[0],cpath[-1]), [])
    # break

    # if ac_min == ac_max:
    # return self.set_level(mg, names, ac_min)

    # def __objective (x, mg=mg):
    # self.set_level(mg, names, x)
    # actual = mg.Read([names[reader]])[names[reader]]
    # actual = device.UMDCMResult(actual)
    # cond, a, n = self.__test_leveling_condition(actual, nominal, c_level)
    # return a-n

    # l = util.secant_solve(__objective, ac_min, ac_max, nominal.get_u()-nominal.get_v(), 0.1)
    # return self.set_level(mg, names, l)
    # #break  # only first true condition ie evaluated
    # return None

    def set_level(self, mg, l, leveler=None):
        """
        """

        sg = mg.instrumentation[mg.name.sg]
        # l is in dBm -> convert to WATT
        l = Quantity(WATT, 10 ** (0.1 * l) * 0.001)

        if leveler is None:  # try to use instance leveler
            try:
                leveler = self.leveler_inst  # (**self.leveler_par)
            except AttributeError:
                pass  # stay with None

        if leveler:  # use MaxSafe
            l = min(l, leveler.MaxSafe)
        err, lv = sg.SetLevel(l)

        # is_save, message = mg.AmplifierProtect (names['sg'], names['a2'], l, sg_unit, typ='lasy')
        # if not is_save:
        #    raise AmplifierProtectionError, message

        self.messenger(util.tstamp() + " Signal Generator set to %s" % (lv), [])
        return lv

    # def __test_leveling_condition(self, actual, nominal, c_level):
    # cond = True
    # actual = util.flatten(actual)  # ensure lists
    # nominal= util.flatten(nominal)
    # for ac,nom in zip(actual,nominal):
    # ac *= c_level
    # if hasattr(nom.get_v(), 'mag'): # a complex
    # nom = nom.mag()
    # ac = ac.mag()
    # ac = ac.convert(nominal.unit)
    # cond &= (nom.get_l() <= ac.get_v() <= nom.get_u())
    # return cond, actual.get_v(), nominal.get_v()

    def make_deslist(self, thedata, description):
        if description is None:
            description = list(thedata.keys())
        if util.issequence(description):  # a sequence
            deslist = [des for des in description if des in thedata]
        else:
            if description in thedata:
                deslist = [description]
            else:
                deslist = []
        return deslist

    def make_whatlist(self, thedata, what):
        allwhat_withdupes = util.flatten([list(v.keys()) for v in thedata.values()])
        allwhat = list(set(allwhat_withdupes))

        if what is None:
            whatlist = allwhat
        else:
            whatlist = []
            what = util.flatten(what)
            whatlist = [w for w in what if w in allwhat]
        return whatlist

    @staticmethod
    def stdEutStatusChecker(status):
        return status in ['ok', 'OK']


class Error(Exception):
    """Base class for all exceptions of this module
    """
    pass


class AmplifierProtectionError(Error):
    def __init__(self, message):
        self.message = message
