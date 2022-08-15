import io

from scuq import *

from mpy.device import sg_rs_swm, amp_ifi_smx25
from mpy.tools.util import format_block

amp_ini = format_block("""
                         [description]
                         DESCRIPTION = SMX25
                         TYPE = AMPLIFIER
                         VENDOR = IFI
                         SERIALNR = 
                         DEVICEID = 
                         DRIVER =

                         [INIT_VALUE]
                         FSTART = 10e3
                         FSTOP = 1e9
                         FSTEP = 0.0
                         NR_OF_CHANNELS = 2
                         GPIB = 9
                         VIRTUAL = 0

                         [CHANNEL_1]
                         NAME = S21
                         UNIT = dB
                         INTERPOLATION = LOG
                         FILE = io.StringIO(format_block('''
                                                                FUNIT: Hz
                                                                UNIT: dB
                                                                ABSERROR: 0.5
                                                                10e6 50
                                                                1e9 50
                                                                '''))
                         [CHANNEL_2]
                         NAME = MAXIN
                         UNIT = dBm
                         INTERPOLATION = LOG
                         FILE = io.StringIO(format_block('''
                                                                FUNIT: Hz
                                                                UNIT: dBm
                                                                ABSERROR: 0.0
                                                                10e6 0
                                                                1e9 0
                                                                '''))
                         """)
amp_ini = io.StringIO(amp_ini)

sg_ini = format_block("""
                        [DESCRIPTION]
                        description: 'SWM'
                        type:        'SIGNALGENERATOR'
                        vendor:      'Rohde&Schwarz'
                        serialnr:
                        deviceid:
                        driver:

                        [Init_Value]
                        fstart: 100e6
                        fstop: 18e9
                        fstep: 1
                        gpib: 15
                        virtual: 0

                        [Channel_1]
                        name: RFOut
                        level: -100
                        unit: 'dBm'
                        outpoutstate: 0
                        """)
sg_ini = io.StringIO(sg_ini)

lv = quantities.Quantity(si.WATT, 1e-4)

sg = sg_rs_swm.SIGNALGENERATOR()
amp = amp_ifi_smx25.AMPLIFIER()
err = sg.Init(sg_ini)
err = amp.Init(amp_ini)
err, _ = sg.RFOn()
err, level = sg.SetLevel(lv)
while True:
    fr = float(eval(input("Freq / Hz: ")))
    if fr < 0:
        break
    sg.SetFreq(fr)
    amp.SetFreq(fr)
    # time.sleep(2)
err = sg.Quit()
err = amp.Quit()
