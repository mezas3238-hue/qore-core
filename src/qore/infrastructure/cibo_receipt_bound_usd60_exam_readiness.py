"""Receipt-bound USD60 pre-exam readiness.

The B readiness value object is retained, but its seven prerequisite PASS flags
are constructed only after canonical source-bound receipts have been verified
against the exact integrated HEAD and frozen policy identity.

This wrapper does not open the holdout and grants no productive authority.
"""

from __future__ import annotations

from qore.infrastructure.cibo_arch_b_forward_economic_manifest import (
    ArchBForwardEconomicManifest,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_crossboundary_evidence_receipt import (
    CiboCrossBoundaryEvidenceReceipt,
)
from qore.infrastructure.cibo_usd60_exam_readiness import (
    CiboUsd60PreExamReadiness,
    CiboUsd60PrerequisiteEvidence,
    assess_cibo_usd60_pre_exam_readiness,
)
from qore.infrastructure.cibo_usd60_prerequisite_receipts import (
    require_usd60_pre_exam_receipts,
    required_usd60_pre_exam_receipt_ids,
)


def assess_receipt_bound_usd60_pre_exam_readiness(
    *,
    forward_manifest: ArchBForwardEconomicManifest,
    receipts: tuple[CiboCrossBoundaryEvidenceReceipt, ...],
    integrated_git_sha: str,
    policy_identity_sha256: str,
) -> CiboUsd60PreExamReadiness:
    if not isinstance(forward_manifest, ArchBForwardEconomicManifest):
        raise CiboCapitalManagementError(
            "receipt-bound USD60 requires canonical forward manifest"
        )
    if forward_manifest.frozen_parameter_sha256 != policy_identity_sha256:
        raise CiboCapitalManagementError(
            "receipt-bound USD60 frozen policy identity drift"
        )

    by_id = require_usd60_pre_exam_receipts(
        receipts=receipts,
        integrated_git_sha=integrated_git_sha,
        policy_identity_sha256=policy_identity_sha256,
    )
    prerequisites = tuple(
        CiboUsd60PrerequisiteEvidence(
            prerequisite_id=receipt_id,
            passed=True,
            evidence_refs=(
                by_id[receipt_id].source_artifact_sha256,
                by_id[receipt_id].fingerprint(),
            ),
            observed_at=by_id[receipt_id].observed_at,
            holdout_outcomes_inspected=False,
        )
        for receipt_id in required_usd60_pre_exam_receipt_ids()
    )
    return assess_cibo_usd60_pre_exam_readiness(
        forward_manifest=forward_manifest,
        prerequisites=prerequisites,
    )
