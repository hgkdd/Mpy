"""Typed name-map contracts and coercion helpers for TEM measurements."""

from __future__ import annotations

from typing import Mapping, Sequence, TypedDict, cast


class TEMImmunityNames(TypedDict):
    """TEMImmunityNames class."""
    sg: str
    a1: str
    a2: str
    tem: str
    pmfwd: str
    pmbwd: str


class TEMEmissionNames(TypedDict):
    """TEMEmissionNames class."""
    port: list[str]
    receiver: list[str]


class TEME0YNames(TypedDict):
    """TEME0YNames class."""
    sg: str
    a1: str
    a2: str
    port: str
    pmfwd: str
    pmbwd: str
    fp: list[str]


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


def coerce_tem_immunity_names(names: Mapping[str, object] | None) -> TEMImmunityNames:
    """coerce_tem_immunity_names function."""
    data = _as_name_map(
        names,
        {"sg": "sg", "a1": "a1", "a2": "a2", "tem": "gtem", "pmfwd": "pm1", "pmbwd": "pm2"},
    )
    for k in ("sg", "a1", "a2", "tem", "pmfwd", "pmbwd"):
        _require_str(data, k)
    return cast(TEMImmunityNames, data)


def coerce_tem_emission_names(names: Mapping[str, object] | None) -> TEMEmissionNames:
    """coerce_tem_emission_names function."""
    data = _as_name_map(names, {"port": ["port"], "receiver": ["analyzer"]})
    for k in ("port", "receiver"):
        _require_list_str(data, k)
    return cast(TEMEmissionNames, data)


def coerce_tem_e0y_names(names: Mapping[str, object] | None) -> TEME0YNames:
    """coerce_tem_e0y_names function."""
    data = _as_name_map(
        names,
        {"sg": "sg", "a1": "a1", "a2": "a2", "port": "port", "pmfwd": "pm1", "pmbwd": "pm2", "fp": ["fp1"]},
    )
    for k in ("sg", "a1", "a2", "port", "pmfwd", "pmbwd"):
        _require_str(data, k)
    _require_list_str(data, "fp")
    return cast(TEME0YNames, data)
