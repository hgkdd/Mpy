"""Legacy GPIB-based sweep helper for the R&S ESHS30 receiver.

This module intentionally keeps a minimal API for older measurement scripts.
Hardware communication is performed only when functions are called directly,
so importing the module remains safe during documentation builds.
"""

from __future__ import annotations

from typing import Iterator, Tuple

try:
    from gpib_ctypes import gpib
except Exception:  # pragma: no cover - optional dependency on measurement hosts
    gpib = None

FSTART_HZ = 150e3
FSTOP_HZ = 30e6
FSTEP_HZ = 1e3


def _require_gpib():
    """Return the gpib backend or raise a clear runtime error if unavailable."""
    if gpib is None:
        raise RuntimeError("gpib_ctypes backend is not available on this host.")
    return gpib


def get_level(interface, device):
    """Query one level value from the currently configured receiver frequency."""
    gpib_backend = _require_gpib()
    gpib_backend.serial_poll(device)  # reset SRQ bit
    gpib_backend.write(device, "LEVEL?")  # start measurement
    gpib_backend.wait(interface, 0x1000)  # wait for SRQ bit
    value = gpib_backend.read(device, 1024)
    gpib_backend.wait(interface, 0x100)  # wait for I/O operation complete
    return float(value)


def sweep_levels(
    interface=0,
    primary_address=17,
    fstart=FSTART_HZ,
    fstop=FSTOP_HZ,
    fstep=FSTEP_HZ,
) -> Iterator[Tuple[float, float]]:
    """Yield ``(frequency_hz, level)`` pairs for a full receiver sweep."""
    gpib_backend = _require_gpib()
    device = gpib_backend.dev(interface, primary_address)

    frequency = fstart
    while frequency <= fstop:
        gpib_backend.write(device, f"FREQUENCY {frequency} HZ")
        level = get_level(interface, device)
        yield frequency, level
        frequency += fstep


def main():
    """Run a sweep and print all measured levels to stdout."""
    for frequency, level in sweep_levels():
        print(f"{frequency}: {level}")


if __name__ == "__main__":
    main()
