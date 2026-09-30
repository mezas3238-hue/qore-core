from __future__ import annotations

from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_r_milestone_protection_2r_v1 as milestone,
)
from qore.infrastructure.trader_lab import (
    capitalizer_first_intervention_cross_trigger_optionality_v30 as v30,
)
from qore.infrastructure.trader_lab import (
    capitalizer_regularized_causal_state_space_v25 as v25,
)


def _model(intercept: float, dimension: int) -> v25.RidgeModel:
    return v25.RidgeModel(
        period="TRAIN",
        feature_mean=tuple(0.0 for _ in range(dimension)),
        feature_scale=tuple(1.0 for _ in range(dimension)),
        coefficients=(intercept, *tuple(0.0 for _ in range(dimension))),
        unique_training_trades=50,
        weighted_observations=50.0,
        feature_dimension=dimension,
        weighted_target_mean=intercept,
        weighted_training_rmse=0.1,
        coefficient_l2_norm=abs(intercept),
    )


def test_cross_trigger_action_horizon_is_frozen() -> None:
    at_050 = v30._eligible_actions(v30.FAMILY_050)
    at_075 = v30._eligible_actions(v30.FAMILY_075)
    at_100 = v30._eligible_actions(v30.FAMILY_100)

    assert len(at_050) == 9
    assert len(at_075) == 7
    assert len(at_100) == 4

    assert milestone.ProtectionMode.ORIGINAL.value in at_050
    assert milestone.ProtectionMode.ORIGINAL.value in at_075
    assert milestone.ProtectionMode.ORIGINAL.value in at_100

    assert milestone.ProtectionMode.BE_AFTER_050.value not in at_075
    assert milestone.ProtectionMode.STAGED_050_100_150.value not in at_075
    assert milestone.ProtectionMode.LOCK025_AFTER_075.value not in at_100
    assert milestone.ProtectionMode.LOCK050_AFTER_100.value in at_050
    assert milestone.ProtectionMode.LOCK050_AFTER_100.value in at_075
    assert milestone.ProtectionMode.LOCK050_AFTER_100.value in at_100


def test_mode_first_family_mapping_is_complete() -> None:
    assert set(v30.MODE_FIRST_FAMILY) == {
        mode.value for mode in milestone.ProtectionMode
    }
    assert (
        v30._mode_family(milestone.ProtectionMode.ORIGINAL.value)
        is None
    )
    assert v30._mode_family("STAGED_050_100_150") == v30.FAMILY_050
    assert v30._mode_family("LOCK025_AFTER_075") == v30.FAMILY_075
    assert v30._mode_family("LOCK050_AFTER_100") == v30.FAMILY_100


def test_robust_selector_can_choose_later_trigger_mode() -> None:
    features = (0.0, 0.0, 0.0)
    same_total = _model(0.20, len(features))
    same_downside = _model(0.10, len(features))
    later_total_a = _model(0.55, len(features))
    later_total_b = _model(0.45, len(features))
    later_downside = _model(0.15, len(features))

    action, score, predictions = v30._choose_action(
        features=features,
        surface_mode="STAGED_050_100_150",
        actions=(
            "BE_AFTER_050",
            "STAGED_050_100_150",
            "LOCK050_AFTER_100",
        ),
        model_a={
            "BE_AFTER_050": (same_total, same_downside),
            "LOCK050_AFTER_100": (later_total_a, later_downside),
        },
        model_b={
            "BE_AFTER_050": (same_total, same_downside),
            "LOCK050_AFTER_100": (later_total_b, later_downside),
        },
    )

    assert action == "LOCK050_AFTER_100"
    assert score == 0.45
    assert predictions == (0.55, 0.45, 0.15, 0.15)


def test_v30_frozen_contract() -> None:
    assert v30.IDENTITY == (
        "QORE_CAPITALIZER_FIRST_INTERVENTION_CROSS_TRIGGER_OPTIONALITY_V30"
    )
    assert v30.POLICY == (
        "FIRST_INTERVENTION_ROBUST_CROSS_TRIGGER_POSDELTA_NONDOWNSIDE"
    )
    assert v30.L2_PRIOR_STRENGTH == 12.0
    assert v30.SOURCE_TRIGGER_STATE_RUN_ID == 36283499014
    assert v30.SOURCE_M1_RUN_ID == 35548099334
    assert v30.FAMILY_ORDER == (
        "TRIGGER_050",
        "TRIGGER_075",
        "TRIGGER_100",
    )
