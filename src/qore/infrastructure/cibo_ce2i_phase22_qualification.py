"""Phase22 sealed-holdout economic qualification for CIBO.

This stage evaluates only a fresh, disjoint, post-Phase21 holdout. It first
proves holdout lineage integrity, then applies the exact frozen Phase20D V2
economic protocol without refit.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from qore.infrastructure.cibo_ce2i_phase20_forward_policy_store import (
    VersionedPhase20ForwardPolicyBook,
)
from qore.infrastructure.cibo_ce2i_phase20_qualification import (
    Phase20QualificationReport,
    Phase20QualificationStatus,
    run_phase20d_v2_qualification,
)
from qore.infrastructure.cibo_ce2i_phase21_policy_freeze import (
    Phase21PolicyFreezeManifest,
)
from qore.infrastructure.cibo_ce2i_phase22_holdout_gate import (
    Phase22HoldoutLineageAssessment,
    assess_phase22_holdout_lineage,
)
from qore.infrastructure.cibo_ce2i_phase22_qualification_plan import (
    FROZEN_PHASE22_HOLDOUT_QUALIFICATION_PLAN,
    phase22_holdout_qualification_plan_sha256,
)
from qore.infrastructure.cibo_ce2i_qualification_evidence_protocol import (
    Phase20QualificationEvidenceBook,
)


class Phase22HoldoutQualificationStatus(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    NOT_READY = "NOT_READY"
    INVALID = "INVALID"


@dataclass(frozen=True, slots=True)
class Phase22HoldoutQualificationReport:
    status: Phase22HoldoutQualificationStatus
    plan_id: str
    plan_sha256: str
    lineage: Phase22HoldoutLineageAssessment
    economic_report: Phase20QualificationReport | None
    failures: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.status is Phase22HoldoutQualificationStatus.PASS:
            if not self.lineage.lineage_valid:
                raise ValueError("Phase22 PASS requires valid holdout lineage")
            if self.economic_report is None:
                raise ValueError("Phase22 PASS requires economic report")
            if self.economic_report.status is not Phase20QualificationStatus.PASS:
                raise ValueError("Phase22 PASS requires economic protocol PASS")
            if self.failures:
                raise ValueError("Phase22 PASS cannot contain failures")
        if (
            not self.lineage.lineage_valid
            and self.status is not Phase22HoldoutQualificationStatus.INVALID
        ):
            raise ValueError("invalid Phase22 lineage must fail closed")

    @property
    def economically_certified(self) -> bool:
        return (
            self.status is Phase22HoldoutQualificationStatus.PASS
            and self.lineage.lineage_valid
            and self.economic_report is not None
            and self.economic_report.status is Phase20QualificationStatus.PASS
            and not self.failures
        )


def run_phase22_holdout_qualification(
    *,
    phase21_manifest: Phase21PolicyFreezeManifest,
    qualification_evidence_book: Phase20QualificationEvidenceBook,
    holdout_evidence_book: Phase20QualificationEvidenceBook,
    holdout_policy_book: VersionedPhase20ForwardPolicyBook,
    qualification_evidence_store_sha256: str,
    qualification_policy_store_sha256: str,
    holdout_evidence_store_sha256: str,
    holdout_policy_store_sha256: str,
) -> Phase22HoldoutQualificationReport:
    """Run the untouched Phase22 confirmation gate with no refit."""

    plan = FROZEN_PHASE22_HOLDOUT_QUALIFICATION_PLAN
    lineage = assess_phase22_holdout_lineage(
        phase21_manifest=phase21_manifest,
        qualification_evidence_book=qualification_evidence_book,
        holdout_evidence_book=holdout_evidence_book,
        holdout_policy_book=holdout_policy_book,
        qualification_evidence_store_sha256=(
            qualification_evidence_store_sha256
        ),
        qualification_policy_store_sha256=qualification_policy_store_sha256,
        holdout_evidence_store_sha256=holdout_evidence_store_sha256,
        holdout_policy_store_sha256=holdout_policy_store_sha256,
    )
    if not lineage.lineage_valid:
        return Phase22HoldoutQualificationReport(
            status=Phase22HoldoutQualificationStatus.INVALID,
            plan_id=plan.plan_id,
            plan_sha256=phase22_holdout_qualification_plan_sha256(),
            lineage=lineage,
            economic_report=None,
            failures=lineage.reasons,
        )

    economic = run_phase20d_v2_qualification(
        evidence_book=holdout_evidence_book,
        policy_book=holdout_policy_book,
    )
    if economic.status is Phase20QualificationStatus.PASS:
        status = Phase22HoldoutQualificationStatus.PASS
    elif economic.status is Phase20QualificationStatus.FAIL:
        status = Phase22HoldoutQualificationStatus.FAIL
    elif economic.status is Phase20QualificationStatus.NOT_READY:
        status = Phase22HoldoutQualificationStatus.NOT_READY
    else:
        status = Phase22HoldoutQualificationStatus.INVALID

    return Phase22HoldoutQualificationReport(
        status=status,
        plan_id=plan.plan_id,
        plan_sha256=phase22_holdout_qualification_plan_sha256(),
        lineage=lineage,
        economic_report=economic,
        failures=economic.failures,
    )
