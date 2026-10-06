from decimal import Decimal

import pytest

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ceiling_discovery import (
    CiboCeilingDiscoveryEvidence,
    CiboCeilingLimitKind,
)


def _evidence(**overrides):
    values = {
        "decision_count": 3368,
        "native_max_pass_count": 3368,
        "sovereign_runtime_evaluation_count": 3368,
        "full_semantic_decision_count": 3368,
        "external_ai_call_count": 0,
        "account_reset_count": 0,
        "economic_era_reset_count": 0,
        "initial_capital_usd": Decimal("60"),
        "ending_capital_usd": Decimal("50000"),
        "peak_capital_usd": Decimal("52000"),
        "maximum_drawdown_usd": Decimal("2000"),
        "native_sovereign_runtime_used": True,
        "qore_risk_sovereign": True,
        "outcome_used_for_predecision": False,
        "target_capital_used_for_tuning": False,
        "sizing_ablation_present": True,
        "adaptive_leverage_ablation_present": True,
        "cibo_compound_ablation_present": True,
        "compound_portfolio_ablation_present": True,
        "cognition_ablation_present": True,
        "population_exhausted": False,
        "growth_capacity_remaining_at_population_end": False,
        "intrinsic_ceiling_claimed": True,
        "observed_lower_bound_only": False,
        "limiting_factor": CiboCeilingLimitKind.MARGIN,
    }
    values.update(overrides)
    return CiboCeilingDiscoveryEvidence(**values)


def test_intrinsic_ceiling_requires_full_sovereign_native_path() -> None:
    evidence = _evidence()

    assert evidence.ceiling_discovery_ready_to_close is True
    assert evidence.capital_multiple * Decimal("60") == Decimal("50000")
    assert evidence.maximum_drawdown_fraction_of_peak == (
        Decimal("2000") / Decimal("52000")
    )


def test_partial_native_max_population_cannot_claim_ceiling() -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="Native MAX on every decision",
    ):
        _evidence(native_max_pass_count=2722)


def test_diagnostic_frontier_cannot_substitute_for_sovereign_runtime() -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="diagnostic frontier cannot substitute",
    ):
        _evidence(native_sovereign_runtime_used=False)


def test_ceiling_discovery_forbids_resets_and_external_ai() -> None:
    with pytest.raises(CiboCapitalManagementError, match="capital resets"):
        _evidence(economic_era_reset_count=1)

    with pytest.raises(CiboCapitalManagementError, match="external AI"):
        _evidence(external_ai_call_count=1)


def test_ceiling_discovery_requires_all_mandatory_ablations() -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="mandatory causal ablations",
    ):
        _evidence(adaptive_leverage_ablation_present=False)


def test_population_end_with_growth_remaining_is_lower_bound_not_ceiling() -> None:
    evidence = _evidence(
        population_exhausted=True,
        growth_capacity_remaining_at_population_end=True,
        intrinsic_ceiling_claimed=False,
        observed_lower_bound_only=True,
        limiting_factor=CiboCeilingLimitKind.OPPORTUNITY_POPULATION_EXHAUSTED,
    )

    assert evidence.ceiling_discovery_ready_to_close is False
    assert evidence.observed_lower_bound_only is True


def test_population_exhaustion_cannot_be_mislabeled_intrinsic_ceiling() -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="remaining growth cannot be intrinsic ceiling",
    ):
        _evidence(
            population_exhausted=True,
            growth_capacity_remaining_at_population_end=True,
            intrinsic_ceiling_claimed=True,
            observed_lower_bound_only=False,
            limiting_factor=CiboCeilingLimitKind.MARGIN,
        )


def test_intrinsic_ceiling_requires_structural_limit_not_unknown() -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="structural limiting factor",
    ):
        _evidence(limiting_factor=CiboCeilingLimitKind.UNKNOWN)
