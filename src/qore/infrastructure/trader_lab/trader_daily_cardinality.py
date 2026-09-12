"""Daily execution-cardinality authority for research Traders.

Diagnostic observations can be many-to-one with an economic opportunity.  This
module owns the stricter market-day boundary: at most one selected setup, pending
selected order, filled trade and terminal trade for one Trader family, canonical
market and America/New_York local date.

The one-trade ceiling is Human Owner execution policy.  It is deliberately
separate from source methodology and grants no Risk, broker, DEMO, LIVE,
Production or real-capital authority.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, replace
from datetime import date, datetime
from enum import StrEnum
from hashlib import sha256
from zoneinfo import ZoneInfo

from qore.kernel.errors import InfrastructureError

_NY = ZoneInfo("America/New_York")
_SHA40_RE = re.compile(r"[0-9a-f]{40}")
_SHA256_RE = re.compile(r"[0-9a-f]{64}")
_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/+-]*")
_MARKET_RE = re.compile(r"[A-Z0-9][A-Z0-9._-]*")
_FAMILY_RE = re.compile(r"[a-z0-9][a-z0-9._-]*")


class DailyCardinalityError(InfrastructureError):
    """Base error for market-day cardinality invariants."""

    __slots__ = ()


class DailyCardinalityValidationError(DailyCardinalityError):
    """Raised when diagnostic or execution accounting violates the contract."""

    __slots__ = ()


class DailyTradeBudget(StrEnum):
    AVAILABLE = "available"
    CONSUMED = "consumed"


class MarketDayPhase(StrEnum):
    DAY_OPEN = "day-open"
    DATA_VALIDATED = "data-validated"
    WINDOWS_EVALUATED = "windows-evaluated"
    DAILY_SELECTION_FROZEN = "daily-selection-frozen"
    ORDER_PENDING = "order-pending"
    FILLED = "filled"
    TERMINAL = "terminal"
    DAY_CLOSED = "day-closed"


def _canonical_token(value: str, *, field: str) -> str:
    if type(value) is not str or _ID_RE.fullmatch(value) is None:
        raise DailyCardinalityValidationError(f"{field} must be a canonical token")
    return value


def _canonical_market(value: str) -> str:
    if type(value) is not str or _MARKET_RE.fullmatch(value) is None:
        raise DailyCardinalityValidationError("canonical_market must be uppercase canonical")
    return value


def _canonical_family(value: str) -> str:
    if type(value) is not str or _FAMILY_RE.fullmatch(value) is None:
        raise DailyCardinalityValidationError("trader_family must be lowercase canonical")
    return value


def _strict_unique_tokens(values: tuple[str, ...], *, field: str) -> tuple[str, ...]:
    if type(values) is not tuple:
        raise DailyCardinalityValidationError(f"{field} must be an immutable tuple")
    for item in values:
        _canonical_token(item, field=field)
    if len(set(values)) != len(values):
        raise DailyCardinalityValidationError(f"{field} must not contain duplicates")
    return values


@dataclass(frozen=True, slots=True, order=True)
class MarketDayId:
    """Economic authority boundary: Trader family + market + New York date."""

    trader_family: str
    canonical_market: str
    local_date: date

    def __post_init__(self) -> None:
        _canonical_family(self.trader_family)
        _canonical_market(self.canonical_market)
        if type(self.local_date) is not date:
            raise DailyCardinalityValidationError("local_date must be exact date")

    def value(self) -> str:
        return f"{self.trader_family}:{self.canonical_market}:{self.local_date.isoformat()}"


def market_day_id_from_timestamp(
    *,
    trader_family: str,
    canonical_market: str,
    observed_at: datetime,
) -> MarketDayId:
    """Map an aware timestamp to its DST-aware America/New_York market day."""

    if (
        type(observed_at) is not datetime
        or observed_at.tzinfo is None
        or observed_at.utcoffset() is None
    ):
        raise DailyCardinalityValidationError("observed_at must be timezone-aware")
    return MarketDayId(
        trader_family=trader_family,
        canonical_market=canonical_market,
        local_date=observed_at.astimezone(_NY).date(),
    )


def stable_candidate_id(
    *,
    market_day_id: MarketDayId,
    anchor_hour_new_york: int,
    scenario: str,
    side: str,
    signal_at: datetime,
    evidence_fingerprint: str,
) -> str:
    """Derive replay-stable diagnostic identity without implying trade authority."""

    if type(anchor_hour_new_york) is not int or not 0 <= anchor_hour_new_york <= 23:
        raise DailyCardinalityValidationError("anchor hour must be 0..23")
    _canonical_token(scenario, field="scenario")
    _canonical_token(side, field="side")
    if type(signal_at) is not datetime or signal_at.tzinfo is None or signal_at.utcoffset() is None:
        raise DailyCardinalityValidationError("signal_at must be timezone-aware")
    if type(evidence_fingerprint) is not str or _SHA256_RE.fullmatch(evidence_fingerprint) is None:
        raise DailyCardinalityValidationError("evidence_fingerprint must be SHA-256")
    material = {
        "market_day_id": market_day_id.value(),
        "anchor_hour_new_york": anchor_hour_new_york,
        "scenario": scenario,
        "side": side,
        "signal_at": signal_at.isoformat(timespec="microseconds"),
        "evidence_fingerprint": evidence_fingerprint,
    }
    digest = sha256(
        json.dumps(material, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return f"candidate:{digest}"


@dataclass(frozen=True, slots=True)
class MarketDayLedger:
    """Immutable diagnostic-to-economic reconciliation for one market-day."""

    market_day_id: MarketDayId
    eligible_day: bool
    data_complete: bool
    authorized_windows: tuple[int, ...]
    source_rule_version: str
    software_sha: str
    evidence_fingerprint: str
    observed_windows: tuple[int, ...] = ()
    candidate_ids: tuple[str, ...] = ()
    qualified_setup_ids: tuple[str, ...] = ()
    selected_setup_id: str | None = None
    pending_order_id: str | None = None
    fill_id: str | None = None
    terminal_trade_id: str | None = None
    abstain_reason: str | None = None
    containment_reason: str | None = None
    day_closed: bool = False

    def __post_init__(self) -> None:
        if type(self.market_day_id) is not MarketDayId:
            raise DailyCardinalityValidationError("market_day_id must be exact MarketDayId")
        if type(self.eligible_day) is not bool or type(self.data_complete) is not bool:
            raise DailyCardinalityValidationError("eligibility and data_complete must be bool")
        if type(self.authorized_windows) is not tuple or not self.authorized_windows:
            raise DailyCardinalityValidationError("authorized_windows must be non-empty tuple")
        if any(type(hour) is not int or not 0 <= hour <= 23 for hour in self.authorized_windows):
            raise DailyCardinalityValidationError("authorized window hours must be 0..23")
        if len(set(self.authorized_windows)) != len(self.authorized_windows):
            raise DailyCardinalityValidationError("authorized windows must be unique")
        if tuple(sorted(self.authorized_windows)) != self.authorized_windows:
            raise DailyCardinalityValidationError("authorized windows must be sorted")
        _canonical_token(self.source_rule_version, field="source_rule_version")
        if type(self.software_sha) is not str or _SHA40_RE.fullmatch(self.software_sha) is None:
            raise DailyCardinalityValidationError("software_sha must be exact 40-hex Git SHA")
        if (
            type(self.evidence_fingerprint) is not str
            or _SHA256_RE.fullmatch(self.evidence_fingerprint) is None
        ):
            raise DailyCardinalityValidationError("evidence_fingerprint must be SHA-256")
        if type(self.observed_windows) is not tuple:
            raise DailyCardinalityValidationError("observed_windows must be tuple")
        if len(set(self.observed_windows)) != len(self.observed_windows):
            raise DailyCardinalityValidationError("observed windows must be unique")
        if any(hour not in self.authorized_windows for hour in self.observed_windows):
            raise DailyCardinalityValidationError("observed window is outside authorized set")
        if tuple(sorted(self.observed_windows)) != self.observed_windows:
            raise DailyCardinalityValidationError("observed windows must be sorted")
        _strict_unique_tokens(self.candidate_ids, field="candidate_ids")
        _strict_unique_tokens(self.qualified_setup_ids, field="qualified_setup_ids")
        for field_name, value in (
            ("selected_setup_id", self.selected_setup_id),
            ("pending_order_id", self.pending_order_id),
            ("fill_id", self.fill_id),
            ("terminal_trade_id", self.terminal_trade_id),
            ("abstain_reason", self.abstain_reason),
            ("containment_reason", self.containment_reason),
        ):
            if value is not None:
                _canonical_token(value, field=field_name)
        if (
            self.selected_setup_id is not None
            and self.selected_setup_id not in self.qualified_setup_ids
        ):
            raise DailyCardinalityValidationError(
                "selected setup must be qualified on this market-day"
            )
        if self.pending_order_id is not None and self.selected_setup_id is None:
            raise DailyCardinalityValidationError("pending order requires one selected setup")
        if self.fill_id is not None and self.pending_order_id is None:
            raise DailyCardinalityValidationError("fill requires the selected pending order")
        if self.terminal_trade_id is not None and self.fill_id is None:
            raise DailyCardinalityValidationError("terminal trade requires a fill")
        if self.selected_setup_id is not None and (not self.eligible_day or not self.data_complete):
            raise DailyCardinalityValidationError(
                "ineligible or incomplete day cannot select a setup"
            )
        if self.day_closed and self.pending_order_id is not None and self.fill_id is None:
            raise DailyCardinalityValidationError(
                "day cannot close with unresolved selected pending order"
            )

    @property
    def candidate_count(self) -> int:
        return len(self.candidate_ids)

    @property
    def qualified_setup_count(self) -> int:
        return len(self.qualified_setup_ids)

    @property
    def selected_setup_count(self) -> int:
        return int(self.selected_setup_id is not None)

    @property
    def pending_order_count(self) -> int:
        return int(self.pending_order_id is not None)

    @property
    def filled_trade_count(self) -> int:
        return int(self.fill_id is not None)

    @property
    def terminal_trade_count(self) -> int:
        return int(self.terminal_trade_id is not None)

    @property
    def daily_trade_budget(self) -> DailyTradeBudget:
        return (
            DailyTradeBudget.CONSUMED
            if self.selected_setup_id is not None
            else DailyTradeBudget.AVAILABLE
        )

    @property
    def phase(self) -> MarketDayPhase:
        if self.day_closed:
            return MarketDayPhase.DAY_CLOSED
        if self.terminal_trade_id is not None:
            return MarketDayPhase.TERMINAL
        if self.fill_id is not None:
            return MarketDayPhase.FILLED
        if self.pending_order_id is not None:
            return MarketDayPhase.ORDER_PENDING
        if self.selected_setup_id is not None:
            return MarketDayPhase.DAILY_SELECTION_FROZEN
        if self.observed_windows:
            return MarketDayPhase.WINDOWS_EVALUATED
        if self.data_complete:
            return MarketDayPhase.DATA_VALIDATED
        return MarketDayPhase.DAY_OPEN

    def observe_window(self, hour_new_york: int) -> "MarketDayLedger":
        if self.day_closed:
            raise DailyCardinalityValidationError("closed day cannot observe another window")
        if hour_new_york not in self.authorized_windows:
            raise DailyCardinalityValidationError("window is not authorized for this Trader family")
        if hour_new_york in self.observed_windows:
            raise DailyCardinalityValidationError("window evidence already observed")
        return replace(
            self,
            observed_windows=tuple(sorted((*self.observed_windows, hour_new_york))),
        )

    def add_candidate(self, candidate_id: str) -> "MarketDayLedger":
        if self.day_closed:
            raise DailyCardinalityValidationError("closed day cannot accept candidates")
        _canonical_token(candidate_id, field="candidate_id")
        if candidate_id in self.candidate_ids:
            raise DailyCardinalityValidationError("duplicate candidate identity")
        return replace(self, candidate_ids=(*self.candidate_ids, candidate_id))

    def add_qualified_setup(self, setup_id: str) -> "MarketDayLedger":
        if self.day_closed:
            raise DailyCardinalityValidationError("closed day cannot accept setups")
        if not self.eligible_day or not self.data_complete:
            raise DailyCardinalityValidationError(
                "ineligible or incomplete day cannot qualify setup"
            )
        _canonical_token(setup_id, field="setup_id")
        if setup_id in self.qualified_setup_ids:
            raise DailyCardinalityValidationError("duplicate qualified setup identity")
        return replace(self, qualified_setup_ids=(*self.qualified_setup_ids, setup_id))

    def select_setup(self, setup_id: str) -> "MarketDayLedger":
        if self.day_closed:
            raise DailyCardinalityValidationError("closed day cannot select setup")
        if setup_id not in self.qualified_setup_ids:
            raise DailyCardinalityValidationError("selected setup must already be qualified")
        if self.selected_setup_id is not None:
            raise DailyCardinalityValidationError("daily selected-setup budget is already consumed")
        return replace(self, selected_setup_id=setup_id)

    def record_pending_order(self, pending_order_id: str) -> "MarketDayLedger":
        _canonical_token(pending_order_id, field="pending_order_id")
        if self.selected_setup_id is None:
            raise DailyCardinalityValidationError("pending order requires selected setup")
        if self.pending_order_id is not None:
            raise DailyCardinalityValidationError("daily pending-order budget is already consumed")
        return replace(self, pending_order_id=pending_order_id)

    def record_fill(self, fill_id: str) -> "MarketDayLedger":
        _canonical_token(fill_id, field="fill_id")
        if self.pending_order_id is None:
            raise DailyCardinalityValidationError("fill requires pending selected order")
        if self.fill_id is not None:
            raise DailyCardinalityValidationError("daily fill budget is already consumed")
        return replace(self, fill_id=fill_id)

    def record_terminal_trade(self, terminal_trade_id: str) -> "MarketDayLedger":
        _canonical_token(terminal_trade_id, field="terminal_trade_id")
        if self.fill_id is None:
            raise DailyCardinalityValidationError("terminal trade requires fill")
        if self.terminal_trade_id is not None:
            raise DailyCardinalityValidationError("daily terminal-trade budget is already consumed")
        return replace(self, terminal_trade_id=terminal_trade_id)

    def close_day(
        self,
        *,
        abstain_reason: str | None = None,
        containment_reason: str | None = None,
    ) -> "MarketDayLedger":
        if self.day_closed:
            raise DailyCardinalityValidationError("market-day is already closed")
        if abstain_reason is not None:
            _canonical_token(abstain_reason, field="abstain_reason")
        if containment_reason is not None:
            _canonical_token(containment_reason, field="containment_reason")
        if self.pending_order_id is not None and self.fill_id is None:
            raise DailyCardinalityValidationError(
                "unresolved pending order requires containment before close"
            )
        return replace(
            self,
            abstain_reason=abstain_reason,
            containment_reason=containment_reason,
            day_closed=True,
        )

    def payload(self) -> dict[str, object]:
        return {
            "market_day_id": self.market_day_id.value(),
            "market": self.market_day_id.canonical_market,
            "trader_family": self.market_day_id.trader_family,
            "local_date": self.market_day_id.local_date.isoformat(),
            "eligible_day": self.eligible_day,
            "data_complete": self.data_complete,
            "authorized_windows": list(self.authorized_windows),
            "observed_windows": list(self.observed_windows),
            "authorized_window_count": len(self.authorized_windows),
            "evaluated_window_count": len(self.observed_windows),
            "candidate_count": self.candidate_count,
            "candidate_ids": list(self.candidate_ids),
            "qualified_setup_count": self.qualified_setup_count,
            "qualified_setup_ids": list(self.qualified_setup_ids),
            "selected_setup_count": self.selected_setup_count,
            "daily_selection": self.selected_setup_id,
            "daily_trade_budget_before": DailyTradeBudget.AVAILABLE.value,
            "daily_trade_budget_after": self.daily_trade_budget.value,
            "pending_order_count": self.pending_order_count,
            "pending_order_id": self.pending_order_id,
            "fill_count": self.filled_trade_count,
            "fill_id": self.fill_id,
            "terminal_trade_count": self.terminal_trade_count,
            "terminal_trade_id": self.terminal_trade_id,
            "abstain_reason": self.abstain_reason,
            "containment_reason": self.containment_reason,
            "source_rule_version": self.source_rule_version,
            "software_sha": self.software_sha,
            "evidence_fingerprint": self.evidence_fingerprint,
            "phase": self.phase.value,
            "daily_cardinality_violation": False,
        }


@dataclass(frozen=True, slots=True)
class DailyCardinalitySummary:
    eligible_market_days: int
    candidate_count: int
    qualified_setup_count: int
    selected_setup_count: int
    pending_order_count: int
    filled_trade_count: int
    terminal_trade_count: int
    daily_cardinality_violations: int

    def payload(self) -> dict[str, int]:
        return {
            "eligible_market_days": self.eligible_market_days,
            "candidate_count": self.candidate_count,
            "qualified_setup_count": self.qualified_setup_count,
            "selected_setup_count": self.selected_setup_count,
            "pending_order_count": self.pending_order_count,
            "filled_trade_count": self.filled_trade_count,
            "terminal_trade_count": self.terminal_trade_count,
            "daily_cardinality_violations": self.daily_cardinality_violations,
        }


def summarize_market_days(ledgers: tuple[MarketDayLedger, ...]) -> DailyCardinalitySummary:
    """Aggregate ledgers and fail closed if market-day identity is duplicated."""

    if type(ledgers) is not tuple:
        raise DailyCardinalityValidationError("ledgers must be immutable tuple")
    ids = tuple(item.market_day_id for item in ledgers)
    if len(set(ids)) != len(ids):
        raise DailyCardinalityValidationError("duplicate MarketDayId in aggregate")
    eligible = sum(item.eligible_day for item in ledgers)
    summary = DailyCardinalitySummary(
        eligible_market_days=eligible,
        candidate_count=sum(item.candidate_count for item in ledgers),
        qualified_setup_count=sum(item.qualified_setup_count for item in ledgers),
        selected_setup_count=sum(item.selected_setup_count for item in ledgers),
        pending_order_count=sum(item.pending_order_count for item in ledgers),
        filled_trade_count=sum(item.filled_trade_count for item in ledgers),
        terminal_trade_count=sum(item.terminal_trade_count for item in ledgers),
        daily_cardinality_violations=0,
    )
    if summary.selected_setup_count > eligible:
        raise DailyCardinalityValidationError("selected setups exceed eligible market-days")
    if summary.pending_order_count > eligible:
        raise DailyCardinalityValidationError("pending orders exceed eligible market-days")
    if summary.filled_trade_count > eligible:
        raise DailyCardinalityValidationError("fills exceed eligible market-days")
    if summary.terminal_trade_count > eligible:
        raise DailyCardinalityValidationError("terminal trades exceed eligible market-days")
    return summary
