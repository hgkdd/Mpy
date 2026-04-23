from inspect import cleandoc

from mpylab.limits.conducted_emission.en_55011 import LIMIT as CISPR11_LIMIT
from mpylab.limits.limit import Limit


class LIMIT(Limit):
    description_title = "IEC 61000-6-4 (generic industrial), conducted"
    description_mapping = """
        This module follows the Academy EMC mapping for generic industrial emission and
        uses CISPR 11 Group 1 Class A conducted limits as practical profile values.
    """
    source = "Academy of EMC standards overview + CISPR 11 profile mapping"
    fmin = 150e3
    fmax = 30e6
    variations = {
        "Detector": ("QP", "AV"),
        "Port": ("AC (≤ 20 kVA)", "AC (≤ 75 kVA)", "AC (> 75 kVA)", "DC (≤ 20 kVA)", "DC (≤ 75 kVA)", "DC (> 75 kVA)"),
    }
    unit = "dBµV"

    def __init__(self, detector=None, port=None):
        super().__init__()
        self.detector = "QP" if detector is None else str(detector).upper()
        self.port = "AC (≤ 20 kVA)" if port is None else str(port)
        if self.detector not in ("QP", "AV"):
            raise ValueError(f"IEC61000-6-4: Detector must be in {self.variations['Detector']}")
        if self.port not in self.variations["Port"]:
            raise ValueError(f"IEC61000-6-4: Port must be in {self.variations['Port']}")
        self._base = CISPR11_LIMIT(group="1", classification="A", detector=self.detector, port=self.port)
        self.limitline = self._base.limitline
        self.description = "".join(
            (
                "# ",
                cleandoc(self.description_title),
                "\n\n",
                cleandoc(self.description_mapping),
                "\n\nSource: ",
                self.source,
            )
        )


IEC61000_6_4 = LIMIT
