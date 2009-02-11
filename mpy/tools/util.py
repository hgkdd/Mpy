# -*- coding: iso-8859-1 -*-
"""
util: all sort of utilities.

Author: Prof. Dr. Hans Georg Krauthaeuser, hgk@ieee.org

Copyright (c) 2001-2008 All rights reserved
"""
from __future__ import division
import math, cmath, re, inspect
import types
import scipy
import ConfigParser, os
import time
import sys
import csv
import cPickle
import traceback
import pprint
import tempfile

scipy_pkgs=('interpolate','integrate','special','stats')
for p in scipy_pkgs:
    try:
        getattr(scipy,p)
    except AttributeError:
        scipy.pkgload(p)

try:
    import msvcrt
    getch = msvcrt.getch
    kbhit = msvcrt.kbhit
    def unbuffer_stdin(): pass
    def restore_stdin(): pass
except ImportError:
    try:
        import unixcrt
        getch = unixcrt.getch
        kbhit = unixcrt.kbhit
        unbuffer_stdin = unixcrt.unbuffer_stdin
        restore_stdin = unixcrt.restore_stdin 
    except ImportError:
        raise AttributeError, "cannot find kbhit/getch support"

c=2.99792458e8
mu0=4*math.pi*1e-7
eps0=1.0/(mu0*c*c)
pi=math.pi


class _Getch:
    """Gets a single character from standard input.  Does not echo to the
screen."""
    def __init__(self):
        try:
            self.impl = _GetchWindows()
        except ImportError:
            try:
                self.impl = _GetchUnix()
            except ImportError:
                self.impl = _GetchMacCarbon()

    def __call__(self): return self.impl()


class _GetchUnix:
    def __init__(self):
        import tty, sys, termios # import termios now or else you'll get the Unix version on the Mac

    def __call__(self):
        import sys, tty, termios
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(sys.stdin.fileno())
            ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return ch

class _GetchWindows:
    def __init__(self):
        import msvcrt

    def __call__(self):
        import msvcrt
        return getch()


class _GetchMacCarbon:
    """
    A function which returns the current ASCII key that is down;
    if no ASCII key is down, the null string is returned.  The
    page http://www.mactech.com/macintosh-c/chap02-1.html was
    very helpful in figuring out how to do this.  
    """
    def __init__(self):
        import Carbon
        
    def __call__(self):
        import Carbon
        if Carbon.Evt.EventAvail(0x0008)[0]==0: # 0x0008 is the keyDownMask
            return ''
        else:
            #
            # The event contains the following info:
            # (what,msg,when,where,mod)=Carbon.Evt.GetNextEvent(0x0008)[1]
            # 
            # The message (msg) contains the ASCII char which is
            # extracted with the 0x000000FF charCodeMask; this
            # number is converted to an ASCII character with chr() and 
            # returned
            #
            (what,msg,when,where,mod)=Carbon.Evt.GetNextEvent(0x0008)[1]
            
            return chr(msg & 0x000000FF)

#getch = _Getch()

class AutoSave:
    def __init__ (self, pname="autosave.p"):
        self.pname = pname

    def autosave(self, obj):
        if not (hasattr(obj,"notify_autosave") and hasattr(obj,"update_asdict")):
            return
        
        frame = inspect.currentframe()
        outerframes = inspect.getouterframes(frame)
        caller = outerframes[1][0]
        try:
            obj.notify_autosave(True)
##            args, varargs, varkw, loc = inspect.getargvalues(caller)
##            allargs = args
##            allargs.pop(0) # self
##            if not varargs is None:
##                allargs += varargs
##            if not varkw is None:
##                allargs += varkw
##            sdict={}
##            for arg in allargs:
##                sdict[arg]=caller.f_locals[arg]
###            sdict = caller.f_locals
###            sdict.update(caller.f_globals)
            ccframe = outerframes[2][0]
            ccmodule = inspect.getmodule(ccframe)
            try:
                slines, start = inspect.getsourcelines(ccmodule)
            except:
                clen = 100
            else:
                clen = len(slines)
            finfo = inspect.getframeinfo(ccframe, clen)
            theindex = finfo[4]
            lines = finfo[3]
            theline = lines[theindex]
            cmd = theline
            for i in range(theindex-1, 0, -1):
                line = lines[i]
                try:
                    compile (cmd.lstrip(), '<string>', 'exec')
                except SyntaxError:
                    cmd = line + cmd
                else:
                    break
##            for key, val in sdict.items():
##                try:
##                    cPickle.dumps(val)
##                except:
##                    del sdict[key]
##                    
##            obj.update_asdict(sdict)
            try:
                pfile = file(self.pname,"w")
                cPickle.dump(obj, pfile)
                cPickle.dump(cmd, pfile)
                pfile.close()
            except:
#                raise
                t, v, tr = sys.exc_info()
                print t, v, tr
            obj.notify_autosave(False)
        finally:        
            del frame
            del outerframes
            del caller
            del ccframe

    def recover (self):
        try:
            try:
                pfile = file(self.pname, "r")
                obj=cPickle.load(pfile)
                cmd=cPickle.load(pfile)
                cmd = cmd.lstrip()
            except:
                obj = None
                cmd = None
        finally:
            try:
                pfile.close()
            except:
                pass
        return obj, cmd


def logspace(start,stop,factor=1.01,endpoint=0,precision=2):
    """ Evenly spaced samples on a logarithmic scale.

        Return num evenly spaced samples from start to stop.  If
        endpoint=1 then last sample is stop and factor is adjusted.
    """
    if factor < 1 and stop > start:
        return []
    try:
        nf = math.log(stop/start)/math.log(factor)
    except ArithmeticError:
        return []
    if endpoint:
        nf = math.ceil(nf)
        try:
            factor = math.pow((stop/start),1/(nf))
        except ArithmeticError:
            return []
    lst = [round(start*factor**i,precision) for i in range(int(math.floor(nf))+1)]
    return lst

def logspaceN(start,stop,number,endpoint=0,precision=2):
    """ Evenly spaced samples on a logarithmic scale.

        Return num evenly spaced samples from start to stop.  If
        endpoint=1 then last sample is stop and factor is adjusted.
    """
    if number < 1 and stop > start:
        return []
    if endpoint:
        nf = number
    else:
        nf = number+1
    try:
        factor = math.pow(stop/start, 1.0/(nf-1))
    except ArithmeticError:
        return []
    lst = [round(start*factor**i,precision) for i in range(number)]
    return lst

def linspace(start,stop,step,endpoint=0,precision=2):
    """ Evenly spaced samples on a linear scale.

        Return num evenly spaced samples from start to stop.  If
        endpoint=1 then last sample is stop and step is adjusted.
    """
    if step < 0 and stop > start:
        return []
    try:
        nf = (stop-start)/step + 1
    except ArithmeticError:
        return []
    if endpoint:
        nf = math.floor(nf)
        try:
            step = (stop-start)/float(nf-1)
        except ArithmeticError:
            return []
    lst = [round(start+step*i,precision) for i in range(int(math.floor(nf)))]
    return lst

def linspaceN(start,stop,number,endpoint=0,precision=2):
    """ Evenly spaced samples on a linear scale.

        Return num evenly spaced samples from start to stop.  If
        endpoint=1 then last sample is stop and step is adjusted.
    """
    if number < 1 and stop > start:
        return []
    if endpoint:
        nf = number
    else:
        nf = number+1
    try:
        step = (stop-start)/float(nf-1)
    except ArithmeticError:
        return []
    lst = [round(start+step*i,precision) for i in range(number)]
    return lst

def logspaceTab (start, end, ftab=[3,6,10,100,1000], nftab=[20,15,10,20,20], endpoint=True):
    freqs = []
    s = start
    finished = False
    for i in range(len(ftab)):
        e = start*ftab[i]
        f = logspaceN(s,e,nftab[i],endpoint=False)
        while len(f) and f[-1]>end:  # More points as we need
            f.pop()
            finished = True
        freqs = freqs + f
        if finished:
            break
        s = e
    if endpoint and end not in freqs:
        freqs.append(end)
    return freqs

def anykeyevent():
    """
    Detects a key or function key pressed and returns its ascii or scancode.
    """
    if kbhit():
        a = ord(getch())
        #print "anykeyevent:", a
        if a == 0 or a == 224:
            b = ord(getch())
            x = a + (b*256)
            return x
        else:
            return a
    #print "anykeyevent:", None
    return None

def keypress(): 
    """
    Waits for the user to press a key. Returns the ascii code 
    for the key pressed or zero for a function key pressed.
    """                             
    while 1:
        a = ord(getch())     # get first byte of keyscan code     
        if a == 0 or a == 224:      # is it a function key?
            getch()          # discard second byte of key scan code
            return 0                # return 0
        else:
            return a                # else return ascii code
    return None

def funkeypress():
    """
    Waits for the user to press any key including function keys. Returns 
    the ascii code for the key or the scancode for the function key.
    """
    while 1:
        a = ord(getch())         # get first byte of keyscan code  
        if a == 0 or a == 224:          # is it a function key?
            b = ord(getch())     # get next byte of key scan code
            x = a + (b*256)             # cook it.
            return x                    # return cooked scancode
        else:
            return a                    # else return ascii code
    return None

def getIndex(val,tab):
    """ 
    returns the index so that val is between tab[index-1], tab[index].
    tab is a sorted list
    """
    if len(tab) == 0:
        return -1
    incr = tab[-1]>tab[0]  # increasing
    if incr:
        #list of all items in tab <= val
        l=[t for t in tab if val>=t]
        #l=filter(lambda t: val >= t, tab)
    else:
        #list of all items in tab >= val
        l=[t for t in tab if val<=t]
        #l=filter(lambda t: val <= t, tab)
    if not len(l):
        index = 0
    else:
        index = tab.index(l[-1])+1
    try:
        tab[index]
    except KeyError:
        index=None
    return index

def combinations(L):
    N = len(L)
    if N == 0:
        return []
    elif N == 1:
        return [ L[0][i:i+1] for i in xrange(0,len(L[0]))]
    else:
        return [ L[0][i:i+1] + subcomb for i in xrange(0, len(L[0])) for subcomb in combinations( L[1:] )]

def LookForUserInterrupt():
    # look for user interupt
    if anykeyevent():
        print "Execution interrupted by user."
        print "Press any key when ready to measure or 'q' to quit."
        if keypress() in map(ord, 'qQ'):
            return True
    return None

def secant_solve(f,x1,x2,ftol,xtol):
    f1 = f(x1)
    if abs(f1) <= ftol:
        return x1        # already effectively zero
    f2 = f(x2)
    if abs(f2) <= ftol:
        return x2        # already effectively zero
    while abs(x2 - x1) > xtol :
        slope = (f2 - f1)/(x2 - x1)
        if slope == 0:
        	return None
#      sys.stderr.write("Division by 0 due to vanishing slope - exit!\n")
#      sys.exit(1)
        x3 = x2 - f2/slope               # the new approximate zero
        f3 = f(x3)                       # and its function value
        if abs(f3) <= ftol:
            break
        x1,f1 = x2,f2                    # copy x2,f2 to x1,f1
        x2,f2 = x3,f3                    # copy x3,f3 to x2,f2
    return x3
       
def mean(x, zero=0.0):
    mu = sum(x, zero)
    return mu/len(x)

def interactive(banner=None):
    import code
    # use exception trick to pick up the current frame
    try:
        raise None
    except:
        frame = sys.exc_info()[2].tb_frame.f_back

    # evaluate commands in current namespace
    namespace = frame.f_globals.copy()
    namespace.update(frame.f_locals)

    code.interact(banner=banner, local=namespace)

def tstamp():
    return time.strftime('%c')        

def frange(start, end=None, inc=None):
    "A range function, that does accept float increments..."

    if end == None:
        end = start + 0.0
        start = 0.0

    if inc == None:
        inc = 1.0

    L = []
    while 1:
        next = start + len(L) * inc
        if inc > 0 and next >= end:
            break
        elif inc < 0 and next <= end:
            break
        L.append(next)
        
    return L

class OutputError:
    def __init__(self):
        self.clear() 
    def write (self, obj):
        self.values.append(obj)
    def readlines(self, lines = None):
        if (lines is None) or (lines > len(self.values)):
            lines = len(self.values)
        ret = self.values[:lines]
        return ret
    def readline(self):
        if self.__lcount__ > len (self.values):
            return []
        self.__lcount__ += 1
        return self.values[self.__lcount__-1]
    def seek (self, count = 0):
        count = min(count, len(self.values))
        self.__lcount__ = count
    def clear (self):
        self.values = []
        self.__lcount__ = 0

def LogError(Messenger):
    out = OutputError()
    (ErrorType,ErrorValue,ErrorTB)=sys.exc_info()
    traceback.print_exc(ErrorTB, out)
    error = out.readlines()
    for err in error:
        err = err.replace ('\n', '; ')
    err_msg = "%s ***Error: %s"%(tstamp(), ''.join(error))
    Messenger (msg = err_msg, but = [])

def idxset(n, m):
    """
    returns a list of length n with equidistant elem of range(m)
    """
    if n==0:
        return []
    if n>=m:
        return range(m)
    step=1.0*m/n
    lst = []
    for i in range(n):
        lst.append(int(round(i*step)))
    return lst[:]

def removefrom (obj, pat):
    if re.search(pat, str(type(obj))) is not None:
        # the obj itself matchs the pattern -> remove it
        del obj
        return

    if type(obj) in types.StringTypes:
        return

    # a dict?
    try:
        for k,v in obj.items():
            if re.search(pat, str(type(v))) is not None:
                del obj[k]
            else:
                removefrom (v, pat)
        return
    except:
        pass
    # a sequence
    try:
        for o in obj:
            removefrom(o, pat)
        return
    except:
        pass
    return

def issequence(a):
    return hasattr(a, '__iter__') and not isinstance(a, basestring) 

def flatten(a):
    if not issequence(a): 
        return [a]  # be sure to return a list
    if len(a)==0:
        return []
    return flatten(a[0])+flatten(a[1:])

def send_email (to=None, fr=None, subj='a message from umdutil', msg=''):
    pass

def get_var_from_nearest_outerframe(varstr):
    __frame = inspect.currentframe()
    __outerframes = inspect.getouterframes(__frame)
    var = None
    for of in __outerframes:
        #print "outerframe is:"
        #print of
        for name,value in of[0].f_locals.items()+of[0].f_globals.items():
            # look for the name
            if name == varstr:
                #print "found name %s"%varstr
                #print "value:", value
                var = value
                break
            # perhaps its in a dictionary
            try:
                var = value[varstr]
                #print "found key %s in dict with name %s"%(varstr,name)
                #print "value:", var
                break
            except (KeyError,TypeError,AttributeError):
                continue
        if var:
            #print "got it!"
            break
    del __outerframes
    del __frame
    if not var:
        #print "not found!"
        pass
    return var

def map2singlechar(i):
    tup=tuple("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz")
    try:
        return tup[i]
    except IndexError:
        return str(i)
    
def format_block(block,nlspaces=0):
    '''Format the given block of text, trimming leading/trailing
    empty lines and any leading whitespace that is common to all lines.
    The purpose is to let us list a code block as a multiline,
    triple-quoted Python string, taking care of
    indentation concerns.'''

    import re

    # separate block into lines
    lines = str(block).split('\n')

    # remove leading/trailing empty lines
    while lines and not lines[0]:  del lines[0]
    while lines and not lines[-1]: del lines[-1]

    # look at first line to see how much indentation to trim
    ws = re.match(r'\s*',lines[0]).group(0)
    if ws:
        lines = map( lambda x: x.replace(ws,'',1), lines )

    # remove leading/trailing blank lines (after leading ws removal)
    # we do this again in case there were pure-whitespace lines
    while lines and not lines[0]:  del lines[0]
    while lines and not lines[-1]: del lines[-1]

    # account for user-specified leading spaces
    flines = ['%s%s' % (' '*nlspaces,line) for line in lines]

    return '\n'.join(flines)+'\n'
