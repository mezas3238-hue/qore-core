"""P0: one persistent research QDLE book, isolated from real broker receipts."""
from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal as D
from pathlib import Path

from qore.infrastructure.qdle_paper_book import PaperQDLE
from qore.infrastructure.qore_dynamic_lot_engine import (
    QDLEAccount, QDLEIntent, QDLEError, QDLESymbol, BrokerValuation, Position,
)

AT = datetime(2026, 10, 9, 12, 0, tzinfo=timezone.utc)


class PaperBroker:
    def __init__(self):
        self.value_at = None

    def value(self, instrument, intent, now):
        return BrokerValuation(D("100"), D("200"), now, "TEST_SCENARIO_NOT_MT5")

    def check_volume(self, instrument, intent, lots):
        if lots % instrument.lot_step or lots < instrument.min_lot:
            raise QDLEError("invalid paper broker grid")


def snapshot(q, sequence, at, active=()):
    risk = sum((D("3") for _ in active), D("0"))
    q.publish_account(QDLEAccount(
        account_id="PAPER_ACCOUNT", provider="FundedNext", currency="USD",
        sequence=sequence, as_of=at, balance=D("2000"), equity=D("2000"),
        free_margin=D("1900") - D("6") * len(active),
        qore_unreserved_risk_usd=D("60") - risk,
        sovereign_free_source_usd=D("60") - risk,
        cushion_free_source_usd=D("0"),
        qore_trading_capital_usd=D("60"),
        positions=tuple(Position(ticket="PAPER:" + sid, symbol="EURUSD",
                                 side="BUY", lots=D("0.03")) for sid in active),
        covered_fill_tickets=tuple("PAPER:" + sid for sid in active),
    ))


def symbol(q, at):
    q.publish_symbol(QDLESymbol(
        broker_symbol="EURUSD", aliases=("EURUSD",),
        min_lot=D("0.01"), max_lot=D("10"), lot_step=D("0.01"),
        directional_volume_limit=D("0"),
        tick_size=D("0.00001"), tick_value_loss_usd=D("1"),
        contract_size=D("100000"), currency_profit="USD",
        fee_usd_per_lot=D("0"), fee_provenance="TEST_PAPER_ONLY",
        as_of=at, tradable=True,
    ))


def request(sid, seq):
    return QDLEIntent(
        request_id=sid, trader_id="T01", symbol="EURUSD", side="BUY",
        entry_price=D("1.10"), stop_price=D("1.095"),
        requested_risk_usd=D("3"), sizing_cap_usd=D("3"),
        cibo_compound_cap_usd=D("3"), portfolio_cap_usd=D("3"),
        leverage_cap_lots=D("10"), margin_cap_usd=D("1900"),
        source_lane="SOVEREIGN_BANK", slippage_usd_per_lot=D("0"),
        expected_account_sequence=seq,
    )


class TestPaperQDLE(unittest.TestCase):
    def test_single_persistent_portfolio_multiple_paper_fills_and_close(self):
        with tempfile.TemporaryDirectory() as td:
            q = PaperQDLE(Path(td) / "one-account.sqlite", PaperBroker())
            snapshot(q, 1, AT)
            symbol(q, AT)
            first = q.reserve_for_trader(request("s1", 1), now=AT)
            self.assertEqual(first.lots, D("0.03"))
            q.paper_fill("s1", AT)
            q.assert_paper_positions({"s1": {"paper_ticket": "PAPER:s1", "lots": D("0.03")}})
            later = AT + timedelta(seconds=1)
            snapshot(q, 2, later, active=("s1",))
            symbol(q, later)
            second = q.reserve_for_trader(request("s2", 2), now=later)
            self.assertGreater(second.lots, D("0"))
            q.paper_fill("s2", later)
            q.assert_paper_positions({
                sid: {"paper_ticket": "PAPER:" + sid, "lots": D("0.03")}
                for sid in ("s1", "s2")
            })
            q.paper_settle("s1", later + timedelta(seconds=1), D("-1.5"))
            q.assert_paper_positions({"s2": {"paper_ticket": "PAPER:s2", "lots": D("0.03")}})
            self.assertEqual(q.paper_coverage(), {
                "physical_quotes": 2, "unassessable": 0,
                "received_accounted": 2, "paper_filled": 2, "paper_settled": 1,
            })
            with self.assertRaises(QDLEError):
                q.paper_settle("s1", later + timedelta(seconds=2), D("-1.5"))
            with self.assertRaises(QDLEError):
                q.acknowledge_fill("s2", "MT5_FAKE")
            with self.assertRaises(QDLEError):
                q.arm_for_live_send("s2")

    def test_unassessable_is_audited_not_fake_physical_quote(self):
        with tempfile.TemporaryDirectory() as td:
            q = PaperQDLE(Path(td) / "account.sqlite", PaperBroker())
            q.paper_unassessable("no_geometry", AT, "INVALID_GEOMETRY")
            self.assertEqual(q.paper_coverage()["unassessable"], 1)
            self.assertEqual(q.paper_coverage()["physical_quotes"], 0)
            with self.assertRaises(Exception):
                q.paper_unassessable("no_geometry", AT, "INVALID_GEOMETRY")
            with self.assertRaises(QDLEError):
                q.paper_fill("no_geometry", AT)

    def test_explicit_cancel_releases_held_paper_quote(self):
        with tempfile.TemporaryDirectory() as td:
            q = PaperQDLE(Path(td) / "account.sqlite", PaperBroker())
            snapshot(q, 1, AT)
            symbol(q, AT)
            self.assertGreater(q.reserve_for_trader(request("s1", 1), now=AT).lots, 0)
            q.paper_cancel("s1", AT, "NO_PATH_NO_FILL")
            self.assertEqual(q.paper_coverage()["paper_filled"], 0)
            with self.assertRaises(QDLEError):
                q.paper_fill("s1", AT)
            t = AT + timedelta(seconds=1)
            snapshot(q, 2, t)
            symbol(q, t)
            self.assertGreater(q.reserve_for_trader(request("s2", 2), now=t).lots, 0)


if __name__ == "__main__":
    unittest.main()
