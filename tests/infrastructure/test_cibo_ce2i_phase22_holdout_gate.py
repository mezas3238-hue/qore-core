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
from qore.infrastructure.cibo_ce2i_phase20_qualification_plan import (
    FROZEN_PHASE20D_QUALIFICATION_PLAN,
    phase20d_qualification_plan_sha256,
)
from qore.infrastructure.cibo_ce2i_phase21_policy_freeze import (
    Phase21EmpiricalValidationKind,
    Phase21PolicySurfaceDigests,
    Phase21QualificationReceipt,
    build_phase21_empirical_validation_receipt,
    build_phase21_policy_freeze,
)
from qore.infrastructure.cibo_ce2i_phase22_holdout_gate import (
    assess_phase22_holdout_lineage,
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
        build_phase21_empirical_validation_receipt(
            kind=kind,
            qualification=qualification,
            validator_git_sha=f"{index + 1:040x}",
            observed_at=QUALIFIED_AT + timedelta(hours=index + 1),
            validation_payload={
                "protocol": f"TEST_{kind.value}",
                "source_decision_epochs": 80,
                "source_candidate_outcomes": 200,
                "source_selected_outcomes": 60,
            },
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
    collector_git_sha: str | None = COLLECTOR_SHA,
) -> Phase20ForwardDecisionSeal:
    candidate = FROZEN_PHASE20_POLICY_CANDIDATE
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
        signal_fingerprints=("signal-one",),
        canonical_payload_json='{"candidates":[]}',
        collector_git_sha=collector_git_sha,
    )


def _policy(evidence_sha: str) -> Phase20ForwardPolicyDecisionSeal:
    return Phase20ForwardPolicyDecisionSeal(
        evidence_sha256=evidence_sha,
        policy_record_sha256=_sha(500),
        allocator_disposition="ABSTAIN",
        selected_signal_fingerprints=(),
        canonical_record_json="{}",
    )


def _assess(
    *,
    qualification_decision: Phase20ForwardDecisionSeal,
    holdout_decision: Phase20ForwardDecisionSeal,
    policies: tuple[Phase20ForwardPolicyDecisionSeal, ...] | None = None,
):
    return assess_phase22_holdout_lineage(
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
            decisions=(
                (_policy(holdout_decision.evidence_sha256),)
                if policies is None
                else policies
            ),
        ),
        qualification_evidence_store_sha256=_sha(1),
        qualification_policy_store_sha256=_sha(2),
        holdout_evidence_store_sha256=_sha(11),
        holdout_policy_store_sha256=_sha(12),
    )


def test_phase22_lineage_accepts_only_fresh_disjoint_frozen_policy() -> None:
    qualification_decision = _decision(
        evidence_sha=_sha(201),
        decision_at=QUALIFIED_AT - timedelta(days=1),
    )
    holdout_decision = _decision(
        evidence_sha=_sha(202),
        decision_at=PHASE21_FROZEN_AT + timedelta(seconds=1),
    )

    assessment = _assess(
        qualification_decision=qualification_decision,
        holdout_decision=holdout_decision,
    )

    assert assessment.lineage_valid is True
    assert assessment.reasons == ()
    assert assessment.decision_epochs == 1
    assert assessment.policy_decisions == 1
    assert assessment.collector_git_shas == (COLLECTOR_SHA,)
    assert assessment.economic_holdout_passed is False


def test_phase22_lineage_rejects_pre_freeze_decision() -> None:
    qualification_decision = _decision(
        evidence_sha=_sha(201),
        decision_at=QUALIFIED_AT - timedelta(days=1),
    )
    holdout_decision = _decision(
        evidence_sha=_sha(202),
        decision_at=PHASE21_FROZEN_AT,
    )

    assessment = _assess(
        qualification_decision=qualification_decision,
        holdout_decision=holdout_decision,
    )

    assert assessment.lineage_valid is False
    assert "HOLDOUT_DECISION_NOT_POST_PHASE21_FREEZE" in assessment.reasons


def test_phase22_lineage_rejects_qualification_decision_reuse() -> None:
    reused_sha = _sha(201)
    qualification_decision = _decision(
        evidence_sha=reused_sha,
        decision_at=QUALIFIED_AT - timedelta(days=1),
    )
    holdout_decision = replace(
        qualification_decision,
        evidence_id="holdout-evidence",
        decision_epoch_id="holdout-epoch",
        decision_at=PHASE21_FROZEN_AT + timedelta(seconds=1),
        sealed_at=PHASE21_FROZEN_AT + timedelta(milliseconds=1100),
        seal_deadline_at=PHASE21_FROZEN_AT + timedelta(seconds=3),
    )

    assessment = _assess(
        qualification_decision=qualification_decision,
        holdout_decision=holdout_decision,
    )

    assert assessment.lineage_valid is False
    assert "QUALIFICATION_DECISION_REUSED_IN_HOLDOUT" in assessment.reasons


def test_phase22_lineage_requires_complete_collector_git_sha() -> None:
    qualification_decision = _decision(
        evidence_sha=_sha(201),
        decision_at=QUALIFIED_AT - timedelta(days=1),
    )
    holdout_decision = _decision(
        evidence_sha=_sha(202),
        decision_at=PHASE21_FROZEN_AT + timedelta(seconds=1),
        collector_git_sha=None,
    )

    assessment = _assess(
        qualification_decision=qualification_decision,
        holdout_decision=holdout_decision,
    )

    assert assessment.lineage_valid is False
    assert "HOLDOUT_COLLECTOR_GIT_LINEAGE_INCOMPLETE" in assessment.reasons


def test_phase22_lineage_requires_one_policy_record_per_decision() -> None:
    qualification_decision = _decision(
        evidence_sha=_sha(201),
        decision_at=QUALIFIED_AT - timedelta(days=1),
    )
    holdout_decision = _decision(
        evidence_sha=_sha(202),
        decision_at=PHASE21_FROZEN_AT + timedelta(seconds=1),
    )

    assessment = _assess(
        qualification_decision=qualification_decision,
        holdout_decision=holdout_decision,
        policies=(),
    )

    assert assessment.lineage_valid is False
    assert "HOLDOUT_POLICY_DECISION_SET_MISMATCH" in assessment.reasons
