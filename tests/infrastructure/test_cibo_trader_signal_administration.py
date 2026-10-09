"""CEO P0: Trader owns selection, CIBO receives/manages, QDLE owns lotage."""
from __future__ import annotations

import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal as D

from qore.infrastructure.cibo_trader_signal_administration import (
    CiboAdministrationError,
    EconomicStopBudget,
    TraderSignalIntake,
    propose_received_trader_management,
)

NOW = datetime(2026, 10, 8, 10, tzinfo=timezone.utc)
HASH = "sha256:" + "a" * 64


def signal(*, index=1, side="BUY", stop=None):
    return TraderSignalIntake(
        signal_fingerprint=f"signal-{index}", trader_id="VT31",
        symbol="EURUSD", side=side, entry_price=D("1.1000"),
        structural_stop_price=(
            D(stop) if stop is not None else
            (D("1.0965") if side == "BUY" else D("1.1035"))
        ),
        take_profit_price=D("1.1060") if side == "BUY" else D("1.0940"),
        decided_at=NOW, trader_evidence_sha256=HASH,
    )


def budget(**kwargs):
    d = dict(
        qore_reconciled_nav_usd=D("60"),
        cibo_max_loss_usd=D("3"),
        source_unreserved_loss_capacity_usd=D("60"),
        broker_min_lot=D(".01"), broker_lot_step=D(".01"),
        tick_size_price=D(".0001"),
        broker_min_stop_distance_price=D(".0002"),
        price_loss_usd_per_price_unit_per_lot=D("100000"),
        opening_commission_usd_per_lot=D("7"),
        closing_commission_usd_per_lot=D("7"),
        execution_buffer_usd_per_lot=D("0"),
        broker_data_as_of=NOW - timedelta(seconds=3),
        price_valuation_evidence_sha256=HASH,
    )
    d.update(kwargs)
    return EconomicStopBudget(**d)


class TestCiboSignalAdministration(unittest.TestCase):
    def test_budgeted_protective_stop_not_fake_lot_or_fill(self):
        # Trader 35p SL, at 0.01 costs $3.64; CIBO economic stop at 28p costs $2.94.
        r = propose_received_trader_management(signal=signal(), budget=budget())
        self.assertEqual(r.status, "RECEIVED_READY_FOR_QDLE")
        self.assertEqual(r.budget_usd, D("3"))
        self.assertEqual(r.structural_stop_price, D("1.0965"))
        self.assertEqual(r.proposed_protective_stop_price, D("1.0972"))
        self.assertEqual(r.min_lot_stop_plus_all_costs_usd, D("2.94"))
        self.assertIsNone(r.qdle_lots)
        self.assertFalse(r.broker_fill_proven)
        self.assertFalse(r.is_broker_order)
        self.assertIn("ECONOMIC_PROTECTIVE_STOP_PROPOSED", r.reason_codes)

    def test_short_side_economic_stop_and_original_reference(self):
        r = propose_received_trader_management(signal=signal(side="SELL"), budget=budget())
        self.assertEqual(r.proposed_protective_stop_price, D("1.1028"))
        self.assertEqual(r.structural_stop_price, D("1.1035"))
        self.assertEqual(r.min_lot_stop_plus_all_costs_usd, D("2.94"))

    def test_no_economic_stop_when_original_affordable(self):
        r = propose_received_trader_management(
            signal=signal(stop="1.0980"), budget=budget()
        )
        self.assertEqual(r.status, "RECEIVED_READY_FOR_QDLE")
        self.assertEqual(r.proposed_protective_stop_price, D("1.0980"))
        self.assertEqual(r.min_lot_stop_plus_all_costs_usd, D("2.14"))
        self.assertEqual(r.reason_codes, ("STRUCTURAL_STOP_AFFORDABLE_MIN_LOT",))

    def test_compounding_budget_is_dynamic_and_lot_not_forced(self):
        r = propose_received_trader_management(
            signal=signal(), budget=budget(qore_reconciled_nav_usd=D("100"),
                                         cibo_max_loss_usd=D("5"))
        )
        self.assertEqual(r.budget_usd, D("5"))
        self.assertEqual(r.proposed_protective_stop_price, D("1.0965"))
        self.assertIsNone(r.qdle_lots)

    def test_early_exit_promise_never_funds_minimum(self):
        r = propose_received_trader_management(
            signal=signal(), budget=budget(
                qore_reconciled_nav_usd=D("2"), cibo_max_loss_usd=D(".1")
            )
        )
        self.assertEqual(r.status, "RECEIVED_UNFUNDABLE")
        self.assertIn("FEES_AND_BUFFERS_EXCEED_CAP", r.reason_codes)
        self.assertIsNone(r.proposed_protective_stop_price)
        self.assertFalse(r.broker_fill_proven)

    def test_broker_min_distance_is_hard_protection(self):
        r = propose_received_trader_management(
            signal=signal(), budget=budget(broker_min_stop_distance_price=D(".0030"))
        )
        self.assertEqual(r.status, "RECEIVED_UNFUNDABLE")
        self.assertIn("PROTECTIVE_STOP_BELOW_BROKER_MIN", r.reason_codes)

    def test_source_limits_can_only_reduce_budget(self):
        r = propose_received_trader_management(
            signal=signal(), budget=budget(source_unreserved_loss_capacity_usd=D("0"))
        )
        self.assertEqual(r.status, "RECEIVED_UNFUNDABLE")
        self.assertEqual(r.budget_usd, D("0"))
        self.assertIn("ZERO_ALLOCATED_RISK_CAPACITY", r.reason_codes)

    def test_missing_broker_quote_retains_signal_as_managed(self):
        r = propose_received_trader_management(signal=signal(), budget=None)
        self.assertEqual(r.status, "RECEIVED_NEEDS_BROKER_VALUATION")
        self.assertFalse(r.broker_fill_proven)

    def test_predecision_valuation_only(self):
        with self.assertRaisesRegex(CiboAdministrationError, "future broker"):
            propose_received_trader_management(
                signal=signal(),
                budget=budget(broker_data_as_of=NOW+timedelta(seconds=1)),
            )

    def test_validation_of_trader_geometry_and_broker_grid(self):
        with self.assertRaises(CiboAdministrationError):
            signal(stop="1.1010")
        with self.assertRaises(CiboAdministrationError):
            budget(broker_min_lot=D(".015"))
        with self.assertRaises(CiboAdministrationError):
            budget(qore_reconciled_nav_usd=D("NaN"))

    def test_all_3368_trader_signals_have_a_reception_receipt(self):
        # No cognitive gate: all 3368 valid signals retain identity and an
        # administration result, whether the stop is affordable or not.
        receipts = [
            propose_received_trader_management(
                signal=signal(index=i, stop="1.0965" if i%2 else "1.0980"),
                budget=budget() if i%3 else None
            )
            for i in range(3368)
        ]
        self.assertEqual(len(receipts), 3368)
        self.assertEqual(len({r.signal_fingerprint for r in receipts}), 3368)
        self.assertTrue(all(r.status.startswith("RECEIVED_") for r in receipts))
        self.assertTrue(all(r.qdle_lots is None and not r.broker_fill_proven for r in receipts))


if __name__ == "__main__":
    unittest.main()
