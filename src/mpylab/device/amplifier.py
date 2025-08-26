# -*- coding: utf-8 -*-

from mpylab.device.nport import NPORT  # parent class
from mpylab.tools.Configuration import fstrcmp  # fuzzy string compare


class AMPLIFIER(NPORT):
    """
    Child class for all py-drivers for amplifiers
    The parent class is NPORT
    
    This class is to be used for all passive amplifiers (no remote control). 
    The class adds the methods 'Operate', 'Standby', 'Pon', 'POff' and
    'SetState' to NPORT to complete the AMPLIFIER API.

    The class is base class for all drivers of remote controlled amplifies. 
    """
    STATES = ('Operate', 'Standby', 'POn', 'POff')
    _FP = r'[-+]?(\d+(\.\d*)?|\d*\.\d+)([eE][-+]?\d+)?'

    def __init__(self):
        NPORT.__init__(self)
        self._cmds = {'Pon': [("Set to POn", None)],
                      'Standby': [("Set to Standby", None)],
                      'Operate': [("Set to Operate", None)],
                      'POff': [("Set to POff", None)],
                      'GetDescription': [('*IDN?', r'(?P<IDN>.*)')]}

    def SetState(self, state):
        """
        Switch the state of the amplifier (in remote operation).

        state: string containig the state to switch to. The state is compared
        to the class variable STATES which is tuple of possible states.
        This comparison is made by meand of tools.Configuration.fstrcmp.

        Returns 0 if succesfull or an error code < 0.
        """
        state = fstrcmp(state, AMPLIFIER.STATES,  ignorecase=True)[0]
        # print state
        self.error = 0
        dct = self._do_cmds(state, locals())
        self._update(dct)
        return self.error

    def Operate(self):
        """
        Switch to mode 'Operate'.

        Calls SetState.
        """
        return self.SetState('Operate')

    def Standby(self):
        """
        Switch to mode 'Standby'.

        Calls SetState.
        """
        return self.SetState('Standby')

    def POn(self):
        """
        Switch to mode 'Power On'.

        Calls SetState.
        """
        return self.SetState('POn')

    def POff(self):
        """
        Switch to mode 'Power Off'.

        Calls SetState.
        """
        return self.SetState('POff')

    def Quit(self):
        self.error = NPORT.Quit(self)
        self.error += self.POff()
        return self.error


def main():
    import sys
    import io
    from mpylab.tools.util import format_block
    import scuq

    try:
        ini = sys.argv[1]
    except IndexError:
        ini = format_block("""
                         [description]
                         DESCRIPTION = Test Amplifier
                         TYPE = AMPLIFIER
                         VENDOR = HGK
                         SERIALNR = 
                         DEVICEID = 
                         DRIVER =

                         [INIT_VALUE]
                         FSTART = 80e6
                         FSTOP = 1e9
                         FSTEP = 0.0
                         NR_OF_CHANNELS = 2
                         VIRTUAL = 0

                         [CHANNEL_1]
                         NAME = S21
                         UNIT = dB
                         INTERPOLATION = LOG
                         FILE = io.StringIO(format_block('''
                                                                FUNIT: Hz
                                                                UNIT: dB
                                                                ABSERROR: 0.5
                                                                80e6 50
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
                                                                80e6 0
                                                                1e9 0
                                                                '''))
                         """)
        ini = io.StringIO(ini)

    amp = AMPLIFIER()
    err = amp.Init(ini)
    amp.POn()
    amp.Operate()
    ctx = scuq.ucomponents.Context()
    for freq in (80e6, 500e6, 1e9):
        amp.SetFreq(freq)
        err, uq = amp.GetData(what='S21')
        val, unc, unit = ctx.value_uncertainty_unit(uq)
        print((freq, uq, val, unc, unit))
    amp.Standby()
    amp.Quit()


if __name__ == '__main__':
    main()
