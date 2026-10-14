"""Synthetic adversarial H-TOM-1 tests; NEVER trade or use real holdouts."""
from __future__ import annotations

import unittest
from datetime import UTC, date, datetime, timedelta

from qore.infrastructure.trader_lab import qore_native_us_index_tom_single_exam_v1 as q


def _fixes() -> dict[date, q.CashFix]:
    out: dict[date, q.CashFix] = {}
    start = date(2021, 12, 1)
    for i in range(130):
        d = start + timedelta(days=i)
        if d.weekday() >= 5:
            continue
        utc = datetime(d.year, d.month, d.day, 20, 55, tzinfo=UTC)
        out[d] = q.CashFix(d, utc, 100_000 + 100 * i, 78)
    return out


class TestQoreNativeSingleEconomicHypothesis(unittest.TestCase):
    def test_invariants_precommitted(self) -> None:
        self.assertEqual(q.PREREG_SHA, "358d2d0e9691a95bbd9c121ea62b0075c2182975")
        self.assertEqual(q.SYMBOLS, ("SP500", "US30", "NAS100"))
        self.assertEqual(q.EMBARGO, date(2024, 9, 17))
        self.assertEqual(q.CASH_LAST_BAR, (15, 55))
        self.assertEqual(q.STRESS_RT_BPS, (5, 10, 20))
        self.assertEqual(q.BSTRAP_BLOCK_MONTHS, 3)
        self.assertEqual(q.BSTRAP_DRAWS, 4000)

    def test_reconstructed_sessions_reject_missing_or_nonpositive(self) -> None:
        d = date(2020, 3, 2)
        at = datetime(2020, 3, 2, 20, 55, tzinfo=UTC)
        result = q._qualifying_dates(
            {d: 59, date(2020, 3, 3): 78},
            {d: (at, 100), date(2020, 3, 3): (at, -1)},
        )
        self.assertFalse(result)

    def test_one_paired_event_per_month_and_fixed_control_sessions(self) -> None:
        # Split starts at 2016-11 so fixture's 2022 period is DIAG or excluded.
        result, audit = q.paired_months(_fixes())
        self.assertEqual(audit["months_complete"], 0)
        self.assertEqual(result["dev"], [])
        self.assertEqual(result["diag"], [])

    def test_reference_pair_on_diagnostic_month(self) -> None:
        fixes = _fixes()
        shifted = {}
        for d, fix in fixes.items():
            # Move four calendar years back into prereg DEV.
            nd = d.replace(year=d.year - 4)
            shifted[nd] = q.CashFix(nd, fix.at_utc, fix.reference_open, 78)
        months, audit = q.paired_months(shifted)
        self.assertGreaterEqual(audit["dev_months"], 2)
        self.assertTrue(all(x.tom_bps - x.control_bps == x.excess_bps for x in months["dev"]))

    def test_no_month_selected_from_outcomes_and_duplicate_fail(self) -> None:
        fixes = _fixes()
        d = next(iter(fixes))
        corrupted = dict(fixes)
        corrupted[d] = q.CashFix(date(2000, 1, 1), fixes[d].at_utc, 1, 78)
        with self.assertRaisesRegex(ValueError, "INVALID_REFERENCE_FIXTURE"):
            q.paired_months(corrupted)

    def test_underpowered_refuses_any_promotion(self) -> None:
        row = q.PairedMonth("2017-01", 100.0, -10.0, 110.0)
        out = q.summarize([row] * 3, seed=10, primary=True, period="dev")
        self.assertEqual(out["verdict"], "INCONCLUSIVE_COVERAGE")
        self.assertIsNone(out["paired_excess_mean_bps"])

    def test_false_signal_fails_even_when_cash_gross_positive(self) -> None:
        events = [q.PairedMonth(f"201{a // 12}-{a % 12 + 1:02d}", 50, 49, 1)
                  for a in range(50)]
        dev = q.summarize(events, seed=4, primary=True, period="dev")
        self.assertEqual(dev["verdict"], "NO_SUPPORT")
        self.assertEqual(dev["gross_TOM_after_hypothetical_RT_cost_bps"]["20"], 30)

    def test_strong_known_positive_support_is_not_certification(self) -> None:
        rows = [q.PairedMonth(f"2020-{i % 12 + 1:02d}", 70, 20, 50)
                for i in range(50)]
        out = q.summarize(rows, seed=7, primary=True, period="dev")
        self.assertEqual(out["verdict"], "PRELIMINARY_SUPPORT")
        self.assertFalse(out["strategy_is_broker_executable"])

    def test_all_three_required_and_negative_replication_closes(self) -> None:
        symbol = {"dev": {"adequate_months": True, "verdict": "PRELIMINARY_SUPPORT"},
                  "diag": {"adequate_months": True, "verdict": "PRELIMINARY_SUPPORT"}}
        samples = {k: symbol for k in q.SYMBOLS}
        with self.assertRaisesRegex(ValueError, "ALL_THREE_INDICES"):
            q.decide({"SP500": symbol})
        self.assertEqual(
            q.decide(samples)["verdict"],
            "PRELIMINARY_GROSS_ASSOCIATION_ONLY_NOT_EXECUTABLE",
        )
        bad = {k: dict(v) for k, v in samples.items()}
        bad["US30"] = {"dev": dict(symbol["dev"]),
                       "diag": {"adequate_months": True, "verdict": "NO_SUPPORT"}}
        self.assertEqual(q.decide(bad)["verdict"], "NO_SUPPORT_UNDER_PREREG")
        self.assertFalse(q.decide(bad)["edge_certified"])

    def test_dst_clock_is_new_york_not_naive_utc(self) -> None:
        winter = datetime(2020, 1, 15, 20, 55, tzinfo=UTC).astimezone(q.NY)
        summer = datetime(2020, 7, 15, 19, 55, tzinfo=UTC).astimezone(q.NY)
        self.assertEqual((winter.hour, winter.minute), q.CASH_LAST_BAR)
        self.assertEqual((summer.hour, summer.minute), q.CASH_LAST_BAR)


if __name__ == "__main__":
    unittest.main()
