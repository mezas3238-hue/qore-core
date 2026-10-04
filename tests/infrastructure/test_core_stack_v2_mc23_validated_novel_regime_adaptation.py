from __future__ import annotations

import numpy as np

from qore.infrastructure.core_stack_v2.mc23_validated_novel_regime_adaptation import (
    ADAPTIVE_INTERACTION_NAMES,
    BASELINE_FEATURE_NAMES,
    TARGET_NAMES,
    build_adaptive_design,
    evaluate_adaptation,
    fit_frozen_ridge_projection,
)


def test_adaptive_design_has_exact_frozen_interactions() -> None:
    x = np.full((8, len(BASELINE_FEATURE_NAMES)), 0.5, dtype=np.float64)
    adaptive = build_adaptive_design(x)
    assert adaptive.shape == (
        8,
        len(BASELINE_FEATURE_NAMES) + len(ADAPTIVE_INTERACTION_NAMES),
    )
    # persistence * inverse decay is the fourth interaction
    assert np.allclose(adaptive[:, -3], 0.25)


def test_fit_is_deterministic() -> None:
    rng = np.random.default_rng(7)
    x = rng.normal(size=(256, len(BASELINE_FEATURE_NAMES)))
    y = rng.normal(size=(256, len(TARGET_NAMES)))
    first = fit_frozen_ridge_projection(
        features=x,
        targets=y,
        feature_names=BASELINE_FEATURE_NAMES,
    )
    second = fit_frozen_ridge_projection(
        features=x,
        targets=y,
        feature_names=BASELINE_FEATURE_NAMES,
    )
    assert first.fingerprint() == second.fingerprint()
    assert np.array_equal(first.coefficients, second.coefficients)


def test_interaction_signal_can_pass_frozen_incremental_gate() -> None:
    rng = np.random.default_rng(11)
    train = rng.uniform(0.0, 1.0, size=(6_000, len(BASELINE_FEATURE_NAMES)))
    valid = rng.uniform(0.0, 1.0, size=(5_500, len(BASELINE_FEATURE_NAMES)))
    train_adapt = build_adaptive_design(train)
    valid_adapt = build_adaptive_design(valid)

    # Four targets share a preregistered nonlinear interaction contribution.
    train_signal = train_adapt[:, -6:] @ np.array(
        [0.8, -0.6, 0.5, 0.7, 0.4, -0.3]
    )
    valid_signal = valid_adapt[:, -6:] @ np.array(
        [0.8, -0.6, 0.5, 0.7, 0.4, -0.3]
    )
    train_y = np.column_stack(
        tuple(train_signal + rng.normal(0, 0.05, train.shape[0]) for _ in TARGET_NAMES)
    )
    valid_y = np.column_stack(
        tuple(valid_signal + rng.normal(0, 0.05, valid.shape[0]) for _ in TARGET_NAMES)
    )

    baseline = fit_frozen_ridge_projection(
        features=train,
        targets=train_y,
        feature_names=BASELINE_FEATURE_NAMES,
    )
    adaptive = fit_frozen_ridge_projection(
        features=train_adapt,
        targets=train_y,
        feature_names=BASELINE_FEATURE_NAMES + ADAPTIVE_INTERACTION_NAMES,
    )
    result = evaluate_adaptation(
        baseline_model=baseline,
        adaptive_model=adaptive,
        baseline_features=valid,
        adaptive_features=valid_adapt,
        targets=valid_y,
    )
    assert result.sample_count == 5_500
    assert result.positive_target_count == 4
    assert result.pooled_incremental_information_bps >= 100
    assert result.pass_gate is True
