# -*- coding: utf-8 -*-
"""This is the :mod:`mpylab.device.driver` module.

   :copyright: Hans Georg Krauthäuser
   :license: All rights reserved

"""

import re
from mpylab.tools.Configuration import Configuration, fstrcmp
from mpylab.device.device import CONVERT, Device


# from tools import *

class DRIVER(object):
    """
    Parent class for all py-drivers.
    
    Beside the common API method for all drivers (see below) this class
    also implements the following low level methods:

       .. method:: write(cmd)
    
          Write a command to the instrument.
    
          :param cmd: the command
          :type cmd: string
          :return: status code of the native write operation
    
       .. method:: read(tmpl)
    
          Read an answer from the instrument instrument.
    
          :param tmpl: a template string
          :type tmpl: valid regular expression string
          :return: the groupdict of the match
          
          Example::
          
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
          :return: the groupdict of the match
    
    For other low level operation you may use the device stored in ``self.dev`` directly.
    """

    # __metaclass__=Meta_Driver


    def __init__(self):
        self.error = 0
        self._commands = {}
        self.conf = {'description':  {},
                     'init_value':  {},
                     'bus': {}}
        self.IDN = ''
        self.convert = CONVERT()
        self.errors = Device._Errors
        self.dev = None
        self.isinit = False

    def _init_bus(self, virtual):
        if virtual:
            self.dev = Virtual_Communication(self.IDN)

        elif 'gpib' in self.conf['init_value']:
            self.conf['bus']['gpib'] = self.conf['init_value']['gpib']
            # print 'gpib'
            self.dev = GPIB_Communication(**self.conf['bus'])
            # print self.dev

        # other Buss-Systems, if required in the future:
        # elif 'something' in self.conf['init_value']:
        #    self.dev = somthing_Communication(**self.conf['bus'])

        else:
            self.dev = Virtual_Communication(self.IDN)

    def Init(self, ininame=None, channel=None):
        """
        Init the instrument.
        
        :param ininame: filename or file-like object with the initialization parameters for the device. 
                        This parameter is handled by 
                        :meth:`mpylab.tools.Configuration.Configuration` which takes also 
                        a configuration template stored in ``self.conftmpl``.
        :param channel: an integer specifiing the channel number of multi channel devices.
                         Numbering is starting with 1.
        :return: 0 if sucessful. 
        """

        error = 0
        self.channel = channel
        if not self.channel:
            self.channel = 1
        if not ininame:
            self.conf['init_value']['virtual'] = True
            self._init_bus(virtual=True)
        else:
            self.Configuration = Configuration(ininame, self.conftmpl, casesensitive=True)
            self.conf.update(self.Configuration.conf)
            if not self.conf['init_value']['virtual']:
                self._init_bus(virtual=False)
            else:
                self._init_bus(virtual=True)

        self.isinit = True
        return error

    def _get(self, sec, key):
        sectok = fstrcmp(sec, self.conftmpl, n=1, cutoff=0, ignorecase=True)[0]
        keytok = fstrcmp(key, self.conftmpl[sectok], n=1, cutoff=0, ignorecase=True)[0]
        if '%' in sectok:
            pos = sectok.index('%')
            sectok = sectok[:pos] + sec[pos:]
        # print sectok, keytok
        # print self.conf.keys()
        return self.conf[sectok][keytok]

    def Quit(self):
        """
        Quit the instrument.
        """
        error = 0
        try:
            error, re = self._Quit()
        except:
            pass
        return error

    def SetVirtual(self, virtual):
        """
        Sets::
        
            ``self.conf['init_value']['virtual']`` to ``virtual``.
        """
        error = 0
        self.conf['init_value']['virtual'] = virtual
        return error

    def GetVirtual(self):
        """
        Returns::
        
            ``(0, self.conf['init_value']['virtual'])``
        """
        return 0, self.conf['init_value']['virtual']

    def GetDescription(self):
        """
        Returns::
        
             ``(0, desc)`` with ``desc`` is the concatination of ``self.conf['description']``
            and ``self.IDN``. The former comes from the ini file, the latter may be set by the driver during
            initialization.
        """
        try:
            error, re = self.__GetDescription()
            self.IDN = str(re)
        except:
            pass
        try:
            des = self.conf['description']
        except KeyError:
            des = self.conf['description'] = ''

        # print self.conf['description'], self.IDN
        return error, str(self.conf['description']) + self.IDN

    def getCommunication_obj(self):
        return self.dev

    def getCommands(self):
        return self._commands

    def isInit(self):
        return self.isinit


class Virtual_Communication(object):

    def __init__(self, IDN):
        self.IDN = IDN

    def write(self, cmd):
        print("IN write", cmd)
        print("%s out:" % self.IDN, cmd)

    def read(self):
        print("In read")
        ans = eval(input('%s -> ' % (self.IDN)))
        return ans

    def query(self, cmd):
        print("In query", cmd)
        self.write(cmd)
        return self.read()


class GPIB_Communication(object):

    def __init__(self, gpib=20,
                 timeout=5,
                 chunk_size=20480,
                 values_format=None,
                 term_chars=None,
                 send_end=True,
                 delay=0,
                 lock=None):

        import pyvisa
        import pyvisa.constants
        self.rm = pyvisa.ResourceManager('@py')
        # if values_format is None:
        #    values_format = visa.ascii
        if lock is None:
            lock = pyvisa.constants.AccessModes.no_lock
        self.dev = self.rm.open_resource(f'GPIB::{gpib}',
                                         timeout=timeout * 1000,
                                         chunk_size=chunk_size,
                                         send_end=send_end,
                                         query_delay=delay,
                                         lock=lock)
        # if values_format in (None, 'ascii', 'ASCII'):
        #     self.dev.values_format.is_binary = False
        # else:
        #     self.dev.values_format.is_binary = True
        if not (term_chars is None):
            self.dev.read_termination = self.dev.write_termination = term_chars

    def write(self, cmd):
        print("In write: ", cmd)
        stat = 0
        if self.dev and isinstance(cmd, str):
            stat = self.dev.write(cmd)
        return stat

    def read(self, tmpl):
        # print("In read", tmpl)
        dct = None
        if self.dev:
            ans = self.dev.read()
            m = re.match(tmpl, ans)
            if m:
                dct = m.groupdict()
        return dct

    def query(self, cmd, tmpl):
        # print("In query", cmd, tmpl)
        dct = None
        if self.dev and isinstance(cmd, str):
            ans = self.dev.query(cmd)
            # print "ans=",ans
            m = re.match(tmpl, ans)
            # print "m=",m
            if m:
                dct = m.groupdict()
        return dct
