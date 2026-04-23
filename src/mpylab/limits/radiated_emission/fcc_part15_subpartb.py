from inspect import cleandoc

from numpy import array, full_like, log10, nan, piecewise

from mpylab.limits.limit import Limit


def uv_to_dbuv(uv_per_m):
    return 20.0 * log10(float(uv_per_m))


class LIMIT(Limit):
    description_title = "FCC 47 CFR Part 15.109 (Subpart B), radiated"
    description_Classification = {
        "A": """
             ## Class A digital device

             Reference distance for the tabulated limits: 10 m.
             """,
        "B": """
             ## Class B digital device

             Reference distance for the tabulated limits: 3 m.
             """,
    }
    description_Detector = {
        "QP": """
              ## Quasi-peak detector

              Implemented for 30 MHz to 960 MHz.
              """,
        "AV": """
              ## Average detector

              Implemented for frequencies above 960 MHz.
              """,
        "PK": """
              ## Peak detector

              Implemented as average + 20 dB above 960 MHz (per 47 CFR 15.35 relationship).
              """,
    }
    source = "47 CFR 15.109 and 15.35 (eCFR / Cornell LII mirror)"
    fmin = 30e6
    fmax = 6e9
    variations = {
        "Classification": ("A", "B"),
        "Detector": ("QP", "AV", "PK"),
        "Distance": ("3 m", "10 m"),
    }
    unit = "dBµV/m"

    def __init__(self, classification=None, detector=None, distance=None):
        super().__init__()
        self.classification = "B" if classification is None else str(classification).upper()
        self.detector = "QP" if detector is None else str(detector).upper()
        self.distance = "3 m" if distance is None else str(distance)
        self.limitline = None

        if self.classification not in self.variations["Classification"]:
            raise ValueError(f"FCC Part 15.109: Classification must be in {self.variations['Classification']}")
        if self.detector not in self.variations["Detector"]:
            raise ValueError(f"FCC Part 15.109: Detector must be in {self.variations['Detector']}")
        if self.distance not in self.variations["Distance"]:
            raise ValueError(f"FCC Part 15.109: Distance must be in {self.variations['Distance']}")

        self.description = "".join(
            (
                "# ",
                cleandoc(self.description_title),
                "\n\n",
                cleandoc(self.description_Classification[self.classification]),
                "\n\n",
                cleandoc(self.description_Detector[self.detector]),
                "\n\nSource: ",
                self.source,
            )
        )

        # The CFR table defines Class B at 3 m and Class A at 10 m.
        # Non-native combinations intentionally fall back to no_limit.
        if (self.classification, self.distance) not in (("A", "10 m"), ("B", "3 m")):
            self.limitline = self.no_limit
            return

        try:
            attr = f"limit_C{self.classification}_{self.distance}_{self.detector}".replace(" ", "_")
            self.limitline = getattr(self, attr)
        except AttributeError:
            self.limitline = self.no_limit

    def _table_class_b_3m(self, f):
        if not isinstance(f, type(array)):
            f = array(f, dtype=float)
        conditions = [(f >= 30e6) & (f < 88e6), (f >= 88e6) & (f < 216e6), (f >= 216e6) & (f <= 960e6)]
        functions = [uv_to_dbuv(100), uv_to_dbuv(150), uv_to_dbuv(200), None]
        return piecewise(f, conditions, functions)

    def _table_class_a_10m(self, f):
        if not isinstance(f, type(array)):
            f = array(f, dtype=float)
        conditions = [(f >= 30e6) & (f < 88e6), (f >= 88e6) & (f < 216e6), (f >= 216e6) & (f <= 960e6)]
        functions = [uv_to_dbuv(90), uv_to_dbuv(150), uv_to_dbuv(210), None]
        return piecewise(f, conditions, functions)

    def _above_960_average(self, f, uv_value):
        if not isinstance(f, type(array)):
            f = array(f, dtype=float)
        out = full_like(f, nan, dtype=float)
        mask = f > 960e6
        out[mask] = uv_to_dbuv(uv_value)
        return out

    def limit_CB_3_m_QP(self, f):
        return self._table_class_b_3m(f)

    def limit_CA_10_m_QP(self, f):
        return self._table_class_a_10m(f)

    def limit_CB_3_m_AV(self, f):
        return self._above_960_average(f, 500)

    def limit_CA_10_m_AV(self, f):
        return self._above_960_average(f, 300)

    def limit_CB_3_m_PK(self, f):
        return self.limit_CB_3_m_AV(f) + 20.0

    def limit_CA_10_m_PK(self, f):
        return self.limit_CA_10_m_AV(f) + 20.0


FCC_PART15_109 = PART15_109 = LIMIT
