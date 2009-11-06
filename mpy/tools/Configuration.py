import os
import ConfigParser

def fstrcmp(word, possibilities, n=None, cutoff=None, ignorecase=True):
    """
    Performs a fuzzy string comparision of *word* agains the strings in the list *possibilities*.

    The function uses difflib.get_close_matches vor the scoring. This works best if the stings in *possibilities* are of same length.
    Therefore, the strings in *possibilities* are padded to the left with '#' before calling get_close_mathes.
    The function returns a list with the best *n* matches with dcreasind scorings (best match first). If *ignorecase* is *True*
    *word* and *possibilities* are casted to lowercase before scoring. 

    The elements of the returned list are allway members of *possibilities*. 
    """
    import difflib as dl
    longest=max(map(len,possibilities))
    if n is None:
        n=3  # difflibs default
    if cutoff is None:
        cutoff=0.0 # don't sort out not-so-good matches
    if ignorecase:
        word=word.lower()
        possdict=dict(zip([p.lower().ljust(longest,'#') for p in possibilities],possibilities))
    else:
        possdict=dict(zip([p.ljust(longest,'#') for p in possibilities],possibilities))
        
    matches=dl.get_close_matches(word,possdict.keys(),n=n,cutoff=cutoff)
    return [possdict[m] for m in matches]

    
def strbool(s):
    return bool(int(s))

class Configuration(object):
    def __init__(self, ininame, cnftmpl):
        self.cnftmpl=cnftmpl
        self.conf={}
        fp=None
        try:
            # try to open file
            fp=file(os.path.normpath(ininame),'r')
        except:
            # assume a file like object
            fp=ininame
        
        # read the whole ini file in to a dict
        config=ConfigParser.SafeConfigParser()
        config.readfp(fp)
        fp.close()
        
        self.sections_in_ini=config.sections()
        self.channel_list=[]
        for sec in self.sections_in_ini:
            #print sec
            tmplsec=fstrcmp(sec, self.cnftmpl.keys(),n=1,cutoff=0,ignorecase=True)[0]
            thesec=tmplsec
            try:
                #print sec, tmplsec
                #print tmplsec.lower().split('channel_')
                #print repr(sec.lower().split('channel_')[1])
                thechannel=int(sec.lower().split('channel_')[1])
                self.channel_list.append(thechannel)
                try:
                    thesec=tmplsec%thechannel
                except TypeError:
                    pass
            except IndexError:
                pass
            self.conf[thesec.lower()]={}
            for key,val in config.items(sec):
                #print key, val
                tmplkey=fstrcmp(key, self.cnftmpl[tmplsec].keys(),n=1,cutoff=0,ignorecase=True)[0]
                self.conf[thesec.lower()][tmplkey.lower()]=self.cnftmpl[tmplsec][tmplkey](val)
            
