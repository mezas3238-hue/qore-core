from types import SimpleNamespace

from qore.infrastructure.trader_lab import (
    capitalizer_regularized_causal_state_space_v25 as v25,
)
from qore.infrastructure.trader_lab import (
    capitalizer_triggered_regularized_protection_policy_v28 as v28,
)


def _model(intercept: float, dimension: int) -> v25.RidgeModel:
    return v25.RidgeModel(
        period="P",
        feature_mean=tuple(0.0 for _ in range(dimension)),
        feature_scale=tuple(1.0 for _ in range(dimension)),
        coefficients=(intercept, *tuple(0.0 for _ in range(dimension))),
        unique_training_trades=20,
        weighted_observations=20.0,
        feature_dimension=dimension,
        weighted_target_mean=intercept,
        weighted_training_rmse=0.0,
        coefficient_l2_norm=0.0,
    )


def test_trigger_families_are_complete_and_existing_only() -> None:
    assert tuple(v28.FAMILIES) == (
        "TRIGGER_050",
        "TRIGGER_075",
        "TRIGGER_100",
    )
    assert v28.FAMILIES["TRIGGER_075"][1] == (
        "BE_AFTER_075",
        "LOCK025_AFTER_075",
        "STAGED_075_125_150",
    )
    existing = {
        mode
        for _family, (_trigger, arms) in v28.FAMILIES.items()
        for mode in arms
    }
    assert existing <= set(v25.MODE_VALUES)


def test_trigger_features_append_exact_continuous_delay() -> None:
    pretrade = SimpleNamespace(
        point=SimpleNamespace(vector=(0.1, 0.2)),
        base_multiplier=0.75,
        mode=v25.MODE_VALUES[0],
    )
    features = v28._trigger_features(
        pretrade,  # type: ignore[arg-type]
        entry_at="2026-01-01T10:00:00+00:00",
        trigger_at="2026-01-01T10:07:30+00:00",
    )
    assert features[-1] == 7.5
    assert features[:3] == (0.1, 0.2, 0.75)


def test_family_action_requires_two_model_agreement() -> None:
    arms = v28.FAMILIES["TRIGGER_075"][1]
    dimension = 1
    model_a = {
        action: (_model(-0.1, dimension), _model(0.1, dimension))
        for action in arms
    }
    model_b = {
        action: (_model(-0.1, dimension), _model(0.1, dimension))
        for action in arms
    }
    good = arms[1]
    model_a[good] = (_model(0.4, dimension), _model(0.1, dimension))
    model_b[good] = (_model(0.3, dimension), _model(0.2, dimension))

    chosen, score, predictions = v28._choose_family_action(
        features=(0.0,),
        surface_mode=arms[0],
        arms=arms,
        model_a=model_a,
        model_b=model_b,
    )
    assert chosen == good
    assert score == 0.3
    assert predictions == (0.4, 0.3, 0.1, 0.2)


def test_family_action_falls_back_when_downside_disagrees() -> None:
    arms = v28.FAMILIES["TRIGGER_050"][1]
    dimension = 1
    model_a = {
        action: (_model(0.4, dimension), _model(0.1, dimension))
        for action in arms
    }
    model_b = {
        action: (_model(0.3, dimension), _model(-0.01, dimension))
        for action in arms
    }
    chosen, score, predictions = v28._choose_family_action(
        features=(0.0,),
        surface_mode="ORIGINAL",
        arms=arms,
        model_a=model_a,
        model_b=model_b,
    )
    assert chosen is None
    assert score is None
    assert predictions is None


def test_v28_frozen_contract() -> None:
    assert v28.POLICY == "TRIGGERED_ROBUST_POSDELTA_NONDOWNSIDE"
    assert v28.L2_PRIOR_STRENGTH == 12.0
    assert len(v28.FAMILIES) == 3
