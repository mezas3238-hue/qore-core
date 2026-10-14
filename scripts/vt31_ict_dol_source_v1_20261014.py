#!/usr/bin/env python3
"""Independent source-time M1 provenance of QORE ICT contextual DOL pools.

This is not an author-exact ICT rule or an order/edge engine. Rebuild source
intervals without consulting COG, then compare a pre-existing COG DTO.
Never call the COG producer here and never derive broker order or sizing.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime, time, timedelta
from decimal import Decimal
from typing import Any

from qore.infrastructure.traders.vt31_ict_cleanroom.contracts import (
    NEW_YORK,
    CognitiveDecision,
    M1Bar,
    SessionId,
    Side,
    utc,
    window_bounds,
)

FAMILIES = (
    "PRIOR_NY_CASH_SESSION",
    "ASIA_NY_CLOCK",
    "LONDON_NY_CLOCK",
)


@dataclass(frozen=True, slots=True)
class DolPool:
    family: str
    side: str
    level: Decimal | None
    source_start: datetime
    source_end: datetime
    state: str
    reason: str
    first_touch_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class DolAttestation:
    session: SessionId
    as_of: datetime
    state: str
    reasons: tuple[str, ...]
    pools: tuple[DolPool, ...]
    method_certified: bool = False
    cognition_certified: bool = False
    execution_authorized: bool = False

    def record(self) -> dict[str, Any]:
        def convert(value: Any) -> Any:
            if isinstance(value, datetime):
                return value.isoformat()
            if isinstance(value, Decimal):
                return str(value)
            if isinstance(value, dict):
                return {k: convert(v) for k, v in value.items()}
            if isinstance(value, (tuple, list)):
                return [convert(v) for v in value]
            return value

        return convert(asdict(self))


def _ny(day: Any, hour: int, minute: int = 0) -> datetime:
    return datetime.combine(day, time(hour, minute), tzinfo=NEW_YORK).astimezone(UTC)


def _previous_weekday(day: Any) -> Any:
    prior = day - timedelta(days=1)
    while prior.weekday() >= 5:
        prior -= timedelta(days=1)
    return prior


def _source_ranges(as_of: datetime) -> tuple[tuple[str, datetime, datetime], ...]:
    day = as_of.astimezone(NEW_YORK).date()
    prior = _previous_weekday(day)
    return (
        ("PRIOR_NY_CASH_SESSION", _ny(prior, 9, 30), _ny(prior, 16)),
        ("ASIA_NY_CLOCK", _ny(day, 0), _ny(day, 3)),
        ("LONDON_NY_CLOCK", _ny(day, 3), _ny(day, 5)),
    )


def _complete_range(
    history: tuple[M1Bar, ...], begin: datetime, end: datetime,
) -> tuple[M1Bar, ...] | None:
    rows = tuple(b for b in history if begin <= utc(b.opened_at) < end)
    count = int((end - begin).total_seconds() // 60)
    if len(rows) != count:
        return None
    if any(
        utc(b.opened_at) != begin + timedelta(minutes=i)
        or utc(b.closed_at) != begin + timedelta(minutes=i + 1)
        for i, b in enumerate(rows)
    ):
        return None
    return rows


def _consumption(
    history: tuple[M1Bar, ...], end: datetime, as_of: datetime,
    side: str, level: Decimal,
) -> tuple[str, str, datetime | None]:
    after = tuple(
        b for b in history if end <= utc(b.opened_at) and utc(b.closed_at) <= as_of
    )
    # Positive touch is observable even when gaps occurred earlier.
    for b in after:
        touched = b.high >= level if side == "HIGH" else b.low <= level
        if touched:
            return "CONSUMED", "LEVEL_TOUCHED_AFTER_SOURCE_CLOSE", utc(b.closed_at)
    # A non-touch is only justified under complete post-source M1 coverage.
    coverage = _complete_range(after, end, as_of)
    if coverage is None:
        return "UNKNOWN", "POST_SOURCE_M1_COVERAGE_GAPPED", None
    return "UNCONSUMED", "NO_POST_SOURCE_TOUCH_WITH_FULL_M1_COVERAGE", None


def _pool_pair(
    *, name: str, start: datetime, end: datetime,
    history: tuple[M1Bar, ...], at: datetime, session: SessionId,
) -> tuple[DolPool, DolPool]:
    if name == "LONDON_NY_CLOCK" and session == SessionId.LONDON:
        reason = "LONDON_RANGE_NOT_COMPLETE_DURING_LONDON_SILVER_BULLET"
        return tuple(
            DolPool(name + "_" + s, s, None, start, end, "UNKNOWN", reason)
            for s in ("HIGH", "LOW")
        )  # type: ignore[return-value]
    if end > at:
        return tuple(
            DolPool(
                name + "_" + s, s, None, start, end, "UNKNOWN",
                "SOURCE_INTERVAL_NOT_CLOSED_AS_OF",
            )
            for s in ("HIGH", "LOW")
        )  # type: ignore[return-value]
    rows = _complete_range(history, start, end)
    if rows is None:
        reason = (
            "PRIOR_WEEKDAY_CASH_INCOMPLETE_OR_HOLIDAY_CALENDAR_UNKNOWN"
            if name == "PRIOR_NY_CASH_SESSION" else "SOURCE_M1_INCOMPLETE"
        )
        return tuple(
            DolPool(name + "_" + s, s, None, start, end, "UNKNOWN", reason)
            for s in ("HIGH", "LOW")
        )  # type: ignore[return-value]
    hi, lo = max(b.high for b in rows), min(b.low for b in rows)
    if hi <= lo:
        return tuple(
            DolPool(name + "_" + s, s, None, start, end, "UNKNOWN",
                    "SOURCE_EXTREMES_DEGENERATE")
            for s in ("HIGH", "LOW")
        )  # type: ignore[return-value]
    result: list[DolPool] = []
    for side, level in (("HIGH", hi), ("LOW", lo)):
        state, reason, first_touch = _consumption(history, end, at, side, level)
        result.append(
            DolPool(name + "_" + side, side, level, start, end,
                    state, reason, first_touch)
        )
    return result[0], result[1]


def attest_ict_dol_source(
    *, as_of: datetime, session: SessionId,
    history: tuple[M1Bar, ...],
    cognition: CognitiveDecision | None = None,
) -> DolAttestation:
    """Witness only: compare reconstructed pools with already emitted COG.

    A missing pool or gaps never get filled from the claimed COG draw_target.
    `CONFIRMED` means a narrow M2 source fact, never certified ICT/trading.
    """
    at = utc(as_of)
    def result(
        state: str, reasons: tuple[str, ...],
        pools: tuple[DolPool, ...] = (),
    ) -> DolAttestation:
        return DolAttestation(session, at, state, reasons, pools)

    if not isinstance(session, SessionId) or at.second or at.microsecond:
        return result("REJECTED", ("INVALID_SESSION_OR_ASOF_ALIGNMENT",))
    first, last = window_bounds(at, session)
    if not first < at <= last:
        return result("REJECTED", ("ASOF_OUTSIDE_CLOSED_M1_SESSION",))
    if not history:
        return result("UNKNOWN", ("NO_M1_HISTORY",))
    if any(utc(b.closed_at) > at for b in history):
        return result("REJECTED", ("FUTURE_M1_FORBIDDEN",))
    stamps = tuple(utc(b.opened_at) for b in history)
    if any(left >= right for left, right in zip(stamps, stamps[1:])):
        return result("REJECTED", ("M1_DUPLICATE_OR_UNSORTED",))
    if utc(history[-1].closed_at) != at:
        return result("UNKNOWN", ("ASOF_CLOSED_M1_NOT_PRESENT",))
    pools = tuple(
        pool
        for name, start, end in _source_ranges(at)
        for pool in _pool_pair(
            name=name, start=start, end=end, history=history,
            at=at, session=session,
        )
    )
    if cognition is None:
        return result("UNKNOWN", ("NO_PREEXISTING_COG_DECISION",), pools)
    if cognition.session != session or utc(cognition.observed_at) != at:
        return result("REJECTED", ("COG_SESSION_OR_ASOF_MISMATCH",), pools)
    target_name = cognition.draw_family
    pool = next((p for p in pools if p.family == target_name), None)
    if pool is None:
        return result("REJECTED", ("COG_DOL_FAMILY_NOT_IN_FROZEN_QORE_SOURCES",), pools)
    expected_side = "HIGH" if cognition.side == Side.LONG else "LOW"
    if pool.side != expected_side:
        return result("REJECTED", ("COG_DOL_SIDE_CONTRADICTS_DIRECTION",), pools)
    if (
        utc(cognition.draw_level_observed_at) < pool.source_end
        or utc(cognition.draw_level_observed_at) > at
    ):
        return result("REJECTED", ("COG_DOL_ANNOUNCED_BEFORE_SOURCE_CLOSE",), pools)
    if pool.level is None:
        return result(
            "UNKNOWN", ("SOURCE_POOL_NOT_CAUSALLY_ATTESTABLE", pool.reason), pools
        )
    if cognition.draw_target != pool.level:
        return result("REJECTED", ("COG_DOL_PRICE_DISAGREES_WITH_SOURCE_M1",), pools)
    if pool.state == "CONSUMED":
        return result("REJECTED", ("COG_DOL_ALREADY_CONSUMED",), pools)
    if pool.state != "UNCONSUMED":
        return result("UNKNOWN", ("POOL_AVAILABILITY_UNVERIFIABLE", pool.reason), pools)
    return result(
        "CONFIRMED", ("M2_QORE_CONTEXT_DOL_SOURCE_AND_AVAILABILITY_ONLY",), pools
    )
