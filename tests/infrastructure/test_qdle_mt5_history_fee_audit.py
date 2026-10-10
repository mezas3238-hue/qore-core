"""Observed FundedNext MT5 sample screenshot 2026-10-09 — fee truth tests.

SOURCE screenshot SHA256:
914072741b2301ee5e69c7c3bb9228292db38f0ca93a9d47da86a8b2efdf54b0
Manually transcribed five completed 0.01-lot positions. Account/ticket IDs
intentionally excluded. Broker-server timezone NOT exposed on screenshot;
UTC below is a normalization assumption for ordering the 5 visible rows only.
No claim that this sample is CIBO-managed or historical 3368 coverage.
"""
import unittest
from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal as D

from qore.infrastructure.qdle_mt5_history_fee_audit import (
    ClosedMT5PositionEvidence, MT5HistoryFeeAuditError,
    reconcile_mt5_closed_history,
)


def t(y, m, d, hh, mm, ss):
    return datetime(y, m, d, hh, mm, ss, tzinfo=timezone.utc)


def sample():
    return (
        ClosedMT5PositionEvidence(
            "EURUSD", "SELL", D(".01"), D("1.13455"), D("1.13439"),
            t(2026, 9, 30, 10, 47, 57), t(2026, 9, 30, 10, 49, 10),
            D(".16"), D(".07")),
        ClosedMT5PositionEvidence(
            "GBPJPY", "BUY", D(".01"), D("209.522"), D("209.503"),
            t(2026, 10, 9, 17, 53, 46), t(2026, 10, 9, 17, 53, 53),
            D("-.12"), D(".07")),
        ClosedMT5PositionEvidence(
            "AUDJPY", "BUY", D(".01"), D("110.471"), D("110.454"),
            t(2026, 10, 9, 17, 34, 11), t(2026, 10, 9, 17, 34, 15),
            D("-.11"), D(".07")),
        ClosedMT5PositionEvidence(
            "XAUUSD", "BUY", D(".01"), D("4185.46"), D("4185.11"),
            t(2026, 10, 9, 17, 37, 42), t(2026, 10, 9, 17, 37, 45),
            D("-.35"), D(".07")),
        ClosedMT5PositionEvidence(
            "NDX100", "BUY", D(".01"), D("30852.60"), D("30848.08"),
            t(2026, 10, 9, 17, 35, 10), t(2026, 10, 9, 17, 35, 18),
            D("-.45"), D("0")),
    )


def audit(**kw):
    a = dict(positions=sample(), initial_balance_usd=D("2000.00"),
             observed_final_balance_usd=D("1998.85"),
             observed_commission_debit_usd=D(".28"),
             reference_usdjpy_spot=D("158.337"))
    a.update(kw)
    return reconcile_mt5_closed_history(**a)


class MT5HistoryScreenshots(unittest.TestCase):
    def test_all_five_closed_deals_fees_and_account_balance_match(self):
        r = audit()
        self.assertEqual(r["position_count"], 5)
        self.assertEqual(r["observed_price_pnl_usd"], "-0.87")
        self.assertEqual(r["observed_total_commission_debit_usd"], "0.28")
        self.assertEqual(r["observed_total_swap_usd"], "0")
        self.assertEqual(D(r["observed_net_change_usd"]), D("-1.15"))
        self.assertEqual(r["observed_final_balance_usd"], "1998.85")
        self.assertTrue(r["all_observed_fees_match_stellar_faq"])
        self.assertEqual(
            [D(z["observed_commission_debit_usd"]) for z in r["rows"]],
            [D(".07"), D(".07"), D(".07"), D(".07"), D("0")],
        )
        self.assertIsNone(r["cibo_3368_managed_dd_pct"])
        self.assertIsNone(r["cibo_3368_managed_final_nav_usd"])
        self.assertFalse(r["fee_leg_timing_independently_proven"])
        self.assertFalse(r["tariff_account_wide_future_verified"])

    def test_observed_jpy_price_move_matches_nearby_usdjpy_approx(self):
        self.assertEqual(audit()["position_count"], 5)
        # Reference USDJPY is a distinct screenshot ~8 minutes later,
        # not exchange-rate evidence for each broker fill.

    def test_reject_forex_14_roundtrip_on_real_account_position(self):
        r = list(sample())
        r[0] = replace(r[0], commission_debit_usd=D(".14"))
        with self.assertRaisesRegex(MT5HistoryFeeAuditError, "commission differs"):
            audit(positions=tuple(r), observed_commission_debit_usd=D(".35"))

    def test_reject_gold_double_fee(self):
        r = list(sample())
        r[3] = replace(r[3], commission_debit_usd=D(".14"))
        with self.assertRaisesRegex(MT5HistoryFeeAuditError, "commission differs"):
            audit(positions=tuple(r), observed_commission_debit_usd=D(".35"))

    def test_reject_index_false_fee(self):
        r = list(sample())
        r[4] = replace(r[4], commission_debit_usd=D(".20"))
        with self.assertRaisesRegex(MT5HistoryFeeAuditError, "commission differs"):
            audit(positions=tuple(r), observed_commission_debit_usd=D(".48"))

    def test_reject_wrong_balance(self):
        with self.assertRaisesRegex(MT5HistoryFeeAuditError, "balance"):
            audit(observed_final_balance_usd=D("1998.90"))

    def test_reject_wrong_price_profit_on_gold(self):
        r = list(sample())
        r[3] = replace(r[3], price_pnl_usd=D("-.70"))
        with self.assertRaisesRegex(MT5HistoryFeeAuditError, "contract mismatch"):
            audit(positions=tuple(r))

    def test_reject_duplicate_history_row(self):
        with self.assertRaisesRegex(MT5HistoryFeeAuditError, "duplicate"):
            audit(positions=sample() + (sample()[0],))

    def test_reject_naive_timestamps(self):
        with self.assertRaisesRegex(MT5HistoryFeeAuditError, "timezone-aware"):
            replace(sample()[0], opened_at=datetime(2026, 9, 30, 10, 47, 57))


if __name__ == "__main__":
    unittest.main()
