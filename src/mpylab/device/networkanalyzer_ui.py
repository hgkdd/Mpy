# -*- coding: utf-8 -*-
# Es wird benötigt enthought.chaco und enthought.enable

import io

import traits.api as tapi
from traits.etsconfig.api import ETSConfig

ETSConfig.toolkit = "wx"
import traitsui.api as tuiapi
from chaco.api import Plot, ArrayPlotData
from enable.component_editor import ComponentEditor

from mpylab.tools.util import format_block
from mpylab.device.device import CONVERT

import numpy as np

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
                gpib: 18
                virtual: 0

                [Channel_1]
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
std_ini = io.StringIO(std_ini)


class UI(tapi.HasTraits):
    """
    Diese Klasse ist die Super Klasse für alle grafischen Test-Oberflächen für 
    Networkanalyer.
    
    In dieser Klasse werden Buttons und Felder definiert die 
    bei allen Networkanalyer identisch sind, wie z.B. das Plot Fenster.
    
    In den konkreten Implementierungen der Driver muss von dieser Klasse eine
    weitere UI-Klasse abgeleitet werden um die restlichen Buttons und Felder zu
    erstellen. Den Hauptteil der Arbeit übernimmt dabei die Metaklasse "Meta_ui"
    die Buttons und Felder anhand des _commands-Dict und _cmds-Dict der Driver-Klasse bzw.
    -Superklasse erstellt.
    
    Diese Metaklasse erstellt auch das eigentliche Fenster mit Taps in dem alle Buttons usw. 
    angeordnet werden. 
    
    Damit die Metaklasse einwandfrei arbeiten kann, dürfen in dieser Klasse nur 
    sogenannte tuiapi.Group (das sind Taps) erstellt werden. Diese müssen wiederrum in einem Dict
    mit dem Namen "GROUPS" gespeichert werden. Wobei folgende Konvention einzuhalten ist:
    
    GROUPS={'Name des Taps' : tuiapi.Group(...)}
    
    """

    Init = tapi.Button()
    INI = tapi.Str()
    int_unit = 'dBm'

    GetSpectrum = tapi.Button("GetSpectrum")
    SPECTRUM = tapi.Str()
    power = ()

    def __init__(self, instance, ini=None):
        # Wenn keine ini übergeben wurde wird die Standard ini verwendet.
        self.dv = instance
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

        if self.dv.GetSweepType()[1] == 'LOGARITHMIC':
            self.plot.index_scale = 'log'
        else:
            self.plot.index_scale = 'linear'

        self.power = self.dv.GetSpectrum()[1]
        x = np.array(self.power[0])
        y = np.array(self.power[1])
        self.plotdata.set_data('x', x)
        self.plotdata.set_data('y', y)
        self.plot.request_redraw()

        self.SPECTRUM = str(self.power[0]) + "\n\n\n" + str(self.power[1])

    # *********************************************************************
    #
    # Fenster erstellen:
    # **********************************************************************

    plot = tapi.Instance(Plot)

    GROUPS = {'Spectrum': tuiapi.Group(
        tuiapi.Item('SPECTRUM', style='custom', springy=True, width=500, height=200, show_label=False),
        tuiapi.Item('GetSpectrum', show_label=False),
        label='Spectrum'),

              'Plot': tuiapi.Group(tuiapi.Item('plot', editor=ComponentEditor(), show_label=False),
                                   tuiapi.Item('GetSpectrum', show_label=False),
                                   label='Plot')}
