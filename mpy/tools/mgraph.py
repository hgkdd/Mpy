import os
import inspect
import re
import ConfigParser
import measure.tools.dot as dot
import measure.device.device as device #new_umddevice as device
from scuq import *
from measure.device.aunits import *

def getUMDPath():
    env = os.environ
    umdpath = env.setdefault('UMDPATH', os.path.curdir)
    return umdpath

def OpenFileFromPath(name, mode='r', path='.'):
    _file = None
    #print type(name), type(path)
    #print "Name:", name, "Path:", repr(path), "End"
    name=os.path.normpath(name)
    if os.path.isabs(name):  # absolute pathname
        try:
            _file = open(name, mode)
        except:
            _file = None
        return _file
    reldir, fname = os.path.split(name)  # seperate file name
    for _dir in path.split(';'):
        # first, try if file (may be with a relativ path) is in thar dir
        try:
            _file = open(os.path.join(_dir,name), mode)
        except:
            _file = None
        else:
            return _file
        for root, dirs, files in os.walk(_dir):
            for f in files:
                if f == fname:  # we got it
                    try:
                        _file = open(os.path.join(root,f), mode)
                    except:
                        _file = None
                    return _file
    # file not found
    return _file 

def GetFileFromPath(name, path='.'):
    name=os.path.normpath(name)
    name=os.path.abspath(name)
    if os.path.isfile(name):
        return name
    else:
        reldir, fname = os.path.split(name)  # seperate file name
        for _dir in path.split(os.pathsep):
            # first, try if file (may be with a relativ path) is in thar dir
            if os.path.isfile(os.path.join(_dir,name)):
                return os.path.join(_dir,name)
            for root, dirs, files in os.walk(_dir):
                for f in files:
                    if f == fname:  # we got it
                        return os.path.join(root,f)
    # file not found
    return None 


class MGraph:
    def __getstate__ (self):
        import copy
        #import pprint
        odict={}
        src = self.__dict__
        odict['graph']=src['graph'].copy()        
        odict['nodes']={}
        for k, n in src['nodes'].items():
            odict['nodes'][k] = {}
            for key,val in n.items():
                if not key == 'inst':
                    odict['nodes'][k][key] = copy.copy(val)
        #pprint.pprint(odict)
        return odict

    def __setstate__ (self, dct):
        self.__dict__.update(dct)
##        __frame = inspect.currentframe()
##        __outerframes = inspect.getouterframes(__frame)
##        __caller = __outerframes[1][0]
##        self.CallerGlobals = __caller.f_globals
##        self.CallerLocals = __caller.f_locals

    def __init__(self, dotfile=None, n={}, g={}, globals=None, locals=None):
        if dotfile is None:
            self.nodes = n.copy()
            self.graph = g.copy()
        else:
            (self.nodes, self.graph) = self.ReadDOTFile (dotfile)
            #print "dotfile: %s, nodes: %r, graph: %r"%(dotfile, self.nodes, self.graph)
        self.dotfile=dotfile
        
        # no dict given -> try globals in caller frame
##        __frame = inspect.currentframe()
##        __outerframes = inspect.getouterframes(__frame)
##        __caller = __outerframes[1][0]
##        if globals is None:
##            self.CallerGlobals = __caller.f_globals
##        else:
##            self.CallerGlobals = globals()
##        if locals is None:
##            self.CallerLocals = __caller.f_locals
##        else:
##            self.CallerLocals = locals()
##        self.CreateDevices () 

    def __str__(self):
        what=['graph', 'nodes']
        ret=''
        for w in what:
            ret += '# %s\n'%w
            ret += pprint.pformat(getattr(self,w))
            ret += '\n'
        return ret
    
    def ReadDOTFile(self, dotfile):
        """
        reads a graph description in the DOT language
        and returns a tuple (n,g) of nodes (dict) and graph (dict)
        Input: dotfile -> file to open; may be abspath, relpath or filename
                          uses ENV variable from getUMDPath (UMDPATH) to search file
                          Exception is raised if file was not found
        Output: (n,g): n dict with node keys from dotfile
                       value for each key is a dict with keys, vals from the node arguments taken from the dot file 
        """
        umdpath = getUMDPath()
        _file = OpenFileFromPath (dotfile, 'r', umdpath)
        try:
            gr = _file.read()
            _file.close()
        except:
            gr = None
            raise
        if gr is None:
            (n,g) = {}, {}
        else:
            #print gr
            (n, g) = dot.parse ("graph", gr )
            #print n,g
        return (n,g)

    def zero (self, unit):
        """
        Returns zero 
        """
        return 0.0

    def find_path(self, start, end, path=[]):
        """
        Returns a path from start to end.
        Ignores nodes with key isActive = False.
        """
        path = path + [start]     # add start to path
        if start == end:          # finished
            return path
        if not self.graph.has_key(start): # start not in graph
            return None
        for node in self.graph[start]:    # for all nodes connected to start
            can_traverse = True
            edge = self.graph[start][str(node)] 
            if edge.has_key('dev'):
                edgedev = self.nodes[edge['dev']] 
                if edgedev.has_key('isActive'):
                    if not edgedev['isActive']:
                        can_traverse = False
            if can_traverse and node not in path:
                newpath = self.find_path(node, end, path)  # recursion
                if newpath:
                    return newpath
        return None

    def find_all_paths(self, start, end, path=[]):
        """
        Find all paths in graph from start to end (without circles)
        Ignores nodes with key isActive = False.
        """
        path = path + [start]
        if start == end:
            return [path]
        if not self.graph.has_key(start):
            return []
        paths = []
        for node in self.graph[start]:
            can_traverse = True
            edge = self.graph[start][str(node)] 
            if edge.has_key('dev'):
                edgedev = self.nodes[edge['dev']] 
                if edgedev.has_key('isActive'):
                    if not edgedev['isActive']:
                        can_traverse = False
            if can_traverse and node not in path:
                newpaths = self.find_all_paths(node, end, path)
                for newpath in newpaths:
                    paths.append(newpath)
        return paths

    def find_shortest_path(self, start, end, path=[]):
        """
        returns the shortest path from start to end
        Ignores nodes with key isActive = False.
        """
        path = path + [start]
        if start == end:
            return path
        if not self.graph.has_key(start):
            return None
        shortest = None
        for node in self.graph[start]:
            can_traverse = True
            edge = self.graph[start][str(node)] 
            if edge.has_key('dev'):
                edgedev = self.nodes[edge['dev']] 
                if edgedev.has_key('isActive'):
                    if not edgedev['isActive']:
                        can_traverse = False
            if can_traverse and node not in path:
                newpath = self.find_shortest_path(node, end, path)
                if newpath:
                    if not shortest or len(newpath) < len(shortest):
                        shortest = newpath
        return shortest

    def get_path_correction (self, start, end, unit=None):
        """
        Returns a dict with the corrections for all edges
        key 'total' gives the total correction.
        All corrections are SCUQ objects.
        """
        assert unit in (AMPLITUDERATIO, POWERRATIO)
        result = {}
        all_paths = self.find_all_paths (start, end)
        #print all_paths
        Total = quantities.Quantity (unit, 0.0)
        for p in all_paths:
            corr = []
            for i in range(len(p)-1):
                left  = p[i]
                right = p[i+1]
                corr.append(self.graph[left][right])
            # totals in that path
            TotalPath = None
            #print corr
            for n in corr:
                #print n
                if (n.has_key('dev')):
                    # the edge
                    dev = str(n['dev'])
                    # edge instance
                    inst = self.nodes[str(n['dev'])]['inst']
                    what = str(n['what'])
                    try:
                        cmds = ['getData', 'GetData']
                        stat = -1
                        for cmd in cmds:
                            #print cmd
                            if hasattr(inst, cmd):
                                #print "Vor getattr", getattr(inst,cmd)
                                stat, result[dev] = getattr(inst,cmd)(what)
                                #print "Nach getattr", stat
                                break
                        if stat < 0:
                            raise UserWarning, 'Failed to getData: %s, %s'%(dev, what)  
                    except AttributeError:
                        # function not callable
                        # 
                        raise UserWarning, 'Failed to getData %s, %s'%(dev, what) 
                    # store the values unconverted
                    #print dev, result[dev]
                    r=result[dev].get_value(unit)
                    if TotalPath:
                        TotalPath *= r
                    else:
                        TotalPath=r
            

            # for different paths between two points, s parameters have
            # to be summed.
            #print TotalPath
            #for k,v in result.items():
            #    print k,v
            Total += quantities.Quantity(unit, TotalPath)

        result['total'] = Total        
        return result

    def EvaluateConditions (self, doAction=True):
        """
        Set key isActice in nodes argument depending on the condition given in the graph
        """
        __frame = inspect.currentframe()
        __outerframes = inspect.getouterframes(__frame)
        __caller = __outerframes[1][0]
        for n in self.nodes:
            #print "Node:", n, self.nodes[n] 
            if self.nodes[n].has_key('condition'):
                stmt = "(" + str(self.nodes[n]['condition']) + ")"
                #print " Cond:", stmt, " = ", 
                cond = eval (stmt, __caller.f_globals, __caller.f_locals)
                #print cond
                if cond:
                    self.nodes[n]['isActive']=True
                    if doAction and self.nodes[n].has_key('action'):
                        act = self.nodes[n]['action']
                        #print str(act)
                        #print self.CallerLocals['f']
                        #print act
                        exec str(act) # in self.CallerGlobals, self.CallerLocals
                else:
                    self.nodes[n]['isActive']=False
            else:
                self.nodes[n]['isActive']=True
        del __caller
        del __outerframes
        del __frame

    def CreateDevices (self):
        """
        Should be called once after creating the instance.
        - Sets isActive = True for all nodes
        - Reads the ini-file (if ini atrib is present)
        - Creates the device instances of all nodes and save the variable in the nodes dict
          (nodes[key]['inst'])
        Returns a dict with keys from the graphs nodes names and val are the device instances
        Can be used to create local references like so:
            for k,v in ddict.items():
                globals()['k']=v
        """
        ddict={}
        for key,attribs in self.nodes.items():
            attribs['isActive'] = True
            try:
                ini = attribs['ini']   # the ini file name
            except KeyError:    
                attribs['inst'] = None # no ini file, no device
                continue            
            #print "ini:", self.nodes
            attribs['inidic'] = self.__parse_ini (ini)  # parse the ini file and save it as dict in the nodes dict
            try:
                typetxt = attribs['inidic']['description']['type'].lower()
            except:
                raise UserWarning, "No type found for node '%s'."%key
            
            # create device instances    
            d = None
            if (re.search('signalgenerator', typetxt)):
                d = device.Signalgenerator()
            elif (re.search('powermeter', typetxt)):
                d = device.Powermeter ()
            elif (re.search('switch', typetxt)):
                d = device.Switch()
            elif (re.search('probe', typetxt)):
                d = device.Fieldprobe ()
            elif (re.search('cable', typetxt)):
                d = device.Cable ()
            elif (re.search('motorcontroller', typetxt)):
                d = device.MotorController ()
            elif (re.search('tuner', typetxt)):
                d = device.Tuner ()
            elif (re.search('antenna', typetxt)):
                d = device.Antenna ()
            elif (re.search('nport', typetxt)):
                d = device.NPort ()
            elif (re.search('amplifier', typetxt)):
                d = device.Amplifier ()
            elif (re.search('step2port', typetxt)):
                d = device.SwitchedTwoPort ()
            elif (re.search('spectrumanalyzer', typetxt)):
                d = device.Spectrumanalyzer ()
            elif (re.search('vectornetworkanalyser', typetxt)):
                d = device.NetworkAnalyser()
            ddict[key]=attribs['inst'] = d # save instances in nodes dict and in return value
            #self.CallerGlobals['d']=d
            #exec str(key)+'=d' in self.CallerGlobals # valiable in caller context
            #exec 'self.'+str(key)+'=d'   # as member variable
            self.__dict__.update(ddict)
        return ddict

    def NBTrigger (self, list):
        """
        Trigers all devices in list if possible 
        (node exists, has dev instance, is active, and has Trigger method)
        Returns dict: keys->list items, vals->None or return val from Trigger method
        """
        result={}
        for n in list:
            stat = None
            try:
                node = self.nodes[n]
                dev = node['inst']
                active = node['isActive']
            except KeyError:
                pass
            else:
                if active and dev and hasattr(dev,'Trigger'):
                    stat = dev.Trigger()
            result[n]=stat
        return result        

    def __Read (self, list, result=None):
        """
        Read the measurement results from devices in list
        Mode is blocking if result is None and NonBlocking else
        A dict is returned with keys from list and values from the device reading or None
        Non blocking is finished when len(result) = len(list)
        """
        if result is None:  #blocking
            cmds = ('getData', 'ReadData')
            result = {}
            NB=False
        else: # none blocking
            cmds = ('getDataNB', 'ReadDataNB')
            NB=True

        for n in list:
            if NB and result.has_key(n):
                continue
            try:
                node = self.nodes[n]
                dev = node['inst']
                active = node['isActive']
            except KeyError:
                result[n] = None
            else:
                c=-1
                for cmd in cmds:
                    try:
                        c,val=getattr(dev, cmd)(0)
                        #print "DEBUG:", dev, cmd, val
                    except AttributeError:
                        continue   # try other command(s)
                    else:
                        break
                if c==0:    
                    result[n]=val                                            
        return result        


    def NBRead (self, list, result):
        """
        Non Blocking read
        see __Read
        """
        return self.__Read (list, result) 

    def Read (self, list):
        """
        Blocking read
        see __Read
        """
        return self.__Read (list) 

    def CmdDevices (self, IgnoreInactive, cmd, *args):
        """
        Tries to send 'cmd(*arg)' to all devices in graph
        if IgnoreInactice is True, only active devices are used
         
        """
        cmd = str(cmd)
        serr=0
        for n,attribs in self.nodes.items():
            if attribs['inst'] is None: # not a real device
                continue
            err = 0
            stat = 0
            if (not IgnoreInactive) or (attribs.has_key('isActive') and attribs['isActive']):
                dev = attribs['inst']
                try:
                    ans = getattr(dev, cmd)(*args)
                    if isinstance(ans, tuple):
                        stat=ans[0]
                    else:
                        stat=ans
                    if (stat < 0):
                        err = attribs['inst'].GetLastError()
                except AttributeError:
                    pass
##                if (hasattr(dev,cmd)):
##                    cmdline = "stat = attribs['inst']." + cmd + "("
##                    for arg in args:
##                        cmdline = cmdline + repr(arg) + ","
##                    if cmdline[-1] == ',':
##                        cmdline = cmdline[:-1]
##                    cmdline = cmdline + ")"
##                    exec cmdline    
##                    if (stat < 0):
##                        err = self.nodes[str(n)]['inst'].GetLastError()
            self.nodes[str(n)]['ret'] = stat
            self.nodes[str(n)]['err'] = err
            serr += stat
        return serr
    
    def Init_Devices (self, IgnoreInactive=False):
        """
        Initialize all device
        raises UserWarning if a device fails to initialize
        If IgnoreInactive = False (default), all devices are initialized, 
        else only active devices are initialized
        """
        serr=0
        for n,attribs in self.nodes.items():
            print "Init %s ..."%str(n)
            if attribs['inst'] is None:
                continue
            err = 0
            stat = 0
            ini = str(attribs['ini'])
            if attribs.has_key('ch'):
                ch = int(str(attribs['ch']))
            else:
                ch = 1
            if (not IgnoreInactive) or (attribs.has_key('isActive') and attribs['isActive']):
                dev=attribs['inst']
                if (hasattr(dev,'Init')):
                    #print n
                    stat = dev.Init(ini, ch)
                    if (stat < 0):
                        #print ini, ch
                        err = dev.GetLastError()
            attribs['ret'] = stat
            attribs['err'] = err
            if stat < 0:
                raise UserWarning, 'Error while init of %s, err: %s'%(str(n), err)
            serr += stat
        return serr

    def Quit_Devices (self, IgnoreInactive=False):
        """
        Quit all devices using CmdDevices
        Input: IgnoreInactive=False
        Return: return val of CmdDevices
        """
        return self.CmdDevices (IgnoreInactive, "Quit")

    def SetFreq_Devices (self, freq, IgnoreInactive=True):
        minfreq = 1e100
        maxfreq = -1e100
        for n,attribs in self.nodes.items():
            if attribs['inst'] is None:
                continue
            err = 0
            if (not IgnoreInactive) or (attribs.has_key('isActive') and attribs['isActive']):
                dev=attribs['inst']
                if (hasattr(dev,'SetFreq')):
                    err, f = dev.SetFreq(freq)
                    minfreq = min(minfreq,f)
                    maxfreq = max(maxfreq,f)
                    attribs['ret'] = f
                attribs['err'] = err
        return (minfreq, maxfreq)

    def ConfReceivers(self, conf, IgnoreInactive=True):
        """
        Configures all SA/Receivers in Graph
        Input: conf: a dict with keys from 
                     ('rbw', 'vbw', 'att', 'preamp', 'reflevel',
                      'detector', 'tracemode', 'sweeptime', 'sweepcount', 'span')
                      and values for these parameters
                If a key, val pair exists in conf, we try to set this parameter
                If the a key is not in conf, or if the value is missing (None),
                we try to read the val from the instrument
        Return: rdict: a dict of dicts with rdict[node][key] = val mapping
        """
        parlist = ('rbw',
                   'vbw',
                   'att',
                   'preamp',
                   'reflevel',
                   'detector',
                   'tracemode',
                   'sweeptime',
                   'sweepcount',
                   'span')
        set_names = ('SetRBW',
                     'SetVBW',
                     'SetAtt',
                     'SetPreAmp',
                     'SetRefLevel',
                     'SetDetector',
                     'SetTraceMode',
                     'SetSweepTime',
                     'SetSweepCount',
                     'SetSpan')
        get_names = ('GetRBW',
                     'GetVBW',
                     'GetAtt',
                     'GetPreAmp',
                     'GetRefLevel',
                     'GetDetector',
                     'GetTraceMode',
                     'GetSweepTime',
                     'GetSweepCount',
                     'GetSpan')
        rdict={}
        for n,attribs in self.nodes.items():
            if attribs['inst'] is None:
                continue  # not a device
            err = 0
            if (not IgnoreInactive) or (attribs.has_key('isActive') and attribs['isActive']):
                dev=attribs['inst']
                if not hasattr(dev, set_names[0]):
                    continue   # not a spectrumanalyzer
                # ok, a spec analyzer
                rdict[str(n)]={}
                for index,par in enumerate(parlist):
                    if conf.has_key(par):
                        val = conf[par]
                    else:
                        val = None
                    if (hasattr(dev,set_names[index]) and val):
                        try:
                            err, val = getattr(dev,set_names[index])(val)
                        except TypeError: 
                            err, val = getattr(dev,set_names[index])(*val)
                        rdict[str(n)][par] = val
                    elif hasattr(dev,get_names[index]):
                        err, val = getattr(dev,get_names[index])()
                        rdict[str(n)][par] = val
        return rdict

    def Zero_Devices (self, IgnoreInactive=True):
        """
        Zero all devices using CmdDevices
        Input: IgnoreInactive=True
        Return: return val of CmdDevices
        """
        return self.CmdDevices (IgnoreInactive, "Zero", 1)

    def RFOn_Devices (self, IgnoreInactive=True):
        """
        RFOn all devices using CmdDevices
        Input: IgnoreInactive=True
        Return: return val of CmdDevices
        """
        return self.CmdDevices (IgnoreInactive, "RFOn")
        
    def RFOff_Devices (self, IgnoreInactive=False):
        """
        RFOff all devices using CmdDevices
        Input: IgnoreInactive=False
        Return: return val of CmdDevices
        """
        return self.CmdDevices (IgnoreInactive, "RFOff")

    def Trigger_Devices (self, IgnoreInactive=True):
        """
        Trigger all devices using CmdDevices
        Input: IgnoreInactive=True
        Return: return val of CmdDevices
        """
        return self.CmdDevices (IgnoreInactive, "Trigger")

    def getBatteryLow_Devices (self, IgnoreInactive=True):
        """
        Get a list of all devices in the graph with a low battery state
        Input: IgnoreInactive=True
        Return: list of nodes with low battery state
        """
        lowBatList = []
        #print self.nodes.items()
        for n,attribs in self.nodes.items():
            if attribs['inst'] is None:
                continue
            err = 0
            if (not IgnoreInactive) or (attribs.has_key('isActive') and attribs['isActive']):
                dev=self.nodes[str(n)]['inst']
                if (hasattr(dev,'getBatteryState')):
                    #print "check bat state for node ", n
                    stat, bat = dev.getBatteryState()
                    if (stat < 0):
                        err = dev.GetLastError()
                    elif bat < 0: # Low
                        lowBatList.append(n)
                    attribs['ret'] = bat
                attribs['err'] = err
        return lowBatList

    def GetAntennaEfficiency(self, node):
        """
        Get the antenna efficiency of an antenna connected to node
        Input: node, the node to which the antenna is connected. Typically this is a 
               'virtual' node in the graph, e.g. 'ant' to which the real antennas are connected.  
        Return: antenna efficiency of the first active , real antenna connected to 'node'
                None is returned if no antenna is found
        """
        eta = None
        cmds = ('getData', 'GetData')
        # look for an antenna connected to 'node' ...
        for n,attribs in self.nodes.items():
            if attribs['inst'] is None:
                continue  # not a real device
            if not attribs['inidic']['description']['type'] in ['antenna', 'ANTENNA']:
                continue  # n is not an antenna
            if (attribs.has_key('isActive') and attribs['isActive']):
                # a real, active antenna
                if self.find_path(n, node) or self.find_path(node, n):
                    # ok, there is a coonection to our node
                    try:
                        stat = -1
                        inst = attribs['inst']
                        for cmd in cmds:
                            if hasattr(inst, cmd):
                                stat, result = getattr(inst, cmd)('EFF')
                                break
                        if stat == 0:
                            eta = result
                            break
                    except AttributeError:
                        # function not callable
                        pass
        return eta
                    
    def AmplifierProtect (self, start, end, startlevel, sg_unit, typ='save'):
        isSafe = True
        msg = ''
        if not hasattr(startlevel, '__unit__'):
            startlevel = quantities.Quantity(sg_unit, startlevel)
        allpaths = self.find_all_paths(start, end)
        for path in allpaths:
            edges = []
            for i in range(len(path)-1):
                left  = path[i]
                right = path[i+1]
                edges.append((left,right,self.graph[left][right]))
            for left,right,edge in edges:
                try:
                    attribs = self.nodes[edge['dev']]
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
                                stat = 0
                                try:
                                    stat, result = getattr(dev, cmd)(w)
                                except AttributeError:
                                    # function not callable
                                    #print "attrErr"
                                    continue 
                                if stat != 0:
                                    #print stat
                                    continue
                                # ok we have a value that can be checked
                                corr = self.get_path_correction(start, left, POWERRATIO)
                                #for _k,_v in corr.items():
                                    #print "corr[%s]:"%_k, _v
                                #print "Startlevel:", startlevel
                                level = corr['total'] * startlevel
                                #print "Level:", level
                                #print "What = '%s', Level = %s, Max = %s\n"%(w, str(level), str(result))
                                #if typ=='lasy':
                                condition=( abs(level) > abs(result) )
                                #elif typ=='save':
                                #    condition=level.get_u() > result.get_l() #be safe: errorbars overlap
                                #else:
                                #    condition=level.get_u() > result.get_l() #be safe: errorbars overlap
                                if condition: 
                                    isSafe=False
                                    msg += "Amplifier Pretection failed for node '%s'. What = '%s', Level = %s, Max = %s, Startlevel = %s, Corr = %s\n"%(edge['dev'], w, level, result, startlevel, corr['total'])
                            break        
        return isSafe,msg


    def CalcLevelFrom (self, sg, limiter, what):
        if sg not in self.nodes:
            raise UserWarning, 'Node not in nodes: %s' %sg
        if limiter not in self.nodes:
            raise UserWarning, 'Node not in nodes: %s' %limiter
        if not len(self.find_all_paths (sg, limiter)):
            raise UserWarning, 'Nodes not connected'
        il = self.get_path_correction (sg, limiter, POWERRATIO)
        return 0

    def __parse_ini (self, ini):
        def readConfig(filename):
            """ Read config data
        
            *** Here add for doc the format of the data ***	
            
            Return configVals
            """
            configVals = ConfigParser.ConfigParser()
            configVals.read(os.path.normpath(filename))
            return (configVals)

        def makeDict(configData):
            """
            create a dict from a Config file
            """
            d = {}
            for section in configData.sections():
                s = section.lower()
                d[s] = {}
                for option in configData.options(section):
                    o = option.lower()
                    d[s][o] = configData.get(section,option)
            return(d)

        umdpath = getUMDPath()
        _ini = GetFileFromPath (ini, umdpath)
        if _ini is None:
            raise "Ini file '%s' not found. Path is '%s'"%(ini,umdpath)
        v = readConfig(_ini)
        return makeDict(v)
