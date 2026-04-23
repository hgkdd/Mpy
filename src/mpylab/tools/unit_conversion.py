"""Backward-compatible unit conversion facade.

Historically this module contained its own conversion logic. The canonical
implementation now lives in :mod:`mpylab.tools.uconv`. This module keeps the
legacy API and delegates all behavior to that single code base.
"""

from mpylab.tools.uconv import (
    UConv,
    _addsum,
    _ident,
    _mulfac,
    _from_dBfac,
    _to_dBfac,
    dB2lin,
    dBm2W,
    dBm2mW,
    dBuV2V,
    dBuV2uV,
    from_quantity,
    lin2dB,
    mW2dBm,
    to_quantity,
    uV2dBuV,
    V2dBuV,
    W2dBm,
)

# Backward-compatible dictionary names.
uconv_to_quantity = UConv.uconv
uconv_from_quantity = UConv.uconv_from_quantity


if __name__ == "__main__":
    def _assert_close(name, actual, expected, tol=1e-12):
        if abs(actual - expected) > tol:
            raise AssertionError(f"{name}: expected {expected}, got {actual}")

    print("Running unit_conversion compatibility self-test...")

    # 1) Legacy dict names are still accessible.
    if "dbm" not in uconv_to_quantity:
        raise AssertionError("uconv_to_quantity missing expected key 'dbm'")
    if "W" not in uconv_from_quantity:
        raise AssertionError("uconv_from_quantity missing expected key 'W'")
    print("OK: legacy dict names available")

    # 2) Legacy function names still work and use canonical backend.
    q = to_quantity("dBm", 0.0)
    back = from_quantity("dbm", q)
    _assert_close("dBm roundtrip", back, 0.0, tol=1e-9)
    print("OK: to_quantity/from_quantity wrappers")

    # 3) lin/dB helpers still behave as before.
    _assert_close("W2dBm", W2dBm(1e-3), 0.0)
    _assert_close("dBm2W", dBm2W(0.0), 1e-3)
    _assert_close("V2dBuV", V2dBuV(1e-6), 0.0)
    _assert_close("dBuV2V", dBuV2V(0.0), 1e-6)
    print("OK: named linear/dB converters")

    # 4) Factory helpers are still present.
    lin = dB2lin(10, 1e-3)
    db = lin2dB(10, 1e3)
    _assert_close("factory dB2lin", lin(0.0), 1e-3)
    _assert_close("factory lin2dB", db(1e-3), 0.0)
    print("OK: factory helpers")

    print("unit_conversion compatibility self-test passed.")
