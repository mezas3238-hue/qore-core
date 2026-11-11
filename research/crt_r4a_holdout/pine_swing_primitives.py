"""Causal M5/M15 swing and MSS primitives derived from pinned R4-A Pine.

Research QA ONLY, NO BROKER EXECUTION, NO CLAIM OF FULL f_engine PARITY.
Reference R4-A Git blob 693e3f49719e86e2ea0702f7b355af33bd0c4c7c.

Pine: M5 ta.pivothigh/low(high/low,L,R)[1], then lastHigh5At
time[right5+1], updated *after* sweep/MSS decisions (L719-723, 2028-35).
M15: three contiguous M5 form one closed M15; arrays of M15 OHLC
and strict pivot L/R updated only when next M15 bucket begins (L997-1029).
MSS: frozen pre-sweep pivot, continuous previous close, strict crossing
after sweep bar end (L1031-44, 1990-97).
Pine pivot tie semantics and exact broker phase mapping still require
event-for-event platform verification; no assumption of certification.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

FIVE = timedelta(minutes=5)
FIFTEEN = timedelta(minutes=15)


@dataclass(frozen=True)
class Bar:
    opened_at: datetime
    high: float
    low: float
    close: float

    def __post_init__(self) -> None:
        if self.opened_at.tzinfo is None:
            raise ValueError("bar requires UTC-offset timestamp")
        if self.high <= 0 or self.low <= 0 or self.high < self.low:
            raise ValueError("invalid OHLC high/low")
        if not self.low <= self.close <= self.high:
            raise ValueError("close outside high/low")

    @property
    def end(self) -> datetime:
        return self.opened_at + FIVE


@dataclass(frozen=True)
class Pivot:
    kind: str
    level: float
    pivot_at: datetime
    confirmed_at: datetime
    segment_at: datetime


@dataclass(frozen=True)
class SwingSnapshot:
    high: Pivot | None
    low: Pivot | None
    segment_at: datetime


@dataclass(frozen=True)
class M15Close:
    start_at: datetime
    closed_at: datetime
    high: float
    low: float
    close: float
    previous_close: float | None
    previous_continuous: bool
    source_phase_min: int


def _strict_pivot(
    highs: list[float], lows: list[float], pivot: int,
    left: int, right: int,
) -> tuple[bool, bool]:
    """Strict isolated extremum, R4-A explicit M15 loop L1014–1028.

    M5 Pine ta.pivot* tie-breaking on equal highs/lows remains a platform
    parity question. Strict here deliberately rejects ambiguous equal highs.
    """
    if pivot < left or len(highs) <= pivot + right:
        return False, False
    ch, cl = highs[pivot], lows[pivot]
    hi = all(
        ch > highs[i] for i in range(pivot - left, pivot + right + 1)
        if i != pivot
    )
    lo = all(
        cl < lows[i] for i in range(pivot - left, pivot + right + 1)
        if i != pivot
    )
    return hi, lo


class M5Swings:
    """Two-phase interface so a sweep cannot freeze same-bar new pivots."""

    def __init__(self, left: int = 2, right: int = 2) -> None:
        if not (1 <= left <= 7 and 1 <= right <= 7):
            raise ValueError("Pine M5 swing inputs require L/R 1..7")
        self.left, self.right = left, right
        self._bars: list[Bar] = []
        self._high: Pivot | None = None
        self._low: Pivot | None = None
        self._last_end: datetime | None = None
        self._segment_at: datetime | None = None

    def before_closed_bar(self, bar: Bar) -> tuple[SwingSnapshot, bool]:
        """State visible while processing bar sweep; then call finish_bar."""
        if self._segment_at is None or self._last_end != bar.opened_at:
            self._bars.clear()
            self._segment_at = bar.opened_at
            self._high = None
            self._low = None
            return SwingSnapshot(None, None, self._segment_at), False
        return SwingSnapshot(self._high, self._low, self._segment_at), True

    def finish_bar(self, bar: Bar) -> None:
        if self._segment_at is None:
            raise ValueError("before_closed_bar must be called first")
        if self._bars and self._bars[-1].end != bar.opened_at:
            raise ValueError("before_closed_bar required after gap")
        self._bars.append(bar)
        self._last_end = bar.end
        # Pine updates the newly confirmed M5 swing AFTER sweep/MSS checks.
        p = len(self._bars) - 1 - self.right
        highs = [v.high for v in self._bars]
        lows = [v.low for v in self._bars]
        hi, lo = _strict_pivot(highs, lows, p, self.left, self.right)
        if hi:
            self._high = Pivot(
                "HIGH", highs[p], self._bars[p].opened_at,
                bar.end, self._segment_at
            )
        if lo:
            self._low = Pivot(
                "LOW", lows[p], self._bars[p].opened_at,
                bar.end, self._segment_at
            )
        # A small left/right window plus age validation is enough for
        # new pivots; the last frozen pivot is retained independently.
        if len(self._bars) > 40:
            self._bars = self._bars[-40:]


class M15Swings:
    """Collect three M5 bars, finalize M15 at the *next* bucket boundary."""

    def __init__(
        self, left: int = 2, right: int = 2, source_phase_min: int = 0
    ) -> None:
        if not (1 <= left <= 7 and 1 <= right <= 7):
            raise ValueError("Pine M15 L/R outside 1..7")
        if not 0 <= source_phase_min <= 4:
            raise ValueError("native provider M5 phase outside 0..4")
        self.left, self.right = left, right
        self.phase = source_phase_min
        self._bucket: datetime | None = None
        self._group: list[Bar] = []
        self._last_end: datetime | None = None
        self._segment: datetime | None = None
        self._history: list[M15Close] = []
        self._high: Pivot | None = None
        self._low: Pivot | None = None

    def bucket_for(self, bar: Bar) -> datetime:
        minute = bar.opened_at.minute
        if minute % 5 != self.phase or bar.opened_at.second:
            raise ValueError("M5 does not match its native phase")
        return bar.opened_at - timedelta(minutes=(minute - self.phase) % 15)

    def snapshot(self) -> SwingSnapshot | None:
        if self._segment is None:
            return None
        return SwingSnapshot(self._high, self._low, self._segment)

    def on_closed_m5(self, bar: Bar) -> M15Close | None:
        bucket = self.bucket_for(bar)
        if self._segment is None or (
            self._last_end is not None and bar.opened_at != self._last_end
        ):
            self._segment = bar.opened_at
            self._bucket = None
            self._group.clear()
            self._history.clear()
            self._high = self._low = None
        completed: M15Close | None = None
        if self._bucket is not None and bucket != self._bucket:
            g = self._group
            if (
                len(g) == 3 and g[0].opened_at == self._bucket
                and g[0].end == g[1].opened_at
                and g[1].end == g[2].opened_at
                and g[-1].end == bucket
            ):
                prev = self._history[-1] if self._history else None
                contiguous = prev is not None and prev.closed_at == self._bucket
                completed = M15Close(
                    self._bucket, g[-1].end,
                    max(x.high for x in g),
                    min(x.low for x in g),
                    g[-1].close,
                    prev.close if contiguous else None,
                    contiguous, self.phase
                )
                self._history.append(completed)
                if len(self._history) > 48:
                    self._history.pop(0)
                p = len(self._history) - 1 - self.right
                highs = [v.high for v in self._history]
                lows = [v.low for v in self._history]
                hi, lo = _strict_pivot(highs, lows, p, self.left, self.right)
                if hi:
                    self._high = Pivot(
                        "HIGH", highs[p], self._history[p].start_at,
                        completed.closed_at, self._segment
                    )
                if lo:
                    self._low = Pivot(
                        "LOW", lows[p], self._history[p].start_at,
                        completed.closed_at, self._segment
                    )
        if self._bucket != bucket:
            self._group = []
            self._bucket = bucket
        self._group.append(bar)
        self._last_end = bar.end
        return completed


def freeze_pre_sweep(
    snapshot: SwingSnapshot | None,
    direction: int, bar_opened_at: datetime,
    max_pivot_age_min: int = 720,
) -> Pivot | None:
    """R4-A pre-sweep pivot validation for independent 3C/Inside (L1818)."""
    if direction not in (1, -1):
        raise ValueError("direction must be +1 LONG or -1 SHORT")
    if max_pivot_age_min < 15 or max_pivot_age_min > 1440:
        raise ValueError("Pine maxPivotAge outside 15..1440")
    if snapshot is None:
        return None
    pivot = snapshot.high if direction == 1 else snapshot.low
    if pivot is None or not snapshot.segment_at <= pivot.pivot_at:
        return None
    age = bar_opened_at - pivot.pivot_at
    if not timedelta(0) < age <= timedelta(minutes=max_pivot_age_min):
        return None
    return pivot


def mss5_cross(
    *, previous_close: float | None, current: Bar, previous_continuous: bool,
    direction: int, pivot: Pivot | None, sweep_closed_at: datetime,
    latest_closed_at: datetime,
) -> bool:
    """R4-A TRUE3C L1992–1997; checks time and genuine close crossover."""
    if (
        pivot is None or previous_close is None or not previous_continuous
        or direction not in (1, -1)
        or pivot.pivot_at >= sweep_closed_at
        or current.opened_at < sweep_closed_at
        or current.end > latest_closed_at
    ):
        return False
    if direction == 1:
        return previous_close <= pivot.level < current.close
    return previous_close >= pivot.level > current.close


def mss15_cross(
    bar: M15Close | None, *, direction: int, pivot: Pivot | None,
    sweep_closed_at: datetime, latest_closed_at: datetime,
) -> bool:
    """R4-A M15 L1031–1044: 3 M5, phase, continuity, frozen cross."""
    if (
        bar is None or not bar.previous_continuous
        or bar.previous_close is None or pivot is None
        or direction not in (1, -1)
        or pivot.pivot_at >= sweep_closed_at
        or not sweep_closed_at < bar.closed_at <= latest_closed_at
        or bar.closed_at.minute % 15 != bar.source_phase_min
        or bar.closed_at.second != 0
    ):
        return False
    if direction == 1:
        return bar.previous_close <= pivot.level < bar.close
    return bar.previous_close >= pivot.level > bar.close
