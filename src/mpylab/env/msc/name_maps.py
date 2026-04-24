"""Typed name-map contracts and coercion helpers for MSC measurements."""

from __future__ import annotations

from typing import Mapping, Sequence, TypedDict, cast


class MSCMainCalNames(TypedDict):
    """Typed device-name mapping for MSC main calibration workflow."""

    sg: str
    a1: str
    a2: str
    ant: str
    pmfwd: str
    pmbwd: str
    fp: list[str]
    tuner: list[str]
    refant: list[str]
    pmref: list[str]


class MSCAutoCorrNames(TypedDict):
    """Typed device-name mapping for MSC auto-correlation workflow."""

    sg: str
    a1: str
    a2: str
    ant: str
    pmfwd: str
    pmbwd: str
    fp: list[str]
    tuner: list[str]


class MSCEUTCalNames(TypedDict):
    """Typed device-name mapping for MSC EUT calibration workflow."""

    sg: str
    a1: str
    a2: str
    ant: str
    pmfwd: str
    pmbwd: str
    tuner: list[str]
    refant: list[str]
    pmref: list[str]
    fp: list[str]


class MSCImmunityNames(TypedDict):
    """Typed device-name mapping for MSC immunity measurement workflow."""

    sg: str
    a1: str
    a2: str
    ant: str
    fp: list[str]
    pmfwd: str
    pmbwd: str
    tuner: list[str]
    refant: list[str]
    pmref: list[str]


class MSCEmissionNames(TypedDict):
    """Typed device-name mapping for MSC emission measurement workflow."""

    tuner: list[str]
    refant: list[str]
    receiver: list[str]


def _default_copy(default: Mapping[str, str | list[str]]) -> dict[str, object]:
    ret: dict[str, object] = {}
    for k, v in default.items():
        ret[k] = list(v) if isinstance(v, list) else v
    return ret


def _as_name_map(names: Mapping[str, object] | None, default: Mapping[str, str | list[str]]) -> dict[str, object]:
    if names is None:
        return _default_copy(default)
    ret = dict(names)
    for k, v in default.items():
        if k not in ret:
            ret[k] = list(v) if isinstance(v, list) else v
    return ret


def _require_str(data: Mapping[str, object], key: str) -> None:
    value = data.get(key)
    if not isinstance(value, str):
        raise TypeError(f"names['{key}'] must be str, got {type(value).__name__}")


def _require_list_str(data: dict[str, object], key: str) -> None:
    value = data.get(key)
    if isinstance(value, list):
        if not all(isinstance(v, str) for v in value):
            raise TypeError(f"names['{key}'] must be list[str]")
        return
    if isinstance(value, tuple):
        if not all(isinstance(v, str) for v in value):
            raise TypeError(f"names['{key}'] must be list[str]")
        data[key] = list(value)
        return
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        if not all(isinstance(v, str) for v in value):
            raise TypeError(f"names['{key}'] must be list[str]")
        data[key] = list(value)
        return
    raise TypeError(f"names['{key}'] must be list[str], got {type(value).__name__}")


def coerce_msc_maincal_names(names: Mapping[str, object] | None) -> MSCMainCalNames:
    """Validate and complete a main-calibration MSC name map."""
    data = _as_name_map(
        names,
        {
            "sg": "sg",
            "a1": "a1",
            "a2": "a2",
            "ant": "ant",
            "pmfwd": "pm1",
            "pmbwd": "pm2",
            "fp": ["fp1", "fp2", "fp3", "fp4", "fp5", "fp6", "fp7", "fp8"],
            "tuner": ["tuner1"],
            "refant": ["refant1"],
            "pmref": ["pmref1"],
        },
    )
    for k in ("sg", "a1", "a2", "ant", "pmfwd", "pmbwd"):
        _require_str(data, k)
    for k in ("fp", "tuner", "refant", "pmref"):
        _require_list_str(data, k)
    return cast(MSCMainCalNames, data)


def coerce_msc_autocorr_names(names: Mapping[str, object] | None) -> MSCAutoCorrNames:
    """Validate and complete an auto-correlation MSC name map."""
    data = _as_name_map(
        names,
        {
            "sg": "sg",
            "a1": "a1",
            "a2": "a2",
            "ant": "ant",
            "pmfwd": "pm1",
            "pmbwd": "pm2",
            "fp": ["fp1", "fp2", "fp3", "fp4", "fp5", "fp6", "fp7", "fp8"],
            "tuner": ["tuner1"],
        },
    )
    for k in ("sg", "a1", "a2", "ant", "pmfwd", "pmbwd"):
        _require_str(data, k)
    for k in ("fp", "tuner"):
        _require_list_str(data, k)
    return cast(MSCAutoCorrNames, data)


def coerce_msc_eutcal_names(names: Mapping[str, object] | None) -> MSCEUTCalNames:
    """Validate and complete an EUT-calibration MSC name map."""
    data = _as_name_map(
        names,
        {
            "sg": "sg",
            "a1": "a1",
            "a2": "a2",
            "ant": "ant",
            "pmfwd": "pm1",
            "pmbwd": "pm2",
            "tuner": ["tuner1"],
            "refant": ["refant1"],
            "pmref": ["pmref1"],
            "fp": [],
        },
    )
    for k in ("sg", "a1", "a2", "ant", "pmfwd", "pmbwd"):
        _require_str(data, k)
    for k in ("tuner", "refant", "pmref", "fp"):
        _require_list_str(data, k)
    return cast(MSCEUTCalNames, data)


def coerce_msc_immunity_names(names: Mapping[str, object] | None) -> MSCImmunityNames:
    """Validate and complete an MSC immunity name map."""
    data = _as_name_map(
        names,
        {
            "sg": "sg",
            "a1": "a1",
            "a2": "a2",
            "ant": "ant",
            "fp": [],
            "pmfwd": "pm1",
            "pmbwd": "pm2",
            "tuner": ["tuner1"],
            "refant": ["refant1"],
            "pmref": ["pmref1"],
        },
    )
    for k in ("sg", "a1", "a2", "ant", "pmfwd", "pmbwd"):
        _require_str(data, k)
    for k in ("fp", "tuner", "refant", "pmref"):
        _require_list_str(data, k)
    return cast(MSCImmunityNames, data)


def coerce_msc_emission_names(names: Mapping[str, object] | None) -> MSCEmissionNames:
    """Validate and complete an MSC emission name map."""
    data = _as_name_map(names, {"tuner": ["tuner1"], "refant": ["refant1"], "receiver": ["saref1"]})
    for k in ("tuner", "refant", "receiver"):
        _require_list_str(data, k)
    return cast(MSCEmissionNames, data)
