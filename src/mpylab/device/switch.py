# -*- coding: iso-8859-1 -*-
from mpylab.tools.util import get_var_from_nearest_outerframe, isiterable


def switch(swstr=None, fstr=None, fs=None):
    """
    Switch the relais.
    swstr: a string refering to the instance of the switch device, e.g. 'self.sw'
    fstr: a string with the name of the variable to look for (frequency), e.g. 'f'
    fs: upper limit for switch states, e.g. fs=1e9 -> f=900MHz->state=0; f=1.1e9->state=1
    """
    f = get_var_from_nearest_outerframe(fstr)
    sw = get_var_from_nearest_outerframe(swstr)
    print(("In switch: f = %s, fs = %s, sw = %s" % (str(f), str(fs), str(sw))))
    if None in (f, sw, fs):
        return -1

    if not isiterable(fs):
        fs = (fs,)
    for swstate, fi in enumerate(fs):
        if f > fi:
            break

    err = sw.switch_to(swstate)
    return err
