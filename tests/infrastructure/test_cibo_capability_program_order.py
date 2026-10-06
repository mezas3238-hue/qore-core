from decimal import Decimal

import pytest

from qore.infrastructure.cibo_capability_program_order import (
    CIBO_CAPABILITY_PROGRAM_ORDER,
    DEFAULT_CIBO_CAPABILITY_PROGRAM_PROGRESS,
    CiboCapabilityProgramProgress,
    CiboCapabilityProgramStage,
    enter_post_ceiling_refinement,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ceiling_discovery import (
    CiboCeilingDiscoveryEvidence,
    CiboCeilingLimitKind,
)


def test_program_starts_with_ceiling_discovery() -> None:
    progress = DEFAULT_CIBO_CAPABILITY_PROGRAM_PROGRESS

    assert (
        progress.current_stage
        is CiboCapabilityProgramStage.CEILING_DISCOVERY
    )
    assert progress.closed_stages == ()
    assert progress.ceiling_discovery_active is True
    assert progress.examinations_unlocked is False


def test_owner_mandated_program_order_is_exact() -> None:
    assert CIBO_CAPABILITY_PROGRAM_ORDER == (
        CiboCapabilityProgramStage.CEILING_DISCOVERY,
        CiboCapabilityProgramStage.POST_CEILING_REFINEMENT,
        CiboCapabilityProgramStage.EXAM_1_ALL_TRADER_RESCUE,
        CiboCapabilityProgramStage.EXAM_3_NEGATIVE_TRADER_ONLY_RESCUE,
        CiboCapabilityProgramStage.EXAM_2_2000_PERCENT_10M,
    )


def test_exam_1_cannot_open_before_ceiling_and_refinement_close() -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="stage order violated",
    ):
        CiboCapabilityProgramProgress(
            current_stage=CiboCapabilityProgramStage.EXAM_1_ALL_TRADER_RESCUE,
            closed_stages=(
                CiboCapabilityProgramStage.CEILING_DISCOVERY,
            ),
        )


def test_exam_3_cannot_open_before_exam_1_closes() -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="stage order violated",
    ):
        CiboCapabilityProgramProgress(
            current_stage=(
                CiboCapabilityProgramStage.EXAM_3_NEGATIVE_TRADER_ONLY_RESCUE
            ),
            closed_stages=(
                CiboCapabilityProgramStage.CEILING_DISCOVERY,
                CiboCapabilityProgramStage.POST_CEILING_REFINEMENT,
            ),
        )


def test_2000_percent_exam_is_last() -> None:
    progress = CiboCapabilityProgramProgress(
        current_stage=CiboCapabilityProgramStage.EXAM_2_2000_PERCENT_10M,
        closed_stages=(
            CiboCapabilityProgramStage.CEILING_DISCOVERY,
            CiboCapabilityProgramStage.POST_CEILING_REFINEMENT,
            CiboCapabilityProgramStage.EXAM_1_ALL_TRADER_RESCUE,
            CiboCapabilityProgramStage.EXAM_3_NEGATIVE_TRADER_ONLY_RESCUE,
        ),
    )

    assert progress.examinations_unlocked is True


def _ceiling_evidence(*, lower_bound: bool = False):
    return CiboCeilingDiscoveryEvidence(
        decision_count=3368,
        native_max_pass_count=3368,
        sovereign_runtime_evaluation_count=3368,
        full_semantic_decision_count=3368,
        external_ai_call_count=0,
        account_reset_count=0,
        economic_era_reset_count=0,
        initial_capital_usd=Decimal("60"),
        ending_capital_usd=Decimal("50000"),
        peak_capital_usd=Decimal("52000"),
        maximum_drawdown_usd=Decimal("2000"),
        native_sovereign_runtime_used=True,
        qore_risk_sovereign=True,
        outcome_used_for_predecision=False,
        target_capital_used_for_tuning=False,
        sizing_ablation_present=True,
        adaptive_leverage_ablation_present=True,
        cibo_compound_ablation_present=True,
        compound_portfolio_ablation_present=True,
        cognition_ablation_present=True,
        population_exhausted=lower_bound,
        growth_capacity_remaining_at_population_end=lower_bound,
        intrinsic_ceiling_claimed=not lower_bound,
        observed_lower_bound_only=lower_bound,
        limiting_factor=(
            CiboCeilingLimitKind.OPPORTUNITY_POPULATION_EXHAUSTED
            if lower_bound
            else CiboCeilingLimitKind.MARGIN
        ),
    )


def test_post_ceiling_refinement_requires_proven_intrinsic_ceiling() -> None:
    progress = enter_post_ceiling_refinement(_ceiling_evidence())

    assert (
        progress.current_stage
        is CiboCapabilityProgramStage.POST_CEILING_REFINEMENT
    )
    assert progress.closed_stages == (
        CiboCapabilityProgramStage.CEILING_DISCOVERY,
    )


def test_population_lower_bound_cannot_unlock_refinement() -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="intrinsic ceiling is proven",
    ):
        enter_post_ceiling_refinement(_ceiling_evidence(lower_bound=True))
