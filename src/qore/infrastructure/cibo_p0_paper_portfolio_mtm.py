"""CIBO PAPER event-sourced portfolio NAV + equity MTM in canonical QDLE SQLite.

Research only. ALL monetary events persist inside the same PaperQDLE SQLite,
not a separate account ledger. Tick observations are historical BID/ASK and
must not be future-dated; NO zero-mark fallback when a position is unpriced.
Cash DD and EQUITY DD are distinct and must not be interchanged. Results are
not broker-certified or MT5 settlements.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
import json

from qore.infrastructure.cibo_p0_native_causal_market import (
    HistoricalBidAsk,exact_asof_quote,CausalEvidenceError,
)
from qore.infrastructure.qdle_paper_book import PaperQDLE
from qore.infrastructure.qore_dynamic_lot_engine import QDLEError

D=Decimal
ZERO=D(0)


class PaperMtmError(ValueError):
    pass


def _number(raw,name,positive=False):
    if not isinstance(raw,D) or not raw.is_finite() or (raw<=ZERO if positive else raw<ZERO):
        raise PaperMtmError(name+": finite "+("positive" if positive else "nonnegative")+" Decimal required")
    return raw


def _timestamp(t):
    if not isinstance(t,datetime) or t.tzinfo is None or t.utcoffset() is None:
        raise PaperMtmError("timezone-aware event instant required")
    return t


class CanonicalPaperPortfolioMtm:
    """One account per scenario; each account's fills+NAV share exactly one DB."""

    def __init__(self, qdle:PaperQDLE, *, starting_nav_usd:D=D("60")):
        if type(qdle) is not PaperQDLE:
            raise PaperMtmError("canonical PaperQDLE singleton required")
        self.qdle=qdle
        _number(starting_nav_usd,"initial NAV",positive=True)
        with qdle._tx() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS paper_cash_account(
                id INTEGER PRIMARY KEY CHECK(id=1),
                initial_nav TEXT NOT NULL, cash TEXT NOT NULL,
                equity_peak TEXT NOT NULL,cash_peak TEXT NOT NULL,
                equity_max_dd_pct TEXT NOT NULL,cash_max_dd_pct TEXT NOT NULL,
                last_snapshot_at TEXT
            )""")
            db.execute("""CREATE TABLE IF NOT EXISTS paper_mtm_positions(
                request_id TEXT PRIMARY KEY,
                symbol TEXT NOT NULL, side TEXT NOT NULL,
                entry_at TEXT NOT NULL, entry_price TEXT NOT NULL,
                lots TEXT NOT NULL, pnl_usd_per_price_unit_lot TEXT NOT NULL,
                fee_open_usd TEXT NOT NULL,
                settled_at TEXT, gross_close_usd TEXT
            )""")
            db.execute("""CREATE TABLE IF NOT EXISTS paper_mtm_event_log(
                event_id TEXT PRIMARY KEY, kind TEXT NOT NULL,
                instant TEXT NOT NULL, payload TEXT NOT NULL
            )""")
            db.execute("""CREATE TABLE IF NOT EXISTS paper_mtm_snapshots(
                at TEXT PRIMARY KEY, cash TEXT NOT NULL, unrealized TEXT NOT NULL,
                equity TEXT NOT NULL, equity_dd_pct TEXT NOT NULL,
                cash_dd_pct TEXT NOT NULL, mark_receipts TEXT NOT NULL
            )""")
            row=db.execute("SELECT initial_nav FROM paper_cash_account WHERE id=1").fetchone()
            if row is None:
                db.execute("INSERT INTO paper_cash_account VALUES(1,?,?,?,?,?,?,NULL)",
                    (str(starting_nav_usd),str(starting_nav_usd),
                     str(starting_nav_usd),str(starting_nav_usd),"0","0"))
            elif D(row[0])!=starting_nav_usd:
                raise PaperMtmError("paper initial NAV cannot change on restart")

    @staticmethod
    def _event(db,event_id,kind,instant,payload)->bool:
        if not isinstance(event_id,str) or not event_id:
            raise PaperMtmError("event identity required")
        as_json=json.dumps(payload,sort_keys=True,separators=(",",":"))
        old=db.execute("SELECT kind,instant,payload FROM paper_mtm_event_log WHERE event_id=?",
                       (event_id,)).fetchone()
        if old is not None:
            if old!=(kind,instant.isoformat(),as_json):
                raise PaperMtmError("conflicting PAPER financial event replay")
            return False
        db.execute("INSERT INTO paper_mtm_event_log VALUES(?,?,?,?)",
                   (event_id,kind,instant.isoformat(),as_json))
        return True

    @staticmethod
    def _latest_event_time(db):
        row=db.execute("SELECT MAX(instant) FROM paper_mtm_event_log").fetchone()
        return datetime.fromisoformat(row[0]) if row and row[0] else None

    def _check_monotone(self,db,now):
        last=self._latest_event_time(db)
        if last is not None and now<last:
            raise PaperMtmError("financial events must arrive in causal timestamp order")

    def cash(self)->D:
        with self.qdle._tx() as db:
            return D(db.execute("SELECT cash FROM paper_cash_account WHERE id=1").fetchone()[0])

    def book_open(self,*,request_id:str,at:datetime,side:str,symbol:str,
                  entry:D,lots:D,contract_usd_per_price_unit_lot:D,
                  commission_open_usd:D) -> None:
        _timestamp(at)
        if side not in ("BUY","SELL") or not symbol:
            raise PaperMtmError("physical symbol/side required")
        for n,v in (("entry",entry),("lots",lots),("contract",contract_usd_per_price_unit_lot)):
            _number(v,n,positive=True)
        _number(commission_open_usd,"opening fee")
        payload=dict(request_id=request_id,side=side,symbol=symbol,entry=str(entry),
            lots=str(lots),contract=str(contract_usd_per_price_unit_lot),
            commission_open=str(commission_open_usd))
        with self.qdle._tx() as db:
            old=db.execute("SELECT kind,instant,payload FROM paper_mtm_event_log WHERE event_id=?",
                           ("OPEN:"+request_id,)).fetchone()
            if old is not None:
                if old!=("OPEN",at.isoformat(),json.dumps(
                        payload,sort_keys=True,separators=(",",":"))):
                    raise PaperMtmError("conflicting PAPER OPEN")
                return
            self._check_monotone(db,at)
            row=db.execute(
                "SELECT r.state,r.lots,t.opened_at FROM reservations r "
                "JOIN paper_trades t ON t.request_id=r.request_id WHERE r.request_id=?",
                (request_id,)).fetchone()
            if (row is None or row[0]!="PAPER_FILLED"
                    or D(row[1])!=lots or row[2]!=at.isoformat()):
                raise PaperMtmError("only canonical PAPER_FILLED reservation may debit cash")
            cash=D(db.execute("SELECT cash FROM paper_cash_account WHERE id=1").fetchone()[0])
            if commission_open_usd>cash:
                raise PaperMtmError("paper opening commission exceeds cash")
            self._event(db,"OPEN:"+request_id,"OPEN",at,payload)
            db.execute("""INSERT INTO paper_mtm_positions
                (request_id,symbol,side,entry_at,entry_price,lots,
                 pnl_usd_per_price_unit_lot,fee_open_usd)
                VALUES(?,?,?,?,?,?,?,?)""",
                (request_id,symbol,side,at.isoformat(),str(entry),str(lots),
                 str(contract_usd_per_price_unit_lot),str(commission_open_usd)))
            db.execute("UPDATE paper_cash_account SET cash=? WHERE id=1",
                       (str(cash-commission_open_usd),))

    def book_close(self,*,request_id:str,at:datetime,gross_pnl_usd:D,
                   commission_close_usd:D=ZERO)->None:
        _timestamp(at)
        if not isinstance(gross_pnl_usd,D) or not gross_pnl_usd.is_finite():
            raise PaperMtmError("gross close PnL must be finite Decimal")
        _number(commission_close_usd,"close fee")
        payload=dict(request_id=request_id,gross=str(gross_pnl_usd),
                     closing_fee=str(commission_close_usd))
        eid="CLOSE:"+request_id
        with self.qdle._tx() as db:
            previous=db.execute("SELECT kind,instant,payload FROM paper_mtm_event_log WHERE event_id=?",
                                (eid,)).fetchone()
            if previous is not None:
                if previous!=("CLOSE",at.isoformat(),
                             json.dumps(payload,sort_keys=True,separators=(",",":"))):
                    raise PaperMtmError("conflicting PAPER CLOSE")
                return
            self._check_monotone(db,at)
            state=db.execute(
                "SELECT r.state,t.settled_at,t.realized_gross_usd "
                "FROM reservations r JOIN paper_trades t USING(request_id) "
                "WHERE r.request_id=?", (request_id,)).fetchone()
            row=db.execute(
                "SELECT entry_at,settled_at FROM paper_mtm_positions WHERE request_id=?",
                (request_id,)).fetchone()
            if (state is None or state[0]!="PAPER_SETTLED"
                    or state[1]!=at.isoformat()
                    or D(state[2])!=gross_pnl_usd
                    or row is None or row[1] is not None
                    or at<datetime.fromisoformat(row[0])):
                raise PaperMtmError("PAPER CLOSE must reconcile exactly with single QDLE settlement")
            self._event(db,eid,"CLOSE",at,payload)
            db.execute("UPDATE paper_mtm_positions SET settled_at=?,gross_close_usd=? WHERE request_id=?",
                       (at.isoformat(),str(gross_pnl_usd),request_id))
            cash=D(db.execute("SELECT cash FROM paper_cash_account WHERE id=1").fetchone()[0])
            db.execute("UPDATE paper_cash_account SET cash=? WHERE id=1",
                       (str(cash+gross_pnl_usd-commission_close_usd),))

    def mark(self,*,at:datetime,quotes:tuple[HistoricalBidAsk,...],
             max_age_seconds:int=60)->dict:
        _timestamp(at)
        if not isinstance(quotes,tuple):
            raise PaperMtmError("historical quote tuple required")
        with self.qdle._tx() as db:
            old=db.execute("SELECT cash,unrealized,equity,equity_dd_pct,cash_dd_pct,mark_receipts "
                           "FROM paper_mtm_snapshots WHERE at=?",(at.isoformat(),)).fetchone()
            if old is not None:
                raise PaperMtmError("duplicate portfolio mark epoch; reopen requires explicit reconciliation")
            self._check_monotone(db,at)
            active=db.execute(
                "SELECT request_id,symbol,side,entry_at,entry_price,lots,"
                "pnl_usd_per_price_unit_lot FROM paper_mtm_positions WHERE settled_at IS NULL"
            ).fetchall()
            qdle_open=db.execute(
                "SELECT request_id FROM reservations WHERE state='PAPER_FILLED'"
            ).fetchall()
            if {row[0] for row in active}!={row[0] for row in qdle_open}:
                raise PaperMtmError("PAPER filled QDLE book and MTM position set diverged")
            marks={}
            unrealized=ZERO
            for request_id,symbol,side,opened,entry,lots,unit in active:
                if at<datetime.fromisoformat(opened):
                    raise PaperMtmError("cannot mark future entry")
                try:
                    quote=exact_asof_quote(quotes,symbol=symbol,decision_at=at,
                                          max_age_seconds=max_age_seconds)
                except CausalEvidenceError as exc:
                    raise PaperMtmError("MISSING_CAUSAL_MTM_MARK "+request_id+" "+str(exc)) from exc
                executable=quote.bid if side=="BUY" else quote.ask
                move=executable-D(entry) if side=="BUY" else D(entry)-executable
                pnl=move*D(lots)*D(unit)
                unrealized+=pnl
                marks[request_id]=dict(symbol=symbol,quote_at=quote.observed_at.isoformat(),
                    side=side,executable_mark=str(executable),unrealized_usd=str(pnl),
                    evidence_sha256=quote.content_sha256)
            account=db.execute(
                "SELECT cash,equity_peak,cash_peak,equity_max_dd_pct,"
                "cash_max_dd_pct FROM paper_cash_account WHERE id=1"
            ).fetchone()
            cash,peak,peak_cash,max_dd,max_cash_dd=map(D,account)
            equity=cash+unrealized
            peak=max(peak,equity)
            peak_cash=max(peak_cash,cash)
            dd=ZERO if peak<=ZERO else (peak-equity)/peak*D(100)
            cash_dd=ZERO if peak_cash<=ZERO else (peak_cash-cash)/peak_cash*D(100)
            max_dd=max(max_dd,dd)
            max_cash_dd=max(max_cash_dd,cash_dd)
            evidence=json.dumps(marks,sort_keys=True,separators=(",",":"))
            db.execute("INSERT INTO paper_mtm_snapshots VALUES(?,?,?,?,?,?)",
                       (at.isoformat(),str(cash),str(unrealized),str(equity),
                        str(dd),str(cash_dd),evidence))
            db.execute(
                "UPDATE paper_cash_account SET equity_peak=?,cash_peak=?,"
                "equity_max_dd_pct=?,cash_max_dd_pct=?,last_snapshot_at=? WHERE id=1",
                (str(peak),str(peak_cash),str(max_dd),str(max_cash_dd),at.isoformat()))
            self._event(db,"MARK:"+at.isoformat(),"MARK",at,marks)
            return dict(at=at.isoformat(),cash_usd=str(cash),
                unrealized_usd=str(unrealized),equity_usd=str(equity),
                equity_drawdown_pct=str(dd),cash_drawdown_pct=str(cash_dd),
                peak_equity_usd=str(peak),peak_cash_usd=str(peak_cash),
                maximum_equity_drawdown_pct=str(max_dd),
                maximum_cash_drawdown_pct=str(max_cash_dd),mark_count=len(marks),
                broker_fills=0,certified=False)

    def summary(self)->dict:
        with self.qdle._tx() as db:
            a=db.execute("SELECT initial_nav,cash,equity_peak,cash_peak,equity_max_dd_pct,"
                         "cash_max_dd_pct,last_snapshot_at FROM paper_cash_account WHERE id=1"
                        ).fetchone()
            snapshots=db.execute("SELECT COUNT(*) FROM paper_mtm_snapshots").fetchone()[0]
            active=db.execute("SELECT COUNT(*) FROM paper_mtm_positions WHERE settled_at IS NULL").fetchone()[0]
            fills=db.execute("SELECT COUNT(*) FROM paper_mtm_positions").fetchone()[0]
            return dict(initial_nav_usd=a[0],cash_usd=a[1],peak_equity_usd=a[2],
                peak_cash_usd=a[3],maximum_equity_drawdown_pct=a[4],
                maximum_cash_drawdown_pct=a[5],last_snapshot_at=a[6],
                fully_marked_epochs=snapshots,open_positions=active,
                total_paper_openings=fills,broker_fills=0,certified=False,
                qdle_single_account=True)
