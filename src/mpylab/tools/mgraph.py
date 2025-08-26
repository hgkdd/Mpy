import os
import io
# import re
import importlib.machinery
import inspect
import pydot
import configparser
from numpy import bool_, sqrt
from scipy.interpolate import interp1d

import mpylab.device.device as device
from scuq import *
from mpylab.tools.aunits import *
from mpylab.tools.Configuration import fstrcmp
from mpylab.tools.util import extrap1d, locate, format_block


def _stripstr(s):
    r = s
    r = r.strip('"')
    r = r.strip("'")
    return r


class DictObj(dict):
    def __getattr__(self, name):
        try:
            return self.__getitem__(name)
        except KeyError:
            return super(DictObj, self).__getattr__(name)


class GName(object):
    def __init__(self, mginst):
        self.mg = mginst

    def __getattribute__(self, name):
        try:
            attr = object.__getattribute__(self, name)
        except AttributeError:
            attr = self.mg.get_gname(name)
            if attr is None:
                raise AttributeError
        return attr


class Graph(object):
    """Graph class based on :mod:`pydot`.

       The graph is created using the methods (called in this order)

         - :meth:`pydot.graph_from_dot_file`
         - :meth:`pydot.graph_from_dot_data`
         - :meth:`pydot.graph_from_edges`
         - :meth:`pydot.graph_from_adjacency_matrix`
         - :meth:`pydot.graph_from_incidence_matrix`

       with the argument of the :meth:`__init__` method.
    """

    def __init__(self, fname_or_data=None, SearchPaths=None):
        if SearchPaths is None:
            SearchPaths = [os.getcwd()]
        self.SearchPaths = SearchPaths

        methods = ('graph_from_dot_file',
                   'graph_from_dot_data',
                   'graph_from_edges',
                   'graph_from_adjacency_matrix',
                   'graph_from_incidence_matrix')
        dotgraph = None
        # self.dotcontents=None
        for m in methods:
            meth = getattr(pydot, m)
            try:
                if m == 'graph_from_dot_file':
                    # print self.SearchPaths, fname_or_data
                    try:
                        # print "Hey", self.instance_from_pickle
                        fname_or_data = next(locate(fname_or_data, paths=self.SearchPaths))  # first hit
                        """
                        if file was found update dotcontets from this file.
                        if not we maybe come from a pickle file and haven't found the graph
                        in this case we restore the graph from self.dotcontets -> except clause
                        """
                        self.dotcontents = (open(fname_or_data, 'r')).read()  #
                        dotgraph = meth(fname_or_data)
                    except StopIteration:  # not found
                        # print "Hey", self.instance_from_pickle
                        if hasattr(self, 'instance_from_pickle') and self.instance_from_pickle:
                            self.graph = dotgraph = pydot.graph_from_dot_data(self.dotcontents)  # TODO
                            return
                        else:
                            raise  # reraise
                else:
                    dotgraph = meth(fname_or_data)
            except (IOError, IndexError):
                continue
            else:
                break
        if dotgraph:
            self.graph = dotgraph[0]
            self.edges = self.graph.get_edges()
        else:
            raise RuntimeError("Graph could no be created")

    def __str__(self):
        return self.graph.to_string()

    def find_path(self, start, end, path=None):
        """Returns a path from *start* to *end*.
           Ignores edges with attribute `active==False`.
        """
        if path is None:
            path = []
        try:
            return self.find_all_paths(start, end, path)[0]
        except IndexError:
            return None

    def _active(self, edge_or_gnode):
        try:
            att = edge_or_gnode.get_attributes()
            act = att['active']
            return act
        except (AttributeError, KeyError):
            return True

    def find_all_paths(self, start, end, path=None, edge=None):
        """Find all paths in graph from *start* to *end* (without circles).
           Ignores edges with attribute `active==False`.
        """
        # print 'enter:', start, end, path
        # path = path + [start]
        if path is None:
            path = []
        if edge:
            path = path + [edge]
            # print "added edge to path:", edge.get_source(), edge.get_destination(), path
        if start == end:  # end node reached
            # print "start==end: returing", [path]
            return [path]  # this is the end of the recursion
        paths = []
        # list of all edges with source==start
        start_edges = [e for e in self.edges if e.get_source() == start]
        for edge in start_edges:
            next_node = edge.get_destination()
            gnode = self.graph.get_node(next_node)
            eact = self._active(edge)
            gact = self._active(gnode)
            is_active = eact and gact
            if is_active and edge not in path:
                newpaths = self.find_all_paths(next_node, end, path, edge)
                # print "newpaths returned:", newpaths
                for newpath in newpaths:
                    paths.append(newpath)
        # print 'exit:', paths
        return paths

    def get_common_parent(self, n1, n2):
        # trivial cases
        if self.find_path(n1, n2):
            return n1
        if self.find_path(n2, n1):
            return n2
        # find for 'real' parent
        edges = [e for e in self.edges if e.get_destination() == n1]
        for edge in edges:
            parent_node = edge.get_source()
            gnode = self.graph.get_node(parent_node)
            eact = self._active(edge)
            gact = self._active(gnode)
            is_active = eact and gact
            if is_active:
                return self.get_common_parent(parent_node, n2)
        return None

    def find_shortest_path(self, start, end, path=None):
        """Returns the shortest path from *start* to *end*.
           Ignores edges with attribute `active==False`.
        """
        if path is None:
            path = []
        allpaths = self.find_all_paths(start, end, path)
        if allpaths:
            return sorted(allpaths)[0]
        else:
            return None


class MGraph(Graph):
    """Measurement grapg class based of :class:`Graph`. See there for the argument of the :meth:`__init__` method.
    """

    def __init__(self, fname_or_data=None, themap=None, SearchPaths=None):
        self.fname_or_data = fname_or_data
        self.map = themap
        if SearchPaths is None:
            SearchPaths = [os.getcwd()]
        super(MGraph, self).__init__(fname_or_data, SearchPaths=SearchPaths)
        self.name = GName(self)
        try:
            self.graph = self.graph[0]    # new version of pydot
        except TypeError:
            self.graph = self.graph       # old version of pydot
        self.gnodes = self.graph.get_nodes()
        self.gedges = self.graph.get_edges()
        self.nodes = dict([[n.get_name(), {}] for n in self.gnodes])
        nametonode = dict([[n.get_name(), n] for n in self.gnodes])
        for n, dct in list(self.nodes.items()):
            dct['gnode'] = nametonode[n]
        self.activenodes = list(self.nodes.keys())
        if themap is None:
            themap = {}
        self.map = themap
        # make map bijective
        self.bimap = self.map
        for k, v in list(themap.items()):
            try:
                self.bimap[v] = k
            except TypeError:  # this happens if v is a list
                for _v in v:
                    self.bimap[_v] = k
        self.instrumentation = None

    def __setstate__(self, dct):
        """used instead of __init__ when instance is created from pickle file"""
        self.instance_from_pickle = True
        if 'dotcontents' not in dct:
            dct['dotcontents'] = "digraph {sg->ant}"
        self.dotcontents = dct['dotcontents']
        self.__init__(fname_or_data=dct['fname_or_data'], themap=dct['map'], SearchPaths=dct['SearchPaths'])

    def __getstate__(self):
        """prepare a dict for pickling"""
        odict = {'fname_or_data': self.fname_or_data,
                 'map': self.map,
                 'SearchPaths': self.SearchPaths,
                 'dotcontents': self.dotcontents}
        return odict

    # def __getattribute__(self, name):
    # try:
    # attr=Graph.__getattribute__(self, name)
    # except AttributeError:
    # attr=self.get_gname(name)
    # if attr is None:
    # raise AttributeError
    # return attr

    def get_gname(self, name):
        if name in self.map:
            return self.map[name]
        elif name in self.bimap:
            return name
        else:
            return None

    @staticmethod
    def _pr2ar(pr):
        assert pr._unit == POWERRATIO
        pr._unit = units.ONE  # yes, we know what we are doing
        ar = sqrt(pr)
        ar._unit = AMPLITUDERATIO
        return ar

    @staticmethod
    def _ar2pr(ar):
        assert ar._unit == AMPLITUDERATIO
        return ar * ar

    def get_path_correction(self, start, end, unit=None):
        if unit is None:
            unit = AMPLITUDERATIO
        assert unit in (AMPLITUDERATIO, POWERRATIO)
        if start == end:
            corr = quantities.Quantity(unit, 1)
            return corr

        parent = self.get_common_parent(start, end)
        if parent == start:
            corr = self.get_path_corrections(start, end, unit=unit)['total']
        elif parent == end:
            corr = 1.0 / self.get_path_corrections(end, start, unit=unit)['total']
        else:
            corr = self.get_path_corrections(parent, end, unit=unit)['total'] / \
                   self.get_path_corrections(parent, start, unit=unit)['total']
        return corr

    def get_path_corrections(self, start, end, unit=None):
        """Returns a dict with the corrections for all edges from *start* to *end*. *unit* can be 
           :data:`mpylab.tools.aunits.AMPLITUDERATIO` or :data:`mpylab.tools.aunits.POWERRATIO`. If *unit* is `None`,
           :data:`mpylab.tools.aunits.AMPLITUDERATIO` is used.

           The key 'total' gives the total correction.
        
           All corrections are :class:`scuq.quantities.Quantity` objects.
        """
        if unit is None:
            unit = AMPLITUDERATIO
        assert unit in (AMPLITUDERATIO, POWERRATIO)
        result = {}

        all_paths = self.find_all_paths(start, end)  # returs a list of (list of edges)
        # print all_paths
        ctx = ucomponents.Context()
        Total = quantities.Quantity(unit, 0.0)  # init total path correction with 0
        for p in all_paths:  # p is a list of edges
            # totals in that path
            TotalPath = quantities.Quantity(unit, 1.0)  # init total corection fpr this path
            for n in p:  # for all edges in this path
                # print n
                n_attr = n.get_attributes()  # dict with edge atributs
                if 'dev' in n_attr:
                    # the edge device
                    dev = str(n_attr['dev'])
                    # edge device instance
                    inst = self.nodes[dev]['inst']
                    try:
                        what = _stripstr(str(n_attr['what']))
                    except KeyError:
                        continue
                    try:
                        stat = -1
                        for cmd in ['getData', 'GetData']:
                            # print cmd
                            if hasattr(inst, cmd):
                                # print "Vor getattr", getattr(inst,cmd)
                                stat, result[dev] = getattr(inst, cmd)(what)
                                # print "Nach getattr", stat
                                break
                        if stat < 0:
                            raise UserWarning('Failed to getData: %s, %s' % (dev, what))
                    except AttributeError:
                        # function not callable
                        # 
                        raise UserWarning('Failed to getData %s, %s' % (dev, what))
                        # store the values unconverted
                    # print dev, result[dev]
                    r = result[dev]  # .get_value(unit)

                    if unit == AMPLITUDERATIO and r._unit == POWERRATIO:
                        r = self._pr2ar(r)
                    elif unit == POWERRATIO and r._unit == AMPLITUDERATIO:
                        r = self._ar2pr(r)
                    elif (unit == POWERRATIO and r._unit == POWERRATIO) or \
                            (unit == AMPLITUDERATIO and r._unit == AMPLITUDERATIO):
                        pass
                    else:
                        raise RuntimeError("Unit Error")
                    TotalPath *= r

                    # for different paths between two points, s parameters have
            # to be summed.
            # print TotalPath
            # for k,v in result.items():
            #    print k,v
            TotalPath = TotalPath.eval()
            TotalPath = TotalPath.reduce_to(unit)
            Total += TotalPath
        # print start, end, Total
        try:
            result['total'] = Total.eval()
        except AttributeError:
            result['total'] = Total
        return result

    def EvaluateConditions(self, doAction=True):
        """Set key *isActice* in nodes argument depending on the condition given in the graph.

           If *doAction* is `True` an action *act* defined in the edge attributed is executed using `exec str(act)` if the 
           condition evaluates to `True`.

           The condition may refer to variables in the callers namespace, e.g. 'f'.
        """

        __frame = inspect.currentframe()
        __outerframes = inspect.getouterframes(__frame)
        __caller = __outerframes[1][0]
        # loop all nodes
        for name, act_dct in list(self.nodes.items()):
            node = act_dct['gnode']
            cond_dct = node.get_attributes()  # dict with node or edge atributs
            if 'condition' in cond_dct:
                stmt = "(%s)" % _stripstr(str(cond_dct['condition']))
                # print " Cond:", stmt, " = ",
                cond = eval(stmt, __caller.f_globals, __caller.f_locals)
                # print cond
                if (cond is True) or (cond is bool_(True)):
                    act_dct['active'] = True
                    if doAction and 'action' in cond_dct:
                        act = cond_dct['action']
                        # print str(act)
                        # print self.CallerLocals['f']
                        # print act
                        exec(str(act))  # in self.CallerGlobals, self.CallerLocals
                else:
                    act_dct['active'] = False
            else:
                act_dct['active'] = True
        self.activenodes = [name for name, dct in list(self.nodes.items()) if dct['active']]
        # loop all edges
        for edge in self.edges:
            act_dct = cond_dct = edge.get_attributes()
            if 'condition' in cond_dct:
                stmt = "(%s)" % _stripstr(str(cond_dct['condition']))
                # print " Cond:", stmt, " = ",
                cond = eval(stmt, __caller.f_globals, __caller.f_locals)
                # print cond
                if (cond is True) or (cond is bool_(True)):
                    act_dct['active'] = True
                    if doAction and 'action' in cond_dct:
                        act = cond_dct['action']
                        # print str(act)
                        # print self.CallerLocals['f']
                        # print act
                        exec(str(act))  # in self.CallerGlobals, self.CallerLocals
                else:
                    act_dct['active'] = False
            else:
                act_dct['active'] = True

        del __caller
        del __outerframes
        del __frame

    def CreateDevices(self):
        """
        Create instances of the devices found in the graph. Should be called once after creating the graph instance.

        - Sets attribute `active = True` for all nodes and edges
        - Reads the ini-file (if ini atrib is present)
        - Creates the device instances of all nodes and save the variable in the nodes dict
          (`nodes[key]['inst']`)

        Returns a dict with keys from the graphs nodes names and val are the device instances
        Can be used to create local references like so::

            for k,v in ddict.items():
                globals()['k']=v

        """
        dev_map = {'signalgenerator': 'Signalgenerator',
                   'powermeter': 'Powermeter',
                   'switch': 'Switch',
                   'fieldprobe': 'Fieldprobe',
                   'cable': 'Cable',
                   'motorcontroller': 'Motorcontroller',
                   'tuner': 'Tuner',
                   'antenna': 'Antenna',
                   'nport': 'NPort',
                   'amplifier': 'Amplifier',
                   'step2port': 'SwitchedTwoPort',
                   'spectrumanalyzer': 'Spectrumanalyzer',
                   'vectornetworkanalyser': 'NetworkAnalyser',
                   'custom': 'Custom'}
        devs = list(dev_map.keys())
        ddict = DictObj()
        for name, dct in list(self.nodes.items()):
            obj = dct['gnode']
            attribs = obj.get_attributes()
            for n, v in list(attribs.items()):
                attribs[n] = _stripstr(v)  # strip ' and "

            dct['active'] = True
            try:
                ini = dct['ini'] = next(locate(attribs['ini'], paths=self.SearchPaths))  # the ini file name
                # print ini
            except KeyError:
                ini = dct['ini'] = dct['inst'] = None  # no ini file, no device
                continue
                # print "ini:", self.nodes
            dct['inidic'] = self.__parse_ini(ini)  # parse the ini file and save it as dict in the attributes
            try:
                typetxt = dct['inidic']['description']['type']
            except:
                raise UserWarning("No type found for node '%s'." % obj.get_name())

            # create device instances    
            d = None
            try:
                # fuzzy type matching...
                best_type_guess = fstrcmp(typetxt, devs, n=1, cutoff=0, ignorecase=True)[0]
            except IndexError:
                raise IndexError(
                    'Instrument type %s from file %s not in list of valid instrument types: %r' % (typetxt, ini, devs))
            dtype = dev_map[best_type_guess]
            if dtype == 'Custom':
                driver = dct['inidic']['description']['driver']
                cls = dct['inidic']['description']['class']
                drvfile = next(locate(driver, self.SearchPaths))
                # m = imp.load_source('m', drvfile)
                m = importlib.machinery.SourceFileLoader(driver, drvfile).load_module()
                d = getattr(m, cls)()
            else:
                d = getattr(device, dtype)(SearchPaths=self.SearchPaths)
            ddict[name] = dct['inst'] = d  # save instances in nodes dict and in return value
            # self.CallerGlobals['d']=d
            # exec str(key)+'=d' in self.CallerGlobals # valiable in caller context
            # exec 'self.'+str(key)+'=d'   # as member variable
            self.__dict__.update(ddict)
            for k, v in list(ddict.items()):
                if k in self.bimap:
                    try:
                        ddict[self.bimap[k]] = v
                    except TypeError:  # this happens if v is a list
                        for _k in self.bimap[k]:
                            ddict[_k] = v
            self.instrumentation = ddict
        return ddict

    def NBTrigger(self, lst):
        """
        Trigers all devices in list if possible 
        (node exists, has dev instance, is active, and has Trigger method).

        Returns dict: keys->list items, vals->None or return val from Trigger method
        """
        devices = [l for l in lst if l in self.activenodes]  # intersept of list and activenodes
        result = {}
        for name in devices:
            attribs = self.nodes[name]
            if not attribs['active']:
                continue
            try:
                stat = attribs['inst'].Trigger()
                result[name] = stat
            except (KeyError, AttributeError):
                continue
        return result

    def _Read(self, lst, result=None):
        """
        Read the measurement results from devices in list.

        Mode is blocking if result is None and NonBlocking else. Non blocking is finished when `len(result) = len(list)`.

        A dict is returned with keys from list and values from the device reading or `None`.
        """
        if result is None:  # blocking
            cmds = ('GetData', 'getData', 'ReadData')
            result = {}
            NB = False
        else:  # none blocking
            cmds = ('GetData', 'getDataNB', 'ReadDataNB')
            NB = True

        devices = [l for l in lst if l in self.activenodes]  # intersept of list and activenodes
        for n in devices:
            if NB and n in result:
                continue
            try:
                nattr = self.nodes[n]
                dev = nattr['inst']
            except KeyError:
                result[n] = None
            else:
                c = -1
                for cmd in cmds:
                    try:
                        c, val = getattr(dev, cmd)()
                        # print "DEBUG:", dev, cmd, val
                    except AttributeError:
                        continue  # try other command(s)
                    else:
                        break
                if c == 0:
                    result[n] = val
        return result

    def NBRead(self, lst, result):
        """
        Non Blocking read.
        See :meth:`_Read`.
        """
        return self._Read(lst, result)

    def Read(self, lst):
        """
        Blocking read.
        See :meth:`_Read`.
        """
        return self._Read(lst)

    def CmdDevices(self, IgnoreInactive, cmd, *args):
        """
        Tries to send `cmd(*arg)` to all devices in graph.

        If *IgnoreInactice* is `True`, only active devices are used.
         
        Returns the sum of all status codes returned from the called methods, i.e. a return value of zero indicates success.

        Return error codes for all devices are stored in `self.nodes[str(n)]['ret']` and `self.nodes[str(n)]['err']`. 
        """
        devices = [name for name in list(self.nodes.keys()) if
                   IgnoreInactive or name in self.activenodes]  # intersept of list and activenodes
        cmd = str(cmd)
        serr = 0
        for n in devices:
            attribs = self.nodes[n]
            if attribs['inst'] is None:  # not a real device
                continue
            err = 0
            stat = 0
            dev = attribs['inst']
            try:
                ans = getattr(dev, cmd)(*args)
                if isinstance(ans, tuple):
                    stat = ans[0]
                else:
                    stat = ans
                if (stat < 0):
                    err = attribs['inst'].GetLastError()
            except AttributeError:
                pass
            self.nodes[str(n)]['ret'] = stat
            self.nodes[str(n)]['err'] = err
            serr += stat
        return serr

    def Init_Devices(self, IgnoreInactive=False):
        """
        Initialize all device.

        Raises :exc:`UserWarning` if a device fails to initialize.

        If `IgnoreInactive = False` (default), all devices are initialized, 
        else only active devices are initialized.
        """
        devices = [name for name in self.nodes if IgnoreInactive or name in self.activenodes]  # intersept
        serr = 0
        for n in devices:
            print("Init %s ..."%str(n))
            attribs = self.nodes[n]
            if attribs['inst'] is None:
                continue
            err = 0
            stat = 0
            ini = attribs['ini']
            gattr = attribs['gnode'].get_attributes()
            ch = 1
            for c in ('ch', 'channel'):
                try:
                    ch = int(gattr[c])
                except KeyError:
                    continue
            dev = attribs['inst']
            if (hasattr(dev, 'Init')):
                # print n
                stat = dev.Init(ini, ch)
                if (stat < 0):
                    # print ini, ch
                    err = dev.GetLastError()
            attribs['ret'] = stat
            attribs['err'] = err
            if stat < 0:
                raise UserWarning('Error while init of %s, err: %s' % (str(n), err))
            serr += stat
        return serr

    def Quit_Devices(self, IgnoreInactive=False):
        """
        Quit all devices using :meth:`CmdDevices`.

        Input: `IgnoreInactive=False`

        Return: return val of :meth:`CmdDevices`
        """
        return self.CmdDevices(IgnoreInactive, "Quit")

    def SetFreq_Devices(self, freq, IgnoreInactive=True):
        minfreq = 1e100
        maxfreq = -1e100
        devices = [name for name in self.nodes if IgnoreInactive or name in self.activenodes]  # intersept
        for n in devices:
            attribs = self.nodes[n]
            if attribs['inst'] is None:
                continue
            err = 0
            dev = attribs['inst']
            if (hasattr(dev, 'SetFreq')):
                err, f = dev.SetFreq(freq)
                minfreq = min(minfreq, f)
                maxfreq = max(maxfreq, f)
                attribs['ret'] = f
            attribs['err'] = err
        return (minfreq, maxfreq)

    def ConfReceivers(self, conf, IgnoreInactive=True):
        """
        Configures all SA/Receivers in Graph.

        Input: 

           - *conf*: a dict with keys from 
                
                `('rbw', 'vbw', 'att', 'preamp', 'reflevel', 'detector', 'tracemode', 'sweeptime', 'sweepcount', 'span')`
                      
             and values for these parameters.

             If a key, val pair exists in *conf*, we try to set this parameter.
             If the a key is not in *conf*, or if the value is missing (`None`),
             we try to read the val from the instrument.
           - *IgnoreInactive*: flag to ignore devices marked as inactive

        Return:
 
           - `rdict`: a dict of dicts with `rdict[node][key] = val` mapping

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
        rdict = {}
        devices = [name for name in self.nodes if IgnoreInactive or name in self.activenodes]  # intersept
        for n in devices:
            attribs = self.nodes[n]
            if attribs['inst'] is None:
                continue  # not a device
            err = 0
            dev = attribs['inst']
            if not hasattr(dev, set_names[0]):
                continue  # not a spectrumanalyzer
            # ok, a spec analyzer
            rdict[str(n)] = {}
            for index, par in enumerate(parlist):
                if par in conf:
                    val = conf[par]
                else:
                    val = None
                if hasattr(dev, set_names[index]) and val:
                    try:
                        err, val = getattr(dev, set_names[index])(val)
                    except TypeError:
                        err, val = getattr(dev, set_names[index])(*val)
                    rdict[str(n)][par] = val
                elif hasattr(dev, get_names[index]):
                    err, val = getattr(dev, get_names[index])()
                    rdict[str(n)][par] = val
        return rdict

    def Zero_Devices(self, IgnoreInactive=True):
        """
        Zero all devices using CmdDevices
        Input: IgnoreInactive=True
        Return: return val of CmdDevices
        """
        return self.CmdDevices(IgnoreInactive, "Zero", 1)

    def RFOn_Devices(self, IgnoreInactive=True):
        """
        RFOn all devices using CmdDevices
        Input: IgnoreInactive=True
        Return: return val of CmdDevices
        """
        return self.CmdDevices(IgnoreInactive, "RFOn")

    def RFOff_Devices(self, IgnoreInactive=False):
        """
        RFOff all devices using CmdDevices
        Input: IgnoreInactive=False
        Return: return val of CmdDevices
        """
        return self.CmdDevices(IgnoreInactive, "RFOff")

    def Trigger_Devices(self, IgnoreInactive=True):
        """
        Trigger all devices using CmdDevices
        Input: IgnoreInactive=True
        Return: return val of CmdDevices
        """
        return self.CmdDevices(IgnoreInactive, "Trigger")

    def getBatteryLow_Devices(self, IgnoreInactive=True):
        """
        Get a list of all devices in the graph with a low battery state
        Input: IgnoreInactive=True
        Return: list of nodes with low battery state
        """
        lowBatList = []
        # print self.nodes.items()
        devices = [name for name in self.nodes if IgnoreInactive or name in self.activenodes]  # intersept
        for n in devices:
            attribs = self.nodes[n]
            if attribs['inst'] is None:
                continue
            err = 0
            dev = attribs['inst']
            if hasattr(dev, 'getBatteryState'):
                # print "check bat state for node ", n
                stat, bat = dev.getBatteryState()
                if stat < 0:
                    err = dev.GetLastError()
                elif bat < 0:  # Low
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
        devices = [n for n in self.nodes if n in self.activenodes]
        for n in devices:
            attribs = self.nodes[n]
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

    def AmplifierProtect(self, start, end, startlevel, sg_unit=si.WATT, typ='save'):
        isSafe = True
        msg = ''
        if not isinstance(startlevel, quantities.Quantity):
            startlevel = quantities.Quantity(sg_unit, startlevel)
        allpaths = self.find_all_paths(start, end)
        for path in allpaths:  # path is a list of edges
            edges = []
            for p in path:
                left = p.get_source()
                right = p.get_destination()
                edges.append((left, right, p))
            for left, right, edge in edges:
                try:
                    edge_dev = edge.get_attributes()['dev']
                    attribs = self.nodes[edge_dev]
                except KeyError:
                    continue
                if attribs['inst'] is None:
                    continue
                err = 0
                if attribs['active']:
                    dev = attribs['inst']
                    cmds = ['getData', 'GetData']
                    stat = -1
                    for cmd in cmds:
                        # print hasattr(dev, cmd)
                        if hasattr(dev, cmd):
                            # at the moment, we only check for MAXIN
                            what = ['MAXIN']  # ['MAXIN', 'MAXFWD', 'MAXBWD']
                            for w in what:
                                stat = 0
                                try:
                                    stat, result = getattr(dev, cmd)(w)
                                except AttributeError:
                                    # function not callable
                                    # print "attrErr"
                                    continue
                                if stat != 0:
                                    # print stat
                                    continue
                                # ok we have a value that can be checked
                                corr = self.get_path_correction(start, left, POWERRATIO)
                                # for _k,_v in corr.items():
                                # print "corr[%s]:"%_k, _v
                                # print "Startlevel:", startlevel
                                level = corr * startlevel
                                level = level.reduce_to(result._unit)
                                # print "Level:", level
                                # print "What = '%s', Level = %s, Max = %s\n"%(w, str(level), str(result))
                                # if typ=='lasy':
                                notsafe = (abs(level.get_expectation_value()) > abs(result.get_expectation_value()))
                                # elif typ=='save':
                                #    condition=level.get_u() > result.get_l() #be safe: errorbars overlap
                                # else:
                                #    condition=level.get_u() > result.get_l() #be safe: errorbars overlap
                                if notsafe:
                                    isSafe = False
                                    msg += "Amplifier Pretection failed for node '%s'. What = '%s', Level = %s, Max = %s, Startlevel = %s, Corr = %s\n" % (
                                        edge_dev, w, level, result, startlevel, corr)
                            break
        return isSafe, msg

    def MaxSafeLevel(self, start, end, typ='save'):
        levels = []
        allpaths = self.find_all_paths(start, end)
        for path in allpaths:  # path is a list of edges
            edges = []
            for p in path:
                left = p.get_source()
                right = p.get_destination()
                edges.append((left, right, p))
            for left, right, edge in edges:
                try:
                    edge_dev = edge.get_attributes()['dev']
                    attribs = self.nodes[edge_dev]
                except KeyError:
                    continue
                if attribs['inst'] is None:
                    continue
                err = 0
                if attribs['active']:
                    dev = attribs['inst']
                    cmds = ['getData', 'GetData']
                    stat = -1
                    for cmd in cmds:
                        # print hasattr(dev, cmd)
                        if hasattr(dev, cmd):
                            # at the moment, we only check for MAXIN
                            what = ['MAXIN']  # ['MAXIN', 'MAXFWD', 'MAXBWD']
                            for w in what:
                                stat = 0
                                try:
                                    stat, result = getattr(dev, cmd)(w)
                                except AttributeError:
                                    # function not callable
                                    # print "attrErr"
                                    continue
                                if stat != 0:
                                    # print stat
                                    continue
                                # ok we have a value that can be checked
                                corr = self.get_path_correction(start, left, POWERRATIO)
                                level = result / corr  # level at start
                                level = level.reduce_to(result._unit)
                                levels.append(level)
        if not len(levels):
            return None
        else:
            return min(levels)

    def CalcLevelFrom(self, sg, limiter, what):
        if sg not in self.nodes:
            raise UserWarning('Node not in nodes: %s' % sg)
        if limiter not in self.nodes:
            raise UserWarning('Node not in nodes: %s' % limiter)
        if not len(self.find_all_paths(sg, limiter)):
            raise UserWarning('Nodes not connected')
        il = self.get_path_correction(sg, limiter, POWERRATIO)
        return 0

    def __parse_ini(self, ini):
        def readConfig(filename):
            """ Read config data
        
            *** Here add for doc the format of the data ***	
            
            Return configVals
            """
            configVals = configparser.ConfigParser()
            if hasattr(filename, 'readline'):  # file like object
                configVals.read_file(filename)
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
                    d[s][o] = configData.get(section, option)
            return (d)

        # umdpath = getUMDPath()
        # _ini = GetFileFromPath (ini, umdpath)
        # if _ini is None:
        #    raise "Ini file '%s' not found. Path is '%s'"%(ini,umdpath)
        v = readConfig(ini)
        return makeDict(v)


class Leveler(object):
    def __init__(self, mg, actor, output, lpoint, observer, pin=None, datafunc=None, min_actor=None):
        """
        mg: MGraph instance
        actor: name of device in mg. device instance has to have SetLevel method
        output: name of output device: path from actor to output is checked for MaxSafeLevel
        lpoint: name of point where a specific value has to be reached
        observer: name of device where lpoint is observed
        """
        if min_actor is None:
            self.min_actor = quantities.Quantity(si.WATT, 1e-13)  # -100 dBm
        self.mg = mg
        self.actor = actor
        self.sg = getattr(mg, actor)
        self.pm = getattr(mg, observer)

        self.lpoint = lpoint
        self.output = output
        self.observer = observer
        self.MaxSafe = abs(mg.MaxSafeLevel(actor, output).get_expectation_value())
        self.actorunit = self.MaxSafe._unit
        self.lpointunit = None
        self.corr = None
        self.samples = {}
        if pin is None:
            pin = [fac * self.MaxSafe for fac in
                   (0.001, 0.01, 0.1)]  # [quantities.Quantity(si.WATT, 1e-6),quantities.Quantity(si.WATT, 1e-4)]#
        if datafunc is None:
            self.datafunc = lambda x: x
        else:
            self.datafunc = datafunc
        self.add_samples(pin)
        self.update_interpol()

    def add_samples(self, pin):
        if not hasattr(pin, '__iter__'):
            pin = [pin]
        pinr = []
        for pi in pin:
            if pi > self.MaxSafe:
                continue
            if pi < self.min_actor:
                pi = self.min_actor
            pinr.append(pi)
            self.sg.SetLevel(pi)
            pikey = abs(pi)
            pikey = pikey.get_expectation_value_as_float()
            self.pm.Trigger()
            err, obs = self.pm.GetData()
            obs = self.datafunc(obs)
            self.corr = self.mg.get_path_correction(self.observer, self.lpoint, POWERRATIO)
            lpoint = obs * self.corr
            lpoint = lpoint.reduce_to(obs._unit)
            lpoint = abs(lpoint)
            if not self.lpointunit:
                self.lpointunit = lpoint._unit
            assert (self.lpointunit == lpoint._unit)
            self.samples[pikey] = lpoint.get_expectation_value_as_float()
        self.update_interpol()
        return pinr

    def update_interpol(self):
        x = sorted(self.samples)
        y = [self.samples[xi] for xi in x]
        self.interp = interp1d(x, y)
        self.extrap = extrap1d(self.interp)
        self.i_interp = interp1d(y, x)
        self.i_extrap = extrap1d(self.i_interp)

    def adjust_level(self, soll, maxiter=10, relerr=0.01):
        # self.add_samples(soll/self.amp.g)
        sf = soll.get_value(self.lpointunit)
        sf = float(abs(sf))
        safemax = self.MaxSafe.get_expectation_value_as_float()
        # self.x=[]
        # self.y=[]
        for i in range(maxiter):
            inval = self.i_extrap(sf)[0]
            pin = quantities.Quantity(self.actorunit, min(inval, safemax))
            pin = self.add_samples(pin)[0]
            pout = quantities.Quantity(self.lpointunit, self.samples[pin.get_expectation_value_as_float()])
            re = abs(pout - soll) / soll
            re = re.reduce_to(units.ONE)
            # self.x.append(pin)
            # self.y.append(pout)
            # print i, pin, pout, soll, re
            if re.get_expectation_value_as_float() <= relerr:
                break
            if (pin >= self.MaxSafe) and (pout <= soll):
                break
        return pin, pout
