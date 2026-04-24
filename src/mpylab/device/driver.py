# -*- coding: utf-8 -*-
"""
This is the :mod:`mpylab.device.driver` module.

   :author: Hans Georg Krauthäuser (main author)

   :license: GPLv3 or higher
"""

import os
from dataclasses import dataclass, field


from mpylab.tools.configuration import Configuration, fstrcmp
from mpylab.device.device import CONVERT, Device
from mpylab.device.communication_gpib import CommunicationGpib
from mpylab.device.communication_debug import CommunicationDebug
from mpylab.device.communication_prologix import CommunicationPrologix


ALLOW_LEGACY_EVAL = True
ALLOW_LEGACY_EXEC = True

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
        self.bus_ready = False
        self.CommunicationClass = None

    def _init_bus(self, timeout=5,
                  chunk_size=20480,
                  values_format=None,
                  term_chars=None,
                  send_end=True,
                  delay=0,
                  lock=None):
        self.bus_ready = False
        self.dev = None
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
            self.bus_ready = True
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
            self.bus_ready = True
        else:  # pyvisa mode
            if visa:
                res_name = visa
            else:
                res_name = f'GPIB::{gpib}::INSTR'
            self.CommunicationClass = CommunicationGpib(res_name,
                                                        lock=lock,
                                                        timeout_s=timeout,
                                                        chunk_size=chunk_size,
                                                        query_delay_s=delay,
                                                        send_end=send_end,
                                                        read_term=term_chars,
                                                        write_term=term_chars)
            self.write = self.CommunicationClass.write
            self.read = self.CommunicationClass.read
            self.query = self.CommunicationClass.query
            self.dev = self.CommunicationClass.dev
            self.bus_ready = True
        return self.dev

    def get_config(self, ini, channel):
        """Load configuration for a channel from ini source into ``self.conf``."""
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
        if self.bus_ready:
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

    def _resolve_expr(self, expr, callerdict=None):
        if callerdict is None:
            callerdict = {}

        if callable(expr):
            callargs = dict(callerdict)
            callargs.pop("self", None)
            expr = expr(self, **callargs)

        if expr is None:
            return ("noop",)

        if isinstance(expr, str):
            return ("write", expr)

        if isinstance(expr, MethodCall):
            return ("call", getattr(self, expr.name), expr.args, expr.kwargs)

        raise TypeError(f"Unsupported expr type: {type(expr).__name__}")

    def _render_cmd(self, cmd, callerdict=None):
        """
        Render a command string during the transition from eval-based command
        expressions to format/callable-based templates.

        Supported:
        1. New style:
             "FREQ {freq} HZ"
           -> cmd.format(**callerdict)

        2. Legacy %-mapping style:
             "SENSe%(channel)d:FREQuency:CENTer %(cfreq)s HZ"
           -> cmd % callerdict

        3. Legacy eval style:
             "'FREQ %s HZ'%freq"
           -> eval(cmd, callerdict)

        If rendering is not possible, the original cmd is returned.
        """
        if callerdict is None:
            callerdict = {}

        if cmd is None:
            return None

        if not isinstance(cmd, str):
            return cmd

        # 1) %-mapping style first
        if "%(" in cmd:
            try:
                return cmd % callerdict
            except (KeyError, TypeError, ValueError):
                pass

        # 2) new {}-style
        if "{" in cmd and "}" in cmd:
            try:
                return cmd.format(**callerdict)
            except (KeyError, AttributeError, IndexError, ValueError):
                pass

        # 3) simple %-style with single value fallback
        if "%" in cmd and len(callerdict) == 1:
            try:
                return cmd % next(iter(callerdict.values()))
            except (TypeError, ValueError):
                pass

        # 4) legacy eval fallback
        if ALLOW_LEGACY_EVAL:
            try:
                expr = eval(cmd, callerdict)
                if expr is None:
                    return cmd
                return expr
            except (SyntaxError, NameError, TypeError, AttributeError, ValueError):
                return cmd
        else:
            raise RuntimeError(f"Legacy eval mode not supported. Check yor command: {cmd}")



    def _bind_preset_action(self, action, value, extra_kwargs=None):
        """
        Convert one preset action into a _cmds-compatible (cmd, tmpl) tuple.

        Parameters
        ----------
        action :
            Tuple (cmd, tmpl), where cmd may be a string or a callable.
        value :
            Configuration value from self.conf[sec][key].
        extra_kwargs :
            Optional dict of additional keyword arguments to bind into callable cmd.

        Returns
        -------
        tuple
            A (cmd, tmpl) tuple suitable for appending to self._cmds['Preset'].
        """
        if extra_kwargs is None:
            extra_kwargs = {}

        cmd, tmpl = action

        if callable(cmd):
            bound_kwargs = dict(extra_kwargs)

            return (
                lambda _self, _cmd=cmd, _v=value, _bound_kwargs=bound_kwargs, **kwargs:
                _cmd(_self, v=_v, **_bound_kwargs, **kwargs),
                tmpl
            )

        return (cmd, tmpl)

    def _is_action_tuple(self, value):
        """Return True if value looks like one low-level (cmd, tmpl) action."""
        if not isinstance(value, (tuple, list)) or len(value) != 2:
            return False
        cmd, _tmpl = value
        return cmd is None or isinstance(cmd, (str, MethodCall)) or callable(cmd)

    def _normalize_preset_actions(self, actions, value, extra_kwargs=None):
        """Normalize preset action definitions into a flat list of (cmd, tmpl) tuples."""
        if extra_kwargs is None:
            extra_kwargs = {}

        if isinstance(actions, str):
            return [(MethodCall(actions, args=(value,)), None)]

        if self._is_action_tuple(actions):
            return [self._bind_preset_action(tuple(actions), value, extra_kwargs=extra_kwargs)]

        if isinstance(actions, (tuple, list)):
            normalized = []
            for action in actions:
                normalized.extend(
                    self._normalize_preset_actions(action, value, extra_kwargs=extra_kwargs)
                )
            return normalized

        raise TypeError(
            f"Unsupported preset action type {type(actions).__name__} for value {value!r}"
        )

    def _normalize_cmd_actions(self, actions):
        """Flatten one _cmds action list into a validated sequence of (cmd, tmpl) tuples."""
        normalized = []
        for action in actions:
            if self._is_action_tuple(action):
                normalized.append(tuple(action))
            elif isinstance(action, (tuple, list)):
                for sub_action in action:
                    if not self._is_action_tuple(sub_action):
                        raise TypeError(
                            f"Malformed command action entry in _cmds: {sub_action!r}"
                        )
                    normalized.append(tuple(sub_action))
            else:
                raise TypeError(f"Malformed command action entry in _cmds: {action!r}")
        return normalized

    def _apply_presets(self, presets, sec, extra_kwargs=None, preset_key='Preset'):
        """
        Apply preset definitions from self.conf[sec] and append resulting actions
        to self._cmds[preset_key].

        Supported preset item formats
        -----------------------------
        Each preset entry must be:

            (key, vals, actions)

        with the following semantics:

        1. vals is None
           actions is one of:
             - a method name as str
             - one action tuple: (cmd, tmpl)
             - a sequence of action tuples / method names

        2. vals is not None
           actions is a list whose selected item is normalized like case 1.

        Matching for vals is case-insensitive.

        Parameters
        ----------
        presets : iterable
            Preset definitions.
        sec : str
            Section key in self.conf.
        extra_kwargs : dict | None
            Extra keyword arguments that should be bound into callable preset commands.
            Example: {'from_u': from_u, 'v_conv': v_conv}
        preset_key : str
            Key in self._cmds to which actions should be appended. Default: 'Preset'

        Returns
        -------
        int
            self.error
        """
        if extra_kwargs is None:
            extra_kwargs = {}

        if not hasattr(self, '_cmds'):
            self._cmds = {}

        self._cmds.setdefault(preset_key, [])

        for k, vals, actions in presets:
            try:
                v = self.conf[sec][k]
            except KeyError:
                continue

            # Case 1: no selection list, direct action
            if vals is None:
                bound_actions = self._normalize_preset_actions(actions, v, extra_kwargs=extra_kwargs)
                self._cmds[preset_key].extend(bound_actions)

            # Case 2: selection list
            else:
                v_cmp = str(v).lower()

                for idx, vi in enumerate(vals):
                    allowed = tuple(str(item).lower() for item in vi)
                    if v_cmp in allowed:
                        bound_actions = self._normalize_preset_actions(
                            actions[idx],
                            v,
                            extra_kwargs=extra_kwargs,
                        )
                        self._cmds[preset_key].extend(bound_actions)
                        break

        return self.error

    def _do_cmds(self, key, callerdict=None):
        send_opc = getattr(self, 'send_opc', False)
        dct = {}

        if callerdict is None:
            callerdict = {}

        if not hasattr(self, '_cmds'):
            return dct

        if key not in self._cmds:
            return dct

        for cmd, tmpl in self._normalize_cmd_actions(self._cmds[key]):
            # --- cmd rendern ---
            if callable(cmd):
                callargs = dict(callerdict or {})
                callargs.pop("self", None)
                callargs.pop("cls", None)
                expr = cmd(self, **callargs)
            else:
                expr = self._render_cmd(cmd, callerdict)

            # --- tmpl rendern (optional ebenfalls callable/templated) ---
            if callable(tmpl):
                tmplargs = dict(callerdict or {})
                tmplargs.pop("self", None)
                tmpl_rendered = tmpl(self, **tmplargs)
            else:
                tmpl_rendered = self._render_cmd(tmpl, callerdict) if isinstance(tmpl, str) else tmpl

            # nur schreiben / Aktion ausführen

            if not tmpl_rendered:
                try:
                    resolved = self._resolve_expr(expr, callerdict)
                except TypeError:
                    if ALLOW_LEGACY_EXEC and isinstance(expr, str):
                        try:
                            exec(expr, callerdict)
                            continue
                        except (SyntaxError, NameError, TypeError, AttributeError):
                            self.write(expr)
                            continue
                    raise
                kind = resolved[0]
                if kind == "write":
                    self.write(resolved[1])
                elif kind == "call":
                    _method, _args, _kwargs = resolved[1], resolved[2], resolved[3]
                    _method(*_args, **_kwargs)
                elif kind == "noop":
                    pass
                else:
                    raise RuntimeError(f"Unhandled expr resolution kind: {kind}")
            # nur lesen
            elif not cmd:
                ans = self.read(tmpl_rendered)
                if ans:
                    dct.update(ans)
            # schreiben + lesen
            else:
                resolved = self._resolve_expr(expr, callerdict)
                kind = resolved[0]
                if kind == "write":
                    ans = self.query(resolved[1], tmpl_rendered, send_opc=send_opc)
                    if ans:
                        dct.update(ans)
                elif kind == "call":
                    _method, _args, _kwargs = resolved[1], resolved[2], resolved[3]
                    _method(*_args, **_kwargs)
                    ans = self.read(tmpl_rendered)
                    if ans:
                        dct.update(ans)
                elif kind == "noop":
                    ans = self.read(tmpl_rendered)
                    if ans:
                        dct.update(ans)
                else:
                    raise RuntimeError(f"Unhandled expr resolution kind: {kind}")
        return dct

        #     # --- nur schreiben ---
        #     if not tmpl_rendered:
        #         # Legacy-Fall: expr kann noch ein Funktionsaufruf-String sein
        #         if isinstance(expr, str):
        #             try:
        #                 exec(expr, callerdict)
        #             except (SyntaxError, NameError, TypeError):
        #                 self.write(expr)
        #         else:
        #             # Falls cmd-callable absichtlich keinen String, sondern z.B. None zurückgibt
        #             pass
        #
        #     # --- nur lesen ---
        #     elif not cmd:
        #         ans = self.read(tmpl_rendered)
        #         if ans:
        #             dct.update(ans)
        #
        #     # --- schreiben + lesen ---
        #     else:
        #         ans = self.query(expr, tmpl_rendered, send_opc=send_opc)
        #         if ans:
        #             dct.update(ans)
        #
        # return dct

    # def _do_cmds(self, key, callerdict=None):
    #     send_opc = getattr(self, 'send_opc', False)  # look for send_opc; default to dont send
    #     dct = {}  # preset returned dictionary
    #     if not hasattr(self, '_cmds'):
    #         return dct  # if self._cmds is not defined we return a empty dict
    #     if key in self._cmds:  # in key is the name of the command to excecute, e.g. 'SetFreq'
    #         for cmd, tmpl in self._cmds[key]:  # loop all command, template pairs for key 'key'
    #             expr = self._render_cmd(cmd, callerdict)
    #             # tmpl is the mask for the string to read
    #             if not tmpl:  # no mask, no read
    #                 # expr may be a function call. Let's try..
    #                 try:
    #                     exec(expr, callerdict)
    #                 except (SyntaxError, NameError, TypeError):
    #                     self.write(expr)
    #             elif not cmd:  # only data read    no cmd, no write
    #                 dct.update(self.read(tmpl))
    #             else:  # both -> write and read
    #                 dct.update(self.query(expr, tmpl, send_opc=send_opc))
    #     return dct

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




@dataclass(frozen=True)
class MethodCall:
    """Structured method-call action used in command/preset definitions."""

    name: str
    args: tuple = ()
    kwargs: dict = field(default_factory=dict)



def test_do_cmds():
    """Run local integration checks for mixed legacy/new `_do_cmds` actions."""
    import re
    import io
    from mpylab.tools.configuration import strbool

    class FakeCommunication:
        """
        Sehr einfacher Simulator für write/read/query ohne Hardware.
        """

        def __init__(self):
            self.writes = []
            self.last_written = None

        def write(self, cmd):
            self.writes.append(cmd)
            self.last_written = cmd
            print(f"WRITE: {cmd}")
            return len(cmd)

        def read(self, tmpl=None):
            """
            Liefert abhängig vom zuletzt geschriebenen Befehl eine simulierte Antwort.
            """
            ans = "OK"

            if self.last_written == "FREQ?":
                ans = "FREQ 1000000000.0 HZ"
            elif self.last_written == "LEVEL?":
                ans = "LEVEL -10.0 DBM"
            elif self.last_written == "IDN?":
                ans = "FAKE,DRIVER,0001,1.0"
            elif self.last_written == "DEPTH?":
                ans = "DEPTH 80"
            elif self.last_written == "CALLABLE?":
                ans = "VALUE 42"
            elif self.last_written == "TEMPLATE?":
                ans = "VALUE 123"
            elif self.last_written == "READONLY":
                ans = "READBACK 77"
            else:
                ans = "OK"

            print(f"READ RAW: {ans}")

            if tmpl is None:
                return ans

            m = re.match(tmpl, ans)
            if m:
                return m.groupdict()
            return None

        def query(self, cmd, tmpl=None, send_opc=False):
            self.write(cmd)
            return self.read(tmpl)

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
            self.dev = None
            self.fake = FakeCommunication()
            self.write = self.fake.write
            self.read = self.fake.read
            self.query = self.fake.query
            self.channel = 1
            self.test_value = None

            self._cmds = {
                # neue {}-Syntax
                'SetFreqNew': [
                    ("FREQ {freq} HZ", None),
                ],

                # alte %-Mapping-Syntax
                'SetFreqOldMap': [
                    ("SENSe%(channel)d:FREQuency:CENTer %(cfreq)s HZ", None),
                ],

                # alte eval-Syntax
                'SetFreqOldEval': [
                    ("'FREQ %s HZ'%freq", None),
                ],

                # klassisches query mit Regex
                'GetFreq': [
                    ("FREQ?", r"FREQ (?P<freq>\S+) HZ"),
                ],

                # nur read
                'ReadOnly': [
                    ("READONLY", None),
                    ("", None),  # nur als Platzhalter, wird hier nicht genutzt
                ],

                # callable cmd
                'CallableCmd': [
                    (
                        lambda self, value, **kwargs: f"SET:VALUE {value:d}",
                        None
                    ),
                ],

                # callable cmd + readback
                'CallableCmdQuery': [
                    (
                        lambda self, **kwargs: "CALLABLE?",
                        r"VALUE (?P<value>\d+)"
                    ),
                ],

                # callable tmpl
                'CallableTemplate': [
                    (
                        "TEMPLATE?",
                        lambda self, **kwargs: r"VALUE (?P<value>\d+)"
                    ),
                ],

                # legacy exec-Pfad: Methodenaufruf als String
                'ExecPath': [
                    ("self._side_effect()", None),
                ],

                # Gemischt: write + query im neuen Stil
                'DepthRoundtrip': [
                    (
                        lambda self, depth, **kwargs: f"AM:DEPTH {int(depth * 100):d}",
                        None
                    ),
                    ("DEPTH?", r"DEPTH (?P<depth>\d+)"),
                ],

                'GetDescription': [
                    ("IDN?", r"(?P<IDN>.*)"),
                ],
            }

        @staticmethod
        def _render_cmd(cmd, callerdict=None):
            """
            Übergangs-Renderer:
            - %(name)s / %(name)d
            - {name}
            - alte eval-Syntax
            """
            if callerdict is None:
                callerdict = {}

            if cmd is None:
                return None

            if not isinstance(cmd, str):
                return cmd

            if "%(" in cmd:
                try:
                    return cmd % callerdict
                except (KeyError, TypeError, ValueError):
                    pass

            if "{" in cmd and "}" in cmd:
                try:
                    return cmd.format(**callerdict)
                except (KeyError, AttributeError, IndexError, ValueError):
                    pass

            if "%" in cmd and len(callerdict) == 1:
                try:
                    return cmd % next(iter(callerdict.values()))
                except (TypeError, ValueError):
                    pass

            try:
                expr = eval(cmd, callerdict)
                if expr is None:
                    return cmd
                return expr
            except (SyntaxError, NameError, TypeError, AttributeError, ValueError):
                return cmd

        def _do_cmds(self, key, callerdict=None):
            send_opc = getattr(self, 'send_opc', False)
            dct = {}

            if callerdict is None:
                callerdict = {}

            if not hasattr(self, '_cmds'):
                return dct

            if key not in self._cmds:
                return dct

            for cmd, tmpl in self._cmds[key]:
                if callable(cmd):
                    callargs = dict(callerdict or {})
                    callargs.pop("self", None)
                    callargs.pop("cls", None)
                    expr = cmd(self, **callargs)
                else:
                    expr = self._render_cmd(cmd, callerdict)

                if callable(tmpl):
                    tmplargs = dict(callerdict or {})
                    tmplargs.pop("self", None)
                    tmpl_rendered = tmpl(self, **tmplargs)
                else:
                    tmpl_rendered = self._render_cmd(tmpl, callerdict) if isinstance(tmpl, str) else tmpl

                if not tmpl_rendered:
                    if isinstance(expr, str) and expr:
                        try:
                            exec(expr, callerdict)
                        except (SyntaxError, NameError, TypeError):
                            self.write(expr)
                elif not cmd:
                    ans = self.read(tmpl_rendered)
                    if ans:
                        dct.update(ans)
                else:
                    ans = self.query(expr, tmpl_rendered, send_opc=send_opc)
                    if ans:
                        dct.update(ans)

            return dct

        def _side_effect(self):
            print("EXEC SIDE EFFECT CALLED")
            self.test_value = "side_effect_ok"

    print("=== DRIVER _do_cmds Test ===")
    drv = DummyDriver()

    print("\n--- 1. Neue {}-Syntax ---")
    drv._do_cmds('SetFreqNew', {'freq': 1e9})

    print("\n--- 2. Alte %-Mapping-Syntax ---")
    drv._do_cmds('SetFreqOldMap', {'channel': 2, 'cfreq': 2.45e9})

    print("\n--- 3. Alte eval-Syntax ---")
    drv._do_cmds('SetFreqOldEval', {'freq': 915e6})

    print("\n--- 4. Query mit Regex ---")
    dct = drv._do_cmds('GetFreq', {})
    print("RESULT:", dct)

    print("\n--- 5. Callable als cmd ---")
    drv._do_cmds('CallableCmd', {'value': 7})

    print("\n--- 6. Callable als cmd + query ---")
    dct = drv._do_cmds('CallableCmdQuery', {})
    print("RESULT:", dct)

    print("\n--- 7. Callable als tmpl ---")
    dct = drv._do_cmds('CallableTemplate', {})
    print("RESULT:", dct)

    print("\n--- 8. Legacy exec-Pfad ---")
    drv._do_cmds('ExecPath', {'self': drv})
    print("test_value:", drv.test_value)

    print("\n--- 9. Callable + Folge-Query ---")
    dct = drv._do_cmds('DepthRoundtrip', {'depth': 0.8})
    print("RESULT:", dct)

    print("\n--- 10. GetDescription ---")
    dct = drv._do_cmds('GetDescription', {})
    print("RESULT:", dct)

    print("\n--- 11. Zusammenfassung gesendeter Befehle ---")
    for i, cmd in enumerate(drv.fake.writes, start=1):
        print(f"{i:02d}: {cmd}")

    print("\n=== Test beendet ===")

def test_dummy_driver():
    """Run a text-level smoke test for base DRIVER initialization flow."""
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

def test_hybrid():
    """Verify `_do_cmds` behavior for hybrid template/callable command styles."""
    import re

    class FakeCommunication:
        def __init__(self):
            self.last = None
            self.writes = []

        def write(self, cmd, *args, **kwargs):
            self.last = cmd
            self.writes.append(cmd)
            print("WRITE:", cmd)
            return len(cmd)

        def read(self, tmpl=None, *args, **kwargs):
            ans = "OK"

            if self.last == "FREQ?":
                ans = "FREQ 1000000000.0 HZ"
            elif self.last == "DEPTH?":
                ans = "DEPTH 80"
            elif self.last == "CALLABLE?":
                ans = "VALUE 42"
            elif self.last == "IDN?":
                ans = "DUMMY,TEST,0001,1.0"

            print("READ:", ans)

            if tmpl is None:
                return ans

            m = re.match(tmpl, ans)
            if m:
                return m.groupdict()
            return None

        def query(self, cmd, tmpl=None, *args, **kwargs):
            self.write(cmd)
            return self.read(tmpl)

    drv = DRIVER()

    fake = FakeCommunication()
    drv.write = fake.write
    drv.read = fake.read
    drv.query = fake.query

    drv._cmds = {
        'HybridTest': [
            ("FREQ {freq} HZ", None),
            ("SENSe%(channel)d:FREQ %(freq)s", None),
            ("'FREQ %s HZ'%freq", None),
            (
                lambda self, depth, **kwargs:
                    f"AM:DEPTH {int(depth * 100):d}",
                None
            ),
            ("FREQ?", r"FREQ (?P<freq>\S+) HZ"),
            (
                "DEPTH?",
                lambda self, **kwargs: r"DEPTH (?P<depth>\d+)"
            ),
            (
                lambda self, **kwargs: "CALLABLE?",
                r"VALUE (?P<value>\d+)"
            ),
            ("IDN?", r"(?P<IDN>.*)")
        ],
        'ExecOnly': [
            ("self._test_exec()", None),
        ]
    }

    def _test_exec():
        print("EXEC CALLED")
        drv.exec_called = True

    drv._test_exec = _test_exec
    drv.exec_called = False

    result = drv._do_cmds(
        'HybridTest',
        {
            'freq': 1e9,
            'channel': 2,
            'depth': 0.8,
        }
    )

    print("RESULT:", result)
    print("WRITES:", fake.writes)

    assert result["freq"] == "1000000000.0"
    assert result["depth"] == "80"
    assert result["value"] == "42"
    assert result["IDN"] == "DUMMY,TEST,0001,1.0"

    assert "FREQ 1000000000.0 HZ" in fake.writes
    assert "SENSe2:FREQ 1000000000.0" in fake.writes
    assert "AM:DEPTH 80" in fake.writes
    assert "FREQ?" in fake.writes
    assert "DEPTH?" in fake.writes
    assert "CALLABLE?" in fake.writes
    assert "IDN?" in fake.writes

    drv._do_cmds(
        'ExecOnly',
        {
            'self': drv
        }
    )

    assert drv.exec_called is True

    print("EXEC FLAG:", drv.exec_called)
    print("test_hybrid passed")

def test_presets_hybrid():
    """Verify legacy-style preset expansion and command rendering behavior."""
    class FakeCommunication:
        def __init__(self):
            self.writes = []

        def write(self, cmd, *args, **kwargs):
            self.writes.append(cmd)
            print("WRITE:", cmd)
            return len(cmd)

        def read(self, tmpl=None, *args, **kwargs):
            return "OK" if tmpl is None else None

        def query(self, cmd, tmpl=None, *args, **kwargs):
            self.write(cmd)
            return self.read(tmpl)

    class FakeConvert:
        def c2c(self, fromunit, tounit, value):
            # bewusst einfache, deterministische Testkonvertierung
            # so sieht man leicht, ob der richtige Wert verwendet wurde
            return float(value) + 1.0

    drv = DRIVER()

    fake = FakeCommunication()
    drv.write = fake.write
    drv.read = fake.read
    drv.query = fake.query
    drv.convert = FakeConvert()

    drv.levelunit = "dBm"
    drv._internal_unit = "dBm"

    sec = "channel_1"
    drv.conf = {
        sec: {
            "attmode": "auto",
            "level": 5.0,
            "outputstate": "on",
            # "missingkey" absichtlich nicht vorhanden
        }
    }

    drv._cmds = {"Preset": []}

    presets = [
        (
            "attmode",
            [("0", "auto"), ("1", "fixed")],
            [
                (":OUTPUT:AMOD AUTO", None),
                (":OUTPUT:AMOD FIXED", None),
            ]
        ),
        (
            "level",
            None,
            (
                lambda self, v, **kwargs:
                    f":LEVEL {self.convert.c2c(self.levelunit, self._internal_unit, float(v)):f}",
                None
            )
        ),
        (
            "outputstate",
            [("1", "on")],
            [
                (":OUTPUT:STATE ON", None),
            ]
        ),
        (
            "missingkey",
            None,
            (
                lambda self, v, **kwargs: f":MISSING {v}",
                None
            )
        ),
    ]

    for k, vals, actions in presets:
        try:
            v = drv.conf[sec][k]

            if vals is None:
                cmd, tmpl = actions

                if callable(cmd):
                    drv._cmds["Preset"].append(
                        (
                            lambda _self, _cmd=cmd, _v=v, **kwargs:
                                _cmd(_self, v=_v, **kwargs),
                            tmpl
                        )
                    )
                else:
                    drv._cmds["Preset"].append((cmd, tmpl))

            else:
                v_cmp = str(v).lower()
                for idx, vi in enumerate(vals):
                    if v_cmp in vi:
                        drv._cmds["Preset"].append(actions[idx])

        except KeyError:
            pass

    result = drv._do_cmds("Preset", {"self": drv})

    print("RESULT:", result)
    print("WRITES:", fake.writes)

    # Es wird nichts gelesen, daher leeres Dict erwartet
    assert result == {}

    # Auswahl-Preset
    assert ":OUTPUT:AMOD AUTO" in fake.writes

    # Berechnetes Preset: 5.0 -> FakeConvert -> 6.0
    assert ":LEVEL 6.000000" in fake.writes

    # Weiterer Auswahlfall
    assert ":OUTPUT:STATE ON" in fake.writes

    # Fehlender Key darf nichts erzeugen
    assert not any(cmd.startswith(":MISSING") for cmd in fake.writes)

    # Genau diese drei Kommandos sollten geschrieben worden sein
    assert len(fake.writes) == 3

    print("test_presets_hybrid passed")

def test_apply_presets_sequences_and_method_calls():
    """Verify sequence presets and string-method-call preset actions."""
    class FakeCommunication:
        def __init__(self):
            self.writes = []

        def write(self, cmd, *args, **kwargs):
            self.writes.append(cmd)
            return len(cmd)

        def read(self, tmpl=None, *args, **kwargs):
            return None

        def query(self, cmd, tmpl=None, *args, **kwargs):
            self.write(cmd)
            return None

    class TestDriver(DRIVER):
        def __init__(self):
            super().__init__()
            self._cmds = {"Preset": []}
            self.mode_calls = []

        def SetMode(self, value):
            self.mode_calls.append(value)
            return 0, value

    drv = TestDriver()
    fake = FakeCommunication()
    drv.write = fake.write
    drv.read = fake.read
    drv.query = fake.query

    sec = "channel_1"
    drv.conf = {
        sec: {
            "mode": "SAFE",
            "startup": "on",
            "shape": "log",
        }
    }

    presets = [
        ("mode", None, "SetMode"),
        (
            "startup",
            None,
            [
                (":OUTP OFF", None),
                (":INIT:CONT OFF", None),
            ],
        ),
        (
            "shape",
            [("lin",), ("log",)],
            [
                [(":SWE:TYPE LIN", None)],
                [(":SWE:TYPE LOG", None), (":DISP:TRACE ON", None)],
            ],
        ),
    ]

    drv._apply_presets(presets, sec)
    result = drv._do_cmds("Preset", {"self": drv})

    assert result == {}
    assert drv.mode_calls == ["SAFE"]
    assert fake.writes == [
        ":OUTP OFF",
        ":INIT:CONT OFF",
        ":SWE:TYPE LOG",
        ":DISP:TRACE ON",
    ]

    drv._cmds["Nested"] = [
        [
            (":A", None),
            (":B", None),
        ]
    ]
    drv._do_cmds("Nested", {"self": drv})
    assert fake.writes[-2:] == [":A", ":B"]

    print("test_apply_presets_sequences_and_method_calls passed")

def test_apply_presets_equivalence():
    """Check equivalence between legacy and normalized preset application paths."""
    class FakeCommunication:
        def __init__(self):
            self.writes = []

        def write(self, cmd, *args, **kwargs):
            self.writes.append(cmd)
            return len(cmd)

        def read(self, tmpl=None, *args, **kwargs):
            return "OK" if tmpl is None else None

        def query(self, cmd, tmpl=None, *args, **kwargs):
            self.write(cmd)
            return self.read(tmpl)

    class FakeConvert:
        def c2c(self, fromunit, tounit, value):
            return float(value) + 1.0

    class TestDriver(DRIVER):
        def __init__(self):
            super().__init__()
            self.convert = FakeConvert()
            self.levelunit = "dBm"
            self._internal_unit = "dBm"
            self._cmds = {"Preset": []}

        @staticmethod
        def _render_cmd(cmd, callerdict=None):
            if callerdict is None:
                callerdict = {}

            if cmd is None:
                return None

            if not isinstance(cmd, str):
                return cmd

            if "%(" in cmd:
                try:
                    return cmd % callerdict
                except (KeyError, TypeError, ValueError):
                    pass

            if "{" in cmd and "}" in cmd:
                try:
                    return cmd.format(**callerdict)
                except (KeyError, AttributeError, IndexError, ValueError):
                    pass

            if "%" in cmd and len(callerdict) == 1:
                try:
                    return cmd % next(iter(callerdict.values()))
                except (TypeError, ValueError):
                    pass

            try:
                expr = eval(cmd, callerdict)
                if expr is None:
                    return cmd
                return expr
            except (SyntaxError, NameError, TypeError, AttributeError, ValueError):
                return cmd

        def _do_cmds(self, key, callerdict=None):
            dct = {}

            if callerdict is None:
                callerdict = {}

            if key not in self._cmds:
                return dct

            for cmd, tmpl in self._cmds[key]:
                if callable(cmd):
                    callargs = dict(callerdict)
                    callargs.pop("self", None)
                    expr = cmd(self, **callargs)
                else:
                    expr = self._render_cmd(cmd, callerdict)

                if callable(tmpl):
                    tmplargs = dict(callerdict)
                    tmplargs.pop("self", None)
                    tmpl_rendered = tmpl(self, **tmplargs)
                else:
                    tmpl_rendered = self._render_cmd(tmpl, callerdict) if isinstance(tmpl, str) else tmpl

                if not tmpl_rendered:
                    self.write(expr)
                elif not cmd:
                    ans = self.read(tmpl_rendered)
                    if ans:
                        dct.update(ans)
                else:
                    ans = self.query(expr, tmpl_rendered)
                    if ans:
                        dct.update(ans)

            return dct

    def apply_presets_old_style(drv, presets, sec):
        for k, vals, actions in presets:
            try:
                v = drv.conf[sec][k]

                if vals is None:
                    drv._cmds['Preset'].append(
                        (
                            eval(
                                actions[0],
                                {},
                                {
                                    "self": drv,
                                    "v": v,
                                    "float": float,
                                    "int": int,
                                    "min": min,
                                    "max": max,
                                },
                            ),
                            actions[1],
                        )
                    )
                else:
                    for idx, vi in enumerate(vals):
                        if str(v).lower() in tuple(str(item).lower() for item in vi):
                            drv._cmds['Preset'].append(actions[idx])
                            break
            except KeyError:
                pass

    sec = "channel_1"

    presets = [
        (
            'attmode',
            [('0', 'auto'), ('1', 'fixed')],
            [
                (':SPECIAL_FUNCTION 3', None),
                (':SPECIAL_FUNCTION 4', None)
            ]
        ),
        (
            'attenuation',
            None,
            (
                "'':SPECIAL_FUNCTION 23,%f''%self.convert.c2c(self.levelunit, self._internal_unit, float(v))",
                None
            )
        ),
        (
            'level',
            None,
            (
                "'':RF_LEVEL:INTERNAL %f DBM''%self.convert.c2c(self.levelunit, self._internal_unit, float(v))",
                None
            )
        ),
        (
            'outputstate',
            [('1', 'on')],
            [
                (':RF_POWER ON', None)
            ]
        )
    ]

    # Strings für eval korrekt setzen
    presets = [
        (
            'attmode',
            [('0', 'auto'), ('1', 'fixed')],
            [
                (':SPECIAL_FUNCTION 3', None),
                (':SPECIAL_FUNCTION 4', None)
            ]
        ),
        (
            'attenuation',
            None,
            (
                "':SPECIAL_FUNCTION 23,%f'%self.convert.c2c(self.levelunit, self._internal_unit, float(v))",
                None
            )
        ),
        (
            'level',
            None,
            (
                "':RF_LEVEL:INTERNAL %f DBM'%self.convert.c2c(self.levelunit, self._internal_unit, float(v))",
                None
            )
        ),
        (
            'outputstate',
            [('1', 'on')],
            [
                (':RF_POWER ON', None)
            ]
        )
    ]

    old_drv = TestDriver()
    new_drv = TestDriver()

    old_fake = FakeCommunication()
    new_fake = FakeCommunication()

    old_drv.write = old_fake.write
    old_drv.read = old_fake.read
    old_drv.query = old_fake.query

    new_drv.write = new_fake.write
    new_drv.read = new_fake.read
    new_drv.query = new_fake.query

    old_drv.conf = {
        sec: {
            "attmode": "auto",
            "attenuation": 5.0,
            "level": -10.0,
            "outputstate": "on",
        }
    }

    new_drv.conf = {
        sec: {
            "attmode": "auto",
            "attenuation": 5.0,
            "level": -10.0,
            "outputstate": "on",
        }
    }

    # Alte Variante
    apply_presets_old_style(old_drv, presets, sec)
    old_drv._do_cmds("Preset", {"self": old_drv})

    # Neue Variante
    new_presets = [
        (
            'attmode',
            [('0', 'auto'), ('1', 'fixed')],
            [
                (':SPECIAL_FUNCTION 3', None),
                (':SPECIAL_FUNCTION 4', None)
            ]
        ),
        (
            'attenuation',
            None,
            (
                lambda self, v, **kwargs:
                    f":SPECIAL_FUNCTION 23,{self.convert.c2c(self.levelunit, self._internal_unit, float(v)):f}",
                None
            )
        ),
        (
            'level',
            None,
            (
                lambda self, v, **kwargs:
                    f":RF_LEVEL:INTERNAL {self.convert.c2c(self.levelunit, self._internal_unit, float(v)):f} DBM",
                None
            )
        ),
        (
            'outputstate',
            [('1', 'on')],
            [
                (':RF_POWER ON', None)
            ]
        )
    ]

    new_drv._apply_presets(new_presets, sec)
    new_drv._do_cmds("Preset", {"self": new_drv})

    print("OLD WRITES:", old_fake.writes)
    print("NEW WRITES:", new_fake.writes)

    assert old_fake.writes == new_fake.writes
    print("test_apply_presets_equivalence passed")

if __name__ == "__main__":
    test_do_cmds()
    test_dummy_driver()
    test_hybrid()
    test_presets_hybrid()
    test_apply_presets_equivalence()
