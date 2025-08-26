import sys
sys.path.insert(0,'..')

from mpylab.env import Measure

class SomeMeasureClass(Measure.Measure):
    def __init__(self):
        super(SomeMeasureClass, self).__init__()

    def __setstate__(self, dct):
        super(SomeMeasureClass, self).__setstate__(dct)

    def __getstate__(self):
        odict = super(SomeMeasureClass, self).__getstate__()
        return odict

    def do_something(self):
        self.do_autosave()
