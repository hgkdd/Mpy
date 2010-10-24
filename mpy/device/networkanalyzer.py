# -*- coding: utf-8 -*-
"""This is :mod:`mpy.device.networkanalyzer`

   :author: Christian Albrecht
   :copyright: All rights reserved
   :license: no licence yet


"""



import re
import functools
from mpy.tools.Configuration import Configuration,strbool,fstrcmp
from scuq import *
from mpy.device.device import CONVERT, Device

#from mpy.device.driver import DRIVER
from driver_new import DRIVER


class NETWORKANALYZER(DRIVER):
    """

    Parent class of all py-drivers for networkanalyzer analyzers.
    
    The parent class is :class:`mpy.device.driver.DRIVER`.

    
    The configuration template for this device class is::
    
        conftmpl={'description': 
                 {'description': str,
                  'type': str,
                  'vendor': str,
                  'serialnr': str,
                  'deviceid': str,
                  'driver': str},
                'init_value':
                    {'fstart': float,
                     'fstop': float,
                     'fstep': float,
                     'gpib': int,
                     'virtual': strbool,
                     'nr_of_channels': int},
                'channel_%d':
                    {'unit': str,
                     'reflevel': float,
                     'rbw': float,
                     'span': float,
                     'window': int,
                     'trace_name': str,
                     'S-Parameter': str,
                     'tracemode': str,
                     'sweepcount': int,
                     'sweeppoints': int,
                     'sweeptype': str
                     }}
       
    The meaning is:
        
    - Section *description*
        - description: string describing the instrument
        - type: string with the instrument type (here: POWERMETER)
        - vendor: string ddescribing the vendor/manufactor
        - serialnr: string with a unique identification
        - deviceid: string with an internal id
        - driver: filename of the instrument driver (.py, .pyc, .pyd, .dll)
    - Section *init_value*
        - *fstart*: lowest possible frequency in Hz of the device
        - *fstop*: highest possible frequency in Hz of the device
        - *fstep*: smallest frequency step in Hz of the device
        - *gpib*: GPIB address of the device
        - *virtual*: 0, false or 1, true. Virtual device are usefull for testing and debugging.
        - *nr_of_channels*: indicates how many channel sections follow
        
    .. rubric:: Methods:
    
    .. method:: SetCenterFreq(something):
    
          Set the CenterFreq of the Device.
    
          :param something: CenterFreq for the device
          :type something: float
          :rtype: CenterFreq which is set on the Device after the set command
    
    .. method:: GetCenterFreq():
            Get the CenterFreq of the Device
            
            :rtype: CenterFreq which is set on the Device
    
    .. method:: SetSpan(something):
            Set the Span of the Device
                
            :param something: Span in Hz
            :type something: float
            :rtype: Span which is set on the Device after the set command 
    """
    
    
    # Diese Listen enthalten mögliche Bezeichnungen "possibilities" für Tracemodes usw.
    # Verwendet ein Gerät andere Bezeichnungen für die Modes, dann muss ein maping von den allgemein
    # gültigen Bezeichnungen hin zu den Bezeichnungen des Geräts stattfinden. 
    # Die Maps müssen die Namen MapListenname für das hin mapen bzw. MapListenname_Back für das
    # zurück mapen erhalten, z.B. MapTRACEMODES,MapTRACEMODES_Back
    # Der Aufbau der Listen ist:
    # hin Map: {Allgemein gültiger Bezeichnung : Bezeichnung Gerät}
    # Back Map: {RückgabeWert von Gerät : Allgemein gültige Bezeichnung}
    # Wird in _setgetlist eine possibilities Liste angegeben, dann werden Maps mit den oben beschriebenen
    # Namen automatisch ausgewertet.
    # Beispiel siehe: sp_rs_zlv-6.py
    
    
    #???
    #TRACEMODES=('WRITE','VIEW','AVERAGE', 'BLANK', 'MAXHOLD', 'MINHOLD')

    #???
    conftmpl={'description': 
                 {'description': str,
                  'type': str,
                  'vendor': str,
                  'serialnr': str,
                  'deviceid': str,
                  'driver': str},
                'init_value':
                    {'fstart': float,
                     'fstop': float,
                     'fstep': float,
                     'gpib': int,
                     'virtual': strbool,
                     'nr_of_channels': int},
                'channel_%d':
                    {'unit': str,
                     'SetRefLevel': float,
                     'SetRBW': float,
                     'SetSpan': float,
                     'CreateWindow': str,
                     'CreateTrace': str,
                     'SetSweepCount': int,
                     'SetSweepPoints': int,
                     'SetSweepType': str
                     }}


    sweepType_possib=('LINEAR','LOGARITHMIC')
    
    triggerMode_possib=('IMMEDIATE', 'EXTERNAL')

    sweepMode_possib=('CONTINUOUS','SINGEL')
    
    measParam_possib=('S11', 'S12', 'S21', 'S22')
 
    _commands={"SetCenterFreq" :   {'parameter': ('cfreq'),
                                     'returntype': float},
               "GetCenterFreq":     {'parameter': None, 
                                     'returntype': float},
    
               "SetSpan":           {'parameter':  'span',
                                     'returntype': float},
                      
               "GetSpan":           {'parameter': None, 
                                     'returntype': float},
               
               "SetStartFreq":      {'parameter': 'stfreq',
                                     'returntype': float},
               
               "GetStartFreq":      {'parameter': None,
                                     'returntype': float},
               
               "SetStopFreq":       {'parameter': "spfreq",
                                     'returntype': float},
               
               "GetStopFreq":       {'parameter': None,
                                     'returntype': float} ,
                
               "SetRBW":            {'parameter': 'rbw',
                                     'returntype': float},
               
               "GetRBW":            {'parameter': None,
                                     'returntype': float},
               
               "SetRefLevel":       {'parameter': "reflevel",
                                     'returntype': float},
               
               "GetRefLevel":       {'parameter': None,
                                     'returntype': float},
               
               "SetDivisionValue":  {'parameter': 'divivalue',
                                     'returntype': float},
    
               "GetDivisionValue":  {'parameter': None,
                                     'returntype': float},
               
               "SetTrace":          {'parameter': "traceName",
                                     'returntype': str},
               
               "GetTrace":          {'parameter': None,
                                     'returntype': str},
              
               "SetSparameter":     {'parameter': "sparam",
                                     'returntype': str},
               
               "GetSparameter":     {'parameter': None,
                                     'returntype': str},
                 
               "SetChannel":        {'parameter': "chan",
                                     'returntype': int},
               
               "GetChannel":        {'parameter': None,
                                     'returntype': int},

               "SetSweepType":      {'parameter': "sweepType",
                                     'returntype': str},
    
               "GetSweepType":      {'parameter': None,
                                     'returntype': str},

               "SetSweepCount":     {'parameter': "sweepCount",
                                    'returntype': int},
               
               "GetSweepCount":     {'parameter': None,
                                     'returntype': int},

               "SetSweepPoints":    {'parameter': "spoints",
                                     'returntype': int},
               
               "GetSweepPoints":    {'parameter': None,
                                      'returntype': int},

               "SetTriggerMode":    {'parameter': "triggerMode",
                                     'returntype': str},
               
               "GetTriggerMode":    {'parameter': None,
                                     'returntype': str},
               
               "SetTriggerDelay":   {'parameter': "tdelay",
                                     'returntype': float},

               "GetTriggerDelay":   {'parameter': None,
                                     'returntype': float}
            }

        
    def __init__(self):
        DRIVER.__init__(self)
        self._cmds={}


if __name__ == '__main__':
    import sys

    try:
        ini=sys.argv[1]
    except IndexError:
        ini=None


    d=SPECTRUMANALYZER()
    d.Init(ini)
    if not ini:
        d.SetVirtual(False)

    err, des=d.GetDescription()
    print "Description: %s"%des

    d.Quit()
