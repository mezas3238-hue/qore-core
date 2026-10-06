"""Strict four-fold temporal utility replication for CE2I research gates.

T06/T07 expansion and T14/T15 causal Pareto gates evaluate one legal
control/treatment population. This module is the separate preregistered
temporal-replication layer. It requires the same frozen treatment and control
to satisfy the same gate independently on four distinct canonical temporal
populations. It never grants runtime, Risk, execution, merge or certification
authority.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum

from qore.infrastructure.cibo_compound_capital import CiboCompoundCapitalError
from qore.infrastructure.cibo_expansion_utility_gate import (
    ExpansionUtilityGateReport,
    ExpansionUtilityGateRow,
    ExpansionUtilityStatus,
)
from qore.infrastructure.cibo_t14_t15_utility_gate import (
    T14T15UtilityGateReport,
    T14T15UtilityGateRow,
    T14T15UtilityStatus,
)

GATE_ID = "CIBO_CE2I_STRICT_FOUR_FOLD_UTILITY_REPLICATION_V1"
_CANONICAL_FOLDS = ("WF1", "WF2", "WF3", "WF4")
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


class Ce2iTemporalReplicationVerdict(StrEnum):
    REPLICATED = "REPLICATED"
    FALSIFIED = "FALSIFIED"


@dataclass(frozen=True, slots=True)
class ExpansionTemporalFoldEvidence:
    fold_id: str
    gate_report: ExpansionUtilityGateReport
    protocol_binding_sha256: str
    outcomes_pooled_across_folds: bool = False

    def __post_init__(self) -> None:
        if self.fold_id not in _CANONICAL_FOLDS:
            raise CiboCompoundCapitalError(
                "CE2I expansion temporal fold must be WF1..WF4"
            )
        if not isinstance(self.gate_report, ExpansionUtilityGateReport):
            raise CiboCompoundCapitalError(
                "CE2I expansion temporal evidence requires canonical gate report"
            )
        _sha(self.protocol_binding_sha256, "protocol_binding_sha256")
        if self.outcomes_pooled_across_folds:
            raise CiboCompoundCapitalError(
                "CE2I temporal replication cannot pool outcomes across folds"
            )


@dataclass(frozen=True, slots=True)
class CausalParetoTemporalFoldEvidence:
    fold_id: str
    gate_report: T14T15UtilityGateReport
    protocol_binding_sha256: str
    outcomes_pooled_across_folds: bool = False

    def __post_init__(self) -> None:
        if self.fold_id not in _CANONICAL_FOLDS:
            raise CiboCompoundCapitalError(
                "CE2I T14/T15 temporal fold must be WF1..WF4"
            )
        if not isinstance(self.gate_report, T14T15UtilityGateReport):
            raise CiboCompoundCapitalError(
                "CE2I T14/T15 temporal evidence requires canonical gate report"
            )
        _sha(self.protocol_binding_sha256, "protocol_binding_sha256")
        if self.outcomes_pooled_across_folds:
            raise CiboCompoundCapitalError(
                "CE2I temporal replication cannot pool outcomes across folds"
            )


@dataclass(frozen=True, slots=True)
class Ce2iTemporalFoldResult:
    fold_id: str
    passed: bool
    treatment_status: str
    failed_dimensions: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.fold_id not in _CANONICAL_FOLDS:
            raise CiboCompoundCapitalError(
                "CE2I temporal fold result must be WF1..WF4"
            )
        if type(self.passed) is not bool:
            raise CiboCompoundCapitalError(
                "CE2I temporal fold result passed must be bool"
            )
        if not isinstance(self.treatment_status, str) or not self.treatment_status:
            raise CiboCompoundCapitalError(
                "CE2I temporal fold treatment status is required"
            )
        if (
            not isinstance(self.failed_dimensions, tuple)
            or any(
                not isinstance(item, str) or not item
                for item in self.failed_dimensions
            )
            or len(self.failed_dimensions) != len(set(self.failed_dimensions))
        ):
            raise CiboCompoundCapitalError(
                "CE2I temporal fold failed dimensions are invalid"
            )
        expected = (
            self.treatment_status == "ELIGIBLE_FOR_FURTHER_RESEARCH"
            and not self.failed_dimensions
        )
        if self.passed != expected:
            raise CiboCompoundCapitalError(
                "CE2I temporal fold pass/status drift"
            )


@dataclass(frozen=True, slots=True)
class Ce2iTemporalReplicationReport:
    gate_id: str
    family: str
    control_candidate_id: str
    treatment_candidate_id: str
    protocol_binding_sha256: str
    fold_results: tuple[Ce2iTemporalFoldResult, ...]
    verdict: Ce2iTemporalReplicationVerdict
    all_four_folds_required: bool = True
    outcomes_pooled_across_folds: bool = False
    winner_selected_after_outcomes: bool = False
    productive_authority: bool = False
    certification_ready: bool = False

    def __post_init__(self) -> None:
        if self.gate_id != GATE_ID:
            raise CiboCompoundCapitalError(
                "CE2I temporal replication gate identity drift"
            )
        if self.family not in {"T06_T07", "T14_T15"}:
            raise CiboCompoundCapitalError(
                "CE2I temporal replication family is invalid"
            )
        if (
            not self.control_candidate_id
            or not self.treatment_candidate_id
            or self.control_candidate_id == self.treatment_candidate_id
        ):
            raise CiboCompoundCapitalError(
                "CE2I temporal replication candidate identity is invalid"
            )
        _sha(self.protocol_binding_sha256, "protocol_binding_sha256")
        if (
            not isinstance(self.fold_results, tuple)
            or any(
                not isinstance(item, Ce2iTemporalFoldResult)
                for item in self.fold_results
            )
        ):
            raise CiboCompoundCapitalError(
                "CE2I temporal replication requires canonical fold results"
            )
        if tuple(item.fold_id for item in self.fold_results) != _CANONICAL_FOLDS:
            raise CiboCompoundCapitalError(
                "CE2I temporal replication requires ordered WF1..WF4"
            )
        expected = all(item.passed for item in self.fold_results)
        if (
            (self.verdict is Ce2iTemporalReplicationVerdict.REPLICATED)
            != expected
        ):
            raise CiboCompoundCapitalError(
                "CE2I temporal replication verdict/result mismatch"
            )
        if (
            not self.all_four_folds_required
            or self.outcomes_pooled_across_folds
            or self.winner_selected_after_outcomes
            or self.productive_authority
            or self.certification_ready
        ):
            raise CiboCompoundCapitalError(
                "CE2I temporal replication governance drift"
            )


def evaluate_expansion_temporal_replication(
    *,
    treatment_candidate_id: str,
    folds: tuple[ExpansionTemporalFoldEvidence, ...],
) -> Ce2iTemporalReplicationReport:
    """Require one T06/T07 treatment to pass independently in WF1..WF4."""

    ordered = _ordered_expansion_folds(folds)
    control_id = ordered[0].gate_report.control_candidate_id
    kind = ordered[0].gate_report.kind
    protocol = ordered[0].protocol_binding_sha256
    populations = {item.gate_report.population_sha256 for item in ordered}

    if len(populations) != 4:
        raise CiboCompoundCapitalError(
            "CE2I temporal replication requires four distinct fold populations"
        )
    if any(item.gate_report.control_candidate_id != control_id for item in ordered):
        raise CiboCompoundCapitalError(
            "CE2I expansion temporal control identity drift"
        )
    if any(item.gate_report.kind is not kind for item in ordered):
        raise CiboCompoundCapitalError(
            "CE2I expansion temporal workstream drift"
        )
    if any(item.protocol_binding_sha256 != protocol for item in ordered):
        raise CiboCompoundCapitalError(
            "CE2I expansion temporal protocol binding drift"
        )

    results: list[Ce2iTemporalFoldResult] = []
    for item in ordered:
        control = _expansion_row_by_id(
            item.gate_report.rows,
            control_id,
            "CE2I expansion temporal control row missing",
        )
        treatment = _expansion_row_by_id(
            item.gate_report.rows,
            treatment_candidate_id,
            "CE2I expansion temporal treatment row missing",
        )
        if control.status is not ExpansionUtilityStatus.CONTROL:
            raise CiboCompoundCapitalError(
                "CE2I expansion temporal canonical control row invalid"
            )
        passed = (
            treatment.status
            is ExpansionUtilityStatus.ELIGIBLE_FOR_FURTHER_RESEARCH
        )
        results.append(
            Ce2iTemporalFoldResult(
                fold_id=item.fold_id,
                passed=passed,
                treatment_status=treatment.status.value,
                failed_dimensions=treatment.failed_dimensions,
            )
        )

    return _report(
        family="T06_T07",
        control_candidate_id=control_id,
        treatment_candidate_id=treatment_candidate_id,
        protocol_binding_sha256=protocol,
        results=tuple(results),
    )


def evaluate_t14_t15_temporal_replication(
    *,
    treatment_candidate_id: str,
    folds: tuple[CausalParetoTemporalFoldEvidence, ...],
) -> Ce2iTemporalReplicationReport:
    """Require one T14/T15 treatment to pass independently in WF1..WF4."""

    ordered = _ordered_causal_pareto_folds(folds)
    control_id = ordered[0].gate_report.control_candidate_id
    kind = ordered[0].gate_report.kind
    protocol = ordered[0].protocol_binding_sha256
    populations = {item.gate_report.population_sha256 for item in ordered}

    if len(populations) != 4:
        raise CiboCompoundCapitalError(
            "CE2I temporal replication requires four distinct fold populations"
        )
    if any(item.gate_report.control_candidate_id != control_id for item in ordered):
        raise CiboCompoundCapitalError(
            "CE2I T14/T15 temporal control identity drift"
        )
    if any(item.gate_report.kind is not kind for item in ordered):
        raise CiboCompoundCapitalError(
            "CE2I T14/T15 temporal workstream drift"
        )
    if any(item.protocol_binding_sha256 != protocol for item in ordered):
        raise CiboCompoundCapitalError(
            "CE2I T14/T15 temporal protocol binding drift"
        )

    results: list[Ce2iTemporalFoldResult] = []
    for item in ordered:
        control = _t14_t15_row_by_id(
            item.gate_report.rows,
            control_id,
            "CE2I T14/T15 temporal control row missing",
        )
        treatment = _t14_t15_row_by_id(
            item.gate_report.rows,
            treatment_candidate_id,
            "CE2I T14/T15 temporal treatment row missing",
        )
        if control.status is not T14T15UtilityStatus.CONTROL:
            raise CiboCompoundCapitalError(
                "CE2I T14/T15 temporal canonical control row invalid"
            )
        passed = (
            treatment.status
            is T14T15UtilityStatus.ELIGIBLE_FOR_FURTHER_RESEARCH
        )
        results.append(
            Ce2iTemporalFoldResult(
                fold_id=item.fold_id,
                passed=passed,
                treatment_status=treatment.status.value,
                failed_dimensions=treatment.failed_dimensions,
            )
        )

    return _report(
        family="T14_T15",
        control_candidate_id=control_id,
        treatment_candidate_id=treatment_candidate_id,
        protocol_binding_sha256=protocol,
        results=tuple(results),
    )


def _ordered_expansion_folds(
    folds: tuple[ExpansionTemporalFoldEvidence, ...],
) -> tuple[ExpansionTemporalFoldEvidence, ...]:
    by_id = {item.fold_id: item for item in folds}
    if len(folds) != 4 or set(by_id) != set(_CANONICAL_FOLDS):
        raise CiboCompoundCapitalError(
            "CE2I expansion temporal replication requires exactly WF1..WF4"
        )
    return tuple(by_id[fold_id] for fold_id in _CANONICAL_FOLDS)


def _ordered_causal_pareto_folds(
    folds: tuple[CausalParetoTemporalFoldEvidence, ...],
) -> tuple[CausalParetoTemporalFoldEvidence, ...]:
    by_id = {item.fold_id: item for item in folds}
    if len(folds) != 4 or set(by_id) != set(_CANONICAL_FOLDS):
        raise CiboCompoundCapitalError(
            "CE2I T14/T15 temporal replication requires exactly WF1..WF4"
        )
    return tuple(by_id[fold_id] for fold_id in _CANONICAL_FOLDS)


def _expansion_row_by_id(
    rows: tuple[ExpansionUtilityGateRow, ...],
    candidate_id: str,
    error_message: str,
) -> ExpansionUtilityGateRow:
    matches = tuple(row for row in rows if row.candidate_id == candidate_id)
    if len(matches) != 1:
        raise CiboCompoundCapitalError(error_message)
    return matches[0]


def _t14_t15_row_by_id(
    rows: tuple[T14T15UtilityGateRow, ...],
    candidate_id: str,
    error_message: str,
) -> T14T15UtilityGateRow:
    matches = tuple(row for row in rows if row.candidate_id == candidate_id)
    if len(matches) != 1:
        raise CiboCompoundCapitalError(error_message)
    return matches[0]


def _report(
    *,
    family: str,
    control_candidate_id: str,
    treatment_candidate_id: str,
    protocol_binding_sha256: str,
    results: tuple[Ce2iTemporalFoldResult, ...],
) -> Ce2iTemporalReplicationReport:
    verdict = (
        Ce2iTemporalReplicationVerdict.REPLICATED
        if all(item.passed for item in results)
        else Ce2iTemporalReplicationVerdict.FALSIFIED
    )
    return Ce2iTemporalReplicationReport(
        gate_id=GATE_ID,
        family=family,
        control_candidate_id=control_candidate_id,
        treatment_candidate_id=treatment_candidate_id,
        protocol_binding_sha256=protocol_binding_sha256,
        fold_results=results,
        verdict=verdict,
    )


def _sha(value: str, name: str) -> None:
    if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
        raise CiboCompoundCapitalError(
            f"CE2I temporal replication {name} must be canonical SHA-256"
        )
