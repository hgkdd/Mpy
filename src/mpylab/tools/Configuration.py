import os
import configparser
from mpylab.tools.levenshtein import fstrcmp as levfstrcmp

fstrcmp = levfstrcmp


def fstrcmp_old(word, possibilities, n=None, cutoff=None, ignorecase=True):
    """
    Performs a fuzzy string comparision of *word* agains the strings in the list *possibilities*.

    The function uses difflib.get_close_matches vor the scoring. This works best if the stings in *possibilities* are of same length.
    Therefore, the strings in *possibilities* are padded to the left with '#' before calling get_close_mathes.
    The function returns a list with the best *n* matches with dcreasind scorings (best match first). If *ignorecase* is *True*
    *word* and *possibilities* are casted to lowercase before scoring. 

    The elements of the returned list are allway members of *possibilities*. 
    """
    import difflib as dl
    longest = max(list(map(len, possibilities)))
    if n is None:
        n = 3  # difflibs default
    if cutoff is None:
        cutoff = 0.0  # don't sort out not-so-good matches
    if ignorecase:
        word = word.lower()
        possdict = dict(list(zip([p.lower().ljust(longest, '#') for p in possibilities], possibilities)))
    else:
        possdict = dict(list(zip([p.ljust(longest, '#') for p in possibilities], possibilities)))
    # print possdict

    matches = dl.get_close_matches(word, list(possdict.keys()), n=n, cutoff=cutoff)
    return [possdict[m] for m in matches]


def strbool(s):
    return bool(int(s))


class Configuration(object):
    def __init__(self, ininame, cnftmpl, casesensitive=False):
        self.cnftmpl = cnftmpl
        self.conf = {}
        self.casesensitive = casesensitive
        fp = None

        try:
            # try to open file
            fp = open(os.path.normpath(ininame), 'r')
        except (IOError, FileNotFoundError, TypeError):
            # assume a file like object
            fp = ininame

        # read the whole ini file in to a dict
        config = configparser.ConfigParser()
        config.read_file(fp)
        # fp.close()

        self.sections_in_ini = config.sections()
        self.channel_list = []
        # print(self.sections_in_ini)
        for sec in self.sections_in_ini:
            # print(sec.strip("'"), sec)
            tmplsec = fstrcmp(sec, list(self.cnftmpl.keys()), n=1, cutoff=0, ignorecase=True)[0]
            thesec = tmplsec
            try:
                # print sec,'\n', tmplsec,'\n','\n'
                # print tmplsec.lower().split('channel_')
                # print repr(sec.lower().split('channel_')[1])
                thechannel = int(sec.lower().split('channel_')[1])
                self.channel_list.append(thechannel)
                try:
                    thesec = tmplsec % thechannel
                except TypeError:
                    pass
            except IndexError:
                pass

            if self.casesensitive:
                thesec_c = thesec
            else:
                thesec_c = thesec.lower()

            self.conf[thesec_c] = {}

            for key, val in config.items(sec):
                # print  key, val
                tmplkey = fstrcmp(key, list(self.cnftmpl[tmplsec].keys()), n=1, cutoff=0, ignorecase=True)[0]
                # print self.cnftmpl[tmplsec].keys()
                if self.casesensitive:
                    tmplkey_c = tmplkey

                else:
                    tmplkey_c = tmplkey.lower()

                self.conf[thesec_c][tmplkey_c] = self.cnftmpl[tmplsec][tmplkey](val)
