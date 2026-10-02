# ruff: noqa: I001
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from dataclasses import replace

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
    build_market_digital_twin,
)
from qore.infrastructure.core_stack_v2.market_digital_twin_history import (
    append_market_digital_twin_snapshot,
    empty_market_digital_twin_history,
    verify_market_digital_twin_history,
)


BASE = datetime(2026, 9, 26, 3, 0, tzinfo=UTC)


def _snapshot(
    *,
    as_of: datetime,
    prediction_observed: bool,
):
    prediction = TwinPrediction(
        prediction_id="p1",
        channel="EXPECTED_DISPLACEMENT",
        made_at=BASE - timedelta(minutes=2),
        target_at=BASE - timedelta(minutes=1),
        expected_bps=7_500,
        tolerance_bps=1_000,
        model_family="MOMENTUM_WORLD",
    )
    observations = (
        (
            TwinObservation(
                prediction_id="p1",
                channel="EXPECTED_DISPLACEMENT",
                observed_at=BASE - timedelta(seconds=30),
                observed_bps=4_000,
            ),
        )
        if prediction_observed
        else ()
    )
    cutoff = as_of - timedelta(seconds=1)
    return build_market_digital_twin(
        as_of=as_of,
        evidence_cutoff_at=cutoff,
        observable_state=(
            TwinStateValue(
                concept="OBSERVED_STRUCTURE",
                probability_bps=6_000,
                confidence_bps=7_000,
                evidence_cutoff_at=cutoff,
            ),
        ),
        latent_state=(
            TwinStateValue(
                concept="LATENT_PRESSURE",
                probability_bps=6_500,
                confidence_bps=5_500,
                evidence_cutoff_at=cutoff,
            ),
        ),
        behavior_hypotheses=(
            BehaviorHypothesis(
                behavior="UNKNOWN_AGENCY",
                probability_bps=5_000,
                confidence_bps=2_000,
                supporting_evidence=("OBSERVED_STRUCTURE",),
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
        predictions=(prediction,),
        observations=observations,
    )


def test_twin_history_is_deterministic_and_verifiable() -> None:
    first = _snapshot(
        as_of=BASE,
        prediction_observed=True,
    )
    second = _snapshot(
        as_of=BASE + timedelta(minutes=1),
        prediction_observed=True,
    )

    left = append_market_digital_twin_snapshot(
        empty_market_digital_twin_history(),
        first,
    )
    left = append_market_digital_twin_snapshot(left, second)

    right = append_market_digital_twin_snapshot(
        empty_market_digital_twin_history(),
        first,
    )
    right = append_market_digital_twin_snapshot(right, second)

    verify_market_digital_twin_history(left)
    verify_market_digital_twin_history(right)

    assert left.head_lineage_hash == right.head_lineage_hash
    assert left.entries[-1].cumulative_prediction_error_ids == ("p1",)
    assert left.execution_authority is False


def test_matured_prediction_error_cannot_disappear() -> None:
    first = _snapshot(
        as_of=BASE,
        prediction_observed=True,
    )
    second_without_error = _snapshot(
        as_of=BASE + timedelta(minutes=1),
        prediction_observed=False,
    )
    history = append_market_digital_twin_snapshot(
        empty_market_digital_twin_history(),
        first,
    )

    with pytest.raises(ValueError, match="cannot disappear"):
        append_market_digital_twin_snapshot(history, second_without_error)


def test_time_regression_fails_closed() -> None:
    first = _snapshot(
        as_of=BASE,
        prediction_observed=True,
    )
    history = append_market_digital_twin_snapshot(
        empty_market_digital_twin_history(),
        first,
    )

    with pytest.raises(ValueError, match="advance strictly in time"):
        append_market_digital_twin_snapshot(history, first)


def test_lineage_tampering_is_detected() -> None:
    first = _snapshot(
        as_of=BASE,
        prediction_observed=True,
    )
    history = append_market_digital_twin_snapshot(
        empty_market_digital_twin_history(),
        first,
    )
    tampered_entry = replace(
        history.entries[0],
        lineage_hash="0" * 64,
    )
    tampered = replace(
        history,
        entries=(tampered_entry,),
        head_lineage_hash="0" * 64,
    )

    with pytest.raises(ValueError, match="lineage hash mismatch"):
        verify_market_digital_twin_history(tampered)
