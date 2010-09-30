# -*- coding: utf-8 -*-
#
import functools
import re,time
import sys
import StringIO
from scuq import *
#from mpy.device.networkanalyzer import NETWORKANALYZER as NETWORKAN
from networkanalyzer import NETWORKANALYZER as NETWORKAN
from mpy.tools.Configuration import fstrcmp
from mpy.tools.spacing import logspaceN,linspaceN
import numpy

from tools import *
from r_types import *
from validators import *
from mpy_exceptions import *

#
#
# Für den Spectrumanalyzer R&S ZVL wird die Klasse 'zlv-6' definiert.
# Diese greift auf die Unterklasse SPECTRUMANALYZER (spectrumanalyzer.py) und darüber auf die Unterklasse DRIVER (driver.py) zu.
#
class NETWORKANALYZER(NETWORKAN):
    
    """
    Test
    Test
    
    .. rubric:: Methods:
    
    .. method:: SetTrace(tracename,measParam,winNumber):
    
          Creat an new Trace.
    
          :param tracename: Name of the Trace. This Name is only to work with this class, the real name which will be used on the Device ist created by the class.
          :type tracename: str
          :param measParam: S parameter für the Trace 'S11' | 'S22' | 'S12' | 'S21'
          :type measParam: str
          :param winNumber: Number of the Window in which the Trace should be created. The Window must be created bevor with SetWindow(winNumber) 
          :type winNumber: int
          :rtype: (error Code,0)
    
    """
    
    __metaclass__=Meta_Driver
    
    NETWORKANALYZERS=[]

    
    #Map: {Allgemein gültige Bezeichnung : Bezeichnung Gerät} 

    #Back Map: {RückgabeWert von Gerät : Allgemein gültige Bezeichnung} 
    
    
    
    GetSweepType_rmap={'LOG'  :   'LOGARITHMIC',
                       'LIN'  :   'LINEAR',
                        }

    sweepMode_possib_map={'CONTINUOUS'  : 'ON',
                          'SINGEL'  :'OFF'
                          }
    
    GetSweepMode_rmap={'1':'CONTINUOUS',
                       '0':'SINGEL'
                          }

    _cmds= CommandsStorage( NETWORKAN,
                    #Manual S. 499       
                    Command('SetCenterFreq','SENSe%(channel)d:FREQuency:CENTer %(cfreq)s HZ',(
                                              Parameter('channel',global_var='internChannel'),
                                              Parameter('cfreq',ptype=float)# requires=IN_RANGE(0,10e6))   
                                              ), rfunction='GetCenterFreq'),              
                    
                    #Manual S. 499                          
                    Command('GetCenterFreq','SENSe%(channel)d:FREQuency:CENTer?',
                                              Parameter('channel',global_var='internChannel'), 
                                              rtype="<default>"),
                    
                    #Manual S. 500                          
                    Command('SetSpan','SENSe%(channel)d:FREQuency:SPAN %(span)s HZ',(
                                              Parameter('channel',global_var='internChannel'),                                       
                                              Parameter('span',ptype=float),                                      
                                              ), rfunction='GetSpan'),
                    
                    #Manual S. 500                          
                    Command('GetSpan', 'SENSe%(channel)d:FREQuency:SPAN?',
                                              Parameter('channel',global_var='internChannel'), 
                                              rtype="<default>"),
                    
                    #Manual S. 501
                    Command('SetStartFreq','SENSe%(channel)d:FREQuency:STARt %(stfreq)s HZ',(
                                              Parameter('channel',global_var='internChannel'),      
                                              Parameter('stfreq',ptype=float)      
                                              ), rfunction='GetStartFreq'),
                    
                    #Manual S. 501                          
                    Command('GetStartFreq', 'SENSe%(channel)d:FREQuency:STARt?',
                                              Parameter('channel',global_var='internChannel'), 
                                              rtype="<default>"),
                    
                    #Manual S. 501                                                    
                    Command('SetStopFreq', 'SENSe%(channel)d:FREQuency:STOP %(spfreq)s HZ', ( 
                                              Parameter('channel',global_var='internChannel'),      
                                              Parameter('spfreq',ptype=float)      
                                              ), rfunction='GetStopFreq'),                                                                                                                
                    
                    #Manual S. 501
                    Command('GetStopFreq', 'SENSe%(channel)d:FREQuency:STOP?',
                                              Parameter('channel',global_var='internChannel'), 
                                              rtype="<default>"),
                    
                    # Meas/Resolution Bandwidht:
                    #Manual S. 473
                    Command('SetRBW', 'SENSe%(channel)d:BANDwidth:RESolution %(rbw)s HZ',(
                                              Parameter('channel',global_var='internChannel'),      
                                              Parameter('rbw',ptype=float)      
                                              ), rfunction='GetRBW'),                    
                    
                    #Manual S. 473
                    Command('GetRBW','SENSe%(channel)d:BANDwidth:RESolution?',
                                              Parameter('channel',global_var='internChannel'), 
                                              rtype="<default>"),                    
                    
                    ###[SENSe<Ch>:]BANDwidth|BWIDth[:RESolution]:SELect FAST | NORMal???
                    
                    #Manual S. 430
                    Command('SetRefLevel', 'DISPlay:WINDow%(WindowName)s:TRACe%(windTraceNumber)s:Y:SCALe:RLEVel %(reflevel)s DBM',(
                                              Parameter('WindowName', global_var='activeWindow_Name'),
                                              Parameter('windTraceNumber',global_var='activeTrace_WinNum'),
                                              Parameter('reflevel',ptype=float)      
                                              ), rfunction='GetRefLevel'),                            
                    
                    #Manual S. 430                   
                    Command('GetRefLevel','DISPlay:WINDow%(WindowName)s:TRACe%(windTraceNumber)s:Y:SCALe:RLEVel?',(
                                              Parameter('WindowName', global_var='activeWindow_Name'),
                                              Parameter('windTraceNumber', global_var='activeTrace_WinNum')                                          
                                              ), rtype="<default>"),                                        
                    
                    #Manual S. 429                          
                    Command('SetDivisionValue', 'DISPlay:WINDow%(WindowName)s:TRACe%(windTraceNumber)s:Y:SCALe:PDIVision %(divivalue)s DBM',(
                                              Parameter('WindowName', global_var='activeWindow_Name'),
                                              Parameter('windTraceNumber', global_var='activeTrace_WinNum'),
                                              Parameter('divivalue',ptype=float)      
                                              ), rfunction='GetDivisionValue'),                                                                                                                     
                    
                    #Manual S. 429         
                    Command('GetDivisionValue', 'DISPlay:WINDow%(WindowName)s:TRACe%(windTraceNumber)s:Y:SCALe:PDIVision?',(
                                              Parameter('WindowName', global_var='activeWindow_Name'),
                                              Parameter('windTraceNumber', global_var='activeTrace_WinNum')                                          
                                              ), rtype="<default>"),                                                   

 
                     ###Trace Mode nur Max hold
                     #CALCulate<Chn>:PHOLd MAX | OFF                #Manual S. 386
                     ###Dafür bei Sweep average!!!!!! 
                     #[SENSe<Ch>:]AVERage[:STATe] <Boolean>           #Manual S. 473
                     #[SENSe<Ch>:]AVERage:CLEar                       #Manual S. 472 
                    
                                              
                    Function('CreateTrace',(
                                   #Manual S. 384         
                                   Command('CreateTrace',"CALCulate%(channel)d:PARameter:SDEFine \'%(tracename)s\', \'%(measParam)s\'", (
                                              Parameter('channel',global_var='internChannel'),
                                              Parameter('tracename',ptype=str),
                                              Parameter('measParam',ptype=str)
                                              ), ),
                                   #Manual S. 426
                                   Command('ActivedTrace', "DISPlay:WINDow%(windowName)d:TRACe%(windTraceNumber)d:FEED \'%(tracename)s\'",(
                                              Parameter('windowName', global_var='activeWindow_Name'),
                                              Parameter('windTraceNumber',ptype=int),                                                                                                                                                 
                                              Parameter('tracename',ptype=str)
                                              )  ),
                                  ) ),
                     
                    Command('DelTrace', "CALCulate%(channel)d:PARameter:DELete \'%(traceName)s\'",(
                                              Parameter('channel',global_var='internChannel'),
                                              Parameter('traceName', ptype=str)
                                              )      ) ,                                                     
                                                                                                                        
                    Command('GetTrace','CALCulate%(channel)d:PARameter:CATalog?',
                                              Parameter('channel',global_var='internChannel'), 
                                              rtype="<default>"
                                              ),                            
                    
                    #
                    Command('SetTrace',"CALCulate%(channel)d:PARameter:SELect \'%(traceName)s\'",(
                                              Parameter('channel',global_var='internChannel'),
                                              Parameter('traceName',ptype=str)
                                              )     ),
                    
                    #Manual S. 383
                    Command('SetSparameter',"CALCulate%(channel)d:PARameter:MEASure \'%(traceName)s\' \'%(measParam)s\'",(
                                              Parameter('channel',global_var='internChannel'),
                                              Parameter('traceName',global_var='activeTrace_Name'),
                                              Parameter('measParam',ptype=str) 
                                              ),rfunction='GetSparameter'  ),
                    
                    #Manual S. 523                          
                    Command('SetSweepType','SENSe%(channel)d:SWEep:TYPE %(sweepType)s',(
                                              Parameter('channel',global_var='internChannel'),
                                              Parameter('sweepType',ptype=str)
                                              ), rfunction='GetSweepType'),
                               
                    Command('GetSweepType','SENSe%(channel)d:SWEep:TYPE?',
                                              Parameter('channel',global_var='internChannel'),
                                              rtype='<default>'),

                    #Manual S. 520
                    Command('SetSweepCount', 'SENSe%(channel)d:SWEep:COUNt %(sweepCount)s',(
                                              Parameter('channel',global_var='internChannel'),
                                              Parameter('sweepCount',ptype=int)
                                              ), rfunction='GetSweepCount'),
                    
                    #Manual S. 520                                                                       
                    Command('GetSweepCount', 'SENSe%(channel)d:SWEep:COUNt?',
                                              Parameter('channel',global_var='internChannel'),
                                              rtype='<default>'),
                    
                    #Manual S. 443                                      
                    Command('NewSweepCount','INITiate%(channel)d:IMMediate',
                                              Parameter('channel',global_var='internChannel')
                                              ),
                    
                    #Manual S. 521                          
                    Command('SetSweepPoints', 'SENSe%(channel)d:SWEep:POINts %(spoints)s',(
                                              Parameter('channel',global_var='internChannel'),
                                              Parameter('spoints',ptype=int)
                                              ), rfunction='GetSweepPoints'),
                    
                    #Manual S. 521
                    Command('GetSweepPoints', 'SENSe%(channel)d:SWEep:POINts?',
                                              Parameter('channel',global_var='internChannel'),
                                              rtype='<default>'),

                    #Manual S. 442
                    Command('SetSweepMode',"INITiate%(channel)d:CONTinuous %(sweepMode)s",(            
                                              Parameter('channel',global_var='internChannel'),
                                              Parameter('sweepMode',ptype=str)
                                              ), rfunction='GetSweepMode'),
                    
                    #Manual S. 442 
                    Command('GetSweepMode', 'INITiate%(channel)d:CONTinuous?',
                                              Parameter('channel',global_var='internChannel'),
                                              rtype=str), 
                    
                    #Manula S. 547
                    Command('SetTriggerMode', 'TRIGger%(channel)d:SEQuence:SOURce %(triggerMode)s',(
                                              Parameter('channel',global_var='internChannel'),
                                              Parameter('triggerMode',ptype=str)
                                              ), rfunction='GetTriggerMode'),
                    
                    #Manula S. 547
                    Command('GetTriggerMode', 'TRIGger%(channel)d:SEQuence:SOURce?',
                                             Parameter('channel',global_var='internChannel'),
                                             rtype='<default>'),
                    
                    #Manual S. 546
                    Command('SetTriggerDelay', 'TRIGger%(channel)d:SEQuence:HOLDoff %(tdelay)s s',(
                                              Parameter('channel',global_var='internChannel'),
                                              Parameter('tdelay',ptype=int)
                                              ), rfunction='GetTriggerDelay'),
                    #Manula S. 546 
                    Command('GetTriggerDelay', 'TRIGger%(channel)d:SEQuence:HOLDoff?',
                                              Parameter('channel',global_var='internChannel'),
                                              rtype='<default>'),

                    #Manual S. 424
                    Command('CreateWindow', 'DISPlay:WINDow%(windowName)d:STATe ON',
                                              Parameter('windowName',ptype=str),
                                              ),
                    
                    #Manual S. 424
                    Command('DelWindow','DISPlay:WINDow%(windowName)d:STATe OFF',
                                              Parameter('windowName',ptype=int),
                                              ),
                                            
                    Command('CreateChannel','CONFigure:CHANnel%(channel)d:STATe ON',
                                            Parameter('channel',global_var='internChannel')
                                            ),                
                    
                    
                    Command('DelChannel','CONFigure:CHANnel%(channel)d:STATe OFF',
                                            Parameter('channel',global_var='internChannel')
                                            ),                         

                    
                    #Manual S. 415 Wird über Method realisiert 
                    #'GetChannel': [("'CONFigure:CHANnel%d:CATalog?'%self.internChannel", r'(?P<chan>.*')],
                    
                    #Manual S. 339
                    Command('GetSpectrum', 'CALCulate%(channel)d:DATA? FDAT', 
                                            Parameter('channel',global_var='internChannel'),
                                            rtype=TUPLE_OF_FLOAT()
                                            ),
                    
                    #Später:
                    #'GetSpectrumNB':  [('DATA?', r'DATA (?P<power>%s)'%self._FP)],   
                                    
                    Command('SetNWAMode',"INSTrument:SELect NWA",()),
                    
                    Command('GetDescription','*IDN?',(),
                                            rtype=str)  
                    
                    #'Quit':     [('QUIT', None)],
                   )    
                



    #*************************************************************************
    #
    #                    Init
    #*************************************************************************
    def __init__(self): 
        NETWORKAN.__init__(self)
        
        self.traces={}
        self.windows={}
        self._internal_unit='dBm'
        
        NETWORKANALYZER.NETWORKANALYZERS.append(self)
        self.internChannel=-1
        self.internChannel=self.__gethighestChannelNumber()
        
        self.activeTrace=None
        self.activeWindow=None
        
    def __del__(self):
        try:
            del NETWORKANALYZER.NETWORKANALYZERS[NETWORKANALYZER.NETWORKANALYZERS.index(self)]
        except ValueError:
            pass
    
    #Erstellt ein neues Festern, dazu muss die Fensternumer übergeben werden.
    #Die hier übergebenen Nummer ist nur in der aktuellen Instanz güllig.
    #Die eigentliche auf dem Gerät verwendet Nummer wird von der Klasse selbständig ermittelt,
    #und ist über alle Instancen hinweg eindeutig.
    def CreateWindow(self,windowName):
        win=WINDOW(windowName)
        self.windows[windowName]=win
        self._CreateWindow(win.getInternName())
        return 0,windowName
        

    def DelWindow(self):
        self.activeWindow.__del__()
        del self.windows[self.activeWindow.getName()]
        return self._DelWindow(self.activeWindow_Name)
        

    #Diese Funktion legt einen neuen Trace auf dem Gerät an
    # *tracename: Name des Traces, dieser ist nur für die aktuelle Instance gültig. Auf dem Gerät
    #        wird ein Name von der Klasse erstellt, der über alle Instancen hinweg eindeutig ist.
    # *measParam: Als String muss übergeben werde, was gemessen werden soll. z.B. "S11"
    # *winNumber: Hier muss die Nummer des Fensters angegeben werden, in dem der Trace dargestellt werden soll.
    #             Das Fenster muss vorher mit SetWindow(self, winNumber) angelegt werden.

    def CreateTrace(self,tracename,measParam):
        
        existing_traces = re.split(r",",self._GetTrace()[1][1:-1])
        
        tra = TRACE(self,tracename,self.activeWindow,measParam)
        
        if tra.getInternName() in existing_traces:
            raise GeneralDriverError("Trace \'%s\' already exist"%tracename)
        
        self.traces.update({tracename: tra})
        self._CreateTrace(tra.getInternName(),measParam,tra.getTraceWindowNumber())
        
        return 0,tracename
    
    
    def DelTrace(self):
        self.activeTrace.__del__()
        del self.traces[self.activeTrace.getName()]
        return self._DelTrace(self.activeTrace_Name)
    
    #something sie die SParameter als String z.B. 'S11'
    def SetSparameter(self,sparam):
        return self._SetSparameter(sparam)
    
    
    def GetSparameter(self):
        return 0,self.GetTrace()[1][1]

    
    def SetTrace(self,traceName):
        self.activeTrace=self.traces.get(traceName)
        self.activeTrace_Name=self.activeTrace.getInternName()
        self.activeTrace_WinNum=self.activeTrace.getTraceWindowNumber()
        self._SetTrace(self.activeTrace_Name)
        return self.GetTrace()
    
    
    def SetWindow(self,windowName):
        self.activeWindow=self.windows[windowName]
        self.activeWindow_Name=self.activeWindow.getInternName()
        return self.GetWindow()
    
    def GetWindow(self):
        return 0,self.activeWindow.getName()


    def SetSweepCount(self,sweepCount):
        if sweepCount == 0:
            error,ans = self.SetSweepMode('CONTINUOUS')
            if ans:
                return 0
            else:
                raise GeneralDriverError('Can not deactivate SweepCount')
        else:
            error,ans = self.SetSweepMode('SINGEL')
            if ans != 'SINGEL':
                raise GeneralDriverError('Can not activate SweepCount')
            
        return self._SetSweepCount(sweepCount)



    #Infos über einen gestimten Trace abrufen
    def GetTrace(self):        
        trace = re.split(r",",self._GetTrace()[1][1:-1])
        trace_index= trace.index(self.activeTrace.getInternName())
        #print trace_index
        #print trace
        return 0,(trace[trace_index],trace[trace_index+1])
   

    def GetChannel(self):
        return 0,self.internChannel
    
    
    #************************************   
    #  Spectrum aus Gerät auslesen
    #************************************
    def GetSpectrum(self):

        #self.SetSweepCount(1)
        #self.NewSweepCount()
        #time.sleep(1)
        
        error,spec=self._GetSpectrum()
        error,sweepType= self.GetSweepType()
 
        if  sweepType == 'LOGARITHMIC':
            xValues=logspaceN(self.GetStartFreq()[1],self.GetStopFreq()[1],self.GetSweepPoints()[1],endpoint=1,precision=0)
        elif sweepType == 'LINEAR':
            xValues=linspaceN(self.GetStartFreq()[1],self.GetStopFreq()[1],self.GetSweepPoints()[1],endpoint=1,precision=0)
        else:
            raise GeneralDriverError('SweeType %s is not supported'%sweepType)
 
        return 0,(tuple(xValues),spec)
    


    #******************************************************************************
    #
    #             Verwaltungs Funktionen
    #*******************************************************************************

    def getChannelNumber(self):
        return self.internChannel

    
    #Ermittelt die Höchste ChannelNummer über alle Intanzen von nw_rs_zlv.py hinweg
    def __gethighestChannelNumber(self):
        numb=1
        for nw in NETWORKANALYZER.NETWORKANALYZERS:
            if (nw.getChannelNumber() >= numb):
                numb = nw.getChannelNumber()+1
        return numb

            



    #***************************************************************************
    #
    #       Die Init Funktion initialisiert das Gerät, sie muss als erstes aufgerufen werden
    #***************************************************************************
    def Init(self, ini=None, channel=None):
        """
        Init Funktion
        """                
        if channel is None:
            channel=1
        error=NETWORKAN.Init(self,ini, channel)
        
        sec='channel_%d'%channel
        try:
            self.levelunit=self.conf[sec]['unit']
        except KeyError:
            self.levelunit=self._internal_unit
        
        #Schaltet das ZVL in in den SAN - Spectrum analyzer Mode
        self.SetNWAMode()
        
        #Erstellt einne neuen Channel auf dem Gerät
        self.CreateChannel()
        
        
        
        eval("self.%s(%s)"%('CreateWindow',self.conf[sec]['CreateWindow']))
        eval("self.%s(%s)"%('SetWindow',self.conf[sec]['CreateWindow']))
        
        #Existierende Traces im Window löschen:
        trace = re.split(r",",self._GetTrace()[1][1:-1])
        print self._GetTrace()
        if trace[0] != '':
            i=0
            while i<len(trace):
                self._DelTrace(trace[i])
                i=i+2
        
        eval("self.%s(%s)"%('CreateTrace',self.conf[sec]['CreateTrace']))
        eval("self.%s(%s)"%('SetTrace',self.conf[sec]['CreateTrace'].split(',')[0]))

        for func,args in self.conf[sec].items():
            if (func == 'CreateTrace') or (func == 'CreateWindow') :
                continue
            #print func,args
            try:
                eval("self.%s(%s)"%(func,args))
            except (AttributeError,NotImplementedError),e :
                #print e
                pass
        
        print "\nINIT ENDE   ",self,"\n\n"
        
        return error
        
    
class TRACE(object):
    
    TRACES=[]
    
    def __init__(self,nw,name,win,measParam):
        TRACE.TRACES.append(self)
        self.networkanalyzer=nw
        self.name=name
        self.window=win
        self.measParameter = measParam
        self.traceWindowNumber=-1
        self.traceWindowNumber=self.__gethighestTraceWindowNumber()
        self.internName='%s_Ch%dWIN%sTR%d'%(name,self.networkanalyzer.getChannelNumber(),self.window.getInternName(),self.traceWindowNumber)
    
    
    def __del__(self):
        try:
            del TRACE.TRACES[TRACE.TRACES.index(self)]
        except ValueError:
            pass
    
    def __gethighestTraceWindowNumber(self):
        numb=9
        for trace in TRACE.TRACES:
            if (trace.getTraceWindowNumber() >= numb):
                numb = trace.getTraceWindowNumber()+1
        return numb
            
    def getTraceWindowNumber(self):
        return self.traceWindowNumber
    
    def getName(self):
        return self.name
    
    def getInternName(self):
        return self.internName
    
    def getMeasParameter(self):
        return self.measParameter
    
    def getWindow(self):
        return self.window
    
    
class WINDOW(object):
    
    WINDOWS=[]
    
    def __init__(self,name):
        WINDOW.WINDOWS.append(self)
        self.name=name
        self.internNumber=-1
        self.internNumber=self.__gethighestWindowNumber()
        
        
    def __del__(self):
        try:
            del WINDOW.WINDOWS[WINDOW.WINDOWS.index(self)]
        except ValueError:
            pass
        
    def __gethighestWindowNumber(self):
        numb=1
        for win in WINDOW.WINDOWS:
            if (win._getInternNumber() >= numb):
                numb = win._getInternNumber()+1
        return numb
    
    def _getInternNumber(self):
        return self.internNumber
    
    def getInternName(self):
        return str(self.internNumber)
    
    def getName(self):
        return self.name







from networkanalyzer_ui import UI as super_ui
from Meta_ui import Metaui
import enthought.traits.api as tapi
import enthought.traits.ui.api as tuiapi
import enthought.traits.ui.menu as tuim

class UI(super_ui):
    
    __metaclass__ = Metaui
    __driverclass__=NETWORKANALYZER
    __super_driverclass__=NETWORKAN
    
    _ignore=('SetChannel','CreateChannel','GetSpectrum')
    
    def __init__(self,instance, ini=None):
        super_ui.__init__(self,instance,ini)
   
   
   
   
    SetWindow=tapi.Button("SetWindow")
    SETWINDOW=tapi.Str()
    newSETWINDOW=tapi.Str()
    def _SetWindow_fired(self):
        err,value=self.dv.SetWindow(self.newSETWINDOW)
        self.SETWINDOW=value
    Main_S=tuiapi.Group(tuiapi.Group(tuiapi.Item('SetWindow',show_label=False,width=100),
                                     tuiapi.Item('SETWINDOW',label='Wert',style='readonly',width=70),
                                     tuiapi.Item('newSETWINDOW',label='traceName',width=60),
                                     orientation='horizontal'),
                        label='Main_Rest')






##########################################################################       
#
# Die Funktion main() wird nur zum Test des Treibers verwendet!
###########################################################################
def main():
    from mpy.tools.util import format_block
    #
    # Wird f￼r den Test des Treibers keine ini-Datei ￼ber die Kommnadoweile eingegebnen, dann muss eine virtuelle Standard-ini-Datei erzeugt
    # werden. Dazu wird der hinterlegte ini-Block mit Hilfe der Methode 'format_block' formatiert und der Ergebnis-String mit Hilfe des Modules
    # 'StringIO' in eine virtuelle Datei umgewandelt.
    #
    err = 0
    try:
        ini=sys.argv[1]
    except IndexError:
        ini=format_block("""
                        [DESCRIPTION]
                        description: 'ZLV-K1'
                        type:        'NETWORKANALYZER'
                        vendor:      'Rohde&Schwarz'
                        serialnr:
                        deviceid:
                        driver:

                        [Init_Value]
                        fstart: 100e6
                        fstop: 6e9
                        fstep: 1
                        gpib: 18
                        virtual: 0
                        nr_of_channels: 2

                        [Channel_1]
                        unit: 'dBm'
                        SetRefLevel: 10
                        SetRBW: 10e3
                        SetSpan: 5999991000
                        CreateWindow: 'default'
                        CreateTrace: 'default','S22'
                        SetSweepCount: 0
                        SetSweepPoints: 100
                        SetSweepType: 'Log'
                        """)
                        # rbw: 3e6
        ini=StringIO.StringIO(ini)
        
        
        ini2=format_block("""
                        [DESCRIPTION]
                        description: 'ZLV-K1'
                        type:        'NETWORKANALYZER'
                        vendor:      'Rohde&Schwarz'
                        serialnr:
                        deviceid:
                        driver:

                        [Init_Value]
                        fstart: 100e6
                        fstop: 6e9
                        fstep: 1
                        gpib: 18
                        virtual: 0

                        [channel_1]
                        unit: 'dBm'
                        SetRefLevel: 0
                        SetRBW: 10e3
                        SetSpan: 5999991000
                        CreateWindow: 'default'
                        CreateTrace: 'default','S11'
                        SetSweepCount: 1
                        SetSweepPoints: 50
                        SetSweepType: 'LINEAR'
                        """)
        ini2=StringIO.StringIO(ini2)
        
    # #
    # # Zum Test des Treibers werden sogenannte Konsistenzabfragen ('assert' Bedingungen) verwendet, welche einen 'AssertationError' liefern,
    # # falls die Bedingung 'false' ist. Zuvor wird eine Testfrequenz und ein Level festgelegt, ein Objekt der Klasse SMB100A erzeugt und der
    # # Signalgenerator initialisiert.
    # #
    #from mpy.device.networkanalyzer_ui import UI as UI
    nw=NETWORKANALYZER()
    nw2=NETWORKANALYZER()
    
    try:
        UI(nw)
    except NameError:
        pass
    else:
       
       ui=UI(nw,ini=ini)
       ui.configure_traits()
       sys.exit(0)    
    
    
    
    err=nw.Init(ini)
    assert err==0, 'Init() fails with error %d'%(err)
    
    err=nw2.Init(ini2)
    assert err==0, 'Init() fails with error %d'%(err)
    
     
    
    #_assertlist=[
    #             ("SetCenterFreq", 3e9,"assert"),                     #Default:3e9
    #              ('SetSpan',5999991000,"print"),                     #Default:6e9
    #              ('SetStartFreq',9e3,"assert"),                      #Default:9e3
    #              ('SetStopFreq',6e9,"assert"),                       #Default:6e9
    #              ('SetRBW',10e3,"assert"),                           #Default:10e3
    #              ('SetSweepType',"LOGARITHMIC","print"),             #LINear | LOGARITHMIC | SEGMent   
    #              ('SetSweepPoints',50,"assert"),                     #Default: 201  
                  #('SetSweepCount',1,"print"),                       #Default: 1
    #             ]
 
    #for funk,value,test in _assertlist:
    #    err,ret = getattr(nw,funk)(value)
    #    assert err==0,  '%s() fails with error %d'%(funk,err)
    #    if value != None:
    #        if test == "assert":
    #            assert ret==value, '%s() returns freq=%s instead of %s'%(funk,ret,value)
    #        else:
    #            print '%s(): Rückgabewert: %s   Sollwert: %s'%(funk,ret,value)
    #    else:
    #        print '%s(): Rückgabewert: %s'%(funk,ret)


    nw.SetSweepCount(1)
    nw.NewSweepCount()
    time.sleep(1)
    err,spec=nw.GetSpectrum()
    assert err==0, 'GetSpectrum() fails with error %d'%(err)
    print spec[0]
    print spec[1]
    
    
    nw2.SetSweepCount(1)
    nw2.NewSweepCount()
    time.sleep(1)
    err,spec=nw2.GetSpectrum()
    assert err==0, 'GetSpectrum() fails with error %d'%(err)
    print spec[0][25]
    print spec[1][25]

    
    
    #err=nw.Quit()
    #assert err==0, 'Quit() fails with error %d'%(err)
#


  
#  ------------ Hauptprogramm ---------------------------
#
# Die Treiberdatei selbst und damit das Hauptprogramm wird nur gestartet, um den Treibercode zu testen. In diesem Fall springt
# das Programm direkt in die Funktion 'main()'. Bei der sp￤teren Verwendung des Treibers wird nur die Klasse 'SMB100A' und deren
# Methoden importiert.
#
if __name__ == '__main__':
    main()
