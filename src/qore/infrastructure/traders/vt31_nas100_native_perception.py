"""Native causal perception for every VT31_NAS100 decision timestamp.

Unlike a specialist-entry match, this perception can be reconstructed for any
archived VT31 opportunity as long as causal NAS100 M1 bars exist through the
decision timestamp. It uses no outcome, no future bar and no external AI.

The output is a complete read-only situation surface for CIBO intelligence.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal
from statistics import median
from zoneinfo import ZoneInfo

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.market_data import OhlcSnapshot
from qore.infrastructure.traders.vt31_nas100_cibo_market_memory import (
    cibo_market_memory_fingerprint,
)
from qore.infrastructure.traders.vt31_nas100_cognitive_memory import (
    memory_fingerprint,
)
from qore.infrastructure.traders.vt31_nas100_market_context_runtime import (
    build_higher_context,
)
from qore.infrastructure.traders.vt31_nas100_strategy_identity_memory import (
    strategy_identity_fingerprint,
)
from qore.infrastructure.traders.vt31_nas100_trader_experience_memory import (
    trader_experience_fingerprint,
)

_NY = ZoneInfo("America/New_York")
_VERSION = "vt31-nas100-native-causal-perception-v1"


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _wall(value: datetime) -> tuple[int, int, int]:
    local = value.astimezone(_NY)
    return local.hour, local.minute, local.second


def _slice(
    bars: Sequence[OhlcSnapshot],
    start: tuple[int, int, int],
    end: tuple[int, int, int],
    *,
    decision_at: datetime | None = None,
) -> tuple[OhlcSnapshot, ...]:
    return tuple(
        bar
        for bar in bars
        if start <= _wall(bar.opened_at) < end
        and (decision_at is None or bar.closed_at <= decision_at)
    )


def _range(bars: Sequence[OhlcSnapshot]) -> Decimal | None:
    if not bars:
        return None
    return max(_d(bar.high) for bar in bars) - min(
        _d(bar.low) for bar in bars
    )


def _fmt(value: Decimal | None) -> str:
    return "unavailable" if value is None else format(value, "f")


def _direction(bars: Sequence[OhlcSnapshot]) -> str:
    if not bars:
        return "unavailable"
    opened = _d(bars[0].open)
    closed = _d(bars[-1].close)
    if closed > opened:
        return "bullish"
    if closed < opened:
        return "bearish"
    return "flat"


def _reference_reclaim_age(
    session: Sequence[OhlcSnapshot],
    *,
    decision_at: datetime,
    side: str,
    reference_high: Decimal,
    reference_low: Decimal,
) -> int | None:
    reclaimed_at: datetime | None = None
    for bar in session:
        if bar.closed_at > decision_at:
            break
        high = _d(bar.high)
        low = _d(bar.low)
        close = _d(bar.close)
        if side == "short" and high > reference_high and close < reference_high:
            reclaimed_at = bar.closed_at
        elif side == "long" and low < reference_low and close > reference_low:
            reclaimed_at = bar.closed_at
    if reclaimed_at is None:
        return None
    return max(
        0,
        int((decision_at - reclaimed_at).total_seconds() // 60),
    )


def _local_sweep_state(
    bars: Sequence[OhlcSnapshot],
    *,
    decision_at: datetime,
) -> tuple[str, int | None]:
    causal = tuple(bar for bar in bars if bar.closed_at <= decision_at)
    if len(causal) < 7:
        return "none", None

    swing_highs: list[tuple[int, Decimal]] = []
    swing_lows: list[tuple[int, Decimal]] = []
    for index in range(2, len(causal) - 2):
        high = _d(causal[index].high)
        low = _d(causal[index].low)
        if (
            high >= max(_d(causal[index - 2].high), _d(causal[index - 1].high))
            and high > max(_d(causal[index + 1].high), _d(causal[index + 2].high))
        ):
            swing_highs.append((index, high))
        if (
            low <= min(_d(causal[index - 2].low), _d(causal[index - 1].low))
            and low < min(_d(causal[index + 1].low), _d(causal[index + 2].low))
        ):
            swing_lows.append((index, low))

    last_event: tuple[datetime, str] | None = None
    for index, bar in enumerate(causal):
        high = _d(bar.high)
        low = _d(bar.low)
        close = _d(bar.close)
        prior_highs = [item for item in swing_highs if item[0] <= index - 2]
        prior_lows = [item for item in swing_lows if item[0] <= index - 2]
        if prior_highs:
            level = prior_highs[-1][1]
            if high > level and close < level:
                last_event = (bar.closed_at, "local-high-sweep-reclaim")
        if prior_lows:
            level = prior_lows[-1][1]
            if low < level and close > level:
                last_event = (bar.closed_at, "local-low-sweep-reclaim")
    if last_event is None:
        return "none", None
    return (
        last_event[1],
        max(0, int((decision_at - last_event[0]).total_seconds() // 60)),
    )


def _prior_reference_widths(
    prior_admitted_days: Sequence[Sequence[OhlcSnapshot]],
) -> tuple[Decimal, ...]:
    widths: list[Decimal] = []
    for bars in prior_admitted_days:
        reference = _slice(bars, (9, 0, 0), (10, 0, 0))
        if len(reference) != 60:
            continue
        width = _range(reference)
        if width is not None and width > 0:
            widths.append(width)
    return tuple(widths[-5:])


def build_vt31_native_causal_perception(
    *,
    day_bars: Sequence[OhlcSnapshot],
    prior_admitted_day_bars: Sequence[OhlcSnapshot],
    prior_admitted_days: Sequence[Sequence[OhlcSnapshot]],
    decision_at: datetime,
    side: str,
    intended_entry: Decimal,
    stop_loss: Decimal,
    take_profit: Decimal,
) -> tuple[tuple[str, str], ...]:
    """Build full VT31 CIBO perception from closed M1 only."""

    if decision_at.tzinfo is None or decision_at.utcoffset() is None:
        raise CiboCapitalManagementError(
            "VT31 native perception decision_at must be timezone-aware"
        )
    if side not in {"long", "short"}:
        raise CiboCapitalManagementError(
            "VT31 native perception side must be long/short"
        )
    causal_day = tuple(
        bar for bar in day_bars if bar.closed_at <= decision_at
    )
    if not causal_day:
        raise CiboCapitalManagementError(
            "VT31 native perception requires causal M1 bars"
        )
    if any(bar.closed_at > decision_at for bar in causal_day):
        raise CiboCapitalManagementError(
            "VT31 native perception admitted a future bar"
        )

    reference = _slice(
        causal_day,
        (9, 0, 0),
        (10, 0, 0),
        decision_at=decision_at,
    )
    if len(reference) != 60:
        raise CiboCapitalManagementError(
            "VT31 native perception requires complete frozen 09:00 reference"
        )
    reference_high = max(_d(bar.high) for bar in reference)
    reference_low = min(_d(bar.low) for bar in reference)
    reference_width = reference_high - reference_low
    if reference_width <= 0:
        raise CiboCapitalManagementError(
            "VT31 native perception reference width must be positive"
        )

    session = _slice(
        causal_day,
        (10, 0, 0),
        (11, 0, 0),
        decision_at=decision_at,
    )
    current_path = _slice(
        causal_day,
        (0, 0, 0),
        (16, 0, 0),
        decision_at=decision_at,
    )
    current_path_range = _range(current_path)

    prior_path = _slice(
        prior_admitted_day_bars,
        (0, 0, 0),
        (16, 0, 0),
    )
    previous_path_range = _range(prior_path)
    path_ratio = (
        current_path_range / previous_path_range
        if current_path_range is not None
        and previous_path_range is not None
        and previous_path_range > 0
        else None
    )

    prior_widths = _prior_reference_widths(prior_admitted_days)
    prior5_median = median(prior_widths) if prior_widths else None
    ref_ratio = (
        reference_width / prior5_median
        if prior5_median is not None and prior5_median > 0
        else None
    )
    ref_volatility = (
        "unavailable"
        if ref_ratio is None
        else (
            "compressed"
            if ref_ratio < Decimal("0.75")
            else "normal"
            if ref_ratio <= Decimal("1.25")
            else "expanded"
        )
    )
    range_state = (
        "unavailable"
        if path_ratio is None
        else (
            "compressed"
            if path_ratio < Decimal("0.75")
            else "normal"
            if path_ratio <= Decimal("1.25")
            else "expanded"
        )
    )

    higher = build_higher_context(
        day_bars=causal_day,
        prior_admitted_day_bars=prior_admitted_day_bars,
        decision_at=decision_at,
        side=side,
        reference_high=reference_high,
        reference_low=reference_low,
    )

    reclaim_age = _reference_reclaim_age(
        session,
        decision_at=decision_at,
        side=side,
        reference_high=reference_high,
        reference_low=reference_low,
    )
    local_event, local_age = _local_sweep_state(
        session,
        decision_at=decision_at,
    )
    risk = (
        intended_entry - stop_loss
        if side == "long"
        else stop_loss - intended_entry
    )
    reward = (
        take_profit - intended_entry
        if side == "long"
        else intended_entry - take_profit
    )
    if risk <= 0 or reward <= 0:
        raise CiboCapitalManagementError(
            "VT31 native perception requires positive risk/reward geometry"
        )
    planned_r = reward / risk
    destination_ref = reward / reference_width

    local = decision_at.astimezone(_NY)
    values = {
        "cibo_native_perception_complete": "true",
        "cibo_native_perception_version": _VERSION,
        "source_context_causal": "true",
        "market": "NAS100",
        "timeframe": "M1",
        "session": "NY_AM_SILVER_BULLET",
        "decision_at": decision_at.isoformat(),
        "decision_minute_ny": str(local.hour * 60 + local.minute),
        "weekday": local.strftime("%A"),
        "side": side,
        "reference_high": format(reference_high, "f"),
        "reference_low": format(reference_low, "f"),
        "reference_width": format(reference_width, "f"),
        "reference_direction": _direction(reference),
        "prior5_reference_width_median": _fmt(prior5_median),
        "reference_width_vs_prior5": _fmt(ref_ratio),
        "reference_volatility_state": ref_volatility,
        "previous_admitted_path_range": _fmt(previous_path_range),
        "current_path_range": _fmt(current_path_range),
        "current_path_vs_previous": _fmt(path_ratio),
        "current_range_state": range_state,
        "prior_day_state": higher.prior_day_state,
        "prior_day_body_fraction": _fmt(higher.prior_day_body_fraction),
        "h4_state": higher.h4_state,
        "h1_state": higher.h1_state,
        "premarket_state": higher.premarket_state,
        "cash_open_state": higher.cash_open_state,
        "position_in_prior_day_range": higher.position_in_prior_day_range,
        "raid_depth_ref": _fmt(higher.raid_depth_ref),
        "recent_path_efficiency": _fmt(higher.recent_path_efficiency),
        "recent_overlap_rate": _fmt(higher.recent_overlap_rate),
        "reference_reclaim_age_minutes": (
            "none" if reclaim_age is None else str(reclaim_age)
        ),
        "local_structure_event": local_event,
        "local_structure_event_age_minutes": (
            "none" if local_age is None else str(local_age)
        ),
        "intended_entry": format(intended_entry, "f"),
        "stop_loss": format(stop_loss, "f"),
        "take_profit": format(take_profit, "f"),
        "risk_distance": format(risk, "f"),
        "target_distance": format(reward, "f"),
        "planned_target_r": format(planned_r, "f"),
        "destination_distance_ref": format(destination_ref, "f"),
        "journey_stage": "PREDECISION",
        "strategy_memory_fingerprint": strategy_identity_fingerprint(),
        "cibo_market_memory_fingerprint": cibo_market_memory_fingerprint(),
        "trader_experience_memory_fingerprint": trader_experience_fingerprint(),
        "cognitive_memory_fingerprint": memory_fingerprint(),
        "future_bar_lookup": "false",
        "date_level_outcome_lookup": "false",
        "external_ai_dependency": "false",
    }
    return tuple(sorted(values.items()))
