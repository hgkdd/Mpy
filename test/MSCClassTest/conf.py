import os

SearchPaths=['\\MpyConfig\\LargeRC', '.']
dotfile = 'mvk-immunity.dot'

#print dotfile

cdict = {"autosave_filename": 'msc-autosave.p',
         "pickle_output_filename": 'msc-maincal.p',
         "pickle_input_filename": None,
         "rawdata_output_filename": 'out_raw_maincal-%s.dat',
         "processeddata_output_filename": 'out_processed_maincal.dat',
         "log_filename": 'msc.log',
         "logger": ['stdlogger'],
         "minimal_autosave_interval": 3600,
         "descriptions": ['empty', 'loaded'],
         "measure_parameters": [{'dotfile': dotfile,
                                 'SearchPaths': SearchPaths,
                                 'delay': 1,
                                 'FStart': 200e6,
                                 'FStop': 300e6,
                                 'SGLevel': -20,
                                 'leveling': None,
                                 'ftab': [3,6,10,100,1000],
                                 'nftab': [20,15,10,20,20],
                                 'ntuntab': [[50,18,12,12,12]],
                                 'tofftab': [[7,14,28,28,28]],
                                 'nprbpostab': [8,8,8,8,8],
                                 'nrefantpostab': [8,8,8,8,8],
                                 'names': {'sg': 'Sg',
                                           'a1': 'Amp_Input',
                                           'a2': 'Amp_Output',
                                           'ant': 'TxAnt',
                                           'pmfwd': 'Pm1',
                                           'pmbwd': 'Pm2',
                                           'fp': ['FProbe'], 
                                           'tuner': ['Tuner'],
                                           'refant': ['RxAnt'],
                                           'pmref': ['Pm']
                                           }
                                }]
        }
