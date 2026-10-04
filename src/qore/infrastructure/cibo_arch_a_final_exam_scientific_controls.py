"""Derive Final Integrated Exam E7/E8/E9 from frozen Architect-A science."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from qore.infrastructure.cibo_arch_a_internal_readiness import (
    ArchitectAPhase22V2ScientificDispositionReceipt,
    ArchitectAPhase22V2ScientificIntakeReport,
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
from qore.infrastructure.cibo_scientific_closure_41 import (
    ScientificClosure41Evidence,
    ScientificClosure41Package,
)

_EVIDENCE_KIND = "FINAL_INTEGRATED_EXAM_CONTROL"
_SCHEMA = "qore.cibo.arch-a.final-scientific-control.v1"

_REQUIRED_BY_ASSERTION: dict[str, tuple[str, ...]] = {
    "E7_ECONOMIC_NONCOMPENSATION": (
        "GEN-C9",
        "PROTECTED_BASE_CAPITAL",
        "CAPITAL_AMPLIFICATION",
    ),
    "E8_STRESS_INTEGRITY": ("ADVERSARIAL_STRESS",),
    "E9_TEMPORAL_REPLICATION": ("TEMPORAL_REPLICATION",),
}


def _qualified_artifact_ref(
    intake: ArchitectAPhase22V2ScientificIntakeReport,
) -> str:
    refs = dict(intake.receipt_refs)
    value = refs.get("qualification_report_sha256")
    if value is None:
        raise CiboCapitalManagementError(
            "A final scientific controls require Phase22 qualification ref"
        )
    return value


def _require_proven_sources(
    *,
    assertion_id: str,
    intake: ArchitectAPhase22V2ScientificIntakeReport,
    dispositions: tuple[ArchitectAPhase22V2ScientificDispositionReceipt, ...],
) -> tuple[ArchitectAPhase22V2ScientificDispositionReceipt, ...]:
    required = _REQUIRED_BY_ASSERTION[assertion_id]
    if (
        not isinstance(dispositions, tuple)
        or any(
            not isinstance(
                item,
                ArchitectAPhase22V2ScientificDispositionReceipt,
            )
            for item in dispositions
        )
    ):
        raise CiboCapitalManagementError(
            "A final scientific controls require canonical dispositions"
        )
    by_id: dict[str, ArchitectAPhase22V2ScientificDispositionReceipt] = {}
    for item in dispositions:
        if item.workstream_id in by_id:
            raise CiboCapitalManagementError(
                "A final scientific controls duplicate workstream disposition"
            )
        if item.phase22_manifest_sha256 != intake.manifest_sha256:
            raise CiboCapitalManagementError(
                "A final scientific controls Phase22 manifest drift"
            )
        by_id[item.workstream_id] = item

    missing = tuple(item for item in required if item not in by_id)
    if missing:
        raise CiboCapitalManagementError(
            "A final scientific controls missing proven workstreams: "
            + ",".join(missing)
        )
    selected = tuple(by_id[item] for item in required)
    invalid = tuple(
        item.workstream_id
        for item in selected
        if (
            not item.passed
            or item.recommended_disposition != "COMPLETED_AND_PROVEN"
            or item.blockers
            or item.failed_dimensions
        )
    )
    if invalid:
        raise CiboCapitalManagementError(
            "A final scientific controls require positive frozen gates: "
            + ",".join(invalid)
        )
    return selected


def _artifact_json(
    *,
    assertion_id: str,
    integrated_git_sha: str,
    phase22_receipt: Phase22QualificationReceipt,
    intake: ArchitectAPhase22V2ScientificIntakeReport,
    observed_at: datetime,
    sources: tuple[ArchitectAPhase22V2ScientificDispositionReceipt, ...],
) -> str:
    payload: dict[str, Any] = {
        "schema": _SCHEMA,
        "evidence_binding_id": assertion_id,
        "evidence_kind": _EVIDENCE_KIND,
        "producer_gate_id": f"CIBO_ARCH_A_{assertion_id}_V1",
        "integrated_git_sha": integrated_git_sha,
        "policy_identity_sha256": phase22_receipt.candidate_parameter_sha256,
        "phase22_qualification_artifact_sha256": (
            phase22_receipt.qualification_artifact_sha256
        ),
        "certification_stage": "POST_PHASE22",
        "observed_at": observed_at.isoformat(),
        "status": "PASS",
        "failures": [],
        "productive_authority": False,
        "synthetic_evidence_used": False,
        "holdout_mining_used": False,
        "outcome_aware_refit": False,
        "operational_authority_claimed": False,
        "phase22_handoff_manifest_sha256": intake.manifest_sha256,
        "scientific_sources": [
            {
                "workstream_id": item.workstream_id,
                "source_gate_id": item.source_gate_id,
                "source_gate_evidence_sha256": item.source_gate_evidence_sha256,
                "source_gate_status": item.source_gate_status,
            }
            for item in sources
        ],
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"



def _require_closure41_positive_sources(
    *,
    assertion_id: str,
    closure_package: ScientificClosure41Package,
) -> tuple[ScientificClosure41Evidence, ...]:
    required = _REQUIRED_BY_ASSERTION[assertion_id]
    by_id = {item.workstream_id: item for item in closure_package.workstreams}
    missing = tuple(item for item in required if item not in by_id)
    if missing:
        raise CiboCapitalManagementError(
            "Closure41 final scientific controls missing workstreams: "
            + ",".join(missing)
        )
    selected = tuple(by_id[item] for item in required)
    for item in selected:
        if item.terminal_disposition != "COMPLETED_AND_PROVEN":
            raise CiboCapitalManagementError(
                "Closure41 final scientific control requires positive terminal gate: "
                + item.workstream_id
            )
        if assertion_id == "E7_ECONOMIC_NONCOMPENSATION":
            passed = item.economic_result == "PASS"
        elif assertion_id == "E8_STRESS_INTEGRITY":
            passed = item.stress_result == "PASS"
        else:
            passed = item.temporal_replication_result == "PASS"
        if not passed:
            raise CiboCapitalManagementError(
                "Closure41 final scientific control positive dimension failed: "
                + item.workstream_id
            )
    return selected


def build_closure41_final_exam_scientific_controls(
    *,
    integrated_git_sha: str,
    phase22_receipt: Phase22QualificationReceipt,
    closure_package: ScientificClosure41Package,
    observed_at: datetime,
) -> tuple[CiboFinalExamControlReceipt, ...]:
    """Build E7/E8/E9 only from positive dimensions in terminal Closure41."""

    if not isinstance(phase22_receipt, Phase22QualificationReceipt):
        raise CiboCapitalManagementError(
            "Closure41 final scientific controls require canonical Phase22 receipt"
        )
    if not isinstance(closure_package, ScientificClosure41Package):
        raise CiboCapitalManagementError(
            "Closure41 final scientific controls require canonical package"
        )
    if observed_at.tzinfo is None or observed_at.utcoffset() is None:
        raise CiboCapitalManagementError(
            "Closure41 final scientific controls observed_at must be timezone-aware"
        )
    if observed_at <= phase22_receipt.qualified_at:
        raise CiboCapitalManagementError(
            "Closure41 final scientific controls must be post-Phase22 qualification"
        )

    receipts: list[CiboFinalExamControlReceipt] = []
    for assertion_id in _REQUIRED_BY_ASSERTION:
        sources = _require_closure41_positive_sources(
            assertion_id=assertion_id,
            closure_package=closure_package,
        )
        payload: dict[str, Any] = {
            "schema": "qore.cibo.closure41.final-scientific-control.v1",
            "evidence_binding_id": assertion_id,
            "evidence_kind": _EVIDENCE_KIND,
            "producer_gate_id": f"CIBO_CLOSURE41_{assertion_id}_V1",
            "integrated_git_sha": integrated_git_sha,
            "policy_identity_sha256": phase22_receipt.candidate_parameter_sha256,
            "phase22_qualification_artifact_sha256": (
                phase22_receipt.qualification_artifact_sha256
            ),
            "certification_stage": "POST_PHASE22",
            "observed_at": observed_at.isoformat(),
            "status": "PASS",
            "failures": [],
            "productive_authority": False,
            "synthetic_evidence_used": False,
            "holdout_mining_used": False,
            "outcome_aware_refit": False,
            "operational_authority_claimed": False,
            "phase22_handoff_manifest_sha256": (
                closure_package.phase22_manifest_sha256
            ),
            "scientific_closure_41_sha256": closure_package.fingerprint(),
            "scientific_sources": [
                {
                    "workstream_id": item.workstream_id,
                    "terminal_disposition": item.terminal_disposition,
                    "evidence_sha256s": list(item.evidence_sha256s),
                    "economic_result": item.economic_result,
                    "stress_result": item.stress_result,
                    "temporal_replication_result": (
                        item.temporal_replication_result
                    ),
                }
                for item in sources
            ],
        }
        receipts.append(
            bind_final_exam_control_artifact(
                receipt_id=assertion_id,
                evidence_kind=_EVIDENCE_KIND,
                source_artifact_json=json.dumps(
                    payload, indent=2, sort_keys=True
                ) + "\n",
            )
        )
    return tuple(receipts)


def build_architect_a_final_exam_scientific_controls(
    *,
    integrated_git_sha: str,
    phase22_receipt: Phase22QualificationReceipt,
    intake: ArchitectAPhase22V2ScientificIntakeReport,
    dispositions: tuple[ArchitectAPhase22V2ScientificDispositionReceipt, ...],
    observed_at: datetime,
) -> tuple[CiboFinalExamControlReceipt, ...]:
    if not isinstance(phase22_receipt, Phase22QualificationReceipt):
        raise CiboCapitalManagementError(
            "A final scientific controls require canonical Phase22 receipt"
        )
    if not isinstance(intake, ArchitectAPhase22V2ScientificIntakeReport):
        raise CiboCapitalManagementError(
            "A final scientific controls require canonical Phase22 intake"
        )
    if not intake.ready_for_scientific_reentry or intake.blockers:
        raise CiboCapitalManagementError(
            "A final scientific controls require admissible Phase22 intake"
        )
    if (
        _qualified_artifact_ref(intake)
        != phase22_receipt.qualification_artifact_sha256
    ):
        raise CiboCapitalManagementError(
            "A final scientific controls qualification artifact drift"
        )
    if observed_at.tzinfo is None or observed_at.utcoffset() is None:
        raise CiboCapitalManagementError(
            "A final scientific controls observed_at must be timezone-aware"
        )
    if observed_at <= phase22_receipt.qualified_at:
        raise CiboCapitalManagementError(
            "A final scientific controls must be post-Phase22 qualification"
        )

    receipts: list[CiboFinalExamControlReceipt] = []
    for assertion_id in _REQUIRED_BY_ASSERTION:
        sources = _require_proven_sources(
            assertion_id=assertion_id,
            intake=intake,
            dispositions=dispositions,
        )
        artifact = _artifact_json(
            assertion_id=assertion_id,
            integrated_git_sha=integrated_git_sha,
            phase22_receipt=phase22_receipt,
            intake=intake,
            observed_at=observed_at,
            sources=sources,
        )
        receipts.append(
            bind_final_exam_control_artifact(
                receipt_id=assertion_id,
                evidence_kind=_EVIDENCE_KIND,
                source_artifact_json=artifact,
            )
        )
    return tuple(receipts)
