from qore.infrastructure.core_stack_v2.shared_lab_statistics import (
    TimeWindow,
    WalkForwardFold,
    assess_walk_forward,
    monte_carlo_resample,
)


def fold(
    fold_id: str,
    dev_start: int,
    dev_end: int,
    val_start: int,
    val_end: int,
) -> WalkForwardFold:
    return WalkForwardFold(
        fold_id,
        TimeWindow(f"{fold_id}-dev", dev_start, dev_end),
        TimeWindow(f"{fold_id}-val", val_start, val_end),
    )


def test_walk_forward_rejects_pooled_rescue():
    folds = (
        fold("F1", 0, 10, 10, 20),
        fold("F2", 20, 30, 30, 40),
    )
    result = assess_walk_forward(
        folds,
        fold_pass={"F1": False, "F2": True},
    )
    assert result.failed_fold_ids == ("F1",)
    assert result.walk_forward_proven is False


def test_walk_forward_requires_non_overlapping_chronological_folds():
    folds = (
        fold("F1", 0, 10, 10, 25),
        fold("F2", 20, 30, 30, 40),
    )
    result = assess_walk_forward(
        folds,
        fold_pass={"F1": True, "F2": True},
    )
    assert result.non_overlapping is False
    assert result.walk_forward_proven is False


def test_monte_carlo_is_deterministic_for_same_seed():
    results = (1.0, -1.0, 0.5, 0.25, -0.25)
    first = monte_carlo_resample(results, seed=17, path_count=200)
    second = monte_carlo_resample(results, seed=17, path_count=200)
    assert first == second
    assert 0.0 <= first.probability_positive <= 1.0
    assert first.p95_max_drawdown_r >= 0.0
