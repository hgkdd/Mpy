# -*- coding: utf-8 -*-
import sys
import io
import time
import struct
import itertools

from scuq import si, quantities, ucomponents
import numpy as np

from mpylab.device.fieldprobe import FIELDPROBE as FLDPRB
# from test.test_interpol import freqs


class FIELDPROBE(FLDPRB):
    conftmpl = FLDPRB.conftmpl
    conftmpl['init_value']['visa'] = str
    conftmpl['init_value']['mode'] = str
    conftmpl['init_value']['mfreq'] = float
    conftmpl['init_value']['channels'] = int

    instances = {}  # dict to hold instances (channels) of this driver
    main_instance = None
    nprb = 1
    data = []

    def __init__(self):
        FLDPRB.__init__(self)
        self._internal_unit = si.VOLT / si.METER
        self.freq = None
        self._cmds = {'Zero': [],
                      'Trigger': [],
                      'Quit': [(':SYST:LAS:EN 0,0', None)],
                      'GetDescription': [('*IDN?', r'(?P<IDN>.*)')]}
        self.term_chars = '\r\n'
        self.error = None
        self.mode = None
        self.LastData_ns = None
        self.LastData = None

    def Init(self, ini=None, channel=None):
        self.ch = channel
        self.mode = None

        if FIELDPROBE.main_instance is None:     # first access
            self.error = FLDPRB.Init(self, ini, channel)
            self.visa = self.conf['init_value']['visa']
            self.mfreq = self.conf['init_value']['mfreq']
            self.lmode = self.conf['init_value']['mode'].split(',')[0]
            self.hmode = self.conf['init_value']['mode'].split(',')[1]
            self.virtual = self.conf['init_value'].get('virtual', False)
            FIELDPROBE.conf = self.conf.copy()   # make a copy of conf dict for the whole class
        else:  # copy from main instance
            self.error = FIELDPROBE.main_instance.error
            self.visa = FIELDPROBE.main_instance.visa
            self.mfreq = FIELDPROBE.main_instance.mfreq
            self.lmode = FIELDPROBE.main_instance.lmode
            self.hmode = FIELDPROBE.main_instance.hmode
            self.virtual = FIELDPROBE.main_instance.virtual
            self.conf = FIELDPROBE.conf.copy()  # copy class conf to instance


        if self.visa and not self.virtual:  # ignore virtual instruments
            key = self._hash()  # here: visa_ch
            if key in FIELDPROBE.instances:
                raise RuntimeWarning("Multi Channel Field Probe: Instance already in use: %s" % key)

            FIELDPROBE.instances.setdefault(key, self)  # register this instance
        if len(FIELDPROBE.instances.keys()) == 1:
            # in this case this is the first instance  -> mark it as main instance
            self.is_main_instance = True
            FIELDPROBE.main_instance = self
        else:
            self.is_main_instance = False

        if self.is_main_instance:
            ans = self.query(':syst:cou?', r'(?P<nprb>\d)')   # Number of probes
            FIELDPROBE.nprb = int(ans['nprb'])

            # wait for laser ready
            self.write(':syst:las:en 1,0')
            self.setMode(self.lmode)
            self._conf_trigger()
        return self.error

    def _hash(self):
        return "%s_%s" % (self.visa, self.ch)

    def wait_for_laser_ready(self):
        if not self.is_main_instance:
            return
        while True:
            # ans = self.query(':syst:las:rdy?', r'(?P<laser>\d)')
            ans = self.query(':meas:rdy? 0', None)  # waits for laser ready AND cal data present
            if all(rdy == 1 for rdy in map(int, ans.split(','))):
                break
            time.sleep(.1)
        self.LastData_ns = time.time_ns()

    def setMode(self, mode):
        if not self.is_main_instance:
            return self.main_instance.mode
        mode = int(mode)

        if self.mode == mode:
            return mode

        if 0 <= mode <= 8:
            self.write(f':syst:freq {self.mfreq},0')  # to prevent errors in tcp server -> set a freq valid for both modes
            self.write(f':syst:mod {mode},0')
            while True:
                ans = self.query(f':syst:mod? 0', None)
                modes = map(int, ans.split(','))
                if all(m == mode for m in modes):
                    break
        time.sleep(0.1)
        self.wait_for_laser_ready()
        # print('Laser is ready')
        self.mode = mode
        # get effective sample rate
        ans = self.query(':SYST:ESRA? 0')
        self.esra = int(ans.split(',')[0])  # take the first; all should be equal
        return mode

    def GetFreq(self):
        self.error = 0
        if not self.is_main_instance:
            return self.error, self.main_instance.freq
        ans = self.query(":syst:freq? 0", None)
        if ans:
            freqs = [float(f) for f in ans.split(',')]
            if len(set(freqs)) == 1:
                freq = freqs[0]
        else:
            self.error = 1
            freq = None
        self.freq = freq
        return self.error, self.freq

    def SetFreq(self, freq):
        self.error = 0
        #self.setMode(1)

        if freq < self.mfreq:
            self.mode = self.setMode(self.lmode)
        else:
            self.mode = self.setMode(self.hmode)
        if self.is_main_instance:
            self.write(f':syst:freq {freq},0')
        return self.GetFreq()

    def _parse_wav_bin_red(self, buffer):
        offset = 0
        ci_number, prb_number, prb_version, sample_count = struct.unpack_from('<IIfI', buffer, offset=offset)
        if sample_count == 0:
            Ex, Ey, Ez = (None, None, None)
            return Ex, Ey, Ez
        offset += 4*4
        waveform_count, = struct.unpack_from('<I', buffer, offset=offset)
        chunck_size = (sample_count*waveform_count)*4
        start = offset + 4
        end = start + chunck_size
        unpack_iter = struct.iter_unpack('<f', buffer[start:])
        Ex = [e[0] for e in itertools.islice(unpack_iter, sample_count)]
        Ey = [e[0] for e in itertools.islice(unpack_iter, sample_count)]
        Ez = [e[0] for e in itertools.islice(unpack_iter, sample_count)]
        return Ex, Ey, Ez

    def _wait_for_trigger_state(self, state=None, timeout=10):
        if not self.is_main_instance:
            return
        err = 0
        err_state_unknown = -(1<<0)
        err_timeout = -(1<<1)
        state = state.upper()
        if state in ('IDLE', 'ARM', 'ARMED', 'TRIGGERED', 'DONE'):
            ts = time.time_ns()
            while True:
                ans = self.query(':TRIG:STAT? 0,0')
                if all(s == state for s in ans.split(',')):
                    break
                tnow = time.time_ns()
                if tnow - ts > timeout*1e9:
                    err += err_timeout
                    break
        else:
            err += err_state_unknown
        return err

    def _conf_trigger(self, begin=0,
                      length=1000,
                      tpoints=1,
                      forceTRIG_CL=True,
                      timeout=10,
                      source='SOFT' ):
        err = 0
        if not self.is_main_instance:
            return err
        if forceTRIG_CL:
            err = self.write(':TRIG:CL')
        # wait for trigger is IDLE
        err = self._wait_for_trigger_state(state='IDLE', timeout=timeout)
        if err < 0:
            return err
        """
        Strategy to have synchronized waveforms from all probes:
        First Probe: 
        trigger mode SINGLE (GUI)
        trigger source SOFT
        BNC output ENABLED
        BNC polarity RISING
        RJ45 output ENABLED
        RJ45 polarity RISING
        Other Probes:
        trigger mode NORMAL (GUI)
        trigger source RJ45 RISING
        BNC output OFF
        RJ45 output OFF
        """
        err = self.write(f':TRIG:SOUR {source},1')
        err = self.write(f':TRIG:OUT 1,1')
        err = self.write(f':TRIG:INV 0,1')
        err = self.write(f':TRIG:BPOUT 1,1')
        err = self.write(f':TRIG:BPINV 0,1')
        for p in range(2, self.nprb+1):
            err = self.write(f':TRIG:SOUR EXT2,{p}')
            err = self.write(f':TRIG:OUT 0,{p}')
            err = self.write(f':TRIG:INV 0,{p}')
            err = self.write(f':TRIG:BPOUT 0,{p}')
            err = self.write(f':TRIG:BPINV 0,{p}')

        err = self._wait_for_trigger_state(state='IDLE', timeout=timeout)

        # for all probes
        err = self.write(f':TRIG:BEG {begin},0')
        #err = self._wait_for_trigger_state(state='IDLE', timeout=timeout)
        err = self.write(f':TRIG:LEN {length},0')
        #err = self._wait_for_trigger_state(state='IDLE', timeout=timeout)
        err = self.write(f':TRIG:POIN {tpoints},0')
        err = self._wait_for_trigger_state(state='IDLE', timeout=timeout)
        self.begin = begin
        self.length = length
        self.tpoints = tpoints
        return err

    def _float_force_trigger_GetData(self, forceTRIG_CL=False, timeout=10):
        if not self.is_main_instance:
            return None

        while True:
            err = 0
            if forceTRIG_CL:
                err = self.write(':TRIG:CL 0')
            # wait for trigger is IDLE
            err = self._wait_for_trigger_state(state='IDLE', timeout=timeout)
            if err < 0:
                continue
            # arm all probes
            err = self.write(f':TRIG:ARM 0')
            err = self._wait_for_trigger_state(state='ARMED', timeout=timeout)
            if err < 0:
                continue
            # force trig (only first probe; other are triggerd by first probe via RJ45)
            err = self.write(':TRIG:FOR 0')
            # wait for trigger DONE
            err = self._wait_for_trigger_state(state='DONE', timeout=timeout)
            if err < 0:
                continue
            break
        #ans = self.query(':TRIG:WAV:E:X?')
        #Ex = [float(s) for s in ans.split(',')]
        #ans = self.query(':TRIG:WAV:E:Y?')
        #Ey = [float(s) for s in ans.split(',')]
        #ans = self.query(':TRIG:WAV:E:Z?')
        #Ez = [float(s) for s in ans.split(',')]
        #Ex = Ex[self.begin:]
        #Ey = Ey[self.begin:]
        #Ez = Ez[self.begin:]
        # lists for field values of the probes
        Exs = []
        Eys = []
        Ezs = []
        err = self.write(':TRIG:WAV:E:BINR? 0')
        ans = self.dev.read_bytes(4)
        bin_block_size, = struct.unpack_from('<I', ans)  # number of bytes in the binary block
        for prb in range(self.nprb): # loop over all probes
            ans = self.dev.read_bytes(int(bin_block_size / self.nprb)) # read the whole data for this probe
            Ex, Ey, Ez = self._parse_wav_bin_red(ans)
            Exs.append(Ex)
            Eys.append(Ey)
            Ezs.append(Ez)
        self.dev.read_bytes(2)  # cr lf
        err = self.write(':TRIG:CL 0')
        return 0, Exs, Eys, Ezs

    # def _float_GetData(self):
    #     cmd = ":meas:all?"
    #     tmpl = r"(?P<x>[\d.]+),(?P<y>[\d.]+),(?P<z>[\d.]+),(?P<m>[\d.]+)"
    #     ans = self.query(cmd, tmpl)
    #     return tuple(float(ans[_k]) for _k in ('x', 'y', 'z', 'm') )

    def GetData(self):
        self.error = 0
        if self.is_main_instance:
            # relative error for single measured point
            if self.freq <= 30e6:
                relerr = 0.072  # 0.6 dB
            elif 30e6 < self.freq <= 1e9:
                relerr = 0.12  # 1 dB
            else:
                relerr = 0.17  # 1.4 dB
            err, exs, eys, ezs  = self._float_force_trigger_GetData(forceTRIG_CL=True)
            sqrt_n = np.sqrt(len(exs[0]))
            relerr /= sqrt_n
            #exs_av = []
            #eys_av = []
            #ezs_av = []
            data_x = []
            data_y = []
            data_z = []
            for p in range(self.nprb):
                #exs_av.append(np.average(exs[p]))
                #eys_av.append(np.average(eys[p]))
                #ezs_av.append(np.average(ezs[p]))
                data_x.append(quantities.Quantity(self._internal_unit,
                                                  ucomponents.UncertainInput(np.average(exs[p]), np.average(exs[p])* relerr)))
                data_y.append(quantities.Quantity(self._internal_unit,
                                                  ucomponents.UncertainInput(np.average(eys[p]), np.average(eys[p]) * relerr)))
                data_z.append(quantities.Quantity(self._internal_unit,
                                                  ucomponents.UncertainInput(np.average(ezs[p]), np.average(ezs[p]) * relerr)))

            FIELDPROBE.data = [data_x, data_y, data_z]
        data = [FIELDPROBE.data[0][self.ch-1], FIELDPROBE.data[1][self.ch-1], FIELDPROBE.data[2][self.ch-1]]
        return self.error, data

    def GetDataNB(self, retrigger=False):
        return self.GetData()

    def GetWaveform(self, forceTRIG_CL=True):
        while True:
            err, Ex, Ey, Ez = self._float_force_trigger_GetData(forceTRIG_CL=forceTRIG_CL)
            if err == 0:
                break
        dt = 1. / self.esra
        ts = np.fromiter((i * dt * 1e3 for i,_ in enumerate(Ex[0])), float, count=-1)  # t in ms
        return err, ts, Ex[0], Ey[0], Ez[0]

    def GetBatteryState(self):
        self.error = 0
        return self.error, 1.0

    def Quit(self):
        if self.is_main_instance:
            FIELDPROBE.instances = {}  # dict to hold instances (channels) of this driver
            FIELDPROBE.main_instance = None
            FIELDPROBE.nprb = 1
            FIELDPROBE.data = None
        self.error = 0
        return self.error

def main2():
    from mpylab.tools.util import format_block
    import numpy as np

    try:
        ini = sys.argv[1]
    except IndexError:
        ini_rc = format_block("""
                        [DESCRIPTION]
                        description: 'LSProbe 2.0'
                        type:        'FIELDPROBE'
                        vendor:      'LUMILOOP'
                        serialnr:
                        deviceid:
                        driver:

                        [Init_Value]
                        fstart: 9e3
                        fstop: 18e9
                        fstep: 0
                        visa: TCPIP::127.0.0.1::10000::SOCKET
                        mode: 2,0
                        mfreq: 700e6
                        virtual: 0
                        channels = 4

                        [Channel_1]
                        name: EField
                        unit: Voverm

                        [Channel_2]
                        name: EField
                        unit: Voverm

                        [Channel_3]
                        name: EField
                        unit: Voverm

                        [Channel_4]
                        name: EField
                        unit: Voverm
                        """)
    ini_gtem = format_block("""
                    [DESCRIPTION]
                    description: 'LSProbe 1.2'
                    type: FIELDPROBE
                    vendor: LUMILOOP
                    serialnr:
                    deviceid:
                    driver: 
                    
                    [Init_Value]
                    fstart: 10e3
                    fstop: 8.2e9
                    fstep: 0
                    visa: TCPIP0::192.168.88.3::10000::SOCKET
                    mode: 0,0
                    mfreq: 8.2e9
                    virtual: 0
                    channels = 1
                    
                    [Channel_1]
                    name: EField
                    unit: Voverm    
                    """)
    ini = ini_gtem
    devs = {}
    devs[0] = FIELDPROBE()
    devs[0].Init(ini=io.StringIO(ini), channel=1)
    err, des = devs[0].GetDescription()
    nprb = devs[0].nprb
    for ch in range(1, nprb):
        devs[ch] = FIELDPROBE()
        devs[ch].Init(ini=io.StringIO(ini), channel=ch+1)

    oldfreq = None
    while True:
        freq = input("Frequency / Hz: ")
        if oldfreq and freq == '':
            freq = oldfreq
        elif freq in 'qQ':
                break
        else:
            freq = float(freq)
            if freq <= 0:
                break

        for dv in [devs[k] for k in range(nprb)]:
            err, ff = dv.SetFreq(freq)
            oldfreq = ff
            # print(f"Frequency set to: {ff} Hz")
            err, dat = dv.GetData()
            print(dat)

    for dv in [devs[k] for k in range(nprb)]:
        dv.Quit()


if __name__ == '__main__':
    main2()
