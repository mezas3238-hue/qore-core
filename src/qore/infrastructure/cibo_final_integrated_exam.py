"""Executable ordinary CIBO Final Integrated Certification Exam gate.

This gate is downstream of the narrow Phase22 economic certification receipt.
It cannot grant DEMO, LIVE, real-capital, execution, Risk or merge authority.
It requires a pre-exam zero-open receipt plus all P1-P8 and E1-E10 evidence.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_final_certification import (
    CiboEconomicCertificationDecision,
    CiboEconomicCertificationStatus,
)

FINAL_INTEGRATED_EXAM_ID = "CIBO_FINAL_INTEGRATED_CERTIFICATION_EXAM_V1"
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_SHA1_RE = re.compile(r"^[0-9a-f]{40}$")


class FinalIntegratedExamStatus(StrEnum):
    PASS = "PASS"
    BLOCKED = "BLOCKED"


class FinalIntegratedAssertionId(StrEnum):
    E1_AUTHORITY = "E1_AUTHORITY"
    E2_CAPITAL_CONSERVATION = "E2_CAPITAL_CONSERVATION"
    E3_REALIZED_CAPITAL_LAW = "E3_REALIZED_CAPITAL_LAW"
    E4_PROVIDER_TRUTH = "E4_PROVIDER_TRUTH"
    E5_RISK_PRECEDENCE = "E5_RISK_PRECEDENCE"
    E6_CHRONOLOGY_NO_LEAKAGE = "E6_CHRONOLOGY_NO_LEAKAGE"
    E7_ECONOMIC_NONCOMPENSATION = "E7_ECONOMIC_NONCOMPENSATION"
    E8_STRESS_INTEGRITY = "E8_STRESS_INTEGRITY"
    E9_TEMPORAL_REPLICATION = "E9_TEMPORAL_REPLICATION"
    E10_DETERMINISTIC_REPLAY = "E10_DETERMINISTIC_REPLAY"


_REQUIRED_ASSERTIONS = frozenset(FinalIntegratedAssertionId)


@dataclass(frozen=True, slots=True)
class FinalIntegratedAssertionEvidence:
    assertion_id: FinalIntegratedAssertionId
    passed: bool
    evidence_sha256: str

    def __post_init__(self) -> None:
        if type(self.assertion_id) is not FinalIntegratedAssertionId:
            raise CiboCapitalManagementError(
                "final integrated assertion identity is invalid"
            )
        if type(self.passed) is not bool:
            raise CiboCapitalManagementError(
                "final integrated assertion pass flag must be bool"
            )
        _sha256(self.evidence_sha256, "assertion evidence")


@dataclass(frozen=True, slots=True)
class FinalIntegratedExamEvidence:
    integrated_head_sha: str
    source_truth_sha256: str
    pre_exam_zero_open_sha256: str
    ci_manifest_sha256: str
    provider_risk_cma_forward_sha256: str
    phase20d_qualification_sha256: str
    policy_calibration_freeze_sha256: str
    scientific_closure_sha256: str
    compound_closure_sha256: str
    economic_certification: CiboEconomicCertificationDecision
    assertions: tuple[FinalIntegratedAssertionEvidence, ...]
    source_truth_reconciled: bool
    pre_exam_zero_open_passed: bool
    certification_ci_clear: bool
    provider_risk_cma_forward_valid: bool
    phase20d_passed: bool
    policy_calibration_frozen: bool
    scientific_closure_terminal: bool
    compound_closure_terminal: bool
    certification_critical_external_blockers: tuple[str, ...] = ()
    synthetic_evidence_used: bool = False
    holdout_mining_used: bool = False
    outcome_aware_refit: bool = False
    operational_authority_claimed: bool = False

    def __post_init__(self) -> None:
        if _SHA1_RE.fullmatch(self.integrated_head_sha) is None:
            raise CiboCapitalManagementError(
                "final integrated exam HEAD must be lowercase 40-hex"
            )
        for name in (
            "source_truth_sha256",
            "pre_exam_zero_open_sha256",
            "ci_manifest_sha256",
            "provider_risk_cma_forward_sha256",
            "phase20d_qualification_sha256",
            "policy_calibration_freeze_sha256",
            "scientific_closure_sha256",
            "compound_closure_sha256",
        ):
            _sha256(getattr(self, name), name)
        if not isinstance(
            self.economic_certification,
            CiboEconomicCertificationDecision,
        ):
            raise CiboCapitalManagementError(
                "final integrated exam requires canonical economic certification"
            )
        ids = tuple(item.assertion_id for item in self.assertions)
        if len(ids) != len(set(ids)):
            raise CiboCapitalManagementError(
                "final integrated exam assertion evidence must be unique"
            )
        for name in (
            "source_truth_reconciled",
            "pre_exam_zero_open_passed",
            "certification_ci_clear",
            "provider_risk_cma_forward_valid",
            "phase20d_passed",
            "policy_calibration_frozen",
            "scientific_closure_terminal",
            "compound_closure_terminal",
            "synthetic_evidence_used",
            "holdout_mining_used",
            "outcome_aware_refit",
            "operational_authority_claimed",
        ):
            if type(getattr(self, name)) is not bool:
                raise CiboCapitalManagementError(
                    f"final integrated exam {name} must be bool"
                )
        if any(
            not isinstance(item, str) or not item
            for item in self.certification_critical_external_blockers
        ):
            raise CiboCapitalManagementError(
                "final integrated exam external blockers must be non-empty strings"
            )


@dataclass(frozen=True, slots=True)
class FinalIntegratedExamReport:
    exam_id: str
    status: FinalIntegratedExamStatus
    integrated_head_sha: str
    blockers: tuple[str, ...]
    demo_execution_authorized: bool = False
    live_authorized: bool = False
    real_capital_authorized: bool = False
    merge_authorized: bool = False

    def __post_init__(self) -> None:
        if self.exam_id != FINAL_INTEGRATED_EXAM_ID:
            raise CiboCapitalManagementError(
                "final integrated exam identity drift"
            )
        if (
            self.demo_execution_authorized
            or self.live_authorized
            or self.real_capital_authorized
            or self.merge_authorized
        ):
            raise CiboCapitalManagementError(
                "final integrated exam cannot grant operational authority"
            )
        if self.status is FinalIntegratedExamStatus.PASS and self.blockers:
            raise CiboCapitalManagementError(
                "passing final integrated exam cannot retain blockers"
            )


def assess_final_integrated_exam(
    evidence: FinalIntegratedExamEvidence,
) -> FinalIntegratedExamReport:
    """Apply preregistered P1-P8 and E1-E10 as a non-compensatory AND gate."""

    if not isinstance(evidence, FinalIntegratedExamEvidence):
        raise CiboCapitalManagementError(
            "final integrated exam requires canonical evidence"
        )
    blockers: list[str] = []
    prerequisites = (
        ("P1_SOURCE_OF_TRUTH_RECONCILED", evidence.source_truth_reconciled),
        ("P2_PRE_EXAM_ZERO_OPEN_PASS", evidence.pre_exam_zero_open_passed),
        ("P3_CERTIFICATION_CI_CLEAR", evidence.certification_ci_clear),
        (
            "P4_PROVIDER_RISK_CMA_FORWARD_TRUTH",
            evidence.provider_risk_cma_forward_valid,
        ),
        ("P5_PHASE20D_PASS", evidence.phase20d_passed),
        ("P6_POLICY_CALIBRATION_FREEZE", evidence.policy_calibration_frozen),
        ("P7_SCIENTIFIC_CLOSURE", evidence.scientific_closure_terminal),
        ("P8_COMPOUND_CLOSURE", evidence.compound_closure_terminal),
    )
    blockers.extend(name for name, passed in prerequisites if not passed)

    if (
        evidence.economic_certification.status
        is not CiboEconomicCertificationStatus.CERTIFIED
    ):
        blockers.append("PHASE22_ECONOMIC_CERTIFICATION_REQUIRED")

    assertion_by_id = {
        item.assertion_id: item for item in evidence.assertions
    }
    for assertion_id in FinalIntegratedAssertionId:
        item = assertion_by_id.get(assertion_id)
        if item is None:
            blockers.append(f"{assertion_id.value}_EVIDENCE_REQUIRED")
        elif not item.passed:
            blockers.append(f"{assertion_id.value}_FAILED")

    if evidence.certification_critical_external_blockers:
        blockers.append("CERTIFICATION_CRITICAL_EXTERNAL_BLOCKER")
    if evidence.synthetic_evidence_used:
        blockers.append("SYNTHETIC_EVIDENCE_USED")
    if evidence.holdout_mining_used:
        blockers.append("HOLDOUT_MINING_USED")
    if evidence.outcome_aware_refit:
        blockers.append("OUTCOME_AWARE_REFIT_USED")
    if evidence.operational_authority_claimed:
        blockers.append("ILLEGAL_OPERATIONAL_AUTHORITY_CLAIM")

    blockers = list(dict.fromkeys(blockers))
    status = (
        FinalIntegratedExamStatus.PASS
        if not blockers
        else FinalIntegratedExamStatus.BLOCKED
    )
    return FinalIntegratedExamReport(
        exam_id=FINAL_INTEGRATED_EXAM_ID,
        status=status,
        integrated_head_sha=evidence.integrated_head_sha,
        blockers=tuple(blockers),
    )


def _sha256(value: str, name: str) -> None:
    if _SHA256_RE.fullmatch(value) is None:
        raise CiboCapitalManagementError(
            f"final integrated exam {name} must be canonical sha256"
        )
