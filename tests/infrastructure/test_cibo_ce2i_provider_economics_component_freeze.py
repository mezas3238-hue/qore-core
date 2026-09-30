from datetime import UTC, datetime
from decimal import Decimal

from qore.infrastructure.cibo_arch_b_forward_economic_manifest import (
    ARCH_B_FORWARD_ECONOMIC_MANIFEST_ID,
    ArchBForwardEconomicManifest,
)
from qore.infrastructure.cibo_ce2i_phase20_execution_risk_store import (
    VersionedPhase20ExecutedRiskBook,
)
from qore.infrastructure.cibo_ce2i_phase20_policy_candidate import (
    FROZEN_PHASE20_POLICY_CANDIDATE,
)
from qore.infrastructure.cibo_ce2i_phase20_qualification_plan import (
    FROZEN_PHASE20D_QUALIFICATION_PLAN,
    phase20d_qualification_plan_sha256,
)
from qore.infrastructure.cibo_ce2i_provider_economics_component_freeze import (
    freeze_current_ctrader_demo_provider_economics,
)
from qore.infrastructure.cibo_ce2i_provider_execution_calibration import (
    calibrate_ctrader_demo_forward_execution,
)


def _empty_manifest() -> ArchBForwardEconomicManifest:
    frozen = FROZEN_PHASE20_POLICY_CANDIDATE
    plan = FROZEN_PHASE20D_QUALIFICATION_PLAN
    return ArchBForwardEconomicManifest(
        manifest_id=ARCH_B_FORWARD_ECONOMIC_MANIFEST_ID,
        frozen_candidate_id=frozen.candidate_id,
        frozen_code_sha=frozen.code_sha,
        frozen_parameter_sha256=frozen.parameter_sha256(),
        qualification_plan_id=plan.plan_id,
        qualification_plan_sha256=phase20d_qualification_plan_sha256(),
        baseline_policy_id=plan.baseline_policy_id,
        qualification_status="NOT_READY",
        decision_epochs=0,
        candidate_rows=0,
        complete_lineage_rows=0,
        rows=(),
        gaps=(),
        ready_for_scientific_consumption=False,
    )


def test_current_provider_terms_freeze_without_overclaiming_slippage() -> None:
    freeze = freeze_current_ctrader_demo_provider_economics(
        frozen_at=datetime(2026, 9, 30, 20, 15, tzinfo=UTC)
    )

    assert freeze.point_in_time_terms_frozen is True
    assert freeze.spread_terms_frozen is True
    assert freeze.commission_terms_frozen is True
    assert freeze.expected_margin_terms_frozen is True
    assert freeze.volume_contract_terms_frozen is True
    assert freeze.empirical_slippage_frozen is False
    assert freeze.execution_model_frozen is False
    assert freeze.historical_2017_exact_claimed is False
    assert freeze.holdout_outcomes_used is False
    assert freeze.target_aware is False
    assert freeze.broker_mutation_performed is False
    assert freeze.pre_holdout_provider_economics_ready is False
    assert freeze.execution_calibration_sha256 is None
    assert freeze.productive_authority is False
    assert freeze.blockers == (
        "EMPIRICAL_SLIPPAGE_NOT_FROZEN",
        "EXECUTION_MODEL_NOT_FROZEN",
    )
    assert "artifact:11104595302" in freeze.source_evidence_ref


def test_not_ready_execution_calibration_is_bound_without_promoting_readiness() -> None:
    calibration = calibrate_ctrader_demo_forward_execution(
        manifest=_empty_manifest(),
        executed_risk_book=VersionedPhase20ExecutedRiskBook(generation=0),
        frozen_at=datetime(2026, 9, 30, 20, 20, tzinfo=UTC),
    )

    freeze = freeze_current_ctrader_demo_provider_economics(
        frozen_at=datetime(2026, 9, 30, 20, 30, tzinfo=UTC),
        execution_calibration=calibration,
    )

    assert calibration.empirical_slippage_calibrated is False
    assert calibration.execution_model_ready is False
    assert freeze.execution_calibration_sha256 == calibration.fingerprint()
    assert freeze.empirical_slippage_frozen is False
    assert freeze.execution_model_frozen is False
    assert freeze.pre_holdout_provider_economics_ready is False
    assert freeze.blockers == (
        "EMPIRICAL_SLIPPAGE_NOT_FROZEN",
        "EXECUTION_MODEL_NOT_FROZEN",
    )
    assert Decimal(freeze.source_observed_at.timestamp()) > 0
