"""Build Final Integrated Exam P4-P6 from the exact Phase22 V2 chain."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from qore.infrastructure.cibo_arch_a_internal_readiness import (
    ArchitectAPhase22V2ScientificIntakeReport,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_final_certification import (
    Phase22QualificationReceipt,
)
from qore.infrastructure.cibo_ce2i_phase20_qualification_plan import (
    phase20d_qualification_plan_sha256,
)
from qore.infrastructure.cibo_ce2i_phase22_qualification_plan import (
    phase22_holdout_qualification_plan_sha256,
)
from qore.infrastructure.cibo_final_exam_control_receipt import (
    CiboFinalExamControlReceipt,
    bind_final_exam_control_artifact,
)

_EVIDENCE_KIND = "FINAL_INTEGRATED_EXAM_CONTROL"
_SCHEMA = "qore.cibo.final-integrated.phase22-prerequisite-control.v1"
_REQUIRED_SYSTEM_CONTROL_IDS = (
    "E1_AUTHORITY",
    "E2_CAPITAL_CONSERVATION",
    "E3_REALIZED_CAPITAL_LAW",
    "E4_PROVIDER_TRUTH",
    "E5_RISK_PRECEDENCE",
    "E6_CHRONOLOGY_NO_LEAKAGE",
    "E10_DETERMINISTIC_REPLAY",
)


def _intake_refs(
    intake: ArchitectAPhase22V2ScientificIntakeReport,
) -> dict[str, str]:
    refs = dict(intake.receipt_refs)
    if len(refs) != len(intake.receipt_refs):
        raise CiboCapitalManagementError(
            "P4-P6 duplicate Phase22 receipt kind"
        )
    return refs


def _system_control_map(
    *,
    controls: tuple[CiboFinalExamControlReceipt, ...],
    integrated_git_sha: str,
    phase22_receipt: Phase22QualificationReceipt,
) -> dict[str, CiboFinalExamControlReceipt]:
    if (
        not isinstance(controls, tuple)
        or any(not isinstance(item, CiboFinalExamControlReceipt) for item in controls)
    ):
        raise CiboCapitalManagementError(
            "P4-P6 require canonical system-control receipts"
        )
    by_id: dict[str, CiboFinalExamControlReceipt] = {}
    for item in controls:
        if item.receipt_id in by_id:
            raise CiboCapitalManagementError(
                "P4-P6 duplicate system-control receipt"
            )
        if item.integrated_git_sha != integrated_git_sha:
            raise CiboCapitalManagementError("P4-P6 integrated HEAD drift")
        if (
            item.policy_identity_sha256
            != phase22_receipt.candidate_parameter_sha256
        ):
            raise CiboCapitalManagementError("P4-P6 policy identity drift")
        if (
            item.phase22_qualification_artifact_sha256
            != phase22_receipt.qualification_artifact_sha256
        ):
            raise CiboCapitalManagementError("P4-P6 Phase22 artifact drift")
        by_id[item.receipt_id] = item

    missing = tuple(
        item for item in _REQUIRED_SYSTEM_CONTROL_IDS if item not in by_id
    )
    if missing:
        raise CiboCapitalManagementError(
            "P4-P6 missing system controls: " + ",".join(missing)
        )
    return by_id


def _artifact_json(
    *,
    receipt_id: str,
    integrated_git_sha: str,
    phase22_receipt: Phase22QualificationReceipt,
    intake: ArchitectAPhase22V2ScientificIntakeReport,
    observed_at: datetime,
    source_refs: dict[str, str],
    details: dict[str, Any],
) -> str:
    payload: dict[str, Any] = {
        "schema": _SCHEMA,
        "evidence_binding_id": receipt_id,
        "evidence_kind": _EVIDENCE_KIND,
        "producer_gate_id": f"CIBO_{receipt_id}_V1",
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
        "source_refs": source_refs,
        "details": details,
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def build_phase22_prerequisite_controls(
    *,
    integrated_git_sha: str,
    phase22_receipt: Phase22QualificationReceipt,
    intake: ArchitectAPhase22V2ScientificIntakeReport,
    system_controls: tuple[CiboFinalExamControlReceipt, ...],
    observed_at: datetime,
) -> tuple[CiboFinalExamControlReceipt, ...]:
    """Build P4/P5/P6 only from a coherent source-bound Phase22 PASS chain."""

    if not isinstance(phase22_receipt, Phase22QualificationReceipt):
        raise CiboCapitalManagementError(
            "P4-P6 require canonical Phase22 receipt"
        )
    if not isinstance(intake, ArchitectAPhase22V2ScientificIntakeReport):
        raise CiboCapitalManagementError(
            "P4-P6 require canonical Phase22 intake"
        )
    if (
        intake.qualification_status != "PASS"
        or not intake.ready_for_scientific_reentry
        or intake.blockers
    ):
        raise CiboCapitalManagementError(
            "P4-P6 require admissible Phase22 PASS intake"
        )
    if observed_at.tzinfo is None or observed_at.utcoffset() is None:
        raise CiboCapitalManagementError(
            "P4-P6 observed_at must be timezone-aware"
        )
    if observed_at <= phase22_receipt.qualified_at:
        raise CiboCapitalManagementError(
            "P4-P6 must be post-Phase22 qualification"
        )

    refs = _intake_refs(intake)
    if (
        refs["qualification_report_sha256"]
        != phase22_receipt.qualification_artifact_sha256
    ):
        raise CiboCapitalManagementError(
            "P4-P6 qualification artifact drift"
        )
    if (
        refs["holdout_evidence_store_sha256"]
        != phase22_receipt.holdout_evidence_store_sha256
        or refs["holdout_policy_store_sha256"]
        != phase22_receipt.holdout_policy_store_sha256
    ):
        raise CiboCapitalManagementError(
            "P4-P6 Phase22 store lineage drift"
        )
    system = _system_control_map(
        controls=system_controls,
        integrated_git_sha=integrated_git_sha,
        phase22_receipt=phase22_receipt,
    )

    phase20_plan_sha = phase20d_qualification_plan_sha256()
    phase22_plan_sha = phase22_holdout_qualification_plan_sha256()
    if phase22_receipt.phase22_plan_sha256 != phase22_plan_sha:
        raise CiboCapitalManagementError(
            "P4-P6 Phase22 plan digest drift"
        )

    specs: tuple[tuple[str, dict[str, str], dict[str, Any]], ...] = (
        (
            "P4_PROVIDER_RISK_CMA_FORWARD_TRUTH",
            {
                "e1_authority_control_sha256": system[
                    "E1_AUTHORITY"
                ].fingerprint(),
                "e2_capital_conservation_control_sha256": system[
                    "E2_CAPITAL_CONSERVATION"
                ].fingerprint(),
                "e3_realized_capital_control_sha256": system[
                    "E3_REALIZED_CAPITAL_LAW"
                ].fingerprint(),
                "e4_provider_truth_control_sha256": system[
                    "E4_PROVIDER_TRUTH"
                ].fingerprint(),
                "e5_risk_precedence_control_sha256": system[
                    "E5_RISK_PRECEDENCE"
                ].fingerprint(),
                "provider_economics_sha256": refs["provider_economics_sha256"],
                "executed_risk_store_sha256": refs["executed_risk_store_sha256"],
                "cma_settlement_store_sha256": refs["cma_settlement_store_sha256"],
                "t20_release_store_sha256": refs["t20_release_store_sha256"],
                "integrated_capital_truth_sha256": refs[
                    "integrated_capital_truth_sha256"
                ],
            },
            {
                "requested_authorized_executed_lineage_required": True,
                "provider_truth_required": True,
                "capital_truth_required": True,
                "fabricated_economics_allowed": False,
            },
        ),
        (
            "P5_PHASE20D_PASS",
            {
                "phase20d_qualification_plan_sha256": phase20_plan_sha,
                "phase22_qualification_plan_sha256": phase22_plan_sha,
                "phase22_qualification_artifact_sha256": (
                    phase22_receipt.qualification_artifact_sha256
                ),
                "as_is_baseline_sha256": refs["as_is_baseline_sha256"],
                "holdout_evidence_store_sha256": refs[
                    "holdout_evidence_store_sha256"
                ],
                "holdout_policy_store_sha256": refs["holdout_policy_store_sha256"],
            },
            {
                "phase20d_thresholds_reused_without_refit": True,
                "phase22_economic_holdout_passed": True,
                "baseline_population_bound": True,
            },
        ),
        (
            "P6_POLICY_CALIBRATION_FREEZE",
            {
                "pre_holdout_freeze_sha256": refs["pre_holdout_freeze_sha256"],
                "source_receipt_sha256": refs["source_receipt_sha256"],
                "trader_parity_manifest_sha256": refs[
                    "trader_parity_manifest_sha256"
                ],
                "phase21_manifest_sha256": phase22_receipt.phase21_manifest_sha256,
                "phase22_plan_sha256": phase22_plan_sha,
            },
            {
                "candidate_parameter_sha256": (
                    phase22_receipt.candidate_parameter_sha256
                ),
                "phase21_freeze_required": True,
                "calibration_freeze_required": True,
                "provider_core_freeze_required": True,
                "parity_7_of_7_required": True,
                "post_outcome_refit_allowed": False,
            },
        ),
    )

    result: list[CiboFinalExamControlReceipt] = []
    for receipt_id, source_refs, details in specs:
        artifact = _artifact_json(
            receipt_id=receipt_id,
            integrated_git_sha=integrated_git_sha,
            phase22_receipt=phase22_receipt,
            intake=intake,
            observed_at=observed_at,
            source_refs=source_refs,
            details=details,
        )
        result.append(
            bind_final_exam_control_artifact(
                receipt_id=receipt_id,
                evidence_kind=_EVIDENCE_KIND,
                source_artifact_json=artifact,
            )
        )
    return tuple(result)
