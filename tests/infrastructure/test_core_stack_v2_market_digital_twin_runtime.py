# ruff: noqa: I001
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from qore.infrastructure.core_stack_v2.market_digital_twin import (
    BehaviorHypothesis,
    ExpectedStateTransition,
    LiquidityTopology,
    RegimeStructure,
    TwinObservation,
    TwinPrediction,
    TwinStateValue,
    TwinUncertainty,
    VolatilityTopology,
)
from qore.infrastructure.core_stack_v2.market_digital_twin_runtime import (
    MarketDigitalTwinUpdate,
    advance_market_digital_twin,
    empty_market_digital_twin_runtime,
    replay_market_digital_twin,
)


BASE = datetime(2026, 9, 26, 3, 0, tzinfo=UTC)


def _update(
    *,
    as_of: datetime,
    new_predictions: tuple[TwinPrediction, ...] = (),
    new_observations: tuple[TwinObservation, ...] = (),
) -> MarketDigitalTwinUpdate:
    cutoff = as_of - timedelta(seconds=1)
    return MarketDigitalTwinUpdate(
        as_of=as_of,
        evidence_cutoff_at=cutoff,
        observable_state=(
            TwinStateValue(
                "OBSERVED_STRUCTURE",
                6_000,
                7_000,
                cutoff,
            ),
        ),
        latent_state=(
            TwinStateValue(
                "LATENT_PRESSURE",
                6_500,
                5_500,
                cutoff,
            ),
        ),
        behavior_hypotheses=(
            BehaviorHypothesis(
                "UNKNOWN_AGENCY",
                5_000,
                2_000,
                ("OBSERVED_STRUCTURE",),
            ),
        ),
        liquidity_topology=LiquidityTopology(
            6_000,
            5_500,
            3_000,
            2_000,
            5_000,
            9_000,
        ),
        volatility_topology=VolatilityTopology(
            5_500,
            5_000,
            3_000,
            2_000,
            6_000,
            9_000,
        ),
        cross_market_dependencies=(),
        regime_structure=RegimeStructure(
            "TRANSITION",
            4_000,
            7_000,
            2_000,
            6_000,
        ),
        uncertainty=TwinUncertainty(
            3_000,
            3_000,
            2_500,
            1_500,
        ),
        expected_transitions=(
            ExpectedStateTransition(
                3,
                "CONTINUATION",
                6_000,
                5_500,
            ),
        ),
        new_predictions=new_predictions,
        new_observations=new_observations,
    )


def test_runtime_carries_prediction_forward_until_observed() -> None:
    prediction = TwinPrediction(
        prediction_id="p1",
        channel="EXPECTED_DISPLACEMENT",
        made_at=BASE,
        target_at=BASE + timedelta(minutes=1),
        expected_bps=7_500,
        tolerance_bps=1_000,
        model_family="MOMENTUM_WORLD",
    )
    first = _update(
        as_of=BASE,
        new_predictions=(prediction,),
    )
    second = _update(
        as_of=BASE + timedelta(minutes=2),
        new_observations=(
            TwinObservation(
                prediction_id="p1",
                channel="EXPECTED_DISPLACEMENT",
                observed_at=BASE + timedelta(minutes=1, seconds=30),
                observed_bps=4_000,
            ),
        ),
    )

    runtime = empty_market_digital_twin_runtime()
    runtime = advance_market_digital_twin(runtime, first)
    assert runtime.history.snapshots[-1].unresolved_prediction_ids == ("p1",)

    runtime = advance_market_digital_twin(runtime, second)
    assert runtime.history.snapshots[-1].unresolved_prediction_ids == ()
    assert (
        runtime.history.snapshots[-1]
        .prediction_error_ledger[0]
        .prediction_id
        == "p1"
    )


def test_replay_is_deterministic() -> None:
    prediction = TwinPrediction(
        prediction_id="p1",
        channel="EXPECTED_VOLATILITY",
        made_at=BASE,
        target_at=BASE + timedelta(minutes=1),
        expected_bps=5_000,
        tolerance_bps=1_000,
        model_family="LIQUIDITY_WORLD",
    )
    updates = (
        _update(
            as_of=BASE,
            new_predictions=(prediction,),
        ),
        _update(
            as_of=BASE + timedelta(minutes=2),
            new_observations=(
                TwinObservation(
                    prediction_id="p1",
                    channel="EXPECTED_VOLATILITY",
                    observed_at=BASE + timedelta(minutes=1, seconds=30),
                    observed_bps=5_500,
                ),
            ),
        ),
    )

    left = replay_market_digital_twin(updates)
    right = replay_market_digital_twin(updates)

    assert left.history.head_lineage_hash == right.history.head_lineage_hash
    assert (
        left.history.head_snapshot_fingerprint
        == right.history.head_snapshot_fingerprint
    )
    assert left.execution_authority is False


def test_unknown_observation_fails_closed() -> None:
    update = _update(
        as_of=BASE,
        new_observations=(
            TwinObservation(
                prediction_id="unknown",
                channel="EXPECTED_VOLATILITY",
                observed_at=BASE,
                observed_bps=5_000,
            ),
        ),
    )

    with pytest.raises(ValueError, match="unknown prediction"):
        advance_market_digital_twin(
            empty_market_digital_twin_runtime(),
            update,
        )


def test_time_regression_fails_closed() -> None:
    runtime = advance_market_digital_twin(
        empty_market_digital_twin_runtime(),
        _update(as_of=BASE),
    )

    with pytest.raises(ValueError, match="advance strictly in time"):
        advance_market_digital_twin(
            runtime,
            _update(as_of=BASE),
        )


def test_future_observation_cannot_enter_update_packet() -> None:
    with pytest.raises(ValueError, match="future observation"):
        _update(
            as_of=BASE,
            new_observations=(
                TwinObservation(
                    prediction_id="p1",
                    channel="EXPECTED_VOLATILITY",
                    observed_at=BASE + timedelta(seconds=1),
                    observed_bps=5_000,
                ),
            ),
        )
