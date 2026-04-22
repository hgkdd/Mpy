# -*- coding: utf-8 -*-
"""Virtual amplifier driver for UI and API tests."""

from mpylab.device.amplifier import AMPLIFIER as BASE_AMPLIFIER


class AMPLIFIER(BASE_AMPLIFIER):
    """Amplifier model with interpolated data and explicit state tracking."""

    def __init__(self, **kw):
        super().__init__(**kw)
        self.state = "POff"
        self.conf = {"init_value": {"virtual": True}}

    def Init(self, ini=None, channel=None, ignore_bus=True):
        self.error = super().Init(ini=ini, channel=channel, ignore_bus=True)
        self.conf.setdefault("init_value", {})["virtual"] = True
        self.state = "Standby"
        return self.error

    def SetState(self, state):
        normalized = str(state)
        aliases = {
            "pon": "POn",
            "power on": "POn",
            "operate": "Operate",
            "standby": "Standby",
            "poff": "POff",
            "power off": "POff",
        }
        self.state = aliases.get(normalized.strip().lower(), normalized)
        self.error = 0
        return self.error

    def Operate(self):
        return self.SetState("Operate")

    def Standby(self):
        return self.SetState("Standby")

    def POn(self):
        return self.SetState("POn")

    def POff(self):
        return self.SetState("POff")

    def GetState(self):
        self.error = 0
        return self.error, self.state

    def GetVirtual(self):
        self.error = 0
        return self.error, True

    def Quit(self):
        self.Standby()
        return self.error
