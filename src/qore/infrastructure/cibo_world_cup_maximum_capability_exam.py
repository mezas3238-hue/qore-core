"""Receipt-bound CIBO World Cup Maximum-Capability Exam.

This gate is downstream of a passed Final Integrated CIBO Exam. Ten canonical
control artifacts must bind to one exact integrated HEAD, one frozen World Cup
policy identity and the deterministic digest of that Final Integrated report.
No aspirational return number is a pass threshold and no operational authority
is granted.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_final_integrated_exam import (
    FinalIntegratedExamReport,
    FinalIntegratedExamStatus,
)

WORLD_CUP_MAXIMUM_CAPABILITY_EXAM_ID = (
    "CIBO_WORLD_CUP_MAXIMUM_CAPABILITY_EXAM_V1"
)
WORLD_CUP_POLICY_ID = "CIBO_WORLD_CUP_MAXIMUM_CAPABILITY_POLICY_V1"
_EVIDENCE_KIND = "WORLD_CUP_MAXIMUM_CAPABILITY_CONTROL"
_STAGE = "POST_FINAL_INTEGRATED"
_SHA1_RE = re.compile(r"^[0-9a-f]{40}$")
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")

_REQUIRED_FIELDS: dict[str, tuple[str, ...]] = {
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
_REQUIRED_IDS = tuple(_REQUIRED_FIELDS)
_GOVERNANCE_FALSE = (
    "synthetic_evidence_used",
    "outcome_aware_refit",
    "post_hoc_selection_used",
    "aspirational_return_target_used",
    "hidden_leverage_used",
    "protected_holdout_reused",
    "operational_authority_claimed",
)


def _canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def world_cup_policy_identity_sha256() -> str:
    payload = {
        "policy_id": WORLD_CUP_POLICY_ID,
        "required_receipt_ids": list(_REQUIRED_IDS),
        "required_fields": {
            key: list(value) for key, value in _REQUIRED_FIELDS.items()
        },
        "governance_false": list(_GOVERNANCE_FALSE),
        "noncompensatory": True,
        "aspirational_return_threshold_allowed": False,
        "final_integrated_pass_required": True,
    }
    raw = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def final_integrated_exam_report_sha256(
    report: FinalIntegratedExamReport,
) -> str:
    if not isinstance(report, FinalIntegratedExamReport):
        raise CiboCapitalManagementError(
            "World Cup requires canonical Final Integrated Exam report"
        )
    payload = asdict(report)
    payload["status"] = report.status.value
    raw = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


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
        if self.receipt_id not in _REQUIRED_IDS or not self.producer_gate_id:
            raise CiboCapitalManagementError(
                "World Cup receipt identity is invalid"
            )
        if _SHA1_RE.fullmatch(self.integrated_git_sha) is None:
            raise CiboCapitalManagementError(
                "World Cup receipt integrated HEAD invalid"
            )
        if (
            self.world_cup_policy_identity_sha256
            != world_cup_policy_identity_sha256()
        ):
            raise CiboCapitalManagementError(
                "World Cup receipt policy identity drift"
            )
        for name in (
            "final_integrated_exam_report_sha256",
            "source_artifact_sha256",
        ):
            if _SHA256_RE.fullmatch(getattr(self, name)) is None:
                raise CiboCapitalManagementError(
                    f"World Cup receipt {name} invalid"
                )
        if (
            self.observed_at.tzinfo is None
            or self.observed_at.utcoffset() is None
        ):
            raise CiboCapitalManagementError(
                "World Cup receipt observed_at must be timezone-aware"
            )
        if type(self.productive_authority) is not bool or self.productive_authority:
            raise CiboCapitalManagementError(
                "World Cup receipt grants no productive authority"
            )
        try:
            artifact = json.loads(self.source_artifact_json)
        except json.JSONDecodeError as error:
            raise CiboCapitalManagementError(
                "World Cup source artifact invalid JSON"
            ) from error
        if not isinstance(artifact, dict) or _canonical_json(artifact) != self.source_artifact_json:
            raise CiboCapitalManagementError(
                "World Cup source artifact must be canonical object JSON"
            )
        digest = "sha256:" + hashlib.sha256(
            self.source_artifact_json.encode("utf-8")
        ).hexdigest()
        if digest != self.source_artifact_sha256:
            raise CiboCapitalManagementError(
                "World Cup source artifact digest mismatch"
            )
        expected = {
            "schema": self.source_artifact_schema,
            "evidence_binding_id": self.receipt_id,
            "evidence_kind": _EVIDENCE_KIND,
            "producer_gate_id": self.producer_gate_id,
            "integrated_git_sha": self.integrated_git_sha,
            "world_cup_policy_identity_sha256": self.world_cup_policy_identity_sha256,
            "final_integrated_exam_report_sha256": self.final_integrated_exam_report_sha256,
            "certification_stage": _STAGE,
            "observed_at": self.observed_at.isoformat(),
            "status": "PASS",
            "failures": [],
            "productive_authority": False,
        }
        for key, value in expected.items():
            if artifact.get(key) != value:
                raise CiboCapitalManagementError(
                    f"World Cup source artifact field mismatch: {key}"
                )
        _assert_clean_governance(artifact)


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
            raise CiboCapitalManagementError("World Cup exam identity drift")
        if self.world_cup_policy_identity_sha256 != world_cup_policy_identity_sha256():
            raise CiboCapitalManagementError("World Cup exam policy drift")
        if self.live_authorized or self.real_capital_authorized or self.merge_authorized:
            raise CiboCapitalManagementError(
                "World Cup exam cannot grant operational authority"
            )
        if self.status is WorldCupMaximumCapabilityStatus.PASS and self.blockers:
            raise CiboCapitalManagementError(
                "passing World Cup exam cannot retain blockers"
            )


def required_world_cup_receipt_ids() -> tuple[str, ...]:
    return _REQUIRED_IDS


def bind_world_cup_control_artifact(
    *,
    receipt_id: str,
    source_artifact_json: str,
) -> WorldCupControlReceipt:
    try:
        payload = json.loads(source_artifact_json)
    except json.JSONDecodeError as error:
        raise CiboCapitalManagementError(
            "World Cup source artifact invalid JSON"
        ) from error
    if not isinstance(payload, dict) or _canonical_json(payload) != source_artifact_json:
        raise CiboCapitalManagementError(
            "World Cup source artifact must use canonical JSON"
        )
    if payload.get("evidence_binding_id") != receipt_id:
        raise CiboCapitalManagementError(
            "World Cup source artifact binding identity drift"
        )
    if payload.get("evidence_kind") != _EVIDENCE_KIND:
        raise CiboCapitalManagementError(
            "World Cup source artifact evidence kind drift"
        )
    if payload.get("status") != "PASS" or payload.get("failures") != []:
        raise CiboCapitalManagementError(
            "World Cup source artifact is not PASS"
        )
    _assert_clean_governance(payload)
    try:
        observed_at = datetime.fromisoformat(str(payload["observed_at"]))
    except (KeyError, ValueError) as error:
        raise CiboCapitalManagementError(
            "World Cup source artifact observed_at invalid"
        ) from error
    digest = "sha256:" + hashlib.sha256(
        source_artifact_json.encode("utf-8")
    ).hexdigest()
    return WorldCupControlReceipt(
        receipt_id=receipt_id,
        producer_gate_id=str(payload.get("producer_gate_id", "")),
        integrated_git_sha=str(payload.get("integrated_git_sha", "")),
        world_cup_policy_identity_sha256=str(
            payload.get("world_cup_policy_identity_sha256", "")
        ),
        final_integrated_exam_report_sha256=str(
            payload.get("final_integrated_exam_report_sha256", "")
        ),
        source_artifact_schema=str(payload.get("schema", "")),
        source_artifact_sha256=digest,
        source_artifact_json=source_artifact_json,
        observed_at=observed_at,
        productive_authority=False,
    )


def assess_receipt_bound_world_cup_maximum_capability_exam(
    *,
    integrated_head_sha: str,
    final_integrated_exam: FinalIntegratedExamReport,
    receipts: tuple[WorldCupControlReceipt, ...],
    certification_critical_external_blockers: tuple[str, ...] = (),
) -> WorldCupMaximumCapabilityReport:
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
            "World Cup Final Integrated Exam HEAD drift"
        )
    if _SHA1_RE.fullmatch(integrated_head_sha) is None:
        raise CiboCapitalManagementError("World Cup integrated HEAD invalid")
    if any(
        not isinstance(item, str) or not item
        for item in certification_critical_external_blockers
    ):
        raise CiboCapitalManagementError(
            "World Cup external blockers must be non-empty strings"
        )
    if not isinstance(receipts, tuple) or any(
        not isinstance(item, WorldCupControlReceipt) for item in receipts
    ):
        raise CiboCapitalManagementError(
            "World Cup receipts must be canonical tuple"
        )
    by_id: dict[str, WorldCupControlReceipt] = {}
    final_sha = final_integrated_exam_report_sha256(final_integrated_exam)
    policy_sha = world_cup_policy_identity_sha256()
    for receipt in receipts:
        if receipt.receipt_id in by_id:
            raise CiboCapitalManagementError("World Cup duplicate receipt id")
        if receipt.integrated_git_sha != integrated_head_sha:
            raise CiboCapitalManagementError("World Cup receipt HEAD drift")
        if receipt.world_cup_policy_identity_sha256 != policy_sha:
            raise CiboCapitalManagementError("World Cup receipt policy drift")
        if receipt.final_integrated_exam_report_sha256 != final_sha:
            raise CiboCapitalManagementError(
                "World Cup receipt Final Integrated report drift"
            )
        by_id[receipt.receipt_id] = receipt
    missing = tuple(item for item in _REQUIRED_IDS if item not in by_id)
    extras = tuple(sorted(set(by_id) - set(_REQUIRED_IDS)))
    if missing:
        raise CiboCapitalManagementError(
            "World Cup required receipts missing: " + ",".join(missing)
        )
    if extras:
        raise CiboCapitalManagementError(
            "World Cup unexpected receipt ids: " + ",".join(extras)
        )

    blockers: list[str] = []
    evidence: list[str] = []
    for receipt_id in _REQUIRED_IDS:
        receipt = by_id[receipt_id]
        payload = json.loads(receipt.source_artifact_json)
        evidence.append(receipt.source_artifact_sha256)
        for field in _REQUIRED_FIELDS[receipt_id]:
            if payload.get(field) is not True:
                blockers.append(f"{receipt_id}:{field}")
    if certification_critical_external_blockers:
        blockers.append("CERTIFICATION_CRITICAL_EXTERNAL_BLOCKER")
    blockers = list(dict.fromkeys(blockers))
    return WorldCupMaximumCapabilityReport(
        exam_id=WORLD_CUP_MAXIMUM_CAPABILITY_EXAM_ID,
        status=(
            WorldCupMaximumCapabilityStatus.PASS
            if not blockers
            else WorldCupMaximumCapabilityStatus.BLOCKED
        ),
        integrated_head_sha=integrated_head_sha,
        world_cup_policy_identity_sha256=policy_sha,
        final_integrated_exam_report_sha256=final_sha,
        evidence_sha256s=tuple(evidence),
        blockers=tuple(blockers),
    )


def _assert_clean_governance(payload: dict[str, Any]) -> None:
    missing = tuple(key for key in _GOVERNANCE_FALSE if key not in payload)
    if missing:
        raise CiboCapitalManagementError(
            "World Cup source artifact missing governance flags: "
            + ",".join(missing)
        )
    contaminated = tuple(
        key for key in _GOVERNANCE_FALSE if payload.get(key) is not False
    )
    if contaminated:
        raise CiboCapitalManagementError(
            "World Cup source artifact governance contamination: "
            + ",".join(contaminated)
        )
