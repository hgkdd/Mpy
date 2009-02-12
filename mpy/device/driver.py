# -*- coding: utf-8 -*-

import re
from mpy.tools.Configuration import Configuration,fstrcmp
from mpy.device.device import CONVERT, Device

class DRIVER(object):
    """
    Parent class for all py-drivers
    """
    def __init__(self):
        self.error=0
        self.conf={}
        self.conf['description']={}
        self.conf['init_value']={}
        self.IDN=''
        self.convert=CONVERT()
        self.errors=Device._Errors
        self.dev=None

    def _init_bus(self,timeout=5,
                       chunk_size=20480,
                       values_format=None,
                       term_chars=None,
                       send_end=True,
                       delay=0,
                       lock=None):
        gpib=None
        virtual=False
        if 'gpib' in self.conf['init_value']:
            gpib=self.conf['init_value']['gpib']
        if 'virtual' in self.conf['init_value']:
            virtual=self.conf['init_value']['virtual']
        # print virtual, gpib
        if virtual or not gpib:
            self.dev=None
            self.write=self._debug_write
            self.read=self._debug_read
            self.query=self._debug_query
            return True
        else:
            import visa
            if values_format is None:
                values_format=visa.ascii
            if lock is None:
                lock=visa.VI_NO_LOCK
            self.dev=visa.instrument('GPIB::%d'%gpib,
                                     timeout=timeout,
                                     chunk_size=chunk_size,
                                     values_format=values_format,
                                     term_chars=term_chars,
                                     send_end=send_end,
                                     delay=delay,
                                     lock=lock)
            self.write=self._gpib_write
            self.read=self._gpib_read
            self.query=self._gpib_query
            return self.dev
        
    def _gpib_write(self, cmd):
        stat=-1
        if self.dev:
            stat=self.dev.write(cmd)
        return stat
    
    def _gpib_read(self, tmpl):
        #print "In read", tmpl 
        dct=None
        if self.dev:
            ans=self.dev.read()
            m=re.match(tmpl, ans)
            if m:
                dct=m.groupdict()
        return dct

    def _gpib_query(self, cmd, tmpl):
        #print "In query", cmd, tmpl
        dct=None
        if self.dev:
            ans=self.dev.ask(cmd)
            m=re.match(tmpl, ans)
            if m:
                dct=m.groupdict()
        return dct

    def _debug_write(self, cmd):
        print "%s out:"%self.IDN, cmd
        return 0
    
    def _debug_read(self, tmpl):
        #print "In read", tmpl 
        dct=None
        ans=raw_input('%s in: %s -> '%(self.IDN, tmpl))
        m=re.match(tmpl, ans)
        if m:
            dct=m.groupdict()
        return dct

    def _debug_query(self, cmd, tmpl):
        #print "In query", cmd, tmpl 
        self.write(cmd)
        return self.read(tmpl)

    def Init(self, ininame=None, channel=None):
        self.error=0
        if not ininame:
            self.conf['init_value']['virtual']=True
        else:
            self.Configuration=Configuration(ininame, self.conftmpl)
            self.conf.update(self.Configuration.conf)
            if not self.conf['init_value']['virtual']:
                buspars={}
                #print "Here"
                for k in ('timeout',
                          'chunk_size',
                          'values_format',
                          'term_chars',
                          'send_end',
                          'delay',
                          'lock'):
                    try:
                        buspars[k]=getattr(self, k)
                    except AttributeError:
                        pass
                
                self.dev=self._init_bus(**buspars)
                if self.dev != None:
                    dct=self._do_cmds('Init', locals())
                    self._update(dct)
        return self.error

    def _get(self, sec, key):
        sectok=fstrcmp(sec,self.conftmpl,n=1,cutoff=0,ignorecase=True)[0]
        keytok=fstrcmp(key,self.conftmpl[sectok],n=1,cutoff=0,ignorecase=True)[0]
        if '%' in sectok:
            pos=sectok.index('%')
            sectok=sectok[:pos]+sec[pos:]
        #print sectok, keytok
        #print self.conf.keys()
        return self.conf[sectok][keytok]
    
    def _do_cmds(self, key, callerdict=None):
        dct={} # preset returned dictionary
        if not hasattr(self, '_cmds'): 
            return dct
        if key in self._cmds: 
            for cmd,tmpl in self._cmds[key]: # loop all command, template pairs for key 'key'
                try:
                    expr=eval(cmd,callerdict) # try to eval cmd as a python expression in callerdict and assign result to expr
                except (SyntaxError, NameError):
                    expr=cmd # else, expr is set to cmd
                    
                # tmpl is the mask for the string to read
                if not tmpl: # no mask, no read
                    self.write(expr)
                elif not cmd: # no cmd, no write
                    dct=self.read(tmpl)
                else: # both -> write and read
                    dct=self.query(expr, tmpl)
        return dct

        #print dct
        #print self.__dict__

    def _update(self, dct):
        """Update the class namespace from the dictionary dct.

        If dct is None 'General Driver Error' is 'or'ed to self.error.
        Fuction returns 'None'.
        """
        if dct is None:
            self.error |= self.errors["General Driver Error"]
        else:
            self.__dict__.update(dct)

    def Quit(self):
        self.error=0
        dct=self._do_cmds('Quit', locals())
        self._update(dct)
        return self.error

    def SetVirtual(self, virtual):
        self.error=0
        self.conf['init_value']['virtual']=virtual
        return self.error

    def GetVirtual(self):
        self.error=0
        return self.error, self.conf['init_value']['virtual']

    def GetDescription(self):
        self.error=0
        dct=self._do_cmds('GetDescription', locals())
        self._update(dct)
        try:
            des = self.conf['description']
        except KeyError:
            des = self.conf['description']=''
        return self.error, self.conf['description']+self.IDN

