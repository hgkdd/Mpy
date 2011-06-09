import os

from scuq.quantities import Quantity
from scuq.si import WATT

from mpy.tools.mgraph import Leveler

SearchPaths=['\\MpyConfig\\LargeRC', '.']
dotfile = 'mvk-immunity.dot'

#print dotfile

soll=Quantity(WATT, 1.0)

cdict = {"autosave_filename": 'msc-autosave.p',
         "pickle_output_filename": 'msc-maincal.p',
         "pickle_input_filename": 'AfterMeasure.p',
         "rawdata_output_filename": 'out_raw_maincal-%s.dat',
         "processeddata_output_filename": 'out_processed_maincal-%s.dat',
         "log_filename": 'msc.log',
         "logger": ['stdLogger'],
         "minimal_autosave_interval": 60,
         "descriptions": ['empty', 'loaded'],
         "measure_parameters": [{'dotfile': dotfile,
                                 'SearchPaths': SearchPaths,
                                 'delay': 1,
                                 'LUF': 250e6,
                                 'FStart': 2e9,
                                 'FStop': 3e9,
                                 'InputLevel': soll,
                                 'leveler': None,
                                 'leveler_par': None,
                                 'ftab': [1,3,6,10,100,1000],
                                 'nftab': [20,15,10,20,20],
                                 'ntuntab': [[3,3,3,3,3]],
                                 'tofftab': [[7,14,28,28,28]],
                                 'nprbpostab': [2,2,2,2,2],
                                 'nrefantpostab': [2,2,2,2,2],
                                 'names': {'sg': 'Sg',
                                           'a1': 'Amp_Input',
                                           'a2': 'Amp_Output',
                                           'ant': 'TxAnt',
                                           'pmfwd': 'Pm1',
                                           'pmbwd': 'Pm2',
                                           'fp': ['Fprobe'], 
                                           'tuner': ['Tuner'],
                                           'refant': ['RxAnt'],
                                           'pmref': ['Pm']
                                           }
                                }]
        }
