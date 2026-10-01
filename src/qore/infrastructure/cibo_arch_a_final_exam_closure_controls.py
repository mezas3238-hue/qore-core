"""Bind Architect-A scientific/Compound closures into final-exam P7/P8 controls."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from qore.infrastructure.cibo_arch_a_internal_readiness import (
    ArchitectAPhase22V2CompoundClosureReceipt,
    ArchitectAPhase22V2ScientificClosureReceipt,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_final_certification import (
    Phase22QualificationReceipt,
)
from qore.infrastructure.cibo_final_exam_control_receipt import (
    CiboFinalExamControlReceipt,
    bind_final_exam_control_artifact,
)

_EVIDENCE_KIND = "FINAL_INTEGRATED_EXAM_CONTROL"
_SCHEMA = "qore.cibo.arch-a.final-exam-closure-control.v1"


def _artifact_json(
    *,
    receipt_id: str,
    producer_gate_id: str,
    integrated_git_sha: str,
    policy_identity_sha256: str,
    phase22_artifact_sha256: str,
    observed_at: datetime,
    phase22_manifest_sha256: str,
    closure_batch_sha256: str,
    closure_receipt_sha256: str,
    details: dict[str, Any],
) -> str:
    payload: dict[str, Any] = {
        "schema": _SCHEMA,
        "evidence_binding_id": receipt_id,
        "evidence_kind": _EVIDENCE_KIND,
        "producer_gate_id": producer_gate_id,
        "integrated_git_sha": integrated_git_sha,
        "policy_identity_sha256": policy_identity_sha256,
        "phase22_qualification_artifact_sha256": phase22_artifact_sha256,
        "certification_stage": "POST_PHASE22",
        "observed_at": observed_at.isoformat(),
        "status": "PASS",
        "failures": [],
        "productive_authority": False,
        "synthetic_evidence_used": False,
        "holdout_mining_used": False,
        "outcome_aware_refit": False,
        "operational_authority_claimed": False,
        "phase22_handoff_manifest_sha256": phase22_manifest_sha256,
        "closure_batch_sha256": closure_batch_sha256,
        "closure_receipt_sha256": closure_receipt_sha256,
        "details": details,
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def build_architect_a_final_exam_closure_controls(
    *,
    integrated_git_sha: str,
    phase22_receipt: Phase22QualificationReceipt,
    scientific_closure: ArchitectAPhase22V2ScientificClosureReceipt,
    compound_closure: ArchitectAPhase22V2CompoundClosureReceipt,
    observed_at: datetime,
) -> tuple[CiboFinalExamControlReceipt, CiboFinalExamControlReceipt]:
    if not isinstance(phase22_receipt, Phase22QualificationReceipt):
        raise CiboCapitalManagementError(
            "A final-exam closure controls require canonical Phase22 receipt"
        )
    if not isinstance(
        scientific_closure,
        ArchitectAPhase22V2ScientificClosureReceipt,
    ):
        raise CiboCapitalManagementError(
            "A final-exam P7 requires canonical scientific closure"
        )
    if not isinstance(
        compound_closure,
        ArchitectAPhase22V2CompoundClosureReceipt,
    ):
        raise CiboCapitalManagementError(
            "A final-exam P8 requires canonical Compound closure"
        )
    if observed_at.tzinfo is None or observed_at.utcoffset() is None:
        raise CiboCapitalManagementError(
            "A final-exam closure observed_at must be timezone-aware"
        )
    if observed_at <= phase22_receipt.qualified_at:
        raise CiboCapitalManagementError(
            "A final-exam closure controls must be post-Phase22 qualification"
        )
    if (
        scientific_closure.phase22_manifest_sha256
        != compound_closure.phase22_manifest_sha256
        or scientific_closure.closure_batch_sha256
        != compound_closure.closure_batch_sha256
    ):
        raise CiboCapitalManagementError(
            "A final-exam closure lineage drift"
        )
    if (
        not scientific_closure.scientific_closure_terminal
        or scientific_closure.blockers
    ):
        raise CiboCapitalManagementError(
            "A final-exam P7 scientific closure is not terminal"
        )
    if (
        not compound_closure.compound_closure_terminal
        or compound_closure.blockers
        or compound_closure.missing_or_nonproven_ids
    ):
        raise CiboCapitalManagementError(
            "A final-exam P8 Compound closure is not proven"
        )

    common = {
        "integrated_git_sha": integrated_git_sha,
        "policy_identity_sha256": phase22_receipt.candidate_parameter_sha256,
        "phase22_artifact_sha256": (
            phase22_receipt.qualification_artifact_sha256
        ),
        "observed_at": observed_at,
        "phase22_manifest_sha256": (
            scientific_closure.phase22_manifest_sha256
        ),
        "closure_batch_sha256": scientific_closure.closure_batch_sha256,
    }
    p7_json = _artifact_json(
        receipt_id="P7_SCIENTIFIC_CLOSURE",
        producer_gate_id="CIBO_ARCH_A_PHASE22_V2_SCIENTIFIC_CLOSURE",
        closure_receipt_sha256=scientific_closure.fingerprint(),
        details={
            "completed_ids": list(scientific_closure.completed_ids),
            "falsified_ids": list(scientific_closure.falsified_ids),
            "scientific_closure_terminal": True,
        },
        **common,
    )
    p8_json = _artifact_json(
        receipt_id="P8_COMPOUND_CLOSURE",
        producer_gate_id="CIBO_ARCH_A_PHASE22_V2_COMPOUND_CLOSURE",
        closure_receipt_sha256=compound_closure.fingerprint(),
        details={
            "required_proven_ids": list(compound_closure.required_proven_ids),
            "compound_closure_terminal": True,
            "genc1_evidence_sha256": compound_closure.genc1_evidence_sha256,
        },
        **common,
    )
    return (
        bind_final_exam_control_artifact(
            receipt_id="P7_SCIENTIFIC_CLOSURE",
            evidence_kind=_EVIDENCE_KIND,
            source_artifact_json=p7_json,
        ),
        bind_final_exam_control_artifact(
            receipt_id="P8_COMPOUND_CLOSURE",
            evidence_kind=_EVIDENCE_KIND,
            source_artifact_json=p8_json,
        ),
    )
