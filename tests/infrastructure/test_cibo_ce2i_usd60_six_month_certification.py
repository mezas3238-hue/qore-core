from dataclasses import replace
from decimal import Decimal

from qore.infrastructure.cibo_ce2i_usd60_six_month_certification import (
    CiboMaximumCapabilityClassification,
    CiboMaximumCapabilityGateSet,
    CiboToolEmpiricalStatus,
    FROZEN_CIBO_USD60_SIX_MONTH_PROTOCOL,
    classify_cibo_maximum_capability,
)


def _passing_gates() -> CiboMaximumCapabilityGateSet:
    return CiboMaximumCapabilityGateSet(
        six_complete_months=True,
        exact_initial_capital=True,
        survival=True,
        robust_economic_maximization=True,
        full_t01_t20_integration=True,
        capital_source_integrity=True,
        zero_double_spend=True,
        zero_outcome_awareness=True,
        zero_future_leakage=True,
        zero_martingale=True,
        zero_loss_recovery_sizing=True,
        risk_sovereignty=True,
        provider_constraint_integrity=True,
        fresh_oos_generalization=True,
        failure_resilience=True,
        baseline_comparison_complete=True,
        ablation_complete=True,
        stress_complete=True,
        monte_carlo_complete=True,
        trajectory_complete=True,
        all_tool_empirical_status_complete=True,
    )


def test_protocol_is_exact_usd60_six_month_no_target_full_surface() -> None:
    protocol = FROZEN_CIBO_USD60_SIX_MONTH_PROTOCOL

    assert protocol.initial_capital_usd == Decimal("60")
    assert protocol.duration_months == 6
    assert protocol.economic_target_usd is None
    assert protocol.trader_lineage_count == 7
    assert protocol.tool_codes == tuple(
        f"T{index:02d}" for index in range(1, 21)
    )
    assert protocol.baselines == (
        "MINIMAL_SEED_ONLY",
        "PREVIOUS_CIBO_CORE",
        "FULL_CIBO_T01_T20",
    )


def test_milestones_are_observation_only_and_not_target() -> None:
    protocol = FROZEN_CIBO_USD60_SIX_MONTH_PROTOCOL

    assert protocol.economic_target_usd is None
    assert protocol.milestones_usd == tuple(
        Decimal(value)
        for value in (
            "100",
            "150",
            "200",
            "300",
            "500",
            "1000",
            "2500",
            "5000",
            "10000",
        )
    )


def test_tool_empirical_completion_requires_all_six_dimensions() -> None:
    status = CiboToolEmpiricalStatus(
        tool_code="T10",
        causal_input_evidence=True,
        correct_capital_source=True,
        correct_action=True,
        rollback_verified=True,
        fail_closed_verified=True,
        incremental_behavior_measured=True,
        activated_count=3,
        blocked_count=2,
        fail_closed_count=1,
    )

    assert status.empirically_complete is True
    assert replace(status, incremental_behavior_measured=False).empirically_complete is False


def test_certification_requires_every_gate() -> None:
    passing = _passing_gates()

    assert classify_cibo_maximum_capability(
        passing,
        hard_integrity_breach=False,
        architecture_or_calibration_intervention_possible=False,
    ) is CiboMaximumCapabilityClassification.CERTIFIED

    intervention = replace(passing, robust_economic_maximization=False)
    assert classify_cibo_maximum_capability(
        intervention,
        hard_integrity_breach=False,
        architecture_or_calibration_intervention_possible=True,
    ) is (
        CiboMaximumCapabilityClassification.INTERVENTION_CONTINUE_ENGINEERING
    )


def test_hard_integrity_breach_is_rejected_even_if_metrics_look_good() -> None:
    assert classify_cibo_maximum_capability(
        _passing_gates(),
        hard_integrity_breach=True,
        architecture_or_calibration_intervention_possible=True,
    ) is CiboMaximumCapabilityClassification.REJECTED
