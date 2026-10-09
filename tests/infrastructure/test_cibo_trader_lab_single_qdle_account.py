"""End-to-end local QDLE reservations and settlements in Trader Lab PAPER only.

Synthetic fills/settlements are explicitly non-MT5 and the live gateway stays
unused. Tests exercise the production QDLE physical kernel with an isolated
per-simulation account SQLite database.
"""
import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal as D
from pathlib import Path

from scripts.cibo_trader_lab_native_qdle_market_atlas_3368 import (
    PaperQdleSession, _mode_quote,
)
from qore.infrastructure.qore_dynamic_lot_engine import QDLEError


class PersistentPaperQdleTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "account-qdle.sqlite"
        self.session = PaperQdleSession(self.path)
        self.start = datetime(2020, 3, 2, 10, tzinfo=timezone.utc)

    @staticmethod
    def _row(sid):
        return {
            "signal_fingerprint": sid,
            "trader": "TRADER_TEST",
            "four_engine_caps_usd": {
                "SIZING": "30",
                "CIBO_COMPOUND": "30",
                "PORTFOLIO_COMPOUND_AVAILABLE_SOURCE": "30",
            },
            "cibo_max_native_requested_risk_fraction_of_nav": "0.05",
            "leverage_max_lots": "1",
            "leverage_margin_budget_usd": "2000",
        }

    def _quote(self, sid, t, nav=D("60"), active=None):
        return _mode_quote(
            self._row(sid), "EURUSD", "BUY", D("1.10000"),
            D("1.09900"), D("100"), D("7"), t, nav,
            active if active is not None else {}, self.session,
        )

    def _state(self, sid):
        with sqlite3.connect(self.path) as db:
            return db.execute(
                "SELECT state FROM reservations WHERE request_id=?", (sid,)
            ).fetchone()[0]

    def test_one_database_fill_and_settle_without_reusing_reserve(self):
        first = self._quote("signal-1", self.start)
        self.assertGreater(first.lots, D(0))
        self.assertLessEqual(first.total_risk_usd, D("3"))
        self.assertEqual(self._state("signal-1"), "HELD")
        fee = first.lots * D("7")
        active = {
            "signal-1": {
                "symbol": "EURUSD", "side": "BUY", "lots": first.lots,
                "risk": first.total_risk_usd, "margin": first.margin_usd,
            }
        }
        nav_after_open_fee = D("60") - fee
        self.session.paper_fill(
            sid="signal-1", at=self.start, nav=nav_after_open_fee, active=active,
        )
        self.assertEqual(self._state("signal-1"), "ABSORBED")
        second = self._quote(
            "signal-2", self.start+timedelta(minutes=5),
            nav_after_open_fee, active,
        )
        self.assertGreaterEqual(second.lots, D(0))
        if second.lots:
            self.session.paper_no_fill(sid="signal-2",reason="SIMULATED_CANCEL")
            self.assertEqual(self._state("signal-2"), "REJECTED_NO_FILL")
        active.clear()
        after_close_nav = nav_after_open_fee + D("0.5")
        self.session.publish_snapshot(
            at=self.start+timedelta(minutes=10),
            nav=after_close_nav, active=active,
        )
        self.session.paper_settlement(sid="signal-1", realized_net=D("0.5"))
        self.assertEqual(self._state("signal-1"), "SETTLED")
        with sqlite3.connect(self.path) as db:
            rows = db.execute(
                "SELECT request_id,deal_receipt FROM broker_settlements"
            ).fetchall()
        self.assertEqual(rows, [("signal-1", "PAPER_SIMULATOR_SETTLED:signal-1")])
        self.assertGreaterEqual(self.session.sequence, 4)

    def test_two_concurrent_fills_reconcile_in_one_account(self):
        active = {}
        nav = D("60")
        for ix in (1,2):
            sid = "concurrent-" + str(ix)
            quote = self._quote(sid,self.start+timedelta(minutes=ix),nav,active)
            self.assertGreater(quote.lots,D(0))
            nav -= quote.lots*D("7")
            active[sid] = {
                "symbol": "EURUSD", "side": "BUY",
                "lots": quote.lots, "risk": quote.total_risk_usd,
                "margin": quote.margin_usd,
            }
            self.session.paper_fill(
                sid=sid,at=self.start+timedelta(minutes=ix),
                nav=nav,active=active,
            )
        with sqlite3.connect(self.path) as db:
            states = db.execute(
                "SELECT request_id,state FROM reservations ORDER BY request_id"
            ).fetchall()
        self.assertEqual(states,[("concurrent-1","ABSORBED"),
                                 ("concurrent-2","ABSORBED")])
        self.assertGreater(sum(t["risk"] for t in active.values()),D("3"))
        # Shared portfolio capital prevents infinite simultaneous fills,
        # even though sovereign 5% is an individual trade upper bound.
        third = self._quote(
            "concurrent-3",self.start+timedelta(minutes=3),nav,active,
        )
        self.assertGreaterEqual(third.lots,D("0"))
        self.assertLessEqual(
            third.total_risk_usd,
            max(D(0),nav-sum(t["risk"] for t in active.values())),
        )

    def test_no_paper_fill_without_positive_reservation(self):
        with self.assertRaises(QDLEError):
            self.session.paper_fill(
                sid="unquoted",at=self.start,nav=D("60"),active={}
            )


if __name__ == "__main__":
    unittest.main()
