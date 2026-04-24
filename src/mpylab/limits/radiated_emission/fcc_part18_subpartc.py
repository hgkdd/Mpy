"""Radiated-emission limits according to FCC Part 18.305 (Subpart C)."""

from inspect import cleandoc

from numpy import array, full_like, log10, nan, piecewise

from mpylab.limits.limit import Limit


def uvm_to_dbuvm(uvm):
    """Convert microvolt-per-meter values to dBµV/m."""
    return 20.0 * log10(float(uvm))


class LIMIT(Limit):
    """Configurable FCC Part 18.305 radiated-emission limit model."""
    description_title = "FCC 47 CFR Part 18.305 (Subpart C), radiated"
    description_case = {
        "RF lighting (consumer)": """
            ## RF lighting devices (consumer)

            Field-strength limits according to 47 CFR 18.305(c), measurement distance 30 m.
        """,
        "RF lighting (non-consumer)": """
            ## RF lighting devices (non-consumer)

            Field-strength limits according to 47 CFR 18.305(c), measurement distance 30 m.
        """,
        "Induction cooking range": """
            ## Induction cooking ranges

            Field-strength limits according to 47 CFR 18.305(b), measurement distance 30 m.
        """,
        "Misc non-ISM (<500 W)": """
            ## Miscellaneous ISM equipment outside ISM bands

            Field-strength limits according to 47 CFR 18.305(a), measurement distance 300 m.
        """,
        "Misc ISM (<500 W)": """
            ## Miscellaneous ISM equipment in ISM bands

            Field-strength limits according to 47 CFR 18.305(a), measurement distance 300 m.
        """,
    }
    source = "47 CFR 18.305 (eCFR / Cornell LII mirror)"
    fmin = 9e3
    fmax = 1e9
    variations = {
        "Case": (
            "RF lighting (consumer)",
            "RF lighting (non-consumer)",
            "Induction cooking range",
            "Misc non-ISM (<500 W)",
            "Misc ISM (<500 W)",
        ),
        "Distance": ("30 m", "300 m"),
    }
    unit = "dBµV/m"

    def __init__(self, case=None, distance=None):
        super().__init__()
        self.case = "RF lighting (consumer)" if case is None else str(case)
        self.distance = "30 m" if distance is None else str(distance)
        self.limitline = None

        if self.case not in self.variations["Case"]:
            raise ValueError(f"FCC Part 18.305: Case must be in {self.variations['Case']}")
        if self.distance not in self.variations["Distance"]:
            raise ValueError(f"FCC Part 18.305: Distance must be in {self.variations['Distance']}")

        self.description = "".join(
            (
                "# ",
                cleandoc(self.description_title),
                "\n\n",
                cleandoc(self.description_case[self.case]),
                "\n\nSource: ",
                self.source,
            )
        )

        try:
            attr = f"limit_{self.case}_{self.distance}"
            attr = attr.replace(" ", "_").replace("-", "_").replace("/", "_")
            attr = attr.replace("(", "").replace(")", "")
            attr = attr.replace("<", "less").replace(">", "over")
            self.limitline = getattr(self, attr)
        except AttributeError:
            self.limitline = self.no_limit

    def limit_RF_lighting_consumer_30_m(self, f):
        """Return consumer RF-lighting limits at 30 m."""
        if not isinstance(f, type(array)):
            f = array(f, dtype=float)
        conditions = [(f >= 30e6) & (f < 88e6), (f >= 88e6) & (f < 216e6), (f >= 216e6) & (f <= 1e9)]
        functions = [uvm_to_dbuvm(30.0), uvm_to_dbuvm(50.0), uvm_to_dbuvm(70.0), None]
        return piecewise(f, conditions, functions)

    def limit_RF_lighting_non_consumer_30_m(self, f):
        """Return non-consumer RF-lighting limits at 30 m."""
        if not isinstance(f, type(array)):
            f = array(f, dtype=float)
        conditions = [(f >= 30e6) & (f < 88e6), (f >= 88e6) & (f < 216e6), (f >= 216e6) & (f <= 1e9)]
        functions = [uvm_to_dbuvm(100.0), uvm_to_dbuvm(150.0), uvm_to_dbuvm(200.0), None]
        return piecewise(f, conditions, functions)

    def limit_Induction_cooking_range_30_m(self, f):
        """Return induction-cooking-range limits at 30 m."""
        if not isinstance(f, type(array)):
            f = array(f, dtype=float)
        conditions = [(f >= 9e3) & (f < 90e3), (f >= 90e3)]
        functions = [uvm_to_dbuvm(1500.0), uvm_to_dbuvm(300.0), None]
        return piecewise(f, conditions, functions)

    def limit_Misc_non_ISM_less500_W_300_m(self, f):
        """Return limits for miscellaneous non-ISM equipment below 500 W at 300 m."""
        if not isinstance(f, type(array)):
            f = array(f, dtype=float)
        out = full_like(f, nan, dtype=float)
        out[:] = uvm_to_dbuvm(15.0)
        return out

    def limit_Misc_ISM_less500_W_300_m(self, f):
        """Return limits for miscellaneous ISM equipment below 500 W at 300 m."""
        if not isinstance(f, type(array)):
            f = array(f, dtype=float)
        out = full_like(f, nan, dtype=float)
        out[:] = uvm_to_dbuvm(25.0)
        return out


FCC_PART18_305 = PART18_305 = LIMIT
