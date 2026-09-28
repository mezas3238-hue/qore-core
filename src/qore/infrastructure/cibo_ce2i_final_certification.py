"""Final economic-certification gate for CIBO CMA + CE2I.

The gate can certify only the frozen policy's economic evidence chain. It never
grants DEMO, LIVE, real-capital, execution, Risk or merge authority.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from hashlib import sha256

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_phase20_policy_candidate import (
    FROZEN_PHASE20_POLICY_CANDIDATE,
)
from qore.infrastructure.cibo_ce2i_phase20_qualification_plan import (
    FROZEN_PHASE20D_QUALIFICATION_PLAN,
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
_SHA1_RE = re.compile(r"^[0-9a-f]{40}$")
_PHASE22_ARTIFACT_SCHEMA = "qore.cibo.phase22.holdout-qualification.v1"


def _artifact_decimal(payload: dict[str, object], key: str) -> Decimal:
    try:
        value = Decimal(str(payload[key]))
    except (KeyError, InvalidOperation, ValueError) as error:
        raise CiboCapitalManagementError(
            f"final certification Phase22 metric invalid: {key}"
        ) from error
    if not value.is_finite():
        raise CiboCapitalManagementError(
            f"final certification Phase22 metric non-finite: {key}"
        )
    return value


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
    qualification_artifact_json: str
    validator_git_sha: str
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
        if _SHA1_RE.fullmatch(self.validator_git_sha) is None:
            raise CiboCapitalManagementError(
                "final certification validator Git SHA must be lowercase 40-hex"
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
        try:
            artifact = json.loads(self.qualification_artifact_json)
        except json.JSONDecodeError as error:
            raise CiboCapitalManagementError(
                "final certification Phase22 artifact is invalid JSON"
            ) from error
        if not isinstance(artifact, dict):
            raise CiboCapitalManagementError(
                "final certification Phase22 artifact must be object"
            )
        expected_json = json.dumps(
            artifact,
            indent=2,
            sort_keys=True,
        ) + "\n"
        if expected_json != self.qualification_artifact_json:
            raise CiboCapitalManagementError(
                "final certification Phase22 artifact must use canonical file JSON"
            )
        digest = (
            "sha256:"
            + sha256(self.qualification_artifact_json.encode("utf-8")).hexdigest()
        )
        if digest != self.qualification_artifact_sha256:
            raise CiboCapitalManagementError(
                "final certification Phase22 artifact digest mismatch"
            )
        expected = {
            "schema": _PHASE22_ARTIFACT_SCHEMA,
            "status": "PASS",
            "candidate_id": self.candidate_id,
            "candidate_parameter_sha256": self.candidate_parameter_sha256,
            "phase21_manifest_sha256": self.phase21_manifest_sha256,
            "phase22_plan_id": self.phase22_plan_id,
            "phase22_plan_sha256": self.phase22_plan_sha256,
            "holdout_evidence_store_sha256": self.holdout_evidence_store_sha256,
            "holdout_policy_store_sha256": self.holdout_policy_store_sha256,
            "validator_git_sha": self.validator_git_sha,
            "qualified_at": self.qualified_at.isoformat(),
            "evidence_class": self.evidence_class,
            "lineage_valid": True,
            "economic_holdout_passed": True,
        }
        for key, value in expected.items():
            if artifact.get(key) != value:
                raise CiboCapitalManagementError(
                    f"final certification Phase22 artifact field mismatch: {key}"
                )
        if artifact.get("failures") != []:
            raise CiboCapitalManagementError(
                "final certification Phase22 artifact has failures"
            )
        lineage = artifact.get("lineage")
        if not isinstance(lineage, dict):
            raise CiboCapitalManagementError(
                "final certification Phase22 lineage artifact missing"
            )
        plan20 = FROZEN_PHASE20D_QUALIFICATION_PLAN
        if (
            type(lineage.get("decision_epochs")) is not int
            or lineage.get("decision_epochs") < plan20.minimum_decision_epochs
            or lineage.get("policy_decisions") != lineage.get("decision_epochs")
            or type(lineage.get("outcomes")) is not int
            or lineage.get("outcomes") < plan20.minimum_candidate_outcomes
        ):
            raise CiboCapitalManagementError(
                "final certification Phase22 holdout population incomplete"
            )
        collector_shas = lineage.get("collector_git_shas")
        if (
            not isinstance(collector_shas, list)
            or len(collector_shas) != 1
            or _SHA1_RE.fullmatch(str(collector_shas[0])) is None
        ):
            raise CiboCapitalManagementError(
                "final certification Phase22 collector lineage incomplete"
            )
        economic = artifact.get("economic")
        if (
            not isinstance(economic, dict)
            or economic.get("status") != "PASS"
            or economic.get("failures") != []
        ):
            raise CiboCapitalManagementError(
                "final certification Phase22 economic artifact is not PASS"
            )
        policy_net = _artifact_decimal(economic, "policy_net_delta_usd")
        baseline_net = _artifact_decimal(economic, "baseline_net_delta_usd")
        policy_dd = _artifact_decimal(
            economic, "policy_settlement_cash_drawdown_usd"
        )
        baseline_dd = _artifact_decimal(
            economic, "baseline_settlement_cash_drawdown_usd"
        )
        policy_productivity = _artifact_decimal(
            economic, "policy_capital_productivity"
        )
        baseline_productivity = _artifact_decimal(
            economic, "baseline_capital_productivity"
        )
        if (
            policy_net <= 0
            or policy_net < baseline_net
            or policy_dd > baseline_dd
            or policy_productivity <= baseline_productivity
        ):
            raise CiboCapitalManagementError(
                "final certification Phase22 economic hard gates not demonstrated"
            )
        for key, minimum in (
            (
                "policy_selected_outcome_coverage",
                plan20.required_selected_outcome_coverage,
            ),
            (
                "baseline_selected_outcome_coverage",
                plan20.required_baseline_selected_outcome_coverage,
            ),
            (
                "candidate_outcome_coverage",
                plan20.minimum_candidate_outcome_coverage,
            ),
        ):
            if _artifact_decimal(economic, key) < minimum:
                raise CiboCapitalManagementError(
                    f"final certification Phase22 coverage not met: {key}"
                )
        governance = artifact.get("governance")
        if not isinstance(governance, dict) or any(
            governance.get(key) is not False
            for key in (
                "synthetic_evidence_used",
                "holdout_mining_used",
                "outcome_aware_refit",
                "qualification_population_reused",
            )
        ):
            raise CiboCapitalManagementError(
                "final certification Phase22 artifact governance contamination"
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
    validator_git_sha: str,
    qualified_at: datetime,
) -> Phase22QualificationReceipt:
    if not report.economically_certified:
        raise CiboCapitalManagementError(
            "cannot build Phase22 receipt without economic holdout PASS"
        )
    for name, value in (
        ("holdout_evidence_store_sha256", holdout_evidence_store_sha256),
        ("holdout_policy_store_sha256", holdout_policy_store_sha256),
    ):
        if _SHA256_RE.fullmatch(value) is None:
            raise CiboCapitalManagementError(
                f"final certification {name} must be canonical sha256"
            )
    if _SHA1_RE.fullmatch(validator_git_sha) is None:
        raise CiboCapitalManagementError(
            "final certification validator Git SHA must be lowercase 40-hex"
        )
    if qualified_at.tzinfo is None or qualified_at.utcoffset() is None:
        raise CiboCapitalManagementError(
            "final certification qualified_at must be timezone-aware"
        )
    economic = report.economic_report
    assert economic is not None
    artifact = {
        "schema": _PHASE22_ARTIFACT_SCHEMA,
        "status": report.status.value,
        "candidate_id": phase21_manifest.candidate_id,
        "candidate_parameter_sha256": (
            phase21_manifest.candidate_parameter_sha256
        ),
        "phase21_manifest_sha256": phase21_manifest.manifest_sha256(),
        "phase22_plan_id": report.plan_id,
        "phase22_plan_sha256": report.plan_sha256,
        "holdout_evidence_store_sha256": holdout_evidence_store_sha256,
        "holdout_policy_store_sha256": holdout_policy_store_sha256,
        "validator_git_sha": validator_git_sha,
        "qualified_at": qualified_at.isoformat(),
        "evidence_class": "FORWARD_EMPIRICAL_HOLDOUT",
        "lineage_valid": report.lineage.lineage_valid,
        "economic_holdout_passed": report.economically_certified,
        "lineage": {
            "decision_epochs": report.lineage.decision_epochs,
            "policy_decisions": report.lineage.policy_decisions,
            "outcomes": report.lineage.outcomes,
            "collector_git_shas": list(report.lineage.collector_git_shas),
            "earliest_decision_at": (
                None
                if report.lineage.earliest_decision_at is None
                else report.lineage.earliest_decision_at.isoformat()
            ),
            "latest_decision_at": (
                None
                if report.lineage.latest_decision_at is None
                else report.lineage.latest_decision_at.isoformat()
            ),
        },
        "economic": {
            "status": economic.status.value,
            "failures": list(economic.failures),
            "policy_net_delta_usd": format(
                economic.policy_net_delta_usd, "f"
            ),
            "baseline_net_delta_usd": format(
                economic.baseline_net_delta_usd, "f"
            ),
            "policy_settlement_cash_drawdown_usd": format(
                economic.policy_settlement_cash_drawdown_usd, "f"
            ),
            "baseline_settlement_cash_drawdown_usd": format(
                economic.baseline_settlement_cash_drawdown_usd, "f"
            ),
            "policy_capital_productivity": format(
                economic.policy_capital_productivity, "f"
            ),
            "baseline_capital_productivity": format(
                economic.baseline_capital_productivity, "f"
            ),
            "policy_selected_outcome_coverage": format(
                economic.policy_selected_outcome_coverage, "f"
            ),
            "baseline_selected_outcome_coverage": format(
                economic.baseline_selected_outcome_coverage, "f"
            ),
            "candidate_outcome_coverage": format(
                economic.candidate_outcome_coverage, "f"
            ),
        },
        "failures": list(report.failures),
        "governance": {
            "synthetic_evidence_used": False,
            "holdout_mining_used": False,
            "outcome_aware_refit": False,
            "qualification_population_reused": False,
        },
    }
    artifact_json = json.dumps(
        artifact,
        indent=2,
        sort_keys=True,
    ) + "\n"
    artifact_sha256 = (
        "sha256:" + sha256(artifact_json.encode("utf-8")).hexdigest()
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
        qualification_artifact_sha256=artifact_sha256,
        qualification_artifact_json=artifact_json,
        validator_git_sha=validator_git_sha,
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
