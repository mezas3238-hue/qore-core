"""Build deterministic World Cup entry controls WC01 and WC02."""

from __future__ import annotations

import json
from datetime import datetime

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_final_integrated_exam import (
    FinalIntegratedExamReport,
    FinalIntegratedExamStatus,
)
from qore.infrastructure.cibo_world_cup_maximum_capability_exam import (
    WorldCupControlReceipt,
    bind_world_cup_control_artifact,
    final_integrated_exam_report_sha256,
    world_cup_policy_identity_sha256,
)

_SCHEMA = "qore.cibo.world-cup-entry-control.v1"
_EVIDENCE_KIND = "WORLD_CUP_MAXIMUM_CAPABILITY_CONTROL"


def _artifact_json(
    *,
    receipt_id: str,
    producer_gate_id: str,
    integrated_git_sha: str,
    final_report_sha256: str,
    observed_at: datetime,
    control_field: str,
) -> str:
    payload = {
        "schema": _SCHEMA,
        "evidence_binding_id": receipt_id,
        "evidence_kind": _EVIDENCE_KIND,
        "producer_gate_id": producer_gate_id,
        "integrated_git_sha": integrated_git_sha,
        "world_cup_policy_identity_sha256": (
            world_cup_policy_identity_sha256()
        ),
        "final_integrated_exam_report_sha256": final_report_sha256,
        "certification_stage": "POST_FINAL_INTEGRATED",
        "observed_at": observed_at.isoformat(),
        "status": "PASS",
        "failures": [],
        "productive_authority": False,
        "synthetic_evidence_used": False,
        "outcome_aware_refit": False,
        "post_hoc_selection_used": False,
        "aspirational_return_target_used": False,
        "hidden_leverage_used": False,
        "protected_holdout_reused": False,
        "future_information_used": False,
        "operational_authority_claimed": False,
        control_field: True,
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def build_world_cup_entry_controls(
    *,
    integrated_git_sha: str,
    final_integrated_exam: FinalIntegratedExamReport,
    observed_at: datetime,
) -> tuple[WorldCupControlReceipt, WorldCupControlReceipt]:
    if not isinstance(final_integrated_exam, FinalIntegratedExamReport):
        raise CiboCapitalManagementError(
            "World Cup entry controls require canonical Final Integrated report"
        )
    if (
        final_integrated_exam.status is not FinalIntegratedExamStatus.PASS
        or final_integrated_exam.blockers
    ):
        raise CiboCapitalManagementError(
            "World Cup entry controls require Final Integrated PASS"
        )
    if final_integrated_exam.integrated_head_sha != integrated_git_sha:
        raise CiboCapitalManagementError(
            "World Cup entry controls Final Integrated HEAD drift"
        )
    if observed_at.tzinfo is None or observed_at.utcoffset() is None:
        raise CiboCapitalManagementError(
            "World Cup entry controls observed_at must be timezone-aware"
        )

    final_sha = final_integrated_exam_report_sha256(final_integrated_exam)
    wc01 = bind_world_cup_control_artifact(
        receipt_id="WC01_FINAL_INTEGRATED_EXAM_PASS",
        source_artifact_json=_artifact_json(
            receipt_id="WC01_FINAL_INTEGRATED_EXAM_PASS",
            producer_gate_id="CIBO_WORLD_CUP_ENTRY_WC01_V1",
            integrated_git_sha=integrated_git_sha,
            final_report_sha256=final_sha,
            observed_at=observed_at,
            control_field="final_integrated_exam_passed",
        ),
    )
    wc02 = bind_world_cup_control_artifact(
        receipt_id="WC02_PROTOCOL_FREEZE",
        source_artifact_json=_artifact_json(
            receipt_id="WC02_PROTOCOL_FREEZE",
            producer_gate_id="CIBO_WORLD_CUP_ENTRY_WC02_V1",
            integrated_git_sha=integrated_git_sha,
            final_report_sha256=final_sha,
            observed_at=observed_at,
            control_field="world_cup_protocol_frozen",
        ),
    )
    return wc01, wc02
