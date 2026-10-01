"""Canonical OOS stress admission for CE2I T08/T09/T12/T13/T18.

These workstreams expose fresh-OOS report objects rather than a shared status
enum. This module consumes those canonical reports directly under each frozen
CIBO adversarial stress kind. It does not synthesize outcomes, normalize a
failure into a pass, or grant runtime/certification authority.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol, TypeVar

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_phase20_t08_oos_ablation import (
    T08NettingOosAblationReport,
)
from qore.infrastructure.cibo_ce2i_phase20_t09_t18_scarcity_utility import (
    Phase20T09T18ScarcityUtilityReport,
)
from qore.infrastructure.cibo_ce2i_phase20_t12_oos_utility import (
    Phase20T12UtilityReport,
)
from qore.infrastructure.cibo_ce2i_phase20_t13_oos_utility import (
    Phase20T13UtilityReport,
)
from qore.infrastructure.cibo_compound_adversarial_stress import (
    CompoundStressKind,
    CompoundStressScenario,
)
from qore.infrastructure.cibo_t09_t18_scarcity_safety_gate import (
    T09T18ScarcityGateReport,
    T09T18ScarcityStatus,
    T09T18ScarcityTool,
)

GATE_ID = "CIBO_CE2I_OOS_MECHANISM_STRESS_ADMISSION_V1"
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_CANONICAL_FOLDS = ("WF1", "WF2", "WF3", "WF4")
_REQUIRED_STRESS_KINDS = tuple(CompoundStressKind)


class _HasStressMeta(Protocol):
    meta: "Ce2iOosStressScenarioMeta"


_TStressEvidence = TypeVar("_TStressEvidence", bound=_HasStressMeta)


class Ce2iOosStressWorkstream(StrEnum):
    T08 = "T08"
    T09 = "T09"
    T12 = "T12"
    T13 = "T13"
    T18 = "T18"


class Ce2iOosStressVerdict(StrEnum):
    STRESS_ROBUST = "STRESS_ROBUST"
    FALSIFIED = "FALSIFIED"


@dataclass(frozen=True, slots=True)
class Ce2iOosStressScenarioMeta:
    scenario: CompoundStressScenario
    stressed_population_sha256: str
    protocol_binding_sha256: str
    scenario_preregistered_before_outcomes: bool
    stress_transform_non_improving: bool

    def __post_init__(self) -> None:
        if not isinstance(self.scenario, CompoundStressScenario):
            raise CiboCapitalManagementError(
                "CE2I OOS stress requires canonical Compound stress scenario"
            )
        _sha(self.stressed_population_sha256, "stressed_population_sha256")
        _sha(self.protocol_binding_sha256, "protocol_binding_sha256")
        if (
            not self.scenario_preregistered_before_outcomes
            or not self.stress_transform_non_improving
        ):
            raise CiboCapitalManagementError(
                "CE2I OOS stress scenario governance drift"
            )


@dataclass(frozen=True, slots=True)
class T08OosStressEvidence:
    meta: Ce2iOosStressScenarioMeta
    report: T08NettingOosAblationReport

    def __post_init__(self) -> None:
        if not isinstance(self.report, T08NettingOosAblationReport):
            raise CiboCapitalManagementError(
                "T08 stress requires canonical OOS ablation report"
            )
        if self.report.required_folds != 4:
            raise CiboCapitalManagementError(
                "T08 stress report must preserve canonical four folds"
            )


@dataclass(frozen=True, slots=True)
class T12OosStressEvidence:
    meta: Ce2iOosStressScenarioMeta
    report: Phase20T12UtilityReport

    def __post_init__(self) -> None:
        if not isinstance(self.report, Phase20T12UtilityReport):
            raise CiboCapitalManagementError(
                "T12 stress requires canonical OOS utility report"
            )


@dataclass(frozen=True, slots=True)
class T13OosStressEvidence:
    meta: Ce2iOosStressScenarioMeta
    report: Phase20T13UtilityReport

    def __post_init__(self) -> None:
        if not isinstance(self.report, Phase20T13UtilityReport):
            raise CiboCapitalManagementError(
                "T13 stress requires canonical OOS utility report"
            )


@dataclass(frozen=True, slots=True)
class T09T18OosStressEvidence:
    meta: Ce2iOosStressScenarioMeta
    tool: T09T18ScarcityTool
    treatment_candidate_id: str
    utility_report: Phase20T09T18ScarcityUtilityReport
    safety_report: T09T18ScarcityGateReport

    def __post_init__(self) -> None:
        if type(self.tool) is not T09T18ScarcityTool:
            raise CiboCapitalManagementError(
                "T09/T18 stress tool identity is invalid"
            )
        if not self.treatment_candidate_id:
            raise CiboCapitalManagementError(
                "T09/T18 stress treatment identity is required"
            )
        if not isinstance(
            self.utility_report,
            Phase20T09T18ScarcityUtilityReport,
        ):
            raise CiboCapitalManagementError(
                "T09/T18 stress requires canonical scarcity utility report"
            )
        if not isinstance(self.safety_report, T09T18ScarcityGateReport):
            raise CiboCapitalManagementError(
                "T09/T18 stress requires canonical scarcity safety report"
            )


@dataclass(frozen=True, slots=True)
class Ce2iOosStressScenarioResult:
    scenario_kind: CompoundStressKind
    scenario_id: str
    passed: bool
    failed_dimensions: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Ce2iOosStressReport:
    gate_id: str
    workstream: Ce2iOosStressWorkstream
    protocol_binding_sha256: str
    scenario_results: tuple[Ce2iOosStressScenarioResult, ...]
    verdict: Ce2iOosStressVerdict
    all_required_stress_kinds_present: bool = True
    cross_scenario_compensation_allowed: bool = False
    productive_authority: bool = False
    certification_ready: bool = False

    def __post_init__(self) -> None:
        if self.gate_id != GATE_ID:
            raise CiboCapitalManagementError(
                "CE2I OOS stress gate identity drift"
            )
        _sha(self.protocol_binding_sha256, "protocol_binding_sha256")
        kinds = tuple(item.scenario_kind for item in self.scenario_results)
        if kinds != _REQUIRED_STRESS_KINDS:
            raise CiboCapitalManagementError(
                "CE2I OOS stress requires canonical stress-kind order"
            )
        expected = all(item.passed for item in self.scenario_results)
        if (
            (self.verdict is Ce2iOosStressVerdict.STRESS_ROBUST)
            != expected
        ):
            raise CiboCapitalManagementError(
                "CE2I OOS stress verdict/result mismatch"
            )
        if (
            not self.all_required_stress_kinds_present
            or self.cross_scenario_compensation_allowed
            or self.productive_authority
            or self.certification_ready
        ):
            raise CiboCapitalManagementError(
                "CE2I OOS stress report governance drift"
            )


def evaluate_t08_oos_stress(
    evidence: tuple[T08OosStressEvidence, ...],
) -> Ce2iOosStressReport:
    ordered = _ordered(evidence, "T08")
    results = tuple(
        Ce2iOosStressScenarioResult(
            scenario_kind=item.meta.scenario.kind,
            scenario_id=item.meta.scenario.scenario_id,
            passed=(
                item.report.fresh_oos_utility_demonstrated
                and item.report.pathwise_authorization_respected
                and item.report.required_folds == 4
            ),
            failed_dimensions=(
                ()
                if (
                    item.report.fresh_oos_utility_demonstrated
                    and item.report.pathwise_authorization_respected
                    and item.report.required_folds == 4
                )
                else tuple(item.report.blockers)
            ),
        )
        for item in ordered
    )
    return _report(
        workstream=Ce2iOosStressWorkstream.T08,
        protocol_binding_sha256=ordered[0].meta.protocol_binding_sha256,
        results=results,
    )


def evaluate_t12_oos_stress(
    evidence: tuple[T12OosStressEvidence, ...],
) -> Ce2iOosStressReport:
    ordered = _ordered(evidence, "T12")
    results = tuple(
        _utility_result(
            meta=item.meta,
            passed=(
                item.report.fresh_oos_utility_demonstrated
                and not item.report.blockers
                and not item.report.runtime_authority
            ),
            blockers=item.report.blockers,
        )
        for item in ordered
    )
    return _report(
        workstream=Ce2iOosStressWorkstream.T12,
        protocol_binding_sha256=ordered[0].meta.protocol_binding_sha256,
        results=results,
    )


def evaluate_t13_oos_stress(
    evidence: tuple[T13OosStressEvidence, ...],
) -> Ce2iOosStressReport:
    ordered = _ordered(evidence, "T13")
    results = tuple(
        _utility_result(
            meta=item.meta,
            passed=(
                item.report.fresh_oos_utility_demonstrated
                and not item.report.blockers
                and not item.report.runtime_authority
            ),
            blockers=item.report.blockers,
        )
        for item in ordered
    )
    return _report(
        workstream=Ce2iOosStressWorkstream.T13,
        protocol_binding_sha256=ordered[0].meta.protocol_binding_sha256,
        results=results,
    )


def evaluate_t09_t18_oos_stress(
    evidence: tuple[T09T18OosStressEvidence, ...],
) -> Ce2iOosStressReport:
    ordered = _ordered(evidence, "T09/T18")
    tool = ordered[0].tool
    candidate = ordered[0].treatment_candidate_id
    if any(item.tool is not tool for item in ordered):
        raise CiboCapitalManagementError(
            "T09/T18 stress tool identity drift"
        )
    if any(item.treatment_candidate_id != candidate for item in ordered):
        raise CiboCapitalManagementError(
            "T09/T18 stress treatment identity drift"
        )

    results: list[Ce2iOosStressScenarioResult] = []
    for item in ordered:
        scope = (
            item.utility_report.t09
            if tool is T09T18ScarcityTool.T09
            else item.utility_report.t18
        )
        verdicts = tuple(
            verdict
            for verdict in item.safety_report.verdicts
            if verdict.tool is tool and verdict.candidate_id == candidate
        )
        if len(verdicts) != 1:
            raise CiboCapitalManagementError(
                "T09/T18 stress safety treatment verdict missing"
            )
        safety = verdicts[0]
        safety_pass = (
            safety.status is T09T18ScarcityStatus.ELIGIBLE_FOR_FURTHER_RESEARCH
            and safety.passed_fold_ids == _CANONICAL_FOLDS
            and not safety.failed_fold_ids
            and not safety.failed_dimensions
        )
        utility_pass = (
            scope.fresh_oos_utility_demonstrated
            and not scope.blockers
            and not scope.runtime_authority
        )
        results.append(
            Ce2iOosStressScenarioResult(
                scenario_kind=item.meta.scenario.kind,
                scenario_id=item.meta.scenario.scenario_id,
                passed=utility_pass and safety_pass,
                failed_dimensions=(
                    ()
                    if utility_pass and safety_pass
                    else tuple(scope.blockers) + safety.failed_dimensions
                ),
            )
        )

    workstream = (
        Ce2iOosStressWorkstream.T09
        if tool is T09T18ScarcityTool.T09
        else Ce2iOosStressWorkstream.T18
    )
    return _report(
        workstream=workstream,
        protocol_binding_sha256=ordered[0].meta.protocol_binding_sha256,
        results=tuple(results),
    )


def _ordered(
    evidence: tuple[_TStressEvidence, ...],
    label: str,
) -> tuple[_TStressEvidence, ...]:
    if not evidence:
        raise CiboCapitalManagementError(
            f"{label} stress evidence is required"
        )
    by_kind = {item.meta.scenario.kind: item for item in evidence}
    if (
        len(evidence) != len(_REQUIRED_STRESS_KINDS)
        or set(by_kind) != set(_REQUIRED_STRESS_KINDS)
    ):
        raise CiboCapitalManagementError(
            f"{label} stress requires every frozen adversarial stress kind"
        )
    scenario_ids = tuple(item.meta.scenario.scenario_id for item in evidence)
    if len(scenario_ids) != len(set(scenario_ids)):
        raise CiboCapitalManagementError(
            f"{label} stress scenario ids must be unique"
        )
    populations = {
        item.meta.stressed_population_sha256 for item in evidence
    }
    if len(populations) != len(_REQUIRED_STRESS_KINDS):
        raise CiboCapitalManagementError(
            f"{label} stress requires distinct stressed populations"
        )
    protocols = {item.meta.protocol_binding_sha256 for item in evidence}
    if len(protocols) != 1:
        raise CiboCapitalManagementError(
            f"{label} stress protocol binding drift"
        )
    return tuple(by_kind[kind] for kind in _REQUIRED_STRESS_KINDS)


def _utility_result(
    *,
    meta: Ce2iOosStressScenarioMeta,
    passed: bool,
    blockers: tuple[str, ...],
) -> Ce2iOosStressScenarioResult:
    return Ce2iOosStressScenarioResult(
        scenario_kind=meta.scenario.kind,
        scenario_id=meta.scenario.scenario_id,
        passed=passed,
        failed_dimensions=() if passed else blockers,
    )


def _report(
    *,
    workstream: Ce2iOosStressWorkstream,
    protocol_binding_sha256: str,
    results: tuple[Ce2iOosStressScenarioResult, ...],
) -> Ce2iOosStressReport:
    verdict = (
        Ce2iOosStressVerdict.STRESS_ROBUST
        if all(item.passed for item in results)
        else Ce2iOosStressVerdict.FALSIFIED
    )
    return Ce2iOosStressReport(
        gate_id=GATE_ID,
        workstream=workstream,
        protocol_binding_sha256=protocol_binding_sha256,
        scenario_results=results,
        verdict=verdict,
    )


def _sha(value: str, name: str) -> None:
    if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
        raise CiboCapitalManagementError(
            f"CE2I OOS stress {name} must be canonical SHA-256"
        )
