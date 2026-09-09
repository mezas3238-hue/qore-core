"""Past-only market-state features and post-decision path diagnostics."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from qore.infrastructure.market_data import OhlcSnapshot
from qore.infrastructure.trader_lab.first_cohort_backtest import (
    _MAX_HOLD_BARS,
    FirstCohortBacktestError,
    FirstCohortBacktestTrade,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide

CLASSIFIER_VERSION = "qore-trader-lab-market-state-v1"
SESSION_POLICY = "dst-aware-local-session-windows-v1"
FORWARD_PATH_POLICY = "contiguous-24bar-post-decision-extrema-v1"
TREND_LOOKBACK = 20
TREND_COMPARISON_LOOKBACK = 40
VOLATILITY_BASELINE = 40
VOLATILITY_RECENT = 10
VOLATILITY_PERCENTILE_LOOKBACK = 100
EXPANSION_BASELINE = 20
EXPANSION_RECENT = 3
MOMENTUM_LOOKBACK = 5
RANGE_LOOKBACK = 20
_LONDON = ZoneInfo("Europe/London")
_NEW_YORK = ZoneInfo("America/New_York")
_TOKYO = ZoneInfo("Asia/Tokyo")


class ConditionalMarketStateFeatureError(FirstCohortBacktestError):
    __slots__ = ()


def mean_decimal(values: list[Decimal]) -> Decimal:
    if not values:
        return Decimal(0)
    return sum(values, Decimal(0)) / Decimal(len(values))


def normalized_range(bar: OhlcSnapshot) -> Decimal:
    close = Decimal(str(bar.close))
    if close <= 0:
        return Decimal(0)
    return (Decimal(str(bar.high)) - Decimal(str(bar.low))) / close


def close_decimal(bar: OhlcSnapshot) -> Decimal:
    return Decimal(str(bar.close))


def trend_efficiency(history: tuple[OhlcSnapshot, ...]) -> Decimal | None:
    if len(history) < TREND_LOOKBACK:
        return None
    closes = [close_decimal(bar) for bar in history[-TREND_LOOKBACK:]]
    path = sum(
        (
            abs(current - previous)
            for previous, current in zip(closes, closes[1:], strict=False)
        ),
        Decimal(0),
    )
    if path == 0:
        return Decimal(0)
    return abs(closes[-1] - closes[0]) / path


def recent_realized_range(history: tuple[OhlcSnapshot, ...]) -> Decimal | None:
    if not history:
        return None
    retained = history[-VOLATILITY_RECENT:]
    return mean_decimal([normalized_range(bar) for bar in retained])


def range_width_fraction(history: tuple[OhlcSnapshot, ...]) -> Decimal | None:
    if len(history) < RANGE_LOOKBACK:
        return None
    recent = history[-RANGE_LOOKBACK:]
    high = max(Decimal(str(bar.high)) for bar in recent)
    low = min(Decimal(str(bar.low)) for bar in recent)
    close = close_decimal(recent[-1])
    if close <= 0:
        return None
    return (high - low) / close


def gap_state(history: tuple[OhlcSnapshot, ...]) -> str:
    if len(history) < 2:
        return "insufficient_history"
    previous = close_decimal(history[-2])
    current_open = Decimal(str(history[-1].open))
    if previous <= 0:
        return "no_material_gap"
    gap = (current_open - previous) / previous
    reference = recent_realized_range(history[:-1])
    if reference is None or reference <= 0 or abs(gap) < reference:
        return "no_material_gap"
    return "gap_up" if gap > 0 else "gap_down"


def momentum_acceleration(history: tuple[OhlcSnapshot, ...]) -> str:
    if len(history) < 7:
        return "insufficient_history"
    closes = [close_decimal(bar) for bar in history[-7:]]
    prior = closes[3] - closes[0]
    recent = closes[6] - closes[3]
    if prior == 0 and recent == 0:
        return "flat"
    if recent > 0 and recent > abs(prior):
        return "accelerating_up"
    if recent < 0 and abs(recent) > abs(prior):
        return "accelerating_down"
    if recent > 0:
        return "decelerating_up"
    if recent < 0:
        return "decelerating_down"
    return "flat"


def trend_regime(history: tuple[OhlcSnapshot, ...]) -> str:
    if len(history) < TREND_LOOKBACK:
        return "insufficient_history"
    recent = history[-TREND_LOOKBACK:]
    closes = [close_decimal(bar) for bar in recent]
    path = sum(
        (
            abs(current - previous)
            for previous, current in zip(closes, closes[1:], strict=False)
        ),
        Decimal(0),
    )
    if path == 0:
        return "range"
    net = closes[-1] - closes[0]
    efficiency = abs(net) / path
    if efficiency >= Decimal("0.60"):
        return "trend_up" if net > 0 else "trend_down"
    if efficiency <= Decimal("0.30"):
        return "range"
    if net > 0:
        return "mixed_up"
    if net < 0:
        return "mixed_down"
    return "mixed_flat"


def trend_family(regime: str) -> str:
    if regime.startswith("trend_"):
        return "trend"
    if regime == "range":
        return "range"
    if regime.startswith("mixed_"):
        return "mixed"
    return regime


def trend_transition(history: tuple[OhlcSnapshot, ...]) -> str:
    if len(history) < TREND_COMPARISON_LOOKBACK:
        return "insufficient_history"
    prior_history = history[-TREND_COMPARISON_LOOKBACK:-TREND_LOOKBACK]
    prior = trend_family(trend_regime(prior_history))
    current = trend_family(trend_regime(history[-TREND_LOOKBACK:]))
    if "insufficient_history" in {prior, current}:
        return "insufficient_history"
    return "transition" if prior != current else f"stable_{current}"


def volatility_ratio(history: tuple[OhlcSnapshot, ...]) -> Decimal | None:
    required = VOLATILITY_BASELINE + VOLATILITY_RECENT
    if len(history) < required:
        return None
    values = [normalized_range(bar) for bar in history[-required:]]
    baseline = mean_decimal(values[:VOLATILITY_BASELINE])
    recent = mean_decimal(values[-VOLATILITY_RECENT:])
    if baseline <= 0:
        return Decimal(1)
    return recent / baseline


def volatility_regime(history: tuple[OhlcSnapshot, ...]) -> str:
    ratio = volatility_ratio(history)
    if ratio is None:
        return "insufficient_history"
    if ratio >= Decimal("1.50"):
        return "high"
    if ratio <= Decimal("0.67"):
        return "low"
    return "normal"


def volatility_percentile(history: tuple[OhlcSnapshot, ...]) -> Decimal | None:
    if len(history) < 2:
        return None
    retained = history[-VOLATILITY_PERCENTILE_LOOKBACK:]
    values = [normalized_range(bar) for bar in retained]
    current = values[-1]
    rank = sum(value <= current for value in values)
    return Decimal(rank) * Decimal(100) / Decimal(len(values))


def percentile_bucket(percentile: Decimal | None) -> str:
    if percentile is None:
        return "insufficient_history"
    if percentile < 20:
        return "p00_20"
    if percentile < 40:
        return "p20_40"
    if percentile < 60:
        return "p40_60"
    if percentile < 80:
        return "p60_80"
    return "p80_100"


def expansion_state(history: tuple[OhlcSnapshot, ...]) -> str:
    required = EXPANSION_BASELINE + EXPANSION_RECENT
    if len(history) < required:
        return "insufficient_history"
    values = [normalized_range(bar) for bar in history[-required:]]
    baseline = mean_decimal(values[:EXPANSION_BASELINE])
    recent = mean_decimal(values[-EXPANSION_RECENT:])
    if baseline <= 0:
        return "stable"
    ratio = recent / baseline
    if ratio >= Decimal("1.25"):
        return "expansion"
    if ratio <= Decimal("0.80"):
        return "compression"
    return "stable"


def momentum_regime(history: tuple[OhlcSnapshot, ...]) -> str:
    if len(history) <= MOMENTUM_LOOKBACK:
        return "insufficient_history"
    start = close_decimal(history[-(MOMENTUM_LOOKBACK + 1)])
    end = close_decimal(history[-1])
    if start <= 0:
        return "flat"
    move = (end - start) / start
    reference = mean_decimal([normalized_range(bar) for bar in history[-20:]])
    threshold = reference * Decimal("1.50")
    if abs(move) < threshold:
        return "flat"
    return "up" if move > 0 else "down"


def range_position(history: tuple[OhlcSnapshot, ...]) -> str:
    if len(history) < RANGE_LOOKBACK:
        return "insufficient_history"
    recent = history[-RANGE_LOOKBACK:]
    high = max(Decimal(str(bar.high)) for bar in recent)
    low = min(Decimal(str(bar.low)) for bar in recent)
    width = high - low
    if width <= 0:
        return "middle_third"
    location = (close_decimal(recent[-1]) - low) / width
    if location <= Decimal("0.33"):
        return "lower_third"
    if location >= Decimal("0.67"):
        return "upper_third"
    return "middle_third"


def cross_timeframe_alignment(execution_regime: str, context_regime: str) -> str:
    if "insufficient_history" in {execution_regime, context_regime}:
        return "insufficient_history"
    if execution_regime.endswith("_up"):
        execution_direction = "up"
    elif execution_regime.endswith("_down"):
        execution_direction = "down"
    else:
        execution_direction = "neutral"
    if context_regime.endswith("_up"):
        context_direction = "up"
    elif context_regime.endswith("_down"):
        context_direction = "down"
    else:
        context_direction = "neutral"
    if execution_direction == "neutral" or context_direction == "neutral":
        return "neutral"
    return "aligned" if execution_direction == context_direction else "divergent"


def session_context(at: datetime) -> tuple[str, bool]:
    if at.tzinfo is None or at.utcoffset() is None:
        raise ConditionalMarketStateFeatureError(
            "session timestamp must be timezone-aware"
        )
    london_hour = at.astimezone(_LONDON).hour
    new_york_hour = at.astimezone(_NEW_YORK).hour
    tokyo_hour = at.astimezone(_TOKYO).hour
    active: list[str] = []
    if 8 <= london_hour < 17:
        active.append("london")
    if 8 <= new_york_hour < 17:
        active.append("new_york")
    if 9 <= tokyo_hour < 17:
        active.append("tokyo")
    if not active:
        return "off_major_sessions", False
    if len(active) == 1:
        return active[0], False
    return "+".join(active), True


def market_state(
    history: tuple[OhlcSnapshot, ...],
    *,
    context_history: tuple[OhlcSnapshot, ...],
    as_of: datetime,
    execution_period: str,
) -> dict[str, object]:
    session, overlap = session_context(as_of)
    percentile = volatility_percentile(history)
    ratio = volatility_ratio(history)
    efficiency = trend_efficiency(history)
    realized_range = recent_realized_range(history)
    range_width = range_width_fraction(history)
    execution_trend = trend_regime(history)
    context_trend = trend_regime(context_history)
    return {
        "as_of_utc": as_of.astimezone(UTC).isoformat(),
        "execution_period": execution_period,
        "hour_utc": f"{as_of.astimezone(UTC).hour:02d}",
        "weekday_utc": str(as_of.astimezone(UTC).weekday()),
        "session_context": session,
        "session_overlap": overlap,
        "trend_regime": execution_trend,
        "trend_efficiency": None if efficiency is None else format(efficiency, "f"),
        "trend_transition": trend_transition(history),
        "volatility_regime": volatility_regime(history),
        "volatility_ratio": None if ratio is None else format(ratio, "f"),
        "volatility_percentile": (
            None if percentile is None else format(percentile, "f")
        ),
        "volatility_percentile_bucket": percentile_bucket(percentile),
        "recent_realized_range_fraction": (
            None if realized_range is None else format(realized_range, "f")
        ),
        "expansion_state": expansion_state(history),
        "momentum_regime": momentum_regime(history),
        "momentum_acceleration": momentum_acceleration(history),
        "range_position": range_position(history),
        "range_width_fraction": (
            None if range_width is None else format(range_width, "f")
        ),
        "gap_state": gap_state(history),
        "higher_timeframe_period": "H4",
        "higher_timeframe_closed_bar_count": len(context_history),
        "higher_timeframe_trend_regime": context_trend,
        "higher_timeframe_volatility_regime": volatility_regime(context_history),
        "cross_timeframe_alignment": cross_timeframe_alignment(
            execution_trend, context_trend
        ),
        "available_closed_bar_count": len(history),
        "classifier_version": CLASSIFIER_VERSION,
        "available_at_only": True,
    }


def contiguous_forward(
    execution: tuple[OhlcSnapshot, ...], signal_index: int
) -> tuple[OhlcSnapshot, ...]:
    if signal_index < 0 or signal_index >= len(execution):
        raise ConditionalMarketStateFeatureError(
            "signal index outside execution evidence"
        )
    rows: list[OhlcSnapshot] = []
    prior = execution[signal_index]
    last = min(signal_index + _MAX_HOLD_BARS, len(execution) - 1)
    for index in range(signal_index + 1, last + 1):
        bar = execution[index]
        if bar.opened_at != prior.closed_at:
            break
        rows.append(bar)
        prior = bar
    return tuple(rows)


def forward_path_evaluation(
    execution: tuple[OhlcSnapshot, ...], signal_index: int
) -> dict[str, object]:
    signal = execution[signal_index]
    reference = close_decimal(signal)
    forward = contiguous_forward(execution, signal_index)
    if reference <= 0 or not forward:
        return {
            "policy_id": FORWARD_PATH_POLICY,
            "forward_bar_count": len(forward),
            "max_up_fraction": "0",
            "max_down_fraction": "0",
        }
    max_high = max(Decimal(str(bar.high)) for bar in forward)
    min_low = min(Decimal(str(bar.low)) for bar in forward)
    return {
        "policy_id": FORWARD_PATH_POLICY,
        "forward_bar_count": len(forward),
        "max_up_fraction": format(
            max((max_high - reference) / reference, Decimal(0)), "f"
        ),
        "max_down_fraction": format(
            max((reference - min_low) / reference, Decimal(0)), "f"
        ),
    }


def trade_excursions(
    trade: FirstCohortBacktestTrade,
    execution: tuple[OhlcSnapshot, ...],
    closed_index: dict[datetime, int],
) -> tuple[Decimal, Decimal]:
    fill_index = closed_index.get(trade.filled_at)
    exit_index = closed_index.get(trade.exited_at)
    if fill_index is None or exit_index is None or exit_index < fill_index:
        return Decimal(0), Decimal(0)
    path = execution[fill_index : exit_index + 1]
    if not path:
        return Decimal(0), Decimal(0)
    entry = trade.entry_price
    if trade.side is DemoTradingSetupSide.LONG:
        favorable = max(
            (Decimal(str(bar.high)) - entry for bar in path), default=Decimal(0)
        )
        adverse = max(
            (entry - Decimal(str(bar.low)) for bar in path), default=Decimal(0)
        )
    else:
        favorable = max(
            (entry - Decimal(str(bar.low)) for bar in path), default=Decimal(0)
        )
        adverse = max(
            (Decimal(str(bar.high)) - entry for bar in path), default=Decimal(0)
        )
    if entry <= 0:
        return Decimal(0), Decimal(0)
    return max(favorable / entry, Decimal(0)), max(adverse / entry, Decimal(0))


def event_fingerprint(
    *,
    trader_code: str,
    symbol: str,
    software_sha: str,
    decision_at: datetime,
    execution_period: str,
) -> str:
    payload = {
        "trader_code": trader_code,
        "symbol": symbol,
        "software_sha": software_sha,
        "decision_at": decision_at.astimezone(UTC).isoformat(),
        "execution_period": execution_period,
        "classifier_version": CLASSIFIER_VERSION,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()
