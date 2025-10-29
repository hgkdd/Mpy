# -*- coding: utf-8 -*-
"""
This is :mod:`mpylab.tools.aunits`.

   Provides alternative units based on scuq.si units

   :author: Hans Georg Krauthäuser (main author)

   :license: GPLv3 or higher
"""

from scuq.units import AlternateUnit
from scuq.si import VOLT, WATT, METER, AMPERE

AMPLITUDERATIO = AlternateUnit('(V/V)', VOLT / VOLT)
POWERRATIO = AlternateUnit('(W/W)', WATT / WATT)   # AMPLITUDERATIO ** 2
EFIELD = VOLT / METER
EFIELDPNORM = EFIELD / WATT.sqrt()
HFIELD = AMPERE / METER
POYNTING = WATT / (METER ** 2)
