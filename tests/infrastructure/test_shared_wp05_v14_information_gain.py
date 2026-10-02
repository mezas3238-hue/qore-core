from __future__ import annotations

from qore.infrastructure.core_stack_v2.active_perception_v14_information_gain import (
    V14_CALIBRATION_TRUE_CONFIRMATION_RETENTION_BPS,
    evaluate_v14_fold,
    select_v14_peer_confirmation_threshold_micros,
)


def test_v14_threshold_is_highest_observed_score_preserving_9800_bps() -> None:
    scores = [100] * 98 + [10] * 2
    threshold, retention = select_v14_peer_confirmation_threshold_micros(scores)
    assert threshold == 100
    assert retention == V14_CALIBRATION_TRUE_CONFIRMATION_RETENTION_BPS


def test_v14_fold_requires_v11_and_peer_confirmation() -> None:
    result = evaluate_v14_fold(
        fold_index=0,
        labels=(True, True, False, False),
        baseline_confirmation_minutes=(3, 5, 3, 5),
        peer_confirmation_scores_micros=(100, 100, 100, -100),
        peer_confirmation_threshold_micros=0,
    )
    assert result.baseline_true_confirmation_count == 2
    assert result.baseline_false_confirmation_count == 2
    assert result.v14_true_confirmation_count == 2
    assert result.v14_false_confirmation_count == 1
    assert result.terminal_confirmation_retention_bps == 10_000
    assert result.absolute_terminal_preservation_bps == 10_000
    assert result.incremental_false_confirmation_veto_bps == 5_000
    assert result.gate_pass is True


def test_v14_never_creates_confirmation_without_v11() -> None:
    result = evaluate_v14_fold(
        fold_index=0,
        labels=(True, False, True, False),
        baseline_confirmation_minutes=(3, 3, None, None),
        peer_confirmation_scores_micros=(100, -100, None, None),
        peer_confirmation_threshold_micros=0,
    )
    assert result.v14_true_confirmation_count == 1
    assert result.v14_false_confirmation_count == 0
