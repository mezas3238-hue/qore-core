"""QDLE live one-shot treasury proof, dynamic 5% equity and drift gates.

ALL amounts below are SYNTHETIC fixtures; NEVER use as provider contract data.
"""
from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal as D
from pathlib import Path

from qore.infrastructure.qore_dynamic_lot_engine import (
    BrokerValuation, QDLE, QDLEAccount, QDLEError,
    QDLEIntent, QDLESymbol,
)

T = datetime(2026, 10, 8, 15, tzinfo=timezone.utc)


class Probe:
    def __init__(self):
        self.preflight = 0
    def value(self, symbol, intent, now):
        # Native adapter would call MT5 order_calc_profit for THIS entry/stop.
        return BrokerValuation(D("100") +
            abs(intent.entry_price-D("1.1000"))*D("10000"),
            D("10"), now, "SYNTHETIC_TEST_ONLY")
    def check_volume(self, symbol, intent, lots):
        self.preflight += 1


def account(equity="60", seq=1):
    return QDLEAccount("123", "FundedNext", "USD", seq, T,
        D(equity), D(equity), D("200"), D("200"), D("200"), D("0"))


def intent(rid="signal-1", budget="30", sequence=1):
    return QDLEIntent(
        rid, "r38", "EURUSD", "BUY", D("1.1000"), D("1.0900"),
        D(budget), D(budget), D(budget), D("200"), D("50"),
        D("200"), "SOVEREIGN_BANK", D("0"), sequence)


def symbol():
    return QDLESymbol("EURUSD", ("EURUSD",), D("0.01"), D("10"),
        D("0.01"), D("0"), D("0.00001"), D("1"), D("100000"),
        "USD", D("0"), "SYNTHETIC_TEST_ONLY", T)


class TestQdleLiveGate(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.broker = Probe()
        self.q = QDLE(Path(self.directory.name) / "engine.sqlite",
                      self.broker, enforce_finance_approval=True)
        self.q.publish_account(account())
        self.q.publish_symbol(symbol())

    def tearDown(self):
        self.directory.cleanup()

    def test_dynamic_five_percent_by_causal_equity(self):
        approved = intent()
        self.q.publish_finance_approval(approved, T)
        proposal = self.q.reserve_for_trader(approved, T)
        self.assertEqual(proposal.lots, D("0.03"))
        self.assertEqual(proposal.total_risk_usd, D("3"))
        self.q.publish_account(account(equity="100", seq=2))
        next_intent = intent("signal-2", sequence=2)
        self.q.publish_finance_approval(next_intent, T)
        second = self.q.reserve_for_trader(next_intent, T)
        self.assertEqual(second.lots, D("0.05"))
        self.assertEqual(second.total_risk_usd, D("5"))

    def test_trader_may_not_approve_or_change_coordinated_economics(self):
        with self.assertRaises(QDLEError):
            self.q.reserve_for_trader(intent(), T)
        self.q.publish_finance_approval(intent(), T)
        with self.assertRaises(QDLEError):
            self.q.reserve_for_trader(intent(budget="300"), T)
        result = self.q.reserve_for_trader(intent(), T)
        self.assertEqual(result.lots, D(".03"))

    def test_live_presend_is_single_use_and_held_after_unknown(self):
        self.q.publish_finance_approval(intent(), T)
        funded = self.q.reserve_for_trader(intent(), T)
        self.q.arm_for_live_send(
            request_id="signal-1", provider_symbol="EURUSD", side="BUY",
            lots=funded.lots, executable_entry=D("1.1000"),
            stop_price=D("1.0900"), now=T)
        with self.assertRaises(QDLEError):
            self.q.arm_for_live_send(
                request_id="signal-1", provider_symbol="EURUSD", side="BUY",
                lots=funded.lots, executable_entry=D("1.1000"),
                stop_price=D("1.0900"), now=T)
        self.assertEqual(self.q.health(now=T)["pending_or_unreconciled_reservations"], 1)
        self.assertEqual(sum(x["event"] == "QDLE_LIVE_SEND_ARMED_ONCE"
                             for x in self.q.ledger()), 1)

    def test_changed_price_expands_risk_and_blocks_live(self):
        self.q.publish_finance_approval(intent(), T)
        proposal = self.q.reserve_for_trader(intent(), T)
        with self.assertRaisesRegex(QDLEError, "drift"):
            self.q.arm_for_live_send(
                request_id="signal-1", provider_symbol="EURUSD", side="BUY",
                lots=proposal.lots, executable_entry=D("1.1010"),
                stop_price=D("1.0900"), now=T)
        self.assertEqual(self.q.health(now=T)["pending_or_unreconciled_reservations"], 1)
        self.assertEqual(sum(x["event"] == "QDLE_LIVE_SEND_ARMED_ONCE"
                             for x in self.q.ledger()), 0)

    def test_changed_snapshot_requires_renewed_approval_and_reservation(self):
        self.q.publish_finance_approval(intent(), T)
        proposal = self.q.reserve_for_trader(intent(), T)
        self.q.publish_account(account(equity="70", seq=2))
        with self.assertRaisesRegex(QDLEError, "changed"):
            self.q.arm_for_live_send(
                request_id="signal-1", provider_symbol="EURUSD", side="BUY",
                lots=proposal.lots, executable_entry=D("1.1000"),
                stop_price=D("1.0900"), now=T)

    def test_new_fill_can_reconcile_after_live_armed(self):
        self.q.publish_finance_approval(intent(), T)
        self.q.reserve_for_trader(intent(), T)
        self.q.arm_for_live_send(
            request_id="signal-1", provider_symbol="EURUSD", side="BUY",
            lots=D(".03"), executable_entry=D("1.1000"),
            stop_price=D("1.0900"), now=T)
        self.q.acknowledge_fill("signal-1", "live-ticket:1")
        self.assertEqual(self.q.health(now=T)["pending_or_unreconciled_reservations"], 1)


if __name__ == "__main__":
    unittest.main()
