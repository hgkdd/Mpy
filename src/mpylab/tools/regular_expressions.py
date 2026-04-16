# -*- coding: utf-8 -*-
"""
This is the :mod:`mpylab.tools.regular_expressions` module.

   :author: Hans Georg Krauthäuser (main author)

   :license: GPLv3 or higher
"""
import re

FP = r'[-+]?(\d+(\.\d*)?|\d*\.\d+)([eE][-+]?\d+)?'
FP_anchor_start = r'^[-+]?(\d+(\.\d*)?|\d*\.\d+)([eE][-+]?\d+)?'
FP_anchor_end = r'[-+]?(\d+(\.\d*)?|\d*\.\d+)([eE][-+]?\d+)?$'

_INLINE_FILE_RE = re.compile(
    r"""^io\.StringIO\(\s*format_block\(\s*([\"']{3})(.*)\1\s*\)\s*\)\s*$""",
    re.DOTALL,
)

_INLINE_FILE_BLOCK_RE = re.compile(
    r"""io\.StringIO\(\s*format_block\(\s*([\"']{3})(.*?)\1\s*\)\s*\)""",
    re.DOTALL,
)
