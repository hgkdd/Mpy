from inspect import cleandoc

from numpy import array, piecewise

from mpylab.limits.limit import Limit, log_linear


class LIMIT(Limit):
    description_title = "FCC 47 CFR Part 15.107 (Subpart B), conducted"
    description_Classification = {
        "A": """
             ## Class A digital device

             Class A limits for equipment connected to public utility (AC) power lines.
             """,
        "B": """
             ## Class B digital device

             Class B limits for equipment connected to public utility (AC) power lines.
             """,
    }
    description_Detector = {
        "QP": """
              ## Quasi-peak detector
              """,
        "AV": """
              ## Average detector
              """,
    }
    source = "47 CFR 15.107 (eCFR / Cornell LII mirror)"
    fmin = 150e3
    fmax = 30e6
    variations = {
        "Classification": ("A", "B"),
        "Detector": ("QP", "AV"),
        "Port": ("AC",),
    }
    unit = "dBµV"

    def __init__(self, classification=None, detector=None, port=None):
        super().__init__()
        self.classification = "B" if classification is None else str(classification).upper()
        self.detector = "QP" if detector is None else str(detector).upper()
        self.port = "AC" if port is None else str(port)
        self.limitline = None

        if self.classification not in self.variations["Classification"]:
            raise ValueError(f"FCC Part 15.107: Classification must be in {self.variations['Classification']}")
        if self.detector not in self.variations["Detector"]:
            raise ValueError(f"FCC Part 15.107: Detector must be in {self.variations['Detector']}")
        if self.port not in self.variations["Port"]:
            raise ValueError(f"FCC Part 15.107: Port must be in {self.variations['Port']}")

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

        try:
            attr = f"limit_C{self.classification}_{self.port}_{self.detector}".replace(" ", "_")
            self.limitline = getattr(self, attr)
        except AttributeError:
            self.limitline = self.no_limit

    def limit_CB_AC_QP(self, f):
        if not isinstance(f, type(array)):
            f = array(f, dtype=float)
        conditions = [(f >= 150e3) & (f < 500e3), (f >= 500e3) & (f < 5e6), (f >= 5e6) & (f <= 30e6)]
        functions = [log_linear(150e3, 66, 500e3, 56), 56, 60, None]
        return piecewise(f, conditions, functions)

    def limit_CB_AC_AV(self, f):
        if not isinstance(f, type(array)):
            f = array(f, dtype=float)
        conditions = [(f >= 150e3) & (f < 500e3), (f >= 500e3) & (f < 5e6), (f >= 5e6) & (f <= 30e6)]
        functions = [log_linear(150e3, 56, 500e3, 46), 46, 50, None]
        return piecewise(f, conditions, functions)

    def limit_CA_AC_QP(self, f):
        if not isinstance(f, type(array)):
            f = array(f, dtype=float)
        conditions = [(f >= 150e3) & (f < 500e3), (f >= 500e3) & (f <= 30e6)]
        functions = [79, 73, None]
        return piecewise(f, conditions, functions)

    def limit_CA_AC_AV(self, f):
        if not isinstance(f, type(array)):
            f = array(f, dtype=float)
        conditions = [(f >= 150e3) & (f < 500e3), (f >= 500e3) & (f <= 30e6)]
        functions = [66, 60, None]
        return piecewise(f, conditions, functions)


FCC_PART15_107 = PART15_107 = LIMIT
