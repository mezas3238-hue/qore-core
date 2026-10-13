"""Synthetic-only test witnesses for the frozen EIA first-next curve hypothesis."""
from __future__ import annotations

import unittest
from datetime import date, timedelta

from qore.infrastructure.trader_lab import qore_futures_a_eia_f1f2_predictive_screen_v1 as lab


def synthetic_month(
    year: int, month: int, *, backwardation: bool, outcome_up: bool
) -> tuple[dict[date, float], dict[date, float]]:
    dates = [date(year, month, 1) + timedelta(days=i) for i in range(12)]
    f1: dict[date, float] = {day: 100.0 for day in dates}
    f2: dict[date, float] = {day: 101.0 for day in dates}
    f2[dates[0]] = 99.0 if backwardation else 101.0
    f1[dates[2]] = 100.0
    f1[dates[7]] = 101.0 if outcome_up else 99.0
    return f1, f2


class EiaPreregisteredDiagnosticSyntheticTests(unittest.TestCase):
    def test_hypergeometric_equals_hand_calculated_fisher(self) -> None:
        # [[3,0],[0,3]] right tail = 1/C(6,3) = 0.05
        self.assertAlmostEqual(lab.one_sided_fisher_greater(3, 0, 0, 3), 0.05)
        self.assertAlmostEqual(lab.one_sided_fisher_greater(0, 3, 3, 0), 1.0)
        self.assertAlmostEqual(lab.one_sided_fisher_greater(3, 3, 3, 3), 0.71645021645)

    def test_only_first_common_day_of_month_is_used(self) -> None:
        f1, f2 = synthetic_month(2015, 3, backwardation=True, outcome_up=True)
        ev, audit = lab.build_monthly_events(f1, f2)
        self.assertEqual(len(ev), 1)
        self.assertEqual(ev[0].month, "2015-03")
        self.assertTrue(ev[0].signal_backwardation)
        self.assertTrue(ev[0].reference_f1_up_later)
        self.assertEqual(audit["valid_one_per_month"], 1)

    def test_negative_prices_are_legal_no_log_division(self) -> None:
        f1, f2 = synthetic_month(2020, 4, backwardation=False, outcome_up=False)
        d = date(2020, 4, 1)
        f1[d] = -37.63
        f2[d] = -32.0
        ev, _ = lab.build_monthly_events(f1, f2)
        self.assertEqual(len(ev), 1)
        self.assertFalse(ev[0].signal_backwardation)

    def test_missing_both_contracts_same_month_fails_closed(self) -> None:
        f1, f2 = synthetic_month(2015, 3, backwardation=True, outcome_up=True)
        for k in list(f2)[6:]:
            f2.pop(k)
        ev, audit = lab.build_monthly_events(f1, f2)
        self.assertEqual(ev, [])
        self.assertEqual(audit["not_enough_same_month_observations"], 1)

    def test_zero_spread_or_zero_outcome_get_excluded(self) -> None:
        f1, f2 = synthetic_month(2015, 3, backwardation=True, outcome_up=True)
        f2[date(2015, 3, 1)] = f1[date(2015, 3, 1)]
        ev, aud = lab.build_monthly_events(f1, f2)
        self.assertEqual(ev, [])
        self.assertEqual(aud["spread_ties"], 1)

    def test_inconclusive_sample_requires_at_least_eight_both_states(self) -> None:
        ev = [
            lab.DiagnosticEvent(
                month=f"2015-{m:02d}",
                signal_backwardation=m % 2 == 0,
                reference_f1_up_later=m % 2 == 0,
            )
            for m in range(1, 13)
        ]
        ans = lab.summarize_window(ev, start=2012, end=2018)
        self.assertEqual(ans["decision"], "INCONCLUSIVE_TOO_FEW_MONTHS")
        self.assertIsNone(ans["one_sided_fisher_p"])

    def test_exact_primary_green_threshold_only_when_populated_and_sig(self) -> None:
        ev = [
            lab.DiagnosticEvent(
                month=f"{2012 + i // 12}-{i % 12 + 1:02d}",
                signal_backwardation=i % 2 == 0,
                reference_f1_up_later=i % 2 == 0,
            )
            for i in range(48)
        ]
        ans = lab.summarize_window(ev, start=2012, end=2018)
        self.assertEqual(ans["decision"], "PRELIMINARY_PREREG_WINDOW_PASS")
        self.assertEqual(ans["delta_probability_up"], 1.0)

    def test_primary_screen_uses_no_pnl_and_dev_diag_only(self) -> None:
        self.assertEqual(lab.HOLDOUT_START.isoformat(), "2022-01-01")
        self.assertEqual(lab.P_THRESHOLD, 0.025)
        self.assertEqual(lab.MIN_DELTA, 0.10)
        self.assertEqual(set(lab.SOURCES), {"WTI_F1", "WTI_F2", "NG_F1", "NG_F2"})


if __name__ == "__main__":
    unittest.main()
