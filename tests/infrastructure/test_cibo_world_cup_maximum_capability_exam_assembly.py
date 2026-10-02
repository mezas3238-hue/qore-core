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
    bind_world_cup_control_artifact,
    final_integrated_exam_report_sha256,
    required_world_cup_receipt_ids,
    world_cup_policy_identity_sha256,
)
from qore.infrastructure.cibo_world_cup_maximum_capability_exam_assembly import (
    assemble_world_cup_control_package,
    assess_assembled_world_cup_exam,
)

HEAD = "a" * 40
T0 = datetime(2026, 10, 1, 20, 0, tzinfo=UTC)

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


def _final(head: str = HEAD) -> FinalIntegratedExamReport:
    return FinalIntegratedExamReport(
        exam_id=FINAL_INTEGRATED_EXAM_ID,
        status=FinalIntegratedExamStatus.PASS,
        integrated_head_sha=head,
        blockers=(),
    )


def _receipts(final: FinalIntegratedExamReport):
    final_sha = final_integrated_exam_report_sha256(final)
    result = []
    for receipt_id in reversed(required_world_cup_receipt_ids()):
        payload: dict[str, object] = {
            "schema": "qore.cibo.world-cup-assembly.test.v1",
            "evidence_binding_id": receipt_id,
            "evidence_kind": "WORLD_CUP_MAXIMUM_CAPABILITY_CONTROL",
            "producer_gate_id": f"gate:{receipt_id}",
            "integrated_git_sha": final.integrated_head_sha,
            "world_cup_policy_identity_sha256": (
                world_cup_policy_identity_sha256()
            ),
            "final_integrated_exam_report_sha256": final_sha,
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
            payload[field] = True
        result.append(
            bind_world_cup_control_artifact(
                receipt_id=receipt_id,
                source_artifact_json=(
                    json.dumps(payload, indent=2, sort_keys=True) + "\n"
                ),
            )
        )
    return tuple(result)


def test_world_cup_assembly_orders_ten_and_executes() -> None:
    final = _final()
    package = assemble_world_cup_control_package(
        integrated_git_sha=HEAD,
        final_integrated_exam=final,
        receipts=_receipts(final),
    )
    assert tuple(item.receipt_id for item in package.receipts) == (
        required_world_cup_receipt_ids()
    )
    assert len(package.receipts) == 10
    assert package.fingerprint().startswith("sha256:")

    report = assess_assembled_world_cup_exam(
        package=package,
        final_integrated_exam=final,
    )
    assert report.status is WorldCupMaximumCapabilityStatus.PASS
    assert report.blockers == ()


def test_world_cup_assembly_rejects_missing_receipt() -> None:
    final = _final()
    with pytest.raises(CiboCapitalManagementError, match="missing receipts"):
        assemble_world_cup_control_package(
            integrated_git_sha=HEAD,
            final_integrated_exam=final,
            receipts=_receipts(final)[:-1],
        )


def test_world_cup_assembly_rejects_cross_head() -> None:
    final = _final()
    other = _final(head="b" * 40)
    with pytest.raises(
        CiboCapitalManagementError,
        match="Final Integrated HEAD drift",
    ):
        assemble_world_cup_control_package(
            integrated_git_sha=HEAD,
            final_integrated_exam=other,
            receipts=_receipts(final),
        )
