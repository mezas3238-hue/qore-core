"""Receipt-bound economic certification for the reused USD60 capability exam.

This module is deliberately parallel to the legacy fresh Phase22 qualification
route.  A reused holdout may certify the requested CIBO capability surface, but
it must never be represented as fresh-OOS evidence or as a Phase22 receipt.

The receipt is bound to the exact integrated Git HEAD, workflow run and the
canonical capability/dual-objective report digests.  It grants no operational,
LIVE, real-capital, production, Risk-bypass or merge authority.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_final_certification import (
    CiboEconomicCertificationStatus,
)
from qore.infrastructure.cibo_reused_holdout_capability_exam import (
    InfrastructureCapabilityExamReport,
)
from qore.infrastructure.cibo_usd60_dual_objective_exam import (
    DUAL_OBJECTIVE_EXAM_ID,
    CiboUsd60DualObjectiveStatus,
    assess_cibo_usd60_dual_objective_exam,
)

CAPABILITY_CERTIFICATION_RECEIPT_ID = (
    "CIBO_USD60_REUSED_HOLDOUT_CAPABILITY_CERTIFICATION_RECEIPT_V1"
)
CAPABILITY_CERTIFICATION_SCOPE = "CAPABILITY_CERTIFICATION_NON_FRESH_OOS"
CAPABILITY_EVIDENCE_CLASS = "NON_CERTIFYING_REUSED_HOLDOUT"
CAPABILITY_CANDIDATE_ID = (
    "CIBO_USD60_6M_HOLDOUT_2014-10-19_2015-04-19_V4"
)

_SHA1_RE = re.compile(r"^[0-9a-f]{40}$")
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


def _canonical(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        return value.isoformat()
    if hasattr(value, "as_tuple") and value.__class__.__name__ == "Decimal":
        return format(value, "f")
    if hasattr(value, "__dataclass_fields__"):
        return {
            str(key): _canonical(item)
            for key, item in asdict(value).items()
        }
    if isinstance(value, tuple):
        return [_canonical(item) for item in value]
    if isinstance(value, list):
        return [_canonical(item) for item in value]
    if isinstance(value, dict):
        return {
            str(key): _canonical(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    return value


def _sha256(payload: Any) -> str:
    raw = json.dumps(
        _canonical(payload),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _capability_policy_identity(
    *,
    integrated_git_sha: str,
) -> str:
    return _sha256(
        {
            "authority_model": "TRADER_VOLUME_FREE__CIBO_CMA__QORE_RISK",
            "dual_objective_exam_id": DUAL_OBJECTIVE_EXAM_ID,
            "integrated_git_sha": integrated_git_sha,
            "scope": CAPABILITY_CERTIFICATION_SCOPE,
        }
    )


@dataclass(frozen=True, slots=True)
class CiboUsd60CapabilityCertificationReceipt:
    receipt_id: str
    certification_scope: str
    evidence_class: str
    integrated_git_sha: str
    workflow_run_id: int
    candidate_id: str
    source_batch_sha256: str
    capability_report_sha256: str
    dual_objective_report_sha256: str
    capability_policy_identity_sha256: str
    qualified_at: datetime
    dual_objective_status: str
    usd60_survival_passed: bool
    maximum_capability_passed: bool
    scientific_freshness_claimed: bool = False
    fresh_oos_generalization_claimed: bool = False
    synthetic_evidence_used: bool = False
    outcome_aware_refit: bool = False
    broker_mutation_performed: bool = False
    live_authorized: bool = False
    real_capital_authorized: bool = False
    production_authorized: bool = False
    merge_authorized: bool = False

    def __post_init__(self) -> None:
        if self.receipt_id != CAPABILITY_CERTIFICATION_RECEIPT_ID:
            raise CiboCapitalManagementError(
                "USD60 capability certification receipt identity drift"
            )
        if self.certification_scope != CAPABILITY_CERTIFICATION_SCOPE:
            raise CiboCapitalManagementError(
                "USD60 capability certification scope drift"
            )
        if self.evidence_class != CAPABILITY_EVIDENCE_CLASS:
            raise CiboCapitalManagementError(
                "USD60 capability receipt must remain explicitly reused/non-fresh"
            )
        if _SHA1_RE.fullmatch(self.integrated_git_sha) is None:
            raise CiboCapitalManagementError(
                "USD60 capability receipt integrated Git SHA invalid"
            )
        if type(self.workflow_run_id) is not int or self.workflow_run_id <= 0:
            raise CiboCapitalManagementError(
                "USD60 capability receipt workflow run id invalid"
            )
        if self.candidate_id != CAPABILITY_CANDIDATE_ID:
            raise CiboCapitalManagementError(
                "USD60 capability receipt holdout identity drift"
            )
        for name in (
            "source_batch_sha256",
            "capability_report_sha256",
            "dual_objective_report_sha256",
            "capability_policy_identity_sha256",
        ):
            if _SHA256_RE.fullmatch(getattr(self, name)) is None:
                raise CiboCapitalManagementError(
                    f"USD60 capability receipt {name} invalid"
                )
        if self.qualified_at.tzinfo is None or self.qualified_at.utcoffset() is None:
            raise CiboCapitalManagementError(
                "USD60 capability receipt qualified_at must be timezone-aware"
            )
        if self.dual_objective_status != CiboUsd60DualObjectiveStatus.PASS.value:
            raise CiboCapitalManagementError(
                "USD60 capability receipt requires dual-objective PASS"
            )
        if not self.usd60_survival_passed or not self.maximum_capability_passed:
            raise CiboCapitalManagementError(
                "USD60 capability receipt requires both strict-AND objectives"
            )
        contaminated = (
            self.scientific_freshness_claimed
            or self.fresh_oos_generalization_claimed
            or self.synthetic_evidence_used
            or self.outcome_aware_refit
            or self.broker_mutation_performed
            or self.live_authorized
            or self.real_capital_authorized
            or self.production_authorized
            or self.merge_authorized
        )
        if contaminated:
            raise CiboCapitalManagementError(
                "USD60 capability certification receipt governance contamination"
            )

    def payload(self) -> dict[str, Any]:
        return _canonical(asdict(self))

    def fingerprint(self) -> str:
        return _sha256(self.payload())


@dataclass(frozen=True, slots=True)
class CiboCapabilityEconomicCertificationDecision:
    status: CiboEconomicCertificationStatus
    certification_basis: str
    certification_scope: str
    evidence_class: str
    candidate_id: str
    capability_policy_identity_sha256: str
    qualification_artifact_sha256: str
    blockers: tuple[str, ...]
    fresh_oos_generalization_claimed: bool = False
    demo_execution_authorized: bool = False
    live_authorized: bool = False
    real_capital_authorized: bool = False
    production_authorized: bool = False
    merge_authorized: bool = False

    def __post_init__(self) -> None:
        if self.certification_basis != DUAL_OBJECTIVE_EXAM_ID:
            raise CiboCapitalManagementError(
                "capability economic certification basis drift"
            )
        if self.certification_scope != CAPABILITY_CERTIFICATION_SCOPE:
            raise CiboCapitalManagementError(
                "capability economic certification scope drift"
            )
        if self.evidence_class != CAPABILITY_EVIDENCE_CLASS:
            raise CiboCapitalManagementError(
                "capability economic certification evidence-class drift"
            )
        if self.candidate_id != CAPABILITY_CANDIDATE_ID:
            raise CiboCapitalManagementError(
                "capability economic certification candidate drift"
            )
        for name in (
            "capability_policy_identity_sha256",
            "qualification_artifact_sha256",
        ):
            if _SHA256_RE.fullmatch(getattr(self, name)) is None:
                raise CiboCapitalManagementError(
                    f"capability economic certification {name} invalid"
                )
        if self.status is not CiboEconomicCertificationStatus.CERTIFIED:
            raise CiboCapitalManagementError(
                "capability economic decision is emitted only after PASS"
            )
        if self.blockers:
            raise CiboCapitalManagementError(
                "certified capability economic decision cannot retain blockers"
            )
        if any(
            (
                self.fresh_oos_generalization_claimed,
                self.demo_execution_authorized,
                self.live_authorized,
                self.real_capital_authorized,
                self.production_authorized,
                self.merge_authorized,
            )
        ):
            raise CiboCapitalManagementError(
                "capability economic certification cannot grant authority/freshness"
            )

    def payload(self) -> dict[str, Any]:
        return _canonical(asdict(self))

    def fingerprint(self) -> str:
        return _sha256(self.payload())


def build_cibo_usd60_capability_certification_receipt(
    *,
    report: InfrastructureCapabilityExamReport,
    integrated_git_sha: str,
    workflow_run_id: int,
    qualified_at: datetime,
) -> CiboUsd60CapabilityCertificationReceipt:
    """Bind a real dual-objective PASS without upgrading it to fresh OOS."""

    if not isinstance(report, InfrastructureCapabilityExamReport):
        raise CiboCapitalManagementError(
            "USD60 capability certification requires canonical capability report"
        )
    if report.validation_mode != CAPABILITY_EVIDENCE_CLASS:
        raise CiboCapitalManagementError(
            "USD60 capability certification requires explicit reused-holdout mode"
        )
    if report.candidate_id != CAPABILITY_CANDIDATE_ID:
        raise CiboCapitalManagementError(
            "USD60 capability certification candidate drift"
        )
    if not report.infrastructure_certified:
        raise CiboCapitalManagementError(
            "USD60 capability infrastructure exam is not PASS"
        )
    if qualified_at.tzinfo is None or qualified_at.utcoffset() is None:
        raise CiboCapitalManagementError(
            "USD60 capability certification qualified_at must be timezone-aware"
        )
    if qualified_at < report.replay_started_at:
        raise CiboCapitalManagementError(
            "USD60 capability certification chronology drift"
        )
    if any(
        (
            report.scientific_freshness_claimed,
            report.fresh_oos_generalization_claimed,
            report.broker_mutation_performed,
            report.live_authorized,
            report.real_capital_authorized,
            report.production_authorized,
            report.merge_authorized,
        )
    ):
        raise CiboCapitalManagementError(
            "USD60 capability report is governance-contaminated"
        )

    dual = assess_cibo_usd60_dual_objective_exam(report)
    if dual.status is not CiboUsd60DualObjectiveStatus.PASS:
        raise CiboCapitalManagementError(
            "USD60 capability certification requires strict dual-objective PASS"
        )
    return CiboUsd60CapabilityCertificationReceipt(
        receipt_id=CAPABILITY_CERTIFICATION_RECEIPT_ID,
        certification_scope=CAPABILITY_CERTIFICATION_SCOPE,
        evidence_class=CAPABILITY_EVIDENCE_CLASS,
        integrated_git_sha=integrated_git_sha,
        workflow_run_id=workflow_run_id,
        candidate_id=report.candidate_id,
        source_batch_sha256=report.source_batch_sha256,
        capability_report_sha256=report.fingerprint(),
        dual_objective_report_sha256=_sha256(dual),
        capability_policy_identity_sha256=_capability_policy_identity(
            integrated_git_sha=integrated_git_sha,
        ),
        qualified_at=qualified_at,
        dual_objective_status=dual.status.value,
        usd60_survival_passed=dual.survival.passed,
        maximum_capability_passed=dual.maximum_capability.passed,
    )


def assess_cibo_capability_economic_certification(
    receipt: CiboUsd60CapabilityCertificationReceipt,
) -> CiboCapabilityEconomicCertificationDecision:
    """Promote the bounded capability PASS to economic certification only."""

    if not isinstance(receipt, CiboUsd60CapabilityCertificationReceipt):
        raise CiboCapitalManagementError(
            "capability economic certification requires canonical receipt"
        )
    return CiboCapabilityEconomicCertificationDecision(
        status=CiboEconomicCertificationStatus.CERTIFIED,
        certification_basis=DUAL_OBJECTIVE_EXAM_ID,
        certification_scope=receipt.certification_scope,
        evidence_class=receipt.evidence_class,
        candidate_id=receipt.candidate_id,
        capability_policy_identity_sha256=(
            receipt.capability_policy_identity_sha256
        ),
        qualification_artifact_sha256=receipt.fingerprint(),
        blockers=(),
    )
