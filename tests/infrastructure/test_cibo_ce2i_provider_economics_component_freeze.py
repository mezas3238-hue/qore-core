from datetime import datetime, timedelta

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
from qore.infrastructure.cibo_ce2i_provider_economics_evidence import (
    CURRENT_CTRADER_DEMO_PROVIDER_ECONOMICS,
)
from qore.infrastructure.cibo_ce2i_provider_execution_calibration import (
    calibrate_ctrader_demo_forward_execution,
)
from qore.infrastructure.cibo_ce2i_provider_stress_bound_freeze import (
    build_provider_stress_bound_freeze,
)

PROVIDER_OBSERVED_AT = datetime.fromisoformat(
    CURRENT_CTRADER_DEMO_PROVIDER_ECONOMICS.observed_at
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
        frozen_at=PROVIDER_OBSERVED_AT + timedelta(minutes=1)
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
        "PROVIDER_STRESS_BOUND_NOT_FROZEN",
    )
    assert (
        f"artifact:{CURRENT_CTRADER_DEMO_PROVIDER_ECONOMICS.artifact_id}"
        in freeze.source_evidence_ref
    )


def test_not_ready_execution_calibration_is_bound_without_promoting_readiness() -> None:
    calibration = calibrate_ctrader_demo_forward_execution(
        manifest=_empty_manifest(),
        executed_risk_book=VersionedPhase20ExecutedRiskBook(generation=0),
        frozen_at=PROVIDER_OBSERVED_AT + timedelta(minutes=2),
    )

    freeze = freeze_current_ctrader_demo_provider_economics(
        frozen_at=PROVIDER_OBSERVED_AT + timedelta(minutes=3),
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



def test_stress_bound_lane_closes_core_without_deployment_overclaim() -> None:
    stress = build_provider_stress_bound_freeze(
        empirical_inventory={
            "schema": "qore.cibo.ctrader_demo.empirical_slippage.v1",
            "status": "EMPIRICAL_SLIPPAGE_NOT_READY",
            "provider_key": "ctrader-demo",
            "environment": "demo",
            "account_entry_deals_found": 3,
            "market_entry_deals_found": 1,
            "qore_deals_found": 1,
            "empirical_slippage_calibrated": False,
            "execution_model_ready": False,
            "broker_mutation_performed": False,
            "holdout_outcomes_used": False,
            "historical_2017_exact_claimed": False,
            "target_aware": False,
            "productive_authority": False,
        },
        frozen_at=PROVIDER_OBSERVED_AT + timedelta(minutes=4),
    )

    freeze = freeze_current_ctrader_demo_provider_economics(
        frozen_at=PROVIDER_OBSERVED_AT + timedelta(minutes=5),
        stress_bound=stress,
    )

    assert freeze.pre_holdout_provider_economics_ready is True
    assert freeze.certification_lane == "PREDECLARED_STRESS_BOUND"
    assert freeze.empirical_slippage_frozen is False
    assert freeze.execution_model_frozen is False
    assert freeze.provider_stress_bound_sha256 == stress.fingerprint()
    assert freeze.provider_deployment_ready is False
    assert freeze.blockers == ()
    assert "PROVIDER_DEPLOYMENT_EMPIRICAL_SLIPPAGE_REQUIRED" in (
        freeze.deployment_blockers
    )
