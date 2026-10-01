"""Strict four-fold temporal replication for Protected Base.

The protected-base economic gate evaluates one legal population. This wrapper
requires one frozen control/treatment candidate pair to re-pass that unchanged
gate independently in WF1..WF4 on four distinct provider-valid populations.
It grants no production or certification authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_protected_base_policy_gate import (
    ProtectedBaseEconomicObservation,
    ProtectedBaseGateStatus,
    ProtectedBasePolicyCandidate,
    evaluate_protected_base_gate,
)

GATE_ID = "CIBO_PROTECTED_BASE_STRICT_FOUR_FOLD_TEMPORAL_REPLICATION_V1"
_CANONICAL_FOLDS = ("WF1", "WF2", "WF3", "WF4")


class ProtectedBaseTemporalVerdict(StrEnum):
    REPLICATED = "REPLICATED"
    FALSIFIED = "FALSIFIED"


@dataclass(frozen=True, slots=True)
class ProtectedBaseTemporalFoldEvidence:
    fold_id: str
    observations: tuple[ProtectedBaseEconomicObservation, ...]

    def __post_init__(self) -> None:
        if self.fold_id not in _CANONICAL_FOLDS:
            raise CiboCapitalManagementError(
                "protected-base temporal fold must be WF1..WF4"
            )
        if not self.observations:
            raise CiboCapitalManagementError(
                "protected-base temporal fold requires observations"
            )
        if any(item.fold_ids != (self.fold_id,) for item in self.observations):
            raise CiboCapitalManagementError(
                "protected-base temporal observations must bind one fold"
            )


@dataclass(frozen=True, slots=True)
class ProtectedBaseTemporalFoldResult:
    fold_id: str
    passed: bool
    treatment_status: ProtectedBaseGateStatus
    failed_dimensions: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ProtectedBaseTemporalReplicationReport:
    gate_id: str
    control_candidate_id: str
    treatment_candidate_id: str
    fold_results: tuple[ProtectedBaseTemporalFoldResult, ...]
    verdict: ProtectedBaseTemporalVerdict
    all_four_folds_required: bool = True
    outcomes_pooled_across_folds: bool = False
    winner_selected_after_outcomes: bool = False
    productive_authority: bool = False
    certification_ready: bool = False

    def __post_init__(self) -> None:
        if self.gate_id != GATE_ID:
            raise CiboCapitalManagementError(
                "protected-base temporal gate identity drift"
            )
        if (
            not self.control_candidate_id
            or not self.treatment_candidate_id
            or self.control_candidate_id == self.treatment_candidate_id
        ):
            raise CiboCapitalManagementError(
                "protected-base temporal candidate identity invalid"
            )
        if tuple(item.fold_id for item in self.fold_results) != _CANONICAL_FOLDS:
            raise CiboCapitalManagementError(
                "protected-base temporal replication requires WF1..WF4"
            )
        expected = all(item.passed for item in self.fold_results)
        if (
            (self.verdict is ProtectedBaseTemporalVerdict.REPLICATED)
            != expected
        ):
            raise CiboCapitalManagementError(
                "protected-base temporal verdict/result mismatch"
            )
        if (
            not self.all_four_folds_required
            or self.outcomes_pooled_across_folds
            or self.winner_selected_after_outcomes
            or self.productive_authority
            or self.certification_ready
        ):
            raise CiboCapitalManagementError(
                "protected-base temporal governance drift"
            )


def evaluate_protected_base_temporal_replication(
    *,
    treatment_candidate_id: str,
    folds: tuple[ProtectedBaseTemporalFoldEvidence, ...],
) -> ProtectedBaseTemporalReplicationReport:
    """Require one frozen Protected Base treatment to pass WF1..WF4."""

    by_id = {item.fold_id: item for item in folds}
    if len(folds) != 4 or set(by_id) != set(_CANONICAL_FOLDS):
        raise CiboCapitalManagementError(
            "protected-base temporal replication requires exactly WF1..WF4"
        )
    ordered = tuple(by_id[fold_id] for fold_id in _CANONICAL_FOLDS)

    populations = {
        item.observations[0].population_sha256 for item in ordered
    }
    if len(populations) != 4:
        raise CiboCapitalManagementError(
            "protected-base temporal replication requires distinct populations"
        )
    provider_surfaces = {
        item.observations[0].provider_surface_sha256 for item in ordered
    }
    if len(provider_surfaces) != 1:
        raise CiboCapitalManagementError(
            "protected-base temporal provider surface drift"
        )

    control_candidate: ProtectedBasePolicyCandidate | None = None
    treatment_candidate: ProtectedBasePolicyCandidate | None = None
    results: list[ProtectedBaseTemporalFoldResult] = []

    for item in ordered:
        populations_in_fold = {
            observation.population_sha256 for observation in item.observations
        }
        providers_in_fold = {
            observation.provider_surface_sha256
            for observation in item.observations
        }
        if len(populations_in_fold) != 1 or len(providers_in_fold) != 1:
            raise CiboCapitalManagementError(
                "protected-base temporal fold comparison surface drift"
            )
        report = evaluate_protected_base_gate(item.observations)
        rows = {row.candidate_id: row for row in report.rows}
        control_row = rows.get(report.control_candidate_id)
        treatment_row = rows.get(treatment_candidate_id)
        if (
            control_row is None
            or control_row.status is not ProtectedBaseGateStatus.CONTROL
            or treatment_row is None
        ):
            raise CiboCapitalManagementError(
                "protected-base temporal control/treatment row missing"
            )

        fold_control = next(
            observation.candidate
            for observation in item.observations
            if observation.candidate.candidate_id == report.control_candidate_id
        )
        fold_treatment = next(
            observation.candidate
            for observation in item.observations
            if observation.candidate.candidate_id == treatment_candidate_id
        )
        if control_candidate is None:
            control_candidate = fold_control
            treatment_candidate = fold_treatment
        elif (
            fold_control != control_candidate
            or fold_treatment != treatment_candidate
        ):
            raise CiboCapitalManagementError(
                "protected-base temporal frozen candidate drift"
            )

        passed = (
            treatment_row.status
            is ProtectedBaseGateStatus.ELIGIBLE_FOR_FURTHER_RESEARCH
        )
        results.append(
            ProtectedBaseTemporalFoldResult(
                fold_id=item.fold_id,
                passed=passed,
                treatment_status=treatment_row.status,
                failed_dimensions=treatment_row.failed_dimensions,
            )
        )

    assert control_candidate is not None
    assert treatment_candidate is not None
    verdict = (
        ProtectedBaseTemporalVerdict.REPLICATED
        if all(item.passed for item in results)
        else ProtectedBaseTemporalVerdict.FALSIFIED
    )
    return ProtectedBaseTemporalReplicationReport(
        gate_id=GATE_ID,
        control_candidate_id=control_candidate.candidate_id,
        treatment_candidate_id=treatment_candidate.candidate_id,
        fold_results=tuple(results),
        verdict=verdict,
    )
