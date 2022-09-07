# -*- coding: utf-8 -*-

# import sys
# sys.path.insert(0,'..')
from mpy.device import sg_rs_smr

ini='smr.ini'

sg=sg_rs_smr.SMR()
sg.Init(ini)
