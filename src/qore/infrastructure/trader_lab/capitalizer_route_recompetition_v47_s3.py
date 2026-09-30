"""Pure outcome-blind route recompetition for Capitalizer V47-S3.

This module contains no source-run constants and consumes no outcomes. It only
normalizes already-admitted exact-fill candidates and applies the frozen MAX3
ceiling across FRACTAL and FTM routes. A later source-frozen workflow must bind
authoritative run/SHA inputs before any empirical S3 result exists.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from qore.infrastructure.trader_lab.capitalizer_contract import (
    MAX_EXECUTIONS_PER_SESSION,
)


@dataclass(frozen=True, slots=True)
class RouteCandidate:
    source_identity: str
    period: str
    symbol: str
    session: str
    operating_date: str
    side: str
    route: str
    entry_at: str
    entry_price: str
    stop_price: str
    target_price: str
    entry_mode: str
    exact_provider_tick_fill: bool
    official_v46_adapter_passed: bool
    outcome_used_for_selection: bool = False
    terminal_outcome_read: bool = False
    fresh_holdout_opened: bool = False
    trader_certified: bool = False

    def __post_init__(self) -> None:
        if not self.source_identity:
            raise ValueError("S3 route candidate source identity required")
        if not self.symbol or self.symbol != self.symbol.upper():
            raise ValueError("S3 route candidate symbol must be uppercase")
        if self.route not in {
            "FRACTAL_SCALP_CONTINUATION",
            "FAILURE_TO_MANIPULATE_CONTINUATION",
        }:
            raise ValueError("S3 route candidate route unsupported")
        at = datetime.fromisoformat(self.entry_at)
        if at.tzinfo is None or at.utcoffset() is None:
            raise ValueError("S3 entry timestamp must be timezone-aware")
        if (
            not self.exact_provider_tick_fill
            or not self.official_v46_adapter_passed
            or self.outcome_used_for_selection
            or self.terminal_outcome_read
            or self.fresh_holdout_opened
            or self.trader_certified
        ):
            raise ValueError("S3 route candidate governance drift")


@dataclass(frozen=True, slots=True)
class RecompetitionResult:
    entrants: tuple[RouteCandidate, ...]
    selected: tuple[RouteCandidate, ...]
    max3_ceiling: int = MAX_EXECUTIONS_PER_SESSION
    outcome_used_for_selection: bool = False
    route_priority_used: bool = False

    def __post_init__(self) -> None:
        if self.max3_ceiling != MAX_EXECUTIONS_PER_SESSION:
            raise ValueError("S3 MAX3 ceiling drift")
        if self.outcome_used_for_selection or self.route_priority_used:
            raise ValueError("S3 recompetition cannot use outcome/route priority")
        selected_ids = {
            (
                row.source_identity,
                row.period,
                row.symbol,
                row.route,
                row.entry_at,
            )
            for row in self.selected
        }
        entrant_ids = {
            (
                row.source_identity,
                row.period,
                row.symbol,
                row.route,
                row.entry_at,
            )
            for row in self.entrants
        }
        if not selected_ids <= entrant_ids:
            raise ValueError("S3 selected candidate was not an entrant")


def _at(row: RouteCandidate) -> datetime:
    return datetime.fromisoformat(row.entry_at).astimezone(UTC)


def _sort_key(row: RouteCandidate) -> tuple[datetime, str, str]:
    # route is a deterministic tie-break only, never a preference.
    return _at(row), row.symbol, row.route


def _identity_key(
    row: RouteCandidate,
) -> tuple[str, str, str, str, str]:
    return (
        row.source_identity,
        row.period,
        row.symbol,
        row.route,
        row.entry_at,
    )


def recompact_exact_duplicates(
    rows: tuple[RouteCandidate, ...],
) -> tuple[RouteCandidate, ...]:
    """Remove byte-equivalent repeated source rows, never cross-route collisions."""

    unique: dict[tuple[str, str, str, str, str], RouteCandidate] = {}
    for row in rows:
        key = _identity_key(row)
        existing = unique.get(key)
        if existing is not None and existing != row:
            raise ValueError("S3 duplicate identity carries divergent payload")
        unique[key] = row
    return tuple(sorted(unique.values(), key=_sort_key))


def select_max3_across_routes(
    rows: tuple[RouteCandidate, ...],
) -> RecompetitionResult:
    """Recompete all exact-fill routes by time; MAX3 is a ceiling, never quota."""

    entrants = recompact_exact_duplicates(rows)
    grouped: dict[tuple[str, str, str], list[RouteCandidate]] = {}
    for row in entrants:
        key = (row.period, row.session, row.operating_date)
        grouped.setdefault(key, []).append(row)

    selected: list[RouteCandidate] = []
    for key in sorted(grouped):
        ordered = sorted(grouped[key], key=_sort_key)
        selected.extend(ordered[:MAX_EXECUTIONS_PER_SESSION])

    result = tuple(sorted(selected, key=_sort_key))
    return RecompetitionResult(
        entrants=entrants,
        selected=result,
    )


def entrant_counts_by_route(
    rows: tuple[RouteCandidate, ...],
) -> dict[str, int]:
    result = {
        "FRACTAL_SCALP_CONTINUATION": 0,
        "FAILURE_TO_MANIPULATE_CONTINUATION": 0,
    }
    for row in rows:
        result[row.route] += 1
    return result


def selected_counts_by_route(
    result: RecompetitionResult,
) -> dict[str, int]:
    return entrant_counts_by_route(result.selected)
