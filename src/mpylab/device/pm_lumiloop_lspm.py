# -*- coding: utf-8 -*-
import sys
import io
import time
import struct
import itertools

from scuq import si, quantities, ucomponents
import numpy as np

from mpylab.device.powermeter import POWERMETER as PMMTR

def dBm2W(vals):
    watts = np.power(10, 0.1*np.asarray(vals))*0.001
    return watts

def linav_dB(dbvals):
    """
    Input: sequence of dB-scaled values
    Output: dB-scaled lin-average of the input sequence

    Example: linav_dB([0,-10]) -> -0.301
    """
    linmean = np.mean(np.power(10., 0.1 * np.asarray(dbvals)))
    return 10 * np.log10(linmean)


def linav_lin(linvals):
    """
    Input: sequence of lin-scaled values
    Output: lin-scaled lin-average of the input sequence

    Example: linav_lin([0,-10]) -> -5
    """
    linmean = np.mean(np.asarray(linvals))
    return linmean


class POWERMETER(PMMTR):
    conftmpl = PMMTR.conftmpl
    conftmpl['init_value']['visa'] = str
    conftmpl['init_value']['mode'] = str
    conftmpl['init_value']['mfreq'] = float
    conftmpl['init_value']['channels'] = int

    instances = {}  # dict to hold instances (channels) of this driver
    main_instance = None
    npm = 1
    data = []

    def __init__(self):
        PMMTR.__init__(self)
        self._internal_unit = 'dBm'
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

        if POWERMETER.main_instance is None:     # first access
            self.error = PMMTR.Init(self, ini, channel)
            self.visa = self.conf['init_value']['visa']
            self.mfreq = self.conf['init_value']['mfreq']
            self.lmode = self.conf['init_value']['mode'].split(',')[0]
            self.hmode = self.conf['init_value']['mode'].split(',')[1]
            self.virtual = self.conf['init_value'].get('virtual', False)
            POWERMETER.conf = self.conf.copy()   # make a copy of conf dict for the whole class
        else:  # copy from main instance
            self.error = POWERMETER.main_instance.error
            self.visa = POWERMETER.main_instance.visa
            self.mfreq = POWERMETER.main_instance.mfreq
            self.lmode = POWERMETER.main_instance.lmode
            self.hmode = POWERMETER.main_instance.hmode
            self.virtual = POWERMETER.main_instance.virtual
            self.conf = POWERMETER.conf.copy()  # copy class conf to instance

        if self.visa and not self.virtual:  # ignore virtual instruments
            key = self._hash()  # here: visa_ch
            if key in POWERMETER.instances:
                raise RuntimeWarning("Multi Channel Field Probe: Instance already in use: %s" % key)

            POWERMETER.instances.setdefault(key, self)  # register this instance
        if len(POWERMETER.instances.keys()) == 1:
            # in this case this is the first instance  -> mark it as main instance
            self.is_main_instance = True
            POWERMETER.main_instance = self
        else:
            self.is_main_instance = False

        if self.is_main_instance:
            ans = self.query(':syst:cou?', r'(?P<npm>\d)')   # Number of powermeters (typical:1)
            POWERMETER.npm = int(ans['npm'])
            ans = self.query(':syst:chan?', r'(?P<nch>\d)')   # Number of channels (typical:1)
            POWERMETER.nch = int(ans['nch'])

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
        prb_number, ci_number, prb_version, sample_count = struct.unpack_from('<IIfI', buffer, offset=offset)
        if sample_count == 0:
            P1, P2, P3 = (None, None, None)
            return P1, P2, P3
        offset += 4*4
        waveform_count, = struct.unpack_from('<I', buffer, offset=offset)
        chunck_size = (sample_count*waveform_count)*4
        start = offset + 4
        end = start + chunck_size
        unpack_iter = struct.iter_unpack('<f', buffer[start:])
        P1 = [p[0] for p in itertools.islice(unpack_iter, sample_count)]
        P2 = [p[0] for p in itertools.islice(unpack_iter, sample_count)]
        P3 = [p[0] for p in itertools.islice(unpack_iter, sample_count)]
        return P1, P2, P3

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
        for p in range(2, self.npm+1):
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
        Ps = []
        err = self.write(':TRIG:WAV:P:BINR? 0')
        ans = self.dev.read_bytes(4)
        bin_block_size, = struct.unpack_from('<I', ans)  # number of bytes in the binary block
        for prb in range(self.npm): # loop over all probes
            ans = self.dev.read_bytes(int(bin_block_size / self.npm)) # read the whole data for this probe
            P = self._parse_wav_bin_red(ans)
            Ps.append(P)
        self.dev.read_bytes(2)  # cr lf
        err = self.write(':TRIG:CL 0')
        return err, Ps

    # def _float_GetData(self):
    #     cmd = ":meas:all?"
    #     tmpl = r"(?P<x>[\d.]+),(?P<y>[\d.]+),(?P<z>[\d.]+),(?P<m>[\d.]+)"
    #     ans = self.query(cmd, tmpl)
    #     return tuple(float(ans[_k]) for _k in ('x', 'y', 'z', 'm') )

    def GetData(self):
        self.error = 0
        if self.is_main_instance:
            # relative error for single measured point
            relerr = 0.047   # 0.2 dB
            err, ps  = self._float_force_trigger_GetData(forceTRIG_CL=True)
            sqrt_n = np.sqrt(len(ps[0]))
            relerr /= sqrt_n
            #exs_av = []
            #eys_av = []
            #ezs_av = []
            data = []
            for p in range(self.npm):
                data.append([])
                for ch in range(3):
                    watts = dBm2W(ps[p][ch])
                    aver = linav_lin(watts)

                    data[p].append(quantities.Quantity(si.WATT,
                                                  ucomponents.UncertainInput(aver, aver * relerr)))
            POWERMETER.data = data
        data = POWERMETER.data[0][self.ch-1]
        return self.error, data

    def GetDataNB(self, retrigger=False):
        return self.GetData()

    def Quit(self):
        self.error = 0
        return self.error

def main2():
    from mpylab.tools.util import format_block
    import numpy as np

    try:
        ini = sys.argv[1]
    except IndexError:
        ini = format_block("""
                        [DESCRIPTION]
                        description: 'LSPM 2.0'
                        type:        'POWERMETER'
                        vendor:      'LUMILOOP'
                        serialnr:
                        deviceid:
                        driver:

                        [Init_Value]
                        fstart: 9e3
                        fstop: 26e9
                        fstep: 0
                        visa: TCPIP::127.0.0.1::10001::SOCKET
                        mode: 2,0
                        mfreq: 700e6
                        virtual: 0
                        channels = 3

                        [Channel_1]
                        name: PFwd
                        unit: dBm

                        [Channel_2]
                        name: PBwd
                        unit: dBm

                        [Channel_3]
                        name: PRef
                        unit: dBm
                        """)
    devs = {}
    devs[0] = POWERMETER()
    devs[0].Init(ini=io.StringIO(ini), channel=1)
    err, des = devs[0].GetDescription()
    npm = devs[0].npm
    nch = devs[0].nch
    for ch in range(1, nch):
        devs[ch] = POWERMETER()
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

        for dv in [devs[k] for k in range(npm*3)]:
            err, ff = dv.SetFreq(freq)
            oldfreq = ff
            # print(f"Frequency set to: {ff} Hz")
            err, dat = dv.GetData()
            print(dat)

    for dv in [devs[k] for k in range(npm)]:
        dv.Quit()


if __name__ == '__main__':
    main2()
