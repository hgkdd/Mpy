#import os
#import re
import inspect
import pydot
import ConfigParser

import mpy.device.device as device
from scuq import *
from mpy.tools.aunits import *
from mpy.tools.Configuration import fstrcmp

class Graph(object):
    def __init__(self, fname_or_data=None):
        methods=('graph_from_dot_file','graph_from_dot_data','graph_from_edges',
                 'graph_from_adjacency_matrix','graph_from_incidence_matrix')             
        dotgraph=None
        for m in methods:
            meth=getattr(pydot, m)
            try:
                dotgraph=meth(fname_or_data)
            except (IOError, IndexError):
                continue
            else:
                break
        if dotgraph:
            self.graph=dotgraph
            self.edges=self.graph.get_edges()
        else:
            raise "Graph could no be created"
        
    def __str__(self):
        return self.graph.to_string()

    def find_path(self, start, end, path=[]):
        """
        Returns a path from start to end.
        Ignores edges with attribute active==False.
        """
        try:
            return self.find_all_paths(start, end, path)[0]
        except IndexError:
            return None

    def find_all_paths(self, start, end, path=[], edge=None):
        """
        Find all paths in graph from start to end (without circles)
        Ignores edges with attribute active==False.
        """
        #print 'enter:', start, end, path 
        #path = path + [start]
        if edge:
            path = path + [edge]
            #print "added edge to path:", edge.get_source(), edge.get_destination(), path
        if start == end:    # end node reached
            #print "start==end: returing", [path]
            return [path]   # this is the end of the recursion
        paths = []
        # list of all edges with source==start
        start_edges=[e for e in self.edges if e.get_source() == start] 
        for edge in start_edges:
            next_node=edge.get_destination()
            gnode=self.graph.get_node(next_node)
            is_active = edge.get_attributes().setdefault('active', True) and gnode.get_attributes().setdefault('active', True) 
            if is_active and edge not in path:
                newpaths = self.find_all_paths(next_node, end, path, edge)
                #print "newpaths returned:", newpaths
                for newpath in newpaths:
                    paths.append(newpath)
        #print 'exit:', paths
        return paths

    def find_shortest_path(self, start, end, path=[]):
        """
        returns the shortest path from start to end
        Ignores edges with attribute active==False.
        """
        allpaths=self.find_all_paths(start, end, path)
        if allpaths:
            return sorted(allpaths)[0]
        else:
            return None

class MGraph(Graph):
    def __init__(self, fname_or_data=None):
        super(MGraph, self).__init__(fname_or_data)
        self.gnodes=self.graph.get_nodes()
        self.gedges=self.graph.get_edges()
        self.nodes=dict([[n.get_name(),{}] for n in self.gnodes])
        nametonode=dict([[n.get_name(),n] for n in self.gnodes])
        for n,dct in self.nodes.items():
            dct['gnode']=nametonode[n]
        self.activenodes=self.nodes.keys()
    
    def get_path_correction (self, start, end, unit=None):
        """
        Returns a dict with the corrections for all edges
        key 'total' gives the total correction.
        All corrections are SCUQ objects.
        """
        assert unit in (AMPLITUDERATIO, POWERRATIO)
        result = {}
        all_paths = self.find_all_paths(start, end) # returs a list of (list of edges)
        #print all_paths
        Total = quantities.Quantity (unit, 0.0) # init total path correction with 0
        for p in all_paths: # p is a list of edges
            # totals in that path
            TotalPath = quantities.Quantity (unit, 1.0)  # init total corection fpr this path
            for n in p:  # for all edges in this path
                #print n
                n_attr=n.get_attributes() # dict with edge atributs
                if 'dev' in n_attr:
                    # the edge device
                    dev = str(n_attr['dev'])
                    # edge device instance
                    inst = self.nodes[dev]['inst']
                    what = str(n_attr['what'])
                    try:
                        stat = -1
                        for cmd in ['getData', 'GetData']:
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
                    TotalPath *= r            

            # for different paths between two points, s parameters have
            # to be summed.
            #print TotalPath
            #for k,v in result.items():
            #    print k,v
            Total += TotalPath
        result['total'] = Total        
        return result

    def EvaluateConditions (self, doAction=True):
        """
        Set key isActice in nodes argument depending on the condition given in the graph
        """
        __frame = inspect.currentframe()
        __outerframes = inspect.getouterframes(__frame)
        __caller = __outerframes[1][0]
        for name,dct in self.nodes.items():
            node=dct['gnode']
            n_attr=node.get_attributes() # dict with node or edge atributs
            if 'condition' in n_attr:
                stmt = "(" + str(n_attr['condition']) + ")"
                #print " Cond:", stmt, " = ", 
                cond = eval (stmt, __caller.f_globals, __caller.f_locals)
                #print cond
                if cond:
                    dct['active']=True
                    if doAction and 'action' in n_attr:
                        act = n_attr['action']
                        #print str(act)
                        #print self.CallerLocals['f']
                        #print act
                        exec str(act) # in self.CallerGlobals, self.CallerLocals
                else:
                    dct['active']=False
            else:
                dct['active']=True
        self.activenodes=[name for name,dct in self.nodes.items() if dct['active']]
        del __caller
        del __outerframes
        del __frame

    def CreateDevices (self):
        """
        Should be called once after creating the instance.

        - Sets attribute `active = True` for all nodes and edges
        - Reads the ini-file (if ini atrib is present)
        - Creates the device instances of all nodes and save the variable in the nodes dict
          (`nodes[key]['inst']`)

        Returns a dict with keys from the graphs nodes names and val are the device instances
        Can be used to create local references like so::

            for k,v in ddict.items():
                globals()['k']=v

        """
        dev_map={'signalgenerator': 'Signalgenerator',
                 'powermeter': 'Powermeter',
                 'switch': 'Switch',
                 'probe': 'Fieldprobe',
                 'cable': 'Cable',
                 'motorcontroller': 'MotorController',
                 'tuner': 'Tuner',
                 'antenna': 'Antenna',
                 'nport': 'NPort',
                 'amplifier': 'Amplifier',
                 'step2port': 'SwitchedTwoPort',
                 'spectrumanalyzer': 'Spectrumanalyzer',
                 'vectornetworkanalyser': 'NetworkAnalyser'}
        devs=dev_map.keys()
        ddict={}
        for name,dct in self.nodes.items():
            obj=dct['gnode']
            attribs=obj.get_attributes()
            for n,v in attribs.items():
                attribs[n]=v.strip("'")   # strip '
                attribs[n]=v.strip('"')   # strip "
                
            dct['active']=True
            try:
                ini=dct['ini']=attribs['ini']   # the ini file name
            except KeyError:    
                ini=dct['ini']=dct['inst']=None # no ini file, no device
                continue            
            #print "ini:", self.nodes
            dct['inidic'] = self.__parse_ini(ini)  # parse the ini file and save it as dict in the attributes
            try:
                typetxt = dct['inidic']['description']['type']
            except:
                raise UserWarning, "No type found for node '%s'."%obj.get_name()
            
            # create device instances    
            d = None
            try:
                # fuzzy type matching...
                best_type_guess=fstrcmp(typetxt, devs, n=1, cutoff=0, ignorecase=True)[0]
            except IndexError:
                raise IndexError, 'Instrument type %s from file %s not in list of valid instrument types: %r'%(typetxt,ini,devs)
            d=getattr(device, dev_map[best_type_guess])()
            ddict[name]=dct['inst']=d # save instances in nodes dict and in return value
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
        devices=[l for l in list if l in self.activenodes]  # intersept of list and activenodes
        result={}
        for name in devices:
            attribs=self.nodes[name]
            if not attribs['active']:
                continue
            try:
                stat=attribs['inst'].Trigger()
                result[name]=stat
            except (KeyError, AttributeError):
                continue
        return result   

    def __Read (self, list, result=None):
        """
        Read the measurement results from devices in list
        Mode is blocking if result is None and NonBlocking else
        A dict is returned with keys from list and values from the device reading or None
        Non blocking is finished when len(result) = len(list)
        """
        if result is None:  #blocking
            cmds = ('GetData', 'getData', 'ReadData')
            result = {}
            NB=False
        else: # none blocking
            cmds = ('GetData', 'getDataNB', 'ReadDataNB')
            NB=True

        devices=[l for l in list if l in self.activenodes]  # intersept of list and activenodes
        for n in devices:
            if NB and n in result:
                continue
            try:
                nattr=self.nodes[n]
                dev = nattr['inst']
            except KeyError:
                result[n] = None
            else:
                c=-1
                for cmd in cmds:
                    try:
                        c,val=getattr(dev, cmd)()
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
        Tries to send `cmd(*arg)` to all devices in graph
        if `IgnoreInactice` is `True`, only active devices are used
         
        """
        devices=[name for name in self.nodes.keys() if IgnoreInactive or name in self.activenodes]  # intersept of list and activenodes
        cmd = str(cmd)
        serr=0
        for n in devices:
            attribs=self.nodes[n]
            if attribs['inst'] is None: # not a real device
                continue
            err = 0
            stat = 0
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
        devices=[name for name in self.nodes if IgnoreInactive or name in self.activenodes]  # intersept        
        serr=0
        for n in devices:
            print "Init %s ..."%str(n)
            attribs=self.nodes[n]
            if attribs['inst'] is None:
                continue
            err = 0
            stat = 0
            ini = attribs['ini']
            gattr=attribs['gnode'].get_attributes()
            ch=1
            for c in ('ch', 'channel'):
                try:
                    ch=int(gattr[c])
                except KeyError:
                    continue
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
        devices=[name for name in self.nodes if IgnoreInactive or name in self.activenodes]  # intersept        
        for n in devices:
            attribs=self.nodes[n]
            if attribs['inst'] is None:
                continue
            err = 0
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
        Input: `conf`: a dict with keys from 
                     `('rbw', 'vbw', 'att', 'preamp', 'reflevel', 'detector', 'tracemode', 'sweeptime', 'sweepcount', 'span')`
                      and values for these parameters

                If a key, val pair exists in conf, we try to set this parameter
                If the a key is not in `conf`, or if the value is missing (`None`),

                we try to read the val from the instrument

        Return: `rdict`: a dict of dicts with `rdict[node][key] = val` mapping
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
        devices=[name for name in self.nodes if IgnoreInactive or name in self.activenodes]  # intersept        
        for n in devices:
            attribs=self.nodes[n]
            if attribs['inst'] is None:
                continue  # not a device
            err = 0
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
        devices=[name for name in self.nodes if IgnoreInactive or name in self.activenodes]  # intersept        
        for n in devices:
            attribs=self.nodes[n]
            if attribs['inst'] is None:
                continue
            err = 0
            dev=attribs['inst']
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
        Get the antenna efficiency of an antenna connected to node.

        Input: 
           node, the node to which the antenna is connected. Typically this is a 
           'virtual' node in the graph, e.g. 'ant' to which the real antennas are connected.  
        
        Return: 
           antenna efficiency of the first active , real antenna connected to 'node'
           None is returned if no antenna is found
        """
        eta = None
        cmds = ('getData', 'GetData')
        # look for an antenna connected to 'node' ...
        devices=[n for n in self.nodes if n in self.activenodes]
        for n in devices:
            attribs=self.nodes[n]
            if attribs['inst'] is None:
                continue  # not a real device
            if not attribs['inidic']['description']['type'] in ('antenna', 'ANTENNA'):
                continue  # n is not an antenna
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
        for path in allpaths: #path is a list of edges
            edges = []
            for p in path:
                left  = p.get_source()
                right = p.get_destination()
                edges.append((left,right,p))
            for left,right,edge in edges:
                try:
                    edge_dev=edge.get_attributes()['dev']
                    attribs = self.nodes[edge_dev]
                except KeyError:
                    continue
                if attribs['inst'] is None:
                    continue
                err = 0
                if attribs['active']:
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
                                    msg += "Amplifier Pretection failed for node '%s'. What = '%s', Level = %s, Max = %s, Startlevel = %s, Corr = %s\n"%(edge_dev, w, level, result, startlevel, corr['total'])
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
            configVals = ConfigParser.SafeConfigParser()
            if hasattr(filename, 'readline'):  # file like object
                configVals.readfp(filename)
            else:
                configVals.read(filename)  # filename
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

        #umdpath = getUMDPath()
        #_ini = GetFileFromPath (ini, umdpath)
        #if _ini is None:
        #    raise "Ini file '%s' not found. Path is '%s'"%(ini,umdpath)
        v=readConfig(ini)
        return makeDict(v)
