"""Canonical ten-receipt assembly for the CIBO World Cup exam."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_final_integrated_exam import (
    FinalIntegratedExamReport,
)
from qore.infrastructure.cibo_world_cup_maximum_capability_exam import (
    WorldCupControlReceipt,
    WorldCupMaximumCapabilityReport,
    assess_receipt_bound_world_cup_maximum_capability_exam,
    final_integrated_exam_report_sha256,
    required_world_cup_receipt_ids,
    world_cup_policy_identity_sha256,
)


@dataclass(frozen=True, slots=True)
class WorldCupControlPackage:
    integrated_git_sha: str
    final_integrated_exam_report_sha256: str
    receipts: tuple[WorldCupControlReceipt, ...]
    certification_claimed: bool = False
    production_authority: bool = False

    def __post_init__(self) -> None:
        required = required_world_cup_receipt_ids()
        if (
            not isinstance(self.receipts, tuple)
            or any(not isinstance(item, WorldCupControlReceipt) for item in self.receipts)
        ):
            raise CiboCapitalManagementError(
                "World Cup package requires canonical receipts"
            )
        ids = tuple(item.receipt_id for item in self.receipts)
        if ids != required:
            raise CiboCapitalManagementError(
                "World Cup package requires exact ordered ten receipts"
            )
        if len(ids) != len(set(ids)):
            raise CiboCapitalManagementError(
                "World Cup package contains duplicate receipt"
            )
        if any(
            item.integrated_git_sha != self.integrated_git_sha
            for item in self.receipts
        ):
            raise CiboCapitalManagementError(
                "World Cup package cross-HEAD receipt"
            )
        if any(
            item.world_cup_policy_identity_sha256
            != world_cup_policy_identity_sha256()
            for item in self.receipts
        ):
            raise CiboCapitalManagementError(
                "World Cup package policy identity drift"
            )
        if any(
            item.final_integrated_exam_report_sha256
            != self.final_integrated_exam_report_sha256
            for item in self.receipts
        ):
            raise CiboCapitalManagementError(
                "World Cup package Final Integrated report drift"
            )
        if self.certification_claimed or self.production_authority:
            raise CiboCapitalManagementError(
                "World Cup package cannot grant authority"
            )

    def fingerprint(self) -> str:
        payload = {
            "integrated_git_sha": self.integrated_git_sha,
            "final_integrated_exam_report_sha256": (
                self.final_integrated_exam_report_sha256
            ),
            "receipt_fingerprints": [
                item.source_artifact_sha256 for item in self.receipts
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


def assemble_world_cup_control_package(
    *,
    integrated_git_sha: str,
    final_integrated_exam: FinalIntegratedExamReport,
    receipts: tuple[WorldCupControlReceipt, ...],
) -> WorldCupControlPackage:
    if not isinstance(final_integrated_exam, FinalIntegratedExamReport):
        raise CiboCapitalManagementError(
            "World Cup assembly requires canonical Final Integrated report"
        )
    if final_integrated_exam.integrated_head_sha != integrated_git_sha:
        raise CiboCapitalManagementError(
            "World Cup assembly Final Integrated HEAD drift"
        )

    by_id: dict[str, WorldCupControlReceipt] = {}
    for receipt in receipts:
        if not isinstance(receipt, WorldCupControlReceipt):
            raise CiboCapitalManagementError(
                "World Cup assembly requires canonical receipts"
            )
        if receipt.receipt_id in by_id:
            raise CiboCapitalManagementError(
                "World Cup assembly duplicate receipt id"
            )
        by_id[receipt.receipt_id] = receipt

    required = required_world_cup_receipt_ids()
    missing = tuple(item for item in required if item not in by_id)
    extras = tuple(sorted(set(by_id) - set(required)))
    if missing:
        raise CiboCapitalManagementError(
            "World Cup assembly missing receipts: " + ",".join(missing)
        )
    if extras:
        raise CiboCapitalManagementError(
            "World Cup assembly unexpected receipts: " + ",".join(extras)
        )

    final_sha = final_integrated_exam_report_sha256(final_integrated_exam)
    return WorldCupControlPackage(
        integrated_git_sha=integrated_git_sha,
        final_integrated_exam_report_sha256=final_sha,
        receipts=tuple(by_id[item] for item in required),
    )


def assess_assembled_world_cup_exam(
    *,
    package: WorldCupControlPackage,
    final_integrated_exam: FinalIntegratedExamReport,
    certification_critical_external_blockers: tuple[str, ...] = (),
) -> WorldCupMaximumCapabilityReport:
    if not isinstance(package, WorldCupControlPackage):
        raise CiboCapitalManagementError(
            "World Cup exam requires canonical control package"
        )
    expected_final_sha = final_integrated_exam_report_sha256(
        final_integrated_exam
    )
    if package.final_integrated_exam_report_sha256 != expected_final_sha:
        raise CiboCapitalManagementError(
            "World Cup package/final report lineage drift"
        )
    return assess_receipt_bound_world_cup_maximum_capability_exam(
        integrated_head_sha=package.integrated_git_sha,
        final_integrated_exam=final_integrated_exam,
        receipts=package.receipts,
        certification_critical_external_blockers=(
            certification_critical_external_blockers
        ),
    )
