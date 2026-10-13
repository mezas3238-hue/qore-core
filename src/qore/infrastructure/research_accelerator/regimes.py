"""Diagnostic-only trailing-window regime annotations (never a live signal or gate)."""
from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from zoneinfo import ZoneInfo

from qore.infrastructure.research_accelerator.core import BidBar, ResearchDataError


@dataclass(frozen=True, slots=True)
class Regime:
    trend: str
    volatility: str
    phase: str


def label_regimes(
    bars: tuple[BidBar, ...],
    *,
    lookback: int = 30,
    trend_ratio_threshold: float = 0.60,
    high_vol_bps: float = 12.0,
) -> tuple[Regime | None, ...]:
    """O(n) prefix-sum diagnostics based on <=current closed BID bar only."""
    if lookback < 3 or not 0 < trend_ratio_threshold < 1 or high_vol_bps <= 0:
        raise ResearchDataError("invalid preregistered regime thresholds")
    if not bars:
        return ()
    returns = [0.0]
    for prev, now in zip(bars, bars[1:], strict=False):
        returns.append(float((now.close / prev.close - 1) * 10000))
    cumulative = [0.0]
    absolute = [0.0]
    squares = [0.0]
    for r in returns:
        cumulative.append(cumulative[-1] + r)
        absolute.append(absolute[-1] + abs(r))
        squares.append(squares[-1] + r * r)
    output: list[Regime | None] = []
    ny = ZoneInfo("America/New_York")
    for i, bar in enumerate(bars):
        if i < lookback:
            output.append(None)
            continue
        left = i - lookback + 1
        n = lookback
        net = cumulative[i + 1] - cumulative[left]
        variation = absolute[i + 1] - absolute[left]
        sq = squares[i + 1] - squares[left]
        mean = net / n
        vol = sqrt(max(0.0, sq / n - mean * mean))
        trend = "trend" if variation and abs(net) / variation >= trend_ratio_threshold else "range"
        clock = bar.closed_at.astimezone(ny)
        if clock.hour == 9 and 30 <= clock.minute < 60:
            phase = "opening"
        elif returns[i] * net < 0:
            phase = "reversal"
        else:
            phase = "continuation"
        output.append(Regime(trend, "high" if vol >= high_vol_bps else "low", phase))
    return tuple(output)
