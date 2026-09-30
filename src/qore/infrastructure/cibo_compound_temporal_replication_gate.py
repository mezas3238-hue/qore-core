"""Strict economic replication gate for Compound / GEN-C9.

The criterion is frozen before a real qualifying population is available:
the same non-compensatory GEN-C9 gate must pass independently in every one of
the four canonical Phase20D temporal folds. Outcomes may not be pooled to
manufacture a pass.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from qore.infrastructure.cibo_compound_capital import (
    CiboCompoundCapitalError,
)
from qore.infrastructure.cibo_genc9_economic_gate import (
    Genc9EconomicGateReport,
    Genc9EconomicGateStatus,
)

_CANONICAL_FOLDS = ("WF1", "WF2", "WF3", "WF4")


class CompoundTemporalEconomicVerdict(StrEnum):
    REPLICATED = "REPLICATED"
    FALSIFIED = "FALSIFIED"


@dataclass(frozen=True, slots=True)
class CompoundTemporalEconomicFoldEvidence:
    fold_id: str
    gate_report: Genc9EconomicGateReport
    source_population_sha256: str
    provider_economics_sha256: str
    forward_observed: bool
    outcomes_pooled: bool = False

    def __post_init__(self) -> None:
        if self.fold_id not in _CANONICAL_FOLDS:
            raise CiboCompoundCapitalError(
                "compound economic replication fold must be WF1..WF4"
            )
        if not isinstance(self.gate_report, Genc9EconomicGateReport):
            raise CiboCompoundCapitalError(
                "compound economic replication requires GEN-C9 gate report"
            )
        _sha(self.source_population_sha256, "source_population_sha256")
        _sha(self.provider_economics_sha256, "provider_economics_sha256")
        if not self.forward_observed or self.outcomes_pooled:
            raise CiboCompoundCapitalError(
                "compound economic replication requires unpooled forward evidence"
            )


@dataclass(frozen=True, slots=True)
class CompoundTemporalEconomicFoldResult:
    fold_id: str
    treatment_status: Genc9EconomicGateStatus
    safety_no_worse: bool
    strict_growth_or_efficiency_improvement: bool
    failed_dimensions: tuple[str, ...]
    passed: bool


@dataclass(frozen=True, slots=True)
class CompoundTemporalEconomicReplicationGate:
    control_candidate_id: str
    treatment_candidate_id: str
    fold_results: tuple[CompoundTemporalEconomicFoldResult, ...]
    verdict: CompoundTemporalEconomicVerdict
    all_four_folds_required: bool = True
    weighted_score_used: bool = False
    outcomes_pooled_across_folds: bool = False
    production_policy_selected: bool = False
    certification_ready: bool = False

    def __post_init__(self) -> None:
        if not self.control_candidate_id or not self.treatment_candidate_id:
            raise CiboCompoundCapitalError(
                "compound economic replication candidate identity is required"
            )
        if self.control_candidate_id == self.treatment_candidate_id:
            raise CiboCompoundCapitalError(
                "compound economic replication treatment must differ from control"
            )
        fold_ids = tuple(item.fold_id for item in self.fold_results)
        if fold_ids != _CANONICAL_FOLDS:
            raise CiboCompoundCapitalError(
                "compound economic replication requires ordered WF1..WF4"
            )
        expected = all(item.passed for item in self.fold_results)
        if (
            (self.verdict is CompoundTemporalEconomicVerdict.REPLICATED)
            != expected
        ):
            raise CiboCompoundCapitalError(
                "compound economic replication verdict/result mismatch"
            )
        if (
            not self.all_four_folds_required
            or self.weighted_score_used
            or self.outcomes_pooled_across_folds
            or self.production_policy_selected
            or self.certification_ready
        ):
            raise CiboCompoundCapitalError(
                "compound economic replication governance drift"
            )


def evaluate_compound_temporal_economic_replication(
    *,
    treatment_candidate_id: str,
    folds: tuple[CompoundTemporalEconomicFoldEvidence, ...],
) -> CompoundTemporalEconomicReplicationGate:
    """Require the treatment to pass the same GEN-C9 gate in every fold."""

    if not treatment_candidate_id:
        raise CiboCompoundCapitalError(
            "compound economic replication treatment identity is required"
        )
    by_id = {item.fold_id: item for item in folds}
    if len(by_id) != len(folds) or set(by_id) != set(_CANONICAL_FOLDS):
        raise CiboCompoundCapitalError(
            "compound economic replication requires exactly WF1..WF4"
        )
    ordered = tuple(by_id[item] for item in _CANONICAL_FOLDS)
    controls = {item.gate_report.control_candidate_id for item in ordered}
    if len(controls) != 1:
        raise CiboCompoundCapitalError(
            "compound economic replication control identity drift"
        )
    control_candidate_id = next(iter(controls))
    if treatment_candidate_id == control_candidate_id:
        raise CiboCompoundCapitalError(
            "compound economic replication treatment must differ from control"
        )

    results: list[CompoundTemporalEconomicFoldResult] = []
    for item in ordered:
        rows = {
            row.candidate_id: row
            for row in item.gate_report.rows
        }
        row = rows.get(treatment_candidate_id)
        if row is None:
            raise CiboCompoundCapitalError(
                "compound economic replication treatment row missing from fold"
            )
        control = rows.get(control_candidate_id)
        if (
            control is None
            or control.status is not Genc9EconomicGateStatus.CONTROL
        ):
            raise CiboCompoundCapitalError(
                "compound economic replication canonical control row missing"
            )
        passed = (
            row.status
            is Genc9EconomicGateStatus.ELIGIBLE_FOR_FURTHER_RESEARCH
            and row.safety_no_worse
            and row.strict_growth_or_efficiency_improvement
            and not row.failed_dimensions
        )
        results.append(
            CompoundTemporalEconomicFoldResult(
                fold_id=item.fold_id,
                treatment_status=row.status,
                safety_no_worse=row.safety_no_worse,
                strict_growth_or_efficiency_improvement=(
                    row.strict_growth_or_efficiency_improvement
                ),
                failed_dimensions=row.failed_dimensions,
                passed=passed,
            )
        )

    fold_results = tuple(results)
    verdict = (
        CompoundTemporalEconomicVerdict.REPLICATED
        if all(item.passed for item in fold_results)
        else CompoundTemporalEconomicVerdict.FALSIFIED
    )
    return CompoundTemporalEconomicReplicationGate(
        control_candidate_id=control_candidate_id,
        treatment_candidate_id=treatment_candidate_id,
        fold_results=fold_results,
        verdict=verdict,
    )


def _sha(value: str, name: str) -> None:
    if (
        not isinstance(value, str)
        or not value.startswith("sha256:")
        or len(value) != 71
        or any(char not in "0123456789abcdef" for char in value[7:])
    ):
        raise CiboCompoundCapitalError(
            f"compound economic replication {name} must be canonical SHA-256"
        )
