"""Canonical receipt set for the CIBO USD60 pre-exam prerequisites.

This adapter replaces caller-supplied prerequisite booleans with seven
cross-boundary PASS receipts bound to one integrated HEAD and policy identity.
It does not open the holdout or grant exam, certification or productive
authority.
"""

from __future__ import annotations

import json

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_crossboundary_evidence_receipt import (
    CiboCrossBoundaryEvidenceReceipt,
    require_cross_boundary_receipts,
)

USD60_PRE_EXAM_RECEIPT_IDS = (
    "PROVIDER_ECONOMICS_AND_COST_FREEZE",
    "RISK_INTEGRATION_PROVEN",
    "INTEGRATED_CAPITAL_TRUTH_REAL_POPULATION_BOUND",
    "T01_T20_ENGINEERING_READINESS",
    "FRESH_OOS_PHASE21_VALIDATIONS",
    "PHASE21_POLICY_FREEZE_SEALED",
    "HOLDOUT_REGISTRY_SEALED_UNTOUCHED",
)


def required_usd60_pre_exam_receipt_ids() -> tuple[str, ...]:
    return USD60_PRE_EXAM_RECEIPT_IDS


def require_usd60_pre_exam_receipts(
    *,
    receipts: tuple[CiboCrossBoundaryEvidenceReceipt, ...],
    integrated_git_sha: str,
    policy_identity_sha256: str,
) -> dict[str, CiboCrossBoundaryEvidenceReceipt]:
    by_id = require_cross_boundary_receipts(
        receipts=receipts,
        required_receipt_ids=USD60_PRE_EXAM_RECEIPT_IDS,
        integrated_git_sha=integrated_git_sha,
        policy_identity_sha256=policy_identity_sha256,
    )
    for receipt_id, receipt in by_id.items():
        if receipt.evidence_kind != "USD60_PRE_EXAM_PREREQUISITE":
            raise CiboCapitalManagementError(
                f"USD60 receipt evidence kind invalid: {receipt_id}"
            )
        payload = json.loads(receipt.source_artifact_json)
        for key in (
            "synthetic_evidence_used",
            "holdout_mining_used",
            "outcome_aware_refit",
            "operational_authority_claimed",
        ):
            if key not in payload:
                raise CiboCapitalManagementError(
                    f"USD60 receipt source missing governance flag: {key}"
                )
            if payload[key] is not False:
                raise CiboCapitalManagementError(
                    f"USD60 receipt governance contamination: {key}"
                )
    return by_id
