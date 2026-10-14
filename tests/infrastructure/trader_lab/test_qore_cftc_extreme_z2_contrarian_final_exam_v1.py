"""Adversarial synthetic tests for the ONE Z2 contrarian scientific family."""
from __future__ import annotations

import math
import unittest
from datetime import date, timedelta

import qore_cftc_extreme_z2_contrarian_final_exam_v1 as z


def _events(successes: int, n: int, year: int) -> list[z.Extreme]:
    start = date(year, 4, 1)
    output = []
    for i in range(n):
        stamp = start + timedelta(days=7 * i)
        output.append(z.Extreme(
            report_date=stamp, z=2.2 if i % 2 else -2.2,
            sign=1 if i % 2 else -1,
            entry_date=stamp + timedelta(days=21),
            exit_date=stamp + timedelta(days=63),
            correct_reversal=i < successes,
        ))
    return output


class TestZ2ContrarianSingleExam(unittest.TestCase):
    def test_frozen_parameters_not_swept(self) -> None:
        self.assertEqual(z.PREREG_SHA, "1cca3399514125ba11ae446a059e09382c605d40")
        self.assertEqual(z.Z_LOOKBACK, 104)
        self.assertEqual(z.Z_THRESHOLD, 2.0)
        self.assertEqual(z.ENTRY_LAG_CALENDAR_DAYS, 21)
        self.assertEqual(z.EXIT_HORIZON_CALENDAR_DAYS, 42)
        self.assertEqual(z.COOLDOWN_REPORTS, 8)
        self.assertEqual(z.ALPHA_PER_MARKET, 0.025)
        self.assertEqual(z.MIN_EVENTS_EACH_WINDOW, 8)

    def test_zscore_uses_only_prior_104_values(self) -> None:
        start = date(2012, 1, 3)
        rows = [
            z.CftcPosition(start + timedelta(days=7 * i), float(i % 7) / 100)
            for i in range(105)
        ]
        self.assertIsNone(z._z(rows, 103))
        value = z._z(rows, 104)
        self.assertIsNotNone(value)
        self.assertTrue(math.isfinite(value))
        with_huge_current = rows[:-1] + [
            z.CftcPosition(rows[-1].report_date, 10000000.0)
        ]
        self.assertGreater(z._z(with_huge_current, 104), 1000.0)

    def test_zero_variance_means_no_synthetic_extreme(self) -> None:
        start = date(2012, 1, 3)
        rows = [
            z.CftcPosition(start + timedelta(days=7 * i), 0.0)
            for i in range(105)
        ]
        self.assertIsNone(z._z(rows, 104))

    def test_only_crossing_with_lag_and_nonoverlap(self) -> None:
        base = date(2012, 1, 3)
        rows = [
            z.CftcPosition(base + timedelta(days=i * 7), (i % 7) / 1000)
            for i in range(260)
        ]
        for index, value in ((122, 0.50), (123, 0.51), (135, -0.50), (136, -0.51)):
            rows[index] = z.CftcPosition(rows[index].report_date, value)
        first_day = base
        prices = {
            first_day + timedelta(days=i): float(i)
            for i in range(2000)
        }
        found, audit = z.select_events(rows, prices)
        self.assertGreaterEqual(audit["crossing_candidates"], 2)
        for item in found:
            self.assertGreaterEqual(
                (item.entry_date - item.report_date).days,
                z.ENTRY_LAG_CALENDAR_DAYS,
            )
            self.assertGreaterEqual(
                (item.exit_date - item.entry_date).days,
                z.EXIT_HORIZON_CALENDAR_DAYS,
            )
        for a, b in zip(found, found[1:]):
            self.assertGreater(b.entry_date, a.exit_date)
        self.assertEqual(len({e.report_date for e in found}), len(found))

    def test_no_reserved_window_even_if_prices_supplied(self) -> None:
        self.assertIsNone(z._window(date(2022, 1, 1)))
        self.assertIsNone(z._window(date(2013, 12, 31)))
        self.assertEqual(z._window(date(2020, 5, 1)), "diag")
        self.assertIsNone(z._window(date(2024, 4, 1)))

    def test_inconclusive_when_less_than_eight_or_one_side_only(self) -> None:
        for sample in (_events(6, 6, 2017), _events(9, 9, 2017)):
            if len(sample) == 9:
                sample = [
                    z.Extreme(e.report_date, e.z, 1, e.entry_date,
                              e.exit_date, e.correct_reversal)
                    for e in sample
                ]
            with self.subTest(n=len(sample)):
                result = z.adjudicate(sample, "dev")
                self.assertEqual(
                    result["decision"],
                    "INCONCLUSIVE_INSUFFICIENT_INDEPENDENT_EXTREMES",
                )
                self.assertIsNone(result["exact_one_sided_p"])

    def test_positive_synthetic_fixture_vs_negative(self) -> None:
        positive = z.adjudicate(_events(15, 16, 2017), "dev")
        negative = z.adjudicate(_events(8, 16, 2017), "dev")
        self.assertEqual(positive["decision"], "PRELIMINARY_SUPPORT")
        self.assertLess(positive["exact_one_sided_p"], 0.025)
        self.assertEqual(negative["decision"], "NO_SUPPORT")
        self.assertGreater(negative["exact_one_sided_p"], 0.025)

    def test_dev_diag_split_does_not_mix_outcomes(self) -> None:
        test = _events(15, 16, 2017) + _events(4, 16, 2020)
        self.assertEqual(z.adjudicate(test, "dev")["correct_reversals"], 15)
        self.assertEqual(z.adjudicate(test, "diag")["correct_reversals"], 4)

    def test_exact_binomial_and_no_parameter_refitting(self) -> None:
        self.assertAlmostEqual(z._one_sided_sign_p(8, 8), 1 / 256)
        self.assertAlmostEqual(z._one_sided_sign_p(8, 4), 163 / 256)
        with self.assertRaises(ValueError):
            z._one_sided_sign_p(0, 0)
        with self.assertRaises(ValueError):
            z.adjudicate([], "oos")


if __name__ == "__main__":
    unittest.main()
