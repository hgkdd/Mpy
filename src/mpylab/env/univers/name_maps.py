"""Typed name-map contracts and coercion helpers for univers measurements."""

from __future__ import annotations

from typing import Mapping, TypedDict, cast


class AmplifierNames(TypedDict):
    """AmplifierNames class."""
    sg: str
    amp_in: str
    amp_out: str
    pm_fwd: str
    pm_bwd: str
    output: str


def coerce_amplifier_names(names: Mapping[str, object] | None) -> AmplifierNames:
    """coerce_amplifier_names function."""
    default = {"sg": "sg", "amp_in": "amp_in", "amp_out": "amp_out", "pm_fwd": "pm1", "pm_bwd": "pm2", "output": "gtem"}
    data = dict(default if names is None else names)
    for k, v in default.items():
        data.setdefault(k, v)
    for k in ("sg", "amp_in", "amp_out", "pm_fwd", "pm_bwd", "output"):
        if not isinstance(data.get(k), str):
            raise TypeError(f"names['{k}'] must be str, got {type(data.get(k)).__name__}")
    return cast(AmplifierNames, data)
