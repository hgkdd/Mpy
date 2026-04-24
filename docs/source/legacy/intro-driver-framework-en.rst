.. -*-coding: utf-8 -*-

Implementing Drivers with the Legacy Driver Framework
======================================================

This document describes the historical metaclass-based driver framework.
That approach is archived and no longer used by active drivers.

Related legacy modules are kept under ``mpylab.device.legacy`` for reference only.
New drivers should use ``mpylab.device.driver.DRIVER`` and the active device base
classes instead.

Historical note
---------------

The original German text in this repository explains the old workflow in depth.
It is preserved for historical context, but should not be used as a template for
new driver implementations.

Current recommendation
----------------------

For new implementations:

- use the active driver base classes from ``src/mpylab/device``
- define command dictionaries and behavior in active (non-legacy) modules
- keep API docstrings in English
- avoid introducing new dependencies on ``mpylab.device.legacy``
