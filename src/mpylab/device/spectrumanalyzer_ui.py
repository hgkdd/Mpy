# -*- coding: utf-8 -*-
import io
import traits.api as tapi
from traits.etsconfig.api import ETSConfig
ETSConfig.toolkit = "wx"
import traitsui.api as tuiapi
import traitsui.menu as tuim
from chaco.api import Plot, ArrayPlotData
from enable.component_editor import ComponentEditor
import numpy as np
from mpylab.tools.util import format_block
from mpylab.device.device import CONVERT

conv = CONVERT()

std_ini = format_block("""
                [DESCRIPTION]
                description: sp template
                type:        'SPECTRUMANALYZER'
                vendor:      some company
                serialnr:    SN12345
                deviceid:    internal ID
                driver:      dummy.py
    
                [Init_Value]
                fstart: 100e6
                fstop: 6e9
                fstep: 1
                gpib: 20
                virtual: 0

                [Channel_1]
                unit: 'dBm'
                attenuation: auto
                reflevel: -20
                rbw: auto
                vbw: 10e6
                span: 6e9
                trace: 1
                tracemode: 'WRITe'
                detector: 'APEak'
                sweepcount: 0
                triggermode: 'IMMediate'
                attmode: 'auto'
                sweeptime: 10e-3
                sweeppoints: 500
                """)
std_ini = io.StringIO(std_ini)


class UI(tapi.HasTraits):
    Init = tapi.Button()
    INI = tapi.Str()
    int_unit = 'dBm'

    # Button und Variablen für Traits anlegen
    #
    # Variablen Namen für Button:
    # SetName
    # GetName
    # Variablen für Felder:
    # NAME
    # newNAME
    #
    # Name muss identisch mit dem Namen in der Liste mainTab sein! (siehe unten)

    SetCenterFreq = tapi.Button("SetCenterFreq")
    GetCenterFreq = tapi.Button("GetCenterFreq")
    CENTERFREQ = tapi.Float()
    newCENTERFREQ = tapi.Float()
    SetSpan = tapi.Button("SetSpan")
    GetSpan = tapi.Button("GetSpan")
    SPAN = tapi.Float()
    newSPAN = tapi.Float()
    SetStartFreq = tapi.Button("SetStartFreq")
    GetStartFreq = tapi.Button("GetStartFreq")
    STARTFREQ = tapi.Float()
    newSTARTFREQ = tapi.Float()
    SetStopFreq = tapi.Button("SetStopFreq")
    GetStopFreq = tapi.Button("GetStopFreq")
    STOPFREQ = tapi.Float()
    newSTOPFREQ = tapi.Float()
    SetRBW = tapi.Button("SetRBW")
    GetRBW = tapi.Button("GetRBW")
    RBW = tapi.Float()
    newRBW = tapi.Str()
    SetVBW = tapi.Button("SetVBW")
    GetVBW = tapi.Button("GetVBW")
    VBW = tapi.Float()
    newVBW = tapi.Str()
    SetRefLevel = tapi.Button("SetRefLevel")
    GetRefLevel = tapi.Button("GetRefLevel")
    REFLEVEL = tapi.Float()
    newREFLEVEL = tapi.Float()
    SetAtt = tapi.Button("SetAtt")
    GetAtt = tapi.Button("GetAtt")
    ATT = tapi.Float()
    newATT = tapi.Str()
    SetAttMode = tapi.Button("SetAttMode")
    GetAttMode = tapi.Button("GetAttMode")
    ATTMODE = tapi.Str()
    newATTMODE = tapi.Str()
    SetPreAmp = tapi.Button("SetPreAmp")
    GetPreAmp = tapi.Button("GetPreAmp")
    PREAMP = tapi.Float()
    newPREAMP = tapi.Float()
    SetDetector = tapi.Button("SetDetector")
    GetDetector = tapi.Button("GetDetector")
    DETECTOR = tapi.Str()
    newDETECTOR = tapi.Str()
    SetTraceMode = tapi.Button("SetTraceMode")
    GetTraceMode = tapi.Button("GetTraceMode")
    TRACEMODE = tapi.Str()
    newTRACEMODE = tapi.Str()
    SetTrace = tapi.Button("SetTrace")
    GetTrace = tapi.Button("GetTrace")
    TRACE = tapi.Int()
    newTRACE = tapi.Int()
    SetSweepCount = tapi.Button("SetSweepCount")
    GetSweepCount = tapi.Button("GetSweepCount")
    SWEEPCOUNT = tapi.Int()
    newSWEEPCOUNT = tapi.Int()
    SetSweepTime = tapi.Button("SetSweepTime")
    GetSweepTime = tapi.Button("GetSweepTime")
    SWEEPTIME = tapi.Float()
    newSWEEPTIME = tapi.Str()
    SetTriggerMode = tapi.Button("SetTriggerMode")
    GetTriggerMode = tapi.Button("GetTriggerMode")
    TRIGGERMODE = tapi.Str()
    newTRIGGERMODE = tapi.Str()
    SetTriggerDelay = tapi.Button("SetTriggerDelay")
    GetTriggerDelay = tapi.Button("GetTriggerDelay")
    TRIGGERDELAY = tapi.Float()
    newTRIGGERDELAY = tapi.Float()
    SetSweepPoints = tapi.Button("SetSweepPoints")
    GetSweepPoints = tapi.Button("GetSweepPoints")
    SWEEPPOINTS = tapi.Int()
    newSWEEPPOINTS = tapi.Int()

    # In mainTab stehen alle Name der Buttons und Felder.
    # Durch mainTab werden alle Buttons und Felder später automatisch angelegt.  
    mainTab = ('CenterFreq', 'Span', 'StartFreq', 'StopFreq', 'RBW', 'VBW',
               'RefLevel', 'Att', 'AttMode', 'PreAmp', 'Detector', 'TraceMode',
               'Trace', 'SweepCount', 'SweepTime', 'TriggerMode', 'TriggerDelay', 'SweepPoints')

    GetSpectrum = tapi.Button("GetSpectrum")
    SPECTRUM = tapi.Str()
    power = ()

    def __init__(self, instance, ini=None, *args, **kwargs):
        # Wenn keine ini übergeben wurde wird die Standard ini verwendet.
        super().__init__(*args, **kwargs)
        self.sp = instance
        if not ini:
            ini = std_ini
        self.ini = ini
        self.INI = ini.read()

        # Plot Fenster erstellen.
        x = np.array([])
        y = np.array([])
        self.plotdata = ArrayPlotData(x=x, y=y)
        plot = Plot(self.plotdata)
        plot.plot(("x", "y"), type="line", color="blue")
        plot.title = "Spectrum"
        plot.index_axis.title = 'Frequenz in Hz'
        plot.value_axis.title = 'Amplitude in dBm'
        self.plot = plot

    # *************************************************************************
    #
    # Funktionen die aufgerufen werden wenn ein Button gedrückt wird. 
    # **************************************************************************

    # Spectrum holen und in Fester und Plot schreiben.
    def _GetSpectrum_fired(self):
        self.power = self.sp.GetSpectrum()[1]
        x = np.array(self.power[0])
        y = np.array(self.power[1])
        self.plotdata.set_data('x', x)
        self.plotdata.set_data('y', y)
        self.plot.request_redraw()

        self.SPECTRUM = str(self.power[0]) + "\n\n\n" + str(self.power[1])

    def _Init_fired(self):
        ini = io.StringIO(self.INI)
        self.sp.Init(ini)

        # Alle Get Funktionen einmal aufrufen und so die Anzeige mit aktuellen Werten belegen.
        for item in self.mainTab:
            getattr(self, "_Get%s_fired" % item)()

    def _SetCenterFreq_fired(self):
        err, value = self.sp.SetCenterFreq(self.newCENTERFREQ)
        self.CENTERFREQ = value

    def _GetCenterFreq_fired(self):
        self.CENTERFREQ = self.sp.GetCenterFreq()[1]

    def _SetSpan_fired(self):
        err, value = self.sp.SetSpan(self.newSPAN)
        self.SPAN = value

    def _GetSpan_fired(self):
        self.SPAN = self.sp.GetSpan()[1]

    def _SetStartFreq_fired(self):
        err, value = self.sp.SetStartFreq(self.newSTARTFREQ)
        self.STARTFREQ = value

    def _GetStartFreq_fired(self):
        self.STARTFREQ = self.sp.GetStartFreq()[1]

    def _SetStopFreq_fired(self):
        err, value = self.sp.SetStopFreq(self.newSTOPFREQ)
        self.STOPFREQ = value

    def _GetStopFreq_fired(self):
        self.STOPFREQ = self.sp.GetStopFreq()[1]

    def _SetRBW_fired(self):
        err, value = self.sp.SetRBW(self.newRBW)
        self.RBW = value

    def _GetRBW_fired(self):
        self.RBW = self.sp.GetRBW()[1]

    def _SetVBW_fired(self):
        err, value = self.sp.SetVBW(self.newVBW)
        self.VBW = value

    def _GetVBW_fired(self):
        self.VBW = self.sp.GetVBW()[1]

    def _SetRefLevel_fired(self):
        err, value = self.sp.SetRefLevel(self.newREFLEVEL)
        self.REFLEVEL = value

    def _GetRefLevel_fired(self):
        self.REFLEVEL = self.sp.GetRefLevel()[1]

    def _SetAtt_fired(self):
        err, value = self.sp.SetAtt(self.newATT)
        self.ATT = value

    def _GetAtt_fired(self):
        self.ATT = self.sp.GetAtt()[1]

    def _SetAttMode_fired(self):
        err, value = self.sp.SetAttMode(self.newATTMODE)
        self.ATTMODE = value

    def _GetAttMode_fired(self):
        self.ATTMODE = self.sp.GetAttMode()[1]

    def _SetPreAmp_fired(self):
        err, value = self.sp.SetPreAmp(self.newPREAMP)
        self.PREAMP = value

    def _GetPreAmp_fired(self):
        self.PREAMP = self.sp.GetPreAmp()[1]

    def _SetDetector_fired(self):
        err, value = self.sp.SetDetector(self.newDETECTOR)
        self.DETECTOR = value

    def _GetDetector_fired(self):
        self.DETECTOR = self.sp.GetDetector()[1]

    def _SetTraceMode_fired(self):
        err, value = self.sp.SetTraceMode(self.newTRACEMODE)
        self.TRACEMODE = value

    def _GetTraceMode_fired(self):
        self.TRACEMODE = self.sp.GetTraceMode()[1]

    def _SetTrace_fired(self):
        err, value = self.sp.SetTrace(self.newTRACE)
        self.TRACE = value

    def _GetTrace_fired(self):
        self.TRACE = self.sp.GetTrace()[1]

    def _SetSweepCount_fired(self):
        err, value = self.sp.SetSweepCount(self.newSWEEPCOUNT)
        self.SWEEPCOUNT = value

    def _GetSweepCount_fired(self):
        self.SWEEPCOUNT = self.sp.GetSweepCount()[1]

    def _SetSweepTime_fired(self):
        err, value = self.sp.SetSweepTime(self.newSWEEPTIME)
        self.SWEEPTIME = value

    def _GetSweepTime_fired(self):
        self.SWEEPTIME = self.sp.GetSweepTime()[1]

    def _SetTriggerMode_fired(self):
        err, value = self.sp.SetTriggerMode(self.newTRIGGERMODE)
        self.TRIGGERMODE = value

    def _GetTriggerMode_fired(self):
        self.TRIGGERMODE = self.sp.GetTriggerMode()[1]

    def _SetTriggerDelay_fired(self):
        err, value = self.sp.SetTriggerDelay(self.newTRIGGERDELAY)
        self.TRIGGERDELAY = value

    def _GetTriggerDelay_fired(self):
        self.TRIGGERDELAY = self.sp.GetTriggerDelay()[1]

    def _SetSweepPoints_fired(self):
        err, value = self.sp.SetSweepPoints(self.newSWEEPPOINTS)
        self.SWEEPPOINTS = value

    def _GetSweepPoints_fired(self):
        self.SWEEPPOINTS = self.sp.GetSweepPoints()[1]

    # *********************************************************************
    #
    # Fenster erstellen:
    # **********************************************************************

    # mainTab in einen String schreiben.
    # Dieser String wird dann druch eval ausgewertet.
    items = ""
    for i in mainTab:
        items = "%s tuiapi.Group(" % (items)
        items = "%s tuiapi.Item('%s',label='Wert',style='readonly',width=70)," % (items, i.upper())
        items = "%s tuiapi.Item('new%s',label='Neu',width=60)," % (items, i.upper())
        items = "%s tuiapi.Item('Set%s',show_label=False)," % (items, i)
        items = "%s tuiapi.Item('Get%s',show_label=False)," % (items, i)
        items = "%s orientation='horizontal')," % (items)
    items = items[:-1]

    MAIN_grp = tuiapi.Group(eval(items),
                            label='Main')

    INI_grp = tuiapi.Group(tuiapi.Item('INI', style='custom', springy=True, width=500, height=200, show_label=False),
                           tuiapi.Item('Init', show_label=False),
                           label='Ini')

    plot = tapi.Instance(Plot)
    SPEC_grp = tuiapi.Group(
        tuiapi.Item('SPECTRUM', style='custom', springy=True, width=500, height=200, show_label=False),
        tuiapi.Item('GetSpectrum', show_label=False),
        label='Spectrum')

    PLOT_grp = tuiapi.Group(tuiapi.Item('plot', editor=ComponentEditor(), show_label=False),
                            tuiapi.Item('GetSpectrum', show_label=False),
                            label='Plot')

    traits_view = tuiapi.View(tuiapi.Group(INI_grp, MAIN_grp, SPEC_grp, PLOT_grp, layout='tabbed'),
                              title="Spectrumanalyer", buttons=[tuim.CancelButton])


def main():
    import sys
    ui = UI("")
    ui.configure_traits()
    sys.exit(0)


if __name__ == '__main__':
    main()
