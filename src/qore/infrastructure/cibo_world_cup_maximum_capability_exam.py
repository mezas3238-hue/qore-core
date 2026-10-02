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

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime
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
_WORLD_CUP_EVIDENCE_KIND = "WORLD_CUP_MAXIMUM_CAPABILITY_CONTROL"
_SHA1_RE = re.compile(r"^[0-9a-f]{40}$")
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")

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



def _canonical_sha256(payload: object) -> str:
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def world_cup_policy_identity_sha256() -> str:
    """Fingerprint the frozen non-compensatory World Cup protocol."""

    return _canonical_sha256(
        {
            "exam_id": WORLD_CUP_MAXIMUM_CAPABILITY_EXAM_ID,
            "required_receipt_fields": {
                key: list(value)
                for key, value in _REQUIRED_RECEIPT_FIELDS.items()
            },
            "governance_false": list(_GOVERNANCE_FALSE),
            "scoring": "NON_COMPENSATORY_AND",
            "aspirational_return_target_used": False,
        }
    )


def final_integrated_exam_report_sha256(
    report: FinalIntegratedExamReport,
) -> str:
    if not isinstance(report, FinalIntegratedExamReport):
        raise CiboCapitalManagementError(
            "World Cup report hash requires canonical Final Integrated report"
        )
    return _canonical_sha256(
        {
            "exam_id": report.exam_id,
            "status": report.status.value,
            "integrated_head_sha": report.integrated_head_sha,
            "blockers": list(report.blockers),
            "demo_execution_authorized": report.demo_execution_authorized,
            "live_authorized": report.live_authorized,
            "real_capital_authorized": report.real_capital_authorized,
            "merge_authorized": report.merge_authorized,
        }
    )


@dataclass(frozen=True, slots=True)
class WorldCupControlReceipt:
    receipt_id: str
    producer_gate_id: str
    integrated_git_sha: str
    world_cup_policy_identity_sha256: str
    final_integrated_exam_report_sha256: str
    source_artifact_schema: str
    source_artifact_sha256: str
    source_artifact_json: str
    observed_at: datetime
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if self.receipt_id not in _REQUIRED_RECEIPT_IDS:
            raise CiboCapitalManagementError(
                "World Cup control receipt identity drift"
            )
        if not self.producer_gate_id:
            raise CiboCapitalManagementError(
                "World Cup control producer gate required"
            )
        if _SHA1_RE.fullmatch(self.integrated_git_sha) is None:
            raise CiboCapitalManagementError(
                "World Cup control integrated HEAD invalid"
            )
        if (
            self.world_cup_policy_identity_sha256
            != world_cup_policy_identity_sha256()
        ):
            raise CiboCapitalManagementError(
                "World Cup control policy identity drift"
            )
        if _SHA256_RE.fullmatch(self.final_integrated_exam_report_sha256) is None:
            raise CiboCapitalManagementError(
                "World Cup control Final Integrated report digest invalid"
            )
        if _SHA256_RE.fullmatch(self.source_artifact_sha256) is None:
            raise CiboCapitalManagementError(
                "World Cup control source digest invalid"
            )
        if self.observed_at.tzinfo is None or self.observed_at.utcoffset() is None:
            raise CiboCapitalManagementError(
                "World Cup control observed_at must be timezone-aware"
            )
        if type(self.productive_authority) is not bool or self.productive_authority:
            raise CiboCapitalManagementError(
                "World Cup control cannot grant productive authority"
            )
        try:
            payload = json.loads(self.source_artifact_json)
        except json.JSONDecodeError as error:
            raise CiboCapitalManagementError(
                "World Cup control source artifact invalid JSON"
            ) from error
        if not isinstance(payload, dict):
            raise CiboCapitalManagementError(
                "World Cup control source artifact must be object"
            )
        expected = {
            "schema": self.source_artifact_schema,
            "evidence_binding_id": self.receipt_id,
            "evidence_kind": _WORLD_CUP_EVIDENCE_KIND,
            "producer_gate_id": self.producer_gate_id,
            "integrated_git_sha": self.integrated_git_sha,
            "world_cup_policy_identity_sha256": (
                self.world_cup_policy_identity_sha256
            ),
            "final_integrated_exam_report_sha256": (
                self.final_integrated_exam_report_sha256
            ),
            "observed_at": self.observed_at.isoformat(),
            "status": "PASS",
            "productive_authority": False,
        }
        for key, value in expected.items():
            if payload.get(key) != value:
                raise CiboCapitalManagementError(
                    f"World Cup control artifact field mismatch: {key}"
                )
        if payload.get("failures") != []:
            raise CiboCapitalManagementError(
                "World Cup control source artifact contains failures"
            )
        digest = "sha256:" + hashlib.sha256(
            self.source_artifact_json.encode("utf-8")
        ).hexdigest()
        if digest != self.source_artifact_sha256:
            raise CiboCapitalManagementError(
                "World Cup control source artifact digest mismatch"
            )

    def fingerprint(self) -> str:
        return _canonical_sha256(
            {
                "receipt_id": self.receipt_id,
                "producer_gate_id": self.producer_gate_id,
                "integrated_git_sha": self.integrated_git_sha,
                "world_cup_policy_identity_sha256": (
                    self.world_cup_policy_identity_sha256
                ),
                "final_integrated_exam_report_sha256": (
                    self.final_integrated_exam_report_sha256
                ),
                "source_artifact_sha256": self.source_artifact_sha256,
                "observed_at": self.observed_at.isoformat(),
                "productive_authority": self.productive_authority,
            }
        )


def bind_world_cup_control_artifact(
    *,
    receipt_id: str,
    source_artifact_json: str,
) -> WorldCupControlReceipt:
    try:
        payload = json.loads(source_artifact_json)
    except json.JSONDecodeError as error:
        raise CiboCapitalManagementError(
            "World Cup control source artifact invalid JSON"
        ) from error
    if not isinstance(payload, dict):
        raise CiboCapitalManagementError(
            "World Cup control source artifact must be object"
        )
    required = (
        "schema",
        "evidence_binding_id",
        "evidence_kind",
        "producer_gate_id",
        "integrated_git_sha",
        "world_cup_policy_identity_sha256",
        "final_integrated_exam_report_sha256",
        "observed_at",
        "status",
        "failures",
        "productive_authority",
    )
    missing = tuple(key for key in required if key not in payload)
    if missing:
        raise CiboCapitalManagementError(
            "World Cup control source artifact missing fields: "
            + ",".join(missing)
        )
    if payload["evidence_binding_id"] != receipt_id:
        raise CiboCapitalManagementError(
            "World Cup control binding identity drift"
        )
    if payload["evidence_kind"] != _WORLD_CUP_EVIDENCE_KIND:
        raise CiboCapitalManagementError(
            "World Cup control evidence kind drift"
        )
    if payload["status"] != "PASS" or payload["failures"] != []:
        raise CiboCapitalManagementError(
            "World Cup control source artifact is not PASS"
        )
    try:
        observed_at = datetime.fromisoformat(str(payload["observed_at"]))
    except ValueError as error:
        raise CiboCapitalManagementError(
            "World Cup control observed_at invalid"
        ) from error
    digest = "sha256:" + hashlib.sha256(
        source_artifact_json.encode("utf-8")
    ).hexdigest()
    return WorldCupControlReceipt(
        receipt_id=receipt_id,
        producer_gate_id=str(payload["producer_gate_id"]),
        integrated_git_sha=str(payload["integrated_git_sha"]),
        world_cup_policy_identity_sha256=str(
            payload["world_cup_policy_identity_sha256"]
        ),
        final_integrated_exam_report_sha256=str(
            payload["final_integrated_exam_report_sha256"]
        ),
        source_artifact_schema=str(payload["schema"]),
        source_artifact_sha256=digest,
        source_artifact_json=source_artifact_json,
        observed_at=observed_at,
        productive_authority=False,
    )


def _require_world_cup_control_receipts(
    *,
    receipts: tuple[WorldCupControlReceipt, ...],
    integrated_git_sha: str,
    final_report_sha256: str,
) -> dict[str, WorldCupControlReceipt]:
    if not isinstance(receipts, tuple) or any(
        not isinstance(item, WorldCupControlReceipt) for item in receipts
    ):
        raise CiboCapitalManagementError(
            "World Cup controls must be canonical tuple"
        )
    by_id: dict[str, WorldCupControlReceipt] = {}
    for receipt in receipts:
        if receipt.receipt_id in by_id:
            raise CiboCapitalManagementError(
                "World Cup duplicate receipt id"
            )
        if receipt.integrated_git_sha != integrated_git_sha:
            raise CiboCapitalManagementError(
                "World Cup receipt integrated-head drift"
            )
        if (
            receipt.world_cup_policy_identity_sha256
            != world_cup_policy_identity_sha256()
        ):
            raise CiboCapitalManagementError(
                "World Cup receipt policy-identity drift"
            )
        if receipt.final_integrated_exam_report_sha256 != final_report_sha256:
            raise CiboCapitalManagementError(
                "World Cup receipt Final Integrated report drift"
            )
        by_id[receipt.receipt_id] = receipt
    missing = tuple(item for item in _REQUIRED_RECEIPT_IDS if item not in by_id)
    extras = tuple(sorted(set(by_id) - set(_REQUIRED_RECEIPT_IDS)))
    if missing:
        raise CiboCapitalManagementError(
            "World Cup required receipts missing: " + ",".join(missing)
        )
    if extras:
        raise CiboCapitalManagementError(
            "World Cup unexpected receipt ids: " + ",".join(extras)
        )
    return by_id


class WorldCupMaximumCapabilityStatus(StrEnum):
    PASS = "PASS"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True, slots=True)
class WorldCupMaximumCapabilityReport:
    exam_id: str
    status: WorldCupMaximumCapabilityStatus
    integrated_head_sha: str
    world_cup_policy_identity_sha256: str
    final_integrated_exam_report_sha256: str
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
        if _SHA256_RE.fullmatch(self.final_integrated_exam_report_sha256) is None:
            raise CiboCapitalManagementError(
                "World Cup Final Integrated report lineage digest invalid"
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
    receipts: tuple[
        WorldCupControlReceipt | CiboCrossBoundaryEvidenceReceipt, ...
    ],
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

    final_report_sha = final_integrated_exam_report_sha256(
        final_integrated_exam
    )
    if receipts and all(
        isinstance(item, WorldCupControlReceipt) for item in receipts
    ):
        if world_cup_policy_identity_sha256 != globals()[
            "world_cup_policy_identity_sha256"
        ]():
            raise CiboCapitalManagementError(
                "World Cup canonical receipt policy identity drift"
            )
        by_id = _require_world_cup_control_receipts(
            receipts=tuple(
                item
                for item in receipts
                if isinstance(item, WorldCupControlReceipt)
            ),
            integrated_git_sha=integrated_head_sha,
            final_report_sha256=final_report_sha,
        )
    else:
        if any(
            not isinstance(item, CiboCrossBoundaryEvidenceReceipt)
            for item in receipts
        ):
            raise CiboCapitalManagementError(
                "World Cup receipt surface cannot mix receipt types"
            )
        by_id = require_cross_boundary_receipts(
            receipts=tuple(
                item
                for item in receipts
                if isinstance(item, CiboCrossBoundaryEvidenceReceipt)
            ),
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
        final_integrated_exam_report_sha256=final_report_sha,
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
