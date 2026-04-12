# -*- coding: utf-8 -*-
"""
This is the :mod:`mpylab.tools.regular_expressions` module.

   :author: Hans Georg Krauthäuser (main author)

   :license: GPLv3 or higher
"""

FP = r'[-+]?(\d+(\.\d*)?|\d*\.\d+)([eE][-+]?\d+)?'
FP_anchor_start = r'^[-+]?(\d+(\.\d*)?|\d*\.\d+)([eE][-+]?\d+)?'
FP_anchor_end = r'[-+]?(\d+(\.\d*)?|\d*\.\d+)([eE][-+]?\d+)?$'
