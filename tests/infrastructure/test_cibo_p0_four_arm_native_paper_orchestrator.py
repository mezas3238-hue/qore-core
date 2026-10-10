"""P0 four-arm sealed source conservation and separate real SQLite PAPER books."""
from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from datetime import datetime,timedelta,timezone
from decimal import Decimal as D
from pathlib import Path

from scripts.cibo_p0_four_arm_native_paper_orchestrator import (
    ArmBook, orchestrate, OrchestrationError,
)
from qore.infrastructure.qore_dynamic_lot_engine import (
    QDLE, QDLEAccount, QDLEIntent, QDLEError,
)

CONF=json.loads(
    (Path(__file__).resolve().parents[2]/
     "config/research/cibo_p0_four_arm_atr_5pct_3368_2026-10-09.json").read_text())
T=datetime(2020,5,5,10,0,tzinfo=timezone.utc)


def one(sid,tf,symbol,trader,n):
    return dict(signal_fingerprint=sid,trader_id=trader,qore_symbol=symbol,
        market_decision_at=(T+timedelta(minutes=n)).isoformat(),
        trader_opportunity=dict(side="long",
            decision_context=[["ctx_timeframe",tf]]))


def sample():
    return dict(opportunities=[
        one("test-vt31","M1","NAS100","VT31_NAS100",1),
        one("test-r38","H1","EURUSD","R38_EURUSD",2),
        one("test-gold","H4","XAUUSD","R34_XAUUSD",3),
    ])


class FourArmOrchestrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir=Path(self.tmp.name)/"scenario-data"

    def run_sample(self):
        return orchestrate(manifest=sample(),config=CONF,output=self.dir,
                           expected_count=3,require_original_seven=False)

    def test_four_independent_sqlite_and_twelve_exact_receipts(self):
        r=self.run_sample()
        self.assertEqual(r["original_signal_count"],3)
        self.assertEqual(r["total_source_arm_receipts"],12)
        self.assertEqual(set(r["arm_results"]),{"A-X","A-Y","B-X","B-Y"})
        self.assertEqual(r["economic_fills"],0)
        self.assertIsNone(r["new_profit_factor"])
        self.assertIsNone(r["new_drawdown_pct"])
        self.assertTrue(r["not_a_four_arm_financial_replay"])
        files=set()
        for arm,part in r["arm_results"].items():
            self.assertEqual(part["coverage"]["unassessable"],3)
            self.assertEqual(part["coverage"]["physical_quotes"],0)
            self.assertEqual(part["coverage"]["paper_filled"],0)
            self.assertEqual(part["mtm"]["cash_usd"],"60")
            path=self.dir/(arm.replace("-","_")+".sqlite")
            self.assertTrue(path.is_file())
            files.add(str(path))
            with sqlite3.connect(path) as db:
                ids={s[0] for s in db.execute("SELECT request_id FROM paper_unassessable")}
                self.assertEqual(ids,{"test-vt31","test-r38","test-gold"})
                self.assertEqual(db.execute(
                    "SELECT COUNT(*) FROM paper_cash_account"
                ).fetchone()[0],1)
                m=db.execute(
                    "SELECT value FROM meta WHERE key='canonical_research_paper_authority'"
                ).fetchone()[0]
                # QDLE stores SQLite meta strings as canonical JSON values.
                self.assertEqual(json.loads(m),"PaperQDLE_V1_SINGLE_RESERVATION_BOOK")
            self.assertTrue(Path(part["sqlite_archive"]["path"]).is_file())
            self.assertTrue(part["receipts_sha256"].startswith("sha256:"))
        self.assertEqual(len(files),4)

    def test_no_reuse_prior_scenario_run_and_broker_live_cannot_reopen(self):
        self.run_sample()
        with self.assertRaisesRegex(OrchestrationError,"prior run"):
            self.run_sample()
        path=self.dir/"A_X.sqlite"
        from scripts.cibo_p0_four_arm_native_paper_orchestrator import NoNativeBrokerCalculator
        with self.assertRaisesRegex(QDLEError,"research-only"):
            QDLE(path,NoNativeBrokerCalculator())

    def test_per_arm_history_cannot_bleed_other_arm(self):
        self.run_sample()
        with sqlite3.connect(self.dir/"A_X.sqlite") as db:
            db.execute("DELETE FROM paper_unassessable WHERE request_id='test-gold'")
            db.commit()
        with sqlite3.connect(self.dir/"A_Y.sqlite") as db:
            self.assertEqual(db.execute(
                "SELECT COUNT(*) FROM paper_unassessable").fetchone()[0],3)
        with sqlite3.connect(self.dir/"A_X.sqlite") as db:
            self.assertEqual(db.execute(
                "SELECT COUNT(*) FROM paper_unassessable").fetchone()[0],2)

    def test_no_market_pack_never_produces_fake_pf_or_lotage(self):
        r=self.run_sample()
        self.assertEqual(r["source_preflight_status_counts"],{
            "NO_CAUSAL_EVIDENCE_PACK_FOR_SIGNAL":3,
        })
        for arm in ("A-X","A-Y","B-X","B-Y"):
            self.assertEqual(r["arm_results"][arm]["unassessable_reasons"],{
                "NO_CAUSAL_EVIDENCE_PACK_FOR_SIGNAL":3,
            })

    def test_missing_native_calculator_refuses_unsubstantiated_positive_quote(self):
        a=ArmBook.open("A-X",self.dir/"A_X.sqlite")
        with self.assertRaisesRegex(QDLEError,"not synchronized"):
            a.reserve(QDLEIntent(
                request_id="unpriced",trader_id="R38_EURUSD",
                symbol="EURUSD",side="BUY",entry_price=D("1.1"),
                stop_price=D("1.099"),requested_risk_usd=D("3"),
                sizing_cap_usd=D("3"),cibo_compound_cap_usd=D("3"),
                portfolio_cap_usd=D("3"),leverage_cap_lots=D("1"),
                margin_cap_usd=D("1000"),source_lane="SOVEREIGN_BANK",
                slippage_usd_per_lot=D(0),expected_account_sequence=1),T)
        self.assertEqual(a.mtm.cash(),D("60"))

    def test_four_arm_config_change_rejected_before_writing_sqlite(self):
        bad=json.loads(json.dumps(CONF))
        bad["scenarios"][0]["arm"]="X-X"
        from scripts.cibo_p0_atr_four_arm_physical_budget import ResearchBlockedError
        with self.assertRaises(ResearchBlockedError):
            orchestrate(manifest=sample(),config=bad,output=self.dir,
                        expected_count=3,require_original_seven=False)
        self.assertFalse(self.dir.exists())


if __name__=="__main__":
    unittest.main()
