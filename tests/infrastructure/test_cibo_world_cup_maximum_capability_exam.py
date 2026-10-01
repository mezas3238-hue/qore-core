from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_final_integrated_exam import (
    FINAL_INTEGRATED_EXAM_ID,
    FinalIntegratedExamReport,
    FinalIntegratedExamStatus,
)
from qore.infrastructure.cibo_world_cup_maximum_capability_exam import (
    WorldCupMaximumCapabilityStatus,
    assess_receipt_bound_world_cup_maximum_capability_exam,
    bind_world_cup_control_artifact,
    final_integrated_exam_report_sha256,
    required_world_cup_receipt_ids,
    world_cup_policy_identity_sha256,
)

T0 = datetime(2026, 10, 1, 18, 30, tzinfo=UTC)
HEAD = "a" * 40

_FIELDS = {
    "WC01_FINAL_INTEGRATED_EXAM_PASS": ("final_integrated_exam_passed",),
    "WC02_PROTOCOL_FREEZE": ("world_cup_protocol_frozen",),
    "WC03_COMPETITION_PROVIDER_ADAPTER": (
        "competition_provider_bound",
        "provider_economics_complete",
    ),
    "WC04_WORLD_CUP_DIGITAL_TWIN": (
        "competition_digital_twin_bound",
        "capital_conservation_proven",
    ),
    "WC05_AS_IS_CONTROL": ("as_is_control_frozen",),
    "WC06_AMPLIFICATION_CAUSAL_ATTRIBUTION": (
        "causal_attribution_complete",
    ),
    "WC07_PATH_DEPENDENT_MONTE_CARLO": ("path_structure_preserved",),
    "WC08_ADVERSARIAL_STRESS": ("stress_noncompensatory_pass",),
    "WC09_TEMPORAL_REPLICATION": ("four_fold_replication_pass",),
    "WC10_SURVIVAL_CAPITAL_PRODUCTIVITY": (
        "survival_nonworse",
        "tail_nonworse",
        "plausible_loss_nonworse",
        "capital_productivity_improved",
    ),
}


def _final(*, passed: bool = True, head: str = HEAD) -> FinalIntegratedExamReport:
    return FinalIntegratedExamReport(
        exam_id=FINAL_INTEGRATED_EXAM_ID,
        status=(
            FinalIntegratedExamStatus.PASS
            if passed else FinalIntegratedExamStatus.BLOCKED
        ),
        integrated_head_sha=head,
        blockers=() if passed else ("PRE_EXAM_REQUIRED",),
    )


def _artifact(
    receipt_id: str,
    *,
    final: FinalIntegratedExamReport,
    override_field: str | None = None,
    contaminated: str | None = None,
) -> str:
    payload: dict[str, object] = {
        "schema": "qore.cibo.world-cup-control.test.v2",
        "evidence_binding_id": receipt_id,
        "evidence_kind": "WORLD_CUP_MAXIMUM_CAPABILITY_CONTROL",
        "producer_gate_id": f"world-cup:{receipt_id}",
        "integrated_git_sha": final.integrated_head_sha,
        "world_cup_policy_identity_sha256": world_cup_policy_identity_sha256(),
        "final_integrated_exam_report_sha256": (
            final_integrated_exam_report_sha256(final)
        ),
        "certification_stage": "POST_FINAL_INTEGRATED",
        "observed_at": T0.isoformat(),
        "status": "PASS",
        "failures": [],
        "productive_authority": False,
        "synthetic_evidence_used": False,
        "outcome_aware_refit": False,
        "post_hoc_selection_used": False,
        "aspirational_return_target_used": False,
        "hidden_leverage_used": False,
        "protected_holdout_reused": False,
        "operational_authority_claimed": False,
    }
    for field in _FIELDS[receipt_id]:
        payload[field] = field != override_field
    if contaminated is not None:
        payload[contaminated] = True
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _receipts(
    final: FinalIntegratedExamReport,
    *,
    override_field: str | None = None,
    contaminated: str | None = None,
):
    return tuple(
        bind_world_cup_control_artifact(
            receipt_id=receipt_id,
            source_artifact_json=_artifact(
                receipt_id,
                final=final,
                override_field=override_field,
                contaminated=contaminated,
            ),
        )
        for receipt_id in required_world_cup_receipt_ids()
    )


def test_world_cup_pass_is_noncompensatory_and_grants_no_authority() -> None:
    final = _final()
    report = assess_receipt_bound_world_cup_maximum_capability_exam(
        integrated_head_sha=HEAD,
        final_integrated_exam=final,
        receipts=_receipts(final),
    )
    assert len(required_world_cup_receipt_ids()) == 10
    assert report.status is WorldCupMaximumCapabilityStatus.PASS
    assert report.blockers == ()
    assert report.live_authorized is False
    assert report.real_capital_authorized is False
    assert report.merge_authorized is False


def test_world_cup_requires_passed_final_integrated_exam() -> None:
    final = _final(passed=False)
    with pytest.raises(
        CiboCapitalManagementError,
        match="requires passed Final Integrated CIBO Exam",
    ):
        assess_receipt_bound_world_cup_maximum_capability_exam(
            integrated_head_sha=HEAD,
            final_integrated_exam=final,
            receipts=(),
        )


def test_world_cup_missing_receipt_fails_closed() -> None:
    final = _final()
    with pytest.raises(
        CiboCapitalManagementError,
        match="required receipts missing",
    ):
        assess_receipt_bound_world_cup_maximum_capability_exam(
            integrated_head_sha=HEAD,
            final_integrated_exam=final,
            receipts=_receipts(final)[:-1],
        )


def test_world_cup_failed_dimension_cannot_be_rescued() -> None:
    final = _final()
    report = assess_receipt_bound_world_cup_maximum_capability_exam(
        integrated_head_sha=HEAD,
        final_integrated_exam=final,
        receipts=_receipts(
            final,
            override_field="capital_productivity_improved",
        ),
    )
    assert report.status is WorldCupMaximumCapabilityStatus.BLOCKED
    assert report.blockers == (
        "WC10_SURVIVAL_CAPITAL_PRODUCTIVITY:capital_productivity_improved",
    )


def test_world_cup_governance_contamination_fails_closed() -> None:
    final = _final()
    with pytest.raises(
        CiboCapitalManagementError,
        match="governance contamination",
    ):
        _receipts(final, contaminated="aspirational_return_target_used")


def test_world_cup_receipts_are_bound_to_final_integrated_report() -> None:
    final = _final()
    receipts = _receipts(final)
    other = _final(head="e" * 40)
    with pytest.raises(
        CiboCapitalManagementError,
        match="HEAD drift",
    ):
        assess_receipt_bound_world_cup_maximum_capability_exam(
            integrated_head_sha=other.integrated_head_sha,
            final_integrated_exam=other,
            receipts=receipts,
        )


def test_world_cup_external_dependency_blocks_exam() -> None:
    final = _final()
    report = assess_receipt_bound_world_cup_maximum_capability_exam(
        integrated_head_sha=HEAD,
        final_integrated_exam=final,
        receipts=_receipts(final),
        certification_critical_external_blockers=("PROVIDER",),
    )
    assert report.status is WorldCupMaximumCapabilityStatus.BLOCKED
    assert report.blockers == ("CERTIFICATION_CRITICAL_EXTERNAL_BLOCKER",)
