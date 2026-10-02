from __future__ import annotations

from qore.infrastructure.cibo_ce2i_holdout_registry import (
    CiboHoldoutCandidateStatus,
    candidate_is_burn_clean_for_all_lineages,
)
from qore.infrastructure.cibo_phase22_next_exam_governance import (
    CONSUMED_V2_CANDIDATE_ID,
    CURRENT_NEXT_PHASE22_READINESS,
    NEXT_CANDIDATE_ID,
    NEXT_PHASE22_CANDIDATE,
    NextPhase22ExamEvidence,
    NextPhase22ReadinessStatus,
    assess_next_phase22_exam,
    next_phase22_governance_payload,
    next_phase22_governance_sha256,
)


def _sha(char: str) -> str:
    return "sha256:" + char * 64


def test_next_candidate_is_mechanical_disjoint_six_month_predecessor() -> None:
    assert NEXT_PHASE22_CANDIDATE.candidate_id == NEXT_CANDIDATE_ID
    assert NEXT_PHASE22_CANDIDATE.start_at.isoformat() == (
        "2015-04-19T00:00:00+00:00"
    )
    assert NEXT_PHASE22_CANDIDATE.end_exclusive_at.isoformat() == (
        "2015-10-19T00:00:00+00:00"
    )
    assert (
        NEXT_PHASE22_CANDIDATE.status
        is CiboHoldoutCandidateStatus.ELIGIBLE_FROZEN
    )
    assert NEXT_PHASE22_CANDIDATE.source_validation_complete is True
    assert NEXT_PHASE22_CANDIDATE.outcome_data_inspected_at_selection is False
    assert candidate_is_burn_clean_for_all_lineages(NEXT_PHASE22_CANDIDATE)


def test_current_next_exam_is_fail_closed_not_ready() -> None:
    result = CURRENT_NEXT_PHASE22_READINESS

    assert result.status is NextPhase22ReadinessStatus.NOT_READY
    assert "TURTLE_SUBORDINATE_WINDOW_INTEGRITY_CI_REQUIRED" not in result.blockers
    assert (
        "ADVANCED_CE2I_PREDECISION_EVIDENCE_OR_ABSTENTION_FREEZE_REQUIRED"
        not in result.blockers
    )
    assert "FROZEN_POLICY_CODE_BUNDLE_LINEAGE_REQUIRED" not in result.blockers
    assert "NEW_HOLDOUT_SOURCE_VALIDATION_REQUIRED" not in result.blockers
    assert result.blockers == ("NEW_ONE_SHOT_OWNER_AUTHORIZATION_REQUIRED",)
    assert result.second_v2_execution_authorized is False


def test_consumed_v2_can_never_become_next_fresh_exam() -> None:
    result = assess_next_phase22_exam(
        NextPhase22ExamEvidence(
            candidate_id=CONSUMED_V2_CANDIDATE_ID,
            second_v2_execution_requested=True,
        )
    )

    assert result.status is NextPhase22ReadinessStatus.INVALID
    assert "CONSUMED_V2_SECOND_FRESH_EXECUTION_FORBIDDEN" in result.blockers


def test_candidate_outcome_inspection_invalidates_next_exam() -> None:
    result = assess_next_phase22_exam(
        NextPhase22ExamEvidence(
            candidate_id=NEXT_CANDIDATE_ID,
            source_outcomes_inspected=True,
        )
    )

    assert result.status is NextPhase22ReadinessStatus.INVALID
    assert "NEW_HOLDOUT_OUTCOME_CONTAMINATION_FORBIDDEN" in result.blockers


def test_ready_requires_all_receipts_and_still_grants_no_productive_authority() -> None:
    result = assess_next_phase22_exam(
        NextPhase22ExamEvidence(
            candidate_id=NEXT_CANDIDATE_ID,
            turtle_window_integrity_run_id=123,
            turtle_window_integrity_head_sha="a" * 40,
            advanced_predecision_evidence_freeze_sha256=_sha("b"),
            policy_code_bundle_lineage_sha256=_sha("c"),
            source_receipt_sha256=_sha("d"),
            source_validation_complete=True,
            source_outcomes_inspected=False,
            owner_authorization_id="OWNER_NEXT_PHASE22_ONE_SHOT_TEST",
        )
    )

    assert result.status is NextPhase22ReadinessStatus.READY
    assert result.blockers == ()
    assert result.burn_clean is True
    assert result.second_v2_execution_authorized is False
    assert result.productive_authority is False


def test_governance_payload_is_nonexecuting_and_digest_bound() -> None:
    payload = next_phase22_governance_payload()

    assert payload["consumed_v2_rerun_authorized"] is False
    assert payload["candidate"]["status"] == "ELIGIBLE_FROZEN"
    assert payload["candidate"]["source_validation_complete"] is True
    assert payload["broker_mutation_authorized"] is False
    assert payload["live_authorized"] is False
    assert payload["real_capital_authorized"] is False
    assert payload["production_authorized"] is False
    assert payload["merge_authorized"] is False
    assert next_phase22_governance_sha256().startswith("sha256:")
