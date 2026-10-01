"""Receipt-bound CIBO World Cup Maximum-Capability Exam.

The World Cup exam is downstream of the ordinary Final Integrated CIBO Exam.
It never uses an aspirational return number as a pass threshold.  Instead it
requires source-bound evidence that the frozen competition protocol, provider
adapter, Digital Twin, control, causal attribution, path Monte Carlo, stress,
temporal replication and non-compensatory survival/productivity constraints all
passed on one exact integrated HEAD and one World Cup policy identity.

The gate grants no LIVE, execution, Risk, real-capital or merge authority.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import StrEnum

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_crossboundary_evidence_receipt import (
    CiboCrossBoundaryEvidenceReceipt,
    require_cross_boundary_receipts,
)
from qore.infrastructure.cibo_final_integrated_exam import (
    FinalIntegratedExamReport,
    FinalIntegratedExamStatus,
)

WORLD_CUP_MAXIMUM_CAPABILITY_EXAM_ID = (
    "CIBO_WORLD_CUP_MAXIMUM_CAPABILITY_EXAM_V1"
)

_REQUIRED_RECEIPT_FIELDS: dict[str, tuple[str, ...]] = {
    "WC01_FINAL_INTEGRATED_EXAM_PASS": (
        "final_integrated_exam_passed",
    ),
    "WC02_PROTOCOL_FREEZE": (
        "world_cup_protocol_frozen",
    ),
    "WC03_COMPETITION_PROVIDER_ADAPTER": (
        "competition_provider_bound",
        "provider_economics_complete",
    ),
    "WC04_WORLD_CUP_DIGITAL_TWIN": (
        "competition_digital_twin_bound",
        "capital_conservation_proven",
    ),
    "WC05_AS_IS_CONTROL": (
        "as_is_control_frozen",
    ),
    "WC06_AMPLIFICATION_CAUSAL_ATTRIBUTION": (
        "causal_attribution_complete",
    ),
    "WC07_PATH_DEPENDENT_MONTE_CARLO": (
        "path_structure_preserved",
    ),
    "WC08_ADVERSARIAL_STRESS": (
        "stress_noncompensatory_pass",
    ),
    "WC09_TEMPORAL_REPLICATION": (
        "four_fold_replication_pass",
    ),
    "WC10_SURVIVAL_CAPITAL_PRODUCTIVITY": (
        "survival_nonworse",
        "tail_nonworse",
        "plausible_loss_nonworse",
        "capital_productivity_improved",
    ),
}
_REQUIRED_RECEIPT_IDS = tuple(_REQUIRED_RECEIPT_FIELDS)

_GOVERNANCE_FALSE = (
    "synthetic_evidence_used",
    "outcome_aware_refit",
    "post_hoc_selection_used",
    "aspirational_return_target_used",
    "hidden_leverage_used",
    "protected_holdout_reused",
    "operational_authority_claimed",
)


class WorldCupMaximumCapabilityStatus(StrEnum):
    PASS = "PASS"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True, slots=True)
class WorldCupMaximumCapabilityReport:
    exam_id: str
    status: WorldCupMaximumCapabilityStatus
    integrated_head_sha: str
    world_cup_policy_identity_sha256: str
    evidence_sha256s: tuple[str, ...]
    blockers: tuple[str, ...]
    live_authorized: bool = False
    real_capital_authorized: bool = False
    merge_authorized: bool = False

    def __post_init__(self) -> None:
        if self.exam_id != WORLD_CUP_MAXIMUM_CAPABILITY_EXAM_ID:
            raise CiboCapitalManagementError(
                "World Cup maximum-capability exam identity drift"
            )
        if (
            self.live_authorized
            or self.real_capital_authorized
            or self.merge_authorized
        ):
            raise CiboCapitalManagementError(
                "World Cup exam cannot grant operational authority"
            )
        if (
            self.status is WorldCupMaximumCapabilityStatus.PASS
            and self.blockers
        ):
            raise CiboCapitalManagementError(
                "passing World Cup exam cannot retain blockers"
            )


def required_world_cup_receipt_ids() -> tuple[str, ...]:
    return _REQUIRED_RECEIPT_IDS


def assess_receipt_bound_world_cup_maximum_capability_exam(
    *,
    integrated_head_sha: str,
    world_cup_policy_identity_sha256: str,
    final_integrated_exam: FinalIntegratedExamReport,
    receipts: tuple[CiboCrossBoundaryEvidenceReceipt, ...],
    certification_critical_external_blockers: tuple[str, ...] = (),
) -> WorldCupMaximumCapabilityReport:
    """Run the frozen non-compensatory World Cup AND gate."""

    if not isinstance(final_integrated_exam, FinalIntegratedExamReport):
        raise CiboCapitalManagementError(
            "World Cup exam requires canonical Final Integrated Exam report"
        )
    if (
        final_integrated_exam.status is not FinalIntegratedExamStatus.PASS
        or final_integrated_exam.blockers
    ):
        raise CiboCapitalManagementError(
            "World Cup exam requires passed Final Integrated CIBO Exam"
        )
    if final_integrated_exam.integrated_head_sha != integrated_head_sha:
        raise CiboCapitalManagementError(
            "World Cup exam Final Integrated Exam HEAD drift"
        )
    if any(
        not isinstance(item, str) or not item
        for item in certification_critical_external_blockers
    ):
        raise CiboCapitalManagementError(
            "World Cup external blockers must be non-empty strings"
        )

    by_id = require_cross_boundary_receipts(
        receipts=receipts,
        required_receipt_ids=_REQUIRED_RECEIPT_IDS,
        integrated_git_sha=integrated_head_sha,
        policy_identity_sha256=world_cup_policy_identity_sha256,
    )

    blockers: list[str] = []
    evidence_sha256s: list[str] = []
    for receipt_id in _REQUIRED_RECEIPT_IDS:
        receipt = by_id[receipt_id]
        payload = json.loads(receipt.source_artifact_json)
        _assert_clean_governance(payload)
        evidence_sha256s.append(receipt.source_artifact_sha256)
        for field in _REQUIRED_RECEIPT_FIELDS[receipt_id]:
            if payload.get(field) is not True:
                blockers.append(f"{receipt_id}:{field}")

    if certification_critical_external_blockers:
        blockers.append("CERTIFICATION_CRITICAL_EXTERNAL_BLOCKER")

    blockers = list(dict.fromkeys(blockers))
    status = (
        WorldCupMaximumCapabilityStatus.PASS
        if not blockers
        else WorldCupMaximumCapabilityStatus.BLOCKED
    )
    return WorldCupMaximumCapabilityReport(
        exam_id=WORLD_CUP_MAXIMUM_CAPABILITY_EXAM_ID,
        status=status,
        integrated_head_sha=integrated_head_sha,
        world_cup_policy_identity_sha256=world_cup_policy_identity_sha256,
        evidence_sha256s=tuple(evidence_sha256s),
        blockers=tuple(blockers),
    )


def _assert_clean_governance(payload: dict[str, object]) -> None:
    missing = tuple(key for key in _GOVERNANCE_FALSE if key not in payload)
    if missing:
        raise CiboCapitalManagementError(
            "World Cup source artifact missing governance flags: "
            + ",".join(missing)
        )
    contaminated = tuple(
        key for key in _GOVERNANCE_FALSE if payload[key] is not False
    )
    if contaminated:
        raise CiboCapitalManagementError(
            "World Cup source artifact governance contamination: "
            + ",".join(contaminated)
        )
