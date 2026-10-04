from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_crossboundary_evidence_receipt import (
    bind_cross_boundary_pass_artifact,
)
from qore.infrastructure.cibo_final_integrated_exam import (
    FINAL_INTEGRATED_EXAM_ID,
    FinalIntegratedExamReport,
    FinalIntegratedExamStatus,
)
from qore.infrastructure.cibo_world_cup_maximum_capability_exam import (
    WorldCupMaximumCapabilityStatus,
    assess_receipt_bound_world_cup_maximum_capability_exam,
    required_world_cup_receipt_ids,
)

T0 = datetime(2026, 10, 1, 6, 0, tzinfo=UTC)
HEAD = "a" * 40
POLICY = "sha256:" + "b" * 64

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
        "no_capital_creation",
        "no_duplicated_profit",
        "no_reused_released_capacity",
        "no_double_counted_netting",
        "margin_feasible",
        "chronology_monotonic",
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
            if passed
            else FinalIntegratedExamStatus.BLOCKED
        ),
        integrated_head_sha=head,
        blockers=() if passed else ("PRE_EXAM_REQUIRED",),
    )


def _artifact(
    receipt_id: str,
    *,
    override_field: str | None = None,
    contaminated: str | None = None,
) -> str:
    payload: dict[str, object] = {
        "schema": "qore.cibo.world-cup-test.v1",
        "evidence_binding_id": receipt_id,
        "evidence_kind": "WORLD_CUP_MAXIMUM_CAPABILITY_CONTROL",
        "producer_gate_id": f"world-cup:{receipt_id}",
        "integrated_git_sha": HEAD,
        "policy_identity_sha256": POLICY,
        "observed_at": T0.isoformat(),
        "status": "PASS",
        "failures": [],
        "holdout_outcomes_inspected": False,
        "productive_authority": False,
        "synthetic_evidence_used": False,
        "outcome_aware_refit": False,
        "post_hoc_selection_used": False,
        "aspirational_return_target_used": False,
        "hidden_leverage_used": False,
        "protected_holdout_reused": False,
        "future_information_used": False,
        "operational_authority_claimed": False,
    }
    for field in _FIELDS[receipt_id]:
        payload[field] = field != override_field
    if contaminated is not None:
        payload[contaminated] = True
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _receipts(
    *,
    override_field: str | None = None,
    contaminated: str | None = None,
):
    return tuple(
        bind_cross_boundary_pass_artifact(
            receipt_id=receipt_id,
            evidence_kind="WORLD_CUP_MAXIMUM_CAPABILITY_CONTROL",
            source_artifact_json=_artifact(
                receipt_id,
                override_field=override_field,
                contaminated=contaminated,
            ),
        )
        for receipt_id in required_world_cup_receipt_ids()
    )


def test_world_cup_pass_is_noncompensatory_and_grants_no_authority() -> None:
    report = assess_receipt_bound_world_cup_maximum_capability_exam(
        integrated_head_sha=HEAD,
        world_cup_policy_identity_sha256=POLICY,
        final_integrated_exam=_final(),
        receipts=_receipts(),
    )

    assert len(required_world_cup_receipt_ids()) == 10
    assert report.status is WorldCupMaximumCapabilityStatus.PASS
    assert report.blockers == ()
    assert report.live_authorized is False
    assert report.real_capital_authorized is False
    assert report.merge_authorized is False


def test_missing_world_cup_receipt_fails_closed() -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="required receipts missing",
    ):
        assess_receipt_bound_world_cup_maximum_capability_exam(
            integrated_head_sha=HEAD,
            world_cup_policy_identity_sha256=POLICY,
            final_integrated_exam=_final(),
            receipts=_receipts()[:-1],
        )


def test_final_integrated_exam_must_pass_first() -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="requires passed Final Integrated CIBO Exam",
    ):
        assess_receipt_bound_world_cup_maximum_capability_exam(
            integrated_head_sha=HEAD,
            world_cup_policy_identity_sha256=POLICY,
            final_integrated_exam=_final(passed=False),
            receipts=_receipts(),
        )


def test_failed_control_blocks_without_pooled_rescue() -> None:
    report = assess_receipt_bound_world_cup_maximum_capability_exam(
        integrated_head_sha=HEAD,
        world_cup_policy_identity_sha256=POLICY,
        final_integrated_exam=_final(),
        receipts=_receipts(override_field="capital_productivity_improved"),
    )

    assert report.status is WorldCupMaximumCapabilityStatus.BLOCKED
    assert report.blockers == (
        "WC10_SURVIVAL_CAPITAL_PRODUCTIVITY:capital_productivity_improved",
    )


def test_aspirational_return_target_cannot_be_used_for_tuning() -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="governance contamination",
    ):
        assess_receipt_bound_world_cup_maximum_capability_exam(
            integrated_head_sha=HEAD,
            world_cup_policy_identity_sha256=POLICY,
            final_integrated_exam=_final(),
            receipts=_receipts(
                contaminated="aspirational_return_target_used"
            ),
        )


def test_certification_external_dependency_blocks_world_cup() -> None:
    report = assess_receipt_bound_world_cup_maximum_capability_exam(
        integrated_head_sha=HEAD,
        world_cup_policy_identity_sha256=POLICY,
        final_integrated_exam=_final(),
        receipts=_receipts(),
        certification_critical_external_blockers=("PHASE20D_POPULATION",),
    )

    assert report.status is WorldCupMaximumCapabilityStatus.BLOCKED
    assert report.blockers == ("CERTIFICATION_CRITICAL_EXTERNAL_BLOCKER",)
