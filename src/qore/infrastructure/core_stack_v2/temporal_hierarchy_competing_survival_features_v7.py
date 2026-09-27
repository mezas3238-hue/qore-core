"""Source-time feature extraction for WP-05 V7.

The extractor implements the preregistered causal geometry:
- exact source distance uses the Target-V2 prior20 INCLUDING the source bar;
- historical breach/reclaim dynamics use rolling frontiers from the 20 bars
  STRICTLY PRECEDING each evaluated bar;
- no bar after the source index is read;
- one fixed Target-V2 anchor interprets the whole hierarchy trajectory.

The output is authority-free cognition for the dual V7 mechanism model.
"""

from __future__ import annotations

from statistics import fmean
from typing import Protocol, Sequence

from qore.infrastructure.core_stack_v2.hierarchical_world_model import WorldScale
from qore.infrastructure.core_stack_v2.temporal_hierarchy_competing_survival_v7 import (
    CompetingSurvivalSourceState,
    RECOVERY_FEATURE_NAMES,
    TERMINAL_FEATURE_NAMES,
)
from qore.infrastructure.core_stack_v2.temporal_hierarchy_engine import (
    TemporalHierarchySnapshot,
)
from qore.infrastructure.core_stack_v2.temporal_hierarchy_transition_v2 import (
    TemporalHierarchyTrajectory,
)


class MarketBarLike(Protocol):
    opened: float
    high: float
    low: float
    close: float


_HIERARCHY_SCALES = (
    WorldScale.M1,
    WorldScale.M3,
    WorldScale.M5,
    WorldScale.M15,
    WorldScale.H1,
    WorldScale.H4,
    WorldScale.DAILY,
)


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _safe_range(bars: Sequence[MarketBarLike]) -> float:
    return max(1e-9, fmean(max(0.0, bar.high - bar.low) for bar in bars))


def _frontier(
    bars: Sequence[MarketBarLike],
    *,
    anchor_direction: int,
) -> tuple[float, float, float]:
    if not bars:
        raise ValueError("frontier requires bars")
    floor = min(bar.low for bar in bars)
    peak = max(bar.high for bar in bars)
    scale = _safe_range(bars)
    frontier = floor if anchor_direction > 0 else peak
    return frontier, scale, peak - floor


def _distance(
    *,
    bar: MarketBarLike,
    frontier: float,
    scale: float,
    anchor_direction: int,
) -> float:
    return (
        (bar.close - frontier) / scale
        if anchor_direction > 0
        else (frontier - bar.close) / scale
    )


def _breach_depth(
    *,
    bar: MarketBarLike,
    frontier: float,
    scale: float,
    anchor_direction: int,
) -> float:
    if anchor_direction > 0:
        return max(0.0, (frontier - bar.low) / scale)
    return max(0.0, (bar.high - frontier) / scale)


def _close_breached(
    *,
    bar: MarketBarLike,
    frontier: float,
    anchor_direction: int,
) -> bool:
    return (
        bar.close < frontier
        if anchor_direction > 0
        else bar.close > frontier
    )


def _touched(
    *,
    bar: MarketBarLike,
    frontier: float,
    anchor_direction: int,
) -> bool:
    return (
        bar.low <= frontier
        if anchor_direction > 0
        else bar.high >= frontier
    )


def _causal_point(
    bars: Sequence[MarketBarLike],
    *,
    index: int,
    anchor_direction: int,
) -> tuple[float, float, bool, bool, float]:
    if index < 20:
        raise ValueError("causal frontier requires 20 strictly prior bars")
    prior = bars[index - 20 : index]
    if len(prior) != 20:
        raise ValueError("causal frontier history is incomplete")
    frontier, scale, _ = _frontier(prior, anchor_direction=anchor_direction)
    bar = bars[index]
    return (
        _distance(
            bar=bar,
            frontier=frontier,
            scale=scale,
            anchor_direction=anchor_direction,
        ),
        _breach_depth(
            bar=bar,
            frontier=frontier,
            scale=scale,
            anchor_direction=anchor_direction,
        ),
        _close_breached(
            bar=bar,
            frontier=frontier,
            anchor_direction=anchor_direction,
        ),
        _touched(
            bar=bar,
            frontier=frontier,
            anchor_direction=anchor_direction,
        ),
        scale,
    )


def _adverse_return(
    bars: Sequence[MarketBarLike],
    *,
    index: int,
    horizon: int,
    anchor_direction: int,
) -> float:
    if index < horizon:
        raise ValueError("return horizon history is incomplete")
    first = bars[index - horizon].close
    last = bars[index].close
    if first == 0:
        return 0.0
    raw_bps = (last / first - 1.0) * 10_000.0
    return _clamp(-anchor_direction * raw_bps / 100.0, -5.0, 5.0)


def _move_persistence(
    bars: Sequence[MarketBarLike],
    *,
    index: int,
    horizon: int,
    anchor_direction: int,
) -> tuple[float, float]:
    if index < horizon:
        raise ValueError("persistence horizon history is incomplete")
    rows = bars[index - horizon : index + 1]
    adverse = 0
    favorable = 0
    for left, right in zip(rows, rows[1:], strict=False):
        signed = anchor_direction * (right.close - left.close)
        adverse += int(signed < 0)
        favorable += int(signed > 0)
    denominator = max(1, len(rows) - 1)
    return adverse / denominator, favorable / denominator


def _consecutive_moves(
    bars: Sequence[MarketBarLike],
    *,
    index: int,
    anchor_direction: int,
) -> tuple[int, int]:
    adverse = 0
    favorable = 0
    for right_index in range(index, max(0, index - 30), -1):
        left_index = right_index - 1
        if left_index < 0:
            break
        signed = anchor_direction * (
            bars[right_index].close - bars[left_index].close
        )
        if signed < 0 and favorable == 0:
            adverse += 1
        elif signed > 0 and adverse == 0:
            favorable += 1
        else:
            break
    return adverse, favorable


def _rejection_fraction(
    bars: Sequence[MarketBarLike],
    *,
    index: int,
    horizon: int,
    anchor_direction: int,
) -> float:
    rows = bars[index - horizon + 1 : index + 1]
    fractions = []
    for bar in rows:
        span = max(1e-9, bar.high - bar.low)
        if anchor_direction > 0:
            wick = min(bar.opened, bar.close) - bar.low
        else:
            wick = bar.high - max(bar.opened, bar.close)
        fractions.append(_clamp(wick / span, 0.0, 1.0))
    return fmean(fractions) if fractions else 0.0


def _snapshot_levels(
    snapshot: TemporalHierarchySnapshot,
) -> dict[WorldScale, object]:
    return {item.scale: item for item in snapshot.levels}


def _depth(snapshot: TemporalHierarchySnapshot, anchor_direction: int) -> int:
    levels = _snapshot_levels(snapshot)
    depth = 0
    for ordinal, scale in enumerate(_HIERARCHY_SCALES, start=1):
        level = levels.get(scale)
        if level is not None and anchor_direction * level.direction_milli < 0:
            depth = ordinal
    return depth


def _higher_resilience_minus_fragility(
    snapshot: TemporalHierarchySnapshot,
) -> float:
    levels = _snapshot_levels(snapshot)
    rows = [
        levels[scale]
        for scale in (WorldScale.H1, WorldScale.H4, WorldScale.DAILY)
        if scale in levels
    ]
    if not rows:
        return 0.0
    return fmean(
        (
            item.persistence_bps
            + item.coherence_bps
            - item.fragility_bps
            - item.transition_bps
        )
        / 20_000.0
        for item in rows
    )


def _higher_transition(snapshot: TemporalHierarchySnapshot) -> float:
    levels = _snapshot_levels(snapshot)
    rows = [
        levels[scale]
        for scale in (WorldScale.H1, WorldScale.H4, WorldScale.DAILY)
        if scale in levels
    ]
    return (
        0.0
        if not rows
        else fmean(item.transition_bps / 10_000.0 for item in rows)
    )


def _higher_coherence(snapshot: TemporalHierarchySnapshot) -> float:
    levels = _snapshot_levels(snapshot)
    rows = [
        levels[scale]
        for scale in (WorldScale.H1, WorldScale.H4, WorldScale.DAILY)
        if scale in levels
    ]
    return (
        0.0
        if not rows
        else fmean(item.coherence_bps / 10_000.0 for item in rows)
    )


def _snapshot_at_or_before(
    trajectory: TemporalHierarchyTrajectory,
    minutes_before_source: int,
) -> TemporalHierarchySnapshot:
    source = trajectory.snapshots[-1]
    target_seconds = minutes_before_source * 60
    candidates = [
        item
        for item in trajectory.snapshots
        if 0
        <= (source.as_of - item.as_of).total_seconds()
        <= target_seconds + 10 * 60
    ]
    if not candidates:
        return trajectory.snapshots[0]
    return min(
        candidates,
        key=lambda item: abs(
            (source.as_of - item.as_of).total_seconds() - target_seconds
        ),
    )


def _hierarchy_features(
    trajectory: TemporalHierarchyTrajectory,
    *,
    anchor_direction: int,
) -> dict[str, float]:
    if anchor_direction not in (-1, 1):
        raise ValueError("V7 hierarchy features require identifiable anchor")
    current = trajectory.snapshots[-1]
    at15 = _snapshot_at_or_before(trajectory, 15)
    at30 = _snapshot_at_or_before(trajectory, 30)
    depths = tuple(_depth(item, anchor_direction) for item in trajectory.snapshots)
    recession = sum(
        right < left for left, right in zip(depths, depths[1:], strict=False)
    )
    advance = sum(
        right > left for left, right in zip(depths, depths[1:], strict=False)
    )
    current_resilience = _higher_resilience_minus_fragility(current)
    return {
        "HIERARCHY_DEPTH": depths[-1] / len(_HIERARCHY_SCALES),
        "HIERARCHY_DEPTH_VELOCITY": (
            depths[-1] - _depth(at15, anchor_direction)
        )
        / len(_HIERARCHY_SCALES),
        "HIERARCHY_RECESSION_COUNT": float(recession),
        "HIERARCHY_ADVANCE_COUNT": float(advance),
        "HIGHER_RESILIENCE_MINUS_FRAGILITY": current_resilience,
        "HIGHER_FRAGILITY_MINUS_RESILIENCE": -current_resilience,
        "HIGHER_RESILIENCE_DELTA_15M": (
            current_resilience - _higher_resilience_minus_fragility(at15)
        ),
        "HIGHER_RESILIENCE_DELTA_30M": (
            current_resilience - _higher_resilience_minus_fragility(at30)
        ),
        "TRANSITION_PRESSURE_DELTA_15M": (
            _higher_transition(current) - _higher_transition(at15)
        ),
        "TRANSITION_PRESSURE_DELTA_30M": (
            _higher_transition(current) - _higher_transition(at30)
        ),
        "COHERENCE_DELTA_15M": (
            _higher_coherence(current) - _higher_coherence(at15)
        ),
        "COHERENCE_DELTA_30M": (
            _higher_coherence(current) - _higher_coherence(at30)
        ),
    }


def _zero_state(
    *,
    trajectory: TemporalHierarchyTrajectory,
    anchor_direction: int,
) -> CompetingSurvivalSourceState:
    return CompetingSurvivalSourceState(
        episode_id=trajectory.episode_id,
        as_of=trajectory.snapshots[-1].as_of,
        anchor_direction=anchor_direction,
        terminal_features=(0.0,) * len(TERMINAL_FEATURE_NAMES),
        recovery_features=(0.0,) * len(RECOVERY_FEATURE_NAMES),
        evidence_complete=False,
    )


def build_competing_survival_source_state(
    *,
    trajectory: TemporalHierarchyTrajectory,
    anchor_direction: int,
    nas_bars: Sequence[MarketBarLike],
    nas_index: int,
    sp500_bars: Sequence[MarketBarLike],
    sp500_index: int,
    us30_bars: Sequence[MarketBarLike],
    us30_index: int,
) -> CompetingSurvivalSourceState:
    """Build one causal V7 source state without reading bars after source."""

    if anchor_direction not in (-1, 1):
        raise ValueError("V7 source builder requires identifiable anchor")
    if len(trajectory.snapshots) < 3:
        return _zero_state(
            trajectory=trajectory,
            anchor_direction=anchor_direction,
        )
    required = (
        nas_index >= 60
        and sp500_index >= 30
        and us30_index >= 30
        and nas_index < len(nas_bars)
        and sp500_index < len(sp500_bars)
        and us30_index < len(us30_bars)
    )
    if not required:
        return _zero_state(
            trajectory=trajectory,
            anchor_direction=anchor_direction,
        )

    source_prior20 = nas_bars[nas_index - 19 : nas_index + 1]
    if len(source_prior20) != 20:
        return _zero_state(
            trajectory=trajectory,
            anchor_direction=anchor_direction,
        )
    source_frontier, source_scale, _ = _frontier(
        source_prior20,
        anchor_direction=anchor_direction,
    )
    distance_now = _distance(
        bar=nas_bars[nas_index],
        frontier=source_frontier,
        scale=source_scale,
        anchor_direction=anchor_direction,
    )

    points = {
        offset: _causal_point(
            nas_bars,
            index=nas_index - offset,
            anchor_direction=anchor_direction,
        )
        for offset in (0, 1, 5, 15, 30)
    }
    causal_now = points[0][0]
    approach_1m = points[1][0] - causal_now
    approach_5m = points[5][0] - causal_now
    approach_15m = points[15][0] - causal_now
    acceleration_5m = approach_1m - approach_5m / 5.0
    acceleration_15m = approach_5m / 5.0 - approach_15m / 15.0

    path = [
        _causal_point(
            nas_bars,
            index=index,
            anchor_direction=anchor_direction,
        )
        for index in range(nas_index - 29, nas_index + 1)
    ]
    breach_depth = max(item[1] for item in path)
    touches_15 = sum(item[3] for item in path[-15:])
    touches_30 = sum(item[3] for item in path)
    breach_flags = [item[2] for item in path]
    transitions_15 = sum(
        left != right
        for left, right in zip(breach_flags[-15:], breach_flags[-14:], strict=False)
    )
    transitions_30 = sum(
        left != right
        for left, right in zip(breach_flags, breach_flags[1:], strict=False)
    )
    acceptance_duration = 0
    for breached in reversed(breach_flags):
        if not breached:
            break
        acceptance_duration += 1
    breach_indexes = [
        index for index, (_, depth, _, _, _) in enumerate(path) if depth > 0
    ]
    reclaim_distance = 0.0
    if breach_indexes:
        reclaim_distance = max(
            0.0,
            causal_now - path[breach_indexes[-1]][0],
        )

    adverse5, favorable5 = _move_persistence(
        nas_bars,
        index=nas_index,
        horizon=5,
        anchor_direction=anchor_direction,
    )
    adverse15, favorable15 = _move_persistence(
        nas_bars,
        index=nas_index,
        horizon=15,
        anchor_direction=anchor_direction,
    )
    consecutive_adverse, consecutive_favorable = _consecutive_moves(
        nas_bars,
        index=nas_index,
        anchor_direction=anchor_direction,
    )
    rejection5 = _rejection_fraction(
        nas_bars,
        index=nas_index,
        horizon=5,
        anchor_direction=anchor_direction,
    )
    rejection15 = _rejection_fraction(
        nas_bars,
        index=nas_index,
        horizon=15,
        anchor_direction=anchor_direction,
    )
    current_bar = nas_bars[nas_index]
    current_span = max(1e-9, current_bar.high - current_bar.low)
    close_location_recovery = (
        (current_bar.close - current_bar.low) / current_span
        if anchor_direction > 0
        else (current_bar.high - current_bar.close) / current_span
    )

    recent30 = nas_bars[nas_index - 29 : nas_index + 1]
    if anchor_direction > 0:
        worst_offset = min(
            range(len(recent30)),
            key=lambda index: recent30[index].low,
        )
        worst_price = recent30[worst_offset].low
        recovery_move = current_bar.close - worst_price
    else:
        worst_offset = max(
            range(len(recent30)),
            key=lambda index: recent30[index].high,
        )
        worst_price = recent30[worst_offset].high
        recovery_move = worst_price - current_bar.close
    time_since_worst = len(recent30) - 1 - worst_offset
    recovery_velocity = recovery_move / max(
        source_scale,
        float(max(1, time_since_worst)),
    )

    range1 = max(1e-9, current_bar.high - current_bar.low)
    range5 = _safe_range(nas_bars[nas_index - 4 : nas_index + 1])
    range20 = _safe_range(nas_bars[nas_index - 19 : nas_index + 1])
    range60 = _safe_range(nas_bars[nas_index - 59 : nas_index + 1])
    range_ratio_1m_5m = range1 / range5
    range_ratio_5m_20m = range5 / range20
    volatility_transition = range5 / range20 - range20 / range60
    adverse_move = max(
        0.0,
        -anchor_direction
        * (current_bar.close - nas_bars[nas_index - 15].close)
        / max(1e-9, range20),
    )
    normalized_recovery = max(0.0, recovery_move / max(1e-9, range20))

    peer_series = (
        (sp500_bars, sp500_index),
        (us30_bars, us30_index),
    )
    peer_adverse = {
        horizon: fmean(
            _adverse_return(
                bars,
                index=index,
                horizon=horizon,
                anchor_direction=anchor_direction,
            )
            for bars, index in peer_series
        )
        for horizon in (1, 5, 15)
    }
    peer_accel5 = peer_adverse[1] - peer_adverse[5] / 5.0
    peer_accel15 = peer_adverse[5] / 5.0 - peer_adverse[15] / 15.0
    peer_breadth = fmean(
        float(
            _adverse_return(
                bars,
                index=index,
                horizon=5,
                anchor_direction=anchor_direction,
            )
            > 0
        )
        for bars, index in peer_series
    )
    peer_contradiction = fmean(
        max(
            0.0,
            -_adverse_return(
                bars,
                index=index,
                horizon=5,
                anchor_direction=anchor_direction,
            ),
        )
        for bars, index in peer_series
    )
    peer_recovery_velocity = fmean(
        max(
            0.0,
            -_adverse_return(
                bars,
                index=index,
                horizon=1,
                anchor_direction=anchor_direction,
            )
            + _adverse_return(
                bars,
                index=index,
                horizon=5,
                anchor_direction=anchor_direction,
            )
            / 5.0,
        )
        for bars, index in peer_series
    )
    signs = []
    for horizon in (1, 5, 15):
        nas_adverse = _adverse_return(
            nas_bars,
            index=nas_index,
            horizon=horizon,
            anchor_direction=anchor_direction,
        )
        for bars, index in peer_series:
            peer = _adverse_return(
                bars,
                index=index,
                horizon=horizon,
                anchor_direction=anchor_direction,
            )
            signs.append(float((nas_adverse >= 0) == (peer >= 0)))
    lead_lag_consistency = fmean(signs)

    hierarchy = _hierarchy_features(
        trajectory,
        anchor_direction=anchor_direction,
    )
    terminal_map = {
        "DISTANCE_NOW": distance_now,
        "DISTANCE_1M": points[1][0],
        "DISTANCE_5M": points[5][0],
        "DISTANCE_15M": points[15][0],
        "DISTANCE_30M": points[30][0],
        "APPROACH_1M": approach_1m,
        "APPROACH_5M": approach_5m,
        "APPROACH_15M": approach_15m,
        "ACCELERATION_5M": acceleration_5m,
        "ACCELERATION_15M": acceleration_15m,
        "BREACH_DEPTH": breach_depth,
        "ACCEPTANCE_DURATION": float(acceptance_duration),
        "ADVERSE_PERSISTENCE_5M": adverse5,
        "ADVERSE_PERSISTENCE_15M": adverse15,
        "CONSECUTIVE_ADVERSE_CLOSES": float(consecutive_adverse),
        "HIERARCHY_DEPTH": hierarchy["HIERARCHY_DEPTH"],
        "HIERARCHY_DEPTH_VELOCITY": hierarchy["HIERARCHY_DEPTH_VELOCITY"],
        "HIGHER_FRAGILITY_MINUS_RESILIENCE": hierarchy[
            "HIGHER_FRAGILITY_MINUS_RESILIENCE"
        ],
        "TRANSITION_PRESSURE_DELTA_15M": hierarchy[
            "TRANSITION_PRESSURE_DELTA_15M"
        ],
        "TRANSITION_PRESSURE_DELTA_30M": hierarchy[
            "TRANSITION_PRESSURE_DELTA_30M"
        ],
        "PEER_ADVERSE_1M": peer_adverse[1],
        "PEER_ADVERSE_5M": peer_adverse[5],
        "PEER_ADVERSE_15M": peer_adverse[15],
        "PEER_ADVERSE_ACCEL_5M": peer_accel5,
        "PEER_ADVERSE_ACCEL_15M": peer_accel15,
        "PEER_ADVERSE_BREADTH": peer_breadth,
        "LEAD_LAG_SIGN_CONSISTENCY": lead_lag_consistency,
        "VOLATILITY_EXPANSION_MINUS_COMPRESSION": volatility_transition,
        "NORMALIZED_ADVERSE_MOVE": adverse_move,
    }
    recovery_map = {
        "DISTANCE_NOW": distance_now,
        "RECLAIM_DISTANCE": reclaim_distance,
        "FRONTIER_TOUCHES_15M": float(touches_15),
        "FRONTIER_TOUCHES_30M": float(touches_30),
        "BREACH_RECLAIM_TRANSITIONS_15M": float(transitions_15),
        "BREACH_RECLAIM_TRANSITIONS_30M": float(transitions_30),
        "FAVORABLE_PERSISTENCE_5M": favorable5,
        "FAVORABLE_PERSISTENCE_15M": favorable15,
        "CONSECUTIVE_FAVORABLE_CLOSES": float(consecutive_favorable),
        "REJECTION_FRACTION_5M": rejection5,
        "REJECTION_FRACTION_15M": rejection15,
        "CLOSE_LOCATION_RECOVERY": _clamp(close_location_recovery, 0.0, 1.0),
        "RECOVERY_VELOCITY": recovery_velocity,
        "TIME_SINCE_WORST_EXCURSION": time_since_worst / 30.0,
        "HIERARCHY_RECESSION_COUNT": hierarchy["HIERARCHY_RECESSION_COUNT"],
        "HIERARCHY_ADVANCE_COUNT": hierarchy["HIERARCHY_ADVANCE_COUNT"],
        "HIGHER_RESILIENCE_MINUS_FRAGILITY": hierarchy[
            "HIGHER_RESILIENCE_MINUS_FRAGILITY"
        ],
        "HIGHER_RESILIENCE_DELTA_15M": hierarchy[
            "HIGHER_RESILIENCE_DELTA_15M"
        ],
        "HIGHER_RESILIENCE_DELTA_30M": hierarchy[
            "HIGHER_RESILIENCE_DELTA_30M"
        ],
        "COHERENCE_DELTA_15M": hierarchy["COHERENCE_DELTA_15M"],
        "COHERENCE_DELTA_30M": hierarchy["COHERENCE_DELTA_30M"],
        "PEER_CONTRADICTION": peer_contradiction,
        "PEER_RECOVERY_VELOCITY": peer_recovery_velocity,
        "RANGE_RATIO_1M_5M": range_ratio_1m_5m,
        "RANGE_RATIO_5M_20M": range_ratio_5m_20m,
        "NORMALIZED_RECOVERY_MOVE": normalized_recovery,
    }

    return CompetingSurvivalSourceState(
        episode_id=trajectory.episode_id,
        as_of=trajectory.snapshots[-1].as_of,
        anchor_direction=anchor_direction,
        terminal_features=tuple(
            float(terminal_map[name]) for name in TERMINAL_FEATURE_NAMES
        ),
        recovery_features=tuple(
            float(recovery_map[name]) for name in RECOVERY_FEATURE_NAMES
        ),
        evidence_complete=True,
    )
