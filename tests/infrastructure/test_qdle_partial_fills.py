"""QDLE P0 synthetic partial-fill lifecycle contract tests (NO broker orders).

Fixtures are deliberately synthetic. These tests establish local reserve,
deal-idempotency, crash and provider/QORE snapshot gates; they DO NOT prove
that the provider token truly authenticates a terminal or its deal history.
"""
from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal as D
from pathlib import Path

from qore.infrastructure.qore_dynamic_lot_engine import (
    BrokerValuation, Position, QDLE, QDLEAccount, QDLEError, QDLEIntent, QDLESymbol,
)

T = datetime(2026, 10, 8, 19, tzinfo=timezone.utc)


class SyntheticBroker:
    def value(self, symbol, intent, now):
        return BrokerValuation(D("100"), D("10"), now, "SYNTHETIC_ONLY")

    def check_volume(self, symbol, intent, lots):
        if lots <= 0:
            raise AssertionError("broker preflight requires positive lots")


def account(sequence=1, *, positions=(), covered=(), when=None):
    return QDLEAccount(
        account_id="fundednext-test-2000", provider="FundedNext", currency="USD",
        sequence=sequence, as_of=when or T, balance=D("2000"),
        equity=D("2000"), free_margin=D("1900"),
        qore_unreserved_risk_usd=D("60"),
        sovereign_free_source_usd=D("60"), cushion_free_source_usd=D("0"),
        qore_trading_capital_usd=D("60"), positions=tuple(positions),
        covered_fill_tickets=tuple(covered),
    )


def intent(request_id):
    return QDLEIntent(
        request_id=request_id, trader_id="synthetic-r38", symbol="EURUSD",
        side="BUY", entry_price=D("1.1000"), stop_price=D("1.0900"),
        requested_risk_usd=D("3"), sizing_cap_usd=D("3"),
        cibo_compound_cap_usd=D("3"), portfolio_cap_usd=D("3"),
        leverage_cap_lots=D("1"), margin_cap_usd=D("100"),
        source_lane="SOVEREIGN_BANK", slippage_usd_per_lot=D("0"),
        expected_account_sequence=1,
    )


def symbol():
    return QDLESymbol(
        broker_symbol="EURUSD", aliases=("EURUSD",),
        min_lot=D(".01"), max_lot=D("40"), lot_step=D(".01"),
        directional_volume_limit=D("0"), tick_size=D(".00001"),
        tick_value_loss_usd=D("1"), contract_size=D("100000"),
        currency_profit="USD", fee_usd_per_lot=D("0"),
        fee_provenance="SYNTHETIC_ONLY", as_of=T,
    )


class TestPartialFills(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = Path(self.temp.name) / "qdle.sqlite"
        self.broker = SyntheticBroker()
        self.q = self.new_engine()
        self.q.publish_account(account())
        self.q.publish_symbol(symbol())

    def tearDown(self):
        self.temp.cleanup()

    def new_engine(self):
        return QDLE(
            self.db, self.broker, enforce_finance_approval=True,
            strict_four_motor_evidence=False,
            strict_live_fee_evidence=False, strict_provider_floor=False,
        )

    def armed(self, request_id):
        planned = intent(request_id)
        self.q.publish_finance_approval(planned, T)
        reserved = self.q.reserve_for_trader(planned, T)
        self.assertEqual(reserved.lots, D(".03"))
        self.assertEqual(reserved.total_risk_usd, D("3"))
        self.q.arm_for_live_send(
            request_id=request_id, provider_symbol="EURUSD", side="BUY",
            lots=D(".03"), executable_entry=D("1.1000"),
            stop_price=D("1.0900"), now=T,
        )
        return reserved

    def newer_account(self, ticket=None, lots=".01", *, covered=True, sequence=2):
        pos = (
            (Position(ticket, "EURUSD", "BUY", D(lots)),) if ticket else ()
        )
        self.q.publish_account(
            account(sequence, positions=pos,
                    covered=(ticket,) if ticket and covered else (),
                    when=T + timedelta(seconds=sequence)),
        )

    def test_partial_requires_authenticated_remainder_cancellation_and_coverage(self):
        self.armed("partial")
        self.q.record_partial_fill("partial", "position-100", "deal-01", D(".01"))
        self.assertEqual(self.q.health(T)["pending_or_unreconciled_reservations"], 1)
        self.newer_account("position-100", ".01")
        with self.assertRaisesRegex(QDLEError, "cancellation missing"):
            self.q.reconcile_fill("partial")
        self.assertEqual(self.q.health(T)["pending_or_unreconciled_reservations"], 1)
        self.q.confirm_partial_remainder_cancelled("partial", "cancel-confirmed-100")
        self.q.reconcile_fill("partial")
        self.assertEqual(self.q.health(T)["pending_or_unreconciled_reservations"], 0)
        covered = [e for e in self.q.ledger() if e["event"] == "FILLED_AND_COVERED"]
        self.assertEqual(covered[0]["receipt"]["executed_lots"], "0.01")

    def test_fully_executed_in_two_deals_needs_no_remainder_cancel(self):
        self.armed("all-filled")
        self.q.record_partial_fill("all-filled", "position-101", "deal-101-a", D(".01"))
        self.q.record_partial_fill("all-filled", "position-101", "deal-101-b", D(".02"))
        with self.assertRaisesRegex(QDLEError, "no unfilled broker volume"):
            self.q.confirm_partial_remainder_cancelled("all-filled", "cancel-not-applicable")
        self.newer_account("position-101", ".03")
        self.q.reconcile_fill("all-filled")
        self.assertEqual(self.q.health(T)["pending_or_unreconciled_reservations"], 0)
        covered = [e for e in self.q.ledger() if e["event"] == "FILLED_AND_COVERED"]
        self.assertEqual(covered[0]["receipt"]["partial_deal_count"], 2)

    def test_duplicate_deal_exactly_idempotent_but_mutation_rejected(self):
        self.armed("duplicate")
        self.q.record_partial_fill("duplicate", "position-102", "deal-102", D(".01"))
        self.q.record_partial_fill("duplicate", "position-102", "deal-102", D(".01"))
        self.assertEqual(sum(e["event"] == "BROKER_PARTIAL_FILL_UNRECONCILED"
                             for e in self.q.ledger()), 1)
        with self.assertRaisesRegex(QDLEError, "reused or mutated"):
            self.q.record_partial_fill("duplicate", "position-102", "deal-102", D(".02"))
        self.assertEqual(self.q.health(T)["pending_or_unreconciled_reservations"], 1)

    def test_overfill_rejected_without_committing_bad_deal(self):
        self.armed("overfill")
        self.q.record_partial_fill("overfill", "position-103", "deal-103-a", D(".02"))
        with self.assertRaisesRegex(QDLEError, "exceed reserved"):
            self.q.record_partial_fill("overfill", "position-103", "deal-103-b", D(".02"))
        self.q.record_partial_fill("overfill", "position-103", "deal-103-b", D(".01"))
        self.assertEqual(sum(e["event"] == "BROKER_PARTIAL_FILL_UNRECONCILED"
                             for e in self.q.ledger()), 2)

    def test_netting_and_hedging_second_ticket_same_request_fail_closed(self):
        self.armed("two-tickets")
        self.q.record_partial_fill("two-tickets", "hedge-ticket-A", "deal-A", D(".01"))
        with self.assertRaisesRegex(QDLEError, "multi-ticket"):
            self.q.record_partial_fill("two-tickets", "hedge-ticket-B", "deal-B", D(".01"))
        self.assertEqual(self.q.health(T)["pending_or_unreconciled_reservations"], 1)

    def test_shared_position_ticket_between_requests_fails_closed(self):
        self.armed("first")
        self.armed("second")
        self.q.record_partial_fill("first", "net-ticket-1", "deal-first", D(".01"))
        with self.assertRaisesRegex(QDLEError, "shared across unrelated entries"):
            self.q.record_partial_fill("second", "net-ticket-1", "deal-second", D(".01"))
        self.assertEqual(self.q.health(T)["pending_or_unreconciled_reservations"], 2)

    def test_deal_id_cannot_be_assigned_to_a_second_request(self):
        self.armed("signal-A")
        self.armed("signal-B")
        self.q.record_partial_fill("signal-A", "ticket-A", "globally-unique-deal", D(".01"))
        with self.assertRaisesRegex(QDLEError, "reused or mutated"):
            self.q.record_partial_fill("signal-B", "ticket-B", "globally-unique-deal", D(".01"))

    def test_cancel_receipt_not_reusable_across_requests(self):
        self.armed("cancel-A")
        self.armed("cancel-B")
        self.q.record_partial_fill("cancel-A", "ticket-A", "deal-A", D(".01"))
        self.q.record_partial_fill("cancel-B", "ticket-B", "deal-B", D(".01"))
        self.q.confirm_partial_remainder_cancelled("cancel-A", "same-cancel")
        self.q.confirm_partial_remainder_cancelled("cancel-A", "same-cancel")
        with self.assertRaisesRegex(QDLEError, "shared across requests"):
            self.q.confirm_partial_remainder_cancelled("cancel-B", "same-cancel")
        with self.assertRaisesRegex(QDLEError, "contradictory"):
            self.q.confirm_partial_remainder_cancelled("cancel-A", "other-cancel")

    def test_no_additional_fill_after_remainder_cancelled(self):
        self.armed("cancelled")
        self.q.record_partial_fill("cancelled", "position-104", "deal-first", D(".01"))
        self.q.confirm_partial_remainder_cancelled("cancelled", "broker-cancel-104")
        with self.assertRaisesRegex(QDLEError, "after remainder cancellation"):
            self.q.record_partial_fill("cancelled", "position-104", "deal-late", D(".01"))

    def test_qore_treasury_coverage_cannot_be_inferred_from_mt5_position(self):
        self.armed("uncovered")
        self.q.record_partial_fill("uncovered", "position-105", "deal-105", D(".01"))
        self.q.confirm_partial_remainder_cancelled("uncovered", "cancel-105")
        self.newer_account("position-105", ".01", covered=False)
        with self.assertRaisesRegex(QDLEError, "coverage absent"):
            self.q.reconcile_fill("uncovered")
        self.assertEqual(self.q.health(T)["pending_or_unreconciled_reservations"], 1)

    def test_wrong_position_volume_not_absorbed(self):
        self.armed("wrong-volume")
        self.q.record_partial_fill("wrong-volume", "position-106", "deal-106", D(".01"))
        self.q.confirm_partial_remainder_cancelled("wrong-volume", "cancel-106")
        self.newer_account("position-106", ".02")
        with self.assertRaisesRegex(QDLEError, "position or QORE"):
            self.q.reconcile_fill("wrong-volume")
        self.assertEqual(self.q.health(T)["pending_or_unreconciled_reservations"], 1)

    def test_restart_keeps_partial_hold_until_fresh_snapshot(self):
        self.armed("crash-mid-fill")
        self.q.record_partial_fill("crash-mid-fill", "position-107", "deal-107", D(".01"))
        self.q.confirm_partial_remainder_cancelled("crash-mid-fill", "cancel-107")
        self.q = self.new_engine()
        self.assertFalse(self.q.health(T)["ready"])
        self.assertEqual(self.q.health(T)["pending_or_unreconciled_reservations"], 1)
        with self.assertRaisesRegex(QDLEError, "not synchronized"):
            self.q.reserve_for_trader(intent("new-after-restart"), T)
        self.newer_account("position-107", ".01", sequence=2)
        self.q.reconcile_fill("crash-mid-fill")
        self.assertEqual(self.q.health(T)["pending_or_unreconciled_reservations"], 0)

    def test_settlement_requires_closed_position_and_unique_deal(self):
        self.armed("settle-partial")
        self.q.record_partial_fill("settle-partial", "position-108", "deal-open", D(".01"))
        self.q.confirm_partial_remainder_cancelled("settle-partial", "cancel-108")
        self.newer_account("position-108", ".01", sequence=2)
        self.q.reconcile_fill("settle-partial")
        with self.assertRaisesRegex(QDLEError, "position open"):
            self.q.record_broker_settlement("settle-partial", "position-108",
                                            "deal-close", D("-2"))
        self.newer_account(sequence=3)
        self.q.record_broker_settlement("settle-partial", "position-108",
                                        "deal-close", D("-2"))
        with self.assertRaises(QDLEError):
            self.q.record_broker_settlement("settle-partial", "position-108",
                                            "deal-close", D("-2"))
        settled = [e for e in self.q.ledger() if e["event"] == "BROKER_REALIZED_SETTLEMENT"]
        self.assertEqual(len(settled), 1)
        self.assertEqual(settled[0]["receipt"]["executed_lots"], "0.01")
        self.assertEqual(settled[0]["receipt"]["realized_net_pnl_usd"], "-2")

    def test_sending_unknown_cannot_be_rejected_after_partial_fill(self):
        self.armed("unknown")
        self.q.record_partial_fill("unknown", "position-109", "deal-109", D(".01"))
        with self.assertRaisesRegex(QDLEError, "only broker-confirmed no-fill"):
            self.q.confirm_rejection("unknown", "not-a-real-zero-fill")
        self.assertEqual(self.q.health(T)["pending_or_unreconciled_reservations"], 1)


if __name__ == "__main__":
    unittest.main()
