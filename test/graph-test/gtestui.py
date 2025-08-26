from traits.api import *
# from enthought.traits.ui.api import *
import wx
import scipy
from scuq import *
from mpylab.tools.mgraph import MGraph


class Measurement(HasTraits):
    dot = String('test.dot')


Measurement().edit_traits()
wx.PySimpleApp().MainLoop()

# dot='test.dot'
# mg=MGraph(dot)

# instrumentation=mg.CreateDevices()
# for k,v in instrumentation.items():
#     globals()[k]=v  # create devices in current namespace

# mg.Init_Devices()  # init all devices in graph

# try:
#     amp.POn()
#     amp.Operate()

#     mg.RFOn_Devices()
#     lv=quantities.Quantity(si.WATT, 1e-4)

#     pwrmeters=('pm_fwd','pm_bwd')
#     for f in scipy.arange(10e6,1e9,10e6):
#         print "Freq:", f,
#         mg.SetFreq_Devices(f)
#         mg.EvaluateConditions()
#         sg.SetLevel(lv)
#         results=mg.Read(pwrmeters)
#         #print results
#         for p in pwrmeters:
#             print p, results[p],
#         print

# finally:    
#     mg.RFOff_Devices()
#     mg.Quit_Devices()
