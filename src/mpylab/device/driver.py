# -*- coding: utf-8 -*-
"""This is the :mod:`mpylab.device.driver` module.

   :copyright: Hans Georg Krauthäuser
   :license: All rights reserved

"""

import re
import os
from mpylab.tools.Configuration import Configuration, fstrcmp
from mpylab.device.device import CONVERT, Device


class DRIVER(object):
    """
    Parent class for all py-drivers.
    
    Beside the common API method for all drivers (see below) this class
    also implements the following low level methods:

       .. method:: write(cmd)
    
          Write a command to the instrument.
    
          :param cmd: the command
          :type cmd: string
          :rtype: status code of the native write operation
    
       .. method:: read(tmpl)
    
          Read an answer from the instrument instrument.
    
          :param tmpl: a template string
          :type tmpl: valid regular expression string
          :rtype: the groupdict of the match
          
          Example: 
          
             If a device (signal generator in this case) returns
             ``:MODULATION:AM:INTERNAL 80 PCT`` to indicate a AM modulation depth 
             of 80%, a template string of ``:MODULATION:AM:INTERNAL (?P<depth>\d+) PCT`` will 
             results in a return dict of ``{"depth": 80}``.
    
       .. method:: query(cmd, tmpl)
    
          Write a command to the instrument and read the answer.
    
          :param cmd: the command
          :type cmd: string
          :param tmpl: a template string
          :type tmpl: valid regular expression string
          :rtype: the groupdict of the match
    
    For other low level operation you may use the device stored in ``self.dev`` directly.
    """

    def __init__(self, SearchPaths=None):
        if SearchPaths is None:
            SearchPaths = [os.getcwd()]
        self.SearchPaths = SearchPaths
        self.error = 0
        self.conf = {'description': {}, 'init_value': {}}
        self.IDN = ''
        self.convert = CONVERT()
        self.errors = Device._Errors
        self.dev = None

    def _init_bus(self, timeout=5,
                  chunk_size=20480,
                  values_format=None,
                  term_chars=None,
                  send_end=True,
                  delay=0,
                  lock=None):
        gpib = None
        visa = None
        virtual = False
        if 'gpib' in self.conf['init_value']:
            gpib = self.conf['init_value']['gpib']
        if 'visa' in self.conf['init_value']:
            visa = self.conf['init_value']['visa']
        if 'virtual' in self.conf['init_value']:
            virtual = self.conf['init_value']['virtual']
        if virtual or not (gpib or visa):  # Virtual mode
            self.dev = None
            self.write = self._debug_write
            self.read = self._debug_read
            self.query = self._debug_query
            return self.dev
        else:  # Normal mode
            import pyvisa
            import pyvisa.constants
            self.rm = pyvisa.ResourceManager()   # configure backend in .pyvisarc in your home dir
            if lock is None:
                lock = pyvisa.constants.AccessModes.no_lock
            if visa:
                res_name = visa
            else:
                res_name = f'GPIB::{gpib}'
            self.dev = self.rm.open_resource(res_name,
                                             access_mode=lock,
                                             timeout=timeout * 1000,
                                             chunk_size=chunk_size,
                                             #send_end=send_end,
                                             query_delay=delay)
            # if values_format in (None, 'ascii', 'ASCII'):
            #     self.dev.values_format.is_binary = False
            # else:
            #     self.dev.values_format.is_binary = True
            if not (term_chars is None):
                self.dev.read_termination = self.dev.write_termination = term_chars

            self.write = self._gpib_write
            self.read = self._gpib_read
            self.query = self._gpib_query
            return self.dev

    def _gpib_write(self, cmd):
        # print "In write", cmd
        stat = 0
        if self.dev and isinstance(cmd, str):
            stat = self.dev.write(cmd)
        return stat

    def _gpib_read(self, tmpl=None):
        # print("In read", tmpl)
        dct = None
        if self.dev:
            ans = self.dev.read()
            if tmpl is None:
                return ans
            m = re.match(tmpl, ans)
            if m:
                dct = m.groupdict()
        return dct

    def _gpib_query(self, cmd, tmpl=None):
        # print("In query", cmd, tmpl)
        dct = None
        if self.dev and isinstance(cmd, str):
            ans = self.dev.query(cmd)
            if tmpl is None:
                return ans
            # print "ans=",ans
            m = re.match(tmpl, ans)
            # print "m=",m
            if m:
                dct = m.groupdict()
        return dct

    def _debug_write(self, cmd):
        print("%s out:" % self.IDN, cmd)
        return 0

    def _debug_read(self, tmpl):
        print(("In read", tmpl))
        dct = None
        ans = eval(input('%s in: %s -> ' % (self.IDN, tmpl)))
        m = re.match(tmpl, ans)
        if m:
            dct = m.groupdict()
        return dct

    def _debug_query(self, cmd, tmpl):
        print(("In query", cmd, tmpl))
        self.write(cmd)
        return self.read(tmpl)

    def get_config(self, ininame, channel):
        self.channel = channel
        if not self.channel:
            self.channel = 1
        if not ininame:
            self.conf['init_value']['virtual'] = True
        else:
            self.Configuration = Configuration(ininame, self.conftmpl)
            self.conf.update(self.Configuration.conf)

    def Init(self, ininame=None, channel=None):
        """
        Init the instrument.
        
        Parameters:
            
           - *ininame*: filename or file-like object with the initialization
             parameters for the device. This parameter is handled by 
             :meth:`mpylab.tools.Configuration.Configuration` which takes also 
             a configuration template stored in ``self.conftmpl``.
           - *channel*: an integer specifiing the channel number of multi channel devices.
             Numbering is starting with 1.
             
        Return: 0 if sucessful. 
        """
        self.error = 0
        self.get_config(ininame, channel)
        if not self.conf['init_value'].get('virtual', False):
            buspars = {}
            for k in ('timeout',
                      'chunk_size',
                      'values_format',
                      'term_chars',
                      'send_end',
                      'delay',
                      'lock'):
                try:
                    buspars[k] = getattr(self, k)
                except AttributeError:
                    pass

            self.dev = self._init_bus(**buspars)
            if self.dev is not None:
                dct = self._do_cmds('Init', locals())
                self._update(dct)
        # print self.error
        return self.error

    def _get(self, sec, key):
        sectok = fstrcmp(sec, self.conftmpl, n=1, cutoff=0, ignorecase=True)[0]
        keytok = fstrcmp(key, self.conftmpl[sectok], n=1, cutoff=0, ignorecase=True)[0]
        if '%' in sectok:
            pos = sectok.index('%')
            sectok = sectok[:pos] + sec[pos:]
        return self.conf[sectok][keytok]

    def _do_cmds(self, key, callerdict=None):
        dct = {}  # preset returned dictionary
        if not hasattr(self, '_cmds'):
            return dct  # if self._cmds is not defined we return a empty dict
        if key in self._cmds:  # in key is the name of the command to excecute, e.g. 'SetFreq'

            for cmd, tmpl in self._cmds[key]:  # loop all command, template pairs for key 'key'

                try:  # try to eval cmd as a python expression in callerdict and assign result to expr
                    # This will insert the value of variables (e.g. freq) into the command
                    expr = eval(cmd, callerdict)
                    # print expr
                    if expr is None:  # no substitution -> None is reutned
                        expr = cmd
                except (SyntaxError, NameError):
                    expr = cmd  # else, expr is set to cmd
                    # tmpl is the mask for the string to read
                if not tmpl:  # no mask, no read
                    # expr may be a function call. Let's try..
                    try:
                        exec(expr, callerdict)
                    except (SyntaxError, NameError, TypeError):
                        self.write(expr)
                elif not cmd:  # only data read    no cmd, no write
                    dct.update(self.read(tmpl))
                else:  # both -> write and read
                    dct.update(self.query(expr, tmpl))

        return dct

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
        """
        Quit the instrument.
        """
        self.error = 0
        dct = self._do_cmds('Quit', locals())
        self._update(dct)
        return self.error

    def SetVirtual(self, virtual):
        """
        Sets ``self.conf['init_value']['virtual']`` to ``virtual``.
        """
        self.error = 0
        self.conf['init_value']['virtual'] = virtual
        return self.error

    def GetVirtual(self):
        """
        Returns ``(0, self.conf['init_value']['virtual'])``
        """
        self.error = 0
        print(self.conf)
        try:
            virt = self.conf['init_value']['virtual']
        except KeyError:
            virt = False
        return self.error, virt

    def GetDescription(self):
        """
        Returns ``(0, desc)`` with ``desc`` is the concatenation of ``self.conf['description']``
        and ``self.IDN``. The former comes from the ini file, the latter may be set by the driver during
        initialization.
        """
        self.error = 0
        dct = self._do_cmds('GetDescription', locals())
        # print dct
        self._update(dct)
        try:
            des = self.conf['description']
        except KeyError:
            des = self.conf['description'] = ''
        # print self.conf['description'], self.IDN
        return self.error, str(self.conf['description']) + self.IDN
