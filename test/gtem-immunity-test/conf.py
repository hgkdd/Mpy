from scuq.quantities import Quantity
from scuq.si import WATT

SearchPaths = ['C:\\Users\\hgkrauth\\Documents\\Development\\git\\MpyConfig\\LargeGTEM', '.']
dotfile = 'gtem-immunity.dot'

# print dotfile

soll = Quantity(WATT, 1.0)

cdict = {"autosave_filename": 'gtem-autosave.p',
         "pickle_output_filename": 'gtem-immunity.p',
         "pickle_input_filename": None,
         "rawdata_output_filename": 'out_raw_immunity-%s.dat',
         "processeddata_output_filename": 'out_processed_immunity-%s.dat',
         "log_filename": 'gtem.log',
         "logger": ['stdlogger'],
         "minimal_autosave_interval": 600,
         "descriptions": ['eut'],
         "measure_parameters": [{'dotfile': dotfile,
                                 'SearchPaths': SearchPaths,
                                 'delay': 1,
                                 'FStart': 80e6,
                                 'FStop': 1e9,
                                 'InputLevel': soll,
                                 'leveler': None,
                                 'leveler_par': None,
                                 'names': {'sg': 'Sg',
                                           'a1': 'amp_in',
                                           'a2': 'amp_out',
                                           'ant': 'gtem',
                                           'pmfwd': 'pm1',
                                           'pmbwd': 'pm2'
                                           }
                                 }]
         }
