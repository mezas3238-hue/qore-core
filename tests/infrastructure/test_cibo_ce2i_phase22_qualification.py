import json
import re
from dataclasses import replace
from datetime import UTC, datetime, timedelta

from qore.infrastructure.cibo_ce2i_phase20_forward_policy_store import (
    Phase20ForwardPolicyDecisionSeal,
    VersionedPhase20ForwardPolicyBook,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_store import (
    Phase20ForwardDecisionSeal,
    VersionedPhase20ForwardEvidenceBook,
)
from qore.infrastructure.cibo_ce2i_phase20_policy_candidate import (
    FROZEN_PHASE20_POLICY_CANDIDATE,
)
from qore.infrastructure.cibo_ce2i_phase20_qualification import (
    Phase20QualificationStatus,
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
from qore.infrastructure.cibo_ce2i_phase22_qualification import (
    Phase22HoldoutQualificationStatus,
    run_phase22_holdout_qualification,
)
from qore.infrastructure.cibo_ce2i_phase22_qualification_plan import (
    FROZEN_PHASE22_HOLDOUT_QUALIFICATION_PLAN,
    phase22_holdout_qualification_plan_sha256,
)

QUALIFIED_AT = datetime(2026, 10, 26, 20, 0, tzinfo=UTC)
PHASE21_FROZEN_AT = QUALIFIED_AT + timedelta(hours=4)
COLLECTOR_SHA = "a" * 40


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


def _decision(
    *,
    evidence_sha: str,
    decision_at: datetime,
) -> Phase20ForwardDecisionSeal:
    candidate = FROZEN_PHASE20_POLICY_CANDIDATE
    payload = json.dumps(
        {
            "candidates": [],
            "hard_risk_headroom_usd": "60",
            "margin_headroom_usd": "60",
            "concentration_limit_by_group": [],
            "population_slots": [],
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return Phase20ForwardDecisionSeal(
        evidence_id=f"evidence-{evidence_sha[-4:]}",
        decision_epoch_id=f"epoch-{evidence_sha[-4:]}",
        evidence_sha256=evidence_sha,
        decision_at=decision_at,
        sealed_at=decision_at + timedelta(milliseconds=100),
        seal_deadline_at=decision_at + timedelta(seconds=2),
        candidate_id=candidate.candidate_id,
        code_sha=candidate.code_sha,
        parameter_sha256=candidate.parameter_sha256(),
        signal_fingerprints=(),
        canonical_payload_json=payload,
        collector_git_sha=COLLECTOR_SHA,
    )


def _policy(evidence_sha: str) -> Phase20ForwardPolicyDecisionSeal:
    return Phase20ForwardPolicyDecisionSeal(
        evidence_sha256=evidence_sha,
        policy_record_sha256=_sha(500),
        allocator_disposition="ABSTAIN",
        selected_signal_fingerprints=(),
        canonical_record_json="{}",
    )


def test_phase22_plan_reuses_exact_phase20d_economic_protocol() -> None:
    plan = FROZEN_PHASE22_HOLDOUT_QUALIFICATION_PLAN

    assert plan.economic_protocol_plan_id == FROZEN_PHASE20D_QUALIFICATION_PLAN.plan_id
    assert (
        plan.economic_protocol_plan_sha256
        == phase20d_qualification_plan_sha256()
    )
    assert plan.reuse_phase20d_economic_thresholds_without_refit is True
    assert plan.allow_synthetic_evidence is False
    assert plan.allow_holdout_mining is False
    assert re.fullmatch(
        r"sha256:[0-9a-f]{64}",
        phase22_holdout_qualification_plan_sha256(),
    )


def test_phase22_valid_lineage_with_immature_population_is_not_ready() -> None:
    qualification_decision = _decision(
        evidence_sha=_sha(201),
        decision_at=QUALIFIED_AT - timedelta(days=1),
    )
    holdout_decision = _decision(
        evidence_sha=_sha(202),
        decision_at=PHASE21_FROZEN_AT + timedelta(seconds=1),
    )

    report = run_phase22_holdout_qualification(
        phase21_manifest=_phase21_manifest(),
        qualification_evidence_book=VersionedPhase20ForwardEvidenceBook(
            generation=1,
            decisions=(qualification_decision,),
        ),
        holdout_evidence_book=VersionedPhase20ForwardEvidenceBook(
            generation=1,
            decisions=(holdout_decision,),
        ),
        holdout_policy_book=VersionedPhase20ForwardPolicyBook(
            generation=1,
            decisions=(_policy(holdout_decision.evidence_sha256),),
        ),
        qualification_evidence_store_sha256=_sha(1),
        qualification_policy_store_sha256=_sha(2),
        holdout_evidence_store_sha256=_sha(11),
        holdout_policy_store_sha256=_sha(12),
    )

    assert report.status is Phase22HoldoutQualificationStatus.NOT_READY
    assert report.lineage.lineage_valid is True
    assert report.economic_report is not None
    assert report.economic_report.status is Phase20QualificationStatus.NOT_READY
    assert report.economically_certified is False


def test_phase22_reused_qualification_decision_is_invalid_before_economics() -> None:
    qualification_decision = _decision(
        evidence_sha=_sha(201),
        decision_at=QUALIFIED_AT - timedelta(days=1),
    )
    holdout_decision = replace(
        qualification_decision,
        evidence_id="holdout-reused",
        decision_epoch_id="holdout-reused",
        decision_at=PHASE21_FROZEN_AT + timedelta(seconds=1),
        sealed_at=PHASE21_FROZEN_AT + timedelta(milliseconds=1100),
        seal_deadline_at=PHASE21_FROZEN_AT + timedelta(seconds=3),
    )

    report = run_phase22_holdout_qualification(
        phase21_manifest=_phase21_manifest(),
        qualification_evidence_book=VersionedPhase20ForwardEvidenceBook(
            generation=1,
            decisions=(qualification_decision,),
        ),
        holdout_evidence_book=VersionedPhase20ForwardEvidenceBook(
            generation=1,
            decisions=(holdout_decision,),
        ),
        holdout_policy_book=VersionedPhase20ForwardPolicyBook(
            generation=1,
            decisions=(_policy(holdout_decision.evidence_sha256),),
        ),
        qualification_evidence_store_sha256=_sha(1),
        qualification_policy_store_sha256=_sha(2),
        holdout_evidence_store_sha256=_sha(11),
        holdout_policy_store_sha256=_sha(12),
    )

    assert report.status is Phase22HoldoutQualificationStatus.INVALID
    assert report.economic_report is None
    assert "QUALIFICATION_DECISION_REUSED_IN_HOLDOUT" in report.failures
    assert report.economically_certified is False
