"""Source-grounded closed-H4 geometry for remaining CRT family hypotheses.

Pine R4-A immutable blob 693e3f49719e86e2ea0702f7b355af33bd0c4c7c:
 Inside return: lines 1482–1518, strict C2 (1557–1569).
 Multi4: L1277–1319.
 MultiN: L1385–1457.
 M15 retest: L1093–1127, L2134–40.

GEOMETRY/QA ONLY. No independent MSS frozen pivot or fill model yet;
none of these recognizers authorizes trades.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from research.crt_r4a_holdout.pine_h4_geometry import (
    ClosedH4,
    c1_allowed,
)
from research.crt_r4a_holdout.pine_swing_primitives import M15Close

FOUR_HOURS = timedelta(hours=4)


@dataclass(frozen=True)
class Geometry:
    name: str
    direction: int
    c1_at: datetime
    ratified_at: datetime
    own_mss_ever_certified: bool = False


def _chain(bars: tuple[ClosedH4, ...]) -> bool:
    return all(x.valid for x in bars) and all(
        bars[i - 1].closed_at == bars[i].opened_at
        for i in range(1, len(bars))
    )


def inside_return(
    c1: ClosedH4, c2: ClosedH4, terminal: ClosedH4, family: str
) -> Geometry | None:
    """C2 strictly inside C1, C3 sweeps C2 SINGLE side, ends inside C2."""
    bars = (c1, c2, terminal)
    if not (
        _chain(bars) and c1_allowed(c1.opened_at, family)
        and c1.low < c2.low and c2.high < c1.high
    ):
        return None
    lower = terminal.low < c2.low
    upper = terminal.high > c2.high
    if lower == upper or not c2.low <= terminal.close <= c2.high:
        return None
    return Geometry(
        "INSIDE_RETURN", 1 if lower else -1,
        c1.opened_at, terminal.closed_at
    )


def multi4(
    c1: ClosedH4, c2a: ClosedH4, c2b: ClosedH4,
    c3: ClosedH4, family: str
) -> Geometry | None:
    """Four consecutive closed H4 from Pine Multi4 (L1285–1294)."""
    if not (
        _chain((c1, c2a, c2b, c3))
        and c1_allowed(c1.opened_at, family)
        and c1.low <= c2a.close <= c1.high
        and c1.low <= c2b.close <= c1.high
    ):
        return None
    bull = (
        c2a.low < c1.low and c2a.high <= c1.high
        and c2b.high <= c1.high and c2b.low <= c1.low
        and c3.close > c2b.close and c3.close >= c1.low
    )
    bear = (
        c2a.high > c1.high and c2a.low >= c1.low
        and c2b.low >= c1.low and c2b.high >= c1.high
        and c3.close < c2b.close and c3.close <= c1.high
    )
    if bull == bear:
        return None
    return Geometry(
        "MULTI4", 1 if bull else -1, c1.opened_at, c3.closed_at
    )


def multi_n(
    bars: tuple[ClosedH4, ...], family: str
) -> Geometry | None:
    """Pine MultiN: C1 + 2..5 strict inside + final one-sided sweep."""
    if len(bars) not in (4, 5, 6, 7) or not _chain(bars):
        return None
    c1, terminal = bars[0], bars[-1]
    if not c1_allowed(c1.opened_at, family):
        return None
    if any(
        not c1.low < inner.low or not inner.high < c1.high
        for inner in bars[1:-1]
    ):
        return None
    low = terminal.low < c1.low and terminal.high <= c1.high
    high = terminal.high > c1.high and terminal.low >= c1.low
    if low == high or not c1.low <= terminal.close <= c1.high:
        return None
    return Geometry(
        "MULTI_N", 1 if low else -1, c1.opened_at, terminal.closed_at
    )


@dataclass(frozen=True)
class RetestSource:
    """Evidence of an *already confirmed* independent M15 MSS of SAME C1."""

    c1_at: datetime
    direction: int
    own_mss15_at: datetime
    own_mss15_pivot: float
    parent_crt_ratified_at: datetime
    source_model: str = "CRT_2C_RETURN"


def retest_m15(
    source: RetestSource, closed_m15: M15Close,
    *, linked_c1_at: datetime,
) -> Geometry | None:
    """Returns retrospective retest geometry only; never a new inherited MSS."""
    if (
        source.source_model != "CRT_2C_RETURN"
        or source.c1_at != linked_c1_at
        or source.direction not in (1, -1)
        or source.own_mss15_pivot <= 0
        or not closed_m15.previous_continuous
        or closed_m15.closed_at <= source.own_mss15_at
        or closed_m15.closed_at > source.own_mss15_at + FOUR_HOURS
        or closed_m15.closed_at.minute % 15 != closed_m15.source_phase_min
        or closed_m15.closed_at.second != 0
    ):
        return None
    if source.direction == 1:
        matched = (
            closed_m15.low <= source.own_mss15_pivot
            and closed_m15.close > source.own_mss15_pivot
        )
    else:
        matched = (
            closed_m15.high >= source.own_mss15_pivot
            and closed_m15.close < source.own_mss15_pivot
        )
    if not matched:
        return None
    return Geometry(
        "M15_RETEST", source.direction,
        source.c1_at,
        max(source.parent_crt_ratified_at, closed_m15.closed_at)
    )
