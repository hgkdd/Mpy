# -*- coding: utf-8 -*-
"""
This is the :mod:`mpylab.device.driver` module.

   :author: Hans Georg Krauthäuser (main author)

   :license: GPLv3 or higher
"""

import os
import pyvisa

from mpylab.tools.configuration import Configuration, fstrcmp
from mpylab.device.device import CONVERT, Device
from mpylab.device.communication_gpib import CommunicationGpib
from mpylab.device.communication_debug import CommunicationDebug
from mpylab.device.communication_prologix import CommunicationPrologix

class DRIVER:
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
             of 80%, a template string of ``:MODULATION:AM:INTERNAL (?P<depth>\\d+) PCT`` will 
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
        self.CommunicationClass = None

    def _init_bus(self, timeout=5,
                  chunk_size=20480,
                  values_format=None,
                  term_chars=None,
                  send_end=True,
                  delay=0,
                  lock=None):
        gpib = None
        visa = None
        prologix = None
        virtual = False
        if 'gpib' in self.conf['init_value']:
            gpib = self.conf['init_value']['gpib']
        if 'visa' in self.conf['init_value']:
            visa = self.conf['init_value']['visa']
            if visa.lower().startswith('prologix'):
                prologix = visa
                visa = None
        if 'virtual' in self.conf['init_value']:
            virtual = self.conf['init_value']['virtual']
        # switch to appropriate Communication Class
        if virtual or not (gpib or visa or prologix):  # Virtual mode
            self.CommunicationClass = CommunicationDebug(self.IDN)
            self.write = self.CommunicationClass.write
            self.read = self.CommunicationClass.read
            self.query = self.CommunicationClass.query
            self.dev = None
        elif prologix:   # prologix mode
            # prologix looks like: PROLOGIX::192.168.7.206::1234::SOCKET::17
            # we have to extract ip-addr and port
            s = prologix.split('::')
            ip = s[1]
            port = int(s[2])
            gpib = int(s[4])
            bufsize = 256
            TXEOL = b'\n'
            timeout_s = 3
            self.CommunicationClass = CommunicationPrologix(ip,
                                                            port,
                                                            gpib,
                                                            bufsize,
                                                            TXEOL,
                                                            timeout_s)
            self.write = self.CommunicationClass.write
            self.read = self.CommunicationClass.read
            self.query = self.CommunicationClass.query
            self.dev = True
        else:  # pyvisa mode
            if lock is None:
                lock = pyvisa.constants.AccessModes.no_lock
            if visa:
                res_name = visa
            else:
                res_name = f'GPIB::{gpib}::INSTR'
            self.CommunicationClass = CommunicationGpib(res_name,
                                                        lock=lock,
                                                        timeout_s=timeout,
                                                        chunk_size=chunk_size,
                                                        query_delay_s=delay,
                                                        send_end=True,
                                                        read_term=term_chars,
                                                        write_term=term_chars)
            self.write = self.CommunicationClass.write
            self.read = self.CommunicationClass.read
            self.query = self.CommunicationClass.query
            self.dev = self.CommunicationClass.dev
        return self.dev

    def get_config(self, ini, channel):
        self.channel = channel
        if not self.channel:
            self.channel = 1
        if not ini:
            self.conf['init_value']['virtual'] = True
        else:
            self.Configuration = Configuration(ini, self.conftmpl)
            self.conf.update(self.Configuration.conf)

    def Init(self, ini=None, channel=None, ignore_bus=False):
        """
        Init the instrument.
        
        Parameters:
            
           - *ini*: filename or file-like object with the initialization
             parameters for the device. This parameter is handled by 
             :meth:`mpylab.tools.Configuration.Configuration` which takes also 
             a configuration template stored in ``self.conftmpl``.
           - *channel*: an integer specifiing the channel number of multi channel devices.
             Numbering is starting with 1.
             
        Return: 0 if sucessful. 
        """
        self.error = 0
        self.get_config(ini, channel)
        if ignore_bus:
            return 0
        buspars = {}
        if not self.conf['init_value'].get('virtual', False):
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
        sectok = fstrcmp(sec, list(self.conftmpl.keys()), cutoff=0, ignorecase=True)[0]
        keytok = fstrcmp(key, list(self.conftmpl[sectok].keys()), cutoff=0, ignorecase=True)[0]
        if '%' in sectok:
            pos = sectok.index('%')
            sectok = sectok[:pos] + sec[pos:]
        return self.conf[sectok][keytok]

    def _render_cmd(self, cmd, callerdict=None):
        """
        Render a command string during the transition from eval-based command
        expressions to str.format-based templates.

        Supported for now:
        1. New style:
             "FREQ {freq} HZ"
           -> cmd.format(**callerdict)

        2. Legacy style:
             "'FREQ %s HZ'%freq"
           -> eval(cmd, callerdict)

        If formatting/evaluation is not possible, the original cmd is returned.
        """
        if callerdict is None:
            callerdict = {}

        # New template style: only try format when curly braces are present
        if isinstance(cmd, str) and ('{' in cmd and '}' in cmd):
            try:
                return cmd.format(**callerdict)
            except (KeyError, AttributeError, IndexError, ValueError):
                pass

        # Legacy fallback
        try:
            expr = eval(cmd, callerdict)
            if expr is None:
                return cmd
            return expr
        except (SyntaxError, NameError, TypeError, AttributeError, ValueError):
            return cmd

    def _do_cmds(self, key, callerdict=None):
        send_opc = getattr(self, 'send_opc', False)  # look for send_opc; default to dont send
        dct = {}  # preset returned dictionary
        if not hasattr(self, '_cmds'):
            return dct  # if self._cmds is not defined we return a empty dict
        if key in self._cmds:  # in key is the name of the command to excecute, e.g. 'SetFreq'
            for cmd, tmpl in self._cmds[key]:  # loop all command, template pairs for key 'key'
                expr = self._render_cmd(cmd, callerdict)
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
                    dct.update(self.query(expr, tmpl, send_opc=send_opc))
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
        # print(self.conf)
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
        desc_dict = self.conf.get('description', {})
        desc = desc_dict.get('description', '')
        return self.error, f'{desc}; {self.IDN}'

if __name__ == "__main__":
    import io
    from mpylab.tools.util import format_block
    from mpylab.tools.configuration import strbool

    class DummyDriver(DRIVER):
        conftmpl = {
            'description': {
                'description': str,
                'type': str,
                'vendor': str,
                'serialnr': str,
                'deviceid': str,
                'driver': str,
            },
            'init_value': {
                'gpib': int,
                'visa': str,
                'virtual': strbool,
            },
            'channel_%d': {
                'name': str,
                'unit': str,
            }
        }

        def __init__(self):
            super().__init__()
            self.IDN = "DUMMY,TEST,0001,1.0"
            self._cmds = {}

    ini_text = format_block("""
        [DESCRIPTION]
        description: 'Dummy Test Device'
        type: 'DUMMY'
        vendor: 'OpenAI'
        serialnr: '12345'
        deviceid: 'DEV-01'
        driver: 'dummy_driver'

        [INIT_VALUE]
        virtual: 1
        gpib: 18

        [CHANNEL_1]
        name: 'CH1'
        unit: 'dBm'
    """)

    ini = io.StringIO(ini_text)

    print("=== DRIVER Texttest ===")

    drv = DummyDriver()

    try:
        print("Initialisiere ...")
        err = drv.Init(ini=ini, channel=1)
        print("Init-Fehlercode:", err)

        print("\n--- Konfiguration ---")
        print("conf:", drv.conf)
        print("channel:", drv.channel)

        print("\n--- Virtual Mode ---")
        print("GetVirtual():", drv.GetVirtual())
        print("CommunicationClass:", type(drv.CommunicationClass).__name__ if drv.CommunicationClass else None)
        print("dev:", drv.dev)

        print("\n--- Description ---")
        print("GetDescription():", drv.GetDescription())

        print("\n--- Einzelzugriffe ---")
        print("description.description:", drv.conf['description']['description'])
        print("init_value.virtual:", drv.conf['init_value']['virtual'])
        print("channel_1.name:", drv.conf['channel_1']['name'])
        print("channel_1.unit:", drv.conf['channel_1']['unit'])

        print("\nTexttest erfolgreich.")

    except Exception as e:
        print("Texttest fehlgeschlagen:", e)
        raise