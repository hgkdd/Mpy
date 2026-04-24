"""mpylab.limits.conducted_emission.iec_61000_6_3 module."""
from inspect import cleandoc

from mpylab.limits.conducted_emission.en_55032 import LIMIT as CISPR32_LIMIT
from mpylab.limits.limit import Limit


class LIMIT(Limit):
    """LIMIT class."""
    description_title = "IEC 61000-6-3 (generic residential/commercial), conducted"
    description_mapping = """
        This module follows the Academy EMC mapping for generic residential emission and
        uses CISPR 32 Class B conducted limits as practical profile values.
    """
    source = "Academy of EMC standards overview + CISPR 32 profile mapping"
    fmin = 150e3
    fmax = 30e6
    variations = {
        "Detector": ("QP", "AV"),
        "Port": ("Mains", "Telecom/LAN"),
    }
    unit = "dBµV"

    def __init__(self, detector=None, port=None):
        super().__init__()
        self.detector = "QP" if detector is None else str(detector).upper()
        self.port = "Mains" if port is None else str(port)
        if self.detector not in self.variations["Detector"]:
            raise ValueError(f"IEC61000-6-3: Detector must be in {self.variations['Detector']}")
        if self.port not in self.variations["Port"]:
            raise ValueError(f"IEC61000-6-3: Port must be in {self.variations['Port']}")
        self._base = CISPR32_LIMIT(classification="B", detector=self.detector, port=self.port)
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


IEC61000_6_3 = LIMIT
