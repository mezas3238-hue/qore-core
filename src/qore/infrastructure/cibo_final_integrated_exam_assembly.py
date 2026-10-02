"""Canonical 18-receipt assembly for the CIBO Final Integrated Exam."""

from __future__ import annotations

import hashlib
import json
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
