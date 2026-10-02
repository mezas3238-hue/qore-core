from __future__ import annotations

from qore.infrastructure.core_stack_v2.multi_world_engine import (
    WorldModelEvidence,
    WorldModelFamily,
    update_multi_world_state,
)


def test_best_explaining_world_receives_most_probability() -> None:
    state = update_multi_world_state(
        (
            WorldModelEvidence(
                WorldModelFamily.LIQUIDITY_DRIVEN,
                prediction_error_bps=1_000,
                causal_consistency_bps=8_500,
                calibration_bps=8_000,
                trajectory_accuracy_bps=8_500,
            ),
            WorldModelEvidence(
                WorldModelFamily.MOMENTUM_DRIVEN,
                prediction_error_bps=4_500,
                causal_consistency_bps=5_000,
                calibration_bps=5_500,
                trajectory_accuracy_bps=5_000,
            ),
            WorldModelEvidence(
                WorldModelFamily.UNRESOLVED,
                prediction_error_bps=5_000,
                causal_consistency_bps=5_000,
                calibration_bps=5_000,
                trajectory_accuracy_bps=5_000,
            ),
        )
    )

    assert state.dominant_world is WorldModelFamily.LIQUIDITY_DRIVEN
    assert sum(item.probability_bps for item in state.posteriors) == 10_000
    assert state.execution_authority is False


def test_close_world_scores_raise_disagreement() -> None:
    state = update_multi_world_state(
        (
            WorldModelEvidence(
                WorldModelFamily.LIQUIDITY_DRIVEN,
                prediction_error_bps=2_000,
                causal_consistency_bps=7_000,
                calibration_bps=7_000,
                trajectory_accuracy_bps=7_000,
            ),
            WorldModelEvidence(
                WorldModelFamily.MOMENTUM_DRIVEN,
                prediction_error_bps=2_200,
                causal_consistency_bps=6_900,
                calibration_bps=7_000,
                trajectory_accuracy_bps=7_000,
            ),
        )
    )

    assert state.disagreement_bps > 8_000
