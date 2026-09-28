from __future__ import annotations

from qore.infrastructure.core_stack_v2.active_perception_v13_information_gain import (
    V13_CHECKPOINTS_MINUTES,
    evaluate_v13_fold,
    fit_v13_checkpoint_density,
    persistent_recovery_score_micros,
    pooled_v13_false_veto_bps,
    score_v13_checkpoint_micros,
    select_v13_recovery_veto_threshold_micros,
)
from qore.infrastructure.core_stack_v2.active_perception_v13_sequential_representation import (
    V13_BASE_FEATURES,
)


def _row(value: int) -> dict[str, object]:
    row: dict[str, object] = {}
    for minute in V13_CHECKPOINTS_MINUTES:
        for field in V13_BASE_FEATURES:
            row[f"t{minute}_{field}"] = value
    return row


def test_v13_checkpoint_density_scores_terminal_and_nonterminal_examples() -> None:
    rows = tuple(_row(9000 + index) for index in range(12)) + tuple(
        _row(1000 + index) for index in range(12)
    )
    labels = (True,) * 12 + (False,) * 12

    model = fit_v13_checkpoint_density(
        checkpoint_minutes=3,
        rows=rows,
        labels=labels,
    )

    assert score_v13_checkpoint_micros(model, _row(9500)) > 0
    assert score_v13_checkpoint_micros(model, _row(1050)) < 0


def test_persistent_recovery_score_requires_adjacent_low_evidence() -> None:
    scores = {
        0: -100,
        3: -200,
        5: 500,
        10: -500,
        15: -600,
    }

    assert persistent_recovery_score_micros(
        checkpoint_scores_micros=scores,
        confirmation_minute=5,
    ) == -100
    assert persistent_recovery_score_micros(
        checkpoint_scores_micros=scores,
        confirmation_minute=15,
    ) == -500


def test_threshold_selection_uses_true_confirmation_retention_only() -> None:
    scores = tuple(range(100))

    threshold, retention = select_v13_recovery_veto_threshold_micros(scores)

    assert threshold == 1
    assert retention == 9800


def test_v13_fold_can_only_remove_existing_v11_confirmations() -> None:
    labels = (True,) * 100 + (False,) * 100
    baseline_minutes = (3,) * 98 + (None,) * 2 + (3,) * 20 + (None,) * 80
    persistent_scores = (
        (10,) * 97
        + (-10,)
        + (None,) * 2
        + ((-10,) * 10 + (10,) * 10)
        + (None,) * 80
    )

    fold = evaluate_v13_fold(
        fold_index=0,
        labels=labels,
        baseline_confirmation_minutes=baseline_minutes,
        persistent_recovery_scores_micros=persistent_scores,
        recovery_veto_threshold_micros=0,
    )

    assert fold.baseline_true_confirmation_count == 98
    assert fold.v13_true_confirmation_count == 97
    assert fold.terminal_confirmation_retention_bps >= 9800
    assert fold.absolute_terminal_preservation_bps >= 9500
    assert fold.incremental_false_confirmation_veto_bps == 5000
    assert fold.gate_pass is True


def test_pooled_v13_false_veto_aggregates_exactly_four_folds() -> None:
    folds = tuple(
        evaluate_v13_fold(
            fold_index=index,
            labels=(True,) * 100 + (False,) * 100,
            baseline_confirmation_minutes=(3,) * 98
            + (None,) * 2
            + (3,) * 20
            + (None,) * 80,
            persistent_recovery_scores_micros=(10,) * 98
            + (None,) * 2
            + ((-10,) * 2 + (10,) * 18)
            + (None,) * 80,
            recovery_veto_threshold_micros=0,
        )
        for index in range(4)
    )

    assert pooled_v13_false_veto_bps(folds) == 1000
