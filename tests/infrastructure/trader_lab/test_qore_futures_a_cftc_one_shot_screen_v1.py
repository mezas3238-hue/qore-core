"""Synthetic checks for preregistered CFTC/EIA screen; NO real outcomes."""
from __future__ import annotations

import math
import unittest
from datetime import date, timedelta

import qore_futures_a_cftc_managed_money_one_shot_screen_v1 as s


class TestCftcOneShotPrecommitted(unittest.TestCase):
    def test_locked_prereg_id_and_fixed_inference(self) -> None:
        self.assertEqual(s.PREREG_SHA, "e6821685cbefd775f820865e4d2b0d03ab94dff2")
        self.assertEqual(s.CONTRACT_CODES, {"WTI": "067651", "NG": "023651"})
        self.assertEqual(s.ALPHA, 0.025)
        self.assertEqual(s.MIN_EFFECT, 0.10)
        self.assertEqual(s.MIN_GROUP, 8)
        self.assertEqual(set(s.DIGESTS), set(range(2012, 2022)))

    def test_fisher_null_all_equal_one(self) -> None:
        self.assertTrue(math.isclose(s._fisher_greater(8, 0, 8, 0), 1.0))

    def test_fisher_strong_effect_is_small(self) -> None:
        self.assertLess(s._fisher_greater(12, 0, 0, 12), s.ALPHA)

    def test_score_cannot_certify_insufficient_groups(self) -> None:
        events = [s.DiagnosticEvent("2017-01", True, True)] * 7
        events += [s.DiagnosticEvent("2017-02", False, False)] * 8
        out = s.score(events, 2012, 2018)
        self.assertEqual(out["window_verdict"], "INCONCLUSIVE_TOO_FEW_EVENTS")
        self.assertIsNone(out["fisher_one_sided_p"])

    def test_score_only_requested_window(self) -> None:
        dev = [s.DiagnosticEvent("2017-01", True, True)] * 12
        dev += [s.DiagnosticEvent("2017-02", False, False)] * 12
        diag = [s.DiagnosticEvent("2020-01", True, False)] * 15
        diag += [s.DiagnosticEvent("2020-02", False, True)] * 15
        self.assertEqual(
            s.score(dev + diag, 2012, 2018)["window_verdict"], "PRELIMINARY_SUPPORT"
        )
        self.assertEqual(s.score(dev + diag, 2019, 2021)["window_verdict"], "NO_SUPPORT")

    def test_future_reference_entry_cannot_precede_twenty_one_days(self) -> None:
        base = date(2017, 1, 3)
        weeks = [
            s.CftcPosition(base + timedelta(days=i * 7), float(i % 6) / 100)
            for i in range(12)
        ]
        # Prices stay level initially, then rise after the 21 day delay.
        days = [date(2017, 1, 2) + timedelta(days=i) for i in range(150)]
        prices = {d: float(i) for i, d in enumerate(days)}
        evs, counter = s.build_events(weeks, prices)
        self.assertGreaterEqual(counter["monthly_reports_considered"], 1)
        self.assertLessEqual(len(evs), 3)
        self.assertEqual(len({e.month for e in evs}), len(evs))
        self.assertTrue(all(e.future_reference_up for e in evs))

    def test_blackout_months_never_create_events(self) -> None:
        base = date(2013, 7, 2)
        weeks = [
            s.CftcPosition(base + timedelta(days=i * 7), i / 1000)
            for i in range(25)
        ]
        prices = {
            base + timedelta(days=i): float(i)
            for i in range(240)
        }
        evs, reason = s.build_events(weeks, prices)
        self.assertGreater(reason["blackout_reports"], 0)
        self.assertFalse(any(e.month.startswith(("2013-09", "2013-10", "2013-11")) for e in evs))

    def test_outcome_ties_do_not_count(self) -> None:
        base = date(2020, 5, 5)
        weeks = [
            s.CftcPosition(base + timedelta(days=i * 7), i / 100)
            for i in range(22)
        ]
        prices = {base + timedelta(days=i): 30.0 for i in range(280)}
        evs, reasons = s.build_events(weeks, prices)
        self.assertEqual(evs, [])
        self.assertGreater(reasons["signal_or_price_ties"], 0)

    def test_non_preregistered_zip_refused_before_outcome(self) -> None:
        with self.assertRaisesRegex(s.CftcScreenError, "CFTC_SOURCE_DIGEST_MISMATCH"):
            s._read_cftc_archive(b"any forged zip", 2019)
        with self.assertRaisesRegex(s.CftcScreenError, "CFTC_SOURCE_DIGEST_MISMATCH"):
            s._read_cftc_archive(b"any forged zip", 2022)


if __name__ == "__main__":
    unittest.main()
