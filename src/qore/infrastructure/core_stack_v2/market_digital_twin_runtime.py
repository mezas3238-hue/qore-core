"""Deterministic update runtime for the probabilistic Market Digital Twin.

WP-01 needs a living twin, not a collection of unrelated snapshots.

This runtime is a pure, immutable state machine:
- ingest new point-in-time evidence;
- register new predictions;
- register observations only when they actually exist;
- rebuild the twin from the full causal registry available at that timestamp;
- append the new snapshot to a hash-chained lineage;
- replay the same update packets deterministically.

It contains no broker, order, Risk, sizing, stop, target or execution authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from qore.infrastructure.core_stack_v2.market_digital_twin import (
    BehaviorHypothesis,
    CrossMarketDependency,
    ExpectedStateTransition,
    LiquidityTopology,
    RegimeStructure,
    TwinObservation,
    TwinPrediction,
    TwinStateValue,
    TwinUncertainty,
    VolatilityTopology,
    build_market_digital_twin,
)
from qore.infrastructure.core_stack_v2.market_digital_twin_history import (
    MarketDigitalTwinHistory,
    append_market_digital_twin_snapshot,
    empty_market_digital_twin_history,
    verify_market_digital_twin_history,
)


@dataclass(frozen=True, slots=True)
class MarketDigitalTwinUpdate:
    as_of: datetime
    evidence_cutoff_at: datetime
    observable_state: tuple[TwinStateValue, ...]
    latent_state: tuple[TwinStateValue, ...]
    behavior_hypotheses: tuple[BehaviorHypothesis, ...]
    liquidity_topology: LiquidityTopology
    volatility_topology: VolatilityTopology
    cross_market_dependencies: tuple[CrossMarketDependency, ...]
    regime_structure: RegimeStructure
    uncertainty: TwinUncertainty
    expected_transitions: tuple[ExpectedStateTransition, ...]
    new_predictions: tuple[TwinPrediction, ...] = ()
    new_observations: tuple[TwinObservation, ...] = ()

    def __post_init__(self) -> None:
        if self.as_of.tzinfo is None or self.as_of.utcoffset() is None:
            raise ValueError("update as_of must be timezone-aware")
        if (
            self.evidence_cutoff_at.tzinfo is None
            or self.evidence_cutoff_at.utcoffset() is None
        ):
            raise ValueError("update evidence_cutoff_at must be timezone-aware")
        if self.evidence_cutoff_at > self.as_of:
            raise ValueError("update evidence cutoff cannot be in the future")
        if any(item.made_at > self.as_of for item in self.new_predictions):
            raise ValueError("future prediction cannot be registered")
        if any(
            item.observed_at > self.as_of
            for item in self.new_observations
        ):
            raise ValueError("future observation cannot be registered")


@dataclass(frozen=True, slots=True)
class MarketDigitalTwinRuntime:
    history: MarketDigitalTwinHistory
    predictions: tuple[TwinPrediction, ...]
    observations: tuple[TwinObservation, ...]
    last_as_of: datetime | None
    outcome_used: bool = False
    pnl_used: bool = False
    future_market_used: bool = False
    sizing_authority: bool = False
    risk_authority: bool = False
    order_authority: bool = False
    execution_authority: bool = False

    def __post_init__(self) -> None:
        if self.last_as_of is None and self.history.snapshots:
            raise ValueError("non-empty runtime history requires last_as_of")
        if self.last_as_of is not None:
            if self.last_as_of.tzinfo is None or self.last_as_of.utcoffset() is None:
                raise ValueError("last_as_of must be timezone-aware")
            if (
                not self.history.snapshots
                or self.history.snapshots[-1].as_of != self.last_as_of
            ):
                raise ValueError("runtime last_as_of does not match history head")
        if (
            self.outcome_used
            or self.pnl_used
            or self.future_market_used
            or self.sizing_authority
            or self.risk_authority
            or self.order_authority
            or self.execution_authority
        ):
            raise ValueError("digital twin runtime cannot carry trading authority")


def empty_market_digital_twin_runtime() -> MarketDigitalTwinRuntime:
    return MarketDigitalTwinRuntime(
        history=empty_market_digital_twin_history(),
        predictions=(),
        observations=(),
        last_as_of=None,
    )


def _merge_predictions(
    current: tuple[TwinPrediction, ...],
    new: tuple[TwinPrediction, ...],
) -> tuple[TwinPrediction, ...]:
    merged = {item.prediction_id: item for item in current}
    for item in new:
        if item.prediction_id in merged:
            if merged[item.prediction_id] != item:
                raise ValueError(
                    f"prediction id reused with different payload: {item.prediction_id}"
                )
            continue
        merged[item.prediction_id] = item
    return tuple(
        sorted(
            merged.values(),
            key=lambda item: (item.made_at, item.prediction_id),
        )
    )


def _merge_observations(
    current: tuple[TwinObservation, ...],
    new: tuple[TwinObservation, ...],
    predictions: tuple[TwinPrediction, ...],
) -> tuple[TwinObservation, ...]:
    known_predictions = {item.prediction_id for item in predictions}
    merged = {item.prediction_id: item for item in current}
    for item in new:
        if item.prediction_id not in known_predictions:
            raise ValueError(
                f"observation references unknown prediction: {item.prediction_id}"
            )
        if item.prediction_id in merged:
            if merged[item.prediction_id] != item:
                raise ValueError(
                    "observation id reused with different payload: "
                    f"{item.prediction_id}"
                )
            continue
        merged[item.prediction_id] = item
    return tuple(
        sorted(
            merged.values(),
            key=lambda item: (item.observed_at, item.prediction_id),
        )
    )


def advance_market_digital_twin(
    runtime: MarketDigitalTwinRuntime,
    update: MarketDigitalTwinUpdate,
) -> MarketDigitalTwinRuntime:
    """Advance the living twin by one causal update."""

    if runtime.last_as_of is not None and update.as_of <= runtime.last_as_of:
        raise ValueError("digital twin runtime must advance strictly in time")

    predictions = _merge_predictions(
        runtime.predictions,
        update.new_predictions,
    )
    observations = _merge_observations(
        runtime.observations,
        update.new_observations,
        predictions,
    )

    snapshot = build_market_digital_twin(
        as_of=update.as_of,
        evidence_cutoff_at=update.evidence_cutoff_at,
        observable_state=update.observable_state,
        latent_state=update.latent_state,
        behavior_hypotheses=update.behavior_hypotheses,
        liquidity_topology=update.liquidity_topology,
        volatility_topology=update.volatility_topology,
        cross_market_dependencies=update.cross_market_dependencies,
        regime_structure=update.regime_structure,
        uncertainty=update.uncertainty,
        expected_transitions=update.expected_transitions,
        predictions=predictions,
        observations=observations,
    )
    history = append_market_digital_twin_snapshot(
        runtime.history,
        snapshot,
    )
    verify_market_digital_twin_history(history)

    return MarketDigitalTwinRuntime(
        history=history,
        predictions=predictions,
        observations=observations,
        last_as_of=update.as_of,
    )


def replay_market_digital_twin(
    updates: tuple[MarketDigitalTwinUpdate, ...],
) -> MarketDigitalTwinRuntime:
    """Replay a causal update stream deterministically from genesis."""

    runtime = empty_market_digital_twin_runtime()
    for update in updates:
        runtime = advance_market_digital_twin(runtime, update)
    return runtime
