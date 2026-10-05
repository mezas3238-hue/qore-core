from qore.infrastructure.core_stack_v2.shared_lab_causality import (
    CausalInterventionReceipt,
    ConfounderStressReceipt,
)


def test_causal_intervention_requires_expected_direction_and_predecision_truth():
    receipt = CausalInterventionReceipt(
        "MC03",
        "INT_001",
        cause_changed=True,
        expected_effect_direction=1,
        observed_effect_direction=1,
        confounders_held_or_adjusted=True,
        predecision_only=True,
        downstream_effect_observed=True,
    )
    assert receipt.passed is True


def test_confounder_instability_fails():
    receipt = ConfounderStressReceipt(
        "MC03",
        "VOLATILITY",
        baseline_effect=0.8,
        adjusted_effect=0.2,
        max_allowed_effect_drift=0.1,
        sign_preserved=True,
    )
    assert receipt.passed is False
