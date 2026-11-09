"""Numerical and scope checks for outcome-free paired-power planning."""
import importlib.util
import math
from pathlib import Path
import unittest

from scipy.stats import binomtest

MODULE = Path(__file__).resolve().parents[1] / 'analysis/publication_power.py'
spec = importlib.util.spec_from_file_location('publication_power', MODULE)
pp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pp)


def brute_power(n, gain, q, alpha):
    total = 0.0
    for w in range(n + 1):
        for loss in range(n - w + 1):
            k = w + loss
            if not k or w <= loss:
                continue
            if binomtest(w, k, .5).pvalue <= alpha:
                rest = n - k
                coefficient = math.factorial(n) / (math.factorial(w) *
                                                    math.factorial(loss) *
                                                    math.factorial(rest))
                total += coefficient * ((q+gain)/2) ** w * ((q-gain)/2) ** loss * (1-q) ** rest
    return total


class PublicationPowerTests(unittest.TestCase):
    def test_exact_power_matches_direct_multinomial_enumeration(self):
        for n, gain, q, alpha in [(8, .1, .4, .05), (12, .2, .4, .05),
                                  (10, .3, 1., .1), (15, .1, .5, .0125),
                                  (8, 0., .4, .05), (6, .5, .5, .05)]:
            with self.subTest(n=n, gain=gain, q=q, alpha=alpha):
                self.assertAlmostEqual(pp.exact_paired_superiority_power(n, gain, q, alpha),
                                       brute_power(n, gain, q, alpha), places=12)

    def test_zero_discordance_does_not_create_power(self):
        self.assertEqual(pp.exact_paired_superiority_power(1000, 0, 0), 0)

    def test_identically_favourable_cases_need_enough_discordances(self):
        self.assertEqual(pp.exact_paired_superiority_power(5, 1, 1, .05), 0)
        self.assertAlmostEqual(pp.exact_paired_superiority_power(6, 1, 1, .05), 1)

    def test_invalid_distribution_rejected(self):
        for args in [(0, .1, .4), (True, .1, .4), (10, .5, .1),
                     (10, -.1, .1), (10, .1, 1.1)]:
            with self.subTest(args=args), self.assertRaises(ValueError):
                pp.exact_paired_superiority_power(*args)

    def test_grid_result_is_explicitly_not_minimum_integer_n(self):
        answer = pp.first_adequate_grid_n(.2, .4, .8, grid=(20, 100, 500))
        self.assertTrue(answer['not_a_minimal_integer_n'])
        self.assertIn(answer['first_adequate_grid_n'], (20, 100, 500))
        self.assertGreaterEqual(answer['achieved_power'], .8)

    def test_ni_null_or_adverse_slack_has_no_recommended_n(self):
        self.assertIsNone(pp.ni_normal_planning_n(.2, .02, .01, .95))
        self.assertIsNone(pp.ni_normal_planning_n(.2, .02, .02, .95))
        self.assertIsNone(pp.ni_normal_planning_n(0, 0, .02, .95))

    def test_tighter_hypothetical_margin_requires_more_incidents(self):
        self.assertGreater(pp.ni_normal_planning_n(.2, 0, .01, .95),
                           pp.ni_normal_planning_n(.2, 0, .05, .95))

    def test_inventory_does_not_open_saved_outcomes(self):
        result = pp.audit_available_family_pool()
        self.assertEqual(result['fresh_usable_family_count'], 0)
        self.assertEqual(result['previously_assigned_calibration_families'], 20)
        self.assertEqual(result['previously_assigned_diagnostic_families'], 212)
        self.assertFalse(result['saved_outcomes_opened'])


if __name__ == '__main__':
    unittest.main()
