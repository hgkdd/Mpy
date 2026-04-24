"""mpylab.limits.radiated_emission.iec_61000_6_4 module."""
from inspect import cleandoc

from mpylab.limits.limit import Limit
from mpylab.limits.radiated_emission.en_55011 import LIMIT as CISPR11_LIMIT


class LIMIT(Limit):
    """LIMIT class."""
    description_title = "IEC 61000-6-4 (generic industrial), radiated"
    description_mapping = """
        This module follows the Academy EMC mapping for generic industrial emission and
        uses CISPR 11 Group 1 Class A radiated profile combinations where available.
    """
    source = "Academy of EMC standards overview + CISPR 11 profile mapping"
    fmin = 30e6
    fmax = 6e9
    variations = {
        "Detector": ("QP", "AV", "PK"),
        "Distance": ("3 m", "10 m"),
    }
    unit = "dBµV/m"

    def __init__(self, detector=None, distance=None):
        super().__init__()
        self.detector = "QP" if detector is None else str(detector).upper()
        self.distance = "10 m" if distance is None else str(distance)
        if self.detector not in self.variations["Detector"]:
            raise ValueError(f"IEC61000-6-4: Detector must be in {self.variations['Detector']}")
        if self.distance not in self.variations["Distance"]:
            raise ValueError(f"IEC61000-6-4: Distance must be in {self.variations['Distance']}")
        self._base = CISPR11_LIMIT(
            group="1",
            classification="A",
            detector=self.detector,
            port="AC (≤ 20 kVA)",
            distance=self.distance,
        )
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
