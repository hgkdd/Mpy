.. -*-coding: utf-8 -*-

Directory structure
-------------------

Main directory of ``MpyLab``:
    * ``src/mpylab``: general source files tree of the framework
    * ``test``: special measurement programs that access the framework. Mainly for testing.
    * ``doc``: documentation tree

Subdirectory ``src/mpylab``:
    * ``device``: drivers for active and passive devices
    * ``env``: measurement environments (MVK, GTEM cell)
    * ``tools``: all kinds of utility programs and functions

Subdirectory ``device``:
    * ``device.py``: wrapper for rewriting old drivers (in ``C``; no longer used) to new ones and providing a uniform interface for the upper layer
    * ``driver.py``: the mother of all new drivers written in Python

Below this, there are different classes of drivers for different device types:
    * ``amplifier.py``: for amplifiers
    * ``nport.py``: for antennas, cables, directional couplers, etc.
    * ``powermeter.py``: for power meters
    * ``signalgenerator.py``: for signal generators
    * ...

There are also special drivers for specific devices, e.g.:
    * ``amp_ifi_smx25.py``: Amplifier from IFI, type SMX25
    * ``pm_gt_8540c.py``: Power meter from GigaTronics, type 8542C Universal Power Meter
    * ``sg_rs_smr.py``: Signal generator from Rohde&Schwarz, type SMR
    * ``sg_rs_swm.py``: Signal generator from Rohde&Schwarz, type SWM

The syntax is therefore ``amp/pm/sg_<manufacturer abbreviation>_<type abbreviation>.py``