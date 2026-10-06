"""Pre-exam readiness gate for the frozen CIBO USD60 / six-month program.

This gate does not run the exam, open the sealed holdout, classify performance,
or grant productive authority. It only proves that the prerequisite evidence
planes are present before the governed exam may be scheduled by the canonical
holdout/Phase21-22 authority chain.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from qore.infrastructure.cibo_arch_b_forward_economic_manifest import (
    ArchBForwardEconomicManifest,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_usd60_six_month_certification import (
    FROZEN_CIBO_USD60_SIX_MONTH_PROTOCOL,
)

USD60_PRE_EXAM_GATE_ID = "CIBO_USD60_PRE_EXAM_READINESS_V1"

_REQUIRED_PREREQUISITES = (
    "PROVIDER_ECONOMICS_AND_COST_FREEZE",
    "RISK_INTEGRATION_PROVEN",
    "INTEGRATED_CAPITAL_TRUTH_REAL_POPULATION_BOUND",
    "T01_T20_ENGINEERING_READINESS",
    "FRESH_OOS_PHASE21_VALIDATIONS",
    "PHASE21_POLICY_FREEZE_SEALED",
    "HOLDOUT_REGISTRY_SEALED_UNTOUCHED",
)


@dataclass(frozen=True, slots=True)
class CiboUsd60PrerequisiteEvidence:
    prerequisite_id: str
    passed: bool
    evidence_refs: tuple[str, ...]
    observed_at: datetime
    holdout_outcomes_inspected: bool = False

    def __post_init__(self) -> None:
        if self.prerequisite_id not in _REQUIRED_PREREQUISITES:
            raise CiboCapitalManagementError(
                "USD60 prerequisite id is not canonical"
            )
        if type(self.passed) is not bool:
            raise CiboCapitalManagementError(
                "USD60 prerequisite passed flag must be bool"
            )
        if (
            not self.evidence_refs
            or len(self.evidence_refs) != len(set(self.evidence_refs))
            or any(not isinstance(item, str) or not item for item in self.evidence_refs)
        ):
            raise CiboCapitalManagementError(
                "USD60 prerequisite evidence refs must be non-empty unique"
            )
        if (
            self.observed_at.tzinfo is None
            or self.observed_at.utcoffset() is None
        ):
            raise CiboCapitalManagementError(
                "USD60 prerequisite observed_at must be timezone-aware"
            )
        if type(self.holdout_outcomes_inspected) is not bool:
            raise CiboCapitalManagementError(
                "USD60 prerequisite holdout inspection flag must be bool"
            )


@dataclass(frozen=True, slots=True)
class CiboUsd60PreExamReadiness:
    gate_id: str
    protocol_id: str
    forward_manifest_sha256: str
    forward_manifest_ready: bool
    prerequisite_count: int
    passed_prerequisite_count: int
    holdout_outcomes_inspected: bool
    ready_for_governed_exam: bool
    blockers: tuple[str, ...]
    holdout_access_authority: bool = False
    certification_ready: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if self.gate_id != USD60_PRE_EXAM_GATE_ID:
            raise CiboCapitalManagementError(
                "USD60 pre-exam gate identity drift"
            )
        if self.protocol_id != FROZEN_CIBO_USD60_SIX_MONTH_PROTOCOL.protocol_id:
            raise CiboCapitalManagementError(
                "USD60 pre-exam protocol identity drift"
            )
        if (
            not self.forward_manifest_sha256.startswith("sha256:")
            or len(self.forward_manifest_sha256) != 71
        ):
            raise CiboCapitalManagementError(
                "USD60 pre-exam forward manifest SHA invalid"
            )
        if self.prerequisite_count != len(_REQUIRED_PREREQUISITES):
            raise CiboCapitalManagementError(
                "USD60 pre-exam prerequisite count drift"
            )
        if not 0 <= self.passed_prerequisite_count <= self.prerequisite_count:
            raise CiboCapitalManagementError(
                "USD60 pre-exam passed prerequisite count invalid"
            )
        for name in (
            "forward_manifest_ready",
            "holdout_outcomes_inspected",
            "ready_for_governed_exam",
            "holdout_access_authority",
            "certification_ready",
            "productive_authority",
        ):
            if type(getattr(self, name)) is not bool:
                raise CiboCapitalManagementError(
                    f"USD60 pre-exam {name} must be bool"
                )
        expected_ready = (
            self.forward_manifest_ready
            and self.passed_prerequisite_count == self.prerequisite_count
            and not self.holdout_outcomes_inspected
            and not self.blockers
        )
        if self.ready_for_governed_exam != expected_ready:
            raise CiboCapitalManagementError(
                "USD60 pre-exam readiness/blocker drift"
            )
        if (
            self.holdout_access_authority
            or self.certification_ready
            or self.productive_authority
        ):
            raise CiboCapitalManagementError(
                "USD60 pre-exam gate cannot grant access/certification/authority"
            )


def assess_cibo_usd60_pre_exam_readiness(
    *,
    forward_manifest: ArchBForwardEconomicManifest,
    prerequisites: tuple[CiboUsd60PrerequisiteEvidence, ...],
) -> CiboUsd60PreExamReadiness:
    """Fail closed until every pre-exam evidence plane is proven."""

    if not isinstance(forward_manifest, ArchBForwardEconomicManifest):
        raise CiboCapitalManagementError(
            "USD60 pre-exam requires canonical Architect-B manifest"
        )
    if not isinstance(prerequisites, tuple) or any(
        not isinstance(item, CiboUsd60PrerequisiteEvidence)
        for item in prerequisites
    ):
        raise CiboCapitalManagementError(
            "USD60 pre-exam requires canonical prerequisite evidence"
        )
    ids = tuple(item.prerequisite_id for item in prerequisites)
    if len(ids) != len(set(ids)):
        raise CiboCapitalManagementError(
            "USD60 pre-exam prerequisite ids must be unique"
        )

    by_id = {item.prerequisite_id: item for item in prerequisites}
    blockers: list[str] = []
    for required in _REQUIRED_PREREQUISITES:
        evidence = by_id.get(required)
        if evidence is None:
            blockers.append(f"USD60_{required}_EVIDENCE_MISSING")
            continue
        if not evidence.passed:
            blockers.append(f"USD60_{required}_NOT_PASSED")
    extra = tuple(sorted(set(ids) - set(_REQUIRED_PREREQUISITES)))
    if extra:
        raise CiboCapitalManagementError(
            "USD60 pre-exam contains non-canonical prerequisite evidence"
        )

    inspected = any(item.holdout_outcomes_inspected for item in prerequisites)
    if inspected:
        blockers.append("USD60_PRE_EXAM_HOLDOUT_OUTCOMES_ALREADY_INSPECTED")
    if not forward_manifest.ready_for_scientific_consumption:
        blockers.append("USD60_PHASE20D_FORWARD_MANIFEST_NOT_READY")

    passed = sum(
        1
        for required in _REQUIRED_PREREQUISITES
        if required in by_id and by_id[required].passed
    )
    blockers = list(dict.fromkeys(blockers))
    return CiboUsd60PreExamReadiness(
        gate_id=USD60_PRE_EXAM_GATE_ID,
        protocol_id=FROZEN_CIBO_USD60_SIX_MONTH_PROTOCOL.protocol_id,
        forward_manifest_sha256=forward_manifest.fingerprint(),
        forward_manifest_ready=forward_manifest.ready_for_scientific_consumption,
        prerequisite_count=len(_REQUIRED_PREREQUISITES),
        passed_prerequisite_count=passed,
        holdout_outcomes_inspected=inspected,
        ready_for_governed_exam=(
            forward_manifest.ready_for_scientific_consumption
            and passed == len(_REQUIRED_PREREQUISITES)
            and not inspected
            and not blockers
        ),
        blockers=tuple(blockers),
    )


def required_usd60_pre_exam_prerequisites() -> tuple[str, ...]:
    return _REQUIRED_PREREQUISITES
