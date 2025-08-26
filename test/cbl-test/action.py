from mpylab.tools.util import get_var_from_nearest_outerframe

def do (fstr, flim):
    '''Switch the relais'''
    f = get_var_from_nearest_outerframe(fstr)
    if f <= flim:
        print("Switch to pos 1")
    else:
        print("Switch to pos 2")

    return 0

