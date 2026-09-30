from __future__ import annotations

from dataclasses import replace

import pytest

from qore.infrastructure.core_stack_v2.shared_alert_materiality import (
    SharedAlertMaterialityPolicy,
    SharedAlertMaterialityState,
    assess_alert_materiality,
)
from qore.infrastructure.core_stack_v2.shared_global_opportunity_trajectory_v2 import (
    SharedOpportunityHeadState,
    SharedOpportunityMechanism,
    SharedOpportunityTrajectoryAssessment,
)
from qore.infrastructure.core_stack_v2.shared_trader_intelligence import (
    SharedOpportunityMaturity,
    SharedTraderIntelligenceValidationError,
)


def _policy() -> SharedAlertMaterialityPolicy:
    return SharedAlertMaterialityPolicy(
        policy_id="sti11-test",
        trajectory_score_delta_bps=1_000,
        contradiction_delta_bps=1_000,
        uncertainty_delta_bps=1_000,
        source_only_calibration=True,
        calibration_evidence_refs=("r8-source-only",),
    )


def _assessment(
    *,
    maturity: SharedOpportunityMaturity = SharedOpportunityMaturity.DEVELOPING,
    score: int = 6_000,
    contradiction: int = 2_000,
    uncertainty: int = 2_500,
) -> SharedOpportunityTrajectoryAssessment:
    return SharedOpportunityTrajectoryAssessment(
        asset="NAS100",
        maturity=maturity,
        dominant_mechanism=SharedOpportunityMechanism.EXPANSION,
        head_states=(
            SharedOpportunityHeadState(
                mechanism=SharedOpportunityMechanism.EXPANSION,
                current_level_bps=6_500,
                velocity_bps=500,
                persistence_bps=7_000,
                trajectory_score_bps=score,
                maturity=maturity,
            ),
        ),
        contradiction_bps=contradiction,
        uncertainty_bps=uncertainty,
        reason_codes=("TEST",),
    )


def test_new_state_is_material() -> None:
    result = assess_alert_materiality(
        previous=None,
        current=_assessment(),
        policy=_policy(),
    )
    assert result.state is SharedAlertMaterialityState.MATERIAL
    assert result.trader_action_required is False


def test_small_unchanged_delta_is_deduplicated() -> None:
    previous = _assessment()
    current = _assessment(score=6_500, contradiction=2_200, uncertainty=2_600)
    result = assess_alert_materiality(
        previous=previous,
        current=current,
        policy=_policy(),
    )
    assert result.state is SharedAlertMaterialityState.DEDUPLICATED


def test_maturity_change_is_material_even_without_large_numeric_delta() -> None:
    previous = _assessment(maturity=SharedOpportunityMaturity.EARLY)
    current = _assessment(maturity=SharedOpportunityMaturity.DEVELOPING)
    result = assess_alert_materiality(
        previous=previous,
        current=current,
        policy=_policy(),
    )
    assert result.state is SharedAlertMaterialityState.MATERIAL
    assert "MATURITY_STATE_CHANGED" in result.reason_codes


def test_materiality_cannot_be_order_priority() -> None:
    with pytest.raises(
        SharedTraderIntelligenceValidationError,
        match="not probability or order priority",
    ):
        replace(_policy(), order_priority_authority=True)
