"""Certified-trader historical frequency/loss telemetry.

This module is descriptive telemetry only.  It does not authorize orders, alter
risk, suppress signals, or turn historical maxima into live trading limits.

Canonical rules:
- select trades by entry_at in a frozen [window_start, window_end) interval;
- convert timestamps to America/New_York before calendar grouping;
- count every ISO calendar week touched by the frozen interval, including
  partial boundary weeks;
- assign closed R to the New York date/week of exit_at;
- P95 entry frequency uses the lower empirical quantile:
  sorted_counts[floor((n - 1) * 0.95)].

The same engine is reusable for future certified market specialists.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import ROUND_FLOOR, Decimal
from enum import StrEnum
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

NEW_YORK = ZoneInfo("America/New_York")
BASELINE_SCHEMA = "qore.certified-trader.weekly-telemetry-baselines.v1"


class TelemetryStatus(StrEnum):
    WITHIN_BASELINE = "WITHIN_BASELINE"
    ABOVE_P95_FREQUENCY = "ABOVE_P95_FREQUENCY"
    ABOVE_HISTORICAL_MAX_FREQUENCY = "ABOVE_HISTORICAL_MAX_FREQUENCY"
    WORSE_THAN_HISTORICAL_DAY = "WORSE_THAN_HISTORICAL_DAY"
    WORSE_THAN_HISTORICAL_WEEK = "WORSE_THAN_HISTORICAL_WEEK"


@dataclass(frozen=True, slots=True)
class HistoricalTrade:
    entry_at: datetime
    exit_at: datetime
    net_r: Decimal

    def __post_init__(self) -> None:
        _aware(self.entry_at, "entry_at")
        _aware(self.exit_at, "exit_at")
        if self.exit_at < self.entry_at:
            raise ValueError("exit_at cannot precede entry_at")
        if not self.net_r.is_finite():
            raise ValueError("net_r must be finite")


@dataclass(frozen=True, slots=True)
class WeeklyTelemetryMetrics:
    window_start: datetime
    window_end: datetime
    timezone: str
    trades: int
    calendar_weeks: int
    active_weeks: int
    zero_entry_weeks: int
    average_entries_per_week: Decimal
    median_entries_per_week: Decimal
    p95_entries_per_week: int
    max_entries_per_week: int
    max_entries_per_day: int
    worst_closed_day: date
    worst_closed_day_r: Decimal
    worst_closed_week_year: int
    worst_closed_week: int
    worst_closed_week_r: Decimal
    closed_trading_days: int
    losing_closed_days: int
    closed_weeks: int
    losing_closed_weeks: int

    def __post_init__(self) -> None:
        _aware(self.window_start, "window_start")
        _aware(self.window_end, "window_end")
        if self.window_end <= self.window_start:
            raise ValueError("window_end must follow window_start")
        for value in (
            self.trades,
            self.calendar_weeks,
            self.active_weeks,
            self.zero_entry_weeks,
            self.p95_entries_per_week,
            self.max_entries_per_week,
            self.max_entries_per_day,
            self.closed_trading_days,
            self.losing_closed_days,
            self.closed_weeks,
            self.losing_closed_weeks,
        ):
            if value < 0:
                raise ValueError("telemetry counts cannot be negative")
        if self.calendar_weeks == 0:
            raise ValueError("calendar_weeks cannot be zero")
        if self.active_weeks + self.zero_entry_weeks != self.calendar_weeks:
            raise ValueError("active/zero week counts do not reconcile")

    def as_json(self) -> dict[str, Any]:
        return {
            "window_start": self.window_start.isoformat(),
            "window_end": self.window_end.isoformat(),
            "timezone": self.timezone,
            "trades": self.trades,
            "calendar_weeks": self.calendar_weeks,
            "active_weeks": self.active_weeks,
            "zero_entry_weeks": self.zero_entry_weeks,
            "average_entries_per_week": str(self.average_entries_per_week),
            "median_entries_per_week": str(self.median_entries_per_week),
            "p95_entries_per_week": self.p95_entries_per_week,
            "max_entries_per_week": self.max_entries_per_week,
            "max_entries_per_day": self.max_entries_per_day,
            "worst_closed_day": self.worst_closed_day.isoformat(),
            "worst_closed_day_r": str(self.worst_closed_day_r),
            "worst_closed_week": {
                "iso_year": self.worst_closed_week_year,
                "iso_week": self.worst_closed_week,
                "closed_r": str(self.worst_closed_week_r),
            },
            "closed_trading_days": self.closed_trading_days,
            "losing_closed_days": self.losing_closed_days,
            "closed_weeks": self.closed_weeks,
            "losing_closed_weeks": self.losing_closed_weeks,
        }


@dataclass(frozen=True, slots=True)
class CertifiedTelemetryBaseline:
    trader_id: str
    identity: str
    symbol: str
    metrics: WeeklyTelemetryMetrics
    source_run_id: int
    source_artifact_id: int
    source_artifact_digest: str
    source_trade_ledger: str
    source_trade_ledger_sha256: str
    certification_run_id: int
    certification_artifact_id: int

    def __post_init__(self) -> None:
        for value in (self.trader_id, self.identity, self.symbol, self.source_trade_ledger):
            if not value:
                raise ValueError("baseline text fields cannot be empty")
        for digest in (self.source_artifact_digest, self.source_trade_ledger_sha256):
            normalized = digest.removeprefix("sha256:")
            if len(normalized) != 64:
                raise ValueError("baseline SHA-256 digest is malformed")


@dataclass(frozen=True, slots=True)
class LiveWeekObservation:
    entries: int
    closed_r: Decimal
    worst_closed_day_r: Decimal

    def __post_init__(self) -> None:
        if self.entries < 0:
            raise ValueError("entries cannot be negative")
        if not self.closed_r.is_finite() or not self.worst_closed_day_r.is_finite():
            raise ValueError("live R observations must be finite")


@dataclass(frozen=True, slots=True)
class LiveBaselineComparison:
    trader_id: str
    entries: int
    closed_r: Decimal
    worst_closed_day_r: Decimal
    frequency_status: TelemetryStatus
    weekly_loss_status: TelemetryStatus
    daily_loss_status: TelemetryStatus
    advisory_only: bool = True

    @property
    def outside_historical_envelope(self) -> bool:
        return any(
            status is not TelemetryStatus.WITHIN_BASELINE
            for status in (
                self.frequency_status,
                self.weekly_loss_status,
                self.daily_loss_status,
            )
        )


def trade_from_mapping(
    row: Mapping[str, Any],
    *,
    r_field: str = "scaled_net_010_r",
) -> HistoricalTrade:
    return HistoricalTrade(
        entry_at=datetime.fromisoformat(str(row["entry_at"])),
        exit_at=datetime.fromisoformat(str(row["exit_at"])),
        net_r=Decimal(str(row[r_field])),
    )


def load_jsonl_trades(
    path: Path,
    *,
    r_field: str = "scaled_net_010_r",
) -> tuple[HistoricalTrade, ...]:
    rows: list[HistoricalTrade] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        raw = json.loads(line)
        if not isinstance(raw, dict):
            raise ValueError(f"trade row {line_number} must be a JSON object")
        rows.append(trade_from_mapping(raw, r_field=r_field))
    return tuple(rows)


def compute_weekly_telemetry(
    trades: Iterable[HistoricalTrade],
    *,
    window_start: datetime,
    window_end: datetime,
    timezone: ZoneInfo = NEW_YORK,
) -> WeeklyTelemetryMetrics:
    _aware(window_start, "window_start")
    _aware(window_end, "window_end")
    if window_end <= window_start:
        raise ValueError("window_end must follow window_start")

    selected = tuple(
        trade
        for trade in trades
        if window_start <= trade.entry_at < window_end
    )
    if not selected:
        raise ValueError("no trades in requested telemetry window")

    week_keys = _calendar_week_keys(window_start, window_end, timezone)
    entries_by_week: dict[tuple[int, int], int] = {key: 0 for key in week_keys}
    entries_by_day: dict[date, int] = {}
    closed_r_by_day: dict[date, Decimal] = {}
    closed_r_by_week: dict[tuple[int, int], Decimal] = {}

    for trade in selected:
        entry_local = trade.entry_at.astimezone(timezone)
        entry_iso = entry_local.isocalendar()
        entry_week = (entry_iso.year, entry_iso.week)
        if entry_week not in entries_by_week:
            raise ValueError("entry week escaped frozen telemetry window")
        entries_by_week[entry_week] += 1
        entries_by_day[entry_local.date()] = entries_by_day.get(entry_local.date(), 0) + 1

        exit_local = trade.exit_at.astimezone(timezone)
        exit_day = exit_local.date()
        exit_iso = exit_local.isocalendar()
        exit_week = (exit_iso.year, exit_iso.week)
        closed_r_by_day[exit_day] = closed_r_by_day.get(exit_day, Decimal(0)) + trade.net_r
        closed_r_by_week[exit_week] = closed_r_by_week.get(exit_week, Decimal(0)) + trade.net_r

    weekly_counts = tuple(entries_by_week[key] for key in week_keys)
    active_weeks = sum(count > 0 for count in weekly_counts)
    sorted_counts = sorted(weekly_counts)
    p95_index = int(
        (
            Decimal(len(sorted_counts) - 1) * Decimal("0.95")
        ).to_integral_value(rounding=ROUND_FLOOR)
    )
    worst_day, worst_day_r = min(closed_r_by_day.items(), key=lambda item: item[1])
    worst_week, worst_week_r = min(closed_r_by_week.items(), key=lambda item: item[1])

    return WeeklyTelemetryMetrics(
        window_start=window_start,
        window_end=window_end,
        timezone=timezone.key,
        trades=len(selected),
        calendar_weeks=len(week_keys),
        active_weeks=active_weeks,
        zero_entry_weeks=len(week_keys) - active_weeks,
        average_entries_per_week=Decimal(len(selected)) / Decimal(len(week_keys)),
        median_entries_per_week=_median_int(weekly_counts),
        p95_entries_per_week=sorted_counts[p95_index],
        max_entries_per_week=max(weekly_counts),
        max_entries_per_day=max(entries_by_day.values()),
        worst_closed_day=worst_day,
        worst_closed_day_r=worst_day_r,
        worst_closed_week_year=worst_week[0],
        worst_closed_week=worst_week[1],
        worst_closed_week_r=worst_week_r,
        closed_trading_days=len(closed_r_by_day),
        losing_closed_days=sum(value < 0 for value in closed_r_by_day.values()),
        closed_weeks=len(closed_r_by_week),
        losing_closed_weeks=sum(value < 0 for value in closed_r_by_week.values()),
    )


def compare_live_week(
    baseline: CertifiedTelemetryBaseline,
    observation: LiveWeekObservation,
) -> LiveBaselineComparison:
    metrics = baseline.metrics
    if observation.entries > metrics.max_entries_per_week:
        frequency = TelemetryStatus.ABOVE_HISTORICAL_MAX_FREQUENCY
    elif observation.entries > metrics.p95_entries_per_week:
        frequency = TelemetryStatus.ABOVE_P95_FREQUENCY
    else:
        frequency = TelemetryStatus.WITHIN_BASELINE

    weekly = (
        TelemetryStatus.WORSE_THAN_HISTORICAL_WEEK
        if observation.closed_r < metrics.worst_closed_week_r
        else TelemetryStatus.WITHIN_BASELINE
    )
    daily = (
        TelemetryStatus.WORSE_THAN_HISTORICAL_DAY
        if observation.worst_closed_day_r < metrics.worst_closed_day_r
        else TelemetryStatus.WITHIN_BASELINE
    )
    return LiveBaselineComparison(
        trader_id=baseline.trader_id,
        entries=observation.entries,
        closed_r=observation.closed_r,
        worst_closed_day_r=observation.worst_closed_day_r,
        frequency_status=frequency,
        weekly_loss_status=weekly,
        daily_loss_status=daily,
    )


def nominal_equity_percent(
    r_value: Decimal,
    *,
    base_risk_fraction_per_1r: Decimal = Decimal("0.002"),
) -> Decimal:
    if base_risk_fraction_per_1r <= 0:
        raise ValueError("base_risk_fraction_per_1r must be positive")
    return r_value * base_risk_fraction_per_1r * Decimal(100)


def load_certified_baselines(path: Path) -> dict[str, CertifiedTelemetryBaseline]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or raw.get("schema") != BASELINE_SCHEMA:
        raise ValueError("certified telemetry baseline schema mismatch")
    if raw.get("timezone") != NEW_YORK.key:
        raise ValueError("certified telemetry baseline timezone drift")
    traders = raw.get("traders")
    if not isinstance(traders, dict) or not traders:
        raise ValueError("certified telemetry baselines require traders")

    result: dict[str, CertifiedTelemetryBaseline] = {}
    for trader_id, payload in traders.items():
        if not isinstance(payload, dict):
            raise ValueError("trader baseline payload must be an object")
        metrics_raw = payload["metrics"]
        if not isinstance(metrics_raw, dict):
            raise ValueError("metrics payload must be an object")
        worst_week = metrics_raw["worst_closed_week"]
        if not isinstance(worst_week, dict):
            raise ValueError("worst_closed_week payload must be an object")
        metrics = WeeklyTelemetryMetrics(
            window_start=datetime.fromisoformat(str(metrics_raw["window_start"])),
            window_end=datetime.fromisoformat(str(metrics_raw["window_end"])),
            timezone=str(metrics_raw["timezone"]),
            trades=int(metrics_raw["trades"]),
            calendar_weeks=int(metrics_raw["calendar_weeks"]),
            active_weeks=int(metrics_raw["active_weeks"]),
            zero_entry_weeks=int(metrics_raw["zero_entry_weeks"]),
            average_entries_per_week=Decimal(str(metrics_raw["average_entries_per_week"])),
            median_entries_per_week=Decimal(str(metrics_raw["median_entries_per_week"])),
            p95_entries_per_week=int(metrics_raw["p95_entries_per_week"]),
            max_entries_per_week=int(metrics_raw["max_entries_per_week"]),
            max_entries_per_day=int(metrics_raw["max_entries_per_day"]),
            worst_closed_day=date.fromisoformat(str(metrics_raw["worst_closed_day"])),
            worst_closed_day_r=Decimal(str(metrics_raw["worst_closed_day_r"])),
            worst_closed_week_year=int(worst_week["iso_year"]),
            worst_closed_week=int(worst_week["iso_week"]),
            worst_closed_week_r=Decimal(str(worst_week["closed_r"])),
            closed_trading_days=int(metrics_raw["closed_trading_days"]),
            losing_closed_days=int(metrics_raw["losing_closed_days"]),
            closed_weeks=int(metrics_raw["closed_weeks"]),
            losing_closed_weeks=int(metrics_raw["losing_closed_weeks"]),
        )
        source = payload["source"]
        certification = payload["certification"]
        if not isinstance(source, dict) or not isinstance(certification, dict):
            raise ValueError("source/certification baseline payload malformed")
        result[str(trader_id)] = CertifiedTelemetryBaseline(
            trader_id=str(trader_id),
            identity=str(payload["identity"]),
            symbol=str(payload["symbol"]),
            metrics=metrics,
            source_run_id=int(source["run_id"]),
            source_artifact_id=int(source["artifact_id"]),
            source_artifact_digest=str(source["artifact_digest"]),
            source_trade_ledger=str(source["trade_ledger"]),
            source_trade_ledger_sha256=str(source["trade_ledger_sha256"]),
            certification_run_id=int(certification["run_id"]),
            certification_artifact_id=int(certification["artifact_id"]),
        )
    return result


def _calendar_week_keys(
    window_start: datetime,
    window_end: datetime,
    timezone: ZoneInfo,
) -> tuple[tuple[int, int], ...]:
    first_day = window_start.astimezone(timezone).date()
    last_day = (window_end - timedelta(microseconds=1)).astimezone(timezone).date()
    cursor = first_day - timedelta(days=first_day.weekday())
    final = last_day - timedelta(days=last_day.weekday())
    keys: list[tuple[int, int]] = []
    while cursor <= final:
        iso = cursor.isocalendar()
        keys.append((iso.year, iso.week))
        cursor += timedelta(days=7)
    return tuple(keys)


def _median_int(values: Iterable[int]) -> Decimal:
    ordered = sorted(values)
    if not ordered:
        raise ValueError("cannot calculate median of empty values")
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return Decimal(ordered[middle])
    return (Decimal(ordered[middle - 1]) + Decimal(ordered[middle])) / Decimal(2)


def _aware(value: datetime, name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")
