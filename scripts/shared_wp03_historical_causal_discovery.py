"""WP-03 historical causal-discovery lab for Shared Brain.

The lab samples a fixed 30-minute grid from immutable NAS100/SP500/US30 M1
market evidence. It does not use trader events, directions, entries, stops,
targets, PnL or trade outcomes.

Protocol:
- R8 discovers candidate relations.
- The R8 candidate set and effect direction are frozen before R6/R5.
- R6 is a later temporal holdout.
- R5 is a second later temporal replication.
- Matched counterfactuals are built independently inside each partition.
- Natural intervention-like evidence requires an extreme source-state switch
  while the confounder/regime context remains unchanged.
- Every result stays RESEARCH_ONLY and carries no knowledge-promotion or
  trading authority.
"""

from __future__ import annotations

import argparse
import gc
import json
import math
import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from qore.infrastructure.core_stack_v2.causal_discovery_engine import (
    CausalDiscoveryAssessment,
    CausalDiscoveryEpisode,
    CausalDiscoveryPolicy,
    CausalDiscoveryStatus,
    CausalEffectDirection,
    discover_causal_relation,
)
from qore.infrastructure.core_stack_v2.dynamic_causal_graph import (
    CausalConcept,
)

SCHEMA = "qore.shared.wp03.historical_causal_discovery.v1"
IDENTITY = "QORE_SHARED_WP03_HISTORICAL_CAUSAL_DISCOVERY_001"
MARKETS = ("NAS100", "SP500", "US30")
PARTITIONS = ("r8", "r6", "r5")
SAMPLE_MINUTES = (0, 30)
TARGET_HORIZON_MINUTES = 30
PRE_WINDOW_MINUTES = 90
EXPOSED_BPS = 6_500
CONTROL_BPS = 3_500
MATCHED_CONTROL_MINIMUM = 50
PROTOCOL_MINIMUM_SAMPLES = 7_000

SOURCE_CONCEPTS = (
    CausalConcept.COMPRESSION,
    CausalConcept.LIQUIDITY_ACCUMULATION,
    CausalConcept.FAILED_AUCTION,
    CausalConcept.DISPLACEMENT,
    CausalConcept.ACCEPTANCE,
    CausalConcept.ABSORPTION,
    CausalConcept.LEADER_CONFIRMATION,
    CausalConcept.LEADER_DIVERGENCE,
    CausalConcept.MOMENTUM_PERSISTENCE,
    CausalConcept.MOMENTUM_DECAY,
    CausalConcept.STRUCTURAL_FRAGILITY,
    CausalConcept.LIQUIDITY_VACUUM,
    CausalConcept.REGIME_TRANSITION,
    CausalConcept.ANOMALY,
)
TARGET_CONCEPTS = (
    CausalConcept.EXPANSION_READINESS,
    CausalConcept.DISPLACEMENT,
    CausalConcept.CONTINUATION,
    CausalConcept.REVERSAL,
    CausalConcept.STRUCTURAL_FAILURE,
    CausalConcept.ANOMALY,
    CausalConcept.ACCEPTANCE,
    CausalConcept.MOMENTUM_PERSISTENCE,
)

SINGLE_PARTITION_POLICY = CausalDiscoveryPolicy(
    exposed_threshold_bps=EXPOSED_BPS,
    control_threshold_bps=CONTROL_BPS,
    minimum_effect_bps=500,
    minimum_group_count=250,
    minimum_stratum_group_count=20,
    minimum_conditional_strata=4,
    minimum_regimes=2,
    minimum_replication_partitions=2,
    minimum_intervention_group_count=30,
    minimum_counterfactual_pairs=100,
    minimum_integrity_bps=9_500,
    sign_stability_gate_bps=8_000,
    temporal_precedence_gate_bps=10_000,
)
COMBINED_POLICY = CausalDiscoveryPolicy(
    exposed_threshold_bps=EXPOSED_BPS,
    control_threshold_bps=CONTROL_BPS,
    minimum_effect_bps=500,
    minimum_group_count=500,
    minimum_stratum_group_count=30,
    minimum_conditional_strata=4,
    minimum_regimes=2,
    minimum_replication_partitions=3,
    minimum_intervention_group_count=50,
    minimum_counterfactual_pairs=200,
    minimum_integrity_bps=9_500,
    sign_stability_gate_bps=8_000,
    temporal_precedence_gate_bps=10_000,
)


@dataclass(frozen=True, slots=True)
class _Bar:
    opened_key: str
    closed_key: str
    opened: float
    high: float
    low: float
    close: float


@dataclass(frozen=True, slots=True)
class _Metric:
    net_bps: float
    path_bps: float
    efficiency: float
    range_mean_bps: float
    max_abs_return_bps: float
    wick_fraction: float
    high: float
    low: float
    close: float


@dataclass(frozen=True, slots=True)
class _Observation:
    partition: str
    source_at: datetime
    target_at: datetime
    confounder_key: str
    regime_key: str
    source_states: tuple[tuple[CausalConcept, int], ...]
    target_states: tuple[tuple[CausalConcept, int], ...]

    def source(self, concept: CausalConcept) -> int:
        for candidate, value in self.source_states:
            if candidate is concept:
                return value
        raise KeyError(concept)

    def target(self, concept: CausalConcept) -> int:
        for candidate, value in self.target_states:
            if candidate is concept:
                return value
        raise KeyError(concept)


def _clamp_bps(value: float) -> int:
    return max(0, min(10_000, int(round(value))))


def _return_bps(last: float, first: float) -> float:
    if first == 0:
        return 0.0
    return (last / first - 1.0) * 10_000.0


def _sign(value: float) -> int:
    if abs(value) < 1e-12:
        return 0
    return 1 if value > 0 else -1


def _parse_key(value: str) -> datetime:
    return datetime.fromisoformat(value).replace(tzinfo=UTC)


def _load_bars(path: Path) -> tuple[_Bar, ...]:
    payload = cast(dict[str, Any], json.loads(path.read_text()))
    raw = cast(list[dict[str, Any]], payload["periods"]["M1"])
    bars = tuple(
        _Bar(
            opened_key=str(row["opened_at"])[:19],
            closed_key=str(row["closed_at"])[:19],
            opened=float(row["open"]),
            high=float(row["high"]),
            low=float(row["low"]),
            close=float(row["close"]),
        )
        for row in raw
    )
    del payload
    del raw
    return bars


def _metric(bars: tuple[_Bar, ...] | list[_Bar]) -> _Metric:
    if len(bars) < 2:
        raise ValueError("metric requires at least two bars")
    one_minute = [
        _return_bps(bars[index].close, bars[index - 1].close)
        for index in range(1, len(bars))
    ]
    net = _return_bps(bars[-1].close, bars[0].close)
    path = sum(abs(value) for value in one_minute)
    ranges = [
        (bar.high - bar.low) / bar.close * 10_000.0
        if bar.close
        else 0.0
        for bar in bars
    ]
    wick = [
        1.0
        - (
            abs(bar.close - bar.opened) / (bar.high - bar.low)
            if bar.high > bar.low
            else 0.0
        )
        for bar in bars
    ]
    return _Metric(
        net_bps=net,
        path_bps=path,
        efficiency=0.0 if path == 0 else abs(net) / path,
        range_mean_bps=statistics.fmean(ranges),
        max_abs_return_bps=max((abs(value) for value in one_minute), default=0.0),
        wick_fraction=statistics.fmean(wick),
        high=max(bar.high for bar in bars),
        low=min(bar.low for bar in bars),
        close=bars[-1].close,
    )


def _coherence(metrics: dict[str, _Metric]) -> tuple[float, float]:
    signs = [_sign(metrics[market].net_bps) for market in MARKETS]
    signed = sum(signs) / len(signs)
    return abs(signed), signed


def _source_state(
    windows: dict[str, tuple[_Bar, ...]],
) -> tuple[dict[CausalConcept, int], float, float]:
    horizon: dict[str, dict[int, _Metric]] = {}
    previous: dict[str, dict[int, _Metric]] = {}
    sweep: dict[str, float] = {}
    acceptance: dict[str, float] = {}
    edge: dict[str, float] = {}

    for market, bars in windows.items():
        horizon[market] = {
            5: _metric(bars[-5:]),
            15: _metric(bars[-15:]),
            30: _metric(bars[-30:]),
            60: _metric(bars[-60:]),
        }
        previous[market] = {
            5: _metric(bars[-35:-30]),
            15: _metric(bars[-45:-30]),
            60: _metric(bars[-90:-30]),
        }

        prior = bars[-25:-5]
        recent = bars[-5:]
        prior_peak = max(bar.high for bar in prior)
        prior_floor = min(bar.low for bar in prior)
        last_close = recent[-1].close
        sweep[market] = float(
            (
                max(bar.high for bar in recent) > prior_peak
                and last_close < prior_peak
            )
            or (
                min(bar.low for bar in recent) < prior_floor
                and last_close > prior_floor
            )
        )
        outside = sum(
            bar.close > prior_peak or bar.close < prior_floor
            for bar in recent
        )
        acceptance[market] = outside / len(recent)
        width = max(1e-12, prior_peak - prior_floor)
        position = (last_close - prior_floor) / width
        edge[market] = min(1.0, abs(position - 0.5) * 2.0)

    def m(market: str, minutes: int) -> _Metric:
        return horizon[market][minutes]

    def p(market: str, minutes: int) -> _Metric:
        return previous[market][minutes]

    coh15, signed15 = _coherence(
        {market: m(market, 15) for market in MARKETS}
    )
    coh60, _ = _coherence({market: m(market, 60) for market in MARKETS})
    prev_coh15, _ = _coherence(
        {market: p(market, 15) for market in MARKETS}
    )

    nas5 = m("NAS100", 5)
    nas15 = m("NAS100", 15)
    nas30 = m("NAS100", 30)
    nas60 = m("NAS100", 60)
    prev5 = p("NAS100", 5)
    prev60 = p("NAS100", 60)

    vol_ratio = nas5.range_mean_bps / max(1e-9, nas60.range_mean_bps)
    prev_vol_ratio = prev5.range_mean_bps / max(
        1e-9,
        prev60.range_mean_bps,
    )
    displacement_scale = abs(nas5.net_bps) / max(
        1e-9,
        nas60.range_mean_bps * math.sqrt(5.0),
    )
    stretch15 = abs(nas15.net_bps) / max(
        1e-9,
        nas60.range_mean_bps * math.sqrt(15.0),
    )
    aligned_5_15_30 = float(
        _sign(nas5.net_bps)
        == _sign(nas15.net_bps)
        == _sign(nas30.net_bps)
        != 0
    )
    reverse5_15 = float(nas5.net_bps * nas15.net_bps < 0)
    recent_speed = abs(nas5.net_bps) / 5.0
    medium_speed = abs(nas15.net_bps) / 15.0
    speed_decay = (
        0.0
        if medium_speed <= 1e-9
        else max(0.0, min(1.0, 1.0 - recent_speed / medium_speed))
    )
    peer_direction = _sign(
        m("SP500", 15).net_bps + m("US30", 15).net_bps
    )
    leader_alignment = float(
        _sign(nas15.net_bps) != 0
        and _sign(nas15.net_bps) == peer_direction
    )
    vol_transition = min(
        1.0,
        abs(vol_ratio - prev_vol_ratio) / 1.5,
    )
    coherence_transition = min(1.0, abs(coh15 - prev_coh15))

    compression = min(
        1.0,
        0.45 * (1.0 - min(1.0, vol_ratio))
        + 0.30 * (1.0 - min(1.0, stretch15))
        + 0.25 * (1.0 - nas15.efficiency),
    )
    liquidity_accumulation = min(
        1.0,
        0.45 * nas30.wick_fraction
        + 0.35 * (1.0 - nas30.efficiency)
        + 0.20 * (1.0 - min(1.0, vol_ratio)),
    )
    failed_auction = min(
        1.0,
        0.65 * sweep["NAS100"]
        + 0.20 * nas5.wick_fraction
        + 0.15 * (1.0 - acceptance["NAS100"]),
    )
    displacement = min(
        1.0,
        0.40 * min(1.0, displacement_scale)
        + 0.35 * nas5.efficiency
        + 0.25 * min(1.0, max(0.0, vol_ratio - 1.0) / 1.5),
    )
    current_acceptance = min(
        1.0,
        0.70 * acceptance["NAS100"]
        + 0.30 * nas5.efficiency,
    )
    absorption = min(
        1.0,
        0.50 * nas15.wick_fraction
        + 0.35 * (1.0 - nas15.efficiency)
        + 0.15 * min(1.0, vol_ratio),
    )
    leader_confirmation = min(
        1.0,
        0.60 * coh15 + 0.40 * leader_alignment,
    )
    leader_divergence = 1.0 - leader_confirmation
    momentum_persistence = min(
        1.0,
        0.40 * aligned_5_15_30
        + 0.30 * nas15.efficiency
        + 0.30 * coh15,
    )
    momentum_decay = min(
        1.0,
        0.40 * speed_decay
        + 0.30 * reverse5_15
        + 0.30 * (1.0 - nas5.efficiency),
    )
    structural_fragility = min(
        1.0,
        0.35 * leader_divergence
        + 0.25 * failed_auction
        + 0.20 * min(1.0, max(0.0, vol_ratio - 1.0))
        + 0.20 * edge["NAS100"],
    )
    liquidity_vacuum = min(
        1.0,
        0.45
        * min(
            1.0,
            nas5.max_abs_return_bps
            / max(1e-9, nas60.range_mean_bps * 2.0),
        )
        + 0.35 * nas5.efficiency
        + 0.20 * (1.0 - nas5.wick_fraction),
    )
    regime_transition = min(
        1.0,
        0.60 * vol_transition + 0.40 * coherence_transition,
    )
    anomaly = min(
        1.0,
        0.60
        * min(
            1.0,
            nas5.max_abs_return_bps
            / max(1e-9, nas60.range_mean_bps * 3.0),
        )
        + 0.40 * min(1.0, max(0.0, vol_ratio - 1.0) / 2.0),
    )

    states = {
        CausalConcept.COMPRESSION: _clamp_bps(compression * 10_000),
        CausalConcept.LIQUIDITY_ACCUMULATION: _clamp_bps(
            liquidity_accumulation * 10_000
        ),
        CausalConcept.FAILED_AUCTION: _clamp_bps(failed_auction * 10_000),
        CausalConcept.DISPLACEMENT: _clamp_bps(displacement * 10_000),
        CausalConcept.ACCEPTANCE: _clamp_bps(current_acceptance * 10_000),
        CausalConcept.ABSORPTION: _clamp_bps(absorption * 10_000),
        CausalConcept.LEADER_CONFIRMATION: _clamp_bps(
            leader_confirmation * 10_000
        ),
        CausalConcept.LEADER_DIVERGENCE: _clamp_bps(
            leader_divergence * 10_000
        ),
        CausalConcept.MOMENTUM_PERSISTENCE: _clamp_bps(
            momentum_persistence * 10_000
        ),
        CausalConcept.MOMENTUM_DECAY: _clamp_bps(momentum_decay * 10_000),
        CausalConcept.STRUCTURAL_FRAGILITY: _clamp_bps(
            structural_fragility * 10_000
        ),
        CausalConcept.LIQUIDITY_VACUUM: _clamp_bps(
            liquidity_vacuum * 10_000
        ),
        CausalConcept.REGIME_TRANSITION: _clamp_bps(
            regime_transition * 10_000
        ),
        CausalConcept.ANOMALY: _clamp_bps(anomaly * 10_000),
    }
    return states, vol_ratio, coh60


def _target_state(
    pre: dict[str, tuple[_Bar, ...]],
    future: dict[str, tuple[_Bar, ...]],
) -> dict[CausalConcept, int]:
    pre60 = _metric(pre["NAS100"][-60:])
    pre15 = _metric(pre["NAS100"][-15:])
    future5 = _metric(future["NAS100"][:5])
    future15 = _metric(future["NAS100"][:15])
    future30 = _metric(future["NAS100"][:30])
    peer30 = {
        market: _metric(future[market][:30])
        for market in MARKETS
    }
    coherence30, _ = _coherence(peer30)

    vol_ratio = future15.range_mean_bps / max(
        1e-9,
        pre60.range_mean_bps,
    )
    displacement_scale = abs(future5.net_bps) / max(
        1e-9,
        pre60.range_mean_bps * math.sqrt(5.0),
    )
    expansion_scale = abs(future15.net_bps) / max(
        1e-9,
        pre60.range_mean_bps * math.sqrt(15.0),
    )
    source_direction = _sign(pre15.net_bps)
    future_direction = _sign(future30.net_bps)
    same_direction = float(
        source_direction != 0 and source_direction == future_direction
    )
    opposite_direction = float(
        source_direction != 0 and source_direction == -future_direction
    )

    prior = pre["NAS100"][-20:]
    prior_peak = max(bar.high for bar in prior)
    prior_floor = min(bar.low for bar in prior)
    final_close = future["NAS100"][29].close
    if source_direction > 0:
        failure_break = float(
            min(bar.low for bar in future["NAS100"][:30]) < prior_floor
            and final_close < prior_floor
        )
    elif source_direction < 0:
        failure_break = float(
            max(bar.high for bar in future["NAS100"][:30]) > prior_peak
            and final_close > prior_peak
        )
    else:
        failure_break = 0.0

    last10 = future["NAS100"][20:30]
    accepted_upper = sum(bar.close > prior_peak for bar in last10) / len(last10)
    accepted_lower = sum(bar.close < prior_floor for bar in last10) / len(last10)
    accepted = max(accepted_upper, accepted_lower)

    signs = [
        _sign(future5.net_bps),
        _sign(future15.net_bps),
        _sign(future30.net_bps),
    ]
    future_persistence = float(signs[0] == signs[1] == signs[2] != 0)

    expansion_readiness = min(
        1.0,
        0.40 * min(1.0, max(0.0, vol_ratio - 0.8) / 1.2)
        + 0.30 * future15.efficiency
        + 0.30 * min(1.0, expansion_scale),
    )
    displacement = min(
        1.0,
        0.45 * min(1.0, displacement_scale)
        + 0.35 * future5.efficiency
        + 0.20 * min(1.0, max(0.0, vol_ratio - 1.0) / 1.5),
    )
    continuation = min(
        1.0,
        0.45 * same_direction
        + 0.30 * future30.efficiency
        + 0.25 * min(1.0, expansion_scale),
    )
    reversal = min(
        1.0,
        0.50 * opposite_direction
        + 0.25 * future30.efficiency
        + 0.25 * min(1.0, expansion_scale),
    )
    structural_failure = min(
        1.0,
        0.55 * failure_break
        + 0.25 * opposite_direction
        + 0.20 * min(1.0, expansion_scale),
    )
    anomaly = min(
        1.0,
        0.60
        * min(
            1.0,
            future30.max_abs_return_bps
            / max(1e-9, pre60.range_mean_bps * 3.0),
        )
        + 0.40 * min(1.0, max(0.0, vol_ratio - 1.0) / 2.0),
    )
    acceptance = min(
        1.0,
        0.70 * accepted + 0.30 * future30.efficiency,
    )
    momentum_persistence = min(
        1.0,
        0.45 * future_persistence
        + 0.30 * future30.efficiency
        + 0.25 * coherence30,
    )

    return {
        CausalConcept.EXPANSION_READINESS: _clamp_bps(
            expansion_readiness * 10_000
        ),
        CausalConcept.DISPLACEMENT: _clamp_bps(displacement * 10_000),
        CausalConcept.CONTINUATION: _clamp_bps(continuation * 10_000),
        CausalConcept.REVERSAL: _clamp_bps(reversal * 10_000),
        CausalConcept.STRUCTURAL_FAILURE: _clamp_bps(
            structural_failure * 10_000
        ),
        CausalConcept.ANOMALY: _clamp_bps(anomaly * 10_000),
        CausalConcept.ACCEPTANCE: _clamp_bps(acceptance * 10_000),
        CausalConcept.MOMENTUM_PERSISTENCE: _clamp_bps(
            momentum_persistence * 10_000
        ),
    }


def _bucket(value: float, low: float, high: float) -> str:
    if value < low:
        return "LOW"
    if value < high:
        return "MID"
    return "HIGH"


def _regime(states: dict[CausalConcept, int]) -> str:
    if states[CausalConcept.ANOMALY] >= 7_000:
        return "DISLOCATION"
    if states[CausalConcept.REGIME_TRANSITION] >= 6_500:
        return "TRANSITION"
    if states[CausalConcept.COMPRESSION] >= 7_000:
        return "COMPRESSION"
    if (
        states[CausalConcept.MOMENTUM_PERSISTENCE] >= 6_500
        and states[CausalConcept.LEADER_CONFIRMATION] >= 6_500
    ):
        return "TREND_COHERENT"
    if (
        states[CausalConcept.ABSORPTION] >= 6_500
        or states[CausalConcept.LIQUIDITY_ACCUMULATION] >= 6_500
    ):
        return "RANGE_ABSORPTION"
    return "MIXED"


def _prepare_partition(
    *,
    partition: str,
    evidence_paths: dict[str, Path],
) -> tuple[_Observation, ...]:
    bars = {
        market: _load_bars(evidence_paths[market])
        for market in MARKETS
    }
    peer_indexes = {
        market: {
            bar.closed_key: index
            for index, bar in enumerate(bars[market])
        }
        for market in ("SP500", "US30")
    }

    observations: list[_Observation] = []
    nas = bars["NAS100"]
    for nas_index in range(
        PRE_WINDOW_MINUTES,
        len(nas) - TARGET_HORIZON_MINUTES - 1,
    ):
        key = nas[nas_index].closed_key
        minute = int(key[14:16])
        if minute not in SAMPLE_MINUTES:
            continue

        indexes = {"NAS100": nas_index}
        missing = False
        for market in ("SP500", "US30"):
            peer_index = peer_indexes[market].get(key)
            if peer_index is None:
                missing = True
                break
            indexes[market] = peer_index
        if missing:
            continue

        pre: dict[str, tuple[_Bar, ...]] = {}
        future: dict[str, tuple[_Bar, ...]] = {}
        continuous = True
        for market in MARKETS:
            index = indexes[market]
            if (
                index < PRE_WINDOW_MINUTES
                or index + TARGET_HORIZON_MINUTES >= len(bars[market])
            ):
                continuous = False
                break
            pre_rows = bars[market][index - PRE_WINDOW_MINUTES + 1 : index + 1]
            future_rows = bars[market][
                index + 1 : index + 1 + TARGET_HORIZON_MINUTES
            ]
            source_at = _parse_key(pre_rows[-1].closed_key)
            pre_start = _parse_key(pre_rows[-60].closed_key)
            target_at = _parse_key(future_rows[-1].closed_key)
            if (source_at - pre_start).total_seconds() > 70 * 60:
                continuous = False
                break
            if (target_at - source_at).total_seconds() > 35 * 60:
                continuous = False
                break
            pre[market] = pre_rows
            future[market] = future_rows
        if not continuous:
            continue

        source_states, vol_ratio, coherence60 = _source_state(pre)
        target_states = _target_state(pre, future)
        source_at = _parse_key(pre["NAS100"][-1].closed_key)
        target_at = _parse_key(future["NAS100"][-1].closed_key)
        hour = source_at.hour
        tod = (
            "Q0"
            if hour < 6
            else "Q1"
            if hour < 12
            else "Q2"
            if hour < 18
            else "Q3"
        )
        confounder = (
            f"VOL_{_bucket(vol_ratio, 0.75, 1.25)}"
            f"|COH_{_bucket(coherence60, 0.34, 0.67)}"
            f"|TOD_{tod}"
        )
        observations.append(
            _Observation(
                partition=partition,
                source_at=source_at,
                target_at=target_at,
                confounder_key=confounder,
                regime_key=_regime(source_states),
                source_states=tuple(
                    (concept, source_states[concept])
                    for concept in SOURCE_CONCEPTS
                ),
                target_states=tuple(
                    (concept, target_states[concept])
                    for concept in TARGET_CONCEPTS
                ),
            )
        )

    del bars
    del peer_indexes
    gc.collect()
    return tuple(observations)


def _relation_episodes(
    observations: tuple[_Observation, ...],
    *,
    source: CausalConcept,
    target: CausalConcept,
) -> tuple[CausalDiscoveryEpisode, ...]:
    controls: dict[tuple[str, str], list[int]] = defaultdict(list)
    for item in observations:
        if item.source(source) <= CONTROL_BPS:
            controls[(item.confounder_key, item.regime_key)].append(
                item.target(target)
            )
    matched_control = {
        key: sum(values) // len(values)
        for key, values in controls.items()
        if len(values) >= MATCHED_CONTROL_MINIMUM
    }

    episodes: list[CausalDiscoveryEpisode] = []
    previous: _Observation | None = None
    for item in observations:
        source_bps = item.source(source)
        if CONTROL_BPS < source_bps < EXPOSED_BPS:
            previous = item
            continue

        natural_intervention = False
        if previous is not None:
            gap = (item.source_at - previous.source_at).total_seconds()
            stable_context = (
                item.confounder_key == previous.confounder_key
                and item.regime_key == previous.regime_key
            )
            switched = (
                source_bps >= EXPOSED_BPS
                and previous.source(source) <= CONTROL_BPS
            ) or (
                source_bps <= CONTROL_BPS
                and previous.source(source) >= EXPOSED_BPS
            )
            natural_intervention = bool(
                0 < gap <= 35 * 60 and stable_context and switched
            )

        counterfactual = None
        if source_bps >= EXPOSED_BPS:
            counterfactual = matched_control.get(
                (item.confounder_key, item.regime_key)
            )

        episodes.append(
            CausalDiscoveryEpisode(
                source=source,
                target=target,
                source_at=item.source_at,
                target_at=item.target_at,
                source_state_bps=source_bps,
                target_state_bps=item.target(target),
                confounder_key=item.confounder_key,
                regime_key=item.regime_key,
                replication_partition=item.partition,
                integrity_bps=10_000,
                natural_intervention=natural_intervention,
                counterfactual_target_without_source_bps=counterfactual,
            )
        )
        previous = item
    return tuple(episodes)


def _assessment_payload(
    assessment: CausalDiscoveryAssessment,
) -> dict[str, Any]:
    return {
        "status": assessment.status.value,
        "direction": assessment.direction.value,
        "sample_count": assessment.sample_count,
        "exposed_count": assessment.exposed_count,
        "control_count": assessment.control_count,
        "raw_effect_bps": assessment.raw_effect_bps,
        "conditional_effect_bps": assessment.conditional_effect_bps,
        "intervention_effect_bps": assessment.intervention_effect_bps,
        "counterfactual_effect_bps": assessment.counterfactual_effect_bps,
        "temporal_precedence_bps": assessment.temporal_precedence_bps,
        "conditional_sign_stability_bps": (
            assessment.conditional_sign_stability_bps
        ),
        "cross_regime_stability_bps": assessment.cross_regime_stability_bps,
        "replication_stability_bps": assessment.replication_stability_bps,
        "conditional_strata_count": assessment.conditional_strata_count,
        "regime_count": assessment.regime_count,
        "replication_partition_count": (
            assessment.replication_partition_count
        ),
        "excluded_low_integrity_count": (
            assessment.excluded_low_integrity_count
        ),
        "intervention_evidence_available": (
            assessment.intervention_evidence_available
        ),
        "counterfactual_evidence_available": (
            assessment.counterfactual_evidence_available
        ),
        "replicated": assessment.replicated,
        "observational_association_only": (
            assessment.observational_association_only
        ),
        "reasons": list(assessment.reasons),
        "authority": {
            "methodology": assessment.methodology_authority,
            "knowledge_promotion": assessment.knowledge_promotion_authority,
            "sizing": assessment.sizing_authority,
            "risk": assessment.risk_authority,
            "order": assessment.order_authority,
            "execution": assessment.execution_authority,
        },
    }


def _assess(
    observations: tuple[_Observation, ...],
    *,
    source: CausalConcept,
    target: CausalConcept,
    policy: CausalDiscoveryPolicy,
) -> tuple[CausalDiscoveryAssessment | None, tuple[CausalDiscoveryEpisode, ...]]:
    episodes = _relation_episodes(
        observations,
        source=source,
        target=target,
    )
    if not episodes:
        return None, ()
    as_of = max(item.target_at for item in episodes)
    try:
        assessment = discover_causal_relation(
            as_of=as_of,
            episodes=episodes,
            policy=policy,
        )
    except ValueError as exc:
        if "integrity gate" in str(exc):
            return None, episodes
        raise
    return assessment, episodes


def _same_material_direction(
    reference: CausalDiscoveryAssessment,
    candidate: CausalDiscoveryAssessment,
) -> bool:
    return (
        reference.direction is not CausalEffectDirection.UNRESOLVED
        and candidate.direction is reference.direction
        and abs(candidate.raw_effect_bps) >= 500
        and candidate.conditional_effect_bps is not None
        and abs(candidate.conditional_effect_bps) >= 500
    )


def _partition_range(
    rows: tuple[_Observation, ...],
) -> dict[str, str | None]:
    if not rows:
        return {
            "source_min": None,
            "source_max": None,
            "target_max": None,
        }
    return {
        "source_min": min(item.source_at for item in rows).isoformat(),
        "source_max": max(item.source_at for item in rows).isoformat(),
        "target_max": max(item.target_at for item in rows).isoformat(),
    }


def _strictly_after(
    earlier: tuple[_Observation, ...],
    later: tuple[_Observation, ...],
) -> bool:
    if not earlier or not later:
        return False
    earlier_target_max = max(item.target_at for item in earlier)
    later_source_min = min(item.source_at for item in later)
    return earlier_target_max < later_source_min


def run(
    *,
    evidence: dict[str, dict[str, Path]],
) -> dict[str, Any]:
    observations = {
        partition: _prepare_partition(
            partition=partition,
            evidence_paths=evidence[partition],
        )
        for partition in PARTITIONS
    }
    sample_counts = {
        partition: len(rows)
        for partition, rows in observations.items()
    }
    partition_ranges = {
        partition: _partition_range(rows)
        for partition, rows in observations.items()
    }
    r6_temporally_after_r8 = _strictly_after(
        observations["r8"],
        observations["r6"],
    )
    r5_temporally_after_r6 = _strictly_after(
        observations["r6"],
        observations["r5"],
    )

    all_pairs = [
        (source, target)
        for source in SOURCE_CONCEPTS
        for target in TARGET_CONCEPTS
        if source is not target
    ]

    r8_screen: list[tuple[CausalConcept, CausalConcept]] = []
    r8_status_counts: Counter[str] = Counter()
    r8_assessments: dict[
        tuple[CausalConcept, CausalConcept],
        CausalDiscoveryAssessment,
    ] = {}
    for source, target in all_pairs:
        assessment, _ = _assess(
            observations["r8"],
            source=source,
            target=target,
            policy=SINGLE_PARTITION_POLICY,
        )
        if assessment is None:
            r8_status_counts["NO_ASSESSMENT"] += 1
            continue
        r8_assessments[(source, target)] = assessment
        r8_status_counts[assessment.status.value] += 1
        if (
            assessment.status is CausalDiscoveryStatus.RESEARCH_CANDIDATE
            and assessment.direction is not CausalEffectDirection.UNRESOLVED
        ):
            r8_screen.append((source, target))

    evaluated: list[dict[str, Any]] = []
    replicated: list[dict[str, Any]] = []
    falsified_holdout = 0

    for source, target in r8_screen:
        r8 = r8_assessments[(source, target)]
        r6, r6_episodes = _assess(
            observations["r6"],
            source=source,
            target=target,
            policy=SINGLE_PARTITION_POLICY,
        )
        r5, r5_episodes = _assess(
            observations["r5"],
            source=source,
            target=target,
            policy=SINGLE_PARTITION_POLICY,
        )
        _, r8_episodes = _assess(
            observations["r8"],
            source=source,
            target=target,
            policy=SINGLE_PARTITION_POLICY,
        )

        if r6 is None or r5 is None:
            continue

        combined_episodes = r8_episodes + r6_episodes + r5_episodes
        combined = discover_causal_relation(
            as_of=max(item.target_at for item in combined_episodes),
            episodes=combined_episodes,
            policy=COMBINED_POLICY,
        )

        r6_direction_pass = _same_material_direction(r8, r6)
        r5_direction_pass = _same_material_direction(r8, r5)
        holdout_falsified = (
            r6.status is CausalDiscoveryStatus.FALSIFIED
            or r5.status is CausalDiscoveryStatus.FALSIFIED
            or not r6_direction_pass
            or not r5_direction_pass
        )
        if holdout_falsified:
            falsified_holdout += 1

        replicated_pass = (
            not holdout_falsified
            and combined.status is CausalDiscoveryStatus.RESEARCH_REPLICATED
            and combined.direction is r8.direction
            and combined.replication_partition_count >= 3
            and combined.replication_stability_bps >= 8_000
            and combined.temporal_precedence_bps == 10_000
        )

        row = {
            "source": source.value,
            "target": target.value,
            "r8_discovery": _assessment_payload(r8),
            "r6_holdout": _assessment_payload(r6),
            "r5_replication": _assessment_payload(r5),
            "combined": _assessment_payload(combined),
            "r6_direction_pass": r6_direction_pass,
            "r5_direction_pass": r5_direction_pass,
            "holdout_falsified": holdout_falsified,
            "replicated_research_relation": replicated_pass,
        }
        evaluated.append(row)
        if replicated_pass:
            replicated.append(row)

    source_extreme_counts = {
        partition: {
            source.value: {
                "exposed": sum(
                    item.source(source) >= EXPOSED_BPS
                    for item in rows
                ),
                "control": sum(
                    item.source(source) <= CONTROL_BPS
                    for item in rows
                ),
            }
            for source in SOURCE_CONCEPTS
        }
        for partition, rows in observations.items()
    }
    ranked_r8 = sorted(
        r8_assessments.items(),
        key=lambda item: abs(
            item[1].conditional_effect_bps
            if item[1].conditional_effect_bps is not None
            else item[1].raw_effect_bps
        ),
        reverse=True,
    )[:20]
    r8_top_associations = [
        {
            "source": source.value,
            "target": target.value,
            "assessment": _assessment_payload(assessment),
        }
        for (source, target), assessment in ranked_r8
    ]

    status = (
        "WP03_REPLICATED_RELATIONS_FOUND_RESEARCH_ONLY"
        if replicated
        else "WP03_NO_REPLICATED_RELATIONS_RESEARCH_ONLY"
    )
    minimum_samples = min(sample_counts.values()) if sample_counts else 0
    protocol_pass = (
        minimum_samples >= PROTOCOL_MINIMUM_SAMPLES
        and r6_temporally_after_r8
        and r5_temporally_after_r6
        and len(all_pairs) >= 50
        and all(
            not value
            for row in replicated
            for value in row["combined"]["authority"].values()
        )
    )

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "status": status,
        "protocol_pass": protocol_pass,
        "sample_counts": sample_counts,
        "partition_ranges": partition_ranges,
        "protocol_minimum_samples": PROTOCOL_MINIMUM_SAMPLES,
        "source_extreme_counts": source_extreme_counts,
        "r8_status_counts": dict(sorted(r8_status_counts.items())),
        "r8_top_associations": r8_top_associations,
        "sampling": {
            "fixed_grid_minutes": list(SAMPLE_MINUTES),
            "target_horizon_minutes": TARGET_HORIZON_MINUTES,
            "minimum_contiguous_pre_minutes": 60,
            "maximum_allowed_pre_span_minutes": 70,
            "maximum_allowed_target_span_minutes": 35,
            "trader_event_timestamps_used": False,
            "full_market_grid_sampling": True,
        },
        "screened_pair_count": len(all_pairs),
        "r8_research_candidate_count": len(r8_screen),
        "r6_r5_evaluated_candidate_count": len(evaluated),
        "holdout_falsified_count": falsified_holdout,
        "replicated_research_relation_count": len(replicated),
        "replicated_research_relations": replicated,
        "evaluated_r8_candidates": evaluated,
        "governance": {
            "r8_only_used_for_candidate_discovery": True,
            "r6_used_for_candidate_selection": False,
            "r5_used_for_candidate_selection": False,
            "r6_temporally_after_r8": r6_temporally_after_r8,
            "r5_temporally_after_r6": r5_temporally_after_r6,
            "matched_counterfactuals_partition_local": True,
            "future_target_used_for_research_evaluation_only": True,
            "trade_direction_used": False,
            "trade_entry_used": False,
            "trade_stop_used": False,
            "trade_target_used": False,
            "trade_pnl_used": False,
            "trade_terminal_outcome_used": False,
            "knowledge_auto_promotion": False,
            "shared_methodology_authority": False,
            "shared_sizing_authority": False,
            "shared_risk_authority": False,
            "shared_order_authority": False,
            "shared_execution_authority": False,
            "live_authorized": False,
            "production_authorized": False,
            "real_capital_authorized": False,
            "merge_authorized": False,
        },
    }


def _partition_paths(
    args: argparse.Namespace,
    partition: str,
) -> dict[str, Path]:
    return {
        "NAS100": getattr(args, f"{partition}_nas"),
        "SP500": getattr(args, f"{partition}_sp"),
        "US30": getattr(args, f"{partition}_us"),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    for partition in PARTITIONS:
        parser.add_argument(f"--{partition}-nas", type=Path, required=True)
        parser.add_argument(f"--{partition}-sp", type=Path, required=True)
        parser.add_argument(f"--{partition}-us", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    payload = run(
        evidence={
            partition: _partition_paths(args, partition)
            for partition in PARTITIONS
        }
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n"
    )
    print(
        json.dumps(
            {
                "status": payload["status"],
                "protocol_pass": payload["protocol_pass"],
                "sample_counts": payload["sample_counts"],
                "screened_pair_count": payload["screened_pair_count"],
                "r8_research_candidate_count": payload[
                    "r8_research_candidate_count"
                ],
                "holdout_falsified_count": payload[
                    "holdout_falsified_count"
                ],
                "replicated_research_relation_count": payload[
                    "replicated_research_relation_count"
                ],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
