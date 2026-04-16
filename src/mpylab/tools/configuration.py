# -*- coding: utf-8 -*-
"""
This is :mod:`mpylab.tools.configuration`.

   Provides the Configuration class; used for ini files

   :author: Hans Georg Krauthäuser (main author)

   :license: GPLv3 or higher
"""


import os
import configparser
from typing import TextIO
import ast
import io
import textwrap

from mpylab.tools.compare import fstrcmp
from mpylab.tools.regular_expressions import _INLINE_FILE_RE, _INLINE_FILE_BLOCK_RE

def parse_ini_value(value, inline_files=None):
    """
    Parse a value from an ini file without using eval().

    Supported:
    - plain strings
    - ints, floats, bools, None
    - tuples, lists, dicts via ast.literal_eval
    - embedded inline data files via placeholders
    """
    if value is None:
        return None

    if not isinstance(value, str):
        return value

    text = value.strip()
    if text == "":
        return ""

    if inline_files is not None and text in inline_files:
        return inline_files[text]

    try:
        return ast.literal_eval(text)
    except (ValueError, SyntaxError):
        pass

    return text


def strbool(s) -> bool:
    """
    Returns *True* if *int(s)* is *True* or *False* otherwise. '0' -> False; '1' -> True
    """
    if isinstance(s, bool):
        return s
    if isinstance(s, int):
        return bool(s)
    if isinstance(s, str):
        text = s.strip().lower()
        if text in ("1", "true", "yes", "on"):
            return True
        if text in ("0", "false", "no", "off"):
            return False
    return bool(int(s))


def preprocess_ini_text(text):
    """
    Replace embedded inline-file Python expressions with placeholders so that
    configparser can parse the ini text.

    Returns:
        processed_text, inline_files
    """
    inline_files = {}
    counter = 0

    def repl(match):
        nonlocal counter
        raw_block = match.group(2)

        try:
            from mpylab.tools.util import format_block
            normalized = format_block(raw_block)
        except Exception:
            normalized = textwrap.dedent(raw_block).strip()

        placeholder = f"__INLINE_FILE_{counter}__"
        inline_files[placeholder] = io.StringIO(normalized)
        counter += 1
        return placeholder

    processed_text = _INLINE_FILE_BLOCK_RE.sub(repl, text)
    return processed_text, inline_files



class Configuration:
    """
    Class for all configuration files.
    """

    def __init__(self, ini: str | TextIO, cnftmpl: dict, casesensitive: bool = False) -> None:
        """
        Constructor

        Parameters:
          - ini: name of the config file or file-like object
          - cnftmpl: dict; configuration template
          - casesensitive: bool; match case-sensitive or not; default: False
        """
        self.cnftmpl = cnftmpl
        self.conf = {}
        self.casesensitive = casesensitive
        self._inline_files = {}

        fp = None
        must_close = False

        try:
            fp = open(os.path.normpath(ini), 'r', encoding='utf-8')
            must_close = True
        except (OSError, TypeError):
            fp = ini

        try:
            raw_text = fp.read()
        finally:
            if must_close and fp is not None:
                fp.close()

        processed_text, self._inline_files = preprocess_ini_text(raw_text)

        config = configparser.ConfigParser()
        config.read_file(io.StringIO(processed_text))

        self.sections_in_ini = config.sections()
        self.channel_list = []

        for sec in self.sections_in_ini:
            matches = fstrcmp(sec, list(self.cnftmpl.keys()), cutoff=0, ignorecase=True)
            if not matches:
                raise KeyError(f"No matching section template found for section '{sec}'")

            tmplsec = matches[0]
            thesec = tmplsec

            try:
                thechannel = int(sec.lower().split('channel_')[1])
                self.channel_list.append(thechannel)
                try:
                    thesec = tmplsec % thechannel
                except TypeError:
                    pass
            except (IndexError, ValueError):
                pass

            thesec_c = thesec if self.casesensitive else thesec.lower()
            self.conf[thesec_c] = {}

            for key, val in config.items(sec):
                key_matches = fstrcmp(
                    key,
                    list(self.cnftmpl[tmplsec].keys()),
                    cutoff=0,
                    ignorecase=True
                )
                if not key_matches:
                    raise KeyError(f"No matching key template found for key '{key}' in section '{sec}'")

                tmplkey = key_matches[0]
                tmplkey_c = tmplkey if self.casesensitive else tmplkey.lower()

                parsed_val = parse_ini_value(val, self._inline_files)
                self.conf[thesec_c][tmplkey_c] = self.cnftmpl[tmplsec][tmplkey](parsed_val)



if __name__ == "__main__":
    import io

    # Beispiel-INI (ähnlich deinem realen Format)
    ini_text = """
    [DESCRIPTION]
    description = 'Test Device'
    type = 'POWERMETER'
    vendor = 'TestCorp'
    serialnr = '12345'
    deviceid = 'XYZ'
    driver = 'test_driver'

    [INIT_VALUE]
    fstart = 100e6
    fstop = 200e6
    fstep = 1e6
    gpib = 18
    visa = 'GPIB0::18::INSTR'
    virtual = 1

    [CHANNEL_1]
    name = 'CH1'
    level = -10
    unit = 'dBm'
    leveloffset = 0
    levellimit = 10
    outputstate = 'ON'
    attmode = 'AUTO'
    attenuation = 5

    [CHANNEL_2]
    name = 'CH2'
    level = -20
    unit = 'dBm'
    leveloffset = 1
    levellimit = 12
    outputstate = 'OFF'
    attmode = 'FIXED'
    attenuation = 10

    [DATA]
    file = io.StringIO(format_block('''
        FUNIT: Hz
        UNIT: powerratio
        ABSERROR: [0.1, 1]
        10 [1, 0]
        20 [0.9, 40]
    '''))
    """

    ini = io.StringIO(ini_text)

    # Dein Template
    conftmpl = {
        'description': {
            'description': str,
            'type': str,
            'vendor': str,
            'serialnr': str,
            'deviceid': str,
            'driver': str
        },
        'init_value': {
            'fstart': float,
            'fstop': float,
            'fstep': float,
            'gpib': int,
            'visa': str,
            'virtual': strbool
        },
        'channel_%d': {
            'name': str,
            'level': float,
            'unit': str,
            'leveloffset': float,
            'levellimit': float,
            'outputstate': str,
            'attmode': str,
            'attenuation': float
        },
        'data': {
            'file': lambda x: x  # hier kommt das io.StringIO Objekt durch
        }
    }

    print("=== Configuration Test ===")

    cfg = Configuration(ini, conftmpl)

    print("\n--- Sections ---")
    for sec, content in cfg.conf.items():
        print(sec)

    print("\n--- Values ---")
    for sec, content in cfg.conf.items():
        print(f"\n[{sec}]")
        for k, v in content.items():
            print(f"  {k}: {v} (type={type(v).__name__})")

    print("\n--- Channel List ---")
    print(cfg.channel_list)

    print("\n--- Inline File Test ---")
    try:
        data_obj = cfg.conf['data']['file']
        if hasattr(data_obj, "read"):
            print("Inline file content:")
            print(data_obj.read())
        else:
            print("No inline file detected")
    except KeyError:
        print("No DATA section found")

    print("\n=== Test finished ===")