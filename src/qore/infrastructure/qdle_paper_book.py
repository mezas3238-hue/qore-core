"""Isolated research-only QDLE PAPER lifecycle for historical Trader Lab.

This is deliberately NOT broker execution or a substitute for MT5 receipts.
A single QDLE SQLite account is reused across the replay. Synthetic paper fills
and settlements have their own states and event namespace. LIVE acknowledgement,
send and settlement APIs are forbidden for this subclass.
"""
from __future__ import annotations

from datetime import datetime
import hashlib
from decimal import Decimal

from qore.infrastructure.qore_dynamic_lot_engine import (
    QDLE, QDLEAccount, QDLEError, _dt,
)


class PaperQDLE(QDLE):
    """Persistent paper research book; NEVER use as a real MT5 gateway."""

    def __init__(self, path, calculator):
        super().__init__(
            path, calculator, enforce_finance_approval=False,
            strict_live_fee_evidence=False, strict_four_motor_evidence=False,
            strict_provider_floor=False, research_paper_mode=True,
        )
        with self._tx() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS paper_trades (
                request_id TEXT PRIMARY KEY,
                paper_ticket TEXT NOT NULL UNIQUE,
                opened_at TEXT NOT NULL,
                settled_at TEXT,
                realized_gross_usd TEXT
            )""")
            db.execute("""CREATE TABLE IF NOT EXISTS paper_unassessable (
                request_id TEXT PRIMARY KEY,
                observed_at TEXT NOT NULL, reason TEXT NOT NULL
            )""")

    def publish_account(self, snapshot: QDLEAccount) -> None:
        """PAPER holds are counted ONCE by native QDLE, never pre-subtracted.

        Snapshot values are the gross current QORE NAV and broker margin
        *before* this book's PAPER reserves. The research portfolio is mirrored
        in paper_trades, not separately in MT5 position tickets.
        """
        if (snapshot.qore_unreserved_risk_usd != snapshot.qore_trading_capital_usd
                or snapshot.sovereign_free_source_usd != snapshot.qore_trading_capital_usd
                or snapshot.cushion_free_source_usd != 0
                or snapshot.positions or snapshot.covered_fill_tickets):
            raise QDLEError("PAPER account snapshot double-counts QDLE open reservations")
        super().publish_account(snapshot)

    def arm_for_live_send(self, *args, **kwargs):
        raise QDLEError("PAPER ONLY: live submission forbidden")

    def acknowledge_fill(self, *args, **kwargs):
        raise QDLEError("PAPER ONLY: broker fill acknowledgement forbidden")

    def reconcile_fill(self, *args, **kwargs):
        raise QDLEError("PAPER ONLY: broker fill reconciliation forbidden")

    def confirm_rejection(self, *args, **kwargs):
        raise QDLEError("PAPER ONLY: broker refusal acknowledgement forbidden")

    def record_partial_fill(self, *args, **kwargs):
        raise QDLEError("PAPER ONLY: broker partial fill forbidden")

    def confirm_partial_remainder_cancelled(self, *args, **kwargs):
        raise QDLEError("PAPER ONLY: broker cancellation forbidden")

    def record_broker_settlement(self, *args, **kwargs):
        raise QDLEError("PAPER ONLY: broker settlement forbidden")

    def paper_unassessable(self, request_id: str, when: datetime, reason: str) -> None:
        """Account for an unsafe/incomplete geometry WITHOUT fabricating lotage."""
        _dt(when)
        if not request_id or not reason:
            raise QDLEError("PAPER unassessable needs signal identity and reason")
        with self._tx() as db:
            if db.execute("SELECT 1 FROM reservations WHERE request_id=?",
                          (request_id,)).fetchone():
                raise QDLEError("PAPER signal already physically assessed")
            db.execute(
                "INSERT INTO paper_unassessable VALUES(?,?,?)",
                (request_id, when.isoformat(), reason),
            )
            self._audit(db, "PAPER_UNASSESSABLE_NO_PHYSICAL_QUOTE", request_id,
                        {"at": when.isoformat(), "reason": reason})

    def paper_fill(self, request_id: str, opened_at: datetime) -> str:
        """Move reserved quote into paper-filled state; never claim an MT5 deal."""
        _dt(opened_at)
        ticket = "PAPER:" + request_id
        with self._tx() as db:
            if db.execute("SELECT 1 FROM paper_unassessable WHERE request_id=?",
                          (request_id,)).fetchone():
                raise QDLEError("unassessable signal cannot be paper-filled")
            row = db.execute(
                "SELECT state,lots FROM reservations WHERE request_id=?",
                (request_id,),
            ).fetchone()
            if row and row[0] == "PAPER_FILLED":
                prior = db.execute(
                    "SELECT paper_ticket,opened_at FROM paper_trades WHERE request_id=?",
                    (request_id,),
                ).fetchone()
                if prior == (ticket, opened_at.isoformat()):
                    return ticket  # exact-once across retries/restarts
                raise QDLEError("conflicting replay of a PAPER fill")
            if not row or row[0] != "HELD" or Decimal(row[1]) <= 0:
                raise QDLEError("PAPER fill requires a positive existing reservation")
            db.execute(
                "INSERT INTO paper_trades(request_id,paper_ticket,opened_at)"
                " VALUES(?,?,?)", (request_id, ticket, opened_at.isoformat()),
            )
            db.execute(
                "UPDATE reservations SET state='PAPER_FILLED',fill_ticket=?"
                " WHERE request_id=?", (ticket, request_id),
            )
            self._audit(db, "PAPER_FILL_MODELED_NOT_MT5", request_id,
                        {"paper_ticket": ticket, "opened_at": opened_at.isoformat(),
                         "lots": row[1]})
        return ticket

    def paper_cancel(self, request_id: str, when: datetime, reason: str) -> None:
        """Release an unfilled quote only with an explicit simulator reason."""
        _dt(when)
        if not reason:
            raise QDLEError("PAPER cancel reason required")
        with self._tx() as db:
            row = db.execute(
                "SELECT state FROM reservations WHERE request_id=?",
                (request_id,),
            ).fetchone()
            if not row or row[0] != "HELD":
                raise QDLEError("PAPER cancel requires unfilled held quote")
            db.execute("UPDATE reservations SET state='PAPER_CANCELLED'"
                       " WHERE request_id=?", (request_id,))
            self._audit(db, "PAPER_NO_FILL_CANCELLED", request_id,
                        {"at": when.isoformat(), "reason": reason})

    def paper_settle(self, request_id: str, at: datetime,
                     gross_pnl_usd: Decimal) -> None:
        """Append a paper settlement, WITHOUT crediting any real QDLE treasury."""
        _dt(at)
        if not isinstance(gross_pnl_usd, Decimal) or not gross_pnl_usd.is_finite():
            raise QDLEError("finite paper PnL Decimal required")
        with self._tx() as db:
            row = db.execute(
                """SELECT r.state,p.opened_at,p.settled_at,p.realized_gross_usd
                   FROM reservations r JOIN paper_trades p ON p.request_id=r.request_id
                   WHERE r.request_id=?""", (request_id,),
            ).fetchone()
            if row and row[0] == "PAPER_SETTLED":
                if row[2] == at.isoformat() and row[3] == str(gross_pnl_usd):
                    return  # idempotent event; never credit the same cash twice
                raise QDLEError("conflicting PAPER settlement replay")
            if not row or row[0] != "PAPER_FILLED":
                raise QDLEError("PAPER settlement requires one open paper fill")
            if at < datetime.fromisoformat(row[1]):
                raise QDLEError("PAPER settlement predates paper fill")
            db.execute(
                "UPDATE paper_trades SET settled_at=?,realized_gross_usd=?"
                " WHERE request_id=?",
                (at.isoformat(), str(gross_pnl_usd), request_id),
            )
            db.execute("UPDATE reservations SET state='PAPER_SETTLED'"
                       " WHERE request_id=?", (request_id,))
            self._audit(db, "PAPER_SETTLED_NOT_MT5", request_id,
                        {"at": at.isoformat(),
                         "gross_usd": str(gross_pnl_usd)})

    def assert_paper_positions(self, active: dict) -> None:
        """Every paper fill still open is present in portfolio account state."""
        with self._tx() as db:
            rows = db.execute(
                "SELECT request_id,fill_ticket,lots FROM reservations"
                " WHERE state='PAPER_FILLED'"
            ).fetchall()
        expected = {rid: (ticket, Decimal(lots)) for rid, ticket, lots in rows}
        actual = {rid: (trade["paper_ticket"], trade["lots"])
                  for rid, trade in active.items()}
        if expected != actual:
            raise QDLEError("PAPER portfolio / QDLE lifecycle diverged")

    def paper_audit_digest(self) -> dict[str, str | int]:
        """Deterministic event commitment, NOT an authenticated broker signature."""
        sha = hashlib.sha256()
        count = 0
        with self._tx() as db:
            for sequence, event, request_id, receipt in db.execute(
                "SELECT id,event,request_id,receipt FROM audit ORDER BY id"
            ):
                line = (
                    str(sequence) + "\\t" + event + "\\t" +
                    (request_id or "") + "\\t" + receipt + "\\n"
                )
                sha.update(line.encode("utf-8"))
                count += 1
        return {"event_count": count, "audit_sha256": "sha256:" + sha.hexdigest(),
                "signature_verified": False}

    def paper_coverage(self) -> dict[str, int]:
        with self._tx() as db:
            physical = db.execute("SELECT COUNT(*) FROM reservations").fetchone()[0]
            unassessable = db.execute(
                "SELECT COUNT(*) FROM paper_unassessable").fetchone()[0]
            filled = db.execute(
                "SELECT COUNT(*) FROM reservations WHERE state IN"
                " ('PAPER_FILLED','PAPER_SETTLED')").fetchone()[0]
            settled = db.execute(
                "SELECT COUNT(*) FROM reservations WHERE state='PAPER_SETTLED'"
            ).fetchone()[0]
        return {"physical_quotes": physical, "unassessable": unassessable,
                "received_accounted": physical + unassessable,
                "paper_filled": filled, "paper_settled": settled}
