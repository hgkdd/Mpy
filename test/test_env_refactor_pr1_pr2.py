import os
import pickle
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from scuq.si import WATT
from scuq.quantities import Quantity

from mpylab.env.Measure import Measure
from mpylab.env.msc.name_maps import coerce_msc_autocorr_names
from mpylab.env.msc.MSC import MSC, stdImmunityKernel as MSCStdImmunityKernel
from mpylab.env.tem.TEMCell import TEMCell, stdImmunityKernel as TEMStdImmunityKernel
from mpylab.env.univers.AmplifierTest import AmplifierTest
from mpylab.tools.aunits import EFIELD


class _FakeSG:
    def SetLevel(self, lv):
        return 0, lv


class _FakeMGraphForMeasure:
    def __init__(self):
        self.name = SimpleNamespace(sg="sg")
        self.instrumentation = {"sg": _FakeSG()}


class _FakeLifecycleMGraph:
    def __init__(self, init_rc=0):
        self.init_rc = init_rc
        self.init_calls = 0
        self.zero_calls = 0
        self.rfoff_calls = 0
        self.quit_calls = 0

    def Init_Devices(self):
        self.init_calls += 1
        return self.init_rc

    def Zero_Devices(self):
        self.zero_calls += 1
        return 0

    def RFOff_Devices(self):
        self.rfoff_calls += 1
        return 0

    def Quit_Devices(self):
        self.quit_calls += 1
        return 0


class _FakeInterruptMGraph(_FakeLifecycleMGraph):
    def __init__(self):
        super().__init__(init_rc=0)
        self.rfon_calls = 0
        self.nbtrigger_calls = 0
        self.eval_calls = 0
        self.setfreq_calls = 0

    def RFOn_Devices(self):
        self.rfon_calls += 1
        return 0

    def NBTrigger(self, nblist):
        _ = nblist
        self.nbtrigger_calls += 1
        return 0

    def EvaluateConditions(self):
        self.eval_calls += 1
        return None

    def SetFreq_Devices(self, f):
        _ = f
        self.setfreq_calls += 1
        return 0.0, 0.0


class _FakeMGraphForAmplifierTest:
    last_instance = None
    raise_on_setfreq = False

    def __init__(self, dotfile, themap, SearchPaths=None):
        _ = (dotfile, SearchPaths)
        self.themap = dict(themap)
        self.name = SimpleNamespace(**self.themap)
        self._init_calls = 0
        self._quit_calls = 0
        self._rfoff_calls = 0
        _FakeMGraphForAmplifierTest.last_instance = self

    def CreateDevices(self):
        return {"sg": _FakeSG()}

    def CmdDevices(self, IgnoreInactive, cmd, *args):
        _ = (IgnoreInactive, cmd, args)
        return 0

    def Init_Devices(self):
        self._init_calls += 1
        return 0

    def EvaluateConditions(self):
        return None

    def SetFreq_Devices(self, f):
        _ = f
        if _FakeMGraphForAmplifierTest.raise_on_setfreq:
            raise RuntimeError("setfreq failed")
        return 0.0, 0.0

    def get_path_correction(self, start, end, unit):
        _ = (start, end, unit)
        return {"total": Quantity(WATT / WATT, 1.0)}

    def RFOn_Devices(self):
        return 0

    def RFOff_Devices(self):
        self._rfoff_calls += 1
        return 0

    def getBatteryLow_Devices(self):
        return []

    def get_gname(self, logical_name):
        return self.themap.get(logical_name, logical_name)

    def Quit_Devices(self):
        self._quit_calls += 1
        return 0


class _FakeTuner:
    def Goto(self, pos):
        return 0, pos


class _FakeMSCLeveler:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def adjust_level(self, input_level):
        return input_level


class _FakeMGraphForMSC:
    last_instance = None

    def __init__(self, dotfile, themap=None, SearchPaths=None):
        _ = (dotfile, SearchPaths)
        self.themap = dict(themap or {})
        self.name = SimpleNamespace(**self.themap)
        self.nodes = {self.name.pmfwd: {"inst": True}}
        self._nbtrigger = 0
        self._nbread = 0
        self._init = 0
        self._quit = 0
        self._rfoff = 0
        self._rfon = 0
        _FakeMGraphForMSC.last_instance = self

    def CreateDevices(self):
        ddict = {}
        for tname in self.themap.get("tuner", []):
            ddict[tname] = _FakeTuner()
        return ddict

    def Init_Devices(self):
        self._init += 1
        return 0

    def RFOff_Devices(self):
        self._rfoff += 1
        return 0

    def RFOn_Devices(self):
        self._rfon += 1
        return 0

    def Zero_Devices(self):
        return 0

    def Quit_Devices(self):
        self._quit += 1
        return 0

    def EvaluateConditions(self):
        return None

    def SetFreq_Devices(self, f):
        _ = f
        return 0.0, 0.0

    def get_path_correction(self, start, end, unit):
        _ = (start, end, unit)
        return Quantity(WATT / WATT, 1.0)

    def GetAntennaEfficiency(self, ant):
        _ = ant
        return Quantity(WATT / WATT, 1.0)

    def NBTrigger(self, nblist):
        _ = nblist
        self._nbtrigger += 1
        return 0

    def NBRead(self, nblist, nbresult):
        self._nbread += 1
        ret = dict(nbresult)
        for n in nblist:
            if n in ret:
                continue
            if n.startswith("fp"):
                ret[n] = [Quantity(EFIELD, 1.0), Quantity(EFIELD, 1.0), Quantity(EFIELD, 1.0)]
            else:
                ret[n] = Quantity(WATT, 1e-3)
        return ret

    def getBatteryLow_Devices(self):
        return []


class _FakeMGraphForTEM:
    last_instance = None

    def __init__(self, dotfile, themap=None, SearchPaths=None):
        _ = (dotfile, SearchPaths, themap)
        self.name = SimpleNamespace(sg="sg", a1="a1", a2="a2", port="port", pmfwd="pm1", pmbwd="pm2")
        self.instrumentation = {self.name.sg: _FakeSG()}
        self.nodes = {self.name.pmfwd: {"inst": True}}
        self._init = 0
        self._quit = 0
        self._rfoff = 0
        self._rfon = 0
        self._nbtrigger = 0
        self._nbread = 0
        _FakeMGraphForTEM.last_instance = self

    def CreateDevices(self):
        return {}

    def Init_Devices(self):
        self._init += 1
        return 0

    def RFOff_Devices(self):
        self._rfoff += 1
        return 0

    def RFOn_Devices(self):
        self._rfon += 1
        return 0

    def Zero_Devices(self):
        return 0

    def Quit_Devices(self):
        self._quit += 1
        return 0

    def EvaluateConditions(self):
        return None

    def SetFreq_Devices(self, f):
        _ = f
        return 0.0, 0.0

    def get_path_correction(self, start, end, unit):
        _ = (start, end, unit)
        return {"total": Quantity(WATT / WATT, 1.0)}

    def NBTrigger(self, nblist):
        _ = nblist
        self._nbtrigger += 1
        return 0

    def NBRead(self, nblist, nbresult):
        self._nbread += 1
        ret = dict(nbresult)
        for n in nblist:
            if n in ret:
                continue
            if n.startswith("fp"):
                ret[n] = [Quantity(EFIELD, 1.0), Quantity(EFIELD, 1.0), Quantity(EFIELD, 1.0)]
            else:
                ret[n] = Quantity(WATT, 1e-3)
        return ret

    def getBatteryLow_Devices(self):
        return []


def _always_start(msg, buttons=None, level="", dct=None):
    _ = (msg, level, dct)
    if not buttons:
        return -1
    if "Start" in buttons:
        return buttons.index("Start")
    return 0


class TestEnvRefactorPR1PR2(unittest.TestCase):
    def test_name_map_coercion_accepts_tuple_lists(self):
        names = coerce_msc_autocorr_names(
            {
                "sg": "sg",
                "a1": "a1",
                "a2": "a2",
                "ant": "ant",
                "pmfwd": "pm1",
                "pmbwd": "pm2",
                "fp": ("fp1", "fp2"),
                "tuner": ("t1",),
            }
        )
        self.assertEqual(names["fp"], ["fp1", "fp2"])
        self.assertEqual(names["tuner"], ["t1"])

    def test_name_map_coercion_rejects_wrong_scalar_type(self):
        with self.assertRaises(TypeError):
            coerce_msc_autocorr_names(
                {
                    "sg": ["sg"],  # type: ignore[list-item]
                    "a1": "a1",
                    "a2": "a2",
                    "ant": "ant",
                    "pmfwd": "pm1",
                    "pmbwd": "pm2",
                    "fp": ["fp1"],
                    "tuner": ["t1"],
                }
            )

    def test_measure_legacy_aliases(self):
        m = Measure()
        m.set_messenger(_always_start)

        mg = _FakeMGraphForMeasure()
        lv = m.setLevel(mg, {"sg": "sg"}, -10.0)
        self.assertIsInstance(lv, Quantity)
        self.assertAlmostEqual(lv.get_expectation_value_as_float(), 1e-4, places=12)

        data = {"A": {"x": 1}, "B": {"y": 2}}
        self.assertEqual(m.MakeDeslist(data, None), ["A", "B"])
        self.assertEqual(sorted(m.MakeWhatlist(data, None)), ["x", "y"])
        self.assertTrue(m.std_eut_status_checker("OK"))
        self.assertFalse(m.std_eut_status_checker("fail"))

    def test_measure_ui_adapter_routing(self):
        m = Measure()

        seen = {"msg": None, "called": 0}

        def custom_messenger(msg, buttons=None, level="", dct=None):
            _ = (buttons, level, dct)
            seen["msg"] = msg
            seen["called"] += 1
            return 123

        m.set_messenger(custom_messenger)
        ret = m.messenger("adapter test", ["Ok"])
        self.assertEqual(ret, 123)
        self.assertEqual(seen["msg"], "adapter test")
        self.assertEqual(seen["called"], 1)

        m.set_user_interrupt_tester(lambda: 77)
        self.assertEqual(m.UserInterruptTester(), 77)
        self.assertEqual(m.PollKey(), 77)
        m.set_user_interrupt_tester(lambda: 78)
        self.assertEqual(m.UserInterruptTester(), 78)

    def test_measure_lifecycle_helpers(self):
        m = Measure()
        m.set_messenger(_always_start)

        mg = _FakeLifecycleMGraph(init_rc=0)
        rc = m._init_measurement_devices(mg, do_zero=True, do_rfoff=True)
        self.assertEqual(rc, 0)
        self.assertEqual(mg.init_calls, 1)
        self.assertEqual(mg.zero_calls, 1)
        self.assertEqual(mg.rfoff_calls, 1)

        stat = m._finalize_measurement_devices(mg, do_rfoff=True, do_quit=True)
        self.assertEqual(stat, 0)
        self.assertEqual(mg.quit_calls, 1)

        mg_fail = _FakeLifecycleMGraph(init_rc=5)
        rc_fail = m._init_measurement_devices(mg_fail, do_zero=True, do_rfoff=True)
        self.assertEqual(rc_fail, 5)
        self.assertEqual(mg_fail.zero_calls, 0)
        self.assertEqual(mg_fail.rfoff_calls, 0)

    def test_common_interrupt_flow_continue(self):
        m = Measure()

        def interrupt_once():
            vals = getattr(interrupt_once, "_vals", [ord("x"), None])
            if vals:
                out = vals.pop(0)
                interrupt_once._vals = vals
                return out
            return None

        def messenger(msg, buttons=None, level="", dct=None):
            _ = (msg, level, dct)
            if buttons and "Continue" in buttons:
                return buttons.index("Continue")
            return -1

        m.set_user_interrupt_tester(interrupt_once)
        m.set_messenger(messenger)

        mg = _FakeInterruptMGraph()
        scope = {"mg": mg, "delay": 0, "nblist": ["dev1"]}
        handled = m._handle_user_interrupt_common(scope, wait_handler=lambda dct: None)
        self.assertTrue(handled)
        self.assertEqual(mg.rfoff_calls, 1)
        self.assertEqual(mg.rfon_calls, 1)
        self.assertEqual(mg.nbtrigger_calls, 1)

    def test_common_interrupt_flow_suspend_resume(self):
        m = Measure()

        def interrupt_once():
            vals = getattr(interrupt_once, "_vals", [ord("x"), None])
            if vals:
                out = vals.pop(0)
                interrupt_once._vals = vals
                return out
            return None

        def messenger(msg, buttons=None, level="", dct=None):
            _ = (msg, level, dct)
            if buttons == ['Continue', 'Suspend', 'Interactive', 'Quit']:
                return buttons.index("Suspend")
            if buttons == ['Resume', 'Quit']:
                return buttons.index("Resume")
            return -1

        m.set_user_interrupt_tester(interrupt_once)
        m.set_messenger(messenger)

        mg = _FakeInterruptMGraph()
        scope = {"mg": mg, "delay": 0, "nblist": ["dev1"]}
        handled = m._handle_user_interrupt_common(scope, wait_handler=lambda dct: None)
        self.assertTrue(handled)
        self.assertEqual(mg.quit_calls, 1)
        self.assertEqual(mg.init_calls, 1)
        self.assertEqual(mg.zero_calls, 1)
        self.assertEqual(mg.rfoff_calls, 2)
        self.assertEqual(mg.rfon_calls, 1)
        self.assertEqual(mg.nbtrigger_calls, 1)

    def test_common_interrupt_flow_suspend_quit_aborts(self):
        m = Measure()

        def interrupt_once():
            vals = getattr(interrupt_once, "_vals", [ord("x"), None])
            if vals:
                out = vals.pop(0)
                interrupt_once._vals = vals
                return out
            return None

        def messenger(msg, buttons=None, level="", dct=None):
            _ = (msg, level, dct)
            if buttons == ['Continue', 'Suspend', 'Interactive', 'Quit']:
                return buttons.index("Suspend")
            if buttons == ['Resume', 'Quit']:
                return buttons.index("Quit")
            return -1

        m.set_user_interrupt_tester(interrupt_once)
        m.set_messenger(messenger)
        mg = _FakeInterruptMGraph()
        with self.assertRaises(UserWarning):
            m._handle_user_interrupt_common({"mg": mg, "delay": 0, "nblist": ["dev1"]}, wait_handler=lambda dct: None)
        self.assertEqual(mg.quit_calls, 1)
        self.assertEqual(mg.rfon_calls, 0)
        self.assertEqual(mg.nbtrigger_calls, 0)

    def test_temcell_interrupt_flow_continue(self):
        tem = TEMCell()

        def interrupt_once():
            vals = getattr(interrupt_once, "_vals", [ord("x"), None])
            if vals:
                out = vals.pop(0)
                interrupt_once._vals = vals
                return out
            return None

        def messenger(msg, buttons=None, level="", dct=None):
            _ = (msg, level, dct)
            if buttons and "Continue" in buttons:
                return buttons.index("Continue")
            return -1

        tem.set_user_interrupt_tester(interrupt_once)
        tem.set_messenger(messenger)

        mg = _FakeInterruptMGraph()
        scope = {"mg": mg, "delay": 0, "nblist": ["dev1"]}
        handled = tem._HandleUserInterrupt(scope)
        self.assertTrue(handled)
        self.assertEqual(mg.rfoff_calls, 1)
        self.assertEqual(mg.rfon_calls, 1)
        self.assertEqual(mg.nbtrigger_calls, 1)

    def test_measure_pickle_roundtrip_restores_ui_adapter(self):
        m = Measure()
        m.set_messenger(_always_start)
        m.set_user_interrupt_tester(lambda: 88)
        blob = pickle.dumps(m)
        m2 = pickle.loads(blob)
        self.assertTrue(hasattr(m2, "ui"))
        self.assertTrue(callable(m2.ui.ask))
        self.assertTrue(callable(m2.UserInterruptTester))
        self.assertTrue(callable(m2.PollKey))
        self.assertEqual(m2.UserInterruptTester.__func__, m2.ui.check_interrupt.__func__)
        self.assertEqual(m2.PollKey.__func__, m2.ui.poll_key.__func__)

    def test_msc_kernel_poll_key_user_event(self):
        kernel = MSCStdImmunityKernel(
            field=1.0,
            tp={1.0: [[0]]},
            messenger=lambda *args, **kwargs: -1,
            UIHandler=lambda: ord("s"),
            lcls={},
            dwell=0.02,
            keylist="sS",
        )
        cmd = None
        for _ in range(10):
            cmd = kernel.test("")
            if cmd[0] == "eut":
                break
        self.assertIsNotNone(cmd)
        self.assertEqual(cmd[0], "eut")
        self.assertEqual(cmd[1], "User event.")
        self.assertEqual(cmd[2]["eutstatus"], "Marked by user")

    def test_temcell_kernel_poll_key_user_event(self):
        kernel = TEMStdImmunityKernel(
            field=1.0,
            freqs=[1.0],
            positions={"v": [0], "h": []},
            messenger=lambda *args, **kwargs: -1,
            UIHandler=lambda: ord("s"),
            lcls={},
            dwell=0.02,
            keylist="sS",
        )
        cmd = None
        for _ in range(10):
            cmd = kernel.test("")
            if cmd[0] == "eut":
                break
        self.assertIsNotNone(cmd)
        self.assertEqual(cmd[0], "eut")
        self.assertEqual(cmd[1], "User event.")
        self.assertEqual(cmd[2]["eutstatus"], "Marked by user")

    def test_msc_interrupt_flow_continue(self):
        msc = MSC()

        def interrupt_once():
            vals = getattr(interrupt_once, "_vals", [ord("x"), None])
            if vals:
                out = vals.pop(0)
                interrupt_once._vals = vals
                return out
            return None

        def messenger(msg, buttons=None, level="", dct=None):
            _ = (msg, level, dct)
            if buttons and "Continue" in buttons:
                return buttons.index("Continue")
            return -1

        msc.set_user_interrupt_tester(interrupt_once)
        msc.set_messenger(messenger)

        mg = _FakeInterruptMGraph()
        scope = {"mg": mg, "delay": 0, "nblist": ["dev1"]}
        handled = msc.stdUserInterruptHandler(scope)
        self.assertTrue(handled)
        self.assertEqual(mg.rfoff_calls, 1)
        self.assertEqual(mg.rfon_calls, 1)
        self.assertEqual(mg.nbtrigger_calls, 1)

    def test_amplifiertest_measure_smoke_with_fake_graph(self):
        at = AmplifierTest()
        at.set_messenger(_always_start)
        at.set_user_interrupt_tester(lambda: None)

        with patch("mpylab.env.univers.AmplifierTest.MGraph", _FakeMGraphForAmplifierTest):
            stat = at.Measure(description="smoke", freqs=[1e6], levels=[], virtual=False)

        self.assertEqual(stat, 0)
        mg = _FakeMGraphForAmplifierTest.last_instance
        self.assertIsNotNone(mg)
        self.assertEqual(mg._init_calls, 1)
        self.assertEqual(mg._quit_calls, 1)
        self.assertGreaterEqual(mg._rfoff_calls, 1)

    def test_amplifiertest_finalize_on_exception(self):
        at = AmplifierTest()
        at.set_messenger(_always_start)
        at.set_user_interrupt_tester(lambda: None)

        _FakeMGraphForAmplifierTest.raise_on_setfreq = True
        try:
            with patch("mpylab.env.univers.AmplifierTest.MGraph", _FakeMGraphForAmplifierTest):
                with self.assertRaises(RuntimeError):
                    at.Measure(description="smoke-exc", freqs=[1e6], levels=[], virtual=False)
        finally:
            _FakeMGraphForAmplifierTest.raise_on_setfreq = False

        mg = _FakeMGraphForAmplifierTest.last_instance
        self.assertIsNotNone(mg)
        self.assertEqual(mg._init_calls, 1)
        self.assertEqual(mg._quit_calls, 1)
        self.assertGreaterEqual(mg._rfoff_calls, 1)

    def test_output_helpers_msc_and_temcell(self):
        msc = MSC()
        msc.rawData_MainCal = {
            "d": {
                "efield": {
                    1.0: {
                        "(0,)": {
                            0: [{"value": [1, 2, 3], "pfwd": 1, "pbwd": 0}]
                        }
                    }
                }
            }
        }
        msc.processedData_MainCal = {"d": {"Enorm": {1.0: {"p0": 1.23}}}}

        tem = TEMCell()
        tem.rawData_e0y = {
            "d": {
                "efield": {
                    1.0: {
                        0: {
                            0: [{"value": [1, 2, 3], "pfwd": 1, "pbwd": 0}]
                        }
                    }
                }
            }
        }
        tem.processedData_e0y = {"d": {"e0y": {1.0: {0: [1, 2, 3]}}}}

        with tempfile.TemporaryDirectory() as td:
            msc_raw = os.path.join(td, "msc_raw.txt")
            msc_proc = os.path.join(td, "msc_proc.txt")
            tem_raw = os.path.join(td, "tem_raw.txt")
            tem_proc = os.path.join(td, "tem_proc.txt")

            msc.OutputRawData_MainCal(fname=msc_raw)
            msc.OutputProcessedData_MainCal(fname=msc_proc)
            tem.OutputRawData_e0y(fname=tem_raw)
            tem.OutputProcessedData_e0y(fname=tem_proc)

            for fn in (msc_raw, msc_proc, tem_raw, tem_proc):
                self.assertTrue(os.path.exists(fn))
                with open(fn, "r", encoding="utf-8") as f:
                    content = f.read()
                self.assertTrue(len(content) > 0)

        # Also ensure stdout path (fname=None) remains callable.
        msc.OutputRawData_MainCal(description="d", what=["efield"], fname=None)
        msc.OutputProcessedData_MainCal(description="d", what=["Enorm"], fname=None)
        tem.OutputRawData_e0y(description="d", what=["efield"], fname=None)
        tem.OutputProcessedData_e0y(description="d", what=["e0y"], fname=None)

    def test_msc_measure_maincal_e2e_with_fake_graph(self):
        msc = MSC()
        msc.set_messenger(_always_start)
        msc.set_user_interrupt_tester(lambda: None)

        names = {
            "sg": "sg",
            "a1": "a1",
            "a2": "a2",
            "ant": "ant",
            "pmfwd": "pm1",
            "pmbwd": "pm2",
            "fp": ["fp1"],
            "tuner": ["tuner1"],
            "refant": ["refant1"],
            "pmref": ["pmref1"],
        }

        with patch("mpylab.env.msc.MSC.mgraph.MGraph", _FakeMGraphForMSC), \
             patch("mpylab.env.msc.MSC.mgraph.Leveler", _FakeMSCLeveler), \
             patch("mpylab.env.msc.MSC.spacing.logspaceTab", lambda *args, **kwargs: [1.0]):
            stat = msc.Measure_MainCal(
                description="e2e",
                delay=0.0,
                LUF=1.0,
                FStart=1.0,
                FStop=1.0,
                ftab=[1.0, 2.0],
                nftab=[1],
                ntuntab=[[1]],
                tofftab=[[1]],
                nprbpostab=[1],
                nrefantpostab=[1],
                names=names,
            )

        self.assertEqual(stat, 0)
        self.assertIn("e2e", msc.rawData_MainCal)
        self.assertIn("efield", msc.rawData_MainCal["e2e"])
        self.assertTrue(msc.rawData_MainCal["e2e"]["efield"])
        mg = _FakeMGraphForMSC.last_instance
        self.assertIsNotNone(mg)
        self.assertEqual(mg._init, 1)
        self.assertEqual(mg._quit, 1)
        self.assertGreaterEqual(mg._rfoff, 1)
        self.assertGreaterEqual(mg._rfon, 1)

    def test_temcell_measure_e0y_e2e_with_fake_graph(self):
        tem = TEMCell()
        tem.set_messenger(_always_start)
        tem.set_user_interrupt_tester(lambda: None)

        names = {
            "sg": "sg",
            "a1": "a1",
            "a2": "a2",
            "port": "port",
            "pmfwd": "pm1",
            "pmbwd": "pm2",
            "fp": ["fp1"],
        }

        with patch("mpylab.env.tem.TEMCell.mgraph.MGraph", _FakeMGraphForTEM):
            stat = tem.Measure_e0y(
                description="e2e",
                delay=0.0,
                freqs=[1.0],
                SGLevel=-10,
                names=names,
            )

        self.assertEqual(stat, 0)
        self.assertIn("e2e", tem.rawData_e0y)
        self.assertIn("efield", tem.rawData_e0y["e2e"])
        self.assertIn(1.0, tem.rawData_e0y["e2e"]["efield"])
        mg = _FakeMGraphForTEM.last_instance
        self.assertIsNotNone(mg)
        self.assertEqual(mg._init, 1)
        self.assertEqual(mg._quit, 1)
        self.assertGreaterEqual(mg._rfoff, 1)
        self.assertGreaterEqual(mg._rfon, 1)

    def test_wait_accepts_legacy_handler_with_context(self):
        m = Measure()
        calls = []

        def handler(dct):
            calls.append(dct["x"])

        m.wait(0.0, {"x": 1}, handler, intervall=0.0)
        m.wait(0.01, {"x": 2}, handler, intervall=0.005)
        self.assertGreaterEqual(len(calls), 1)
        self.assertIn(2, calls)

    def test_wait_accepts_poll_key_style_handler(self):
        m = Measure()
        calls = []

        def handler():
            calls.append(1)
            return None

        m.wait(0.01, {"ignored": True}, handler, intervall=0.005)
        self.assertGreaterEqual(len(calls), 1)


if __name__ == "__main__":
    unittest.main()
