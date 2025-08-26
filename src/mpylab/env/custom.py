# -*- coding: utf-8 -*-
from mpylab.tools.util import get_var_from_nearest_outerframe


def my_switch(swstr, fstr, fs=1e9):
    """Function to switch a switch *swstr* depending from the value of the
       variable *fstr* with respect to *fs*. 
    """
    f = get_var_from_nearest_outerframe(fstr)
    sw = get_var_from_nearest_outerframe(swstr)
    # print("In custom.my_switch: f = %s, fs = %s, sw = %s"%(str(f),str(fs),str(sw)))
    if f is None or sw is None:
        return -1

    err = 0
    if f <= fs:
        to_ch = 1
    else:
        to_ch = 2
    err, is_ch, val = sw.GetSWState()
    if err or is_ch != to_ch:
        # print("going to switch to ch %d"%to_ch)
        err, is_ch = sw.SwitchTo(to_ch)
    else:
        # print("do not switch")
        pass
    return err
