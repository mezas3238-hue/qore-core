"""QORE Dynamic Lot Engine (QDLE), fail-closed, broker-agnostic and trader-neutral.

The sole lot-quantity calculation service; no trading or admission authority.
SQLite BEGIN IMMEDIATE serializes reservations across threads/processes. A
fresh QORE treasury snapshot and broker-native valuation are prerequisites.
This module NEVER sends broker orders and NEVER treats a quote as a fill.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import contextmanager
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Protocol

from qore.infrastructure.cibo_physical_lot_sizing import (
    CiboLotSizingInput, compute_cibo_lot_sizing,
)


class QDLEError(ValueError):
    """Hard safety invariant or stale/unknown broker information."""


def _d(name: str, value: Decimal, zero: bool = False) -> Decimal:
    if not isinstance(value, Decimal) or not value.is_finite():
        raise QDLEError(f"{name}: finite Decimal required")
    if value < 0 or (not zero and value == 0):
        raise QDLEError(f"{name}: invalid nonpositive amount")
    return value


def _dt(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise QDLEError("timezone-aware event timestamp required")
    return value


def _j(value: object) -> str:
    return json.dumps(value, default=lambda x: format(x, "f") if isinstance(x, Decimal)
                      else x.isoformat() if isinstance(x, datetime) else str(x),
                      sort_keys=True, separators=(",", ":"))


@dataclass(frozen=True)
class Position:
    ticket: str
    symbol: str
    side: str
    lots: Decimal

    def __post_init__(self) -> None:
        if not self.ticket or not self.symbol or self.side not in ("BUY", "SELL"):
            raise QDLEError("invalid position identity/side")
        _d("position.lots", self.lots)


@dataclass(frozen=True)
class QDLEAccount:
    account_id: str
    provider: str
    currency: str
    sequence: int
    as_of: datetime
    balance: Decimal
    equity: Decimal
    free_margin: Decimal
    qore_unreserved_risk_usd: Decimal
    sovereign_free_source_usd: Decimal
    cushion_free_source_usd: Decimal
    qore_trading_capital_usd: Decimal
    positions: tuple[Position, ...] = ()
    covered_fill_tickets: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.account_id or self.provider != "FundedNext" or self.currency != "USD":
            raise QDLEError("verified FundedNext USD account binding required")
        if type(self.sequence) is not int or self.sequence <= 0:
            raise QDLEError("account snapshot sequence must increase")
        _dt(self.as_of)
        for name in ("balance", "equity", "free_margin", "qore_unreserved_risk_usd",
                     "sovereign_free_source_usd", "cushion_free_source_usd",
                     "qore_trading_capital_usd"):
            _d(name, getattr(self, name), zero=True)
        if len({p.ticket for p in self.positions}) != len(self.positions):
            raise QDLEError("duplicate MT5 position ticket")
        if len(self.covered_fill_tickets) != len(set(self.covered_fill_tickets)):
            raise QDLEError("duplicate covered ticket")
        if set(self.covered_fill_tickets) - {p.ticket for p in self.positions}:
            raise QDLEError("covered ticket must exist in current positions")


@dataclass(frozen=True)
class QDLESymbol:
    broker_symbol: str
    aliases: tuple[str, ...]
    min_lot: Decimal
    max_lot: Decimal
    lot_step: Decimal
    directional_volume_limit: Decimal
    tick_size: Decimal
    tick_value_loss_usd: Decimal
    contract_size: Decimal
    currency_profit: str
    fee_usd_per_lot: Decimal
    fee_provenance: str
    as_of: datetime
    tradable: bool = True

    def __post_init__(self) -> None:
        if not self.broker_symbol or not self.aliases or not self.currency_profit:
            raise QDLEError("missing real broker symbol, alias or profit currency")
        if not self.fee_provenance or self.fee_provenance == "ASSUMED":
            raise QDLEError("fee schedule must have verifiable provenance")
        _dt(self.as_of)
        for name in ("min_lot", "max_lot", "lot_step", "tick_size",
                     "tick_value_loss_usd", "contract_size"):
            _d(name, getattr(self, name))
        _d("directional_volume_limit", self.directional_volume_limit, zero=True)
        _d("fee_usd_per_lot", self.fee_usd_per_lot, zero=True)
        if self.min_lot > self.max_lot:
            raise QDLEError("broker minimum exceeds maximum")


@dataclass(frozen=True)
class QDLEIntent:
    request_id: str
    trader_id: str
    symbol: str
    side: str
    entry_price: Decimal
    stop_price: Decimal
    requested_risk_usd: Decimal
    sizing_cap_usd: Decimal
    cibo_compound_cap_usd: Decimal
    portfolio_cap_usd: Decimal
    leverage_cap_lots: Decimal
    margin_cap_usd: Decimal
    source_lane: str
    slippage_usd_per_lot: Decimal
    expected_account_sequence: int
    methodology_min_lots: Decimal = Decimal(0)

    def __post_init__(self) -> None:
        if not self.request_id or not self.trader_id or not self.symbol:
            raise QDLEError("trader intent requires request identity and symbol")
        if self.side not in ("BUY", "SELL") or self.source_lane not in (
            "SOVEREIGN_BANK", "PORTFOLIO_CUSHION"
        ):
            raise QDLEError("side or treasury source invalid")
        _d("entry", self.entry_price)
        _d("stop", self.stop_price)
        if ((self.side == "BUY" and self.stop_price >= self.entry_price)
                or (self.side == "SELL" and self.stop_price <= self.entry_price)):
            raise QDLEError("stop must be adverse to the entry")
        for name in ("requested_risk_usd", "sizing_cap_usd",
                     "cibo_compound_cap_usd", "portfolio_cap_usd",
                     "leverage_cap_lots", "margin_cap_usd"):
            _d(name, getattr(self, name), zero=True)
        _d("slippage_usd_per_lot", self.slippage_usd_per_lot, zero=True)
        _d("methodology_min_lots", self.methodology_min_lots, zero=True)
        if self.expected_account_sequence <= 0:
            raise QDLEError("expected account sequence required")


@dataclass(frozen=True)
class BrokerValuation:
    stop_loss_per_lot_usd: Decimal
    margin_per_lot_usd: Decimal
    as_of: datetime
    provenance: str

    def __post_init__(self) -> None:
        _d("stop loss per lot", self.stop_loss_per_lot_usd)
        _d("margin per lot", self.margin_per_lot_usd)
        _dt(self.as_of)
        if not self.provenance:
            raise QDLEError("broker valuation provenance missing")


class BrokerCalculator(Protocol):
    def value(self, instrument: QDLESymbol, intent: QDLEIntent, now: datetime) -> BrokerValuation: ...
    def check_volume(self, instrument: QDLESymbol, intent: QDLEIntent,
                     lots: Decimal) -> None: ...


@dataclass(frozen=True)
class QDLEResult:
    request_id: str
    state: str
    symbol: str
    lots: Decimal
    stop_usd: Decimal
    cost_usd: Decimal
    total_risk_usd: Decimal
    margin_usd: Decimal
    account_sequence: int
    binding_limits: tuple[str, ...]
    note: str = ""


class QDLE:
    """Persistent account-wide reservation authority.

    One SQLite path is one funded account, not one Trader. Reserving quotes uses
    BEGIN IMMEDIATE, preventing two concurrent orders from spending one margin
    or unreserved stop-loss budget. Public interface: publish_account,
    publish_symbol, reserve_for_trader, acknowledge_fill, reconcile_fill,
    confirm_rejection, ledger, health. Snapshots are authoritative AFTER open
    positions are accounted for; unsettled reservations are deducted here.
    """

    def __init__(self, path: str | Path, calculator: BrokerCalculator,
                 max_age_seconds: int = 10,
                 entry_risk_fraction: Decimal = Decimal('0.05'),
                 enforce_finance_approval: bool = False,
                 strict_live_fee_evidence: bool = True,
                 strict_four_motor_evidence: bool = True) -> None:
        _d('entry_risk_fraction', entry_risk_fraction)
        if entry_risk_fraction != Decimal("0.05"):
            raise QDLEError("QDLE sovereign risk fraction is fixed at 5pct of QORE trading capital")
        self.entry_risk_fraction = entry_risk_fraction
        self.enforce_finance_approval = enforce_finance_approval
        # Only explicitly trusted broker round-trip fee schedules permit LIVE.
        # Synthetic tests must opt out; deployed VPS uses the strict default.
        self.strict_live_fee_evidence = strict_live_fee_evidence
        self.strict_four_motor_evidence = strict_four_motor_evidence
        if max_age_seconds <= 0:
            raise QDLEError("invalid maximum snapshot age")
        self.path = str(path)
        self.calculator = calculator
        self.max_age = timedelta(seconds=max_age_seconds)
        self._ready_in_this_process = False
        with self._tx() as db:
            db.execute("CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS symbols (symbol TEXT PRIMARY KEY, payload TEXT NOT NULL)")
            db.execute("""CREATE TABLE IF NOT EXISTS reservations (
                request_id TEXT PRIMARY KEY, payload_sha TEXT NOT NULL, state TEXT NOT NULL,
                source_lane TEXT NOT NULL, symbol TEXT NOT NULL, side TEXT NOT NULL,
                lots TEXT NOT NULL, risk TEXT NOT NULL, margin TEXT NOT NULL,
                snapshot_seq INTEGER NOT NULL, fill_ticket TEXT, result TEXT NOT NULL)""")
            db.execute("""CREATE TABLE IF NOT EXISTS finance_approvals (
                request_id TEXT PRIMARY KEY, payload_sha TEXT NOT NULL,
                account_sequence INTEGER NOT NULL, approval_at TEXT NOT NULL,
                intent_json TEXT)""")
            existing_columns = {x[1] for x in db.execute("PRAGMA table_info(finance_approvals)")}
            if "intent_json" not in existing_columns:
                db.execute("ALTER TABLE finance_approvals ADD COLUMN intent_json TEXT")
            if "module_evidence_json" not in existing_columns:
                db.execute("ALTER TABLE finance_approvals ADD COLUMN module_evidence_json TEXT")
            db.execute("""CREATE TABLE IF NOT EXISTS audit (
                id INTEGER PRIMARY KEY AUTOINCREMENT, event TEXT NOT NULL,
                request_id TEXT, receipt TEXT NOT NULL)""")
            # Multiple trade IDs must never attribute the same authenticated
            # broker close deal as two independent profits.
            db.execute("""CREATE TABLE IF NOT EXISTS broker_settlements (
                deal_receipt TEXT PRIMARY KEY, request_id TEXT NOT NULL UNIQUE,
                broker_ticket TEXT NOT NULL, net_pnl_usd TEXT NOT NULL)""")
            # Recovery of existing persistent QDLE databases: reconstruct the
            # unique deal registry from the append-only audit before accepting
            # a new settlement. Never silently discard conflicting receipts.
            for legacy_id, legacy_request, receipt_json in db.execute(
                """SELECT id,request_id,receipt FROM audit
                   WHERE event='BROKER_REALIZED_SETTLEMENT' ORDER BY id"""
            ).fetchall():
                try:
                    evidence = json.loads(receipt_json)
                    deal = str(evidence["deal_receipt"])
                    ticket = str(evidence["broker_ticket"])
                    pnl = str(evidence["realized_net_pnl_usd"])
                except (KeyError, TypeError, ValueError) as exc:
                    raise QDLEError(
                        f"existing settlement audit {legacy_id} cannot migrate") from exc
                previous = db.execute(
                    "SELECT request_id FROM broker_settlements WHERE deal_receipt=?",
                    (deal,),
                ).fetchone()
                if previous is not None and previous[0] != legacy_request:
                    raise QDLEError("duplicate legacy broker deal: account frozen")
                db.execute(
                    """INSERT OR IGNORE INTO broker_settlements
                       (deal_receipt,request_id,broker_ticket,net_pnl_usd)
                       VALUES (?,?,?,?)""",
                    (deal, legacy_request, ticket, pnl),
                )

    @contextmanager
    def _tx(self):
        with sqlite3.connect(self.path, isolation_level=None, timeout=15) as db:
            db.execute("PRAGMA busy_timeout=15000")
            db.execute("BEGIN IMMEDIATE")
            try:
                yield db
                db.execute("COMMIT")
            except BaseException:
                db.execute("ROLLBACK")
                raise

    @staticmethod
    def _meta(db, key: str) -> dict | None:
        row = db.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
        return json.loads(row[0]) if row else None

    @staticmethod
    def _audit(db, event: str, rid: str | None, receipt: object) -> None:
        db.execute("INSERT INTO audit(event,request_id,receipt) VALUES(?,?,?)",
                   (event, rid, _j(receipt)))

    @staticmethod
    def _account(raw: dict) -> QDLEAccount:
        return QDLEAccount(
            account_id=raw["account_id"], provider=raw["provider"], currency=raw["currency"],
            sequence=raw["sequence"], as_of=datetime.fromisoformat(raw["as_of"]),
            balance=Decimal(raw["balance"]), equity=Decimal(raw["equity"]),
            free_margin=Decimal(raw["free_margin"]),
            qore_unreserved_risk_usd=Decimal(raw["qore_unreserved_risk_usd"]),
            sovereign_free_source_usd=Decimal(raw["sovereign_free_source_usd"]),
            cushion_free_source_usd=Decimal(raw["cushion_free_source_usd"]),
            qore_trading_capital_usd=Decimal(raw["qore_trading_capital_usd"]),
            positions=tuple(Position(
                p["ticket"], p["symbol"], p["side"], Decimal(p["lots"])
            ) for p in raw["positions"]),
            covered_fill_tickets=tuple(raw["covered_fill_tickets"]),
        )

    @staticmethod
    def _symbol(raw: dict) -> QDLESymbol:
        return QDLESymbol(
            broker_symbol=raw["broker_symbol"], aliases=tuple(raw["aliases"]),
            min_lot=Decimal(raw["min_lot"]), max_lot=Decimal(raw["max_lot"]),
            lot_step=Decimal(raw["lot_step"]),
            directional_volume_limit=Decimal(raw["directional_volume_limit"]),
            tick_size=Decimal(raw["tick_size"]),
            tick_value_loss_usd=Decimal(raw["tick_value_loss_usd"]),
            contract_size=Decimal(raw["contract_size"]),
            currency_profit=raw["currency_profit"],
            fee_usd_per_lot=Decimal(raw["fee_usd_per_lot"]),
            fee_provenance=raw["fee_provenance"],
            as_of=datetime.fromisoformat(raw["as_of"]),
            tradable=raw["tradable"],
        )

    @staticmethod
    def _result(raw: dict) -> QDLEResult:
        return QDLEResult(
            request_id=raw["request_id"], state=raw["state"],
            symbol=raw["symbol"], lots=Decimal(raw["lots"]),
            stop_usd=Decimal(raw["stop_usd"]), cost_usd=Decimal(raw["cost_usd"]),
            total_risk_usd=Decimal(raw["total_risk_usd"]),
            margin_usd=Decimal(raw["margin_usd"]),
            account_sequence=raw["account_sequence"],
            binding_limits=tuple(raw["binding_limits"]), note=raw["note"],
        )

    def publish_account(self, snapshot: QDLEAccount) -> None:
        if not isinstance(snapshot, QDLEAccount):
            raise QDLEError("QDLEAccount required")
        if snapshot.qore_trading_capital_usd > snapshot.equity:
            raise QDLEError("QORE economic capital exceeds broker equity")
        if (snapshot.sovereign_free_source_usd + snapshot.cushion_free_source_usd
                > snapshot.qore_trading_capital_usd):
            raise QDLEError("QORE economic sources exceed proprietary trading capital")
        if snapshot.qore_unreserved_risk_usd > snapshot.qore_trading_capital_usd:
            raise QDLEError("QORE risk headroom exceeds proprietary trading capital")
        with self._tx() as db:
            previous = self._meta(db, "account")
            if previous and previous["account_id"] != snapshot.account_id:
                raise QDLEError("different account: independent database required")
            if previous and snapshot.sequence <= previous["sequence"]:
                raise QDLEError("out-of-order account event")
            db.execute("INSERT OR REPLACE INTO meta VALUES('account',?)",
                       (_j(asdict(snapshot)),))
            self._audit(db, "ACCOUNT_SNAPSHOT", None,
                        {"sequence": snapshot.sequence, "broker_equity": snapshot.equity,
                         "qore_trading_capital_usd": snapshot.qore_trading_capital_usd,
                         "positions": len(snapshot.positions)})
        self._ready_in_this_process = True

    def publish_symbol(self, spec: QDLESymbol) -> None:
        if not isinstance(spec, QDLESymbol):
            raise QDLEError("QDLESymbol required")
        with self._tx() as db:
            previous = db.execute("SELECT payload FROM symbols WHERE symbol=?",
                                  (spec.broker_symbol,)).fetchone()
            if previous and spec.as_of <= datetime.fromisoformat(json.loads(previous[0])["as_of"]):
                raise QDLEError("out-of-order symbol specification")
            db.execute("INSERT OR REPLACE INTO symbols VALUES(?,?)",
                       (spec.broker_symbol, _j(asdict(spec))))
            self._audit(db, "SYMBOL_SPEC", None,
                        {"symbol": spec.broker_symbol, "as_of": spec.as_of})

    @staticmethod
    def _validate_motor_receipts(intent: QDLEIntent, proof: dict | None,
                                 approved_at: datetime) -> None:
        """Enforce four separately attributable event receipts before LIVE.

        Only the treasury actor may forward these. Receipt presence does NOT
        replace verifying each source producer's signature upstream.
        """
        expected = {
            "SIZING": {"approved_risk_usd": intent.sizing_cap_usd},
            "CIBO_COMPOUND": {"approved_risk_usd": intent.cibo_compound_cap_usd},
            "ADAPTIVE_LEVERAGE": {
                "approved_max_lots": intent.leverage_cap_lots,
                "approved_margin_usd": intent.margin_cap_usd,
            },
            "PORTFOLIO_COMPOUND": {
                "approved_source_funds_usd": intent.portfolio_cap_usd,
            },
        }
        if not isinstance(proof, dict) or set(proof) != set(expected):
            raise QDLEError("missing independent four-motor economic receipts")
        hashes = set()
        for name, fields in expected.items():
            row = proof[name]
            if not isinstance(row, dict):
                raise QDLEError(f"{name} evidence must be an object")
            if (row.get("request_id") != intent.request_id
                    or row.get("account_sequence") != intent.expected_account_sequence):
                raise QDLEError(f"{name} receipt is bound to a different signal/epoch")
            receipt = row.get("source_event_sha256")
            if (not isinstance(receipt, str) or not receipt.startswith("sha256:")
                    or len(receipt) != 71
                    or any(c not in "0123456789abcdef" for c in receipt[7:])):
                raise QDLEError(f"{name} has no source-specific SHA256 evidence")
            if receipt in hashes:
                raise QDLEError("four motors cannot reuse a single decision receipt")
            hashes.add(receipt)
            try:
                event_time = datetime.fromisoformat(row["observed_at"])
                if not timedelta(0) <= _dt(approved_at) - _dt(event_time) <= timedelta(seconds=10):
                    raise QDLEError(f"{name} economic approval stale or future")
                if any(Decimal(str(row[k])) != value for k, value in fields.items()):
                    raise QDLEError(f"{name} signed economic cap differs from QDLE intent")
            except (KeyError, TypeError, ValueError) as exc:
                raise QDLEError(f"{name} economic proof incomplete") from exc

    def publish_finance_approval(self, intent: QDLEIntent,
                                 approved_at: datetime,
                                 module_evidence: dict | None = None) -> None:
        """Treasury-only: approve immutable four-engine economics and Trader geometry.

        Authenticate the caller at the local service boundary; approvals cannot
        be submitted by Traders. A second, conflicting approval ID fails closed.
        Every approval binds to the exact causal account snapshot sequence.
        """
        if not isinstance(intent, QDLEIntent):
            raise QDLEError("QDLEIntent required for sovereign finance approval")
        approved_at = _dt(approved_at)
        if self.enforce_finance_approval and self.strict_four_motor_evidence:
            self._validate_motor_receipts(intent, module_evidence, approved_at)
        fingerprint = hashlib.sha256(_j(asdict(intent)).encode()).hexdigest()
        with self._tx() as db:
            current = self._meta(db, "account")
            if current is None or current["sequence"] != intent.expected_account_sequence:
                raise QDLEError("approval requires matching current account snapshot")
            self._fresh(datetime.fromisoformat(current["as_of"]), approved_at)
            existing = db.execute(
                "SELECT payload_sha,module_evidence_json FROM finance_approvals WHERE request_id=?",
                (intent.request_id,)).fetchone()
            if existing and existing[0] != fingerprint:
                raise QDLEError("cannot change economic approval for a signal ID")
            signed_modules = _j(module_evidence) if module_evidence is not None else None
            if existing and existing[1] != signed_modules:
                raise QDLEError("cannot alter the four motor receipts for a signal ID")
            db.execute("""INSERT OR IGNORE INTO finance_approvals
                        (request_id,payload_sha,account_sequence,approval_at,
                         intent_json,module_evidence_json)
                        VALUES(?,?,?,?,?,?)""",
                       (intent.request_id, fingerprint,
                        intent.expected_account_sequence, approved_at.isoformat(),
                        _j(asdict(intent)), signed_modules))
            db.execute("""UPDATE finance_approvals SET intent_json=?
                          WHERE request_id=? AND intent_json IS NULL""",
                       (_j(asdict(intent)), intent.request_id))
            self._audit(db, "QORE_FOUR_ENGINE_FINANCE_APPROVED",
                        intent.request_id, {
                            "account_sequence": intent.expected_account_sequence,
                            "sha256": fingerprint,
                            "requested_risk_usd": intent.requested_risk_usd,
                            "sizing_risk_usd": intent.sizing_cap_usd,
                            "cibo_compound_risk_usd": intent.cibo_compound_cap_usd,
                            "portfolio_source_budget_usd": intent.portfolio_cap_usd,
                            "adaptive_leverage_lots": intent.leverage_cap_lots,
                            "adaptive_leverage_margin_usd": intent.margin_cap_usd,
                        })

    def _fresh(self, when: datetime, now: datetime) -> None:
        age = _dt(now) - _dt(when)
        if age < timedelta(0) or age > self.max_age:
            raise QDLEError("stale or future-dated MT5/QORE snapshot")

    def reserve_for_trader(self, intent: QDLEIntent,
                           now: datetime | None = None) -> QDLEResult:
        if not isinstance(intent, QDLEIntent):
            raise QDLEError("QDLEIntent required")
        now = _dt(now or datetime.now(timezone.utc))
        if not self._ready_in_this_process:
            raise QDLEError("not synchronized since process start; publish fresh account")
        fingerprint = hashlib.sha256(_j(asdict(intent)).encode()).hexdigest()
        with self._tx() as db:
            prior = db.execute("SELECT payload_sha,result FROM reservations WHERE request_id=?",
                               (intent.request_id,)).fetchone()
            if prior:
                if prior[0] != fingerprint:
                    raise QDLEError("idempotency key reused for a different entry")
                return self._result(json.loads(prior[1]))
            if self.enforce_finance_approval:
                approval = db.execute(
                    """SELECT payload_sha,account_sequence,approval_at
                       FROM finance_approvals WHERE request_id=?""",
                    (intent.request_id,)).fetchone()
                if approval is None or approval[0] != fingerprint:
                    raise QDLEError("no QORE sovereign four-engine financial approval")
                if approval[1] != intent.expected_account_sequence:
                    raise QDLEError("economic approval account epoch mismatch")
                self._fresh(datetime.fromisoformat(approval[2]), now)
            raw = self._meta(db, "account")
            if raw is None:
                raise QDLEError("no account snapshot")
            acc = self._account(raw)
            self._fresh(acc.as_of, now)
            if acc.sequence != intent.expected_account_sequence:
                raise QDLEError("stale economic coordination epoch")
            rows = db.execute("SELECT payload FROM symbols").fetchall()
            specs = [self._symbol(json.loads(row[0])) for row in rows]
            matching = [s for s in specs if
                        intent.symbol in s.aliases or intent.symbol == s.broker_symbol]
            if len(matching) != 1:
                raise QDLEError("symbol alias unresolved or ambiguous")
            spec = matching[0]
            self._fresh(spec.as_of, now)
            if not spec.tradable:
                raise QDLEError("MT5 symbol is not tradeable")
            valuation = self.calculator.value(spec, intent, now)
            if not isinstance(valuation, BrokerValuation):
                raise QDLEError("broker valuation required")
            self._fresh(valuation.as_of, now)
            held = db.execute("""SELECT source_lane,symbol,side,lots,risk,margin
                                FROM reservations WHERE state IN ('HELD','SENDING','FILL_UNRECONCILED')""").fetchall()
            total_held_risk = sum((Decimal(x[4]) for x in held), Decimal(0))
            total_held_margin = sum((Decimal(x[5]) for x in held), Decimal(0))
            source_held = sum((Decimal(x[4]) for x in held
                               if x[0] == intent.source_lane), Decimal(0))
            volume_held = sum((Decimal(x[3]) for x in held
                               if x[1] == spec.broker_symbol and x[2] == intent.side),
                              Decimal(0))
            open_lots = sum((p.lots for p in acc.positions
                             if p.symbol == spec.broker_symbol and p.side == intent.side),
                            Decimal(0))
            volume_cap = (spec.max_lot if spec.directional_volume_limit == 0
                          else max(Decimal(0), spec.directional_volume_limit
                                   - open_lots - volume_held))
            source_total = (acc.sovereign_free_source_usd
                            if intent.source_lane == "SOVEREIGN_BANK"
                            else acc.cushion_free_source_usd)
            free_source = max(Decimal(0), source_total - source_held)
            remaining_risk = max(Decimal(0), acc.qore_unreserved_risk_usd
                                 - total_held_risk)
            remaining_margin = max(Decimal(0), acc.free_margin - total_held_margin)
            causal_entry_budget = min(intent.requested_risk_usd,
                                      acc.qore_trading_capital_usd * self.entry_risk_fraction)
            zero_ceiling = (min(causal_entry_budget, intent.sizing_cap_usd,
                                intent.cibo_compound_cap_usd, intent.portfolio_cap_usd,
                                remaining_risk, free_source,
                                remaining_margin, intent.margin_cap_usd,
                                intent.leverage_cap_lots, volume_cap) <= 0)
            if zero_ceiling:
                result = QDLEResult(intent.request_id, "UNFUNDABLE", spec.broker_symbol,
                                    Decimal(0), Decimal(0), Decimal(0), Decimal(0),
                                    Decimal(0), acc.sequence, ("ZERO_FINANCE_CAPACITY",),
                                    "No physical broker-minimum allocation")
            else:
                result = self._reserve_positive(db, spec, intent, acc,
                    valuation, free_source, remaining_risk, remaining_margin, volume_cap)
            db.execute("""INSERT INTO reservations
                (request_id,payload_sha,state,source_lane,symbol,side,lots,risk,margin,
                 snapshot_seq,fill_ticket,result)
                 VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                       (intent.request_id, fingerprint,
                        "HELD" if result.lots > 0 else "BLOCKED",
                        intent.source_lane, spec.broker_symbol, intent.side,
                        str(result.lots), str(result.total_risk_usd),
                        str(result.margin_usd), acc.sequence, None,
                        _j(asdict(result))))
            self._audit(db, "VOLUME_RESERVED" if result.lots else "UNFUNDABLE",
                        intent.request_id, asdict(result))
            return result

    def _reserve_positive(self, db, spec: QDLESymbol, intent: QDLEIntent,
                          acc: QDLEAccount, valuation: BrokerValuation,
                          free_source: Decimal, remaining_risk: Decimal,
                          remaining_margin: Decimal, volume_cap: Decimal) -> QDLEResult:
            input_spec = CiboLotSizingInput(
                requested_loss_budget_usd=min(intent.requested_risk_usd,
                    acc.qore_trading_capital_usd * self.entry_risk_fraction),
                stop_risk_usd_per_lot=valuation.stop_loss_per_lot_usd,
                provider_cost_usd_per_lot=(spec.fee_usd_per_lot
                                            + intent.slippage_usd_per_lot),
                margin_usd_per_lot=valuation.margin_per_lot_usd,
                broker_min_lot=max(spec.min_lot, intent.methodology_min_lots),
                broker_max_lot=spec.max_lot,
                broker_lot_step=spec.lot_step,
                sizing_risk_cap_usd=intent.sizing_cap_usd,
                cibo_compound_risk_cap_usd=intent.cibo_compound_cap_usd,
                sovereign_unreserved_cash_usd=(min(free_source, intent.portfolio_cap_usd)
                        if intent.source_lane == "SOVEREIGN_BANK" else Decimal(0)),
                portfolio_unreserved_cash_usd=(min(free_source, intent.portfolio_cap_usd)
                        if intent.source_lane == "PORTFOLIO_CUSHION" else Decimal(0)),
                source_lane=intent.source_lane,
                leverage_available_margin_usd=min(
                    remaining_margin, intent.margin_cap_usd),
                sovereign_unreserved_risk_usd=remaining_risk,
                leverage_max_lots=min(intent.leverage_cap_lots, volume_cap),
            )
            # Every positive quote must pass native broker order_check (or
            # explicit deterministic replay preflight), before reserving cash.
            computed = compute_cibo_lot_sizing(input_spec)
            if computed.lots > 0:
                self.calculator.check_volume(spec, intent, computed.lots)
            result = QDLEResult(
                    intent.request_id,
                    "RESERVED_FOR_TRADER" if computed.lots > 0 else "UNFUNDABLE",
                    spec.broker_symbol, computed.lots, computed.stop_risk_usd,
                    computed.provider_cost_usd, computed.all_in_loss_if_stopped_usd,
                    computed.margin_required_usd, acc.sequence,
                    computed.binding_constraints,
                    "5pct dynamic QORE-owned trading capital; broker margin separate; not an MT5 fill",
                )
            return result

    def arm_for_live_send(
        self, *, request_id: str, provider_symbol: str,
        side: str, lots: Decimal, executable_entry: Decimal,
        stop_price: Decimal, now: datetime,
    ) -> None:
        """Atomic one-shot LIVE gate immediately before broker order_send.

        This ONLY grants a one-shot reservation claim, not permission to enter
        or any broker proof of a fill. The LIVE gateway separately verifies
        canonical RiskAuthorization, provider rules, fresh ticks, and order_check.
        A crash during SENDING remains RESERVED/UNKNOWN until broker reconciliation.
        """
        _dt(now)
        for label, item in (("lots", lots), ("entry", executable_entry),
                            ("stop", stop_price)):
            _d(label, item)
        if not self.enforce_finance_approval or not self._ready_in_this_process:
            raise QDLEError("LIVE gate needs treasury approved fresh account service")
        with self._tx() as db:
            reservation = db.execute(
                """SELECT state,symbol,side,lots,risk,margin,snapshot_seq
                   FROM reservations WHERE request_id=?""",
                (request_id,)).fetchone()
            if reservation is None or reservation[0] != "HELD":
                raise QDLEError("LIVE requires a unique HELD, unconsumed QDLE reservation")
            if (reservation[1] != provider_symbol or reservation[2] != side
                    or Decimal(reservation[3]) != lots):
                raise QDLEError("Trader LIVE lotage, symbol or direction differs from QDLE")
            approval = db.execute(
                """SELECT account_sequence, approval_at, intent_json
                   FROM finance_approvals WHERE request_id=?""",
                (request_id,)).fetchone()
            if approval is None or approval[2] is None:
                raise QDLEError("no immutable QORE finance-approved intent")
            raw = json.loads(approval[2])
            numeric_fields = (
                "entry_price", "stop_price", "requested_risk_usd",
                "sizing_cap_usd", "cibo_compound_cap_usd",
                "portfolio_cap_usd", "leverage_cap_lots", "margin_cap_usd",
                "slippage_usd_per_lot", "methodology_min_lots",
            )
            for name in numeric_fields:
                raw[name] = Decimal(str(raw[name]))
            approved_intent = QDLEIntent(**raw)
            if (approved_intent.request_id != request_id
                    or approved_intent.side != side
                    or approved_intent.stop_price != stop_price
                    or approved_intent.symbol not in (provider_symbol,)):
                # Canonical live payload must use exactly the same broker
                # symbol as the original Treasury-approved intent.
                raise QDLEError("LIVE geometry differs from QORE-approved entry")
            account_raw = self._meta(db, "account")
            if account_raw is None:
                raise QDLEError("LIVE account snapshot absent")
            account = self._account(account_raw)
            self._fresh(account.as_of, now)
            self._fresh(datetime.fromisoformat(approval[1]), now)
            if (account.sequence != reservation[6]
                    or account.sequence != approval[0]):
                raise QDLEError("LIVE QORE funds changed: new approval and reservation needed")
            broker_row = db.execute(
                "SELECT payload FROM symbols WHERE symbol=?", (provider_symbol,)
            ).fetchone()
            if broker_row is None:
                raise QDLEError("LIVE missing real broker instrument")
            spec = self._symbol(json.loads(broker_row[0]))
            self._fresh(spec.as_of, now)
            if not spec.tradable:
                raise QDLEError("LIVE symbol cannot be traded")
            if (self.strict_live_fee_evidence
                    and not spec.fee_provenance.startswith("BROKER_ROUND_TRIP_VERIFIED:")):
                raise QDLEError(
                    "LIVE commission schedule does not prove open AND close fees")
            current = replace(approved_intent, entry_price=executable_entry)
            quote = self.calculator.value(spec, current, now)
            if not isinstance(quote, BrokerValuation):
                raise QDLEError("LIVE broker-native valuation missing")
            self._fresh(quote.as_of, now)
            actual_loss = (quote.stop_loss_per_lot_usd + spec.fee_usd_per_lot
                           + current.slippage_usd_per_lot) * lots
            actual_margin = quote.margin_per_lot_usd * lots
            if (actual_loss > Decimal(reservation[4])
                    or actual_margin > Decimal(reservation[5])
                    or actual_loss > account.qore_trading_capital_usd * self.entry_risk_fraction):
                raise QDLEError("LIVE price/margin drift exceeds atomically funded reservation")
            self.calculator.check_volume(spec, current, lots)
            db.execute("""UPDATE reservations SET state='SENDING'
                          WHERE request_id=? AND state='HELD'""",
                       (request_id,))
            self._audit(db, "QDLE_LIVE_SEND_ARMED_ONCE", request_id, {
                "symbol": provider_symbol, "side": side,
                "broker_lots": format(lots, "f"),
                "revalidated_stop_usd": format(actual_loss, "f"),
                "revalidated_margin_usd": format(actual_margin, "f"),
                "account_sequence": account.sequence,
                "live_send_is_not_fill": True,
            })

    def acknowledge_fill(self, request_id: str, ticket: str) -> None:
        """Broker-confirmed fill. Retain its entire reserve until QORE+MT5 reconcile."""
        if not ticket:
            raise QDLEError("broker fill ticket required")
        with self._tx() as db:
            row = db.execute("SELECT state,fill_ticket FROM reservations WHERE request_id=?",
                             (request_id,)).fetchone()
            if not row or row[0] not in ("HELD", "SENDING", "FILL_UNRECONCILED"):
                raise QDLEError("unknown or non-reserved fill")
            if self.enforce_finance_approval and row[0] == "HELD":
                raise QDLEError("broker fill before sovereign LIVE presend arm is forbidden")
            if row[1] and row[1] != ticket:
                raise QDLEError("contradictory broker fill ticket")
            other = db.execute("SELECT request_id FROM reservations WHERE fill_ticket=? AND request_id!=?",
                               (ticket, request_id)).fetchone()
            if other:
                raise QDLEError("broker ticket attributed to more than one entry")
            db.execute("""UPDATE reservations SET state='FILL_UNRECONCILED',
                          fill_ticket=? WHERE request_id=?""", (ticket, request_id))
            self._audit(db, "BROKER_FILL_UNRECONCILED", request_id, {"ticket": ticket})

    def reconcile_fill(self, request_id: str) -> None:
        """Release local hold ONLY after newer broker+QORE covered-position snapshot."""
        with self._tx() as db:
            row = db.execute("""SELECT state,fill_ticket,snapshot_seq,symbol,side,lots
                                FROM reservations WHERE request_id=?""", (request_id,)).fetchone()
            if not row or row[0] != "FILL_UNRECONCILED" or not row[1]:
                raise QDLEError("fill not awaiting reconciliation")
            raw = self._meta(db, "account")
            if not raw or raw["sequence"] <= row[2]:
                raise QDLEError("newer account snapshot must reflect fill")
            acc = self._account(raw)
            matches = [p for p in acc.positions if p.ticket == row[1]
                       and p.symbol == row[3] and p.side == row[4]
                       and p.lots == Decimal(row[5])]
            if len(matches) != 1 or row[1] not in acc.covered_fill_tickets:
                raise QDLEError("broker position or QORE funded-source coverage absent")
            db.execute("UPDATE reservations SET state='ABSORBED' WHERE request_id=?",
                       (request_id,))
            self._audit(db, "FILLED_AND_COVERED", request_id,
                        {"ticket": row[1], "executed_lots": str(matches[0].lots),
                         "source_covered": True, "account_sequence": acc.sequence})

    def confirm_rejection(self, request_id: str, broker_rejection_ref: str) -> None:
        """Only call with verified broker refusal/no-fill. Unknown outcomes stay held."""
        if not broker_rejection_ref:
            raise QDLEError("verified broker no-fill receipt required")
        with self._tx() as db:
            row = db.execute("SELECT state FROM reservations WHERE request_id=?",
                             (request_id,)).fetchone()
            if not row or row[0] not in ("HELD", "SENDING"):
                raise QDLEError("only broker-confirmed no-fill requests may be released")
            db.execute("UPDATE reservations SET state='REJECTED_NO_FILL' WHERE request_id=?",
                       (request_id,))
            self._audit(db, "BROKER_REJECTED_NO_FILL", request_id,
                        {"broker_ref": broker_rejection_ref})

    def record_broker_settlement(
        self, request_id: str, broker_ticket: str, deal_receipt: str,
        realized_net_pnl_usd: Decimal,
    ) -> None:
        """Post-execution loss/profit telemetry only; NO broker position mutation.

        The broker provider actor must verify final historical deal receipt.
        Requires a newer account snapshot without the position, so terminal
        cash, equity and sovereign risk reflect the closed trade already.
        """
        _d("realized PnL magnitude", abs(realized_net_pnl_usd), zero=True)
        if not broker_ticket or not deal_receipt:
            raise QDLEError("verified broker close/deal receipt required")
        with self._tx() as db:
            row = db.execute("""SELECT state,fill_ticket,snapshot_seq, result
                                FROM reservations WHERE request_id=?""",
                             (request_id,)).fetchone()
            if not row or row[0] != "ABSORBED" or row[1] != broker_ticket:
                raise QDLEError("only broker-confirmed, funded fills may be settled")
            raw = self._meta(db, "account")
            if not raw or raw["sequence"] <= row[2]:
                raise QDLEError("settlement requires newer account snapshot")
            acc = self._account(raw)
            if any(p.ticket == broker_ticket for p in acc.positions):
                raise QDLEError("broker still reports position open")
            receipt = self._result(json.loads(row[3]))
            already_recorded = db.execute(
                "SELECT request_id FROM broker_settlements WHERE deal_receipt=?",
                (deal_receipt,)).fetchone()
            if already_recorded is not None:
                raise QDLEError("broker settlement deal receipt reused by another trade")
            db.execute(
                """INSERT INTO broker_settlements
                   (deal_receipt,request_id,broker_ticket,net_pnl_usd)
                   VALUES (?,?,?,?)""",
                (deal_receipt, request_id, broker_ticket, format(realized_net_pnl_usd, "f")),
            )
            db.execute("UPDATE reservations SET state='SETTLED' WHERE request_id=?",
                       (request_id,))
            self._audit(db, "BROKER_REALIZED_SETTLEMENT", request_id, {
                "broker_ticket": broker_ticket, "deal_receipt": deal_receipt,
                "realized_net_pnl_usd": format(realized_net_pnl_usd, "f"),
                "executed_lots": format(receipt.lots, "f"),
                "planned_stop_usd": format(receipt.total_risk_usd, "f"),
                "margin_reserved_usd": format(receipt.margin_usd, "f"),
                "realized_pnl_to_reserved_margin_ratio": (
                    format(realized_net_pnl_usd /
                           max(Decimal("1e-50"), receipt.margin_usd), "f")
                ),
                "account_sequence": acc.sequence,
            })

    def ledger(self, limit: int = 100) -> list[dict]:
        if not 0 < limit <= 1000:
            raise QDLEError("invalid audit limit")
        with sqlite3.connect(self.path) as db:
            rows = db.execute("""SELECT id,event,request_id,receipt
                                 FROM audit ORDER BY id DESC LIMIT ?""", (limit,)).fetchall()
        return [{"sequence": i, "event": e, "request_id": r,
                 "receipt": json.loads(receipt)} for i, e, r, receipt in rows]

    def health(self, now: datetime | None = None) -> dict:
        now = _dt(now or datetime.now(timezone.utc))
        with sqlite3.connect(self.path) as db:
            raw = self._meta(db, "account")
            pending = db.execute("""SELECT COUNT(*) FROM reservations
                                    WHERE state IN ('HELD','SENDING','FILL_UNRECONCILED')""").fetchone()[0]
            symbol_rows = db.execute("SELECT payload FROM symbols").fetchall()
        stale = (raw is None or (now - datetime.fromisoformat(raw["as_of"])) < timedelta(0)
                 or (now - datetime.fromisoformat(raw["as_of"])) > self.max_age)
        provider_stale = (not symbol_rows or any(
            not timedelta(0) <= now - datetime.fromisoformat(
                json.loads(row[0])["as_of"]) <= self.max_age for row in symbol_rows
        ))
        return {"ready": self._ready_in_this_process and not stale and not provider_stale,
                "account_sequence": raw["sequence"] if raw else None,
                "pending_or_unreconciled_reservations": pending,
                "mode": "CALCULATE_RESERVE_ONLY_NO_ORDER_SEND"}
