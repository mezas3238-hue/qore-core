from datetime import UTC, datetime, timedelta

from qore.infrastructure.cibo_ce2i_final_certification import (
    CiboEconomicCertificationStatus,
    Phase22QualificationReceipt,
    assess_cibo_final_economic_certification,
)
from qore.infrastructure.cibo_ce2i_phase20_policy_candidate import (
    FROZEN_PHASE20_POLICY_CANDIDATE,
)
from qore.infrastructure.cibo_ce2i_phase20_qualification_plan import (
    FROZEN_PHASE20D_QUALIFICATION_PLAN,
    phase20d_qualification_plan_sha256,
)
from qore.infrastructure.cibo_ce2i_phase21_policy_freeze import (
    Phase21EmpiricalValidationKind,
    Phase21EmpiricalValidationReceipt,
    Phase21PolicySurfaceDigests,
    Phase21QualificationReceipt,
    build_phase21_policy_freeze,
)
from qore.infrastructure.cibo_ce2i_phase22_qualification_plan import (
    FROZEN_PHASE22_HOLDOUT_QUALIFICATION_PLAN,
    phase22_holdout_qualification_plan_sha256,
)

QUALIFIED_AT = datetime(2026, 10, 26, 20, 0, tzinfo=UTC)
PHASE21_FROZEN_AT = QUALIFIED_AT + timedelta(hours=4)


def _sha(index: int) -> str:
    return f"sha256:{index:064x}"


def _phase21_manifest():
    candidate = FROZEN_PHASE20_POLICY_CANDIDATE
    qualification = Phase21QualificationReceipt(
        candidate_id=candidate.candidate_id,
        candidate_parameter_sha256=candidate.parameter_sha256(),
        plan_id=FROZEN_PHASE20D_QUALIFICATION_PLAN.plan_id,
        plan_sha256=phase20d_qualification_plan_sha256(),
        evidence_store_sha256=_sha(1),
        policy_store_sha256=_sha(2),
        qualification_artifact_sha256=_sha(3),
        qualified_at=QUALIFIED_AT,
        passed=True,
    )
    validations = tuple(
        Phase21EmpiricalValidationReceipt(
            kind=kind,
            candidate_id=candidate.candidate_id,
            candidate_parameter_sha256=candidate.parameter_sha256(),
            qualification_artifact_sha256=_sha(3),
            evidence_class="FORWARD_EMPIRICAL",
            artifact_sha256=_sha(20 + index),
            observed_at=QUALIFIED_AT + timedelta(hours=index + 1),
            passed=True,
        )
        for index, kind in enumerate(Phase21EmpiricalValidationKind)
    )
    surface = Phase21PolicySurfaceDigests(
        state_machine_sha256=_sha(101),
        tool_registry_sha256=_sha(102),
        eligibility_sha256=_sha(103),
        source_ledger_sha256=_sha(104),
        trader_adapters_sha256=_sha(105),
        provider_profiles_sha256=_sha(106),
    )
    return build_phase21_policy_freeze(
        qualification=qualification,
        empirical_validations=validations,
        policy_surface=surface,
        frozen_at=PHASE21_FROZEN_AT,
    )


def _receipt(*, phase21_sha: str) -> Phase22QualificationReceipt:
    candidate = FROZEN_PHASE20_POLICY_CANDIDATE
    plan = FROZEN_PHASE22_HOLDOUT_QUALIFICATION_PLAN
    return Phase22QualificationReceipt(
        candidate_id=candidate.candidate_id,
        candidate_parameter_sha256=candidate.parameter_sha256(),
        phase21_manifest_sha256=phase21_sha,
        phase22_plan_id=plan.plan_id,
        phase22_plan_sha256=phase22_holdout_qualification_plan_sha256(),
        holdout_evidence_store_sha256=_sha(201),
        holdout_policy_store_sha256=_sha(202),
        qualification_artifact_sha256=_sha(203),
        qualified_at=PHASE21_FROZEN_AT + timedelta(days=29),
        evidence_class="FORWARD_EMPIRICAL_HOLDOUT",
        passed=True,
        lineage_valid=True,
        economic_holdout_passed=True,
    )


def test_final_certification_remains_pending_without_phase22_receipt() -> None:
    manifest = _phase21_manifest()

    decision = assess_cibo_final_economic_certification(
        phase21_manifest=manifest,
        phase22_receipt=None,
    )

    assert decision.status is CiboEconomicCertificationStatus.PENDING
    assert decision.blockers == ("PHASE22_QUALIFICATION_RECEIPT_REQUIRED",)
    assert decision.live_authorized is False
    assert decision.real_capital_authorized is False


def test_final_certification_requires_exact_phase21_lineage() -> None:
    manifest = _phase21_manifest()

    decision = assess_cibo_final_economic_certification(
        phase21_manifest=manifest,
        phase22_receipt=_receipt(phase21_sha=_sha(999)),
    )

    assert decision.status is CiboEconomicCertificationStatus.INVALID
    assert decision.blockers == ("PHASE21_MANIFEST_LINEAGE_MISMATCH",)


def test_final_certification_accepts_exact_sealed_economic_chain_only() -> None:
    manifest = _phase21_manifest()

    decision = assess_cibo_final_economic_certification(
        phase21_manifest=manifest,
        phase22_receipt=_receipt(
            phase21_sha=manifest.manifest_sha256(),
        ),
    )

    assert decision.status is CiboEconomicCertificationStatus.CERTIFIED
    assert decision.blockers == ()
    assert decision.demo_execution_authorized is False
    assert decision.live_authorized is False
    assert decision.real_capital_authorized is False
    assert decision.merge_authorized is False
