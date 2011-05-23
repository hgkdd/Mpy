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
    
    This Driver use the new dirver framework!
    
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
                     'virtual': strbool},
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
    - Section *channel_%d*
        - *unit*:
        - *SetRefLevel*:
        - *SetRBW*:
        - *SetSpan*:
        - *CreateWindow*:
        - *CreateTrace*:
        - *SetSweepCount*:
        - *SetSweepPoints*:
        - *SetSweepType*:
        
        
        
    .. rubric:: Methods:
    
    .. method:: SetCenterFreq(cfreq):
    
          Set the CenterFreq of the Device.
    
          :param cfreq: CenterFreq for the device
          :type cfreq: float
          :rtype: CenterFreq which is set on the Device after the set command; Type float
    
    .. method:: GetCenterFreq():
            Get the CenterFreq of the Device
            
            :rtype: CenterFreq which is set on the Device; Type float
    
    .. method:: SetSpan(span):
            Set the Span of the Device
                
            :param span: Span in Hz
            :type span: float
            :rtype: Span which is set on the Device after the set command; Type float
            
    .. method:: GetSpan():
            Get the Span of the Device
            
            :rtype: Span which is set on the Device; Type float
    
    .. method:: SetStartFreq(stfreq):
            Set the Start Frequency of the Device
            
            :param stfreq: Start Frequency of the Device
            :type stfreq: float
            :rtype: Start Frequency which is set on the Device; Type float
            
    .. method:: GetStartFreq():
            Get the Start Frequency of the Device
            
            :rtpye: Start Frequency which is set on the Device; Type float
            
    .. method:: SetStopFreq(spfreq):
            Set the Stop Frequency of the Device
            
            :param spfreq: Stop Frequency of the Device
            :type spfreq: float
            :rtype: Stop Frequency which is set on the Device; Type float
            
    .. method:: GetStopFreq():
            Get the Stop Frequency of the Device
            
            :rtpye: Stop Frequency which is set on the Device; Type float

    .. method:: SetRBW(rbw):
            Set the Resolution Bandwidth of the Device
            
            :param rbw: Resolution Bandwidth of the Device
            :type rbw: float
            :rtype: Resolution Bandwidth which is set on the Device; Type float
            
    .. method:: GetRBW():
            Get the Resolution Bandwidth of the Device
            
            :rtpye: Resolution Bandwidth which is set on the Device; Type float

    .. method:: SetRefLevel(reflevel):
            Set the Reference Level of the Device
            
            :param reflevel: Reference Level of the Device
            :type reflevel: float
            :rtype: Reference Level which is set on the Device; Type float
    
    .. method:: GetRefLevel():
            Get the Reference Level of the Device
            
            :rtpye: Reference Level which is set on the Device; Type float

    .. method:: SetDivisionValue(divivalue):
            Sets the value between two grid graticules (value per division) for the diagram area.
            
            :param divivalue: Division Value of the Device
            :type divivalue: float
            :rtype: Division Value which is set on the Device; Type float

    .. method:: GetDivisionValue():
            Gets the value between two grid graticules (value per division) for the diagram area.
            
            :rtpye: Division Value which is set on the Device; Type float
            
    .. method:: SetTrace(traceName):
            Creates a Trace and assigns the given name to it.
            
            :param traceName: Name of the new Trace
            :type traceName: String
            :rtype: Name of the currently active Trace; Type String
            
    .. method:: GetTrace():
            Gets the Name of the currently active Trace
            
            :rtpye: Name of the currently active Trace; Type String
            
    .. method:: SetSparameter(sparam):
            Assigns the s-parameter to the currently active Trace
            
            :param sparam: S-parameter as String; ('S11', 'S12', 'S21', 'S22')
            :type sparam: String
            :rtype: S-parameter of the currently active Trace which is set on the Device; Type String
            
    .. method:: GetTrace():
            Gets s-parameter of the currently active Trace
            
            :rtpye: S-parameter of the currently active Trace which is set on the Device; Type String

    .. method:: SetChannel(chan):
            Sets the Channel Number of the Device
            
            :param chan: Number of the Channel
            :type chan: Integer
            :rtype: Channel Number of the Device ; Type Integer
            
    .. method:: GetChannel():
            Gets the Channel Number of the Device
            
            :rtpye: Channel Number of the Device; Type Integer

    .. method:: SetSweepType(sweepType):
            Selects the sweep type and the position of the sweep points across the sweep range.
            
            :param sweepType: sweep type as String ('LINEAR','LOGARITHMIC')
            :type sweepType: String
            :rtype: sweep type of the current channel which is set on the Device; Type String
            
    .. method:: GetSweepType():
            Selects the sweep type and the position of the sweep points across the sweep range.
            
            :rtpye: sweep type of the current channel which is set on the Device; Type String

    .. method:: SetSweepCount(sweepCount):
            Sets the number of sweeps to be measured in single sweep mode
            
            :param sweepCount: Reference Level of the Device
            :type sweepCount: Integer
            :rtype: Sweep Count which is set on the Device; Type Integer
    
    .. method:: GetSweepCount():
            Gets the number of sweeps to be measured in single sweep mode
            
            :rtpye: Sweep Count which is set on the Device; Type Integer
            
    .. method:: SetSweepPoints(spoints):
            Sets the total number of measurement points per sweep
            
            :param spoints: Sweep Points of the Device
            :type spoints: Integer
            :rtype: Sweep Point which is set on the Device; Type Integer
    
    .. method:: GetSweepPoints():
            Gets the total number of measurement points per sweep
            
            :rtpye: Sweep Point which is set on the Device; Type Integer
    
    .. method:: SetTriggerMode(triggerMode):
            xxxx
            
            :param spoints: Trigger Mode of the Device ('IMMEDIATE', 'EXTERNAL')
            :type spoints: String
            :rtype: Trigger Mode which is set on the Device; Type String
    
    .. method:: GetTriggerMode():
            xxxx
            
            :rtpye: Trigger Mode which is set on the Device; Type String

    .. method:: SetTriggerDelay(tdelay):
            xxxx
            
            :param tdelay: Trigger Delay of the Device
            :type tdelay: Float
            :rtype: Trigger Delay which is set on the Device; Type Float
    
    .. method:: GetTriggerMode():
            xxxx
            
            :rtpye: Trigger Delay which is set on the Device; Type Float
            
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
                     'virtual': strbool},
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
