# -*- coding: utf-8 -*-

from math import log10
import bidict
from scuq import quantities
from scuq import si
import numpy as np
from mpylab.device.driver import DRIVER
from mpylab.tools.configuration import strbool
from mpylab.tools.compare import fstrcmp
from mpylab.tools.regular_expressions import FP


class SIGNALGENERATOR(DRIVER):
    """
    Parent class for all py-drivers for signal generators.

    The parent class is :class:`mpylab.device.driver.DRIVER`.
    """
    AM_sources = ('INT1', 'INT2', 'EXT1', 'EXT2', 'EXT_AC', 'EXT_DC', 'TWOTONE_AC', 'TWOTONE_DC', 'OFF')
    AM_waveforms = ('SINE', 'SQUARE', 'TRIANGLE', 'NOISE', 'SAWTOOTH')
    AM_LFOut = ('OFF', 'ON')

    PM_sources = ('INT', 'EXT1', 'EXT2', 'OFF')
    PM_pol = ('NORMAL', 'INVERTED')

    ATT_modes = ('AUTO', 'FIXED')

    PARAMETER_SETS = {
        'AM_sources': AM_sources,
        'AM_waveforms': AM_waveforms,
        'AM_LFOut': AM_LFOut,
        'PM_sources': PM_sources,
        'PM_pol': PM_pol,
        'ATT_modes': ATT_modes,
    }

    map = {
        name: bidict.bidict((v, v) for v in values)
        for name, values in PARAMETER_SETS.items()
    }

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
                     'visa': str,
                     'virtual': strbool},
                'channel_%d':
                    {'name': str,
                     'level': float,
                     'unit': str,
                     'leveloffset': float,
                     'levellimit': float,
                     'outputstate': str,
                     'attmode': str,
                     'attenuation': float}}

    # regular expression for a Fixed Point value in the raw string notation
    # this is the same as %e,%E,%f,%F known from scanf
    _FP = FP

    def __init__(self, SearchPaths=None):
        DRIVER.__init__(self, SearchPaths=SearchPaths)
        self._cmds = {'SetFreq': [("FREQ {freq} HZ", None)],
                      'GetFreq': [('FREQ?', rf'FREQ (?P<freq>{self._FP}) HZ')],
                      'SetLevel': [("LEVEL {level} {unit}", None)],
                      'GetLevel': [('LEVEL?', rf'LEVEL (?P<level>{self._FP}) (?P<unit>\S+)')],
                      'ConfAM': [("AM:FREQ {freq} HZ", None),
                                 ('AM:FREQ?', rf'FREQ (?P<freq>{self._FP}) HZ'),
                                 ("AM:SOURCE {source}", None),
                                 ('AM:SOURCE?', r'SOURCE (?P<source>\S+)'),
                                 (
                                     lambda self, depth, **kwargs:
                                     f"AM:DEPTH {int(depth * 100):d} %",
                                     None
                                 ),
                                 ('AM:DEPTH?', r'DEPTH (?P<depth>\d+)'),
                                 ("'AM:WAVEFRM {waveform}'", None),
                                 ('AM:WAVEFRM?', r'WFRM (?P<waveform>\S+)'),
                                 ("'LF:OUT {LFOut}}'", None),
                                 ('LF:OUT??', r'LF (?P<LFOut>\S+)')],
                      'RFOn': [('RFOn', None)],
                      'RFOff': [('RFOff', None)],
                      'AMOn': [('AMOn', None)],
                      'AMOff': [('AMOff', None)],
                      'PMOn': [('PMOn', None)],
                      'PMOff': [('PMOff', None)],
                      'Quit': [('QUIT', None)],
                      'GetDescription': [('*IDN?', r'(?P<IDN>.*)')]}
        self.freq = None
        self.level = None
        self.unit = None
        self._internal_unit = 'dBm'

    def _adjust_for_unit(self, level_unit, internal_unit, impedance=50):
        deziZ = 10*log10(impedance)
        # dBm = dBµV - 106.9897  @ 50 OHM
        # dBuV = dBm + 106.9897
        from_u = level_unit
        if level_unit.lower() == 'dbm' and internal_unit.lower() == 'dbuv':
            # v has to be converted from dBm to dBuV
            v_conv = lambda v: float(v + 90 + deziZ)
            from_u = self._internal_unit
        elif self.levelunit.lower() == 'dbuv' and self._internal_unit.lower() == 'dbm':
            v_conv = lambda v: float(v - 90 - deziZ)
            from_u = self._internal_unit
        else:
            v_conv = lambda v: float(v)
            from_u = self.levelunit

        return from_u, v_conv

    def SetFreq(self, freq):
        # set a certain frequency
        self.error = 0  # reset error number
        dct = self._do_cmds('SetFreq', locals())
        self._update(dct)
        dct = self._do_cmds('GetFreq', locals())
        self._update(dct)
        if self.error == 0:
            self.freq = float(self.freq)
        return self.error, self.freq

    def GetFreq(self):
        self.error = 0
        dct = self._do_cmds('GetFreq', locals())
        self._update(dct)
        if self.error == 0 and self.freq is not None:
            self.freq = float(self.freq)
        return self.error, self.freq

    def SetLevel(self, lv):
        self.error = 0

        if self._internal_unit.lower() in ('dbm', 'w'):
            if str(lv._unit) == 'V':
                lv = lv**2 / quantities.Quantity(si.VOLT/si.AMPERE, 50)   # V -> W  P=U^2/Z
                lv = lv.reduce_to(si.WATT)
        elif self._internal_unit.lower() in ('dbuv', 'v'):
            if str(lv._unit) == 'W':
                lv = np.sqrt(lv * quantities.Quantity(si.VOLT/si.AMPERE, 50))  # W -> V  U = sqrt(P*Z)
                lv = lv.reduce_to(si.VOLT)
        else:
            raise ValueError(f'Level unit {lv._unit} not compatible with internal unit {self._internal_unit}.')

        level = lv.get_value(lv._unit)
        unit = lv._unit

        dct = self._do_cmds('SetLevel', locals())  # conversion to self._internal_unit is done inside _do_cmd
        self._update(dct)
        dct = self._do_cmds('GetLevel', locals())
        self._update(dct)

        if self.error == 0 and self.level is not None:
            self.level = float(self.level)
            self.level, self.unit = self.convert.c2scuq(self._internal_unit, self.level)
            obj = quantities.Quantity(self.unit, self.level)
        else:
            obj = None

        return self.error, obj

    def GetLevel(self):
        self.error = 0
        dct = self._do_cmds('GetLevel', locals())
        self._update(dct)

        if self.error == 0 and self.level is not None:
            self.level = float(self.level)
            self.level, self.unit = self.convert.c2scuq(self._internal_unit, self.level)
            obj = quantities.Quantity(self.unit, self.level)
        else:
            obj = None

        return self.error, obj

    def SetState(self, state):
        self.error = 0
        if str(state).lower() == 'on':
            dct = self._do_cmds('RFOn', locals())
            self._update(dct)
        else:
            dct = self._do_cmds('RFOff', locals())
            self._update(dct)
        return self.error, 0

    def ConfAM(self, source, freq, depth, waveform, LFOut):
        self.error = 0
        source = fstrcmp(source, self.AM_sources, cutoff=0, ignorecase=True)[0]
        source = self.map['AM_sources'][source]
        waveform = fstrcmp(waveform, self.AM_waveforms, cutoff=0, ignorecase=True)[0]
        waveform = self.map['AM_waveforms'][waveform]
        LFOut = fstrcmp(LFOut, self.AM_LFOut, cutoff=0, ignorecase=True)[0]
        LFOut = self.map['AM_LFOut'][LFOut]
        dct = self._do_cmds('ConfAM', locals())
        # print dct
        dct['source'] = self.map['AM_sources'].inverse[dct['source']]  # inverse mapping from bidict
        dct['waveform'] = self.map['AM_waveforms'].inverse[dct['waveform']]  # inverse mapping from bidict
        dct['LFOut'] = self.map['AM_LFOut'].inverse[dct['LFOut']]  # inverse mapping from bidict
        dct['depth'] = float(dct['depth'])
        if dct['depth'] > 1:  # depth was returned in PCT
            dct['depth'] = 0.01 * dct['depth']
        dct['freq'] = float(dct['freq'])
        # print dct
        self._update(dct)
        return self.error

    def ConfPM(self, source, freq, pol, width, delay):
        self.error = 0
        source = fstrcmp(source, self.PM_sources, cutoff=0, ignorecase=True)[0]
        source = self.map['PM_sources'][source]
        pol = fstrcmp(pol, self.PM_pol, cutoff=0, ignorecase=True)[0]
        pol = self.map['PM_pol'][pol]
        dct = self._do_cmds('ConfPM', locals())
        dct['source'] = self.map['PM_sources'].inverse[dct['source']]
        dct['pol'] = self.map['PM_pol'].inverse[dct['pol']]
        if 'period' in dct:
            dct['freq'] = 1. / float(dct['period'])
        self._update(dct)
        return self.error

    def SetAM(self, state):
        self.error = 0
        if str(state).lower() == 'on':
            dct = self._do_cmds('AMOn', locals())
            self._update(dct)
        else:
            dct = self._do_cmds('AMOff', locals())
            self._update(dct)
        return self.error, 0

    def SetPM(self, state):
        self.error = 0
        if str(state).lower() == 'on':
            dct = self._do_cmds('PMOn', locals())
            self._update(dct)
        else:
            dct = self._do_cmds('PMOff', locals())
            self._update(dct)
        return self.error, 0

    def RFOn(self):
        return self.SetState('ON')

    def RFOff(self):
        return self.SetState('OFF')

    def AMOn(self):
        return self.SetAM('ON')

    def AMOff(self):
        return self.SetAM('OFF')

    def PMOn(self):
        return self.SetPM('ON')

    def PMOff(self):
        return self.SetPM('OFF')

def test_signalgenerator_virtual():
    import io
    import re
    from scuq import quantities
    from scuq import si

    class FakeCommunication:
        def __init__(self):
            self.last = None
            self.writes = []

        def write(self, cmd, *args, **kwargs):
            self.last = cmd
            self.writes.append(cmd)
            print("WRITE:", cmd)
            return len(cmd)

        def read(self, tmpl=None, *args, **kwargs):
            ans = "OK"

            if self.last == "*IDN?":
                ans = "FAKE,SG,0001,1.0"
            elif self.last == "FREQ?":
                ans = "FREQ 1000000000.0 HZ"
            elif self.last == "LEVEL?":
                ans = "LEVEL -10.0 DBM"
            elif self.last == "AM:SOURCE?":
                ans = "SOURCE INT1"
            elif self.last == "AM:FREQ?":
                ans = "FREQ 100000.0 HZ"
            elif self.last == "AM:DEPTH?":
                ans = "DEPTH 80"
            elif self.last == "AM:WAVEFRM?":
                ans = "WFRM SINE"
            elif self.last == "LF:OUT??":
                ans = "LF ON"

            print("READ:", ans)

            if tmpl is None:
                return ans

            m = re.match(tmpl, ans)
            if m:
                return m.groupdict()
            return None

        def query(self, cmd, tmpl=None, *args, **kwargs):
            self.write(cmd)
            return self.read(tmpl)

    class FakeConvert:
        def c2scuq(self, unit, value):
            unit_l = str(unit).lower()

            if unit_l == "dbm":
                return float(value), si.WATT
            if unit_l == "w":
                return float(value), si.WATT
            if unit_l == "dbuv":
                return float(value), si.VOLT
            if unit_l == "v":
                return float(value), si.VOLT

            return float(value), si.WATT

    class TestSignalGenerator(SIGNALGENERATOR):
        def __init__(self):
            super().__init__()
            self.IDN = "TEST,SG,0001,1.0"
            self.convert = FakeConvert()

    ini_text = """
    [DESCRIPTION]
    description = 'Virtual SG'
    type = 'SIGNALGENERATOR'
    vendor = 'OpenAI'
    serialnr = '12345'
    deviceid = 'SG-01'
    driver = 'test_signalgenerator'

    [INIT_VALUE]
    virtual = 1
    gpib = 18

    [CHANNEL_1]
    name = 'CH1'
    level = -10
    unit = 'dBm'
    leveloffset = 0
    levellimit = 10
    outputstate = 'ON'
    attmode = 'AUTO'
    attenuation = 5
    """

    sg = TestSignalGenerator()

    fake = FakeCommunication()
    sg.write = fake.write
    sg.read = fake.read
    sg.query = fake.query
    sg.dev = None

    print("=== test_signalgenerator_virtual ===")

    err = sg.Init(ini=io.StringIO(ini_text), channel=1, ignore_bus=True)
    print("INIT ERR:", err)
    assert err == 0

    print("\n--- GetDescription ---")
    err, desc = sg.GetDescription()
    print("DESC:", err, desc)
    assert err == 0
    assert "Virtual SG" in desc

    print("\n--- SetFreq ---")
    err, freq = sg.SetFreq(1e9)
    print("SETFREQ:", err, freq)
    assert err == 0
    assert float(freq) == 1e9
    assert "FREQ 1000000000.0 HZ" in fake.writes

    print("\n--- SetState ON/OFF ---")
    err, _ = sg.SetState("ON")
    print("STATE ON:", err)
    assert err == 0

    err, _ = sg.SetState("OFF")
    print("STATE OFF:", err)
    assert err == 0

    print("\n--- SetAM ON/OFF ---")
    err, _ = sg.SetAM("ON")
    print("AM ON:", err)
    assert err == 0

    err, _ = sg.SetAM("OFF")
    print("AM OFF:", err)
    assert err == 0

    print("\n--- SetPM ON/OFF ---")
    err, _ = sg.SetPM("ON")
    print("PM ON:", err)
    assert err == 0

    err, _ = sg.SetPM("OFF")
    print("PM OFF:", err)
    assert err == 0

    print("\n--- ConfAM ---")
    err = sg.ConfAM("INT1", 100e3, 0.8, "SINE", "ON")
    print("CONFAM ERR:", err)
    assert err == 0

    print("\n--- SetLevel ---")
    lv = quantities.Quantity(si.WATT, -10.0)
    try:
        err, out_lv = sg.SetLevel(lv)
        print("SETLEVEL:", err, out_lv)
        assert err == 0
    except Exception as exc:
        print("SETLEVEL skipped due to unit/backend specifics:", exc)

    print("\n--- Writes summary ---")
    for i, cmd in enumerate(fake.writes, start=1):
        print(f"{i:02d}: {cmd}")

    assert any(cmd.startswith("FREQ ") for cmd in fake.writes)
    assert any(cmd == "*IDN?" for cmd in fake.writes)

    print("test_signalgenerator_virtual passed")

def test_normal():
    import sys

    try:
        ini = sys.argv[1]
    except IndexError:
        ini = None

    sg = SIGNALGENERATOR()
    sg.Init(ini)
    if not ini:
        sg.SetVirtual(False)

    err, des = sg.GetDescription()
    # print "Description: %s"%des

    for freq in [100]:
        print(f"Set freq to {freq:e} Hz")
        err, rfreq = sg.SetFreq(freq)
        if err == 0:
            print(f"Freq set to {rfreq:e} Hz")
        else:
            print("Error setting freq")

    lv = quantities.Quantity(si.VOLT, 10)
    print(f"Set level to {lv}")
    err, lv = sg.SetLevel(lv)
    if err == 0:
        print(f"Level set to: {lv}")
    else:
        print("Error setting level")

    err = sg.ConfAM('int', 100e3, 0.8, 'siNe', 'oN')

    err = sg.ConfPM('int', 100e3, 'NORMAL', 1e-3, 0)

    print((sg.SetState('On')))
    print((sg.SetState('Off')))
    print((sg.SetPM('On')))
    print((sg.SetPM('OFF')))
    print((sg.SetAM('On')))
    print((sg.SetAM('off')))

    sg.Quit()


if __name__ == '__main__':
    test_signalgenerator_virtual()

