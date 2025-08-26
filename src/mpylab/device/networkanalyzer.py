# -*- coding: utf-8 -*-
"""This is :mod:`mpylab.device.networkanalyzer`

   :author: Christian Albrecht
   :copyright: All rights reserved
   :license: no licence yet


"""

###Refers to the currently active Trace. See also SetTrace()


from mpylab.tools.Configuration import strbool

# from mpylab.device.driver import DRIVER
from .driver_new import DRIVER


class NETWORKANALYZER(DRIVER):
    """

    Parent class of all py-drivers for networkanalyzer analyzers.
    
    This Driver use the new dirver framework!
    
    The parent class is :class:`mpylab.device.driver.DRIVER`.

    
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
        - *SetRefLevel*: Reference Level (for further information see function description)
        - *SetRBW*: Resolution Bandwidth (for further information see function description)
        - *SetSpan*: Span of Device (for further information see function description)
        - *CreateWindow*: Name of the first Window (for further information see function description)
        - *CreateTrace*: Name of the first Trace (for further information see function description)
        - *SetSweepCount*: Sets the number of sweeps to be measured in single sweep mode. (for further information see function description)
        - *SetSweepPoints*: Sweep Points (for further information see function description)
        - *SetSweepType*: Sweep Type (for further information see function description)
        
    .. rubric:: Das _commands-Dict:
        
    Im _commands-Dict werden alle Funktionen Definiert welche möglichst in allen Driver Klassen
    Implementiert werden sollten. Durch _commands kann so sichergestellt werden, dass alle Driver die von
    dieser Klasse abgeleitet werden eine Reihe standard Funktionen haben, die in allen Implementierungen
    gleich sind.
    
    Beim Schreiben des Dicti ist folgende Konvention einzuhalten::
        
        _commands={"Name_der_Funktion": {'parameter': String-Tupel_von_Strings-None,
                                     'returntype': Standard_Pthon-Typ oder r_type},
                    ......
                   
    Für r_type siehe auch: :mod:`mpylab.device.r_types`
    
    Siehe auch :class:`mpylab.device.tools.Meta_Driver`
    
    Die Driver Metaklasse prüft anhand von _commands ob Funktionen, deren Name im Dict vorhanden ist, die gleich 
    Parameter-Liste besitzen, das heißt: gleiche Anzahl und gleiche Reihenfolge der Parameter. Fehlt in einer 
    konkreten Implementierung eines Drivers ein in _commands defniniert Funktion, so baut die Metaklasse ein 
    Funktion welche einen NotImplementedError wirft.

    
       
    .. rubric:: Possibiltie-Listen:
    Possibilities sind mögliche Werte für einen Parameter. Bei bestimmen Parameter können immer nur bestimmte
    Werte übergeben werden, so sind beispielsweise bei sparam (S-Paramter) außschließlich ('S11', 'S12', 'S21', 'S22')
    möglich. Damit nicht jeder kleine Schreibfehelr sofort zum Abbruch des Programm führt und damit sichergestellt ist
    das immer ein richtier Wert übergeben wird, wird mit Hilfe eines Fuzzy-string-compares der übergebene Wert auf einen 
    in der Posssibilites-Liste vorhandenen zurückgeführt.
        
    Possibility-Listen können sowol in einer konkreten Implementierung einer Driver-Klasse als auch in einer Driver-
    Superklasse definiert werden. Es wird geraten die Definition immer in der Super-Klasse vorzunehmen, damit die 
    Possibilities für alle Driver gleich sind.
        
    Für eine genau beschreibung siehe: :class:`mpylab.device.tools.Meta_Driver`

    .. rubric:: Methods:
    .. method:: SetCenterFreq(cfreq):
    
          Set the CenterFreq of the Device.
    
          :param cfreq: CenterFreq for the device
          :type cfreq: float
          :return: CenterFreq which is set on the Device after the set command 
          :rtype: float
    
    .. method:: GetCenterFreq():
            Get the CenterFreq of the Device
            
            :return: CenterFreq which is set on the Device
            :rtype: float
    
    .. method:: SetSpan(span):
            Set the Span of the Device.
            Defines the width of the measurement and display range for a frequency sweep.
                
            :param span: Span in Hz
            :type span: float
            :return: Span which is set on the Device after the set command
            :rtype: float
            
    .. method:: GetSpan():
            Get the Span of the Device
            
            :return: Span which is set on the Device 
            :rtype: float
    
    .. method:: SetStartFreq(stfreq):
            Set the Start Frequency of the Device
            
            :param stfreq: Start Frequency of the Device
            :type stfreq: float
            :return: Start Frequency which is set on the Device after the set command 
            :rtype: float
            
    .. method:: GetStartFreq():
            Get the Start Frequency of the Device
            
            :return: Start Frequency which is set on the Device after the set command  
            :rtype: float
            
    .. method:: SetStopFreq(spfreq):
            Set the Stop Frequency of the Device
            
            :param spfreq: Stop Frequency of the Device
            :type spfreq: float
            :return: Stop Frequency which is set on the Device after the set command
            :rtype: float
            
    .. method:: GetStopFreq():
            Get the Stop Frequency of the Device
            
            :return: Stop Frequency which is set on the Device
            :rtype: float

    .. method:: SetRBW(rbw):
            Set the Resolution Bandwidth of the Device
            
            :param rbw: Resolution Bandwidth of the Device
            :type rbw: float
            :return: Resolution Bandwidth which is set on the Device after the set command 
            :rtype: float
            
    .. method:: GetRBW():
            Get the Resolution Bandwidth of the Device
            
            :return: Resolution Bandwidth which is set on the Device 
            :rtype: float

    .. method:: SetRefLevel(reflevel):
            Set the Reference Level of the currently active Trace.
            
            :param reflevel: Reference Level of the Device
            :type reflevel: float
            :return: Reference Level which is set on the Device after the set command 
            :rtype: float
    
    .. method:: GetRefLevel():
            Get the Reference Level of the currently active Trace.
            
            :return: Reference Level which is set on the Device 
            :rtype: float

    .. method:: SetDivisionValue(divivalue):
            Sets the value between two grid graticules (value per division) for the diagram area.
            
            :param divivalue: Division Value of the Device
            :type divivalue: float
            :return: Division Value which is set on the Device after the set command 
            :rtype: float

    .. method:: GetDivisionValue():
            Gets the value between two grid graticules (value per division) for the diagram area.
            
            :return: Division Value which is set on the Device 
            :rtype: float
    
    
    .. method:: CreateTrace(tracename, sparam):
             Creates a Trace and assigns the given name to it.
             
             :param tracename: Name of the new Trace
             :type tracename: String
             :param sparam: S-parameter as String; ('S11', 'S12', 'S21', 'S22')
             :type sparam: String
             :return: Name of the new Trace 
             :rtype: String
    
    .. method:: DelTrace(traceName):
              Deletes a trace with a specified trace name.
              
              :param traceName: Name of the Trace which should deleted
              :type traceName: String
              :rtype: None
    
    .. method:: SetTrace(traceName):
             Selects an existing trace as the active trace.
            
             :param traceName: Name of the trace which should be selected.
             :type traceName: String
             :return: Name of the currently active Trace after the set command 
             :rtype: String
            
    .. method:: GetTrace():
            Gets the Name of the currently active Trace
            
            :return: Name of the currently active Trace 
            :rtype: String
            
    .. method:: SetSparameter(sparam):
            Assigns the s-parameter to the currently active Trace.
            See also SetTrace()
            
            :param sparam: S-parameter as String; ('S11', 'S12', 'S21', 'S22')
            :type sparam: String
            :return: S-parameter of the currently active Trace which is set on the Device after the set command 
            :rtype: String
            
    .. method:: GetTrace():
            Gets s-parameter of the currently active Trace.
            See also SetTrace()
            
            :return: S-parameter of the currently active Trace which is set on the Device 
            :rtype: String

    .. method:: SetChannel(chan):
            Sets the Channel Number of the Device
            
            :param chan: Number of the Channel
            :type chan: Integer
            :return: Channel Number of the Device after the set command 
            :rtype: Integer
            
    .. method:: GetChannel():
            Gets the Channel Number of the Device
            
            :return: Channel Number of the Device 
            :rtype: Integer

    .. method:: SetSweepType(sweepType):
            Selects the sweep type and the position of the sweep points across the sweep range.
            
            :param sweepType: sweep type as String ('LINEAR','LOGARITHMIC')
            :type sweepType: String
            :return: sweep type which is set on the device after the set command 
            :rtype: String
            
    .. method:: GetSweepType():
            Selects the sweep type and the position of the sweep points across the sweep range.
            
            :return: sweep type which is set on the Device 
            :rtype: String

    .. method:: SetSweepCount(sweepCount):
            Sets the number of sweeps to be measured in single sweep mode.
            
            :param sweepCount: Reference Level of the Device
            :type sweepCount: Integer
            :return: Sweep Count which is set on the Device after the set command 
            :rtype: Integer
    
    .. :method:: GetSweepCount():
            Gets the number of sweeps to be measured in single sweep mode
            
            :return: Sweep Count which is set on the Device 
            :rtype: Integer
            
    .. :method:: NewSweepCount():
            Starts a new single sweep sequence.
            
            
    .. :method:: SetSweepPoints(spoints):
            Sets the total number of measurement points per sweep
            
            :param spoints: Sweep Points of the Device
            :type spoints: Integer
            :return: Sweep Point which is set on the Device after the set command 
            :rtype: Integer
    
    .. :method:: GetSweepPoints():
            Gets the total number of measurement points per sweep
            
            :return: Sweep Point which is set on the Device 
            :rtype: Integer
    
    .. :method:: SetSweepMode(sweepMode):
            Set the sweep mode to in single sweep or in continuous sweep
            
            :param sweepMode: Sweep mode which should set. ('CONTINUOUS','SINGEL')
            :type sweepMode: String
            :return: Sweep Mode which is set on the Device after the set command 
            :rtype: String
    
    .. :method:: GetSweepMode():
            Get the sweep mode of the device.
            
            :return: Sweep Mode which is set on the Device 
            :rtype: String
            
    
    .. :method:: SetTriggerMode(triggerMode):
            Selects the source for the events that the analyzer uses to start a sweep.
            
            :param spoints: Trigger Mode of the Device ('IMMEDIATE', 'EXTERNAL')
            :type spoints: String
            :return: Trigger Mode which is set on the Device 
            :rtype: String
    
    .. :method:: GetTriggerMode():
            Gets the source for the events that the analyzer uses to start a sweep.
            
            :return: Trigger Mode which is set on the Device 
            :rtype: String

    .. :method:: SetTriggerDelay(tdelay):
            Sets a delay time between the trigger event and the start of the measurement.
            
            :param tdelay: Trigger Delay of the Device
            :type tdelay: Float
            :return: Trigger Delay which is set on the Device 
            :rtype: Float
    
    .. :method:: GetTriggerMode():
            Sets a delay time between the trigger event and the start of the measurement.
            
            :return: Trigger Delay which is set on the Device 
            :rtype: Float
    """

    conftmpl = {'description':
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

    # Die "possibilities" Listen:
    sweepType_possib = ('LINEAR', 'LOGARITHMIC')

    triggerMode_possib = ('IMMEDIATE', 'EXTERNAL')

    sweepMode_possib = ('CONTINUOUS', 'SINGEL')

    sparam_possib = ('S11', 'S12', 'S21', 'S22')

    _commands = {"SetCenterFreq": {'parameter': ('cfreq'),
                                   'returntype': float},
                 "GetCenterFreq": {'parameter': None,
                                   'returntype': float},

                 "SetSpan": {'parameter': 'span',
                             'returntype': float},

                 "GetSpan": {'parameter': None,
                             'returntype': float},

                 "SetStartFreq": {'parameter': 'stfreq',
                                  'returntype': float},

                 "GetStartFreq": {'parameter': None,
                                  'returntype': float},

                 "SetStopFreq": {'parameter': "spfreq",
                                 'returntype': float},

                 "GetStopFreq": {'parameter': None,
                                 'returntype': float},

                 "SetRBW": {'parameter': 'rbw',
                            'returntype': float},

                 "GetRBW": {'parameter': None,
                            'returntype': float},

                 "SetRefLevel": {'parameter': "reflevel",
                                 'returntype': float},

                 "GetRefLevel": {'parameter': None,
                                 'returntype': float},

                 "SetDivisionValue": {'parameter': 'divivalue',
                                      'returntype': float},

                 "GetDivisionValue": {'parameter': None,
                                      'returntype': float},

                 "CreateTrace": {'parameter': ('tracename', 'sparam'),
                                 'returntype': str},

                 "DelTrace": {'parameter': None,
                              'returntype': str},

                 "SetTrace": {'parameter': "traceName",
                              'returntype': str},

                 "GetTrace": {'parameter': None,
                              'returntype': str},

                 "SetSparameter": {'parameter': "sparam",
                                   'returntype': str},

                 "GetSparameter": {'parameter': None,
                                   'returntype': str},

                 "SetChannel": {'parameter': "chan",
                                'returntype': int},

                 "GetChannel": {'parameter': None,
                                'returntype': int},

                 "SetSweepType": {'parameter': "sweepType",
                                  'returntype': str},

                 "GetSweepType": {'parameter': None,
                                  'returntype': str},

                 "SetSweepCount": {'parameter': "sweepCount",
                                   'returntype': int},

                 "GetSweepCount": {'parameter': None,
                                   'returntype': int},

                 "NewSweepCount": {'parameter': None,
                                   'returntype': None},

                 "SetSweepPoints": {'parameter': "spoints",
                                    'returntype': int},

                 "GetSweepPoints": {'parameter': None,
                                    'returntype': int},

                 "SetSweepMode": {'parameter': "sweepMode",
                                  'returntype': str},

                 "GetSweepMode": {'parameter': None,
                                  'returntype': str},

                 "SetTriggerMode": {'parameter': "triggerMode",
                                    'returntype': str},

                 "GetTriggerMode": {'parameter': None,
                                    'returntype': str},

                 "SetTriggerDelay": {'parameter': "tdelay",
                                     'returntype': float},

                 "GetTriggerDelay": {'parameter': None,
                                     'returntype': float}
                 }

    def __init__(self):
        DRIVER.__init__(self)
        self._cmds = {}


if __name__ == '__main__':
    import sys

    try:
        ini = sys.argv[1]
    except IndexError:
        ini = None

    d = NETWORKANALYZER()
    d.Init(ini)
    if not ini:
        d.SetVirtual(False)

    err, des = d.GetDescription()
    print(("Description: %s" % des))

    d.Quit()
