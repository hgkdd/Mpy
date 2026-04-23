import os
import sys
import unittest


_THIS_DIR = os.path.dirname(__file__)
if _THIS_DIR and _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

import test_env_refactor_pr1_pr2 as ref_tests


class TestEnvSmoke(unittest.TestCase):
    """Fast smoke entry for core env measurement paths."""

    test_amplifiertest_smoke = ref_tests.TestEnvRefactorPR1PR2.test_amplifiertest_measure_smoke_with_fake_graph
    test_msc_maincal_smoke = ref_tests.TestEnvRefactorPR1PR2.test_msc_measure_maincal_e2e_with_fake_graph
    test_temcell_e0y_smoke = ref_tests.TestEnvRefactorPR1PR2.test_temcell_measure_e0y_e2e_with_fake_graph


if __name__ == "__main__":
    unittest.main()
