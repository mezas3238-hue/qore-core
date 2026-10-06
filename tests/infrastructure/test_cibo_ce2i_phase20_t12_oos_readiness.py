from datetime import timedelta

import pytest

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_policy_store import (
    Phase20ForwardPolicyDecisionSeal,
    VersionedPhase20ForwardPolicyBook,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_store import (
    Phase20ForwardDecisionSeal,
    VersionedPhase20ForwardEvidenceBook,
)
from qore.infrastructure.cibo_ce2i_phase20_t12_oos_readiness import (
    assess_phase20_t12_oos_readiness,
)
from qore.infrastructure.cibo_ce2i_phase20_t12_shadow_policy import (
    T12_SHADOW_POLICY_FROZEN_AT,
    t12_shadow_policy_sha256,
)
from qore.infrastructure.cibo_ce2i_phase20_t12_shadow_store import (
    T12ShadowDecisionSeal,
)


def _decision() -> Phase20ForwardDecisionSeal:
    decision_at = T12_SHADOW_POLICY_FROZEN_AT + timedelta(minutes=1)
    return Phase20ForwardDecisionSeal(
        evidence_id="t12-oos-evidence",
        decision_epoch_id="t12-oos-epoch",
        evidence_sha256="sha256:" + "1" * 64,
        decision_at=decision_at,
        candidate_id="candidate-v3",
        code_sha="a" * 40,
        parameter_sha256="sha256:" + "b" * 64,
        signal_fingerprints=(),
        canonical_payload_json=(
            '{"candidates":[],"evidence_kind":"FORWARD_OBSERVED"}'
        ),
        sealed_at=decision_at + timedelta(milliseconds=100),
        seal_deadline_at=decision_at + timedelta(seconds=2),
    )


def _policy() -> Phase20ForwardPolicyDecisionSeal:
    return Phase20ForwardPolicyDecisionSeal(
        evidence_sha256="sha256:" + "1" * 64,
        policy_record_sha256="sha256:" + "2" * 64,
        allocator_disposition="PRESERVE_CAPACITY",
        selected_signal_fingerprints=(),
        canonical_record_json="{}",
    )


def _shadow(
    *,
    baseline_sha: str = "sha256:" + "2" * 64,
) -> T12ShadowDecisionSeal:
    decision_at = T12_SHADOW_POLICY_FROZEN_AT + timedelta(minutes=1)
    return T12ShadowDecisionSeal(
        shadow_decision_sha256="sha256:" + "3" * 64,
        policy_sha256=t12_shadow_policy_sha256(),
        decision_epoch_id="t12-oos-epoch",
        decision_evidence_sha256="sha256:" + "1" * 64,
        baseline_policy_record_sha256=baseline_sha,
        decision_at=decision_at,
        shadow_sealed_at=decision_at + timedelta(seconds=1),
        treatment_enabled_tools=("T03",),
        treatment_blocked_tools=("T09",),
        control_enabled_tools=("T03", "T09"),
        control_blocked_tools=(),
        treatment_allocator_disposition="PRESERVE_CAPACITY",
        control_allocator_disposition="PRESERVE_CAPACITY",
        treatment_allocator_applied_tools=("T03",),
        control_allocator_applied_tools=("T03",),
        treatment_selected_signal_fingerprints=(),
        control_selected_signal_fingerprints=(),
        selection_changed=False,
        allocator_changed=False,
    )


def test_t12_oos_empty_population_fails_closed_without_claiming_utility() -> None:
    readiness = assess_phase20_t12_oos_readiness(
        evidence_book=VersionedPhase20ForwardEvidenceBook(generation=0),
        treatment_policy_book=VersionedPhase20ForwardPolicyBook(generation=0),
        shadow_decisions=(),
    )

    assert readiness.ready_for_utility_analysis is False
    assert readiness.fresh_oos_utility_demonstrated is False
    assert readiness.post_freeze_decision_epochs == 0
    assert "T12_MINIMUM_DECISION_EPOCHS_NOT_MET" in readiness.blockers
    assert readiness.decision_sha256s == ()


def test_t12_oos_binds_treatment_and_shadow_without_reading_pnl() -> None:
    decision = _decision()
    readiness = assess_phase20_t12_oos_readiness(
        evidence_book=VersionedPhase20ForwardEvidenceBook(
            generation=1,
            decisions=(decision,),
        ),
        treatment_policy_book=VersionedPhase20ForwardPolicyBook(
            generation=1,
            decisions=(_policy(),),
        ),
        shadow_decisions=(_shadow(),),
    )

    assert readiness.missing_shadow_decisions == 0
    assert readiness.missing_treatment_policy_decisions == 0
    assert readiness.shadow_sealed_epochs == 1
    assert readiness.selection_changed_epochs == 0
    assert readiness.ready_for_utility_analysis is False
    assert "T12_NO_SELECTION_CHANGE_EPOCHS" in readiness.blockers


def test_t12_oos_fails_closed_on_policy_shadow_digest_drift() -> None:
    decision = _decision()
    with pytest.raises(
        CiboCapitalManagementError,
        match="treatment/shadow binding drift",
    ):
        assess_phase20_t12_oos_readiness(
            evidence_book=VersionedPhase20ForwardEvidenceBook(
                generation=1,
                decisions=(decision,),
            ),
            treatment_policy_book=VersionedPhase20ForwardPolicyBook(
                generation=1,
                decisions=(_policy(),),
            ),
            shadow_decisions=(
                _shadow(baseline_sha="sha256:" + "4" * 64),
            ),
        )
