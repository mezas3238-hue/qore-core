"""Derive Final Integrated Exam E1-E6/E10 from source-bound Phase22 truth."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import fields
from datetime import datetime
from typing import Any

from qore.infrastructure.account_wide_risk import RiskDecision
from qore.infrastructure.cibo_arch_a_internal_readiness import (
    ArchitectAPhase22V2CompoundClosureReceipt,
    ArchitectAPhase22V2MechanismEvidenceReceipt,
    ArchitectAPhase22V2ScientificIntakeReport,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
    TraderOpportunityEnvelope,
)
from qore.infrastructure.cibo_ce2i_final_certification import (
    Phase22QualificationReceipt,
)
from qore.infrastructure.cibo_final_exam_control_receipt import (
    CiboFinalExamControlReceipt,
    bind_final_exam_control_artifact,
)

_EVIDENCE_KIND = "FINAL_INTEGRATED_EXAM_CONTROL"
_SCHEMA = "qore.cibo.arch-a.final-system-control.v1"
_STRICT_TEMPORAL_KIND = "STRICT_TEMPORAL_POPULATION_LINEAGE"
_CAPITAL_TRUTH_BINDING_ID = (
    "CIBO_INTEGRATED_CAPITAL_FORWARD_POPULATION_BINDING_V1"
)
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_FORBIDDEN_TRADER_SIZING_FIELDS = (
    "volume",
    "lots",
    "risk_usd",
    "requested_risk_usd",
    "capital_allocation_usd",
)
_REQUIRED_ASSERTIONS = (
    "E1_AUTHORITY",
    "E2_CAPITAL_CONSERVATION",
    "E3_REALIZED_CAPITAL_LAW",
    "E4_PROVIDER_TRUTH",
    "E5_RISK_PRECEDENCE",
    "E6_CHRONOLOGY_NO_LEAKAGE",
    "E10_DETERMINISTIC_REPLAY",
)


def authority_boundary_contract_sha256() -> str:
    trader_fields = tuple(item.name for item in fields(TraderOpportunityEnvelope))
    forbidden_present = tuple(
        item for item in _FORBIDDEN_TRADER_SIZING_FIELDS if item in trader_fields
    )
    if forbidden_present:
        raise CiboCapitalManagementError(
            "A final authority contract detected Trader sizing fields: "
            + ",".join(forbidden_present)
        )
    risk_decisions = tuple(item.value for item in RiskDecision)
    if risk_decisions != ("ALLOW", "REDUCE", "REJECT"):
        raise CiboCapitalManagementError(
            "A final authority contract Risk decision surface drift"
        )
    payload = {
        "schema": "qore.cibo.authority-boundary-contract.v1",
        "trader_owns": "METHODOLOGY_ENTRY_EXIT_GEOMETRY",
        "trader_sizing_fields_forbidden": list(_FORBIDDEN_TRADER_SIZING_FIELDS),
        "trader_envelope_fields": list(trader_fields),
        "cibo_owns": "ACCOUNT_SCOPED_CAPITAL_AND_SIZING",
        "risk_owns": list(risk_decisions),
        "execution_owns": "BROKER_MUTATION",
        "cibo_cannot_waive_risk": True,
        "trader_cannot_size": True,
    }
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _intake_refs(
    intake: ArchitectAPhase22V2ScientificIntakeReport,
) -> dict[str, str]:
    refs = dict(intake.receipt_refs)
    if len(refs) != len(intake.receipt_refs):
        raise CiboCapitalManagementError(
            "A final system controls duplicate Phase22 receipt kind"
        )
    return refs


def _mechanism_ref(
    mechanism: ArchitectAPhase22V2MechanismEvidenceReceipt,
    kind: str,
) -> str:
    refs = dict(mechanism.evidence_refs)
    value = refs.get(kind)
    if value is None:
        raise CiboCapitalManagementError(
            f"A final system controls missing mechanism evidence: {kind}"
        )
    return value



def _validate_capital_truth_artifact(
    *,
    artifact_json: str,
    expected_sha256: str,
) -> dict[str, Any]:
    actual_sha256 = "sha256:" + hashlib.sha256(
        artifact_json.encode("utf-8")
    ).hexdigest()
    if actual_sha256 != expected_sha256:
        raise CiboCapitalManagementError(
            "A final system controls Integrated Capital Truth digest drift"
        )
    try:
        payload = json.loads(artifact_json)
    except json.JSONDecodeError as error:
        raise CiboCapitalManagementError(
            "A final system controls Integrated Capital Truth invalid JSON"
        ) from error
    if not isinstance(payload, dict):
        raise CiboCapitalManagementError(
            "A final system controls Integrated Capital Truth must be object"
        )
    if payload.get("binding_id") != _CAPITAL_TRUTH_BINDING_ID:
        raise CiboCapitalManagementError(
            "A final system controls Integrated Capital Truth identity drift"
        )
    for field in (
        "manifest_scientifically_ready",
        "account_scope_match",
        "settlement_population_exact",
        "positive_profit_reconciliation_match",
        "integrated_capital_truth_pass",
        "ready_for_scientific_consumption",
    ):
        if payload.get(field) is not True:
            raise CiboCapitalManagementError(
                "A final system controls Integrated Capital Truth gate failed: "
                + field
            )
    if payload.get("blockers") not in ([], ()):
        raise CiboCapitalManagementError(
            "A final system controls Integrated Capital Truth retains blockers"
        )
    for field in ("source_ledger_sha256", "compound_cycle_state_sha256"):
        value = payload.get(field)
        if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
            raise CiboCapitalManagementError(
                "A final system controls Integrated Capital Truth missing ref: "
                + field
            )
    for field in (
        "runtime_authority",
        "sizing_authority",
        "risk_authority",
        "execution_authority",
    ):
        if payload.get(field) is not False:
            raise CiboCapitalManagementError(
                "A final system controls Integrated Capital Truth authority drift: "
                + field
            )
    return payload


def _artifact_json(
    *,
    assertion_id: str,
    integrated_git_sha: str,
    phase22_receipt: Phase22QualificationReceipt,
    intake: ArchitectAPhase22V2ScientificIntakeReport,
    observed_at: datetime,
    source_refs: dict[str, str],
    details: dict[str, Any],
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
        "source_refs": source_refs,
        "details": details,
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def build_architect_a_final_exam_system_controls(
    *,
    integrated_git_sha: str,
    phase22_receipt: Phase22QualificationReceipt,
    intake: ArchitectAPhase22V2ScientificIntakeReport,
    mechanism: ArchitectAPhase22V2MechanismEvidenceReceipt,
    compound_closure: ArchitectAPhase22V2CompoundClosureReceipt,
    integrated_capital_truth_artifact_json: str,
    observed_at: datetime,
) -> tuple[CiboFinalExamControlReceipt, ...]:
    if not isinstance(phase22_receipt, Phase22QualificationReceipt):
        raise CiboCapitalManagementError(
            "A final system controls require canonical Phase22 receipt"
        )
    if not isinstance(intake, ArchitectAPhase22V2ScientificIntakeReport):
        raise CiboCapitalManagementError(
            "A final system controls require canonical Phase22 intake"
        )
    if not isinstance(
        mechanism,
        ArchitectAPhase22V2MechanismEvidenceReceipt,
    ):
        raise CiboCapitalManagementError(
            "A final system controls require canonical mechanism evidence"
        )
    if not isinstance(
        compound_closure,
        ArchitectAPhase22V2CompoundClosureReceipt,
    ):
        raise CiboCapitalManagementError(
            "A final system controls require canonical Compound closure"
        )
    if intake.qualification_status != "PASS":
        raise CiboCapitalManagementError(
            "A final system controls require Phase22 PASS intake"
        )
    if not intake.ready_for_scientific_reentry or intake.blockers:
        raise CiboCapitalManagementError(
            "A final system controls require admissible Phase22 intake"
        )
    if mechanism.phase22_manifest_sha256 != intake.manifest_sha256:
        raise CiboCapitalManagementError(
            "A final system controls mechanism manifest drift"
        )
    if compound_closure.phase22_manifest_sha256 != intake.manifest_sha256:
        raise CiboCapitalManagementError(
            "A final system controls Compound manifest drift"
        )
    if (
        not compound_closure.compound_closure_terminal
        or compound_closure.blockers
        or compound_closure.missing_or_nonproven_ids
    ):
        raise CiboCapitalManagementError(
            "A final system controls require proven Compound closure"
        )
    if observed_at.tzinfo is None or observed_at.utcoffset() is None:
        raise CiboCapitalManagementError(
            "A final system controls observed_at must be timezone-aware"
        )
    if observed_at <= phase22_receipt.qualified_at:
        raise CiboCapitalManagementError(
            "A final system controls must be post-Phase22 qualification"
        )

    refs = _intake_refs(intake)
    if (
        refs["qualification_report_sha256"]
        != phase22_receipt.qualification_artifact_sha256
    ):
        raise CiboCapitalManagementError(
            "A final system controls qualification artifact drift"
        )
    if (
        refs["holdout_evidence_store_sha256"]
        != phase22_receipt.holdout_evidence_store_sha256
        or refs["holdout_policy_store_sha256"]
        != phase22_receipt.holdout_policy_store_sha256
    ):
        raise CiboCapitalManagementError(
            "A final system controls Phase22 store lineage drift"
        )

    capital_truth = _validate_capital_truth_artifact(
        artifact_json=integrated_capital_truth_artifact_json,
        expected_sha256=refs["integrated_capital_truth_sha256"],
    )
    strict_temporal_sha = _mechanism_ref(mechanism, _STRICT_TEMPORAL_KIND)
    authority_sha = authority_boundary_contract_sha256()
    risk_decisions = tuple(item.value for item in RiskDecision)
    specs: tuple[tuple[str, dict[str, str], dict[str, Any]], ...] = (
        (
            "E1_AUTHORITY",
            {
                "authority_contract_sha256": authority_sha,
                "execution_manifest_sha256": refs["execution_manifest_sha256"],
                "executed_risk_store_sha256": refs["executed_risk_store_sha256"],
                "cma_settlement_store_sha256": refs["cma_settlement_store_sha256"],
            },
            {
                "trader_volume_free": True,
                "cibo_owns_sizing": True,
                "risk_decisions": list(risk_decisions),
                "execution_owns_broker_mutation": True,
            },
        ),
        (
            "E2_CAPITAL_CONSERVATION",
            {
                "integrated_capital_truth_sha256": refs[
                    "integrated_capital_truth_sha256"
                ],
                "cma_settlement_store_sha256": refs["cma_settlement_store_sha256"],
                "t20_release_store_sha256": refs["t20_release_store_sha256"],
                "compound_closure_sha256": compound_closure.fingerprint(),
                "source_ledger_sha256": capital_truth["source_ledger_sha256"],
                "compound_cycle_state_sha256": capital_truth[
                    "compound_cycle_state_sha256"
                ],
            },
            {
                "settlement_population_exact": capital_truth[
                    "settlement_population_exact"
                ],
                "positive_profit_reconciliation_match": capital_truth[
                    "positive_profit_reconciliation_match"
                ],
                "integrated_capital_truth_pass": capital_truth[
                    "integrated_capital_truth_pass"
                ],
                "accounting_residual_required": "0",
                "double_spend_allowed": False,
                "phantom_capital_allowed": False,
            },
        ),
        (
            "E3_REALIZED_CAPITAL_LAW",
            {
                "integrated_capital_truth_sha256": refs[
                    "integrated_capital_truth_sha256"
                ],
                "cma_settlement_store_sha256": refs["cma_settlement_store_sha256"],
                "t20_release_store_sha256": refs["t20_release_store_sha256"],
                "source_ledger_sha256": capital_truth["source_ledger_sha256"],
                "compound_cycle_state_sha256": capital_truth[
                    "compound_cycle_state_sha256"
                ],
            },
            {
                "settlement_population_exact": capital_truth[
                    "settlement_population_exact"
                ],
                "integrated_capital_truth_pass": capital_truth[
                    "integrated_capital_truth_pass"
                ],
                "floating_pnl_is_cash": False,
                "loss_recovery_sizing_allowed": False,
                "release_before_reuse_required": True,
            },
        ),
        (
            "E4_PROVIDER_TRUTH",
            {
                "provider_economics_sha256": refs["provider_economics_sha256"],
                "source_receipt_sha256": refs["source_receipt_sha256"],
            },
            {
                "synthetic_provider_economics_allowed": False,
                "provider_bound_execution_required": True,
            },
        ),
        (
            "E5_RISK_PRECEDENCE",
            {
                "executed_risk_store_sha256": refs["executed_risk_store_sha256"],
                "execution_manifest_sha256": refs["execution_manifest_sha256"],
            },
            {
                "risk_decisions": list(risk_decisions),
                "cibo_can_waive_reject": False,
                "executed_exposure_must_be_risk_authorized": True,
            },
        ),
        (
            "E6_CHRONOLOGY_NO_LEAKAGE",
            {
                "holdout_evidence_store_sha256": refs[
                    "holdout_evidence_store_sha256"
                ],
                "holdout_policy_store_sha256": refs["holdout_policy_store_sha256"],
                "execution_manifest_sha256": refs["execution_manifest_sha256"],
                "strict_temporal_population_sha256": strict_temporal_sha,
            },
            {
                "future_leakage_allowed": False,
                "outcome_selected_configuration_allowed": False,
                "decision_before_outcome_required": True,
            },
        ),
        (
            "E10_DETERMINISTIC_REPLAY",
            {
                "source_receipt_sha256": refs["source_receipt_sha256"],
                "trader_parity_manifest_sha256": refs[
                    "trader_parity_manifest_sha256"
                ],
                "execution_manifest_sha256": refs["execution_manifest_sha256"],
                "holdout_evidence_store_sha256": refs[
                    "holdout_evidence_store_sha256"
                ],
                "holdout_policy_store_sha256": refs["holdout_policy_store_sha256"],
                "qualification_report_sha256": refs[
                    "qualification_report_sha256"
                ],
                "strict_temporal_population_sha256": strict_temporal_sha,
            },
            {
                "immutable_identity_chain_required": True,
                "replay_same_verdict_required": True,
                "post_hoc_mutation_allowed": False,
            },
        ),
    )

    receipts: list[CiboFinalExamControlReceipt] = []
    for assertion_id, source_refs, details in specs:
        artifact = _artifact_json(
            assertion_id=assertion_id,
            integrated_git_sha=integrated_git_sha,
            phase22_receipt=phase22_receipt,
            intake=intake,
            observed_at=observed_at,
            source_refs=source_refs,
            details=details,
        )
        receipts.append(
            bind_final_exam_control_artifact(
                receipt_id=assertion_id,
                evidence_kind=_EVIDENCE_KIND,
                source_artifact_json=artifact,
            )
        )
    if tuple(item.receipt_id for item in receipts) != _REQUIRED_ASSERTIONS:
        raise CiboCapitalManagementError(
            "A final system controls assertion surface drift"
        )
    return tuple(receipts)
