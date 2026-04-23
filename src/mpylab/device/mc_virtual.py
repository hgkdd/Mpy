# -*- coding: utf-8 -*-
"""Virtual motor controller driver for tests without positioning hardware."""

import io
import re
import time

from mpylab.device.motorcontroller import MOTORCONTROLLER as MOTORCONTROLLER_BASE
from mpylab.tools.util import format_block


class MOTORCONTROLLER(MOTORCONTROLLER_BASE):
    """In-memory motor controller with deterministic angle and speed state."""

    def __init__(self, SearchPaths=None):
        super().__init__(SearchPaths=SearchPaths)
        self.IDN = "Virtual,MotorController,000000,1.0"
        self._last_response = ""
        self._reset_state()

    def _reset_state(self):
        """Reset virtual motion state to deterministic defaults."""
        self.position = 0.0
        self.speed = 30.0
        self.direction = 0
        self.target_position = None
        self._last_update = time.monotonic()

    def Init(self, ini=None, channel=None, ignore_bus=True):
        """Initialize the virtual motor controller without opening a bus."""
        self.error = MOTORCONTROLLER_BASE.Init(self, ini=ini, channel=channel, ignore_bus=True)
        self.conf.setdefault("init_value", {})
        self.conf["init_value"]["virtual"] = True
        self._reset_state()
        return self.error

    def _update_position(self):
        """Advance the simulated position according to elapsed time and direction."""
        now = time.monotonic()
        elapsed = now - self._last_update
        self._last_update = now
        if not self.direction or self.speed <= 0:
            return

        step = abs(self.speed * elapsed)
        if self.target_position is None:
            self.position = (self.position + self.direction * step) % 360.0
            return

        remaining = self._directed_distance(self.position, self.target_position, self.direction)
        if step >= remaining:
            self.position = self.target_position
            self.direction = 0
            self.target_position = None
        else:
            self.position = (self.position + self.direction * step) % 360.0

    def _shortest_direction(self, current, target):
        """Return direction for the shortest path from current to target."""
        clockwise = (target - current) % 360.0
        anti_clockwise = (current - target) % 360.0
        if clockwise == 0:
            return 0
        if clockwise <= anti_clockwise:
            return 1
        return -1

    def _directed_distance(self, current, target, direction):
        """Return remaining distance from current to target in the given direction."""
        if direction > 0:
            return (target - current) % 360.0
        if direction < 0:
            return (current - target) % 360.0
        return 0.0

    def GetDescription(self):
        """Return a virtual identification string."""
        return 0, self.IDN

    def GetVirtual(self):
        """Return whether this driver is virtual."""
        return 0, True

    def Goto(self, pos):
        """Start moving to an absolute angle in degrees using the configured speed."""
        self.error = 0
        self._update_position()
        self.target_position = float(pos) % 360.0
        self.direction = self._shortest_direction(self.position, self.target_position)
        if self.direction == 0:
            self.target_position = None
        return self.error, self.position

    def Move(self, direction):
        """Start continuous movement in direction -1, 0, or 1."""
        direction = int(direction)
        if direction not in (-1, 0, 1):
            self.error = -1
            raise ValueError("direction must be -1, 0, or 1")
        self.error = 0
        self._update_position()
        self.direction = direction
        self.target_position = None
        return self.error, self.direction

    def GetState(self):
        """Return ``(error, position_deg, direction)``."""
        self.error = 0
        self._update_position()
        return self.error, self.position, self.direction

    def SetSpeed(self, speed):
        """Set and return virtual angular speed in degrees per second."""
        speed = float(speed)
        if speed < 0:
            self.error = -1
            raise ValueError("speed must be non-negative")
        self.error = 0
        self._update_position()
        self.speed = speed
        return self.error, self.speed

    def GetSpeed(self):
        """Return virtual angular speed in degrees per second."""
        self.error = 0
        return self.error, self.speed

    def Quit(self):
        """Stop virtual motion and quit."""
        self.error = 0
        self._update_position()
        self.direction = 0
        self.target_position = None
        return self.error

    def write(self, cmd):
        """Handle a small command subset for raw command tests."""
        cmd = str(cmd).strip()
        upper = cmd.upper()
        self._last_response = ""
        if upper == "*IDN?":
            self._last_response = self.IDN
        elif upper == "STATE?":
            _err, pos, direction = self.GetState()
            self._last_response = f"POS {pos:g} DEG, DIR {direction:d}"
        elif upper == "SPEED?":
            self._last_response = f"SPEED {self.speed:g}"
        elif upper.startswith("SPEED "):
            self.SetSpeed(cmd.split(maxsplit=1)[1])
        elif upper.startswith("GOTO "):
            parts = cmd.split()
            self.Goto(parts[1])
        elif upper.startswith("MOVE "):
            self.Move(cmd.split(maxsplit=1)[1])
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
    DESCRIPTION = Virtual Motor Controller
    TYPE = MOTORCONTROLLER
    VENDOR = mpylab
    SERIALNR =
    DEVICEID =
    DRIVER = mc_virtual.py

    [INIT_VALUE]
    GPIB = 0
    VIRTUAL = 1

    [CHANNEL_1]
    NAME = Turntable
    UNIT = deg
    """).strip()


def main():
    """Run a short virtual motor controller smoke test."""
    dev = MOTORCONTROLLER()
    print("Init:", dev.Init(io.StringIO(std_ini_text)))
    print("Description:", dev.GetDescription())
    print("Goto:", dev.Goto(90))
    print("Speed:", dev.SetSpeed(45))
    print("Move:", dev.Move(1))
    time.sleep(0.05)
    print("State:", dev.GetState())
    print("Quit:", dev.Quit())


if __name__ == "__main__":
    main()
