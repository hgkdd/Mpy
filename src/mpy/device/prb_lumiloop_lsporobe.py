# -*- coding: utf-8 -*-
import sys
import io
import time
import struct
import itertools

from scuq import si, quantities, ucomponents
import numpy as np

from mpy.device.fieldprobe import FIELDPROBE as FLDPRB


class FIELDPROBE(FLDPRB):
    conftmpl = FLDPRB.conftmpl
    conftmpl['init_value']['visa'] = str
    conftmpl['init_value']['mode'] = int

    def __init__(self):
        FLDPRB.__init__(self)
        self._internal_unit = si.VOLT / si.METER
        self.freq = None
        self._cmds = {'GetFreq': [(":syst:freq?", r'(?P<freq>%s)' % self._FP)],
                      'Zero': [],
                      'Trigger': [],
                      'Quit': [(':SYST:LAS:EN 0', None)],
                      'GetDescription': [('*IDN?', r'(?P<IDN>.*)')]}
        self.term_chars = '\r\n'
        self.error = None
        self.mode = None
        self.LastData_ns = None
        self.LastData = None

    def Init(self, ini=None, channel=None):
        self.error = FLDPRB.Init(self, ini, channel)
        self.mode = None
        # wait for laser ready
        self.write(':syst:las:en 1')
        self.setMode(self.conf['init_value']['mode'])
        self._conf_trigger()
        return self.error

    def wait_for_laser_ready(self):
        while True:
            # ans = self.query(':syst:las:rdy?', r'(?P<laser>\d)')
            ans = self.query(':meas:rdy?', r'(?P<laser>\d)')  # waits for laser ready AND cal data present
            if ans:
                if int(ans['laser']) == 1:
                    break
            time.sleep(.1)
        self.LastData_ns = time.time_ns()

    def setMode(self, mode):
        mode = int(mode)

        if self.mode == mode:
            return mode

        if 0 <= mode <= 8:
            self.write(f':syst:mod {mode}')
            while True:
                ans = self.query(f':syst:mod?', None)
                if int(ans) == mode:
                    break
        self.wait_for_laser_ready()
        self.mode = mode
        # get effective sample rate
        ans = self.query(':SYST:ESRA?')
        self.esra = int(ans)
        return mode

    def SetFreq(self, freq):
        self.error = 0
        #self.setMode(1)
        self.write(f':syst:freq {freq}')
        tmpl = r'(?P<freq>%s)' % self._FP
        ans = self.query(":syst:freq?", tmpl)
        if ans:
            freq = float(ans['freq'])
        else:
            self.error = 1
            freq = None
        self.freq = freq
        return self.error, freq

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
                ans = self.query(':TRIG:STAT?')
                if ans == state:
                    break
                tnow = time.time_ns()
                if tnow - ts > timeout*1e9:
                    err += err_timeout
                    break
        else:
            err += err_state_unknown
        return err

    def _conf_trigger(self, begin=0, length=1000, tpoints=1, forceTRIG_CL=True, timeout=10):
        err = 0
        if forceTRIG_CL:
            err = self.write(':TRIG:CL')
        # wait for trigger is IDLE
        err = self._wait_for_trigger_state(state='IDLE', timeout=timeout)
        if err < 0:
            return err
        err = self.write(f':TRIG:BEG {begin}')
        err = self._wait_for_trigger_state(state='IDLE', timeout=timeout)
        err = self.write(f':TRIG:LEN {length}')
        err = self._wait_for_trigger_state(state='IDLE', timeout=timeout)
        err = self.write(f':TRIG:POIN {tpoints}')
        err = self._wait_for_trigger_state(state='IDLE', timeout=timeout)
        self.begin = begin
        self.length = length
        self.tpoints = tpoints
        return err

    def _float_force_trigger_GetData(self, forceTRIG_CL=False, timeout=10):
        err = 0
        if forceTRIG_CL:
            err = self.write(':TRIG:CL')
        # wait for trigger is IDLE
        err = self._wait_for_trigger_state(state='IDLE', timeout=timeout)
        if err < 0:
            return err, None
        # force trig
        err = self.write(':TRIG:FOR')
        # wait for trigger DONE
        err = self._wait_for_trigger_state(state='DONE', timeout=timeout)
        if err < 0:
            return err, None
        #ans = self.query(':TRIG:WAV:E:X?')
        #Ex = [float(s) for s in ans.split(',')]
        #ans = self.query(':TRIG:WAV:E:Y?')
        #Ey = [float(s) for s in ans.split(',')]
        #ans = self.query(':TRIG:WAV:E:Z?')
        #Ez = [float(s) for s in ans.split(',')]
        #Ex = Ex[self.begin:]
        #Ey = Ey[self.begin:]
        #Ez = Ez[self.begin:]
        err = self.write(':TRIG:WAV:E:BINR?')
        ans = self.dev.read_bytes(4)
        bin_block_size, = struct.unpack_from('<I', ans)
        ans = self.dev.read_bytes(bin_block_size)
        self.dev.read_bytes(2)  # cr lf
        Ex, Ey, Ez = self._parse_wav_bin_red(ans)
        err = self.write(':TRIG:CL')
        return err, Ex, Ey, Ez

    def _float_GetData(self):
        cmd = ":meas:all?"
        tmpl = r"(?P<x>[\d.]+),(?P<y>[\d.]+),(?P<z>[\d.]+),(?P<m>[\d.]+)"
        ans = self.query(cmd, tmpl)
        return tuple(float(ans[_k]) for _k in ('x', 'y', 'z', 'm') )

    def GetData(self):
        self.error = 0
        # relative error for single measured point
        if self.freq <= 30e6:
            relerr = 0.072  # 0.6 dB
        elif 30e6 < self.freq <= 1e9:
            relerr = 0.12  # 1 dB
        elif 1e9 < self.freq:
            relerr = 0.17  # 1.4 dB
        err, ex, ey, ez  = self._float_force_trigger_GetData()
        sqrt_n = numpy.sqrt(len(ex))
        relerr /= sqrt_n
        ex_av = numpy.average(ex)
        ey_av = numpy.average(ey)
        ez_av = numpy.average(ez)
        data = [ quantities.Quantity(self._internal_unit, ucomponents.UncertainInput(val, val * relerr)) for val in (ex_av,ey_av,ez_av) ]
        return self.error, data

    def GetDataNB(self, retrigger):
        return self.GetData()

    def _get_waveform(self, forceTRIG_CL=True):
        err, Ex, Ey, Ez = self._float_force_trigger_GetData(forceTRIG_CL=forceTRIG_CL)
        dt = 1. / self.esra
        ts = np.array((i * dt * 1e3 for i,_ in enumerate(Ex)))  # t in ms
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
                        description: 'LSProbe 1.2'
                        type:        'FIELDPROBE'
                        vendor:      'LUMILOOP'
                        serialnr:
                        deviceid:
                        driver:

                        [Init_Value]
                        fstart: 10e3
                        fstop: 8.2e9
                        fstep: 0
                        visa: TCPIP0::192.168.88.3::10000::SOCKET
                        mode: 0
                        virtual: 0

                        [Channel_1]
                        name: EField
                        unit: Voverm
                        """)
        ini = io.StringIO(ini)
    dev = FIELDPROBE()

    dev.Init(ini=ini, channel=1)
    err, des = dev.GetDescription()

    err, Ex, Ey, Ez = dev._float_force_trigger_GetData(forceTRIG_CL=True)
    dt = 1./dev.esra
    ts = np.array([i*dt*1e3 for i in range(len(Ex))]) # t in ms

    fitdata = fit_sin(ts, Ex)
    freqAM = fitdata['freq']
    meanAM = fitdata['offset']
    modAM = abs(fitdata['amp']) / meanAM * 100

    plt.ion()
    fig = plt.figure()
    ax = fig.add_subplot(111)
    lineEx, = ax.plot(ts, Ex, marker=',')
    lineEy, = ax.plot(ts, Ey, marker=',')
    lineEz, = ax.plot(ts, Ez, marker=',')
    lineSin, = ax.plot(ts, fitdata['fitfunc'](ts), ls='-')
    plt.xlabel("Time in ms")
    plt.ylabel("E-Field in V/m")
    plt.title(f"E-Field: {meanAM:.2f} V/m, AM-Freq: {freqAM:.2f} kHz, AM-Depth: {modAM:.2f} %")
    plt.grid()
    plt.show()


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
            err, Ex, Ey, Ez = dev._float_force_trigger_GetData(forceTRIG_CL=True)
            delta_t = (time.time_ns() - t1) * 1e-6 # in ms
            fitdata = fit_sin(ts, Ex)
            freqAM = fitdata['freq']
            meanAM = fitdata['offset']
            modAM = abs(fitdata['amp']) / meanAM * 100
            plt.title(f"E-Field: {meanAM:.2f} V/m, AM-Freq: {freqAM:.2f} kHz, AM-Depth: {modAM:.2f} %, Dt = {delta_t:.1f} ms")
            # lineEx.set_xdata(ts)
            lineEx.set_ydata(Ex)
            lineEy.set_ydata(Ey)
            lineEz.set_ydata(Ez)
            lineSin.set_ydata(fitdata['fitfunc'](ts))
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
                        description: 'LSProbe 1.2'
                        type:        'FIELDPROBE'
                        vendor:      'LUMILOOP'
                        serialnr:
                        deviceid:
                        driver:

                        [Init_Value]
                        fstart: 10e3
                        fstop: 8.2e9
                        fstep: 0
                        visa: TCPIP0::192.168.88.3::10000::SOCKET
                        mode: 0
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
                err, dat = dev.GetData()
                ex,ey,ez =(dat[i] for i in range(3))
                end_ns = time.time_ns()
                print(ff, i, (end_ns-start_ns)/1e6, ex, ey, ez)
        except ValueError:
            break
    dev.Quit()


if __name__ == '__main__':
    main2()
