import ast
import os
import sys
import gzip
import pprint

import pickle

from mpylab.env.tem.TEMCell import TEMCell
import mpylab.tools.util

cdict = {"autosave_filename": 'gtem-autosave.p',
         "pickle_output_filename": 'gtem-immunity.p',
         "pickle_input_filename": None,
         "rawdata_output_filename": 'out_raw_immunity-%s.dat',
         "processeddata_output_filename": 'out_processed_immunity-%s.dat',
         "log_filename": 'gtem.log',
         "logger": ['stdlogger'],
         "minimal_autosave_interval": 3600,
         "descriptions": ['eut',],
         "measure_parameters": [{'dotfile': 'gtem-immunity.dot',
                                 'SearchPaths': None,
                                 'delay': 1,
                                 'FStart': 80e6,
                                 'FStop': 1e9,
                                 'InputLevel': None,
                                 'leveler': None,
                                 'leveler_par': None,
                                 'names': {'sg': 'sg',
                                           'a1': 'a1',
                                           'a2': 'a2',
                                           'ant': 'ant',
                                           'pmfwd': 'pm1',
                                           'pmbwd': 'pm2',
                                           'fp': ['fp1', 'fp2', 'fp3', 'fp4', 'fp5', 'fp6', 'fp7', 'fp8'],
                                           'tuner': ['tuner1'],
                                           'refant': ['refant1'],
                                           'pmref': ['pmref1']
                                           }
                                 }]
         }


def myopen(name, mode):
    if name[-3:] == '.gz':
        return gzip.open(name, mode)
    else:
        return open(name, mode)


def update_conf(cdict):
    try:
        import config
        cdict.update(config.cdict)
        print("Configuration updated from 'config.py'.")
    except ImportError:
        pass

    if len(sys.argv) > 1:
        for name in sys.argv[1:]:
            try:
                _mod = __import__(name[:name.rindex('.')])
                cdict.update(getattr(_mod, 'cdict'))
                print(("Configuration updated from '%s'." % name))
            except BaseException as e:
                try:
                    dct = ast.literal_eval(name)
                    if isinstance(dct, dict):
                        cdict.update(dct)
                        print(("Configuration updated from '%s'." % str(dct)))
                except BaseException as e:
                    pass


def load_from_autosave(fname):
    gtem = None
    cmd = None
    if os.path.isfile(fname):
        try:
            pfile = myopen(fname, "rb")
            try:
                gtem = pickle.load(pfile)
            except BaseException as e:
                pfile.close()
                pfile = myopen(fname, "rb")
                gtem = pickle.load(pfile, encoding='latin1')
            cmd = gtem.ascmd
            if gtem:
                msg = "Auto save file %s found.\ncmd: %s\n\nResume: Resume Measurement\nNew: Start new." % (fname, cmd)
                but = ["Resume", "New"]
                answer = gtem.messenger(msg, but)
                # answer = 1
                if answer == but.index('Resume'):
                    startnew = False
                else:
                    del gtem
                    del cmd
                    gtem = None
                    cmd = None
        except IOError as m:
            # this is no problem
            gtem.messenger("IOError during check for autosave-file: %s\nContinue with normal operation..." % m, [])
        except (pickle.UnpicklingError, AttributeError, EOFError, ImportError, IndexError) as m:
            # unpickle was not succesful, but we will continue anyway
            # user can decide later if he is wanting to finish.
            gtem.messenger("Error during unpickle of autosave-file: %s\nContinue with normal operation..." % m, [])
        except BaseException as e:
            # raise all unhadled exceptions
            print(f"Unexpected {e=}, {type(e)=}")
            raise
    return gtem, cmd


def make_logger_list(gtem, clogger):
    logger = []
    for _l in clogger:
        _lst = _l.split('.')  # _lst can be e.g. [stdlogger] or [custom, Filetablogger]
        _mod = None
        if len(_lst) == 1:
            # no module given
            _mod = gtem
        elif len(_lst) == 2:
            try:
                _mod = __import__(_lst[0])
            except ImportError as m:
                _mod = None
                gtem.messenger("ImportError: %s" % m, [])
        if _mod:
            try:
                logger.append(getattr(gtem, _l))
            except AttributeError as m:
                gtem.messenger("Logger not found: %s" % m, [])
    if not len(logger):  # empty
        logger = [gtem.stdlogger]  # fall back to stdlogger
    return logger[:]


if __name__ == '__main__':

    update_conf(cdict)
    print("Configuration values:")
    print()
    pprint.pprint(cdict)

    gtem, cmd = load_from_autosave(cdict['autosave_filename'])

    if not gtem:
        if cdict['pickle_input_filename']:
            pfile = myopen(cdict['pickle_input_filename'], "rb")
            print(("Loading input pickle file '%s'..." % cdict['pickle_input_filename']))
            gtem = pickle.load(pfile)
            pfile.close()
            print("...done")
        else:
            gtem = TEMCell()
        gtem.set_logfile(cdict['log_filename'])
        logger = make_logger_list(gtem, cdict['logger'])
        gtem.set_logger(logger)
        gtem.set_autosave(cdict['autosave_filename'])
        gtem.set_autosave_interval(cdict['minimal_autosave_interval'])

        descriptions = cdict['descriptions'][:]
        for _i, _des in enumerate(cdict['descriptions']):
            try:
                mp = cdict['measure_parameters'][_i]
            except IndexError:
                mp = cdict['measure_parameters'][0]
            mp['description'] = _des
            domeas = True
            doeval = True
            if _des in gtem.rawData_MainCal:
                domeas = False
                doeval = False
                msg = """"
                Measurement with description '%s' allready found in MSC instance.\n
                How do you want to proceed?\n\n
                Continue: Continue with Measurement.\n
                Skip: Skip Measurement but do Evaluation.\n
                Break: Skip Measurement and Evaluation.\n
                Exit: Exit Application
                """ % _des
                but = ["Continue", "Skip", "Break", "Exit"]
                answer = gtem.messenger(msg, but)
                # answer=0
                if answer == but.index('Break'):
                    continue
                elif answer == but.index('Exit'):
                    sys.exit()
                elif answer == but.index('Continue'):
                    domeas = True
                    doeval = True
                elif answer == but.index('Skip'):
                    domeas = False
                    doeval = True
                else:
                    # be safe and do nothing
                    continue
            if domeas:
                gtem.Measure_MainCal(**mp)
                pickle.dump(gtem, open('AfterMeasure.p', 'wb'), 2)
            if doeval:
                gtem.OutputRawData_MainCal(description=_des, fname=cdict["rawdata_output_filename"] % _des)
                gtem.Evaluate_MainCal(description=_des)
            for _passedcal in cdict['descriptions'][:cdict['descriptions'].index(_des)]:
                gtem.CalculateLoading_MainCal(empty_cal=_passedcal, loaded_cal=_des)
                descriptions.append("%s+%s" % (_passedcal, _des))
        dest_str = '_'.join(descriptions)
        pickle.dump(gtem, open('AfterEval.p', 'wb'), 2)
        gtem.OutputProcessedData_MainCal(fname=(cdict["processeddata_output_filename"]) % dest_str)
    else:
        msg = "Select description to use.\n"
        but = []
        for _i, _des in enumerate(cdict['descriptions']):
            msg += '%d: %s' % (_i, _des)
            but.append('%d: %s' % (_i, _des))
        answer = gtem.messenger(msg, but)
        try:
            mp = cdict['measure_parameters'][answer]
        except IndexError:
            mp = cdict['measure_parameters'][0]
        mp['description'] = cdict['descriptions'][answer]
        cmd='gtem.Measure_MainCal(**mp)'
        exec(cmd)

    if os.path.isfile(cdict['pickle_output_filename']):
        msg = "Pickle file %s allready exist.\n\nOverwrite: Overwrite file\nAppend: Append to file." % (
            cdict['pickle_output_filename'])
        but = ["Overwrite", "Append"]
        answer = gtem.messenger(msg, but)
        if answer == but.index('Overwrite'):
            mode = 'wb'
        else:
            mode = 'ab'
    else:
        mode = 'wb'
    try:
        gtem.messenger(mpylab.tools.util.tstamp() + " pickle results to '%s' ..." % (cdict['pickle_output_filename']), [])
        pf = myopen(cdict['pickle_output_filename'], mode)
        pickle.dump(gtem, pf, 2)
        gtem.messenger(mpylab.tools.util.tstamp() + " ...done.", [])
    except BaseException as e:
        gtem.messenger(mpylab.tools.util.tstamp() + " failed to pickle to %s" % (cdict['pickle_output_filename']), [])
        raise
    else:
        # remove autosave file after measurement is completed and class instance was pickled
        try:
            os.remove(cdict['autosave_filename'])
        except BaseException as e:
            pass
