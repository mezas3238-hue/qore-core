"""Full Shared Core V2 stack shadow challenge against VT08 Index PR #604.

Owner instruction:
- use Shared as the cognitive engine;
- VT08 supplies only methodology-valid opportunities, market evidence and later
  realized outcomes for falsification;
- exercise the extended Shared intelligence surface;
- sizing/risk weighting is absolutely forbidden.

This V3 lab is deliberately SHADOW. It does not mutate VT08 methodology or
claim economic uplift from unexecuted directives. It measures whether the full
Shared stack can causally discriminate opportunity quality, adverse
environments, recoverable adversity, winner paths and loss-defense situations.

Current/future outcome is never an input to a Shared assessment. Historical
outcomes enter only after their trades have closed and then only through
Shared's causal memory/stability contracts.
"""
# ruff: noqa: E501
from __future__ import annotations

import argparse
import bisect
import heapq
import json
from collections import Counter, defaultdict
from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import vt08_index_shared_cognitive_challenge_v2 as v2

from qore.infrastructure.core_stack_v2.analog_memory import (
    AnalogQuery,
    CausalAnalogMemory,
    ClosedEpisode,
)
from qore.infrastructure.core_stack_v2.competing_future_intelligence import (
    CausalHorizonSnapshot,
    CompetingFutureAssessment,
    CompetingFutureState,
    assess_competing_futures,
)
from qore.infrastructure.core_stack_v2.drawdown_phenotype_memory import (
    DrawdownPhenotype,
    DrawdownPhenotypeComposition,
    DrawdownPhenotypeQuery,
    DrawdownPhenotypeRecognition,
    UniversalDrawdownPhenotypeMemory,
)
from qore.infrastructure.core_stack_v2.environment_intelligence import (
    MarketEnvironmentAssessment,
    MarketEnvironmentObservation,
    assess_market_environment,
)
from qore.infrastructure.core_stack_v2.future_geometry_intelligence import (
    FutureGeometryAssessment,
    FutureGeometryState,
    assess_future_geometry,
    build_horizon_geometry,
)
from qore.infrastructure.core_stack_v2.instinct_intelligence import (
    InstinctAssessment,
    assess_instinct,
)
from qore.infrastructure.core_stack_v2.journey_intelligence import (
    PositionJourneyEvidence,
    assess_position_journey,
)
from qore.infrastructure.core_stack_v2.path_intelligence import (
    PositionPathObservation,
    assess_position_path,
)
from qore.infrastructure.core_stack_v2.perception_engine import (
    PerceptionBar,
    infer_situation,
    perceive_market,
)
from qore.infrastructure.core_stack_v2.realtime_trade_management import (
    RealtimeTradeAction,
    assess_realtime_trade_management,
)
from qore.infrastructure.core_stack_v2.stability_intelligence import (
    MarketStabilityEvidence,
    TraderStabilityTelemetry,
    assess_drawdown_stability,
)
from qore.infrastructure.core_stack_v2.transition_intelligence import (
    MarketTrajectoryAssessment,
    MarketTransitionObservation,
    assess_market_trajectory,
)

SCHEMA = "qore.shared.vt08_index.full_stack_challenge.v3"
IDENTITY = "QORE_SHARED_VT08_INDEX_FULL_STACK_NO_SIZING_V3"
VT08_PR = 604
VT08_HEAD = v2.VT08_HEAD
ZERO = Decimal("0")
ONE = Decimal("1")
TARGET_R = Decimal("2.5")
TRAJECTORY_WINDOW = 8
ENVIRONMENT_WINDOW = 8
PATH_WINDOW = 8
ANALOG_LIMIT = 128
PHENOTYPE_LIMIT = 256


def _clip(value: int) -> int:
    return max(0, min(10_000, int(value)))


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _jsonable(value: object) -> object:
    if isinstance(value, datetime):
        return value.astimezone(UTC).isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if hasattr(value, "value"):
        return getattr(value, "value")
    if isinstance(value, tuple):
        return [_jsonable(item) for item in value]
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    return value


def _history(
    item: object,
    *,
    bars_by_symbol: dict[str, Sequence[object]],
    closed_by_symbol: dict[str, tuple[datetime, ...]],
    as_of: datetime | None = None,
) -> tuple[MarketTransitionObservation, ...]:
    signal = item.opportunity.signal
    decision_at = (
        signal.signal_at.astimezone(UTC)
        if as_of is None
        else as_of.astimezone(UTC)
    )
    symbol = str(signal.symbol)
    side = v2._side_text(item)
    local_closed = closed_by_symbol[symbol]
    end = bisect.bisect_right(local_closed, decision_at)
    times = local_closed[max(0, end - v2.OBSERVATION_HISTORY):end]
    return tuple(
        v2._observation(
            symbol=symbol,
            side=side,
            as_of=stamp,
            bars_by_symbol=bars_by_symbol,
            closed_by_symbol=closed_by_symbol,
        )
        for stamp in times
    )


def _trajectory(history: Sequence[MarketTransitionObservation]) -> MarketTrajectoryAssessment:
    if not history:
        raise ValueError("Shared trajectory requires causal history")
    window = tuple(history[-min(TRAJECTORY_WINDOW, len(history)):])
    return assess_market_trajectory(window)


def _environment_observation(
    transition: MarketTransitionObservation,
    trajectory: MarketTrajectoryAssessment,
) -> MarketEnvironmentObservation:
    return MarketEnvironmentObservation(
        as_of=transition.as_of,
        data_integrity_bps=transition.data_integrity_bps,
        trajectory_support_bps=trajectory.support_bps,
        trajectory_adversity_bps=trajectory.adversity_bps,
        deterioration_velocity_bps=trajectory.deterioration_velocity_bps,
        recovery_velocity_bps=trajectory.recovery_velocity_bps,
        cross_market_breadth_bps=transition.cross_market_confirmation_bps,
        leadership_stability_bps=transition.correlation_stability_bps,
        correlation_stability_bps=transition.correlation_stability_bps,
        volatility_stability_bps=transition.volatility_stability_bps,
        liquidity_stability_bps=transition.liquidity_capacity_bps,
        regime_stability_bps=_clip(10_000 - transition.uncertainty_bps),
        anomaly_bps=transition.anomaly_bps,
        uncertainty_bps=transition.uncertainty_bps,
        opposite_pressure_bps=transition.opposite_pressure_bps,
    )


def _environment(
    history: Sequence[MarketTransitionObservation],
) -> MarketEnvironmentAssessment:
    env_history: list[MarketEnvironmentObservation] = []
    for idx, transition in enumerate(history):
        prefix = tuple(history[max(0, idx - TRAJECTORY_WINDOW + 1): idx + 1])
        trajectory = assess_market_trajectory(prefix)
        env_history.append(_environment_observation(transition, trajectory))
    return assess_market_environment(
        tuple(env_history[-min(ENVIRONMENT_WINDOW, len(env_history)):])
    )


def _geometry(
    history: Sequence[MarketTransitionObservation],
) -> FutureGeometryAssessment:
    geometries = tuple(
        build_horizon_geometry(
            tuple(history[-min(count, len(history)):]),
            horizon_minutes=minutes,
        )
        for minutes, count in v2.HORIZONS
        if len(history) >= 2
    )
    if not geometries:
        raise ValueError("Shared future geometry requires causal history")
    return assess_future_geometry(geometries)


def _future_snapshot(
    history: Sequence[MarketTransitionObservation],
    *,
    minutes: int,
    count: int,
) -> CausalHorizonSnapshot:
    window = tuple(history[-min(count, len(history)):])
    trajectory = assess_market_trajectory(window)
    latest = window[-1]
    structural_fragility = (
        latest.contradiction_bps
        + latest.anomaly_bps
        + latest.opposite_pressure_bps
    ) // 3
    return CausalHorizonSnapshot(
        horizon_minutes=minutes,
        as_of=latest.as_of,
        evidence_count=len(window),
        data_integrity_bps=min(item.data_integrity_bps for item in window),
        support_bps=trajectory.support_bps,
        adversity_bps=trajectory.adversity_bps,
        deterioration_velocity_bps=trajectory.deterioration_velocity_bps,
        recovery_velocity_bps=trajectory.recovery_velocity_bps,
        deterioration_persistence_bps=trajectory.deterioration_persistence_bps,
        recovery_persistence_bps=trajectory.recovery_persistence_bps,
        cross_market_confirmation_bps=latest.cross_market_confirmation_bps,
        cross_market_fragility_bps=10_000 - latest.cross_market_confirmation_bps,
        structural_fragility_bps=_clip(structural_fragility),
        trend_support_bps=latest.trend_support_bps,
        uncertainty_bps=latest.uncertainty_bps,
    )


def _competing_futures(
    history: Sequence[MarketTransitionObservation],
) -> CompetingFutureAssessment:
    snapshots = tuple(
        _future_snapshot(history, minutes=minutes, count=count)
        for minutes, count in v2.HORIZONS
        if len(history) >= 2
    )
    return assess_competing_futures(snapshots)


def _perception(
    item: object,
    *,
    bars_by_symbol: dict[str, Sequence[object]],
    closed_by_symbol: dict[str, tuple[datetime, ...]],
) -> tuple[object, object]:
    signal = item.opportunity.signal
    as_of = signal.signal_at.astimezone(UTC)
    symbol = str(signal.symbol)
    rows = v2._recent_asof(
        bars_by_symbol[symbol],
        closed_by_symbol[symbol],
        as_of=as_of,
        count=21,
    )
    bars = tuple(
        PerceptionBar(
            opened_at=bar.opened_at.astimezone(UTC).isoformat(),
            closed_at=bar.closed_at.astimezone(UTC).isoformat(),
            open=_d(bar.open),
            high=_d(bar.high),
            low=_d(bar.low),
            close=_d(bar.close),
        )
        for bar in rows
    )
    current = perceive_market(bars, as_of=as_of.isoformat())
    previous = None
    if len(bars) >= 2:
        previous = perceive_market(
            bars[:-1],
            as_of=bars[-2].closed_at,
        )
    return current, infer_situation(current, previous=previous)


def _signature(
    *,
    situation: object,
    trajectory: MarketTrajectoryAssessment,
    environment: MarketEnvironmentAssessment,
    geometry: FutureGeometryAssessment,
    futures: CompetingFutureAssessment,
) -> tuple[tuple[str, str], ...]:
    return tuple(
        sorted(
            (
                ("regime", str(situation.regime)),
                ("transition", str(situation.transition)),
                ("trajectory", trajectory.state.value),
                ("environment", environment.state.value),
                ("geometry", geometry.state.value),
                ("futures", futures.state.value),
            )
        )
    )


def _phenotype_views(signature: tuple[tuple[str, str], ...]) -> tuple[tuple[str, str], ...]:
    values = dict(signature)
    return tuple(
        sorted(
            (
                ("REGIME_TRANSITION", f"{values['regime']}|{values['transition']}"),
                ("TRAJECTORY_ENV", f"{values['trajectory']}|{values['environment']}"),
                ("FUTURE_GEOMETRY", values["geometry"]),
                ("COMPETING_FUTURES", values["futures"]),
            )
        )
    )


def _composition(losses: int, winners: int) -> DrawdownPhenotypeComposition:
    if losses > 0 and winners == 0:
        return DrawdownPhenotypeComposition.PURE_LOSS
    if losses > winners:
        return DrawdownPhenotypeComposition.LOSS_DOMINANT
    if losses == winners:
        return DrawdownPhenotypeComposition.MIXED_BALANCED
    return DrawdownPhenotypeComposition.WINNER_DOMINANT


def _memory(
    *,
    records: Sequence[dict[str, object]],
    market: str,
    as_of: datetime,
    signature: tuple[tuple[str, str], ...],
) -> tuple[object, object]:
    recent = tuple(records[-PHENOTYPE_LIMIT:])
    episodes = tuple(
        ClosedEpisode(
            episode_id=str(row["episode_id"]),
            market=str(row["market"]),
            closed_at=row["closed_at"],
            signature=row["signature"],
            terminal_r=row["terminal_r"],
        )
        for row in recent[-ANALOG_LIMIT:]
        if str(row["market"]) == market
    )
    analog = CausalAnalogMemory(episodes).query(
        AnalogQuery(
            market=market,
            as_of=as_of,
            signature=signature,
            maximum_analogs=32,
            minimum_similarity_bps=2_500,
        )
    )

    counts: dict[tuple[str, str], list[int]] = defaultdict(lambda: [0, 0])
    for row in recent:
        terminal_r = row["terminal_r"]
        for view, value in row["phenotype_views"]:
            bucket = counts[(view, value)]
            if terminal_r < ZERO:
                bucket[0] += 1
            elif terminal_r > ZERO:
                bucket[1] += 1

    phenotypes = tuple(
        DrawdownPhenotype(
            view=view,
            signature=value,
            composition=_composition(losses, winners),
            historical_sample=losses + winners,
            historical_losses=losses,
            historical_winners=winners,
            fold_presence="CAUSAL_PRIOR_ONLY",
            temporal_stability="DYNAMIC_CLOSED_MEMORY",
        )
        for (view, value), (losses, winners) in sorted(counts.items())
        if losses + winners >= 3
    )
    phenotype = UniversalDrawdownPhenotypeMemory(phenotypes).assess(
        DrawdownPhenotypeQuery(signatures=_phenotype_views(signature))
    )
    return analog, phenotype


def _stability(
    *,
    records: Sequence[dict[str, object]],
    as_of: datetime,
    situation: object,
    latest: MarketTransitionObservation,
    trajectory: MarketTrajectoryAssessment,
) -> object:
    ordered = tuple(sorted(records, key=lambda row: row["closed_at"]))
    values = [row["terminal_r"] for row in ordered]
    equities = [ZERO]
    for value in values:
        equities.append(equities[-1] + value)
    equity = equities[-1]
    peak = max(equities)
    dd = peak - equity
    if len(equities) >= 2:
        prev_equity = equities[-2]
        prev_peak = max(equities[:-1])
        prev_dd = prev_peak - prev_equity
    else:
        prev_dd = ZERO
    velocity = dd - prev_dd
    peak_index = max(range(len(equities)), key=lambda idx: equities[idx])
    trough = min(equities[peak_index:]) if peak_index < len(equities) else equity
    recovery = max(ZERO, equity - trough)
    recent = values[-20:]
    recent_losses = sum(value < ZERO for value in recent)
    market = MarketStabilityEvidence(
        as_of=as_of,
        regime=str(situation.regime),
        transition=str(situation.transition),
        uncertainty_bps=latest.uncertainty_bps,
        contradiction_bps=latest.contradiction_bps,
        cross_market_confirmation_bps=latest.cross_market_confirmation_bps,
        failure_hypothesis_bps=_clip(
            (trajectory.adversity_bps + trajectory.deterioration_pressure_bps) // 2
        ),
        continuation_support_bps=trajectory.support_bps,
        anomaly_bps=latest.anomaly_bps,
    )
    telemetry = TraderStabilityTelemetry(
        trader_id="VT08_INDEX_FALSIFICATION_LAB",
        as_of=as_of,
        last_closed_trade_at=(None if not ordered else ordered[-1]["closed_at"]),
        current_drawdown_r=dd,
        drawdown_velocity_r=velocity,
        recovery_from_trough_r=recovery,
        recent_trade_count=len(recent),
        recent_loss_count=recent_losses,
        recent_net_r=sum(recent, ZERO),
        max_single_trade_risk_r=ONE,
    )
    return assess_drawdown_stability(telemetry, market)


def _memory_quality_bps(analog: object, phenotype: object) -> int:
    analog_quality = 5_000
    if analog.weighted_loss_rate is not None and analog.confidence_bps > 0:
        loss_rate = _d(analog.weighted_loss_rate)
        analog_quality = _clip(int((ONE - loss_rate) * Decimal(10_000)))
    phenotype_quality = 5_000
    if phenotype.recognition is DrawdownPhenotypeRecognition.KNOWN_PURE_LOSS:
        phenotype_quality = 1_500
    elif phenotype.recognition is DrawdownPhenotypeRecognition.KNOWN_LOSS_BIASED:
        phenotype_quality = 3_000
    elif phenotype.recognition is DrawdownPhenotypeRecognition.KNOWN_WINNER_OVERLAP:
        phenotype_quality = 6_500
    elif phenotype.recognition is DrawdownPhenotypeRecognition.KNOWN_AMBIGUOUS:
        phenotype_quality = 5_000
    return (analog_quality + phenotype_quality) // 2


def _future_quality_bps(
    geometry: FutureGeometryAssessment,
    futures: CompetingFutureAssessment,
) -> int:
    geometry_map = {
        FutureGeometryState.TERMINAL_COLLAPSE: 2_000,
        FutureGeometryState.RECOVERABLE_ADVERSITY: 5_500,
        FutureGeometryState.SUPPORTIVE_CONTINUATION: 8_000,
        FutureGeometryState.CONFLICTED: 4_500,
        FutureGeometryState.INSUFFICIENT: 5_000,
    }
    futures_map = {
        CompetingFutureState.TERMINAL_ADVERSE: 2_000,
        CompetingFutureState.RECOVERABLE_ADVERSE: 5_500,
        CompetingFutureState.SUPPORTIVE: 8_000,
        CompetingFutureState.CONFLICTED: 4_500,
        CompetingFutureState.INSUFFICIENT: 5_000,
    }
    return (geometry_map[geometry.state] + futures_map[futures.state]) // 2


def _stability_quality_bps(stability: object) -> int:
    value = stability.cognitive_state.value
    if value == "PASS":
        return 7_000
    if value == "WAIT":
        return 4_500
    return 2_000


def _entry_assessment(
    item: object,
    *,
    bars_by_symbol: dict[str, Sequence[object]],
    closed_by_symbol: dict[str, tuple[datetime, ...]],
    closed_memory: Sequence[dict[str, object]],
) -> dict[str, object]:
    signal = item.opportunity.signal
    as_of = signal.signal_at.astimezone(UTC)
    history = _history(
        item,
        bars_by_symbol=bars_by_symbol,
        closed_by_symbol=closed_by_symbol,
    )
    trajectory = _trajectory(history)
    environment = _environment(history)
    geometry = _geometry(history)
    futures = _competing_futures(history)
    perception, situation = _perception(
        item,
        bars_by_symbol=bars_by_symbol,
        closed_by_symbol=closed_by_symbol,
    )
    signature = _signature(
        situation=situation,
        trajectory=trajectory,
        environment=environment,
        geometry=geometry,
        futures=futures,
    )
    analog, phenotype = _memory(
        records=closed_memory,
        market=str(signal.symbol),
        as_of=as_of,
        signature=signature,
    )
    stability = _stability(
        records=closed_memory,
        as_of=as_of,
        situation=situation,
        latest=history[-1],
        trajectory=trajectory,
    )

    memory_quality = _memory_quality_bps(analog, phenotype)
    future_quality = _future_quality_bps(geometry, futures)
    stability_quality = _stability_quality_bps(stability)
    opportunity_quality = (
        environment.market_support_bps
        + trajectory.support_bps
        + memory_quality
        + future_quality
        + stability_quality
    ) // 5
    latest = history[-1]
    expansion_capacity = (
        latest.trend_support_bps
        + latest.momentum_bps
        + latest.displacement_bps
        + latest.cross_market_confirmation_bps
        + latest.volatility_stability_bps
        + (10_000 - latest.anomaly_bps)
    ) // 6
    instinct = assess_instinct(
        environment,
        trajectory,
        opportunity_quality_bps=_clip(opportunity_quality),
        expansion_capacity_bps=_clip(expansion_capacity),
        data_integrity_bps=min(item.data_integrity_bps for item in history),
    )

    return {
        "as_of": as_of,
        "history": history,
        "perception": perception,
        "situation": situation,
        "trajectory": trajectory,
        "environment": environment,
        "geometry": geometry,
        "futures": futures,
        "analog": analog,
        "phenotype": phenotype,
        "stability": stability,
        "signature": signature,
        "phenotype_views": _phenotype_views(signature),
        "memory_quality_bps": memory_quality,
        "future_quality_bps": future_quality,
        "opportunity_quality_bps": _clip(opportunity_quality),
        "expansion_capacity_bps": _clip(expansion_capacity),
        "instinct": instinct,
    }


def _signed_r(signal: object, price: Decimal) -> Decimal:
    risk = abs(_d(signal.entry) - _d(signal.stop))
    if risk <= ZERO:
        return ZERO
    if str(signal.side.value).lower() == "long":
        return (price - _d(signal.entry)) / risk
    return (_d(signal.entry) - price) / risk


def _post_entry_shadow(
    item: object,
    *,
    entry: dict[str, object],
    bars_by_symbol: dict[str, Sequence[object]],
    closed_by_symbol: dict[str, tuple[datetime, ...]],
) -> dict[str, object]:
    signal = item.opportunity.signal
    symbol = str(signal.symbol)
    side = str(signal.side.value).lower()
    risk = abs(_d(signal.entry) - _d(signal.stop))
    if risk <= ZERO:
        return {"observation_count": 0, "actions": {}, "first_action": None}

    all_bars = bars_by_symbol[symbol]
    closed = closed_by_symbol[symbol]
    start = bisect.bisect_right(closed, signal.signal_at.astimezone(UTC))
    end = bisect.bisect_right(closed, item.exited_at.astimezone(UTC))
    observed_bars = tuple(all_bars[start:end])
    if not observed_bars:
        return {"observation_count": 0, "actions": {}, "first_action": None}

    path_history: list[PositionPathObservation] = []
    action_rows: list[dict[str, object]] = []
    max_mfe = ZERO
    max_mae = ZERO

    for idx, bar in enumerate(observed_bars):
        as_of = bar.closed_at.astimezone(UTC)
        if side == "long":
            mfe = (_d(bar.high) - _d(signal.entry)) / risk
            mae = (_d(signal.entry) - _d(bar.low)) / risk
            body_r = (_d(bar.close) - _d(bar.open)) / risk
        else:
            mfe = (_d(signal.entry) - _d(bar.low)) / risk
            mae = (_d(bar.high) - _d(signal.entry)) / risk
            body_r = (_d(bar.open) - _d(bar.close)) / risk
        max_mfe = max(max_mfe, mfe)
        max_mae = max(max_mae, mae)
        close_r = _signed_r(signal, _d(bar.close))

        history = _history(
            item,
            bars_by_symbol=bars_by_symbol,
            closed_by_symbol=closed_by_symbol,
            as_of=as_of,
        )
        trajectory = _trajectory(history)
        environment = _environment(history)
        latest = history[-1]
        progress_bps = _clip(
            int(max(ZERO, max_mfe) / TARGET_R * Decimal(10_000))
        )
        close_support = _clip(int(Decimal(5_000) + close_r * Decimal(2_500)))
        favorable_body = _clip(
            int(max(ZERO, body_r) * Decimal(10_000))
        )
        adverse_body = _clip(
            int(max(ZERO, -body_r) * Decimal(10_000))
        )
        recovery_evidence = _clip(
            (trajectory.recovery_velocity_bps + environment.recovery_velocity_bps) // 2
        )
        path_history.append(
            PositionPathObservation(
                as_of=as_of,
                data_integrity_bps=latest.data_integrity_bps,
                journey_progress_bps=progress_bps,
                close_support_bps=close_support,
                directional_efficiency_bps=latest.momentum_bps,
                favorable_excursion_bps=progress_bps,
                adverse_excursion_bps=_clip(
                    int(max(ZERO, max_mae) * Decimal(10_000))
                ),
                favorable_body_bps=favorable_body,
                adverse_body_bps=adverse_body,
                market_support_bps=environment.market_support_bps,
                environment_adverse_bps=environment.adverse_environment_bps,
                recovery_evidence_bps=recovery_evidence,
            )
        )
        path = assess_position_path(
            tuple(path_history[-min(PATH_WINDOW, len(path_history)):])
        )
        journey = assess_position_journey(
            PositionJourneyEvidence(
                trader_id="VT08_INDEX_FALSIFICATION_LAB",
                market=symbol,
                side=side.upper(),
                opened_at=signal.signal_at.astimezone(UTC),
                as_of=as_of,
                data_integrity_bps=latest.data_integrity_bps,
                regime_stability_bps=_clip(
                    (environment.market_support_bps + trajectory.support_bps) // 2
                ),
                expansion_bps=progress_bps,
                displacement_bps=latest.displacement_bps,
                momentum_bps=latest.momentum_bps,
                liquidity_capacity_bps=latest.liquidity_capacity_bps,
                cross_market_confirmation_bps=latest.cross_market_confirmation_bps,
                exhaustion_bps=environment.adverse_environment_bps,
                opposite_displacement_bps=latest.opposite_pressure_bps,
                contradiction_bps=latest.contradiction_bps,
                anomaly_bps=latest.anomaly_bps,
                uncertainty_bps=latest.uncertainty_bps,
            )
        )
        expansion_capacity = (
            latest.trend_support_bps
            + latest.momentum_bps
            + latest.displacement_bps
            + latest.cross_market_confirmation_bps
            + latest.volatility_stability_bps
            + (10_000 - latest.anomaly_bps)
        ) // 6
        instinct = assess_instinct(
            environment,
            trajectory,
            path=path,
            opportunity_quality_bps=int(entry["opportunity_quality_bps"]),
            expansion_capacity_bps=_clip(expansion_capacity),
            data_integrity_bps=latest.data_integrity_bps,
        )
        directive = assess_realtime_trade_management(
            instinct,
            journey,
            path,
            progress_bps=progress_bps,
            data_integrity_bps=latest.data_integrity_bps,
        )
        action_rows.append(
            {
                "as_of": as_of.isoformat(),
                "bar_index": idx + 1,
                "bars_before_canonical_exit": len(observed_bars) - idx - 1,
                "action": directive.action.value,
                "stop_mode": directive.stop_mode.value,
                "target_mode": directive.target_mode.value,
                "path_state": path.state.value,
                "journey": journey.disposition.value,
                "instinct": instinct.situation.value,
                "support_methodology": instinct.support_methodology.value,
                "progress_bps": progress_bps,
                "threat_bps": instinct.threat_bps,
                "winner_protection_bps": path.winner_protection_bps,
                "extension_capacity_bps": instinct.expansion_capacity_bps,
            }
        )

    counts = Counter(str(row["action"]) for row in action_rows)
    actionable = [
        row for row in action_rows
        if row["action"] not in {
            RealtimeTradeAction.HOLD.value,
            RealtimeTradeAction.INSUFFICIENT.value,
        }
    ]
    defense = [
        row for row in action_rows
        if row["action"] in {
            RealtimeTradeAction.DEFEND.value,
            RealtimeTradeAction.EXIT_RISK.value,
        }
    ]
    extension = [
        row for row in action_rows
        if row["action"] in {
            RealtimeTradeAction.EXTEND.value,
            RealtimeTradeAction.TRAIL_AND_EXTEND.value,
        }
    ]
    winner_protect = [
        row for row in action_rows
        if row["action"] in {
            RealtimeTradeAction.TRAIL.value,
            RealtimeTradeAction.TRAIL_AND_EXTEND.value,
        }
    ]
    return {
        "observation_count": len(action_rows),
        "actions": dict(sorted(counts.items())),
        "first_action": None if not actionable else actionable[0],
        "first_defense": None if not defense else defense[0],
        "first_extension": None if not extension else extension[0],
        "first_winner_protection": None if not winner_protect else winner_protect[0],
        "rows": action_rows,
    }


def _cohort(rows: Sequence[object]) -> dict[str, object]:
    if not rows:
        return {"sample": 0, "primary": None, "secondary": None}
    bundle = v2.r108._cohort_bundle(tuple(rows))
    return {
        "sample": len(rows),
        "primary": bundle["primary"],
        "secondary": bundle["secondary"],
    }


def _window(
    *,
    roots: dict[str, Path],
    window_id: str,
) -> dict[str, object]:
    canonical, bars_raw, provenance = v2.r74._load_window(
        roots=roots,
        window_id=window_id,
    )
    start_date, end_date, expected = v2.r74._window_contract(window_id)
    bars_by_symbol = {
        symbol: tuple(rows)
        for symbol, rows in bars_raw.items()
    }
    opened_by_symbol = {
        symbol: tuple(bar.opened_at.astimezone(UTC) for bar in rows)
        for symbol, rows in bars_by_symbol.items()
    }
    closed_by_symbol = {
        symbol: tuple(bar.closed_at.astimezone(UTC) for bar in rows)
        for symbol, rows in bars_by_symbol.items()
    }
    base, _ = v2.r58._exact_r47(
        tuple(canonical),
        bars_by_symbol=bars_by_symbol,
    )
    control, _ = v2.r102._apply_confidence_policy(
        tuple(base),
        bars_by_symbol=bars_by_symbol,
        policy_id=v2.r102.POLICY_EXPLICIT_FULL,
    )
    control = v2._unitize(tuple(control))
    if len(control) != expected:
        raise ValueError(f"VT08 Shared V3 {window_id} density drift")

    ordered = tuple(
        sorted(
            control,
            key=lambda item: (
                item.opportunity.signal.signal_at.astimezone(UTC),
                item.trade_id,
            ),
        )
    )
    pending: list[tuple[datetime, int, dict[str, object]]] = []
    closed_memory: list[dict[str, object]] = []
    rows: list[dict[str, object]] = []
    cohorts: dict[str, list[object]] = defaultdict(list)

    for item in ordered:
        signal_at = item.opportunity.signal.signal_at.astimezone(UTC)
        while pending and pending[0][0] <= signal_at:
            _closed_at, _trade_id, record = heapq.heappop(pending)
            closed_memory.append(record)

        entry = _entry_assessment(
            item,
            bars_by_symbol=bars_by_symbol,
            closed_by_symbol=closed_by_symbol,
            closed_memory=closed_memory,
        )
        post = _post_entry_shadow(
            item,
            entry=entry,
            bars_by_symbol=bars_by_symbol,
            closed_by_symbol=closed_by_symbol,
        )
        instinct: InstinctAssessment = entry["instinct"]
        cohort_key = instinct.support_methodology.value
        cohorts[cohort_key].append(item)

        terminal_r = _d(item.outcome.r_multiple)
        outcome = "LOSS" if terminal_r < ZERO else "WIN" if terminal_r > ZERO else "FLAT"
        first_defense = post["first_defense"]
        first_extension = post["first_extension"]
        first_protection = post["first_winner_protection"]
        rows.append(
            {
                "trade_id": item.trade_id,
                "market": item.symbol,
                "signal_at": signal_at.isoformat(),
                "exited_at": item.exited_at.astimezone(UTC).isoformat(),
                "terminal_r": str(terminal_r),
                "outcome": outcome,
                "support_methodology": instinct.support_methodology.value,
                "instinct_situation": instinct.situation.value,
                "opportunity_quality_bps": entry["opportunity_quality_bps"],
                "expansion_capacity_bps": entry["expansion_capacity_bps"],
                "trajectory_state": entry["trajectory"].state.value,
                "environment_state": entry["environment"].state.value,
                "geometry_state": entry["geometry"].state.value,
                "future_state": entry["futures"].state.value,
                "regime": entry["situation"].regime,
                "regime_transition": entry["situation"].transition,
                "stability_mode": entry["stability"].mode.value,
                "stability_cognitive_state": entry["stability"].cognitive_state.value,
                "analog_confidence_bps": entry["analog"].confidence_bps,
                "analog_loss_rate": entry["analog"].weighted_loss_rate,
                "phenotype_recognition": entry["phenotype"].recognition.value,
                "phenotype_confidence_bps": entry["phenotype"].confidence_bps,
                "post_entry_observations": post["observation_count"],
                "management_actions": post["actions"],
                "first_defense": first_defense,
                "first_extension": first_extension,
                "first_winner_protection": first_protection,
            }
        )

        record = {
            "episode_id": f"{window_id}:{item.trade_id}",
            "market": str(item.symbol),
            "closed_at": item.exited_at.astimezone(UTC),
            "terminal_r": terminal_r,
            "signature": entry["signature"],
            "phenotype_views": entry["phenotype_views"],
        }
        heapq.heappush(
            pending,
            (item.exited_at.astimezone(UTC), item.trade_id, record),
        )

    baseline = v2.r108._bundle(
        control,
        bars_by_symbol=bars_by_symbol,
        opened_by_symbol=opened_by_symbol,
        window_id=window_id,
        start_date=start_date,
        end_date=end_date,
    )

    losses = [row for row in rows if row["outcome"] == "LOSS"]
    winners = [row for row in rows if row["outcome"] == "WIN"]
    loss_defended = [row for row in losses if row["first_defense"] is not None]
    winner_false_defense = [row for row in winners if row["first_defense"] is not None]
    winner_extensions = [row for row in winners if row["first_extension"] is not None]
    winner_protection = [
        row for row in winners if row["first_winner_protection"] is not None
    ]

    return {
        "window_id": window_id,
        "sample": len(control),
        "canonical_expected": expected,
        "density_retained_shadow": "1",
        "baseline": baseline,
        "support_methodology_counts": dict(
            sorted(Counter(row["support_methodology"] for row in rows).items())
        ),
        "instinct_situation_counts": dict(
            sorted(Counter(row["instinct_situation"] for row in rows).items())
        ),
        "trajectory_counts": dict(
            sorted(Counter(row["trajectory_state"] for row in rows).items())
        ),
        "environment_counts": dict(
            sorted(Counter(row["environment_state"] for row in rows).items())
        ),
        "geometry_counts": dict(
            sorted(Counter(row["geometry_state"] for row in rows).items())
        ),
        "future_counts": dict(
            sorted(Counter(row["future_state"] for row in rows).items())
        ),
        "stability_counts": dict(
            sorted(Counter(row["stability_cognitive_state"] for row in rows).items())
        ),
        "phenotype_counts": dict(
            sorted(Counter(row["phenotype_recognition"] for row in rows).items())
        ),
        "cohort_economics_by_support_methodology": {
            key: _cohort(value)
            for key, value in sorted(cohorts.items())
        },
        "management_falsification": {
            "losses": len(losses),
            "winners": len(winners),
            "losses_with_causal_defense_before_canonical_exit": len(loss_defended),
            "loss_defense_recall": (
                "0"
                if not losses
                else str(Decimal(len(loss_defended)) / Decimal(len(losses)))
            ),
            "winners_with_false_defense": len(winner_false_defense),
            "winner_false_defense_rate": (
                "0"
                if not winners
                else str(
                    Decimal(len(winner_false_defense)) / Decimal(len(winners))
                )
            ),
            "winners_with_extension_support": len(winner_extensions),
            "winner_extension_recall": (
                "0"
                if not winners
                else str(Decimal(len(winner_extensions)) / Decimal(len(winners)))
            ),
            "winners_with_protection": len(winner_protection),
            "winner_protection_recall": (
                "0"
                if not winners
                else str(Decimal(len(winner_protection)) / Decimal(len(winners)))
            ),
        },
        "rows": rows,
        "provenance": provenance,
    }


def run(
    *,
    nas100_root: Path,
    sp500_root: Path,
    us30_root: Path,
) -> dict[str, object]:
    roots = {
        "NAS100": nas100_root,
        "SP500": sp500_root,
        "US30": us30_root,
    }
    five = _window(roots=roots, window_id="five_year")
    recent = _window(roots=roots, window_id="recent_two_year")
    r66 = _window(roots=roots, window_id="r66_consumed_failed_holdout")
    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "challenge": {
            "source_pr": VT08_PR,
            "source_head": VT08_HEAD,
            "shared_is_cognitive_engine": True,
            "vt08_cognition_used_by_shared": False,
            "vt31_cognition_used_by_shared": False,
            "vt08_role": "METHODOLOGY_VALID_OPPORTUNITY_AND_FALSIFICATION_SURFACE_ONLY",
            "official_book": "UNIT_R_EQUAL_RISK_PER_OPPORTUNITY",
            "same_initial_position_size": True,
            "sizing_used": False,
            "capital_weighting_used": False,
            "risk_weighting_used": False,
            "shared_sizing_authority": False,
            "entry_signal_population_changed": False,
            "shadow_only": True,
            "outcome_used_before_current_trade_closed": False,
            "future_market_used_by_runtime_assessment": False,
        },
        "shared_extended_capabilities_exercised": (
            "PERCEPTION_ENGINE",
            "REGIME_AND_TRANSITION_INTELLIGENCE",
            "DYNAMIC_MARKET_DETERIORATION_RECOVERY_INTELLIGENCE",
            "ADVERSE_MARKET_ENVIRONMENT_INTELLIGENCE",
            "GLOBAL_CROSS_MARKET_INTELLIGENCE",
            "MULTI_HORIZON_COMPETING_FUTURES_INTELLIGENCE",
            "MULTI_AXIS_FUTURE_GEOMETRY_INTELLIGENCE",
            "HISTORICAL_CAUSAL_ANALOG_MEMORY",
            "UNIVERSAL_DRAWDOWN_PHENOTYPE_MEMORY",
            "UNIVERSAL_DRAWDOWN_STABILITY_INTELLIGENCE",
            "OPPORTUNITY_QUALITY_INTELLIGENCE",
            "ULTRAFAST_INSTINCT_HOT_PATH_INTELLIGENCE",
            "CAUSAL_POSITION_PATH_ASYMMETRY_INTELLIGENCE",
            "UNIVERSAL_POSITION_JOURNEY_INTELLIGENCE",
            "WINNER_PROTECTION_INTELLIGENCE",
            "MARKET_EXPANSION_CAPACITY_INTELLIGENCE",
            "REALTIME_TRAILING_AND_TARGET_MANAGEMENT_INTELLIGENCE_SHADOW",
        ),
        "five_year": five,
        "recent_two_year": recent,
        "r66_consumed_failed_holdout": r66,
        "governance": {
            "research_only": True,
            "consumed_evidence_only": True,
            "fresh_holdout_opened": False,
            "sizing_forbidden": True,
            "sizing_used": False,
            "capital_weighting_used": False,
            "risk_budget_changed": False,
            "vt08_methodology_modified": False,
            "shared_order_authority": False,
            "shared_risk_authority": False,
            "live_authorized": False,
            "production_authorized": False,
            "real_capital_authorized": False,
            "merge_authorized": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--nas100-root", type=Path, required=True)
    parser.add_argument("--sp500-root", type=Path, required=True)
    parser.add_argument("--us30-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    payload = run(
        nas100_root=args.nas100_root,
        sp500_root=args.sp500_root,
        us30_root=args.us30_root,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(_jsonable(payload), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "identity": payload["identity"],
                "five_year": {
                    "support_methodology_counts": payload["five_year"]["support_methodology_counts"],
                    "management": payload["five_year"]["management_falsification"],
                },
                "recent_two_year": {
                    "support_methodology_counts": payload["recent_two_year"]["support_methodology_counts"],
                    "management": payload["recent_two_year"]["management_falsification"],
                },
                "r66": {
                    "support_methodology_counts": payload["r66_consumed_failed_holdout"]["support_methodology_counts"],
                    "management": payload["r66_consumed_failed_holdout"]["management_falsification"],
                },
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
