# -*- coding: utf-8 -*-
import sys
import io
import time
import struct
import itertools

from scuq import si, quantities, ucomponents
import numpy as np

from mpy.device.fieldprobe import FIELDPROBE as FLDPRB
# from test.test_interpol import freqs


class FIELDPROBE(FLDPRB):
    conftmpl = FLDPRB.conftmpl
    conftmpl['init_value']['visa'] = str
    conftmpl['init_value']['mode'] = str
    conftmpl['init_value']['mfreq'] = float

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
        self.error = FLDPRB.Init(self, ini, channel)
        self.mfreq = self.conf['init_value']['mfreq']
        self.lmode = self.conf['init_value']['mode'].split(',')[0]
        self.hmode = self.conf['init_value']['mode'].split(',')[1]
        self.mode = None
        ans = self.query(':syst:cou?', r'(?P<nprb>\d)')   # Number of probes
        self.nprb = int(ans['nprb'])

        # wait for laser ready
        self.write(':syst:las:en 1,0')
        self.setMode(self.lmode)
        self._conf_trigger()
        return self.error

    def wait_for_laser_ready(self):
        while True:
            # ans = self.query(':syst:las:rdy?', r'(?P<laser>\d)')
            ans = self.query(':meas:rdy? 0', None)  # waits for laser ready AND cal data present
            if all(rdy == 1 for rdy in map(int, ans.split(','))):
                break
            time.sleep(.1)
        self.LastData_ns = time.time_ns()

    def setMode(self, mode):
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
            err = self.write(':TRIG:FOR')
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
        return err, Exs, Eys, Ezs

    # def _float_GetData(self):
    #     cmd = ":meas:all?"
    #     tmpl = r"(?P<x>[\d.]+),(?P<y>[\d.]+),(?P<z>[\d.]+),(?P<m>[\d.]+)"
    #     ans = self.query(cmd, tmpl)
    #     return tuple(float(ans[_k]) for _k in ('x', 'y', 'z', 'm') )

    def GetData(self):
        self.error = 0
        # relative error for single measured point
        if self.freq <= 30e6:
            relerr = 0.072  # 0.6 dB
        elif 30e6 < self.freq <= 1e9:
            relerr = 0.12  # 1 dB
        else:
            relerr = 0.17  # 1.4 dB
        err, exs, eys, ezs  = self._float_force_trigger_GetData()
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

            data = [data_x, data_y, data_z]
        return self.error, data

    def GetDataNB(self, retrigger=False):
        return self.GetData()

    def GetWaveform(self, forceTRIG_CL=True):
        while True:
            err, data = self._float_force_trigger_GetData(forceTRIG_CL=forceTRIG_CL)
            if err == 0 and data is not None:
                break
        Ex, Ey, Ez = data
        dt = 1. / self.esra
        ts = np.fromiter((i * dt * 1e3 for i,_ in enumerate(Ex)), float, count=-1)  # t in ms
        return err, ts, Ex, Ey, Ez


def main():
    from mpy.tools.util import format_block
    import numpy as np
    import matplotlib.pyplot as plt
    from mpy.tools.sin_fit import fit_sin

    try:
        ini = sys.argv[1]
    except IndexError:
        ini = format_block("""
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

                        [Channel_1]
                        name: EField
                        unit: Voverm
                        """)
        ini = io.StringIO(ini)
    dev = FIELDPROBE()

    dev.Init(ini=ini, channel=1)
    err, des = dev.GetDescription()

    dev.SetFreq(1e9)

    err, Exs, Eys, Ezs = dev._float_force_trigger_GetData(forceTRIG_CL=True)
    dt = 1./dev.esra
    ts = np.array([i*dt*1e3 for i in range(len(Exs[0]))]) # t in ms

    #fitdata = fit_sin(ts, Exs[0])
    #freqAM = fitdata['freq']
    #meanAM = fitdata['offset']
    #modAM = abs(fitdata['amp']) / meanAM * 100

    plt.ion()
    fig, axs = plt.subplots(dev.nprb, 1, sharex=True, sharey=True, figsize=(10,10))
    lineEx=[[] for i in range(dev.nprb)]
    lineEy=[[] for i in range(dev.nprb)]
    lineEz=[[] for i in range(dev.nprb)]
    for i, ax in enumerate(axs.flatten()):
        lineEx[i], = ax.plot(ts, Exs[i], marker=',', label=f'p: {i+1}, x')
        lineEy[i], = ax.plot(ts, Eys[i], marker=',', label=f'p: {i+1}, y')
        lineEz[i], = ax.plot(ts, Ezs[i], marker=',', label=f'p: {i+1}, z')
        # lineSin, = ax.plot(ts, fitdata['fitfunc'](ts), ls='-')
        ax.set_xlabel("Time in ms")
        ax.set_ylabel("E-Field in V/m")
        ax.grid()
        ax.legend(loc='upper left')
    #plt.title(f"E-Field: {meanAM:.2f} V/m, AM-Freq: {freqAM:.2f} kHz, AM-Depth: {modAM:.2f} %")
    #plt.grid()
    plt.tight_layout()
    plt.show()
    # return
    while True:
        # freq = input("Frequency / Hz: ")
        # if freq in 'qQ':
        #     break
        # try:
        #     freq = float(freq)
        #     if freq <= 0:
        #         break
        #     err, ff = dev.SetFreq(freq)
        #     print(f"Frequency set to: {ff} Hz")
        #     start_ns = time.time_ns()
        #     ts = []
        #     Ex = []
        #     for i in range(1000):
        #         #start_ns = time.time_ns()
        #         dat = dev._float_GetData()
        #         end_ns = time.time_ns()
        #         t_ms = (end_ns-start_ns)*1e-6
        #         #print(ff, i, (end_ns-start_ns)/1e6, dat[0], dat[1], dat[2])
        #         ts.append(t_ms)
        #         Ex.append(dat[0])
        t1 = time.time_ns()
        err, Exs, Eys, Ezs = dev._float_force_trigger_GetData(forceTRIG_CL=True)
        delta_t = (time.time_ns() - t1) * 1e-6 # in ms
        #fitdata = fit_sin(ts, Ex)
        #freqAM = fitdata['freq']
        #meanAM = fitdata['offset']
        #modAM = abs(fitdata['amp']) / meanAM * 100
        #plt.title(f"E-Field: {meanAM:.2f} V/m, AM-Freq: {freqAM:.2f} kHz, AM-Depth: {modAM:.2f} %, Dt = {delta_t:.1f} ms")
        # lineEx.set_xdata(ts)
        for i, ax in enumerate(axs.flatten()):
            lineEx[i].set_ydata(Exs[i])
            lineEy[i].set_ydata(Eys[i])
            lineEz[i].set_ydata(Ezs[i])
            #lineSin.set_ydata(fitdata['fitfunc'](ts))
            ax.relim()
            ax.autoscale_view(True, True, True)
        fig.canvas.draw()
        fig.canvas.flush_events()

            #plt.show()
        #except ValueError:
        #    break
    dev.Quit()


def main2():
    from mpy.tools.util import format_block
    import numpy as np

    try:
        ini = sys.argv[1]
    except IndexError:
        ini = format_block("""
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

                        [Channel_1]
                        name: EField
                        unit: Voverm
                        """)
        ini = io.StringIO(ini)
    dev = FIELDPROBE()

    dev.Init(ini=ini, channel=1)
    err, des = dev.GetDescription()

    while True:
        freq = input("Frequency / Hz: ")
        if freq in 'qQ':
            break
        try:
            freq = float(freq)
            if freq <= 0:
                break
            err, ff = dev.SetFreq(freq)
            print(f"Frequency set to: {ff} Hz")
            for i in range(10):
                start_ns = time.time_ns()
                print("vor GetData")
                err, dat = dev.GetData()
                exs,eys,ezs =(dat[i] for i in range(3))
                end_ns = time.time_ns()
                print(f'freq: {ff} Hz, count: {i}, duration: {(end_ns-start_ns)/1e6} ms')
                for p in range(dev.nprb):
                    print(f'prb: {p}, x: {exs[p]}, y: {eys[p]}, z: {ezs[p]}')
        except ValueError:
            break
    dev.Quit()


if __name__ == '__main__':
    main()
