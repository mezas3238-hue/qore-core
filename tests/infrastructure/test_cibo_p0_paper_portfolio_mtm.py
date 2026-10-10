"""Native PAPER MTM DD uses canonical PaperQDLE SQLite, not cash-only DD."""
from __future__ import annotations
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal as D
from pathlib import Path

from qore.infrastructure.cibo_p0_native_causal_market import HistoricalBidAsk
from qore.infrastructure.cibo_p0_paper_portfolio_mtm import (
    CanonicalPaperPortfolioMtm,PaperMtmError,
)
from qore.infrastructure.qdle_paper_book import PaperQDLE
from qore.infrastructure.qore_dynamic_lot_engine import (
    QDLEAccount, QDLEIntent, QDLESymbol, BrokerValuation, QDLEError,
)

T=datetime(2026,10,9,12,tzinfo=timezone.utc)
H="sha256:"+"a"*64


class PaperBroker:
    def value(self, spec,intent,now):
        return BrokerValuation(D("93"),D("200"),now,"SYNTHETIC_LOCAL_TEST")
    def check_volume(self,spec,intent,lots):
        if lots<D(".01") or lots%D(".01"):
            raise QDLEError("grid violation")


def snapshot(q,at,seq,nav=D("60")):
    q.publish_account(QDLEAccount(
        account_id="PAPER_MTM",provider="FundedNext",currency="USD",
        sequence=seq,as_of=at,balance=D("2000"),equity=D("2000"),
        free_margin=D("1900"),qore_unreserved_risk_usd=nav,
        sovereign_free_source_usd=nav,cushion_free_source_usd=D(0),
        qore_trading_capital_usd=nav,positions=(),covered_fill_tickets=(),
    ))


def symbol(q,at,name="EURUSD"):
    q.publish_symbol(QDLESymbol(
        broker_symbol=name,aliases=(name,),min_lot=D(".01"),
        max_lot=D("40"),lot_step=D(".01"),directional_volume_limit=D(0),
        tick_size=D(".00001"),tick_value_loss_usd=D("1"),
        contract_size=D(100000),currency_profit="USD",
        fee_usd_per_lot=D(7),fee_provenance="SYNTHETIC_PAPER_OPEN_TEST",
        as_of=at,tradable=True,
    ))


def request(sid,seq,name="EURUSD"):
    return QDLEIntent(
        request_id=sid,trader_id="T01",symbol=name,side="BUY",
        entry_price=D("1.1000"),stop_price=D("1.09907"),
        requested_risk_usd=D("1.5"),sizing_cap_usd=D("3"),
        cibo_compound_cap_usd=D("3"),portfolio_cap_usd=D("3"),
        leverage_cap_lots=D("10"),margin_cap_usd=D("1900"),
        source_lane="SOVEREIGN_BANK",slippage_usd_per_lot=D(0),
        expected_account_sequence=seq,
    )


def quote(at,bid,ask,symbol="EURUSD",source="BROKER_HISTORICAL_EXECUTABLE_BID_ASK"):
    return HistoricalBidAsk(symbol,at,D(str(bid)),D(str(ask)),H,source)


class PortfolioMtm(unittest.TestCase):
    def setUp(self):
        td=tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.path=Path(td.name)/"canonical-single-paper.sqlite"
        self.q=PaperQDLE(self.path,PaperBroker())
        self.nav=CanonicalPaperPortfolioMtm(self.q,starting_nav_usd=D("60"))
        snapshot(self.q,T,1)
        symbol(self.q,T)

    def open(self,sid="one",at=T,sequence=1,asset="EURUSD"):
        result=self.q.reserve_for_trader(request(sid,sequence,asset),now=at)
        self.assertEqual(result.lots,D(".01"))
        self.q.paper_fill(sid,at)
        self.nav.book_open(request_id=sid,at=at,side="BUY",symbol=asset,
            entry=D("1.1000"),lots=D(".01"),
            contract_usd_per_price_unit_lot=D(100000),
            commission_open_usd=D(".07"))
        return result

    def test_cash_vs_equity_dd_and_exact_reconciliation(self):
        self.open()
        self.assertEqual(self.nav.cash(),D("59.93"))
        first=self.nav.mark(at=T+timedelta(seconds=1),
                            quotes=(quote(T+timedelta(seconds=1),"1.0990","1.0991"),))
        self.assertEqual(D(first["unrealized_usd"]),D("-1.0"))
        self.assertEqual(D(first["equity_usd"]),D("58.93"))
        self.assertEqual(D(first["cash_usd"]),D("59.93"))
        self.assertGreater(D(first["equity_drawdown_pct"]),
                           D(first["cash_drawdown_pct"]))
        # A profitable close is NOT allowed to overwrite the earlier
        # underwater equity drawdown.
        close_at=T+timedelta(seconds=3)
        self.q.paper_settle("one",close_at,D(".50"))
        self.nav.book_close(request_id="one",at=close_at,gross_pnl_usd=D(".50"))
        self.assertEqual(self.nav.cash(),D("60.43"))
        after=self.nav.mark(at=T+timedelta(seconds=4),quotes=())
        self.assertEqual(D(after["equity_usd"]),D("60.43"))
        self.assertEqual(D(after["unrealized_usd"]),D(0))
        self.assertEqual(D(after["maximum_equity_drawdown_pct"]),
                         D(first["equity_drawdown_pct"]))
        self.assertEqual(self.nav.summary()["total_paper_openings"],1)
        self.assertEqual(self.nav.summary()["open_positions"],0)
        self.assertEqual(self.nav.summary()["fully_marked_epochs"],2)
        self.assertEqual(self.q.paper_coverage()["paper_settled"],1)

    def test_no_future_or_missing_price_marks_and_no_hidden_zero_fallback(self):
        self.open()
        at=T+timedelta(seconds=1)
        with self.assertRaisesRegex(PaperMtmError,"MISSING_CAUSAL_MTM_MARK"):
            self.nav.mark(at=at,quotes=())
        with self.assertRaisesRegex(PaperMtmError,"NO_CAUSAL"):
            self.nav.mark(at=at,quotes=(quote(at+timedelta(seconds=1),"1.101","1.102"),))
        self.assertEqual(self.nav.summary()["fully_marked_epochs"],0)
        good=self.nav.mark(at=at,quotes=(quote(at,"1.101","1.102"),))
        self.assertEqual(good["mark_count"],1)

    def test_double_cash_debit_and_double_pnl_credit_impossible(self):
        self.open()
        self.open()
        self.assertEqual(self.nav.cash(),D("59.93"))
        with self.assertRaisesRegex(PaperMtmError,"conflicting PAPER OPEN"):
            self.nav.book_open(request_id="one",at=T,side="BUY",symbol="EURUSD",
                entry=D("1.101"),lots=D(".01"),
                contract_usd_per_price_unit_lot=D(100000),
                commission_open_usd=D(".07"))
        when=T+timedelta(seconds=1)
        self.q.paper_settle("one",when,D("1"))
        self.nav.book_close(request_id="one",at=when,gross_pnl_usd=D("1"))
        self.nav.book_close(request_id="one",at=when,gross_pnl_usd=D("1"))
        self.assertEqual(self.nav.cash(),D("60.93"))
        with self.assertRaisesRegex(PaperMtmError,"conflicting PAPER CLOSE"):
            self.nav.book_close(request_id="one",at=when,gross_pnl_usd=D(".5"))

    def test_same_sqlite_restart_and_no_fake_MTM_prior_to_open_receipt(self):
        result=self.q.reserve_for_trader(request("not-yet-filled",1),now=T)
        self.assertGreater(result.lots,0)
        with self.assertRaisesRegex(PaperMtmError,"canonical PAPER_FILLED"):
            self.nav.book_open(request_id="not-yet-filled",at=T,
                side="BUY",symbol="EURUSD",entry=D("1.1"),lots=D(".01"),
                contract_usd_per_price_unit_lot=D(100000),
                commission_open_usd=D(".07"))
        self.assertEqual(self.nav.cash(),D("60"))
        self.q.paper_cancel("not-yet-filled",T,"TEST_ABORT")
        reopened=PaperQDLE(self.path,PaperBroker())
        restored=CanonicalPaperPortfolioMtm(reopened)
        self.assertEqual(restored.cash(),D("60"))
        with self.assertRaisesRegex(PaperMtmError,"initial NAV cannot change"):
            CanonicalPaperPortfolioMtm(reopened,starting_nav_usd=D("90"))

    def test_commission_cannot_diverge_from_qdle_economics(self):
        result=self.q.reserve_for_trader(request("mismatch",1),now=T)
        self.q.paper_fill("mismatch",T)
        with self.assertRaisesRegex(PaperMtmError,"opening fee diverges"):
            self.nav.book_open(request_id="mismatch",at=T,side="BUY",
                symbol="EURUSD",entry=D("1.1"),lots=result.lots,
                contract_usd_per_price_unit_lot=D(100000),
                commission_open_usd=D(".14"))
        self.assertEqual(self.nav.cash(),D("60"))

    def test_unpriced_other_open_position_blocks_global_dd(self):
        self.open("one")
        t=T+timedelta(seconds=1)
        fully_marked=self.nav.mark(
            at=t,quotes=(quote(t,"1.099","1.100"),))
        snapshot(self.q,t,2,nav=D(fully_marked["equity_usd"]))
        symbol(self.q,t,"GBPUSD")
        second=self.q.reserve_for_trader(request("two",2,"GBPUSD"),now=t)
        self.assertEqual(second.lots,D(".01"))
        self.q.paper_fill("two",t)
        self.nav.book_open(request_id="two",at=t,side="BUY",symbol="GBPUSD",
            entry=D("1.1"),lots=D(".01"),contract_usd_per_price_unit_lot=D(100000),
            commission_open_usd=D(".07"))
        when=t+timedelta(seconds=1)
        with self.assertRaisesRegex(PaperMtmError,"MISSING_CAUSAL_MTM_MARK two"):
            self.nav.mark(at=when,quotes=(quote(when,"1.099","1.100"),))
        self.assertEqual(self.nav.summary()["fully_marked_epochs"],0)
        marks=self.nav.mark(at=when,quotes=(
            quote(when,"1.099","1.100"),
            quote(when,"1.098","1.099","GBPUSD"),
        ))
        self.assertEqual(marks["mark_count"],2)

    def test_inflight_fill_without_cash_book_or_close_without_cash_release_blocks(self):
        q=self.q.reserve_for_trader(request("inflight",1),now=T)
        self.assertEqual(q.lots,D(".01"))
        self.q.paper_fill("inflight",T)
        later=T+timedelta(seconds=1)
        snapshot(self.q,later,2)
        symbol(self.q,later)
        with self.assertRaisesRegex(QDLEError,"open trades / MTM cash journal mismatch"):
            self.q.reserve_for_trader(request("pending-ledger",2),now=later)
        self.nav.book_open(request_id="inflight",at=T,side="BUY",symbol="EURUSD",
            entry=D("1.1"),lots=D(".01"),
            contract_usd_per_price_unit_lot=D(100000),
            commission_open_usd=D(".07"))
        fully_marked=self.nav.mark(
            at=later,quotes=(quote(later,"1.099","1.100"),))
        snapshot(self.q,later,3,nav=D(fully_marked["equity_usd"]))
        release=self.q.reserve_for_trader(request("ready",3),now=later)
        self.assertEqual(release.lots,D(".01"))
        # Quoted but not filled holds DO NOT appear as active positions.
        self.q.paper_cancel("ready",later,"TEST_CANCEL")
        done=later+timedelta(seconds=1)
        self.q.paper_settle("inflight",done,D(".50"))
        snapshot(self.q,done,4,nav=self.nav.cash())
        with self.assertRaisesRegex(QDLEError,"open trades / MTM cash journal mismatch"):
            self.q.reserve_for_trader(request("bad-close",4),now=done)

    def test_new_QDLE_reserve_refuses_stale_or_mismatched_MTM_nav(self):
        self.open("one")
        later=T+timedelta(seconds=1)
        # No post-open MTM mark: merely publishing raw cash is not enough
        # for a new QDLE risk reservation.
        snapshot(self.q,later,2,nav=self.nav.cash())
        symbol(self.q,later)
        with self.assertRaisesRegex(QDLEError,"complete MTM NAV epoch"):
            self.q.reserve_for_trader(request("second",2),now=later)
        full=self.nav.mark(
            at=later,quotes=(quote(later,"1.099","1.100"),))
        self.assertEqual(D(full["equity_usd"]),D("58.93"))
        snapshot(self.q,later,3,nav=D("60"))  # deliberately falsified
        with self.assertRaisesRegex(QDLEError,"complete MTM NAV epoch"):
            self.q.reserve_for_trader(request("third",3),now=later)
        # Correct, fully marked as-of NAV from identical PAPER SQLite works.
        snapshot(self.q,later,4,nav=D(full["equity_usd"]))
        approved=self.q.reserve_for_trader(request("fourth",4),now=later)
        self.assertEqual(approved.lots,D(".01"))

    def test_non_UTC_event_dates_rejected_not_lexicographic(self):
        from datetime import timezone as tz
        offset=tz(timedelta(hours=3))
        with self.assertRaisesRegex(PaperMtmError,"canonical UTC"):
            self.nav.mark(at=T.astimezone(offset),quotes=())


if __name__=="__main__":
    unittest.main()
