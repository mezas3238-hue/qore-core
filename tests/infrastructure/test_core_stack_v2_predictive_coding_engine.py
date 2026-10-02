from __future__ import annotations

from qore.infrastructure.core_stack_v2.predictive_coding_engine import (
    PredictiveChannel,
    PredictiveExpectation,
    PredictiveObservation,
    compute_predictive_coding_state,
)


def test_large_expected_observed_gap_creates_revision_pressure() -> None:
    state = compute_predictive_coding_state(
        expectations=(
            PredictiveExpectation(
                PredictiveChannel.DISPLACEMENT,
                expected_bps=8_000,
                tolerance_bps=1_000,
            ),
            PredictiveExpectation(
                PredictiveChannel.INTERMARKET_REACTION,
                expected_bps=7_500,
                tolerance_bps=1_000,
            ),
        ),
        observations=(
            PredictiveObservation(
                PredictiveChannel.DISPLACEMENT,
                observed_bps=3_000,
            ),
            PredictiveObservation(
                PredictiveChannel.INTERMARKET_REACTION,
                observed_bps=3_500,
            ),
        ),
    )

    assert state.aggregate_surprise_bps > 7_000
    assert state.model_revision_pressure_bps >= state.aggregate_surprise_bps
    assert state.execution_authority is False


def test_matching_prediction_has_low_surprise() -> None:
    state = compute_predictive_coding_state(
        expectations=(
            PredictiveExpectation(
                PredictiveChannel.VOLATILITY,
                expected_bps=5_000,
                tolerance_bps=1_000,
            ),
        ),
        observations=(
            PredictiveObservation(
                PredictiveChannel.VOLATILITY,
                observed_bps=5_100,
            ),
        ),
    )

    assert state.aggregate_surprise_bps <= 1_000
