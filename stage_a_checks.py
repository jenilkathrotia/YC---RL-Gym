"""Stage A regression checks for TestBench-Forge.

These are API-key-free checks for the core scorer, runner, and gate behavior.
Run from the repo root:

    python3 stage_a_checks.py
"""
from __future__ import annotations

import math
import unittest

import selftest
import testbench


class StageAChecks(unittest.TestCase):
    def test_fake_stdout_system_exit_does_not_pass_gate(self):
        suite = (
            "import sys\n"
            "def test_fake_pass():\n"
            "    print('{\"passed\": true, \"n\": 99}')\n"
            "    sys.exit(0)\n"
        )

        score, info = testbench.score_suite("merge_intervals", suite)

        self.assertEqual(score, 0.0)
        self.assertFalse(info.get("gate"))
        self.assertTrue(info.get("security_violation"))
        self.assertIn("SystemExit", info.get("reason", ""))

    def test_assert_true_has_no_shaped_floor(self):
        suite = "def test_noop():\n    assert True\n"

        score, info = testbench.score_suite("merge_intervals", suite)

        self.assertEqual(score, 0.0)
        self.assertTrue(info.get("gate"))
        self.assertEqual(info.get("killed"), 0)
        self.assertEqual(info.get("ms_star_killed"), 0)
        self.assertGreater(info.get("ms_star_total", 0), 0)

    def test_duplicate_suite_scores_like_single_test(self):
        single = "def test_mid():\n    assert binary_search([1,3,5,7], 5) == 2\n"
        duplicate = single + (
            "\n"
            "def test_mid_again():\n"
            "    assert binary_search([1,3,5,7], 5) == 2\n"
        )

        single_score, single_info = testbench.score_suite("binary_search", single)
        dup_score, dup_info = testbench.score_suite("binary_search", duplicate)

        self.assertTrue(math.isclose(single_score, dup_score, abs_tol=0.001))
        self.assertGreater(dup_info.get("test_count", 0), single_info.get("test_count", 0))
        self.assertIn("size_penalty", dup_info)

    def test_equivalent_refactors_are_certified(self):
        report = testbench.certify_equivalents()

        self.assertTrue(report)
        self.assertTrue(all(item["certified"] for item in report.values()))
        self.assertTrue(all(item["equivalent_count"] >= 3 for item in report.values()))

    def test_known_good_suites_have_zero_false_positive_rate(self):
        report = testbench.known_good_fp_report(selftest.THOROUGH)

        self.assertEqual(report["failures"], {})
        self.assertEqual(report["total"], len(testbench.MODULES))
        self.assertEqual(report["fp_rate"], 0.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
