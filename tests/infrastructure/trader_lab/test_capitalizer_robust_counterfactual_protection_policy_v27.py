from types import SimpleNamespace

from qore.infrastructure.trader_lab import (
    capitalizer_regularized_causal_state_space_v25 as v25,
)
from qore.infrastructure.trader_lab import (
    capitalizer_robust_counterfactual_protection_policy_v27 as v27,
)


def _model(intercept: float) -> v25.RidgeModel:
    return v25.RidgeModel(
        period="P",
        feature_mean=(0.0,),
        feature_scale=(1.0,),
        coefficients=(intercept, 0.0),
        unique_training_trades=10,
        weighted_observations=10.0,
        feature_dimension=1,
        weighted_target_mean=intercept,
        weighted_training_rmse=0.0,
        coefficient_l2_norm=0.0,
    )


def test_entry_features_include_multiplier_and_surface_mode() -> None:
    pretrade = SimpleNamespace(
        point=SimpleNamespace(vector=(0.1, 0.2)),
        base_multiplier=0.75,
        mode=v27.ACTIONS[2],
    )
    features = v27._entry_features(pretrade)  # type: ignore[arg-type]
    assert features[:3] == (0.1, 0.2, 0.75)
    one_hot = features[3:]
    assert len(one_hot) == len(v27.ACTIONS)
    assert sum(one_hot) == 1.0
    assert one_hot[2] == 1.0


def test_choose_action_requires_two_model_pareto_agreement() -> None:
    surface = v27.ACTIONS[0]
    good = v27.ACTIONS[1]
    bad = v27.ACTIONS[2]

    models_a = {
        action: (_model(0.0), _model(0.0))
        for action in v27.ACTIONS
    }
    models_b = {
        action: (_model(0.0), _model(0.0))
        for action in v27.ACTIONS
    }
    models_a[good] = (_model(0.4), _model(0.1))
    models_b[good] = (_model(0.3), _model(0.2))
    models_a[bad] = (_model(0.8), _model(0.2))
    models_b[bad] = (_model(-0.1), _model(0.2))

    chosen, score, predictions = v27._choose_action(
        features=(0.0,),
        surface_mode=surface,
        model_a=models_a,
        model_b=models_b,
    )
    assert chosen == good
    assert score == 0.3
    assert predictions == (0.4, 0.3, 0.1, 0.2)


def test_choose_action_falls_back_to_surface_without_agreement() -> None:
    surface = v27.ACTIONS[0]
    models_a = {
        action: (_model(-0.1), _model(0.1))
        for action in v27.ACTIONS
    }
    models_b = {
        action: (_model(0.1), _model(0.1))
        for action in v27.ACTIONS
    }
    chosen, score, predictions = v27._choose_action(
        features=(0.0,),
        surface_mode=surface,
        model_a=models_a,
        model_b=models_b,
    )
    assert chosen == surface
    assert score is None
    assert predictions is None


def test_v27_contract() -> None:
    assert v27.POLICY == "ROBUST_POSDELTA_NONDOWNSIDE"
    assert v27.L2_PRIOR_STRENGTH == 12.0
    assert len(v27.ACTIONS) == 9
