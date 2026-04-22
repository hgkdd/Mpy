# -*- coding: utf-8 -*-
"""Compatibility launcher for the generic network analyzer test utility.

The ZVL-specific UI has been merged into :mod:`mpylab.device.networkanalyzer_ui`.
Keep this module so existing launch commands continue to work.
"""

import sys

from mpylab.device.networkanalyzer_ui import NetworkAnalyzerWidget, main


UI = NetworkAnalyzerWidget


if __name__ == "__main__":
    sys.exit(main())
