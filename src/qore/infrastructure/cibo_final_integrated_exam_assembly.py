"""Canonical 18-receipt assembly for the CIBO Final Integrated Exam."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_final_certification import (
    Phase22QualificationReceipt,
)
from qore.infrastructure.cibo_ce2i_phase21_policy_freeze import (
    Phase21PolicyFreezeManifest,
)
from qore.infrastructure.cibo_final_exam_control_receipt import (
    CiboFinalExamControlReceipt,
)
from qore.infrastructure.cibo_final_integrated_exam import (
    FinalIntegratedExamReport,
)
from qore.infrastructure.cibo_receipt_bound_final_integrated_exam_v2 import (
    assess_receipt_bound_final_integrated_exam_v2,
    expected_final_exam_control_producer_gate_id,
    required_final_exam_control_ids,
)
from qore.infrastructure.cibo_scientific_closure_41 import (
    validate_certifiable_holdout_id,
)

_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_CLOSURE41_RECEIPT_IDS = (
    "P7_SCIENTIFIC_CLOSURE",
    "P8_COMPOUND_CLOSURE",
    "E7_ECONOMIC_NONCOMPENSATION",
    "E8_STRESS_INTEGRITY",
    "E9_TEMPORAL_REPLICATION",
)


def _parse_receipt_artifact(
    receipt: CiboFinalExamControlReceipt,
) -> dict[str, object]:
    try:
        payload = json.loads(receipt.source_artifact_json)
    except json.JSONDecodeError as error:
        raise CiboCapitalManagementError(
            "final integrated package Closure41 artifact JSON invalid"
        ) from error
    if not isinstance(payload, dict):
        raise CiboCapitalManagementError(
            "final integrated package Closure41 artifact must be object"
        )
    return payload


def _require_artifact_sha256(
    payload: dict[str, object],
    key: str,
) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
        raise CiboCapitalManagementError(
            "final integrated package Closure41 lineage field invalid: " + key
        )
    return value


def _validate_closure41_receipt_lineage(
    receipts: tuple[CiboFinalExamControlReceipt, ...],
) -> None:
    by_id = {item.receipt_id: item for item in receipts}
    artifacts = {
        receipt_id: _parse_receipt_artifact(by_id[receipt_id])
        for receipt_id in _CLOSURE41_RECEIPT_IDS
    }
    manifests = {
        _require_artifact_sha256(
            artifacts[receipt_id],
            "phase22_handoff_manifest_sha256",
        )
        for receipt_id in _CLOSURE41_RECEIPT_IDS
    }
    if len(manifests) != 1:
        raise CiboCapitalManagementError(
            "final integrated package Closure41 manifest lineage drift"
        )

    p7 = artifacts["P7_SCIENTIFIC_CLOSURE"]
    p8 = artifacts["P8_COMPOUND_CLOSURE"]
    closure_batch = _require_artifact_sha256(p7, "closure_batch_sha256")
    if _require_artifact_sha256(p8, "closure_batch_sha256") != closure_batch:
        raise CiboCapitalManagementError(
            "final integrated package P7/P8 closure batch drift"
        )
    for receipt_id in (
        "E7_ECONOMIC_NONCOMPENSATION",
        "E8_STRESS_INTEGRITY",
        "E9_TEMPORAL_REPLICATION",
    ):
        if (
            _require_artifact_sha256(
                artifacts[receipt_id],
                "scientific_closure_41_sha256",
            )
            != closure_batch
        ):
            raise CiboCapitalManagementError(
                "final integrated package scientific assertion/Closure41 drift: "
                + receipt_id
            )

    p7_details = p7.get("details")
    p8_details = p8.get("details")
    if not isinstance(p7_details, dict) or not isinstance(p8_details, dict):
        raise CiboCapitalManagementError(
            "final integrated package P7/P8 holdout binding missing"
        )
    p7_holdout = p7_details.get("holdout_id")
    p8_holdout = p8_details.get("holdout_id")
    if not isinstance(p7_holdout, str):
        raise CiboCapitalManagementError(
            "final integrated package P7 holdout binding invalid"
        )
    validate_certifiable_holdout_id(
        p7_holdout,
        "Final Integrated Exam Closure41 holdout",
    )
    if p8_holdout != p7_holdout:
        raise CiboCapitalManagementError(
            "final integrated package P7/P8 holdout lineage drift"
        )



@dataclass(frozen=True, slots=True)
class FinalIntegratedControlPackage:
    integrated_git_sha: str
    receipts: tuple[CiboFinalExamControlReceipt, ...]
    certification_claimed: bool = False
    production_authority: bool = False

    def __post_init__(self) -> None:
        required = required_final_exam_control_ids()
        if (
            not isinstance(self.receipts, tuple)
            or any(
                not isinstance(item, CiboFinalExamControlReceipt)
                for item in self.receipts
            )
        ):
            raise CiboCapitalManagementError(
                "final integrated package requires canonical receipts"
            )
        ids = tuple(item.receipt_id for item in self.receipts)
        if ids != required:
            raise CiboCapitalManagementError(
                "final integrated package requires exact ordered 18 receipts"
            )
        if len(ids) != len(set(ids)):
            raise CiboCapitalManagementError(
                "final integrated package contains duplicate receipt"
            )
        for item in self.receipts:
            expected_producer = expected_final_exam_control_producer_gate_id(
                item.receipt_id
            )
            if item.producer_gate_id != expected_producer:
                raise CiboCapitalManagementError(
                    "final integrated package producer-gate drift: "
                    + item.receipt_id
                )
        _validate_closure41_receipt_lineage(self.receipts)
        if any(
            item.integrated_git_sha != self.integrated_git_sha
            for item in self.receipts
        ):
            raise CiboCapitalManagementError(
                "final integrated package cross-HEAD receipt"
            )
        policy_ids = {item.policy_identity_sha256 for item in self.receipts}
        phase22_ids = {
            item.phase22_qualification_artifact_sha256
            for item in self.receipts
        }
        if len(policy_ids) != 1 or len(phase22_ids) != 1:
            raise CiboCapitalManagementError(
                "final integrated package policy/Phase22 lineage drift"
            )
        if self.certification_claimed or self.production_authority:
            raise CiboCapitalManagementError(
                "final integrated package cannot grant authority"
            )

    @property
    def policy_identity_sha256(self) -> str:
        return self.receipts[0].policy_identity_sha256

    @property
    def phase22_qualification_artifact_sha256(self) -> str:
        return self.receipts[0].phase22_qualification_artifact_sha256

    def fingerprint(self) -> str:
        payload = {
            "integrated_git_sha": self.integrated_git_sha,
            "receipt_fingerprints": [
                item.fingerprint() for item in self.receipts
            ],
            "certification_claimed": self.certification_claimed,
            "production_authority": self.production_authority,
        }
        raw = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
        return "sha256:" + hashlib.sha256(raw).hexdigest()


def assemble_final_integrated_control_package(
    *,
    integrated_git_sha: str,
    receipts: tuple[CiboFinalExamControlReceipt, ...],
) -> FinalIntegratedControlPackage:
    by_id: dict[str, CiboFinalExamControlReceipt] = {}
    for receipt in receipts:
        if not isinstance(receipt, CiboFinalExamControlReceipt):
            raise CiboCapitalManagementError(
                "final integrated assembly requires canonical receipts"
            )
        if receipt.receipt_id in by_id:
            raise CiboCapitalManagementError(
                "final integrated assembly duplicate receipt id"
            )
        by_id[receipt.receipt_id] = receipt

    required = required_final_exam_control_ids()
    missing = tuple(item for item in required if item not in by_id)
    extras = tuple(sorted(set(by_id) - set(required)))
    if missing:
        raise CiboCapitalManagementError(
            "final integrated assembly missing receipts: " + ",".join(missing)
        )
    if extras:
        raise CiboCapitalManagementError(
            "final integrated assembly unexpected receipts: " + ",".join(extras)
        )
    ordered = tuple(by_id[item] for item in required)
    return FinalIntegratedControlPackage(
        integrated_git_sha=integrated_git_sha,
        receipts=ordered,
    )


def assess_assembled_final_integrated_exam(
    *,
    package: FinalIntegratedControlPackage,
    phase21_manifest: Phase21PolicyFreezeManifest,
    phase22_receipt: Phase22QualificationReceipt,
    certification_critical_external_blockers: tuple[str, ...] = (),
) -> FinalIntegratedExamReport:
    if not isinstance(package, FinalIntegratedControlPackage):
        raise CiboCapitalManagementError(
            "final integrated exam requires canonical control package"
        )
    if (
        package.policy_identity_sha256
        != phase22_receipt.candidate_parameter_sha256
        or package.phase22_qualification_artifact_sha256
        != phase22_receipt.qualification_artifact_sha256
    ):
        raise CiboCapitalManagementError(
            "final integrated package/Phase22 lineage drift"
        )
    return assess_receipt_bound_final_integrated_exam_v2(
        integrated_head_sha=package.integrated_git_sha,
        phase21_manifest=phase21_manifest,
        phase22_receipt=phase22_receipt,
        receipts=package.receipts,
        certification_critical_external_blockers=(
            certification_critical_external_blockers
        ),
    )
