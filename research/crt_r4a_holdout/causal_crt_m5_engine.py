"""Integrated causal R4-A 2C/MSS15 and TRUE3C/MSS5 research detector.

Processes CLOSED native M5 in order and emits only ratified structural events
with frozen pre-sweep pivots. Six NY H4 anchors; two independent models.
No broker orders, PnL, indicator FVG/Inside/Multi, or TradingView event parity.
R4-A pinned Git blob 693e3f49719e86e2ea0702f7b355af33bd0c4c7c.

Research limitations: reference H4 aggregation parity on DST transitions and
native provider phases, Pine M5 tie rules, and full f_engine state still unproven.
Never label these as original Pine events until parity_gate actually passes.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from research.crt_r4a_holdout.pine_h4_geometry import (
    ClosedH4,
    c1_allowed,
    true_three_c,
    two_c_return,
)
from research.crt_r4a_holdout.pine_swing_primitives import (
    Bar,
    M5Swings,
    M15Close,
    M15Swings,
    Pivot,
    SwingSnapshot,
    freeze_pre_sweep,
    mss15_cross,
    mss5_cross,
)

NY = ZoneInfo("America/New_York")
H4 = timedelta(hours=4)
M5 = timedelta(minutes=5)


@dataclass(frozen=True)
class Candle:
    opened_at: datetime
    open: float
    high: float
    low: float
    close: float

    def __post_init__(self) -> None:
        if self.opened_at.tzinfo is None:
            raise ValueError("M5 candle needs UTC offset")
        if not (
            0 < self.low <= min(self.open, self.close)
            <= max(self.open, self.close) <= self.high
        ):
            raise ValueError("M5 OHLC invalid")

    @property
    def end(self) -> datetime:
        return self.opened_at + M5

    def swing_bar(self) -> Bar:
        return Bar(self.opened_at, self.high, self.low, self.close)


@dataclass
class Pending:
    model: str
    c1: ClosedH4
    c2: ClosedH4 | None
    target_start: datetime
    direction: int = 0
    double_sweep: bool = False
    sweep_at: datetime | None = None
    pivot5: Pivot | None = None
    pivot15: Pivot | None = None
    mss5_at: datetime | None = None
    mss15_at: datetime | None = None
    swept: ClosedH4 | None = None
    ratified_at: datetime | None = None
    emitted: bool = False


@dataclass(frozen=True)
class Evidence:
    identity: str
    symbol: str
    model: str
    side: str
    c1_at: datetime
    sweep_at: datetime
    ratified_at: datetime
    mss_at: datetime
    available_at: datetime
    c1_high: float
    c1_low: float
    sweep_high: float
    sweep_low: float
    mss_pivot: float

    def parity_row(self) -> dict[str, str]:
        values = {
            "event_id": self.identity,
            "symbol": self.symbol,
            "model": self.model,
            "side": self.side,
        }
        for key in (
            "c1_at", "sweep_at", "ratified_at", "mss_at", "available_at"
        ):
            values[key] = getattr(self, key).isoformat()
        for key in (
            "c1_high", "c1_low", "sweep_high", "sweep_low", "mss_pivot"
        ):
            values[key] = str(getattr(self, key))
        return values


class CausalCRTM5:
    """Mutable strictly chronological two-model QA detector, no trade fills."""

    def __init__(self, symbol: str, family: str, phase: int = 0) -> None:
        if not symbol or family not in ("forex", "index", "btc"):
            raise ValueError("symbol and R4-A family required")
        if phase not in range(5):
            raise ValueError("native M5 phase outside [0,4]")
        self.symbol, self.family, self.phase = symbol, family, phase
        self.m5 = M5Swings(left=2, right=2)
        self.m15 = M15Swings(left=2, right=2, source_phase_min=phase)
        self._last: Candle | None = None
        self._bucket: tuple[str, int] | None = None
        self._bucket_start: datetime | None = None
        self._group: list[Candle] = []
        self._closed: list[ClosedH4] = []
        self._a_c2: Pending | None = None
        self._a_c3: Pending | None = None
        self._b_c3: Pending | None = None
        self.evidence: list[Evidence] = []
        self.stats: dict[str, int] = {}

    def _count(self, key: str) -> None:
        self.stats[key] = self.stats.get(key, 0) + 1

    def _bucket_for(self, opened: datetime) -> tuple[str, int]:
        local = opened.astimezone(NY)
        if local.minute % 5 != self.phase or local.second:
            raise ValueError("source M5 phase/seconds mismatch")
        origin = 2 if self.family == "index" else 1
        h = (origin + 4 * ((local.hour - origin) % 24 // 4)) % 24
        day = local.date() - timedelta(days=1) if local.hour < origin else local.date()
        return day.isoformat(), h

    def _closed_h4(self) -> ClosedH4 | None:
        bars = self._group
        if not bars or len(bars) != 48 or self._bucket is None:
            return None
        first, last = bars[0], bars[-1]
        ny_first = first.opened_at.astimezone(NY)
        ny_end = last.end.astimezone(NY)
        h = self._bucket[1]
        if (
            ny_first.hour != h or ny_first.minute != self.phase
            or ny_end.hour != (h + 4) % 24 or ny_end.minute != self.phase
            or any(bars[i - 1].end != bars[i].opened_at
                   for i in range(1, len(bars)))
        ):
            return None
        hi, low = max(b.high for b in bars), min(b.low for b in bars)
        if hi <= low:
            return None
        return ClosedH4(
            first.opened_at, last.end, hi, low, last.close
        )

    def _emit(self, pending: Pending) -> None:
        if pending.emitted or pending.double_sweep:
            return
        if (
            pending.sweep_at is None or pending.ratified_at is None
            or pending.swept is None or pending.direction not in (1, -1)
        ):
            return
        if pending.model == "A_2C_MSS15":
            mss, p = pending.mss15_at, pending.pivot15
        else:
            mss, p = pending.mss5_at, pending.pivot5
        if mss is None or p is None or p.pivot_at >= pending.sweep_at:
            return
        available = max(mss, pending.ratified_at)
        identity = (
            f"{self.symbol}|{pending.model}|"
            f"{pending.c1.opened_at.isoformat()}|"
            f"{pending.target_start.isoformat()}"
        )
        self.evidence.append(Evidence(
            identity, self.symbol, pending.model,
            "LONG" if pending.direction == 1 else "SHORT",
            pending.c1.opened_at, pending.sweep_at,
            pending.ratified_at, mss, available,
            pending.c1.high, pending.c1.low,
            pending.swept.high, pending.swept.low, p.level
        ))
        pending.emitted = True
        self._count("events_" + pending.model)

    def _on_m15(self, closed: M15Close | None) -> None:
        if closed is None:
            return
        for p, limit in (
            (self._a_c2, self._a_c2.target_start + H4 if self._a_c2 else None),
            (self._a_c3, self._a_c3.target_start + H4 if self._a_c3 else None),
        ):
            if (
                p is None or limit is None or p.double_sweep
                or p.sweep_at is None or p.mss15_at is not None
            ):
                continue
            if mss15_cross(
                closed, direction=p.direction, pivot=p.pivot15,
                sweep_closed_at=p.sweep_at, latest_closed_at=limit
            ):
                p.mss15_at = closed.closed_at
                self._count("mss15_a")
                if p.ratified_at is not None:
                    self._emit(p)

    def _finish_period(self, closed: ClosedH4 | None) -> None:
        # Both old C3 models expire after the H4 currently closing.
        if self._b_c3 is not None and closed is not None:
            p = self._b_c3
            if p.target_start == closed.opened_at:
                geometry = true_three_c(p.c1, p.c2, closed, self.family) if p.c2 else 0
                if (
                    geometry == p.direction != 0
                    and not p.double_sweep
                    and p.mss5_at is not None
                ):
                    p.ratified_at = closed.closed_at
                    p.swept = closed
                    self._emit(p)
                elif geometry:
                    self._count("b_geometry_without_own_mss5")
        self._b_c3 = None
        self._a_c3 = None

        if self._a_c2 is not None and closed is not None:
            p = self._a_c2
            if p.target_start == closed.opened_at:
                geometry = two_c_return(p.c1, closed, self.family)
                if geometry == p.direction != 0 and not p.double_sweep:
                    self._count("a_ratified_geometry")
                    p.ratified_at = closed.closed_at
                    p.swept = closed
                    self._emit(p)
                    self._a_c3 = p
                    p.target_start = closed.closed_at
                elif geometry:
                    self._count("a_geometry_without_causal_sweep")
        self._a_c2 = None

        if closed is None:
            self._closed.clear()
            self._count("h4_incomplete")
            return
        self._closed.append(closed)
        self._closed = self._closed[-3:]
        self._count("h4_complete")

        # Each closed H4 can become next C1 regardless of another cycle.
        if c1_allowed(closed.opened_at, self.family):
            self._a_c2 = Pending(
                "A_2C_MSS15", closed, None, closed.closed_at
            )
        if len(self._closed) >= 2:
            c1, c2 = self._closed[-2:]
            if (
                c1.closed_at == c2.opened_at
                and c1_allowed(c1.opened_at, self.family)
                and c2.high <= c1.high and c2.low >= c1.low
                and c1.low < c2.close < c1.high
            ):
                self._b_c3 = Pending(
                    "B_TRUE3C_MSS5", c1, c2, c2.closed_at
                )
                self._count("b_setup_ready")

    def _sweep(
        self, p: Pending | None, bar: Candle,
        before5: SwingSnapshot, before15: SwingSnapshot | None
    ) -> None:
        if p is None or p.double_sweep or bar.opened_at < p.target_start:
            return
        if bar.opened_at >= p.target_start + H4:
            return
        low = bar.low < p.c1.low
        high = bar.high > p.c1.high
        if low and high:
            p.double_sweep = True
            p.mss5_at = p.mss15_at = None
            self._count("double_sweep")
            return
        direction = 1 if low else -1 if high else 0
        if direction == 0:
            return
        if p.direction != 0:
            if p.direction != direction:
                p.double_sweep = True
                p.mss5_at = p.mss15_at = None
                self._count("double_sweep")
            return
        p.direction = direction
        p.sweep_at = bar.end
        p.pivot5 = freeze_pre_sweep(before5, direction, bar.opened_at)
        p.pivot15 = freeze_pre_sweep(before15, direction, bar.opened_at)
        self._count("sweeps_" + p.model)
        if (
            (p.model == "B_TRUE3C_MSS5" and p.pivot5 is None)
            or (p.model == "A_2C_MSS15" and p.pivot15 is None)
        ):
            self._count("sweeps_missing_confirmed_pivot")

    def consume(self, candle: Candle) -> list[Evidence]:
        """Process one M5 newly CLOSED at candle.end; event time is causal."""
        if self._last is not None and candle.opened_at <= self._last.opened_at:
            raise ValueError("nonmonotone native M5 feed")
        old_count = len(self.evidence)
        now = candle.swing_bar()
        before5, continuous = self.m5.before_closed_bar(now)
        closed15 = self.m15.on_closed_m5(now)
        self._on_m15(closed15)
        bucket = self._bucket_for(candle.opened_at)
        if self._bucket is not None and bucket != self._bucket:
            self._finish_period(self._closed_h4())
            self._group.clear()
        if self._bucket is None or bucket != self._bucket:
            self._bucket = bucket
            self._bucket_start = candle.opened_at
        if not continuous and self._last is not None:
            # A gap cannot carry a pre-sweep candidate or an unclosed H4.
            self._a_c2 = self._a_c3 = self._b_c3 = None
            self._closed.clear()
            self._group.clear()
            self._count("feed_gaps")
        before15 = self.m15.snapshot()
        self._sweep(self._a_c2, candle, before5, before15)
        self._sweep(self._b_c3, candle, before5, before15)
        p = self._b_c3
        if (
            p is not None and p.sweep_at is not None
            and p.mss5_at is None and not p.double_sweep
            and mss5_cross(
                previous_close=self._last.close if self._last else None,
                current=now, previous_continuous=continuous,
                direction=p.direction, pivot=p.pivot5,
                sweep_closed_at=p.sweep_at,
                latest_closed_at=p.target_start + H4
            )
        ):
            p.mss5_at = candle.end
            self._count("mss5_b")
        self._group.append(candle)
        self.m5.finish_bar(now)
        self._last = candle
        self._count("m5_processed")
        return self.evidence[old_count:]

    def readout(self) -> dict[str, object]:
        return {
            "symbol": self.symbol,
            "family": self.family,
            "m5_phase": self.phase,
            "stats": dict(self.stats),
            "events_total": len(self.evidence),
            "events_a": sum(x.model == "A_2C_MSS15" for x in self.evidence),
            "events_b": sum(x.model == "B_TRUE3C_MSS5" for x in self.evidence),
            "status": "INTEGRATED_RESEARCH_DETECTOR_NOT_PINE_PARITY",
            "is_original_pine_f_engine": False,
            "holdout_certified": False,
            "trading_orders_permitted": False,
        }
