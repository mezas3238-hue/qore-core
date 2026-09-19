"""Daily candidate-to-trade cardinality authority for research Traders.

The one-trade-per-market/New-York-date ceiling is Human Owner execution policy,
not a TTrades source rule. This module never chooses which qualified setup wins
and grants no broker, Risk, DEMO, LIVE or real-capital authority.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, replace
from datetime import UTC, date, datetime
from enum import StrEnum
from hashlib import sha256
from zoneinfo import ZoneInfo

from qore.kernel.errors import InfrastructureError

_NY = ZoneInfo("America/New_York")
_TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/+-]*")
_MARKET = re.compile(r"[A-Z0-9][A-Z0-9._-]*")
_FAMILY = re.compile(r"[a-z0-9][a-z0-9._-]*")
_SHA40 = re.compile(r"[0-9a-f]{40}")
_SHA256 = re.compile(r"[0-9a-f]{64}")


class DailyCardinalityError(InfrastructureError):
    __slots__ = ()


class DailyCardinalityValidationError(DailyCardinalityError):
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
    ORDER_UNFILLED = "order-unfilled"
    FILLED = "filled"
    TERMINAL = "terminal"
    DAY_CLOSED = "day-closed"


def _token(value: str, field: str) -> str:
    if type(value) is not str or _TOKEN.fullmatch(value) is None:
        raise DailyCardinalityValidationError(f"invalid {field}")
    return value


def _unique(values: tuple[str, ...], field: str) -> None:
    if type(values) is not tuple:
        raise DailyCardinalityValidationError(f"{field} must be tuple")
    for value in values:
        _token(value, field)
    if len(values) != len(set(values)):
        raise DailyCardinalityValidationError(f"duplicate {field}")


@dataclass(frozen=True, slots=True, order=True)
class MarketDayId:
    trader_family: str
    canonical_market: str
    local_date: date

    def __post_init__(self) -> None:
        if type(self.trader_family) is not str or _FAMILY.fullmatch(self.trader_family) is None:
            raise DailyCardinalityValidationError("invalid trader_family")
        if (
            type(self.canonical_market) is not str
            or _MARKET.fullmatch(self.canonical_market) is None
        ):
            raise DailyCardinalityValidationError("invalid canonical_market")
        if type(self.local_date) is not date:
            raise DailyCardinalityValidationError("invalid local_date")

    def value(self) -> str:
        return f"{self.trader_family}:{self.canonical_market}:{self.local_date.isoformat()}"


def market_day_id_from_timestamp(
    *, trader_family: str, canonical_market: str, observed_at: datetime
) -> MarketDayId:
    if (
        type(observed_at) is not datetime
        or observed_at.tzinfo is None
        or observed_at.utcoffset() is None
    ):
        raise DailyCardinalityValidationError("observed_at must be timezone-aware")
    return MarketDayId(
        trader_family,
        canonical_market,
        observed_at.astimezone(_NY).date(),
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
    if type(anchor_hour_new_york) is not int or not 0 <= anchor_hour_new_york <= 23:
        raise DailyCardinalityValidationError("invalid anchor hour")
    _token(scenario, "scenario")
    _token(side, "side")
    if signal_at.tzinfo is None or signal_at.utcoffset() is None:
        raise DailyCardinalityValidationError("signal_at must be timezone-aware")
    if type(evidence_fingerprint) is not str or _SHA256.fullmatch(evidence_fingerprint) is None:
        raise DailyCardinalityValidationError("invalid evidence fingerprint")
    material = {
        "day": market_day_id.value(),
        "anchor": anchor_hour_new_york,
        "scenario": scenario,
        "side": side,
        "signal_at": signal_at.astimezone(UTC).isoformat(timespec="microseconds"),
        "evidence": evidence_fingerprint,
    }
    digest = sha256(
        json.dumps(material, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return f"candidate:{digest}"


@dataclass(frozen=True, slots=True)
class MarketDayLedger:
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
    unfilled_order_id: str | None = None
    fill_id: str | None = None
    terminal_trade_id: str | None = None
    abstain_reason: str | None = None
    containment_reason: str | None = None
    day_closed: bool = False

    def __post_init__(self) -> None:
        if type(self.market_day_id) is not MarketDayId:
            raise DailyCardinalityValidationError("invalid market_day_id")
        if type(self.eligible_day) is not bool or type(self.data_complete) is not bool:
            raise DailyCardinalityValidationError("invalid eligibility flags")
        if (
            type(self.authorized_windows) is not tuple
            or not self.authorized_windows
            or tuple(sorted(set(self.authorized_windows))) != self.authorized_windows
            or any(type(hour) is not int or not 0 <= hour <= 23 for hour in self.authorized_windows)
        ):
            raise DailyCardinalityValidationError("invalid authorized windows")
        if (
            type(self.observed_windows) is not tuple
            or tuple(sorted(set(self.observed_windows))) != self.observed_windows
            or any(hour not in self.authorized_windows for hour in self.observed_windows)
        ):
            raise DailyCardinalityValidationError("invalid observed windows")
        _token(self.source_rule_version, "source_rule_version")
        if type(self.software_sha) is not str or _SHA40.fullmatch(self.software_sha) is None:
            raise DailyCardinalityValidationError("invalid software_sha")
        if (
            type(self.evidence_fingerprint) is not str
            or _SHA256.fullmatch(self.evidence_fingerprint) is None
        ):
            raise DailyCardinalityValidationError("invalid evidence_fingerprint")
        _unique(self.candidate_ids, "candidate_ids")
        _unique(self.qualified_setup_ids, "qualified_setup_ids")
        for name, value in (
            ("selected_setup_id", self.selected_setup_id),
            ("pending_order_id", self.pending_order_id),
            ("unfilled_order_id", self.unfilled_order_id),
            ("fill_id", self.fill_id),
            ("terminal_trade_id", self.terminal_trade_id),
            ("abstain_reason", self.abstain_reason),
            ("containment_reason", self.containment_reason),
        ):
            if value is not None:
                _token(value, name)
        if self.selected_setup_id is not None:
            if self.selected_setup_id not in self.qualified_setup_ids:
                raise DailyCardinalityValidationError("selected setup is not qualified")
            if not self.eligible_day or not self.data_complete:
                raise DailyCardinalityValidationError("day cannot select a setup")
        if self.pending_order_id is not None and self.selected_setup_id is None:
            raise DailyCardinalityValidationError("pending order lacks selection")
        if self.unfilled_order_id is not None and self.pending_order_id is None:
            raise DailyCardinalityValidationError("unfilled order lacks pending order")
        if self.fill_id is not None and self.pending_order_id is None:
            raise DailyCardinalityValidationError("fill lacks pending order")
        if self.unfilled_order_id is not None and self.fill_id is not None:
            raise DailyCardinalityValidationError("order cannot be filled and unfilled")
        if self.terminal_trade_id is not None and self.fill_id is None:
            raise DailyCardinalityValidationError("terminal trade lacks fill")
        if (
            self.day_closed
            and self.pending_order_id is not None
            and self.fill_id is None
            and self.unfilled_order_id is None
        ):
            raise DailyCardinalityValidationError("closed day retains unresolved order")

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
    def unfilled_order_count(self) -> int:
        return int(self.unfilled_order_id is not None)

    @property
    def filled_trade_count(self) -> int:
        return int(self.fill_id is not None)

    @property
    def terminal_trade_count(self) -> int:
        return int(self.terminal_trade_id is not None)

    @property
    def daily_trade_budget(self) -> DailyTradeBudget:
        if self.selected_setup_id is None:
            return DailyTradeBudget.AVAILABLE
        return DailyTradeBudget.CONSUMED

    @property
    def phase(self) -> MarketDayPhase:
        if self.day_closed:
            return MarketDayPhase.DAY_CLOSED
        if self.terminal_trade_id is not None:
            return MarketDayPhase.TERMINAL
        if self.fill_id is not None:
            return MarketDayPhase.FILLED
        if self.unfilled_order_id is not None:
            return MarketDayPhase.ORDER_UNFILLED
        if self.pending_order_id is not None:
            return MarketDayPhase.ORDER_PENDING
        if self.selected_setup_id is not None:
            return MarketDayPhase.DAILY_SELECTION_FROZEN
        if self.observed_windows:
            return MarketDayPhase.WINDOWS_EVALUATED
        if self.data_complete:
            return MarketDayPhase.DATA_VALIDATED
        return MarketDayPhase.DAY_OPEN

    def observe_window(self, hour: int) -> MarketDayLedger:
        if self.day_closed or hour not in self.authorized_windows or hour in self.observed_windows:
            raise DailyCardinalityValidationError("window cannot be observed")
        return replace(self, observed_windows=tuple(sorted((*self.observed_windows, hour))))

    def add_candidate(self, candidate_id: str) -> MarketDayLedger:
        _token(candidate_id, "candidate_id")
        if self.day_closed or candidate_id in self.candidate_ids:
            raise DailyCardinalityValidationError("candidate cannot be added")
        return replace(self, candidate_ids=(*self.candidate_ids, candidate_id))

    def add_qualified_setup(self, setup_id: str) -> MarketDayLedger:
        _token(setup_id, "setup_id")
        if (
            self.day_closed
            or not self.eligible_day
            or not self.data_complete
            or setup_id in self.qualified_setup_ids
        ):
            raise DailyCardinalityValidationError("setup cannot be qualified")
        return replace(self, qualified_setup_ids=(*self.qualified_setup_ids, setup_id))

    def select_setup(self, setup_id: str) -> MarketDayLedger:
        if (
            self.day_closed
            or setup_id not in self.qualified_setup_ids
            or self.selected_setup_id is not None
        ):
            raise DailyCardinalityValidationError("daily setup budget is unavailable")
        return replace(self, selected_setup_id=setup_id)

    def record_pending_order(self, order_id: str) -> MarketDayLedger:
        _token(order_id, "order_id")
        if self.selected_setup_id is None or self.pending_order_id is not None:
            raise DailyCardinalityValidationError("daily pending-order budget is unavailable")
        return replace(self, pending_order_id=order_id)

    def record_unfilled_order(self, unfilled_id: str) -> MarketDayLedger:
        _token(unfilled_id, "unfilled_id")
        if (
            self.pending_order_id is None
            or self.fill_id is not None
            or self.unfilled_order_id is not None
        ):
            raise DailyCardinalityValidationError("pending order cannot resolve unfilled")
        return replace(self, unfilled_order_id=unfilled_id)

    def record_fill(self, fill_id: str) -> MarketDayLedger:
        _token(fill_id, "fill_id")
        if (
            self.pending_order_id is None
            or self.unfilled_order_id is not None
            or self.fill_id is not None
        ):
            raise DailyCardinalityValidationError("daily fill budget is unavailable")
        return replace(self, fill_id=fill_id)

    def record_terminal_trade(self, trade_id: str) -> MarketDayLedger:
        _token(trade_id, "trade_id")
        if self.fill_id is None or self.terminal_trade_id is not None:
            raise DailyCardinalityValidationError("daily terminal-trade budget is unavailable")
        return replace(self, terminal_trade_id=trade_id)

    def close_day(
        self,
        *,
        abstain_reason: str | None = None,
        containment_reason: str | None = None,
    ) -> MarketDayLedger:
        if self.day_closed:
            raise DailyCardinalityValidationError("day is already closed")
        if abstain_reason is not None:
            _token(abstain_reason, "abstain_reason")
        if containment_reason is not None:
            _token(containment_reason, "containment_reason")
        if (
            self.pending_order_id is not None
            and self.fill_id is None
            and self.unfilled_order_id is None
        ):
            raise DailyCardinalityValidationError("unresolved order prevents close")
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
            "candidate_count": self.candidate_count,
            "candidate_ids": list(self.candidate_ids),
            "qualified_setup_count": self.qualified_setup_count,
            "qualified_setup_ids": list(self.qualified_setup_ids),
            "selected_setup_count": self.selected_setup_count,
            "daily_selection": self.selected_setup_id,
            "daily_trade_budget_before": DailyTradeBudget.AVAILABLE.value,
            "daily_trade_budget_after": self.daily_trade_budget.value,
            "pending_order_count": self.pending_order_count,
            "unfilled_order_count": self.unfilled_order_count,
            "fill_count": self.filled_trade_count,
            "terminal_trade_count": self.terminal_trade_count,
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
    unfilled_order_count: int
    filled_trade_count: int
    terminal_trade_count: int
    daily_cardinality_violations: int = 0


def summarize_market_days(ledgers: tuple[MarketDayLedger, ...]) -> DailyCardinalitySummary:
    if type(ledgers) is not tuple or len({item.market_day_id for item in ledgers}) != len(ledgers):
        raise DailyCardinalityValidationError("aggregate MarketDayId set is invalid")
    eligible = sum(item.eligible_day for item in ledgers)
    summary = DailyCardinalitySummary(
        eligible_market_days=eligible,
        candidate_count=sum(item.candidate_count for item in ledgers),
        qualified_setup_count=sum(item.qualified_setup_count for item in ledgers),
        selected_setup_count=sum(item.selected_setup_count for item in ledgers),
        pending_order_count=sum(item.pending_order_count for item in ledgers),
        unfilled_order_count=sum(item.unfilled_order_count for item in ledgers),
        filled_trade_count=sum(item.filled_trade_count for item in ledgers),
        terminal_trade_count=sum(item.terminal_trade_count for item in ledgers),
    )
    if max(
        summary.selected_setup_count,
        summary.pending_order_count,
        summary.filled_trade_count,
        summary.terminal_trade_count,
    ) > eligible:
        raise DailyCardinalityValidationError("economic count exceeds eligible market-days")
    return summary
