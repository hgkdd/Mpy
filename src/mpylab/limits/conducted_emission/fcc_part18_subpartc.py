"""Conducted-emission limits according to FCC Part 18.307 (Subpart C)."""

from inspect import cleandoc

from numpy import array, full_like, log10, nan, piecewise

from mpylab.limits.limit import Limit, log_linear


def uv_to_dbuv(uv):
    """Convert microvolt values to dBµV."""
    return 20.0 * log10(float(uv))


class LIMIT(Limit):
    """Configurable FCC Part 18.307 conducted-emission limit model."""
    description_title = "FCC 47 CFR Part 18.307 (Subpart C), conducted"
    description_case = {
        "Other consumer device": """
            ## All other Part 18 consumer devices

            Conducted limits according to 47 CFR 18.307(b).
        """,
        "Induction/Ultrasonic": """
            ## Induction cooking ranges and ultrasonic equipment

            Conducted limits according to 47 CFR 18.307(a).
        """,
        "RF lighting (consumer)": """
            ## RF lighting devices (consumer)

            Maximum RF line voltage according to 47 CFR 18.307(c).
        """,
        "RF lighting (non-consumer)": """
            ## RF lighting devices (non-consumer)

            Maximum RF line voltage according to 47 CFR 18.307(c).
        """,
    }
    description_detector = {
        "QP": "## Quasi-peak detector / maximum line voltage representation",
        "AV": "## Average detector / maximum line voltage representation",
    }
    source = "47 CFR 18.307 (eCFR / Cornell LII mirror)"
    fmin = 9e3
    fmax = 30e6
    variations = {
        "Case": (
            "Other consumer device",
            "Induction/Ultrasonic",
            "RF lighting (consumer)",
            "RF lighting (non-consumer)",
        ),
        "Detector": ("QP", "AV"),
        "Port": ("AC",),
    }
    unit = "dBµV"

    def __init__(self, case=None, detector=None, port=None):
        super().__init__()
        self.case = "Other consumer device" if case is None else str(case)
        self.detector = "QP" if detector is None else str(detector).upper()
        self.port = "AC" if port is None else str(port)
        self.limitline = None

        if self.case not in self.variations["Case"]:
            raise ValueError(f"FCC Part 18.307: Case must be in {self.variations['Case']}")
        if self.detector not in self.variations["Detector"]:
            raise ValueError(f"FCC Part 18.307: Detector must be in {self.variations['Detector']}")
        if self.port not in self.variations["Port"]:
            raise ValueError(f"FCC Part 18.307: Port must be in {self.variations['Port']}")

        self.description = "".join(
            (
                "# ",
                cleandoc(self.description_title),
                "\n\n",
                cleandoc(self.description_case[self.case]),
                "\n\n",
                cleandoc(self.description_detector[self.detector]),
                "\n\nSource: ",
                self.source,
            )
        )

        try:
            attr = f"limit_{self.case}_{self.detector}"
            attr = attr.replace(" ", "_").replace("-", "_").replace("/", "_")
            attr = attr.replace("(", "").replace(")", "")
            attr = attr.replace("<", "less").replace(">", "over")
            self.limitline = getattr(self, attr)
        except AttributeError:
            self.limitline = self.no_limit

    def _common_150k_to_30m(self, f, qp_start, qp_stop, av_start, av_stop):
        if not isinstance(f, type(array)):
            f = array(f, dtype=float)
        conditions = [(f >= 150e3) & (f < 500e3), (f >= 500e3) & (f < 5e6), (f >= 5e6) & (f <= 30e6)]
        if self.detector == "QP":
            functions = [log_linear(150e3, qp_start, 500e3, qp_stop), qp_stop, 60.0, None]
        else:
            functions = [log_linear(150e3, av_start, 500e3, av_stop), av_stop, 50.0, None]
        return piecewise(f, conditions, functions)

    def limit_Other_consumer_device_QP(self, f):
        """Return QP limits for generic consumer Part 18 devices."""
        return self._common_150k_to_30m(f, 66.0, 56.0, 56.0, 46.0)

    def limit_Other_consumer_device_AV(self, f):
        """Return AV limits for generic consumer Part 18 devices."""
        return self._common_150k_to_30m(f, 66.0, 56.0, 56.0, 46.0)

    def limit_Induction_Ultrasonic_QP(self, f):
        """Return QP limits for induction cooking/ultrasonic equipment."""
        if not isinstance(f, type(array)):
            f = array(f, dtype=float)
        conditions = [
            (f >= 9e3) & (f < 50e3),
            (f >= 50e3) & (f < 150e3),
            (f >= 150e3) & (f < 500e3),
            (f >= 500e3) & (f < 5e6),
            (f >= 5e6) & (f <= 30e6),
        ]
        functions = [110.0, log_linear(50e3, 90.0, 150e3, 80.0), log_linear(150e3, 66.0, 500e3, 56.0), 56.0, 60.0, None]
        return piecewise(f, conditions, functions)

    def limit_Induction_Ultrasonic_AV(self, f):
        """Return AV limits for induction cooking/ultrasonic equipment."""
        if not isinstance(f, type(array)):
            f = array(f, dtype=float)
        # CFR table does not specify AV limit below 150 kHz for this equipment.
        out = full_like(f, nan, dtype=float)
        conditions = [(f >= 150e3) & (f < 500e3), (f >= 500e3) & (f < 5e6), (f >= 5e6) & (f <= 30e6)]
        functions = [log_linear(150e3, 56.0, 500e3, 46.0), 46.0, 50.0, None]
        out = piecewise(f, conditions, functions)
        out[(f >= 9e3) & (f < 150e3)] = nan
        return out

    def limit_RF_lighting_consumer_QP(self, f):
        """Return QP limits for consumer RF lighting equipment."""
        return self._limit_rf_lighting(f, consumer=True)

    def limit_RF_lighting_consumer_AV(self, f):
        """Return AV limits for consumer RF lighting equipment."""
        return self._limit_rf_lighting(f, consumer=True)

    def limit_RF_lighting_non_consumer_QP(self, f):
        """Return QP limits for non-consumer RF lighting equipment."""
        return self._limit_rf_lighting(f, consumer=False)

    def limit_RF_lighting_non_consumer_AV(self, f):
        """Return AV limits for non-consumer RF lighting equipment."""
        return self._limit_rf_lighting(f, consumer=False)

    def _limit_rf_lighting(self, f, consumer):
        if not isinstance(f, type(array)):
            f = array(f, dtype=float)
        if consumer:
            conditions = [(f >= 450e3) & (f < 2.51e6), (f >= 2.51e6) & (f < 3e6), (f >= 3e6) & (f <= 30e6)]
            functions = [uv_to_dbuv(250.0), uv_to_dbuv(3000.0), uv_to_dbuv(250.0), None]
        else:
            conditions = [(f >= 450e3) & (f < 1.6e6), (f >= 1.6e6) & (f <= 30e6)]
            functions = [uv_to_dbuv(1000.0), uv_to_dbuv(3000.0), None]
        return piecewise(f, conditions, functions)


FCC_PART18_307 = PART18_307 = LIMIT
