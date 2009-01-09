import time
import os
import umddevice
import umdutil

UMDCMRTYPE = [type(umddevice.UMDCMResult()), type(umddevice.UMDCMResultPtr(umddevice.UMDCMResult()))]
UMDMRTYPE = [type(umddevice.UMDMResult()), type(umddevice.UMDMResultPtr(umddevice.UMDMResult()))]
UMDFIELDTYPE = [type(umddevice.stdVectorUMDMResult()),
                type(umddevice.stdVectorUMDMResultPtr(umddevice.stdVectorUMDMResult()))]
VALTYPE = [float , int]


def _mkdir(newdir):
    if os.path.isdir(newdir):
        pass
    elif os.path.isfile(newdir):
        raise OSError("a file with the same name as the desired dir, '%s', already exists." % newdir)
    else:
        head, tail = os.path.split(newdir)
        if head and not os.path.isdir(head):
            _mkdir(head)
        #print "_mkdir %s" % repr(newdir)
        if tail:
            os.mkdir(newdir)

def my_switch (swstr, fstr, fs=1e9):
    '''Switch the relais'''
    f = umdutil.get_var_from_nearest_outerframe(fstr)
    sw = umdutil.get_var_from_nearest_outerframe(swstr)
    print "In custom.my_switch: f = %s, fs = %s, sw = %s"%(str(f),str(fs),str(sw))
    if f is None or sw is None:
        return -1
    
    err = 0
    if (f<=fs):
        to_ch = 1
    else:
        to_ch = 2
    err, is_ch, val = sw.GetSWState()
    if err or is_ch != to_ch:
        print "going to switch to ch %d"%to_ch 
        err = sw.SwitchTo(to_ch)
    else:
        print "do not switch"
        pass
    return err

class FILETABLOGGER:

    def __init__(self):
        self.mydir = './'+time.strftime("%x", time.localtime()).replace('/','-') 
        _mkdir(self.mydir)
        self.mydir += '\\'
        self.rawfile = {}
        self.desc = {}
        self.params = {}
        self.OutFilesAreOpen = False
        self.rawfile['messages'] = {}
        self.rawfile['messages']['file'] = file(self.mydir+'messages__'+time.strftime("%X", time.localtime()).replace(':','-')+'.log','a+')

    def out_block(self, b):                                   #eigentliche output routine
        if not hasattr(b, 'keys'):
            self.rawfile['messages']['file'].write(b+'\n')
            self.rawfile['messages']['file'].flush()
            return
        
        items = b.keys()
        items.sort()
        if not self.OutFilesAreOpen:
            for i in items:
                self.rawfile[i] = {}
                self.rawfile[i]['file'] = file(self.mydir+str(i)+'__'+time.strftime("%X", time.localtime()).replace(':','-')+'.log','a+')
                self.OutFilesAreOpen = True

    #--------------------------------local functions---------------------------------------        
        def copy_param(block):
            param = {}
            parameters = block.keys()
            parameters.sort()
            for p in parameters:
                    param[p] = block[p]
            return param
        
        def eq_param(block, param):
            meas_par = block.keys()
            meas_par.sort()
            mypar = param.keys()
            mypar.sort()
            if not meas_par == mypar:
                return False
            for p in meas_par:
                if block[p].has_key('parameter'):
                    if param[p].has_key('parameter'):
                        if not eq_param(block[p]['parameter'], param[p]['parameter']):
                            return False
                    else:
                        return False
                if block[p].has_key('comment') & param[p].has_key('comment'):
                    if param[p]['comment'] == block[p]['comment']:
                        pass
                    else:
                        return False
            return True
        
        def write_param(block, item, what):
            parameters = block.keys()
            parameters.sort()
            for p in parameters:
                if block[p].has_key('parameter'):
                    write_param(block[p]['parameter'], item, what)
                if what == 'desc':
                    if block[p].has_key('comment'):
                        self.rawfile[item]['file'].write('# '+str(p)+' : ' + str(block[p]['comment'])+'\n')
                    else:
                        self.rawfile[item]['file'].write('# '+str(p)+'\n')
                if what == 'head':
                    if type(block[p]['value']) in UMDCMRTYPE:
                            self.rawfile[item]['file'].write(str(p)+': [(Re(lower limit), Im(lower limit)), (Re(val), Im(Val)), (Re(upper limit) , Im(upper limit))] unit \t')
                    elif type(block[p]['value']) in UMDMRTYPE:
                            self.rawfile[item]['file'].write(str(p)+': [lower limit, value, upper limit] unit \t')
                    elif type(block[p]['value']) in UMDFIELDTYPE:
                            self.rawfile[item]['file'].write(str(p)+': [lower limit(x), value(x), upper limit(x)] [lower limit(y), value(x), upper limit(y)] [lower limit(z), value(z), upper limit(z)] \t')
                    elif type(block[p]['value']) in VALTYPE:
                            self.rawfile[item]['file'].write(str(p)+ ': value \t')
                    else:
                            self.rawfile[item]['file'].write(str(p)+ '\t')
                elif what == 'value':
                    self.__out(item, block[p]['value'])
    #-------------------------------------------------------------------------------------------------        
        if self.desc.keys() == []:                      # nur bei 1. aufruf der routine gefuellt
            print 'writing first desc and head'
            for item in items:
                if b[item].has_key('comment'):          # kopieren der messwertbeschreibung
                    self.desc[item] = b[item]['comment']
                if b[item].has_key('parameter'):    # parameter kopieren 
                    self.params[item] = copy_param(b[item]['parameter'])
                    self.rawfile[item].setdefault('whead' , True)      #schreibe kopfzeile
                self.rawfile[item].setdefault('wcom' , True)     # schreibe kommentare
        else:
            for item in items:                          # vergleich der messgroessenbschreibungg
                if self.desc.has_key(item):
                    if self.desc[item] == b[item]['comment']:
                        if b[item].has_key('parameter'):    # vergleich der parameterbeschreibung
                            if eq_param(b[item]['parameter'], self.params[item]):
                                pass
                            else:
                                self.params[item] = copy_param(b[item]['parameter'])
                                self.rawfile[item]['whead'] = True        #schreibe kopfzeile
                                print 'write head'
                    else:
                        self.desc[item] = b[item]['comment']
                        self.rawfile[item]['wcom'] = True                         #schreibe kommentare
                        print 'write desc'
        for item in items:
            if self.rawfile[item]['wcom']:
                    self.rawfile[item]['file'].write('# Measure value: ' + str(item)+' : ' + str(self.desc[item])+'\n')
                    self.rawfile[item]['file'].write('# Parameter:\n')
                    write_param(b[item]['parameter'], item, 'desc')
                    self.rawfile[item]['file'].write('\n')
                    self.rawfile[item]['wcom'] = False
            if self.rawfile[item]['whead']:
                self.rawfile[item]['file'].write('# ')
                write_param(b[item]['parameter'], item, 'head')
                if type(b[item]['value']) in UMDCMRTYPE:
                        self.rawfile[item]['file'].write('time \t'+ str(item)+': [(Re(lower limit), Im(lower limit)), (Re(val), Im(Val)), (Re(upper limit) , Im(upper limit))] unit \t')
                elif type(b[item]['value']) in UMDMRTYPE:
                        self.rawfile[item]['file'].write('time \t'+ str(item)+': [ lower limit, value, upper limit] unit \t')
                elif type(b[item]['value']) in UMDFIELDTYPE:
                        self.rawfile[item]['file'].write('time \t'+ str(item)+': [lower limit(x), value(x), upper limit(x) ] [lower limit(y), value(x), upper limit(y)] [lower limit(z), value(z), upper limit(z)] \t')
                elif type(b[item]['value']) in VALTYPE:
                        self.rawfile[item]['file'].write(str(item)+ ': value')
                else:
                        self.rawfile[item]['file'].write(str(item))
                self.rawfile[item]['file'].write('\n')
                self.rawfile[item]['whead'] = False
                
            if b[item].has_key('parameter'):
                write_param(b[item]['parameter'], item, 'value')
            if b[item].has_key('value'):
                self.__out(item, b[item]['value'])
            else:
                self.__out(item, 'None')
            self.rawfile[item]['file'].write('\n')
            self.rawfile[item]['file'].flush()

    def close_file(self):
        key = self.rawfile.keys
        for k in key:
            self.rawfile[k]['file'].close()

    def __out(self, key, item):
        if hasattr(item, 'keys'):  # a dict
            self.rawfile[key]['file'].write( " { ")
            for k in item.keys():
                self.rawfile[key]['file'].write(str(k)+":")
                self.__out(key, item[k])
            self.rawfile[key]['file'].write( " } \t")
        elif hasattr(item,'get_v'): # MResult or CMResult
            self.rawfile[key]['file'].write( item.get_TimeStr()+' '+str(item)+' \t')
        elif type(item) in UMDFIELDTYPE: # UMDFieldTypes
            self.rawfile[key]['file'].write( item[0].get_TimeStr()+' [ '+str(item[0]) + ' , ' + str(item[1]) + ' , '
                                             + str(item[2]) + ' ]\t')
        elif hasattr(item, 'sort'):  # a list
            self.rawfile[key]['file'].write( " [ ")
            for i in item:
                self.__out(key, i)
            self.rawfile[key]['file'].write( " ] \t")
        elif hasattr(item, 'append'): # vector
            self.rawfile[key]['file'].write( " ( ")
            for i in item:
                self.__out(key, i)
            self.rawfile[key]['file'].write( " ) \t")
        else:
            self.rawfile[key]['file'].write(' ' + str(item) + ' ')

