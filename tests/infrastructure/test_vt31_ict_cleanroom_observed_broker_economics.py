"""Regression tests: owner's MT5 NDX100 sample is evidence, NOT contract facts."""
from __future__ import annotations

import unittest
from decimal import Decimal

from qore.infrastructure.traders.vt31_ict_cleanroom.observed_broker_economics import (
    NDX100_CLOSED_SAMPLE,
    MT5ClosedPositionObservation,
    screenshot_economic_observation,
)


class TestObservedMT5Economics(unittest.TestCase):
    def test_real_001_lot_movement_pnl_and_zero_commission_observed(self) -> None:
        s = NDX100_CLOSED_SAMPLE
        self.assertEqual(s.symbol, "NDX100")
        self.assertEqual(s.lots, Decimal("0.01"))
        self.assertEqual(s.signed_price_move, Decimal("-4.52"))
        self.assertEqual(s.gross_result_displayed, Decimal("-0.45"))
        self.assertEqual(s.commission_displayed, Decimal("0.00"))
        self.assertAlmostEqual(
            float(s.implied_account_currency_per_point_at_observed_lots),
            0.10, places=2,
        )

    def test_nominal_ten_per_point_per_full_lot_matches_display_rounding(self) -> None:
        s = NDX100_CLOSED_SAMPLE
        self.assertEqual(
            s.theoretical_gross_at_hypothetical_point_value(Decimal("10")),
            Decimal("-0.45"),
        )
        self.assertNotEqual(
            s.theoretical_gross_at_hypothetical_point_value(Decimal("1")),
            s.gross_result_displayed,
        )
        # A two-decimal PnL cannot establish the unique contractual
        # value of 1.00 lot; keep one-sample calibration only.
        self.assertNotEqual(
            s.implied_account_currency_per_point_per_lot, Decimal("10")
        )

    def test_other_symbols_fees_do_not_contaminate_ndx100(self) -> None:
        commissions = (
            Decimal("-0.07"), Decimal("-0.07"),
            Decimal("-0.07"), Decimal("-0.07"), Decimal("0.00"),
        )
        gross_pnl = (
            Decimal("0.16"), Decimal("-0.12"), Decimal("-0.11"),
            Decimal("-0.35"), Decimal("-0.45"),
        )
        self.assertEqual(sum(gross_pnl), Decimal("-0.87"))
        self.assertEqual(sum(commissions), Decimal("-0.28"))
        self.assertEqual(
            Decimal("2000.00") + sum(gross_pnl) + sum(commissions),
            Decimal("1998.85"),
        )
        self.assertEqual(NDX100_CLOSED_SAMPLE.commission_displayed, Decimal(0))

    def test_evidence_does_not_certify_broker_contract_or_live_risk(self) -> None:
        r = screenshot_economic_observation()
        self.assertEqual(r["trader_id"], "VT31")
        self.assertEqual(r["observed_mt5_symbol"], "NDX100")
        self.assertEqual(r["strategy_symbol"], "NAS100")
        self.assertTrue(
            r["hypothesized_ten_account_currency_units_per_point_per_lot"]
        )
        self.assertFalse(r["NDX100_NAS100_contract_identity_verified"])
        self.assertFalse(r["broker_contract_spec_confirmed"])
        self.assertFalse(r["account_currency_confirmed"])
        self.assertFalse(r["historical_bid_ask_tick_source_available"])
        self.assertFalse(r["safe_to_use_for_live_sizing"])
        self.assertFalse(r["commission_waiver_for_all_NDX100_trades_confirmed"])

    def test_cross_asset_sample_cannot_rebrand_to_ndx100(self) -> None:
        s = NDX100_CLOSED_SAMPLE
        with self.assertRaises(ValueError):
            MT5ClosedPositionObservation(
                symbol="XAUUSD", side=s.side, lots=s.lots,
                opening_execution=s.opening_execution,
                closing_execution=s.closing_execution,
                gross_result_displayed=s.gross_result_displayed,
                commission_displayed=s.commission_displayed,
            )


if __name__ == "__main__":
    unittest.main()
