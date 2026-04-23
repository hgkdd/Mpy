# -*- coding: utf-8 -*-
"""Virtual switch driver for tests without switching hardware."""

import io
import re

from mpylab.device.driver import DRIVER
from mpylab.tools.configuration import strbool
from mpylab.tools.util import format_block


class SWITCH(DRIVER):
    """In-memory switch implementation exposing the expected ``switch_to`` API."""

    conftmpl = {
        "description": {
            "description": str,
            "type": str,
            "vendor": str,
            "serialnr": str,
            "deviceid": str,
            "driver": str,
        },
        "init_value": {
            "states": int,
            "initial_state": int,
            "virtual": strbool,
        },
    }

    def __init__(self, SearchPaths=None):
        super().__init__(SearchPaths=SearchPaths)
        self.IDN = "Virtual,Switch,000000,1.0"
        self._last_response = ""
        self._reset_state()

    def _reset_state(self):
        """Reset the virtual switch to deterministic defaults."""
        self.states = 2
        self.state = 0
        self.history = []

    def Init(self, ini=None, channel=None, ignore_bus=True):
        """Initialize the virtual switch without opening a hardware bus."""
        self.error = DRIVER.Init(self, ini=ini, channel=channel, ignore_bus=True)
        self.conf.setdefault("init_value", {})
        self.conf["init_value"]["virtual"] = True
        self.states = int(self.conf["init_value"].get("states", self.states))
        initial_state = int(self.conf["init_value"].get("initial_state", self.state))
        self.switch_to(initial_state)
        return self.error

    def GetDescription(self):
        """Return a virtual identification string."""
        return 0, self.conf.get("description", {}).get("description", self.IDN)

    def GetVirtual(self):
        """Return whether this driver is virtual."""
        return 0, True

    def switch_to(self, state):
        """Switch to a zero-based state index and return an error code."""
        state = int(state)
        if state < 0 or state >= self.states:
            self.error = -1
            raise ValueError(f"Switch state {state} outside valid range 0..{self.states - 1}")
        self.error = 0
        self.state = state
        self.history.append(state)
        return self.error

    def SetState(self, state):
        """Set and return the active switch state."""
        self.switch_to(state)
        return self.error, self.state

    def GetState(self):
        """Return the active switch state."""
        self.error = 0
        return self.error, self.state

    def GetStates(self):
        """Return the number of available virtual switch states."""
        self.error = 0
        return self.error, self.states

    def Quit(self):
        """Quit the virtual switch."""
        self.error = 0
        return self.error

    def write(self, cmd):
        """Handle a small command subset for raw command tests."""
        cmd = str(cmd).strip()
        upper = cmd.upper()
        self._last_response = ""
        if upper == "*IDN?":
            self._last_response = self.IDN
        elif upper == "STATE?":
            self._last_response = str(self.state)
        elif upper == "STATES?":
            self._last_response = str(self.states)
        elif upper.startswith("STATE "):
            self.SetState(cmd.split(maxsplit=1)[1])
        elif upper in {"QUIT", "SYST:LOC"}:
            self.Quit()
        else:
            self._last_response = f"OK {cmd}"
        return 0

    def read(self, tmpl=None):
        """Return or parse the last virtual command response."""
        if tmpl is None:
            return self._last_response
        match = re.match(tmpl, self._last_response)
        if match is None:
            return {}
        return match.groupdict()

    def query(self, cmd, tmpl=None):
        """Write a virtual command and return the raw or parsed response."""
        self.write(cmd)
        return self.read(tmpl)


std_ini_text = format_block("""
    [description]
    DESCRIPTION = Virtual Switch
    TYPE = SWITCH
    VENDOR = mpylab
    SERIALNR =
    DEVICEID =
    DRIVER = switch_virtual.py

    [INIT_VALUE]
    STATES = 2
    INITIAL_STATE = 0
    VIRTUAL = 1
    """).strip()


def main():
    """Run a short virtual switch smoke test."""
    dev = SWITCH()
    err = dev.Init(io.StringIO(std_ini_text))
    print("Init:", err)
    print("Description:", dev.GetDescription())
    print("States:", dev.GetStates())
    for state in range(dev.states):
        print("SetState:", dev.SetState(state))
    print("History:", dev.history)
    print("Quit:", dev.Quit())


if __name__ == "__main__":
    main()
