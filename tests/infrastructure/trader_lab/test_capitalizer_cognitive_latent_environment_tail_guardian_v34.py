from __future__ import annotations

from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_latent_environment_tail_guardian_v34 as v34,
)
from qore.infrastructure.trader_lab import (
    capitalizer_regularized_causal_state_space_v25 as v25,
)


def _ridge(intercept: float, dimension: int = 1) -> v25.RidgeModel:
    return v25.RidgeModel(
        period="TRAIN",
        feature_mean=tuple(0.0 for _ in range(dimension)),
        feature_scale=tuple(1.0 for _ in range(dimension)),
        coefficients=(intercept, *tuple(0.0 for _ in range(dimension))),
        unique_training_trades=20,
        weighted_observations=20.0,
        feature_dimension=dimension,
        weighted_target_mean=intercept,
        weighted_training_rmse=0.1,
        coefficient_l2_norm=0.0,
    )


def _mixture_head(value: float) -> v34.MixtureHead:
    return v34.MixtureHead(
        experts=tuple(_ridge(value) for _ in range(v34.ENVIRONMENT_COUNT)),
        residual_q20=0.0,
        chronological_residual_count=20,
    )


def _family_model(
    *,
    episode: float,
    total: float,
    downside: float,
    action: str,
) -> v34.LatentFamilyModel:
    geometry = v34.EnvironmentGeometry(
        feature_mean=(0.0,),
        feature_scale=(1.0,),
        centroids=((0.0,), (1.0,), (2.0,), (3.0,)),
        hard_counts=(5, 5, 5, 5),
        iterations=2,
    )
    return v34.LatentFamilyModel(
        geometry=geometry,
        actions={
            action: v34.LatentActionHeads(
                episode_relief=_mixture_head(episode),
                total_delta=_mixture_head(total),
                downside_delta=_mixture_head(downside),
            )
        },
    )


def test_environment_discovery_is_deterministic_and_complete() -> None:
    features = tuple(
        (float(index), float(index % 3), float((index * 2) % 5))
        for index in range(20)
    )

    first = v34._discover_geometry(features)
    second = v34._discover_geometry(features)

    assert first == second
    assert len(first.centroids) == v34.ENVIRONMENT_COUNT == 4
    assert sum(first.hard_counts) == len(features)
    assert 1 <= first.iterations <= v34.MAX_KMEANS_ITERATIONS


def test_soft_environment_membership_is_positive_and_normalized() -> None:
    features = tuple(
        (float(index), float(index % 4))
        for index in range(16)
    )
    geometry = v34._discover_geometry(features)

    weights = v34._environment_weights(geometry, (3.5, 1.0))

    assert len(weights) == 4
    assert all(value > 0.0 for value in weights)
    assert abs(sum(weights) - 1.0) < 1e-12


def test_weighted_batch_ridge_matches_v25_when_weights_are_one() -> None:
    features = (
        (0.0, 1.0),
        (1.0, 0.0),
        (1.0, 1.0),
        (2.0, -1.0),
        (-1.0, 2.0),
        (0.5, -0.5),
    )
    keys = tuple(
        (f"S{index}", f"2026-01-05T08:0{index}:00+00:00")
        for index in range(len(features))
    )
    values = (0.1, -0.2, 0.3, 0.5, -0.4, 0.2)
    target_id = ("LOCK025_AFTER_075", "TOTAL")

    actual = v34._fit_weighted_many(
        label="TEST",
        features=features,
        keys=keys,
        targets={target_id: values},
        weights=tuple(1.0 for _ in features),
    )[target_id]
    expected = v25._fit_model(
        period="TEST",
        examples=tuple(
            (feature, target, 1.0, key)
            for feature, target, key in zip(
                features,
                values,
                keys,
                strict=True,
            )
        ),
    )

    for left, right in zip(
        actual.coefficients,
        expected.coefficients,
        strict=True,
    ):
        assert abs(left - right) < 1e-10
    assert abs(
        actual.weighted_training_rmse - expected.weighted_training_rmse
    ) < 1e-10


def test_dual_world_latent_gate_can_select_supported_action() -> None:
    action = "LOCK025_AFTER_075"
    model_a = _family_model(
        episode=0.30,
        total=0.20,
        downside=0.10,
        action=action,
    )
    model_b = _family_model(
        episode=0.25,
        total=0.15,
        downside=0.05,
        action=action,
    )

    selected, score, lcbs, weights_a, weights_b, epistemic = (
        v34._choose_action(
            features=(0.5,),
            surface_mode="BE_AFTER_050",
            actions=("BE_AFTER_050", action),
            model_a=model_a,
            model_b=model_b,
        )
    )

    assert selected == action
    assert score == 0.25
    assert lcbs is not None
    assert weights_a is not None and abs(sum(weights_a) - 1.0) < 1e-12
    assert weights_b is not None and abs(sum(weights_b) - 1.0) < 1e-12
    assert epistemic == "WELL_SUPPORTED"


def test_dual_world_latent_gate_fails_closed_on_disagreement() -> None:
    action = "LOCK025_AFTER_075"
    model_a = _family_model(
        episode=0.30,
        total=0.20,
        downside=0.10,
        action=action,
    )
    model_b = _family_model(
        episode=-0.01,
        total=0.15,
        downside=0.05,
        action=action,
    )

    selected, score, lcbs, weights_a, weights_b, epistemic = (
        v34._choose_action(
            features=(0.5,),
            surface_mode="BE_AFTER_050",
            actions=("BE_AFTER_050", action),
            model_a=model_a,
            model_b=model_b,
        )
    )

    assert selected is None
    assert score is None
    assert lcbs is None
    assert weights_a is None
    assert weights_b is None
    assert epistemic == "CONFLICTED"


def test_v34_frozen_contract() -> None:
    assert v34.IDENTITY == (
        "QORE_CAPITALIZER_COGNITIVE_LATENT_ENVIRONMENT_TAIL_GUARDIAN_V34"
    )
    assert v34.POLICY == (
        "SURFACE_DEFAULT_DUAL_WORLD_SOFT_ENVIRONMENT_TAIL_OVERRIDE"
    )
    assert v34.ENVIRONMENT_COUNT == 4
    assert v34.MAX_KMEANS_ITERATIONS == 20
    assert v34.CHRONOLOGICAL_FOLDS == 5
    assert v34.MIN_CHRONOLOGICAL_CALIBRATION_EXAMPLES == 10
    assert v34.RESIDUAL_QUANTILE == 0.20
    assert v34.L2_PRIOR_STRENGTH == 12.0
    assert v34.EXPECTED_FEATURE_DIMENSION == 95
