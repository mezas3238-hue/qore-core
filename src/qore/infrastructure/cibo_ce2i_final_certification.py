"""Final economic-certification gate for CIBO CMA + CE2I.

The gate can certify only the frozen policy's economic evidence chain. It never
grants DEMO, LIVE, real-capital, execution, Risk or merge authority.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_phase20_policy_candidate import (
    FROZEN_PHASE20_POLICY_CANDIDATE,
)
from qore.infrastructure.cibo_ce2i_phase21_policy_freeze import (
    Phase21PolicyFreezeManifest,
)
from qore.infrastructure.cibo_ce2i_phase22_qualification import (
    Phase22HoldoutQualificationReport,
)
from qore.infrastructure.cibo_ce2i_phase22_qualification_plan import (
    FROZEN_PHASE22_HOLDOUT_QUALIFICATION_PLAN,
    phase22_holdout_qualification_plan_sha256,
)

_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


class CiboEconomicCertificationStatus(StrEnum):
    CERTIFIED = "CIBO_ECONOMICALLY_CERTIFIED"
    PENDING = "PENDING"
    INVALID = "INVALID"


@dataclass(frozen=True, slots=True)
class Phase22QualificationReceipt:
    candidate_id: str
    candidate_parameter_sha256: str
    phase21_manifest_sha256: str
    phase22_plan_id: str
    phase22_plan_sha256: str
    holdout_evidence_store_sha256: str
    holdout_policy_store_sha256: str
    qualification_artifact_sha256: str
    qualified_at: datetime
    evidence_class: str
    passed: bool
    lineage_valid: bool
    economic_holdout_passed: bool

    def __post_init__(self) -> None:
        candidate = FROZEN_PHASE20_POLICY_CANDIDATE
        plan = FROZEN_PHASE22_HOLDOUT_QUALIFICATION_PLAN
        if self.candidate_id != candidate.candidate_id:
            raise CiboCapitalManagementError(
                "final certification candidate identity drift"
            )
        if self.candidate_parameter_sha256 != candidate.parameter_sha256():
            raise CiboCapitalManagementError(
                "final certification parameter digest drift"
            )
        if self.phase22_plan_id != plan.plan_id:
            raise CiboCapitalManagementError(
                "final certification Phase22 plan identity drift"
            )
        if self.phase22_plan_sha256 != phase22_holdout_qualification_plan_sha256():
            raise CiboCapitalManagementError(
                "final certification Phase22 plan digest drift"
            )
        for name in (
            "phase21_manifest_sha256",
            "holdout_evidence_store_sha256",
            "holdout_policy_store_sha256",
            "qualification_artifact_sha256",
        ):
            if _SHA256_RE.fullmatch(getattr(self, name)) is None:
                raise CiboCapitalManagementError(
                    f"final certification {name} must be canonical sha256"
                )
        if self.qualified_at.tzinfo is None or self.qualified_at.utcoffset() is None:
            raise CiboCapitalManagementError(
                "final certification qualified_at must be timezone-aware"
            )
        if self.evidence_class != "FORWARD_EMPIRICAL_HOLDOUT":
            raise CiboCapitalManagementError(
                "final certification requires FORWARD_EMPIRICAL_HOLDOUT"
            )
        if not (
            self.passed
            and self.lineage_valid
            and self.economic_holdout_passed
        ):
            raise CiboCapitalManagementError(
                "final certification receipt requires Phase22 economic PASS"
            )


@dataclass(frozen=True, slots=True)
class CiboEconomicCertificationDecision:
    status: CiboEconomicCertificationStatus
    candidate_id: str
    candidate_parameter_sha256: str
    phase21_manifest_sha256: str
    phase22_plan_sha256: str
    blockers: tuple[str, ...]
    demo_execution_authorized: bool = False
    live_authorized: bool = False
    real_capital_authorized: bool = False
    merge_authorized: bool = False

    def __post_init__(self) -> None:
        if (
            self.demo_execution_authorized
            or self.live_authorized
            or self.real_capital_authorized
            or self.merge_authorized
        ):
            raise CiboCapitalManagementError(
                "economic certification cannot grant operational authority"
            )
        if (
            self.status is CiboEconomicCertificationStatus.CERTIFIED
            and self.blockers
        ):
            raise CiboCapitalManagementError(
                "certified economic decision cannot contain blockers"
            )


def build_phase22_qualification_receipt(
    *,
    phase21_manifest: Phase21PolicyFreezeManifest,
    report: Phase22HoldoutQualificationReport,
    holdout_evidence_store_sha256: str,
    holdout_policy_store_sha256: str,
    qualification_artifact_sha256: str,
    qualified_at: datetime,
) -> Phase22QualificationReceipt:
    if not report.economically_certified:
        raise CiboCapitalManagementError(
            "cannot build Phase22 receipt without economic holdout PASS"
        )
    return Phase22QualificationReceipt(
        candidate_id=phase21_manifest.candidate_id,
        candidate_parameter_sha256=(
            phase21_manifest.candidate_parameter_sha256
        ),
        phase21_manifest_sha256=phase21_manifest.manifest_sha256(),
        phase22_plan_id=report.plan_id,
        phase22_plan_sha256=report.plan_sha256,
        holdout_evidence_store_sha256=holdout_evidence_store_sha256,
        holdout_policy_store_sha256=holdout_policy_store_sha256,
        qualification_artifact_sha256=qualification_artifact_sha256,
        qualified_at=qualified_at,
        evidence_class="FORWARD_EMPIRICAL_HOLDOUT",
        passed=True,
        lineage_valid=report.lineage.lineage_valid,
        economic_holdout_passed=True,
    )


def assess_cibo_final_economic_certification(
    *,
    phase21_manifest: Phase21PolicyFreezeManifest,
    phase22_receipt: Phase22QualificationReceipt | None,
) -> CiboEconomicCertificationDecision:
    phase21_sha = phase21_manifest.manifest_sha256()
    plan_sha = phase22_holdout_qualification_plan_sha256()
    candidate = FROZEN_PHASE20_POLICY_CANDIDATE

    if phase22_receipt is None:
        return CiboEconomicCertificationDecision(
            status=CiboEconomicCertificationStatus.PENDING,
            candidate_id=candidate.candidate_id,
            candidate_parameter_sha256=candidate.parameter_sha256(),
            phase21_manifest_sha256=phase21_sha,
            phase22_plan_sha256=plan_sha,
            blockers=("PHASE22_QUALIFICATION_RECEIPT_REQUIRED",),
        )

    blockers: list[str] = []
    if phase22_receipt.phase21_manifest_sha256 != phase21_sha:
        blockers.append("PHASE21_MANIFEST_LINEAGE_MISMATCH")
    if phase22_receipt.qualified_at <= phase21_manifest.frozen_at:
        blockers.append("PHASE22_QUALIFICATION_NOT_POST_PHASE21_FREEZE")

    if blockers:
        status = CiboEconomicCertificationStatus.INVALID
    else:
        status = CiboEconomicCertificationStatus.CERTIFIED

    return CiboEconomicCertificationDecision(
        status=status,
        candidate_id=candidate.candidate_id,
        candidate_parameter_sha256=candidate.parameter_sha256(),
        phase21_manifest_sha256=phase21_sha,
        phase22_plan_sha256=plan_sha,
        blockers=tuple(blockers),
    )
