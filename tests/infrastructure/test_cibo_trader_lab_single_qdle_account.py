"""Integration P0: #746 Trader Lab uses the one #745 canonical PaperQDLE."""
from __future__ import annotations

import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal as D
from pathlib import Path

from scripts.cibo_trader_lab_native_qdle_market_atlas_3368 import (
    PaperQdleSession, _mode_quote,
)
from qore.infrastructure.qore_dynamic_lot_engine import QDLE, QDLEError
from qore.infrastructure.qdle_paper_book import PaperQDLE


class CanonicalSessionIntegration(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.path=Path(temp.name)/"one-and-only-paper.sqlite"
        self.session=PaperQdleSession(self.path)
        self.t=datetime(2020,3,2,10,tzinfo=timezone.utc)

    @staticmethod
    def _row(sid, fraction="0.05"):
        return {
            "signal_fingerprint":sid,
            "trader":"TRADER_TEST",
            "four_engine_caps_usd":{
                "SIZING":"30","CIBO_COMPOUND":"30",
                "PORTFOLIO_COMPOUND_AVAILABLE_SOURCE":"30",
            },
            "cibo_max_native_requested_risk_fraction_of_nav":fraction,
            "leverage_max_lots":"1","leverage_margin_budget_usd":"2000",
        }

    def quote(self,sid,at,nav=D("60"),fraction="0.05",active=None):
        return _mode_quote(
            self._row(sid,fraction), "EURUSD","BUY",D("1.10000"),
            D("1.09900"),D("100"),D("7"),at,nav,
            active if active is not None else {},self.session,
        )

    def state(self,sid):
        with sqlite3.connect(self.path) as db:
            return db.execute(
                "SELECT state FROM reservations WHERE request_id=?", (sid,)
            ).fetchone()[0]

    def test_single_authority_open_settle_and_no_broker_events(self):
        q=self.quote("source-1",self.t)
        self.assertEqual(q.lots,D(".02"))
        self.assertEqual(self.state("source-1"),"HELD")
        fee=q.lots*D("7")
        nav=D("60")-fee
        active={"source-1":{
            "symbol":"EURUSD","side":"BUY","lots":q.lots,
            "risk":q.total_risk_usd,"margin":q.margin_usd,
            "paper_ticket":"PAPER:source-1",
        }}
        self.session.paper_fill(sid="source-1",at=self.t,nav=nav,active=active)
        self.assertEqual(self.state("source-1"),"PAPER_FILLED")
        self.session.qdle.assert_paper_positions(active)
        # The second $1.07 physical 0.01-lot cannot fit after first $2.14
        # reservation in a 5%-of-$59.86 account.
        later=self.t+timedelta(minutes=5)
        second=self.quote("source-2",later,nav,active=active)
        self.assertEqual(second.lots,D(0))
        self.assertEqual(self.state("source-2"),"BLOCKED")
        self.session.paper_settle(sid="source-1",
                                  at=later+timedelta(seconds=1),
                                  gross=D(".50"))
        self.assertEqual(self.state("source-1"),"PAPER_SETTLED")
        self.session.paper_settle(sid="source-1",
                                  at=later+timedelta(seconds=1),
                                  gross=D(".50"))
        with sqlite3.connect(self.path) as db:
            row=db.execute(
                "SELECT paper_ticket,realized_gross_usd FROM paper_trades "
                "WHERE request_id='source-1'"
            ).fetchone()
            broker_deals=db.execute(
                "SELECT COUNT(*) FROM broker_settlements"
            ).fetchone()[0]
            events=dict(db.execute(
                "SELECT event,COUNT(*) FROM audit GROUP BY event"
            ).fetchall())
        self.assertEqual(row,("PAPER:source-1","0.50"))
        self.assertEqual(broker_deals,0)
        self.assertEqual(events["PAPER_FILL_MODELED_NOT_MT5"],1)
        self.assertEqual(events["PAPER_SETTLED_NOT_MT5"],1)
        with self.assertRaisesRegex(QDLEError,"research-only"):
            QDLE(self.path,self.session.broker)

    def test_multiple_concurrent_positions_respect_shared_5pct(self):
        nav=D("60")
        active={}
        for idx in (1,2):
            sid="concurrent-"+str(idx)
            at=self.t+timedelta(minutes=idx)
            q=self.quote(sid,at,nav,fraction="0.025",active=active)
            self.assertEqual(q.lots,D(".01"))
            fee=q.lots*D("7")
            nav-=fee
            active[sid]={
                "symbol":"EURUSD","side":"BUY","lots":q.lots,
                "risk":q.total_risk_usd,"margin":q.margin_usd,
                "paper_ticket":"PAPER:"+sid,
            }
            self.session.paper_fill(sid=sid,at=at,nav=nav,active=active)
        self.session.qdle.assert_paper_positions(active)
        risk=sum((x["risk"] for x in active.values()),D(0))
        self.assertEqual(risk,D("2.14"))
        self.assertLessEqual(risk,nav*D("0.05"))
        third=self.quote("concurrent-3",self.t+timedelta(minutes=3),nav,active=active)
        self.assertEqual(third.lots,D(0))
        self.assertEqual(self.session.qdle.paper_coverage()["paper_filled"],2)
        with sqlite3.connect(self.path) as db:
            states=db.execute(
                "SELECT request_id,state FROM reservations "
                "WHERE state='PAPER_FILLED' ORDER BY request_id"
            ).fetchall()
        self.assertEqual(states,[
            ("concurrent-1","PAPER_FILLED"),
            ("concurrent-2","PAPER_FILLED"),
        ])

    def test_unassessable_and_cancel_preserve_distinct_receipts(self):
        missing=self.session.paper_unassessable(
            sid="no-native-m1",reason="NATIVE_M1_PRICE_NOT_VERIFIED",
            at=self.t,nav=D("60"),active={})
        self.assertEqual(missing.state,"RESEARCH_UNASSESSABLE_NOT_QUOTED")
        self.assertEqual(missing.lots,D(0))
        q=self.quote("cancelled",self.t+timedelta(minutes=1))
        self.assertGreater(q.lots,D(0))
        self.session.paper_no_fill(
            sid="cancelled",at=self.t+timedelta(minutes=1),
            reason="NO_CAUSAL_EXIT_PRICE_PATH")
        self.assertEqual(self.state("cancelled"),"PAPER_CANCELLED")
        self.assertEqual(self.session.qdle.paper_coverage()["received_accounted"],2)
        with self.assertRaises(QDLEError):
            self.session.paper_fill(
                sid="no-native-m1",at=self.t,nav=D("60"),active={})

    def test_no_generic_parallel_research_book(self):
        with self.assertRaisesRegex(QDLEError,"canonical PaperQDLE"):
            QDLE(self.path,self.session.broker,research_paper_mode=True)
        self.assertIsInstance(self.session.qdle,PaperQDLE)


if __name__=="__main__":
    unittest.main()
