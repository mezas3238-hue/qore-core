"""Independent causal MSS researcher for Inside return, Multi4, MultiN.

Family7 M15 retest uses the source-owned original CRT MSS from the separate
SecondaryGeometryObserver. These 3 extra family tracks freeze their own
pre-sweep pivot, invalidate double sweep, and require closed-H4 geometry.
They never execute orders or claim identical Pine f_engine() timing.

Pine source R4-A blob 693e3f49719e86e2ea0702f7b355af33bd0c4c7c.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Protocol

from research.crt_r4a_holdout.pine_h4_geometry import (
    ClosedH4,
    c1_allowed,
)
from research.crt_r4a_holdout.pine_swing_primitives import (
    Bar,
    M15Close,
    Pivot,
    SwingSnapshot,
    freeze_pre_sweep,
    mss15_cross,
    mss5_cross,
)
from research.crt_r4a_holdout.secondary_family_geometry import (
    Geometry,
    inside_return,
    multi4,
    multi_n,
)
from research.crt_r4a_holdout.seven_family_contract import Family

H4 = timedelta(hours=4)


class NativeClosedM5(Protocol):
    opened_at: datetime
    high: float
    low: float
    close: float

    @property
    def end(self) -> datetime: ...


@dataclass
class AuxiliaryPending:
    family: Family
    c1: ClosedH4
    start: datetime
    terminal_end: datetime
    first_sweep_end: datetime
    inside_c2: ClosedH4 | None = None
    direction: int = 0
    double_sweep: bool = False
    sweep_at: datetime | None = None
    own_pivot5: Pivot | None = None
    own_pivot15: Pivot | None = None
    own_mss5_at: datetime | None = None
    own_mss15_at: datetime | None = None


@dataclass(frozen=True)
class AuxiliaryMssEvent:
    family: Family
    symbol: str
    identity: str
    side: str
    c1_at: datetime
    sweep_at: datetime
    own_pivot_at: datetime
    own_pivot_price: float
    own_mss15_at: datetime
    ratified_at: datetime
    available_at: datetime
    own_pivot_frozen_pre_sweep: bool = True
    broker_orders_executed: int = 0
    pine_parity_certified: bool = False


class AuxiliaryOwnedMss:
    """Separate per-family source lineage, never borrowing 2C MSS."""

    def __init__(self, symbol: str, family: str) -> None:
        if not symbol or family not in ("forex", "index", "btc"):
            raise ValueError("valid R4-A instrument and family required")
        self.symbol, self.family = symbol, family
        self.history: list[ClosedH4] = []
        self.pending: list[AuxiliaryPending] = []
        self.events: list[AuxiliaryMssEvent] = []
        self._seen: set[str] = set()
        self._terminal_selected: set[tuple[Family, datetime]] = set()
        self.stats: dict[str, int] = {}

    def _count(self, key: str) -> None:
        self.stats[key] = self.stats.get(key, 0) + 1

    def _emit(self, p: AuxiliaryPending, g: Geometry) -> None:
        pivot = p.own_pivot15
        if (
            p.double_sweep or p.direction == 0
            or p.direction != g.direction
            or p.sweep_at is None or pivot is None
            or p.own_mss15_at is None
            or pivot.pivot_at >= p.sweep_at
            or p.own_mss15_at <= p.sweep_at
            or p.own_mss15_at > g.ratified_at
        ):
            return
        # For overlapping Multi-N c1, prefer most recent shorter N.
        terminal_key = (p.family, g.ratified_at)
        if (
            p.family == Family.MULTIN
            and terminal_key in self._terminal_selected
        ):
            return
        identity = (
            f"{self.symbol}|{p.family.value}|{p.c1.opened_at.isoformat()}|"
            f"{p.start.isoformat()}"
        )
        if identity in self._seen:
            return
        self._seen.add(identity)
        self._terminal_selected.add(terminal_key)
        self.events.append(AuxiliaryMssEvent(
            p.family, self.symbol, identity,
            "LONG" if p.direction == 1 else "SHORT",
            p.c1.opened_at, p.sweep_at,
            pivot.pivot_at, pivot.level, p.own_mss15_at,
            g.ratified_at, max(g.ratified_at, p.own_mss15_at),
        ))
        self._count("signals_" + p.family.value)

    def on_closed_h4(self, closed: ClosedH4 | None) -> None:
        if closed is None or not closed.valid:
            self.history.clear()
            self.pending.clear()
            self._count("h4_discontinuities")
            return
        self.history.append(closed)
        self.history = self.history[-7:]
        h = self.history

        # Existing pending candidates mature at the end of their own H4,
        # not when an unrelated CRT closes.
        due = sorted(
            (p for p in self.pending if p.terminal_end == closed.closed_at),
            key=lambda p: p.c1.opened_at, reverse=True
        )
        for p in due:
            g: Geometry | None = None
            if p.family == Family.INSIDE_RETURN and p.inside_c2:
                g = inside_return(
                    p.c1, p.inside_c2, closed, self.family
                )
            elif p.family == Family.MULTI4 and len(h) >= 4:
                bars = h[-4:]
                if bars[0].opened_at == p.c1.opened_at:
                    g = multi4(*bars, self.family)
            elif p.family == Family.MULTIN and len(h) >= 4:
                for n in range(4, min(7, len(h)) + 1):
                    bars = tuple(h[-n:])
                    if bars[0].opened_at == p.c1.opened_at:
                        g = multi_n(bars, self.family)
                        break
            if g is not None:
                self._count("geometry_" + p.family.value)
                self._emit(p, g)
        self.pending = [
            p for p in self.pending if p.terminal_end > closed.closed_at
        ]

        # New C1 is legal in each of the six H4 source clock windows.
        if c1_allowed(closed.opened_at, self.family):
            self.pending.append(AuxiliaryPending(
                Family.MULTI4, closed, closed.closed_at,
                closed.closed_at + 3 * H4, closed.closed_at + H4
            ))
        # Inside requires C2 strict inside C1; its *next* H4 may sweep C2.
        if len(h) >= 2:
            c1, c2 = h[-2:]
            if (
                c1.closed_at == c2.opened_at
                and c1_allowed(c1.opened_at, self.family)
                and c1.low < c2.low and c2.high < c1.high
            ):
                self.pending.append(AuxiliaryPending(
                    Family.INSIDE_RETURN, c1, c2.closed_at,
                    c2.closed_at + H4, c2.closed_at + H4,
                    inside_c2=c2
                ))
        # Multi-N terminal after 2..5 strictly interior H4; each C1 owns
        # a separate pending, but exactly one newest will publish per end.
        for n in range(3, min(6, len(h)) + 1):
            bars = tuple(h[-n:])
            c1 = bars[0]
            if not (
                c1_allowed(c1.opened_at, self.family)
                and all(x.valid for x in bars)
                and all(
                    bars[i-1].closed_at == bars[i].opened_at
                    for i in range(1, n)
                )
                and all(
                    c1.low < x.low and x.high < c1.high
                    for x in bars[1:]
                )
            ):
                continue
            self.pending.append(AuxiliaryPending(
                Family.MULTIN, c1, closed.closed_at,
                closed.closed_at + H4, closed.closed_at + H4
            ))
        if len(self.pending) > 24:
            raise ValueError("auxiliary family candidate memory ceiling")

    def on_closed_m15(self, closed: M15Close | None) -> None:
        if closed is None:
            return
        for p in self.pending:
            if (
                p.double_sweep or p.sweep_at is None
                or p.own_mss15_at is not None
            ):
                continue
            if mss15_cross(
                closed, direction=p.direction, pivot=p.own_pivot15,
                sweep_closed_at=p.sweep_at, latest_closed_at=p.terminal_end
            ):
                p.own_mss15_at = closed.closed_at
                self._count("mss15_" + p.family.value)

    def on_closed_m5(
        self, current: NativeClosedM5, *,
        before5: SwingSnapshot, before15: SwingSnapshot | None,
        previous_close: float | None, previous_continuous: bool
    ) -> None:
        bar = Bar(current.opened_at, current.high, current.low, current.close)
        for p in self.pending:
            if p.double_sweep or not p.start <= bar.opened_at < p.terminal_end:
                continue
            threshold_low = (
                p.inside_c2.low if p.inside_c2 is not None else p.c1.low
            )
            threshold_high = (
                p.inside_c2.high if p.inside_c2 is not None else p.c1.high
            )
            low = bar.low < threshold_low
            high = bar.high > threshold_high
            if p.sweep_at is not None:
                if (p.direction == 1 and high) or (
                    p.direction == -1 and low
                ):
                    p.double_sweep = True
                    p.own_mss5_at = p.own_mss15_at = None
                    self._count("opposite_sweep")
                    continue
            elif bar.opened_at < p.first_sweep_end:
                if low and high:
                    p.double_sweep = True
                    self._count("first_bar_double_sweep")
                    continue
                if low != high:
                    p.direction = 1 if low else -1
                    p.sweep_at = bar.end
                    p.own_pivot5 = freeze_pre_sweep(
                        before5, p.direction, bar.opened_at
                    )
                    p.own_pivot15 = freeze_pre_sweep(
                        before15, p.direction, bar.opened_at
                    )
                    self._count("sweep_" + p.family.value)
            if (
                p.sweep_at is not None and p.own_mss5_at is None
                and mss5_cross(
                    previous_close=previous_close, current=bar,
                    previous_continuous=previous_continuous,
                    direction=p.direction, pivot=p.own_pivot5,
                    sweep_closed_at=p.sweep_at,
                    latest_closed_at=p.terminal_end
                )
            ):
                p.own_mss5_at = bar.end
                self._count("mss5_" + p.family.value)

    def readout(self) -> dict[str, object]:
        names = (Family.INSIDE_RETURN, Family.MULTI4, Family.MULTIN)
        counts = {
            name.value: sum(x.family == name for x in self.events)
            for name in names
        }
        return {
            "status": "THREE_EXTRA_OWN_MSS15_RESEARCH_LANES",
            "family_events": counts,
            "total_extra_mss15_events": len(self.events),
            "candidate_stats": dict(self.stats),
            "not_identical_pine_f_engine": True,
            "unseen_holdout": False,
            "trades_executed": 0,
        }
