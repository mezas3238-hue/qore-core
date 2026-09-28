"""Fail-closed Phase 21 policy-freeze contract for CIBO.

Phase 21 may freeze the CIBO policy only after the frozen Phase20 candidate
passes fresh-forward qualification and the required empirical validations.
This module grants no DEMO, LIVE, execution, Risk, merge or real-capital
authority; it only creates a cryptographically bound research freeze manifest.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from hashlib import sha256
from typing import Any

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_phase20_policy_candidate import (
    FROZEN_PHASE20_POLICY_CANDIDATE,
)
from qore.infrastructure.cibo_ce2i_phase20_qualification_plan import (
    FROZEN_PHASE20D_QUALIFICATION_PLAN,
    phase20d_qualification_plan_sha256,
)

_SHA1_RE = re.compile(r"^[0-9a-f]{40}$")
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


class Phase21EmpiricalValidationKind(StrEnum):
    CAPITAL_STATE_MONTE_CARLO = "CAPITAL_STATE_MONTE_CARLO"
    PROVIDER_STRESS = "PROVIDER_STRESS"
    INTERACTION_ABLATION = "INTERACTION_ABLATION"


_REQUIRED_EMPIRICAL_VALIDATIONS = frozenset(Phase21EmpiricalValidationKind)
_EMPIRICAL_REPORT_SCHEMA = "qore.cibo.phase21.empirical-validation.v1"
_EMPIRICAL_PLAN_ID = "CIBO_PHASE21_EMPIRICAL_VALIDATION_LINEAGE_V1"


def _empirical_plan_payload() -> dict[str, object]:
    return {
        "plan_id": _EMPIRICAL_PLAN_ID,
        "required_kinds": sorted(
            item.value for item in _REQUIRED_EMPIRICAL_VALIDATIONS
        ),
        "required_evidence_class": "FORWARD_EMPIRICAL",
        "bind_exact_phase20d_qualification_population": True,
        "synthetic_evidence_allowed": False,
        "phase19j_burned_validation_reused": False,
        "outcome_aware_refit_allowed": False,
        "historical_replay_substitution_allowed": False,
        "capital_state_monte_carlo": {
            "minimum_simulations": 1000,
            "required_policy_capacity_breach_paths": 0,
            "required_baseline_capacity_breach_paths": 0,
            "policy_p95_drawdown_must_not_exceed_baseline": True,
            "policy_median_ending_delta_must_not_be_below_baseline": True,
        },
        "provider_stress": {
            "required_scenario_count": 9,
            "required_policy_constraint_bypasses": 0,
            "required_baseline_constraint_bypasses": 0,
            "policy_worst_case_net_delta_must_not_be_below_baseline": True,
            "policy_failure_incidence_must_not_exceed_baseline": True,
        },
        "interaction_ablation": {
            "minimum_ablation_cases": 3,
            "required_unsafe_interaction_count": 0,
            "required_population_mismatch_count": 0,
            "full_policy_must_not_be_pareto_dominated_by_ablation": True,
        },
    }


def phase21_empirical_validation_plan_sha256() -> str:
    raw = json.dumps(
        _empirical_plan_payload(),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return f"sha256:{sha256(raw).hexdigest()}"


def phase21_empirical_population_sha256(
    *,
    evidence_store_sha256: str,
    policy_store_sha256: str,
    qualification_artifact_sha256: str,
) -> str:
    for name, value in (
        ("evidence_store_sha256", evidence_store_sha256),
        ("policy_store_sha256", policy_store_sha256),
        ("qualification_artifact_sha256", qualification_artifact_sha256),
    ):
        _require_sha256(value, name)
    raw = json.dumps(
        {
            "evidence_store_sha256": evidence_store_sha256,
            "policy_store_sha256": policy_store_sha256,
            "qualification_artifact_sha256": qualification_artifact_sha256,
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return f"sha256:{sha256(raw).hexdigest()}"


def _canonical_report_json(payload: dict[str, Any]) -> str:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )


def _canonical_report_sha256(payload: dict[str, Any]) -> str:
    raw = _canonical_report_json(payload).encode("utf-8")
    return f"sha256:{sha256(raw).hexdigest()}"


def _metric_decimal(
    payload: dict[str, Any],
    key: str,
) -> Decimal:
    if key not in payload:
        raise CiboCapitalManagementError(
            f"Phase21 empirical validation metric missing: {key}"
        )
    try:
        value = Decimal(str(payload[key]))
    except (InvalidOperation, ValueError) as error:
        raise CiboCapitalManagementError(
            f"Phase21 empirical validation metric invalid: {key}"
        ) from error
    if not value.is_finite():
        raise CiboCapitalManagementError(
            f"Phase21 empirical validation metric non-finite: {key}"
        )
    return value


def _metric_int(
    payload: dict[str, Any],
    key: str,
) -> int:
    value = payload.get(key)
    if type(value) is not int:
        raise CiboCapitalManagementError(
            f"Phase21 empirical validation metric must be int: {key}"
        )
    return value


def _metric_bool(
    payload: dict[str, Any],
    key: str,
) -> bool:
    value = payload.get(key)
    if type(value) is not bool:
        raise CiboCapitalManagementError(
            f"Phase21 empirical validation metric must be bool: {key}"
        )
    return value


def _validate_empirical_validation_payload(
    *,
    kind: Phase21EmpiricalValidationKind,
    payload: dict[str, Any],
) -> None:
    if kind is Phase21EmpiricalValidationKind.CAPITAL_STATE_MONTE_CARLO:
        simulations = _metric_int(payload, "simulation_count")
        policy_breaches = _metric_int(
            payload, "policy_capacity_breach_paths"
        )
        baseline_breaches = _metric_int(
            payload, "baseline_capacity_breach_paths"
        )
        policy_p95 = _metric_decimal(payload, "policy_p95_drawdown_usd")
        baseline_p95 = _metric_decimal(
            payload, "baseline_p95_drawdown_usd"
        )
        policy_median = _metric_decimal(
            payload, "policy_median_ending_delta_usd"
        )
        baseline_median = _metric_decimal(
            payload, "baseline_median_ending_delta_usd"
        )
        if (
            simulations < 1000
            or policy_breaches != 0
            or baseline_breaches != 0
            or policy_p95 > baseline_p95
            or policy_median < baseline_median
        ):
            raise CiboCapitalManagementError(
                "Phase21 empirical capital-state Monte Carlo did not PASS"
            )
        return

    if kind is Phase21EmpiricalValidationKind.PROVIDER_STRESS:
        scenario_count = _metric_int(payload, "scenario_count")
        policy_bypasses = _metric_int(
            payload, "policy_constraint_bypasses"
        )
        baseline_bypasses = _metric_int(
            payload, "baseline_constraint_bypasses"
        )
        policy_worst = _metric_decimal(
            payload, "policy_worst_case_net_delta_usd"
        )
        baseline_worst = _metric_decimal(
            payload, "baseline_worst_case_net_delta_usd"
        )
        policy_fail = _metric_decimal(
            payload, "policy_provider_failure_incidence"
        )
        baseline_fail = _metric_decimal(
            payload, "baseline_provider_failure_incidence"
        )
        if (
            scenario_count != 9
            or policy_bypasses != 0
            or baseline_bypasses != 0
            or policy_worst < baseline_worst
            or policy_fail > baseline_fail
            or policy_fail < 0
            or baseline_fail < 0
            or policy_fail > 1
            or baseline_fail > 1
        ):
            raise CiboCapitalManagementError(
                "Phase21 empirical provider stress did not PASS"
            )
        return

    if kind is Phase21EmpiricalValidationKind.INTERACTION_ABLATION:
        case_count = _metric_int(payload, "ablation_case_count")
        unsafe = _metric_int(payload, "unsafe_interaction_count")
        population_mismatch = _metric_int(
            payload, "population_mismatch_count"
        )
        dominated = _metric_bool(
            payload, "full_policy_pareto_dominated_by_ablation"
        )
        if (
            case_count < 3
            or unsafe != 0
            or population_mismatch != 0
            or dominated
        ):
            raise CiboCapitalManagementError(
                "Phase21 empirical interaction ablation did not PASS"
            )
        return

    raise CiboCapitalManagementError(
        "Phase21 empirical validation kind is unsupported"
    )




@dataclass(frozen=True, slots=True)
class Phase21QualificationReceipt:
    candidate_id: str
    candidate_parameter_sha256: str
    plan_id: str
    plan_sha256: str
    evidence_store_sha256: str
    policy_store_sha256: str
    qualification_artifact_sha256: str
    qualification_git_sha: str
    qualification_artifact_json: str
    qualified_at: datetime
    passed: bool

    def __post_init__(self) -> None:
        if self.candidate_id != FROZEN_PHASE20_POLICY_CANDIDATE.candidate_id:
            raise CiboCapitalManagementError(
                "Phase21 qualification candidate identity drift"
            )
        if (
            self.candidate_parameter_sha256
            != FROZEN_PHASE20_POLICY_CANDIDATE.parameter_sha256()
        ):
            raise CiboCapitalManagementError(
                "Phase21 qualification parameter digest drift"
            )
        if self.plan_id != FROZEN_PHASE20D_QUALIFICATION_PLAN.plan_id:
            raise CiboCapitalManagementError(
                "Phase21 qualification plan identity drift"
            )
        if self.plan_sha256 != phase20d_qualification_plan_sha256():
            raise CiboCapitalManagementError(
                "Phase21 qualification plan digest drift"
            )
        for name in (
            "evidence_store_sha256",
            "policy_store_sha256",
            "qualification_artifact_sha256",
        ):
            _require_sha256(getattr(self, name), name)
        if _SHA1_RE.fullmatch(self.qualification_git_sha) is None:
            raise CiboCapitalManagementError(
                "Phase21 qualification Git SHA must be lowercase 40-hex"
            )
        _require_aware(self.qualified_at, "qualified_at")
        if not self.passed:
            raise CiboCapitalManagementError(
                "Phase21 requires Phase20D PASS qualification"
            )
        try:
            report = json.loads(self.qualification_artifact_json)
        except json.JSONDecodeError as error:
            raise CiboCapitalManagementError(
                "Phase21 qualification artifact is invalid JSON"
            ) from error
        if not isinstance(report, dict):
            raise CiboCapitalManagementError(
                "Phase21 qualification artifact must be object"
            )
        expected_json = json.dumps(
            report,
            indent=2,
            sort_keys=True,
        ) + "\n"
        if expected_json != self.qualification_artifact_json:
            raise CiboCapitalManagementError(
                "Phase21 qualification artifact must use canonical file JSON"
            )
        digest = (
            "sha256:"
            + sha256(self.qualification_artifact_json.encode("utf-8")).hexdigest()
        )
        if digest != self.qualification_artifact_sha256:
            raise CiboCapitalManagementError(
                "Phase21 qualification artifact digest mismatch"
            )
        if report.get("schema") != "qore.cibo.phase20d.v2-qualification.v5":
            raise CiboCapitalManagementError(
                "Phase21 qualification schema mismatch"
            )
        if report.get("status") != "PASS":
            raise CiboCapitalManagementError(
                "Phase21 qualification artifact is not PASS"
            )
        if report.get("candidate_id") != self.candidate_id:
            raise CiboCapitalManagementError(
                "Phase21 qualification artifact candidate mismatch"
            )
        if (
            report.get("plan_id") != self.plan_id
            or report.get("plan_sha256") != self.plan_sha256
        ):
            raise CiboCapitalManagementError(
                "Phase21 qualification artifact plan mismatch"
            )
        if report.get("failures_or_pending_reasons") != []:
            raise CiboCapitalManagementError(
                "Phase21 qualification artifact has failures"
            )
        readiness = report.get("readiness")
        if not isinstance(readiness, dict) or readiness.get("ready") is not True:
            raise CiboCapitalManagementError(
                "Phase21 qualification artifact is not forward-ready"
            )
        plan = FROZEN_PHASE20D_QUALIFICATION_PLAN
        required_counts = (
            ("decision_epochs", plan.minimum_decision_epochs),
            ("candidate_outcomes", plan.minimum_candidate_outcomes),
            ("selected_outcomes", plan.minimum_selected_outcomes),
            ("calendar_span_days", plan.minimum_calendar_span_days),
            ("distinct_trading_days", plan.minimum_distinct_trading_days),
            ("represented_lineages", plan.minimum_global_lineages),
            ("minimum_outcomes_any_lineage", plan.minimum_outcomes_per_lineage),
            (
                "minimum_fold_candidate_outcomes",
                plan.minimum_fold_candidate_outcomes,
            ),
            ("minimum_fold_lineages", plan.minimum_fold_lineages),
        )
        for key, minimum in required_counts:
            value = readiness.get(key)
            if type(value) is not int or value < minimum:
                raise CiboCapitalManagementError(
                    f"Phase21 qualification readiness threshold not met: {key}"
                )
        if (
            readiness.get("missing_policy_decisions") != 0
            or readiness.get("pre_freeze_decisions") != 0
        ):
            raise CiboCapitalManagementError(
                "Phase21 qualification readiness lineage contamination"
            )
        for key, coverage_minimum in (
            (
                "candidate_outcome_coverage",
                plan.minimum_candidate_outcome_coverage,
            ),
            (
                "selected_outcome_coverage",
                plan.required_selected_outcome_coverage,
            ),
        ):
            try:
                coverage_value = Decimal(str(readiness.get(key)))
            except (InvalidOperation, ValueError) as error:
                raise CiboCapitalManagementError(
                    f"Phase21 qualification readiness decimal invalid: {key}"
                ) from error
            if (
                not coverage_value.is_finite()
                or coverage_value < coverage_minimum
            ):
                raise CiboCapitalManagementError(
                    f"Phase21 qualification readiness coverage not met: {key}"
                )
        economics = report.get("economics")
        if not isinstance(economics, dict):
            raise CiboCapitalManagementError(
                "Phase21 qualification economics missing"
            )
        policy_net = _metric_decimal(
            economics, "policy_net_delta_usd"
        )
        baseline_net = _metric_decimal(
            economics, "baseline_net_delta_usd"
        )
        policy_dd = _metric_decimal(
            economics, "policy_settlement_cash_drawdown_usd"
        )
        baseline_dd = _metric_decimal(
            economics, "baseline_settlement_cash_drawdown_usd"
        )
        policy_productivity = _metric_decimal(
            economics, "policy_capital_productivity"
        )
        baseline_productivity = _metric_decimal(
            economics, "baseline_capital_productivity"
        )
        if (
            policy_net <= 0
            or policy_net < baseline_net
            or policy_dd > baseline_dd
            or policy_productivity <= baseline_productivity
        ):
            raise CiboCapitalManagementError(
                "Phase21 qualification economic hard gates not demonstrated"
            )
        for key, coverage_minimum in (
            (
                "policy_selected_outcome_coverage",
                plan.required_selected_outcome_coverage,
            ),
            (
                "baseline_selected_outcome_coverage",
                plan.required_baseline_selected_outcome_coverage,
            ),
            (
                "candidate_outcome_coverage",
                plan.minimum_candidate_outcome_coverage,
            ),
        ):
            coverage_value = _metric_decimal(economics, key)
            if coverage_value < coverage_minimum:
                raise CiboCapitalManagementError(
                    f"Phase21 qualification economic coverage not met: {key}"
                )
        folds = report.get("folds")
        if not isinstance(folds, list) or len(folds) != plan.fold_count:
            raise CiboCapitalManagementError(
                "Phase21 qualification temporal folds incomplete"
            )
        for fold in folds:
            if not isinstance(fold, dict):
                raise CiboCapitalManagementError(
                    "Phase21 qualification fold must be object"
                )
            if _metric_decimal(fold, "policy_net_delta_usd") <= 0:
                raise CiboCapitalManagementError(
                    "Phase21 qualification fold policy delta not positive"
                )
        dataset = report.get("dataset")
        if not isinstance(dataset, list) or not dataset:
            raise CiboCapitalManagementError(
                "Phase21 qualification dataset missing"
            )
        provenance = report.get("provenance")
        if not isinstance(provenance, dict):
            raise CiboCapitalManagementError(
                "Phase21 qualification provenance missing"
            )
        if (
            provenance.get("evidence_store_sha256")
            != self.evidence_store_sha256
            or provenance.get("policy_store_sha256")
            != self.policy_store_sha256
        ):
            raise CiboCapitalManagementError(
                "Phase21 qualification store lineage mismatch"
            )
        decision_epochs_value = readiness.get("decision_epochs")
        candidate_outcomes_value = readiness.get("candidate_outcomes")
        outcome_count_value = provenance.get("outcome_count")
        if (
            type(decision_epochs_value) is not int
            or type(candidate_outcomes_value) is not int
            or type(outcome_count_value) is not int
            or provenance.get("decision_count") != decision_epochs_value
            or provenance.get("policy_decision_count") != decision_epochs_value
            or outcome_count_value < candidate_outcomes_value
        ):
            raise CiboCapitalManagementError(
                "Phase21 qualification provenance population mismatch"
            )
        if provenance.get("git_sha") != self.qualification_git_sha:
            raise CiboCapitalManagementError(
                "Phase21 qualification Git lineage mismatch"
            )
        collector_shas = provenance.get("collector_git_shas")
        if (
            provenance.get("missing_collector_git_sha_decisions") != 0
            or not isinstance(collector_shas, list)
            or len(collector_shas) != 1
            or _SHA1_RE.fullmatch(str(collector_shas[0])) is None
        ):
            raise CiboCapitalManagementError(
                "Phase21 qualification collector lineage incomplete"
            )
        gate = report.get("phase20d_gate")
        if (
            not isinstance(gate, dict)
            or gate.get("status") != "PASS"
            or gate.get("eligible_for_phase21") is not True
            or gate.get("blockers") != []
            or gate.get("requires_exact_evidence_and_policy_digests") is not True
            or gate.get("requires_single_collector_git_sha") is not True
        ):
            raise CiboCapitalManagementError(
                "Phase21 qualification gate is not eligible"
            )
        final_gate = report.get("final_certification")
        if (
            not isinstance(final_gate, dict)
            or final_gate.get("status") != "PENDING_PHASE21_PHASE22"
            or final_gate.get("eligible") is not False
            or final_gate.get("phase20d_eligible_for_phase21") is not True
        ):
            raise CiboCapitalManagementError(
                "Phase21 qualification artifact final gate drift"
            )


def build_phase21_qualification_receipt(
    *,
    qualification_artifact_json: str,
    qualified_at: datetime,
) -> Phase21QualificationReceipt:
    try:
        report = json.loads(qualification_artifact_json)
    except json.JSONDecodeError as error:
        raise CiboCapitalManagementError(
            "Phase21 qualification artifact is invalid JSON"
        ) from error
    if not isinstance(report, dict):
        raise CiboCapitalManagementError(
            "Phase21 qualification artifact must be object"
        )
    provenance = report.get("provenance")
    if not isinstance(provenance, dict):
        raise CiboCapitalManagementError(
            "Phase21 qualification provenance missing"
        )
    candidate = FROZEN_PHASE20_POLICY_CANDIDATE
    return Phase21QualificationReceipt(
        candidate_id=str(report.get("candidate_id", "")),
        candidate_parameter_sha256=candidate.parameter_sha256(),
        plan_id=str(report.get("plan_id", "")),
        plan_sha256=str(report.get("plan_sha256", "")),
        evidence_store_sha256=str(
            provenance.get("evidence_store_sha256", "")
        ),
        policy_store_sha256=str(
            provenance.get("policy_store_sha256", "")
        ),
        qualification_artifact_sha256=(
            "sha256:"
            + sha256(qualification_artifact_json.encode("utf-8")).hexdigest()
        ),
        qualification_git_sha=str(provenance.get("git_sha", "")),
        qualification_artifact_json=qualification_artifact_json,
        qualified_at=qualified_at,
        passed=report.get("status") == "PASS",
    )


@dataclass(frozen=True, slots=True)
class Phase21EmpiricalValidationReceipt:
    kind: Phase21EmpiricalValidationKind
    candidate_id: str
    candidate_parameter_sha256: str
    qualification_artifact_sha256: str
    evidence_store_sha256: str
    policy_store_sha256: str
    source_population_sha256: str
    validation_plan_sha256: str
    validator_git_sha: str
    evidence_class: str
    artifact_sha256: str
    canonical_report_json: str
    observed_at: datetime
    passed: bool

    def __post_init__(self) -> None:
        if not isinstance(self.kind, Phase21EmpiricalValidationKind):
            raise CiboCapitalManagementError(
                "Phase21 empirical validation kind is invalid"
            )
        if self.candidate_id != FROZEN_PHASE20_POLICY_CANDIDATE.candidate_id:
            raise CiboCapitalManagementError(
                "Phase21 empirical candidate identity drift"
            )
        if (
            self.candidate_parameter_sha256
            != FROZEN_PHASE20_POLICY_CANDIDATE.parameter_sha256()
        ):
            raise CiboCapitalManagementError(
                "Phase21 empirical parameter digest drift"
            )
        for name in (
            "qualification_artifact_sha256",
            "evidence_store_sha256",
            "policy_store_sha256",
            "source_population_sha256",
            "validation_plan_sha256",
            "artifact_sha256",
        ):
            _require_sha256(getattr(self, name), name)
        if _SHA1_RE.fullmatch(self.validator_git_sha) is None:
            raise CiboCapitalManagementError(
                "Phase21 empirical validator Git SHA must be lowercase 40-hex"
            )
        _require_aware(self.observed_at, "observed_at")
        if self.evidence_class != "FORWARD_EMPIRICAL":
            raise CiboCapitalManagementError(
                "Phase21 empirical receipt must be FORWARD_EMPIRICAL"
            )
        if not self.passed:
            raise CiboCapitalManagementError(
                "Phase21 empirical validation must PASS"
            )
        expected_population = phase21_empirical_population_sha256(
            evidence_store_sha256=self.evidence_store_sha256,
            policy_store_sha256=self.policy_store_sha256,
            qualification_artifact_sha256=self.qualification_artifact_sha256,
        )
        if self.source_population_sha256 != expected_population:
            raise CiboCapitalManagementError(
                "Phase21 empirical source population digest mismatch"
            )
        if self.validation_plan_sha256 != (
            phase21_empirical_validation_plan_sha256()
        ):
            raise CiboCapitalManagementError(
                "Phase21 empirical validation plan digest drift"
            )
        try:
            report = json.loads(self.canonical_report_json)
        except json.JSONDecodeError as error:
            raise CiboCapitalManagementError(
                "Phase21 empirical canonical report is invalid JSON"
            ) from error
        if not isinstance(report, dict):
            raise CiboCapitalManagementError(
                "Phase21 empirical canonical report must be object"
            )
        canonical = _canonical_report_json(report)
        if canonical != self.canonical_report_json:
            raise CiboCapitalManagementError(
                "Phase21 empirical report must use canonical JSON"
            )
        if _canonical_report_sha256(report) != self.artifact_sha256:
            raise CiboCapitalManagementError(
                "Phase21 empirical artifact digest/report mismatch"
            )
        expected = {
            "schema": _EMPIRICAL_REPORT_SCHEMA,
            "kind": self.kind.value,
            "candidate_id": self.candidate_id,
            "candidate_parameter_sha256": self.candidate_parameter_sha256,
            "qualification_artifact_sha256": (
                self.qualification_artifact_sha256
            ),
            "evidence_store_sha256": self.evidence_store_sha256,
            "policy_store_sha256": self.policy_store_sha256,
            "source_population_sha256": self.source_population_sha256,
            "validation_plan_sha256": self.validation_plan_sha256,
            "validator_git_sha": self.validator_git_sha,
            "evidence_class": self.evidence_class,
            "observed_at": self.observed_at.isoformat(),
            "passed": self.passed,
        }
        for key, value in expected.items():
            if report.get(key) != value:
                raise CiboCapitalManagementError(
                    f"Phase21 empirical report field mismatch: {key}"
                )
        failures = report.get("failures")
        if failures != []:
            raise CiboCapitalManagementError(
                "Phase21 empirical PASS report must have zero failures"
            )
        governance = report.get("governance")
        if not isinstance(governance, dict):
            raise CiboCapitalManagementError(
                "Phase21 empirical governance block is required"
            )
        forbidden = (
            "synthetic_evidence_used",
            "phase19j_burned_validation_reused",
            "outcome_aware_refit",
            "historical_replay_substituted_for_forward",
        )
        if any(governance.get(key) is not False for key in forbidden):
            raise CiboCapitalManagementError(
                "Phase21 empirical report governance contamination"
            )


def build_phase21_empirical_validation_receipt(
    *,
    kind: Phase21EmpiricalValidationKind,
    qualification: Phase21QualificationReceipt,
    validator_git_sha: str,
    observed_at: datetime,
    validation_payload: dict[str, Any],
) -> Phase21EmpiricalValidationReceipt:
    if not isinstance(validation_payload, dict):
        raise CiboCapitalManagementError(
            "Phase21 empirical validation payload must be object"
        )
    _validate_empirical_validation_payload(
        kind=kind,
        payload=validation_payload,
    )
    source_population_sha256 = phase21_empirical_population_sha256(
        evidence_store_sha256=qualification.evidence_store_sha256,
        policy_store_sha256=qualification.policy_store_sha256,
        qualification_artifact_sha256=(
            qualification.qualification_artifact_sha256
        ),
    )
    report: dict[str, Any] = {
        "schema": _EMPIRICAL_REPORT_SCHEMA,
        "kind": kind.value,
        "candidate_id": qualification.candidate_id,
        "candidate_parameter_sha256": (
            qualification.candidate_parameter_sha256
        ),
        "qualification_artifact_sha256": (
            qualification.qualification_artifact_sha256
        ),
        "evidence_store_sha256": qualification.evidence_store_sha256,
        "policy_store_sha256": qualification.policy_store_sha256,
        "source_population_sha256": source_population_sha256,
        "validation_plan_sha256": (
            phase21_empirical_validation_plan_sha256()
        ),
        "validator_git_sha": validator_git_sha,
        "evidence_class": "FORWARD_EMPIRICAL",
        "observed_at": observed_at.isoformat(),
        "passed": True,
        "failures": [],
        "validation": validation_payload,
        "governance": {
            "synthetic_evidence_used": False,
            "phase19j_burned_validation_reused": False,
            "outcome_aware_refit": False,
            "historical_replay_substituted_for_forward": False,
        },
    }
    canonical = _canonical_report_json(report)
    return Phase21EmpiricalValidationReceipt(
        kind=kind,
        candidate_id=qualification.candidate_id,
        candidate_parameter_sha256=(
            qualification.candidate_parameter_sha256
        ),
        qualification_artifact_sha256=(
            qualification.qualification_artifact_sha256
        ),
        evidence_store_sha256=qualification.evidence_store_sha256,
        policy_store_sha256=qualification.policy_store_sha256,
        source_population_sha256=source_population_sha256,
        validation_plan_sha256=phase21_empirical_validation_plan_sha256(),
        validator_git_sha=validator_git_sha,
        evidence_class="FORWARD_EMPIRICAL",
        artifact_sha256=_canonical_report_sha256(report),
        canonical_report_json=canonical,
        observed_at=observed_at,
        passed=True,
    )


@dataclass(frozen=True, slots=True)
class Phase21PolicySurfaceDigests:
    state_machine_sha256: str
    tool_registry_sha256: str
    eligibility_sha256: str
    source_ledger_sha256: str
    trader_adapters_sha256: str
    provider_profiles_sha256: str

    def __post_init__(self) -> None:
        for name in (
            "state_machine_sha256",
            "tool_registry_sha256",
            "eligibility_sha256",
            "source_ledger_sha256",
            "trader_adapters_sha256",
            "provider_profiles_sha256",
        ):
            _require_sha256(getattr(self, name), name)

    def payload(self) -> dict[str, str]:
        return {
            "state_machine_sha256": self.state_machine_sha256,
            "tool_registry_sha256": self.tool_registry_sha256,
            "eligibility_sha256": self.eligibility_sha256,
            "source_ledger_sha256": self.source_ledger_sha256,
            "trader_adapters_sha256": self.trader_adapters_sha256,
            "provider_profiles_sha256": self.provider_profiles_sha256,
        }


@dataclass(frozen=True, slots=True)
class Phase21PolicyFreezeManifest:
    candidate_id: str
    candidate_code_sha: str
    candidate_parameter_sha256: str
    qualification: Phase21QualificationReceipt
    empirical_validations: tuple[Phase21EmpiricalValidationReceipt, ...]
    policy_surface: Phase21PolicySurfaceDigests
    frozen_at: datetime
    demo_execution_authorized: bool = False
    live_authorized: bool = False
    real_capital_authorized: bool = False
    merge_authorized: bool = False

    def __post_init__(self) -> None:
        candidate = FROZEN_PHASE20_POLICY_CANDIDATE
        if self.candidate_id != candidate.candidate_id:
            raise CiboCapitalManagementError(
                "Phase21 manifest candidate identity drift"
            )
        if self.candidate_code_sha != candidate.code_sha:
            raise CiboCapitalManagementError(
                "Phase21 manifest code SHA drift"
            )
        if _SHA1_RE.fullmatch(self.candidate_code_sha) is None:
            raise CiboCapitalManagementError(
                "Phase21 manifest code SHA must be lowercase 40-hex"
            )
        if self.candidate_parameter_sha256 != candidate.parameter_sha256():
            raise CiboCapitalManagementError(
                "Phase21 manifest parameter digest drift"
            )
        _require_aware(self.frozen_at, "frozen_at")
        if self.frozen_at <= self.qualification.qualified_at:
            raise CiboCapitalManagementError(
                "Phase21 freeze must follow Phase20D qualification"
            )
        kinds = tuple(item.kind for item in self.empirical_validations)
        if len(kinds) != len(set(kinds)):
            raise CiboCapitalManagementError(
                "Phase21 empirical validation kinds must be unique"
            )
        if frozenset(kinds) != _REQUIRED_EMPIRICAL_VALIDATIONS:
            raise CiboCapitalManagementError(
                "Phase21 requires MC, provider stress and interaction ablation"
            )
        for receipt in self.empirical_validations:
            if (
                receipt.qualification_artifact_sha256
                != self.qualification.qualification_artifact_sha256
            ):
                raise CiboCapitalManagementError(
                    "Phase21 empirical receipt qualification lineage mismatch"
                )
            if (
                receipt.evidence_store_sha256
                != self.qualification.evidence_store_sha256
                or receipt.policy_store_sha256
                != self.qualification.policy_store_sha256
            ):
                raise CiboCapitalManagementError(
                    "Phase21 empirical receipt source population mismatch"
                )
            if receipt.observed_at <= self.qualification.qualified_at:
                raise CiboCapitalManagementError(
                    "Phase21 empirical validation must follow qualification"
                )
            if self.frozen_at <= receipt.observed_at:
                raise CiboCapitalManagementError(
                    "Phase21 freeze must follow empirical validation"
                )
        if (
            self.demo_execution_authorized
            or self.live_authorized
            or self.real_capital_authorized
            or self.merge_authorized
        ):
            raise CiboCapitalManagementError(
                "Phase21 research freeze cannot grant operational authority"
            )

    def canonical_payload(self) -> dict[str, object]:
        validations = sorted(
            self.empirical_validations,
            key=lambda item: item.kind.value,
        )
        return {
            "schema": "qore.cibo.phase21.policy-freeze.v1",
            "candidate_id": self.candidate_id,
            "candidate_code_sha": self.candidate_code_sha,
            "candidate_parameter_sha256": self.candidate_parameter_sha256,
            "qualification": {
                "plan_id": self.qualification.plan_id,
                "plan_sha256": self.qualification.plan_sha256,
                "evidence_store_sha256": (
                    self.qualification.evidence_store_sha256
                ),
                "policy_store_sha256": (
                    self.qualification.policy_store_sha256
                ),
                "qualification_artifact_sha256": (
                    self.qualification.qualification_artifact_sha256
                ),
                "qualification_git_sha": (
                    self.qualification.qualification_git_sha
                ),
                "qualified_at": self.qualification.qualified_at.isoformat(),
            },
            "empirical_validations": [
                {
                    "kind": item.kind.value,
                    "evidence_class": item.evidence_class,
                    "artifact_sha256": item.artifact_sha256,
                    "observed_at": item.observed_at.isoformat(),
                }
                for item in validations
            ],
            "policy_surface": self.policy_surface.payload(),
            "frozen_at": self.frozen_at.isoformat(),
            "governance": {
                "demo_execution_authorized": False,
                "live_authorized": False,
                "real_capital_authorized": False,
                "merge_authorized": False,
            },
        }

    def manifest_sha256(self) -> str:
        raw = json.dumps(
            self.canonical_payload(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
        return f"sha256:{sha256(raw).hexdigest()}"


def build_phase21_policy_freeze(
    *,
    qualification: Phase21QualificationReceipt,
    empirical_validations: tuple[Phase21EmpiricalValidationReceipt, ...],
    policy_surface: Phase21PolicySurfaceDigests,
    frozen_at: datetime,
) -> Phase21PolicyFreezeManifest:
    candidate = FROZEN_PHASE20_POLICY_CANDIDATE
    return Phase21PolicyFreezeManifest(
        candidate_id=candidate.candidate_id,
        candidate_code_sha=candidate.code_sha,
        candidate_parameter_sha256=candidate.parameter_sha256(),
        qualification=qualification,
        empirical_validations=empirical_validations,
        policy_surface=policy_surface,
        frozen_at=frozen_at,
    )


def _require_sha256(value: str, name: str) -> None:
    if _SHA256_RE.fullmatch(value) is None:
        raise CiboCapitalManagementError(
            f"Phase21 {name} must be sha256: plus 64 lowercase hex"
        )


def _require_aware(value: datetime, name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise CiboCapitalManagementError(
            f"Phase21 {name} must be timezone-aware"
        )
