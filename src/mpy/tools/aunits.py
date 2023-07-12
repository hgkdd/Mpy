# -*- coding: utf-8 -*-

from scuq import units, si

AMPLITUDERATIO = units.AlternateUnit('(V/V)', si.VOLT / si.VOLT)
POWERRATIO = units.AlternateUnit('(W/W)', si.WATT / si.WATT)   # AMPLITUDERATIO ** 2
EFIELD = si.VOLT / si.METER
EFIELDPNORM = EFIELD / si.WATT.sqrt()
HFIELD = si.AMPERE / si.METER
POYNTING = si.WATT / (si.METER ** 2)
