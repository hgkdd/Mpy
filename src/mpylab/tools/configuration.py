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

from mpylab.tools.levenshtein import fstrcmp


def strbool(s: str) -> bool:
    """
    Returns *True* if *int(s)* is *True* or *False* otherwise. '0' -> False; '1' -> True
    """
    return bool(int(s))


class Configuration:
    """
    Class for all configuration files.
    """
    def __init__(self, ini: str | TextIO, cnftmpl: dict, casesensitive: bool = False) -> None:
        """
        Constructor

        Parameter:
          - *ini*: name of the config file of file like object
          - *cnftmpl*: dict; configuration template
          - *casesensitive*: bool; match case sensitive or not; default: False
        """
        self.cnftmpl = cnftmpl
        self.conf = {}   # this holds the configuration, will be dict(dict(...))
        self.casesensitive = casesensitive
        fp = None

        try:
            # try to open file
            fp = open(os.path.normpath(ini), 'r')    # open file by its name
        except (IOError, FileNotFoundError, TypeError):
            # assume a file like object
            fp = ini   # file like object

        # read the whole ini file in to a dict
        config = configparser.ConfigParser()
        config.read_file(fp)
        # fp.close()

        self.sections_in_ini = config.sections()   # list of sections
        self.channel_list = []     # devices may have one or more channels
        # print(self.sections_in_ini)
        for sec in self.sections_in_ini:   # iterate sections
            # print(sec.strip("'"), sec)
            tmplsec = fstrcmp(sec, list(self.cnftmpl.keys()), cutoff=0, ignorecase=True)[0]   # take best match from fuzzy string compare; sec vs keys in cnftmpl
            thesec = tmplsec
            try:
                # print sec,'\n', tmplsec,'\n','\n'
                # print tmplsec.lower().split('channel_')
                # print repr(sec.lower().split('channel_')[1])
                thechannel = int(sec.lower().split('channel_')[1])   # try to get the channel number as int
                self.channel_list.append(thechannel)
                try:
                    thesec = tmplsec % thechannel   # tmplate is 'channel_%d'; modulo operator used to format
                except TypeError:
                    pass    # no %d ...
            except IndexError: # no channel number
                pass

            if self.casesensitive:
                thesec_c = thesec   # don't change case
            else:
                thesec_c = thesec.lower()    # convert to lower

            self.conf[thesec_c] = {}   # init dict for this section

            for key, val in config.items(sec):
                # print  key, val
                tmplkey = fstrcmp(key, list(self.cnftmpl[tmplsec].keys()), cutoff=0, ignorecase=True)[0]   # best fuzzy match
                # print self.cnftmpl[tmplsec].keys()
                if self.casesensitive:
                    tmplkey_c = tmplkey
                else:
                    tmplkey_c = tmplkey.lower()

                self.conf[thesec_c][tmplkey_c] = self.cnftmpl[tmplsec][tmplkey](val)
