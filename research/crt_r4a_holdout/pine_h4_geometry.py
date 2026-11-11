"""QORE R4-A H4 C1 clock and two-pattern geometry from exact Pine source.

R4-A blob: 693e3f49719e86e2ea0702f7b355af33bd0c4c7c.
L149–155: 6/6 NY H4 anchors. L1348–1359: TRUE3C strict close.
L1550–1594: C2 single-sweep return.
Not a whole f_engine() port. A valid/closed H4 from provider remains required.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

NY = ZoneInfo("America/New_York")
C1_CLOCKS = {
    "forex": frozenset((1, 5, 9, 13, 17, 21)),
    "index": frozenset((2, 6, 10, 14, 18, 22)),
    "btc": frozenset((1, 5, 9, 13, 17, 21)),
}
LEGACY_PROXY_C1_CLOCKS = {
    "forex": frozenset((1, 5, 21)),
    "index": frozenset((2, 6, 22)),
    "btc": frozenset((1, 5, 21)),
}


@dataclass(frozen=True)
class ClosedH4:
    opened_at: datetime
    closed_at: datetime
    high: float
    low: float
    close: float
    valid: bool = True

    def __post_init__(self) -> None:
        if self.opened_at.tzinfo is None or self.closed_at.tzinfo is None:
            raise ValueError("H4 timestamps must be timezone-aware")
        if self.closed_at <= self.opened_at:
            raise ValueError("H4 end must follow start")
        if not (
            self.low > 0 and self.high > self.low
            and self.low <= self.close <= self.high
        ):
            raise ValueError("invalid H4 candle geometry")


def c1_allowed(opened_at: datetime, family: str) -> bool:
    if family not in C1_CLOCKS:
        raise ValueError("unsupported R4-A family")
    if opened_at.tzinfo is None:
        raise ValueError("C1 NY clock requires timezone offset")
    return opened_at.astimezone(NY).hour in C1_CLOCKS[family]


def proxy_old_c1_allowed(opened_at: datetime, family: str) -> bool:
    if family not in LEGACY_PROXY_C1_CLOCKS:
        raise ValueError("unsupported legacy family")
    if opened_at.tzinfo is None:
        raise ValueError("timestamp requires timezone offset")
    return opened_at.astimezone(NY).hour in LEGACY_PROXY_C1_CLOCKS[family]


def two_c_return(c1: ClosedH4, c2: ClosedH4, family: str) -> int:
    """R4-A C2 strict single sweep + inclusive close inside C1, 1/-1/0."""
    if not (c1.valid and c2.valid and
            c1.closed_at == c2.opened_at and
            c1_allowed(c1.opened_at, family)):
        return 0
    low_sweep = c2.low < c1.low
    high_sweep = c2.high > c1.high
    if low_sweep == high_sweep or not c1.low <= c2.close <= c1.high:
        return 0
    return 1 if low_sweep else -1


def true_three_c(c1: ClosedH4, c2: ClosedH4, c3: ClosedH4, family: str) -> int:
    """R4-A L1352–58 strict C2 body return/C3 one-sided C1 sweep."""
    if not (
        c1.valid and c2.valid and c3.valid
        and c1.closed_at == c2.opened_at
        and c2.closed_at == c3.opened_at
        and c1_allowed(c1.opened_at, family)
        and c2.high <= c1.high
        and c2.low >= c1.low
        and c1.low < c2.close < c1.high
        and c1.low < c3.close < c1.high
    ):
        return 0
    low_sweep = c3.low < c1.low and c3.high <= c1.high
    high_sweep = c3.high > c1.high and c3.low >= c1.low
    if low_sweep == high_sweep:
        return 0
    return 1 if low_sweep else -1
