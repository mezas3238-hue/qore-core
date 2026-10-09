"""P0 #746 migration gate: canonical PaperQDLE only, never generic research QDLE."""
from __future__ import annotations

import tempfile
import unittest
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
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
    # PAPER_FILLED positions are reserved INSIDE SQLite; snapshots must
    # publish gross NAV and broker margin with no mirrored MT5 positions.
    q.publish_account(QDLEAccount(
        account_id="PAPER_ACCOUNT", provider="FundedNext", currency="USD",
        sequence=sequence, as_of=at, balance=D("2000"), equity=D("2000"),
        free_margin=D("1900"),
        qore_unreserved_risk_usd=D("60"),
        sovereign_free_source_usd=D("60"),
        cushion_free_source_usd=D("0"),
        qore_trading_capital_usd=D("60"),
        positions=(), covered_fill_tickets=(),
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
    def test_opening_commission_debit_cannot_break_dynamic_five_pct_cap(self):
        class FeeBroker(PaperBroker):
            def value(self, instrument, intent, now):
                return BrokerValuation(D("90"),D("200"),now,"TEST_NOT_MT5")
        with tempfile.TemporaryDirectory() as td:
            q=PaperQDLE(Path(td)/"fee-account.sqlite",FeeBroker())
            snapshot(q,1,AT)
            q.publish_symbol(QDLESymbol(
                broker_symbol="EURUSD",aliases=("EURUSD",),
                min_lot=D(".01"),max_lot=D("10"),lot_step=D(".01"),
                directional_volume_limit=D(0),tick_size=D(".00001"),
                tick_value_loss_usd=D("1"),contract_size=D("100000"),
                currency_profit="USD",fee_usd_per_lot=D("10"),
                fee_provenance="PAPER_OPEN_FEE_TEST",as_of=AT,tradable=True,
            ))
            # Before OPEN fee: 0.03 lots * $100 all-in = exactly $3.
            # Afterwards: NAV=$59.70, so max aggregate is only $2.985.
            # The repaired physical PAPER book must round down to 0.02.
            result=q.reserve_for_trader(request("with_fee",1),now=AT)
            self.assertEqual(result.lots,D(".02"))
            immediate_fee=result.lots*D("10")
            self.assertLessEqual(result.total_risk_usd,
                                 D("0.05")*(D("60")-immediate_fee))
            q.paper_fill("with_fee",AT)
            q.assert_paper_positions({
                "with_fee":{"paper_ticket":"PAPER:with_fee","lots":D(".02")}
            })

    def test_single_account_total_five_pct_hold_and_idempotent_settlement(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td) / "one-account.sqlite"
            q=PaperQDLE(path,PaperBroker())
            snapshot(q,1,AT)
            symbol(q,AT)
            first=q.reserve_for_trader(request("s1",1),now=AT)
            self.assertEqual(first.lots,D("0.03"))
            self.assertEqual(q.paper_fill("s1",AT),"PAPER:s1")
            self.assertEqual(q.paper_fill("s1",AT),"PAPER:s1")
            q.assert_paper_positions({
                "s1":{"paper_ticket":"PAPER:s1","lots":D("0.03")}
            })
            t=AT+timedelta(seconds=1)
            snapshot(q,2,t,active=("s1",))
            symbol(q,t)
            # QDLE sees PAPER_FILLED risk=$3 in SQLite and enforces TOTAL
            # portfolio risk 5% of NAV=$60, not 5% per new entry.
            denied=q.reserve_for_trader(request("s2",2),now=t)
            self.assertEqual(denied.lots,D(0))
            q.paper_settle("s1",t,D("-1.5"))
            q.paper_settle("s1",t,D("-1.5"))  # exactly-once retry
            with self.assertRaises(QDLEError):
                q.paper_settle("s1",t,D("-2"))
            t2=t+timedelta(seconds=1)
            snapshot(q,3,t2)
            symbol(q,t2)
            funded=q.reserve_for_trader(request("s3",3),now=t2)
            self.assertEqual(funded.lots,D("0.03"))
            q.paper_fill("s3",t2)
            q.assert_paper_positions({
                "s3":{"paper_ticket":"PAPER:s3","lots":D("0.03")}
            })
            self.assertEqual(q.paper_coverage(),{
                "physical_quotes":3,"unassessable":0,
                "received_accounted":3,"paper_filled":2,"paper_settled":1,
            })
            with self.assertRaises(QDLEError):
                q.acknowledge_fill("s3","MT5_FAKE")
            with self.assertRaises(QDLEError):
                q.arm_for_live_send("s3")

    def test_legacy_competing_paper_marker_requires_explicit_migration(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"other-paper.sqlite"
            with sqlite3.connect(path) as db:
                db.execute(
                    "CREATE TABLE meta(key TEXT PRIMARY KEY,value TEXT NOT NULL)")
                db.execute(
                    "INSERT INTO meta VALUES('research_paper_database','true')")
            with self.assertRaisesRegex(QDLEError,"competing PAPER SQLite"):
                PaperQDLE(path,PaperBroker())

    def test_prior_live_snapshot_without_reservations_not_silently_converted(self):
        from qore.infrastructure.qore_dynamic_lot_engine import QDLE
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"broker.sqlite"
            broker=QDLE(path,PaperBroker())
            snapshot(broker,1,AT)
            with self.assertRaisesRegex(QDLEError,"explicit migration"):
                PaperQDLE(path,PaperBroker())

    def test_second_generic_paper_authority_is_rejected(self):
        from qore.infrastructure.qore_dynamic_lot_engine import QDLE
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaisesRegex(QDLEError,"canonical PaperQDLE"):
                QDLE(Path(td)/"competing.sqlite",PaperBroker(),
                     research_paper_mode=True)

    def test_existing_broker_reservations_cannot_be_relabelled_paper(self):
        from qore.infrastructure.qore_dynamic_lot_engine import QDLE
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"broker.sqlite"
            broker=QDLE(path,PaperBroker())
            snapshot(broker,1,AT)
            symbol(broker,AT)
            self.assertEqual(
                broker.reserve_for_trader(request("real_hold",1),now=AT).lots,
                D("0.03"))
            with self.assertRaisesRegex(QDLEError,"cannot convert broker reservations"):
                PaperQDLE(path,PaperBroker())

    def test_paper_sqlite_rejects_broker_QDLE_reopen_after_restart(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"paper.sqlite"
            q=PaperQDLE(path,PaperBroker())
            snapshot(q,1,AT)
            symbol(q,AT)
            q.reserve_for_trader(request("s1",1),now=AT)
            q.paper_fill("s1",AT)
            from qore.infrastructure.qore_dynamic_lot_engine import QDLE
            with self.assertRaisesRegex(QDLEError,"research-only"):
                QDLE(path,PaperBroker())
            reopened=PaperQDLE(path,PaperBroker())
            t=AT+timedelta(seconds=1)
            snapshot(reopened,2,t)
            symbol(reopened,t)
            self.assertEqual(
                reopened.reserve_for_trader(request("s2",2),now=t).lots,D(0))
            reopened.assert_paper_positions({
                "s1":{"paper_ticket":"PAPER:s1","lots":D("0.03")}
            })

    def test_two_concurrent_reservations_cannot_both_spend_five_pct(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"one-account.sqlite"
            first=PaperQDLE(path,PaperBroker())
            second=PaperQDLE(path,PaperBroker())
            snapshot(first,1,AT)
            symbol(first,AT)
            # Each process publishes/observes the same immutable snapshot.
            snapshot(second,2,AT+timedelta(seconds=1))
            symbol(second,AT+timedelta(seconds=1))
            now=AT+timedelta(seconds=1)
            with ThreadPoolExecutor(max_workers=2) as pool:
                futures=[
                    pool.submit(first.reserve_for_trader,request("s1",2),now),
                    pool.submit(second.reserve_for_trader,request("s2",2),now),
                ]
                lots=[f.result().lots for f in futures]
            self.assertEqual(sorted(lots),[D(0),D("0.03")])
            self.assertEqual(first.paper_coverage()["physical_quotes"],2)

    def test_paper_rejects_pre_subtracted_or_mirrored_snapshot(self):
        with tempfile.TemporaryDirectory() as td:
            q=PaperQDLE(Path(td)/"book.sqlite",PaperBroker())
            base=QDLEAccount(
                account_id="PAPER_ACCOUNT",provider="FundedNext",currency="USD",
                sequence=1,as_of=AT,balance=D("2000"),equity=D("2000"),
                free_margin=D("1900"),qore_unreserved_risk_usd=D("57"),
                sovereign_free_source_usd=D("57"),cushion_free_source_usd=D(0),
                qore_trading_capital_usd=D("60"))
            with self.assertRaisesRegex(QDLEError,"double-count"):
                q.publish_account(base)
            with self.assertRaisesRegex(QDLEError,"double-count"):
                q.publish_account(replace(
                    base,qore_unreserved_risk_usd=D("60"),
                    sovereign_free_source_usd=D("60"),
                    positions=(Position("PAPER:FAKE","EURUSD","BUY",D(".01")),),
                    covered_fill_tickets=("PAPER:FAKE",),
                ))

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
