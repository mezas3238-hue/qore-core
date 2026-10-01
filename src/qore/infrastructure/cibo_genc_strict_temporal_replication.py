"""Strict temporal replication for GEN-C7/8/11/12/13.

The underlying economic gates remain authoritative for one legal population.
This module re-runs those frozen gates independently on four distinct temporal
populations and rejects pooled rescue, treatment drift and post-outcome winner
selection. It grants no runtime, Risk, execution or certification authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from qore.infrastructure.cibo_adaptive_compound_speed_economic_gate import (
    Genc8EconomicGateRow,
    Genc8EconomicGateStatus,
    Genc8EconomicObservation,
    evaluate_genc8_economic_gate,
)
from qore.infrastructure.cibo_compound_capital import CiboCompoundCapitalError
from qore.infrastructure.cibo_genc9_economic_gate import Genc9EconomicGateStatus
from qore.infrastructure.cibo_genc11_genc13_utility_gate import (
    Genc11Genc13UtilityInput,
    Genc11Genc13Workstream,
    evaluate_genc11_genc13_utility,
)
from qore.infrastructure.cibo_genc12_economic_gate import (
    Genc12CrisisEconomicObservation,
    Genc12EconomicGateRow,
    Genc12EconomicGateStatus,
    evaluate_genc12_economic_gate,
)
from qore.infrastructure.cibo_profit_preservation_economic_gate import (
    Genc7CausalEconomicObservation,
    Genc7EconomicGateRow,
    Genc7EconomicGateStatus,
    evaluate_genc7_economic_gate,
)
from qore.infrastructure.cibo_profit_preservation_shadow import Genc7Action

GATE_ID = "CIBO_GENC_STRICT_FOUR_FOLD_TEMPORAL_REPLICATION_V1"
_CANONICAL_FOLDS = ("WF1", "WF2", "WF3", "WF4")


class GencTemporalReplicationVerdict(StrEnum):
    REPLICATED = "REPLICATED"
    FALSIFIED = "FALSIFIED"


@dataclass(frozen=True, slots=True)
class Genc7TemporalFoldEvidence:
    fold_id: str
    observations: tuple[Genc7CausalEconomicObservation, ...]

    def __post_init__(self) -> None:
        _validate_fold_id(self.fold_id)
        if not self.observations:
            raise CiboCompoundCapitalError(
                "GEN-C7 temporal fold requires observations"
            )
        if any(item.fold_ids != (self.fold_id,) for item in self.observations):
            raise CiboCompoundCapitalError(
                "GEN-C7 temporal observations must bind exactly one fold"
            )


@dataclass(frozen=True, slots=True)
class Genc8TemporalFoldEvidence:
    fold_id: str
    observations: tuple[Genc8EconomicObservation, ...]

    def __post_init__(self) -> None:
        _validate_fold_id(self.fold_id)
        if not self.observations:
            raise CiboCompoundCapitalError(
                "GEN-C8 temporal fold requires observations"
            )
        if any(item.fold_ids != (self.fold_id,) for item in self.observations):
            raise CiboCompoundCapitalError(
                "GEN-C8 temporal observations must bind exactly one fold"
            )


@dataclass(frozen=True, slots=True)
class Genc12TemporalFoldEvidence:
    fold_id: str
    observations: tuple[Genc12CrisisEconomicObservation, ...]

    def __post_init__(self) -> None:
        _validate_fold_id(self.fold_id)
        if not self.observations:
            raise CiboCompoundCapitalError(
                "GEN-C12 temporal fold requires observations"
            )


@dataclass(frozen=True, slots=True)
class Genc11Genc13TemporalFoldEvidence:
    fold_id: str
    evidence: Genc11Genc13UtilityInput

    def __post_init__(self) -> None:
        _validate_fold_id(self.fold_id)
        if not isinstance(self.evidence, Genc11Genc13UtilityInput):
            raise CiboCompoundCapitalError(
                "GEN-C11/13 temporal fold requires canonical utility input"
            )


@dataclass(frozen=True, slots=True)
class GencTemporalFoldResult:
    fold_id: str
    passed: bool
    treatment_status: str
    failed_dimensions: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class GencTemporalReplicationReport:
    gate_id: str
    workstream: str
    control_candidate_id: str
    treatment_candidate_id: str
    fold_results: tuple[GencTemporalFoldResult, ...]
    verdict: GencTemporalReplicationVerdict
    all_four_folds_required: bool = True
    outcomes_pooled_across_folds: bool = False
    winner_selected_after_outcomes: bool = False
    productive_authority: bool = False
    certification_ready: bool = False

    def __post_init__(self) -> None:
        if self.gate_id != GATE_ID:
            raise CiboCompoundCapitalError(
                "GEN-C temporal replication gate identity drift"
            )
        if self.workstream not in {
            "GEN-C7",
            "GEN-C8",
            "GEN-C11",
            "GEN-C12",
            "GEN-C13",
        }:
            raise CiboCompoundCapitalError(
                "GEN-C temporal replication workstream is invalid"
            )
        if (
            not self.control_candidate_id
            or not self.treatment_candidate_id
            or self.control_candidate_id == self.treatment_candidate_id
        ):
            raise CiboCompoundCapitalError(
                "GEN-C temporal replication candidate identity is invalid"
            )
        if tuple(item.fold_id for item in self.fold_results) != _CANONICAL_FOLDS:
            raise CiboCompoundCapitalError(
                "GEN-C temporal replication requires ordered WF1..WF4"
            )
        expected = all(item.passed for item in self.fold_results)
        if (
            (self.verdict is GencTemporalReplicationVerdict.REPLICATED)
            != expected
        ):
            raise CiboCompoundCapitalError(
                "GEN-C temporal replication verdict/result mismatch"
            )
        if (
            not self.all_four_folds_required
            or self.outcomes_pooled_across_folds
            or self.winner_selected_after_outcomes
            or self.productive_authority
            or self.certification_ready
        ):
            raise CiboCompoundCapitalError(
                "GEN-C temporal replication governance drift"
            )


def evaluate_genc7_temporal_replication(
    *,
    treatment_candidate_id: str,
    folds: tuple[Genc7TemporalFoldEvidence, ...],
) -> GencTemporalReplicationReport:
    ordered = _ordered_genc7(folds)
    populations: set[str] = set()
    control_id: str | None = None
    treatment_action: Genc7Action | None = None
    results: list[GencTemporalFoldResult] = []

    for item in ordered:
        _same_surface_genc7(item.observations)
        population = item.observations[0].population_sha256
        populations.add(population)
        report = evaluate_genc7_economic_gate(item.observations)
        if control_id is None:
            control_id = report.control_candidate_id
        elif report.control_candidate_id != control_id:
            raise CiboCompoundCapitalError(
                "GEN-C7 temporal control identity drift"
            )
        treatment = _find_genc7_row(report.rows, treatment_candidate_id)
        control = _find_genc7_row(report.rows, report.control_candidate_id)
        if control.status is not Genc7EconomicGateStatus.CONTROL:
            raise CiboCompoundCapitalError(
                "GEN-C7 temporal canonical control row invalid"
            )
        if treatment_action is None:
            treatment_action = treatment.action
        elif treatment.action is not treatment_action:
            raise CiboCompoundCapitalError(
                "GEN-C7 temporal treatment action drift"
            )
        passed = (
            treatment.status
            is Genc7EconomicGateStatus.ELIGIBLE_FOR_FURTHER_RESEARCH
        )
        results.append(
            GencTemporalFoldResult(
                fold_id=item.fold_id,
                passed=passed,
                treatment_status=treatment.status.value,
                failed_dimensions=treatment.failed_dimensions,
            )
        )

    _require_distinct_populations(populations)
    assert control_id is not None
    return _report(
        workstream="GEN-C7",
        control_candidate_id=control_id,
        treatment_candidate_id=treatment_candidate_id,
        results=tuple(results),
    )


def evaluate_genc8_temporal_replication(
    *,
    treatment_candidate_id: str,
    folds: tuple[Genc8TemporalFoldEvidence, ...],
) -> GencTemporalReplicationReport:
    ordered = _ordered_genc8(folds)
    populations: set[str] = set()
    control_id: str | None = None
    results: list[GencTemporalFoldResult] = []

    for item in ordered:
        _same_surface_genc8(item.observations)
        populations.add(item.observations[0].population_sha256)
        report = evaluate_genc8_economic_gate(item.observations)
        if control_id is None:
            control_id = report.control_candidate_id
        elif report.control_candidate_id != control_id:
            raise CiboCompoundCapitalError(
                "GEN-C8 temporal control identity drift"
            )
        treatment = _find_genc8_row(report.rows, treatment_candidate_id)
        control = _find_genc8_row(report.rows, report.control_candidate_id)
        if control.status is not Genc8EconomicGateStatus.CONTROL:
            raise CiboCompoundCapitalError(
                "GEN-C8 temporal canonical control row invalid"
            )
        passed = (
            treatment.status
            is Genc8EconomicGateStatus.ELIGIBLE_FOR_FURTHER_RESEARCH
        )
        results.append(
            GencTemporalFoldResult(
                fold_id=item.fold_id,
                passed=passed,
                treatment_status=treatment.status.value,
                failed_dimensions=treatment.failed_dimensions,
            )
        )

    _require_distinct_populations(populations)
    assert control_id is not None
    return _report(
        workstream="GEN-C8",
        control_candidate_id=control_id,
        treatment_candidate_id=treatment_candidate_id,
        results=tuple(results),
    )


def evaluate_genc12_temporal_replication(
    *,
    treatment_candidate_id: str,
    folds: tuple[Genc12TemporalFoldEvidence, ...],
) -> GencTemporalReplicationReport:
    ordered = _ordered_genc12(folds)
    populations: set[str] = set()
    crisis_sets: set[str] = set()
    control_id: str | None = None
    results: list[GencTemporalFoldResult] = []

    for item in ordered:
        _same_surface_genc12(item.observations)
        populations.add(item.observations[0].population_sha256)
        crisis_sets.add(item.observations[0].crisis_factor_set_sha256)
        report = evaluate_genc12_economic_gate(item.observations)
        if control_id is None:
            control_id = report.control_candidate_id
        elif report.control_candidate_id != control_id:
            raise CiboCompoundCapitalError(
                "GEN-C12 temporal control identity drift"
            )
        treatment = _find_genc12_row(report.rows, treatment_candidate_id)
        control = _find_genc12_row(report.rows, report.control_candidate_id)
        if control.status is not Genc12EconomicGateStatus.CONTROL:
            raise CiboCompoundCapitalError(
                "GEN-C12 temporal canonical control row invalid"
            )
        passed = (
            treatment.status
            is Genc12EconomicGateStatus.ELIGIBLE_FOR_FURTHER_RESEARCH
        )
        results.append(
            GencTemporalFoldResult(
                fold_id=item.fold_id,
                passed=passed,
                treatment_status=treatment.status.value,
                failed_dimensions=treatment.failed_dimensions,
            )
        )

    _require_distinct_populations(populations)
    if len(crisis_sets) != 1:
        raise CiboCompoundCapitalError(
            "GEN-C12 temporal crisis factor-set drift"
        )
    assert control_id is not None
    return _report(
        workstream="GEN-C12",
        control_candidate_id=control_id,
        treatment_candidate_id=treatment_candidate_id,
        results=tuple(results),
    )


def evaluate_genc11_genc13_temporal_replication(
    folds: tuple[Genc11Genc13TemporalFoldEvidence, ...],
) -> GencTemporalReplicationReport:
    ordered = _ordered_genc11_13(folds)
    first = ordered[0].evidence
    populations = {item.evidence.population_sha256 for item in ordered}

    if len(populations) != 4:
        raise CiboCompoundCapitalError(
            "GEN-C11/13 temporal replication requires four distinct populations"
        )
    for item in ordered[1:]:
        evidence = item.evidence
        if (
            evidence.workstream is not first.workstream
            or evidence.control_candidate_id != first.control_candidate_id
            or evidence.treatment_candidate_id != first.treatment_candidate_id
            or evidence.protocol_binding_sha256 != first.protocol_binding_sha256
        ):
            raise CiboCompoundCapitalError(
                "GEN-C11/13 temporal treatment/control/protocol drift"
            )
        if first.workstream is Genc11Genc13Workstream.GENC11:
            if (
                evidence.transition_calibration_sha256
                != first.transition_calibration_sha256
            ):
                raise CiboCompoundCapitalError(
                    "GEN-C11 temporal transition calibration drift"
                )
        elif evidence.memory_hypothesis_sha256 != first.memory_hypothesis_sha256:
            raise CiboCompoundCapitalError(
                "GEN-C13 temporal memory hypothesis drift"
            )

    results: list[GencTemporalFoldResult] = []
    for item in ordered:
        report = evaluate_genc11_genc13_utility(item.evidence)
        passed = (
            report.status
            is Genc9EconomicGateStatus.ELIGIBLE_FOR_FURTHER_RESEARCH
        )
        results.append(
            GencTemporalFoldResult(
                fold_id=item.fold_id,
                passed=passed,
                treatment_status=report.status.value,
                failed_dimensions=report.failed_dimensions,
            )
        )

    return _report(
        workstream=first.workstream.value,
        control_candidate_id=first.control_candidate_id,
        treatment_candidate_id=first.treatment_candidate_id,
        results=tuple(results),
    )


def _ordered_genc7(
    folds: tuple[Genc7TemporalFoldEvidence, ...],
) -> tuple[Genc7TemporalFoldEvidence, ...]:
    by_id = {item.fold_id: item for item in folds}
    if len(folds) != 4 or set(by_id) != set(_CANONICAL_FOLDS):
        raise CiboCompoundCapitalError(
            "GEN-C7 temporal replication requires exactly WF1..WF4"
        )
    return tuple(by_id[fold_id] for fold_id in _CANONICAL_FOLDS)


def _ordered_genc8(
    folds: tuple[Genc8TemporalFoldEvidence, ...],
) -> tuple[Genc8TemporalFoldEvidence, ...]:
    by_id = {item.fold_id: item for item in folds}
    if len(folds) != 4 or set(by_id) != set(_CANONICAL_FOLDS):
        raise CiboCompoundCapitalError(
            "GEN-C8 temporal replication requires exactly WF1..WF4"
        )
    return tuple(by_id[fold_id] for fold_id in _CANONICAL_FOLDS)


def _ordered_genc12(
    folds: tuple[Genc12TemporalFoldEvidence, ...],
) -> tuple[Genc12TemporalFoldEvidence, ...]:
    by_id = {item.fold_id: item for item in folds}
    if len(folds) != 4 or set(by_id) != set(_CANONICAL_FOLDS):
        raise CiboCompoundCapitalError(
            "GEN-C12 temporal replication requires exactly WF1..WF4"
        )
    return tuple(by_id[fold_id] for fold_id in _CANONICAL_FOLDS)


def _ordered_genc11_13(
    folds: tuple[Genc11Genc13TemporalFoldEvidence, ...],
) -> tuple[Genc11Genc13TemporalFoldEvidence, ...]:
    by_id = {item.fold_id: item for item in folds}
    if len(folds) != 4 or set(by_id) != set(_CANONICAL_FOLDS):
        raise CiboCompoundCapitalError(
            "GEN-C11/13 temporal replication requires exactly WF1..WF4"
        )
    return tuple(by_id[fold_id] for fold_id in _CANONICAL_FOLDS)


def _same_surface_genc7(
    observations: tuple[Genc7CausalEconomicObservation, ...],
) -> None:
    if len({item.population_sha256 for item in observations}) != 1:
        raise CiboCompoundCapitalError(
            "GEN-C7 temporal fold population drift"
        )
    if len({item.provider_surface_sha256 for item in observations}) != 1:
        raise CiboCompoundCapitalError(
            "GEN-C7 temporal fold provider-surface drift"
        )


def _same_surface_genc8(
    observations: tuple[Genc8EconomicObservation, ...],
) -> None:
    if len({item.population_sha256 for item in observations}) != 1:
        raise CiboCompoundCapitalError(
            "GEN-C8 temporal fold population drift"
        )
    if len({item.provider_surface_sha256 for item in observations}) != 1:
        raise CiboCompoundCapitalError(
            "GEN-C8 temporal fold provider-surface drift"
        )


def _same_surface_genc12(
    observations: tuple[Genc12CrisisEconomicObservation, ...],
) -> None:
    if len({item.population_sha256 for item in observations}) != 1:
        raise CiboCompoundCapitalError(
            "GEN-C12 temporal fold population drift"
        )
    if len({item.provider_surface_sha256 for item in observations}) != 1:
        raise CiboCompoundCapitalError(
            "GEN-C12 temporal fold provider-surface drift"
        )
    if len({item.crisis_factor_set_sha256 for item in observations}) != 1:
        raise CiboCompoundCapitalError(
            "GEN-C12 temporal fold crisis factor-set drift"
        )


def _find_genc7_row(
    rows: tuple[Genc7EconomicGateRow, ...],
    candidate_id: str,
) -> Genc7EconomicGateRow:
    matches = tuple(row for row in rows if row.candidate_id == candidate_id)
    if len(matches) != 1:
        raise CiboCompoundCapitalError(
            "GEN-C7 temporal treatment/control row missing"
        )
    return matches[0]


def _find_genc8_row(
    rows: tuple[Genc8EconomicGateRow, ...],
    candidate_id: str,
) -> Genc8EconomicGateRow:
    matches = tuple(row for row in rows if row.candidate_id == candidate_id)
    if len(matches) != 1:
        raise CiboCompoundCapitalError(
            "GEN-C8 temporal treatment/control row missing"
        )
    return matches[0]


def _find_genc12_row(
    rows: tuple[Genc12EconomicGateRow, ...],
    candidate_id: str,
) -> Genc12EconomicGateRow:
    matches = tuple(row for row in rows if row.candidate_id == candidate_id)
    if len(matches) != 1:
        raise CiboCompoundCapitalError(
            "GEN-C12 temporal treatment/control row missing"
        )
    return matches[0]


def _require_distinct_populations(populations: set[str]) -> None:
    if len(populations) != 4:
        raise CiboCompoundCapitalError(
            "GEN-C temporal replication requires four distinct populations"
        )


def _validate_fold_id(fold_id: str) -> None:
    if fold_id not in _CANONICAL_FOLDS:
        raise CiboCompoundCapitalError(
            "GEN-C temporal fold must be WF1..WF4"
        )


def _report(
    *,
    workstream: str,
    control_candidate_id: str,
    treatment_candidate_id: str,
    results: tuple[GencTemporalFoldResult, ...],
) -> GencTemporalReplicationReport:
    verdict = (
        GencTemporalReplicationVerdict.REPLICATED
        if all(item.passed for item in results)
        else GencTemporalReplicationVerdict.FALSIFIED
    )
    return GencTemporalReplicationReport(
        gate_id=GATE_ID,
        workstream=workstream,
        control_candidate_id=control_candidate_id,
        treatment_candidate_id=treatment_candidate_id,
        fold_results=results,
        verdict=verdict,
    )
