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
from qore.infrastructure.cibo_compound_temporal_replication import (
    CompoundTemporalReplicationReport,
)
from qore.infrastructure.cibo_genc9_economic_gate import (
    Genc9EconomicGateReport,
    Genc9EconomicGateStatus,
)

_CANONICAL_FOLDS = ("WF1", "WF2", "WF3", "WF4")


class CompoundTemporalEconomicVerdict(StrEnum):
    REPLICATED = "REPLICATED"
    FALSIFIED = "FALSIFIED"


class CompoundTemporalPopulationDisposition(StrEnum):
    ELIGIBLE_FORWARD_UNPOOLED = "ELIGIBLE_FORWARD_UNPOOLED"
    INELIGIBLE_NOT_FORWARD = "INELIGIBLE_NOT_FORWARD"
    INELIGIBLE_OUTCOMES_POOLED = "INELIGIBLE_OUTCOMES_POOLED"


@dataclass(frozen=True, slots=True)
class CompoundTemporalPopulationAssessment:
    """Universal input assessment before the strict economic replication gate."""

    source_population_sha256: str
    provider_economics_sha256: str
    forward_observed: bool
    outcomes_pooled: bool
    disposition: CompoundTemporalPopulationDisposition
    eligible_for_strict_replication_gate: bool
    certification_ready: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        _sha(self.source_population_sha256, "source_population_sha256")
        _sha(self.provider_economics_sha256, "provider_economics_sha256")
        if type(self.forward_observed) is not bool or type(self.outcomes_pooled) is not bool:
            raise CiboCompoundCapitalError(
                "compound temporal population flags must be bool"
            )
        if type(self.disposition) is not CompoundTemporalPopulationDisposition:
            raise CiboCompoundCapitalError(
                "compound temporal population disposition is invalid"
            )
        expected = (
            CompoundTemporalPopulationDisposition.INELIGIBLE_OUTCOMES_POOLED
            if self.outcomes_pooled
            else (
                CompoundTemporalPopulationDisposition.ELIGIBLE_FORWARD_UNPOOLED
                if self.forward_observed
                else CompoundTemporalPopulationDisposition.INELIGIBLE_NOT_FORWARD
            )
        )
        if self.disposition is not expected:
            raise CiboCompoundCapitalError(
                "compound temporal population disposition/flags drift"
            )
        expected_eligible = expected is (
            CompoundTemporalPopulationDisposition.ELIGIBLE_FORWARD_UNPOOLED
        )
        if self.eligible_for_strict_replication_gate != expected_eligible:
            raise CiboCompoundCapitalError(
                "compound temporal population eligibility drift"
            )
        if self.certification_ready or self.productive_authority:
            raise CiboCompoundCapitalError(
                "compound temporal population assessment grants no certification/authority"
            )


def assess_compound_temporal_population(
    *,
    source_population_sha256: str,
    provider_economics_sha256: str,
    forward_observed: bool,
    outcomes_pooled: bool = False,
) -> CompoundTemporalPopulationAssessment:
    """Classify any canonical population without relabelling its evidence quality."""

    if type(forward_observed) is not bool or type(outcomes_pooled) is not bool:
        raise CiboCompoundCapitalError(
            "compound temporal population flags must be bool"
        )
    if outcomes_pooled:
        disposition = CompoundTemporalPopulationDisposition.INELIGIBLE_OUTCOMES_POOLED
    elif forward_observed:
        disposition = CompoundTemporalPopulationDisposition.ELIGIBLE_FORWARD_UNPOOLED
    else:
        disposition = CompoundTemporalPopulationDisposition.INELIGIBLE_NOT_FORWARD
    return CompoundTemporalPopulationAssessment(
        source_population_sha256=source_population_sha256,
        provider_economics_sha256=provider_economics_sha256,
        forward_observed=forward_observed,
        outcomes_pooled=outcomes_pooled,
        disposition=disposition,
        eligible_for_strict_replication_gate=(
            disposition
            is CompoundTemporalPopulationDisposition.ELIGIBLE_FORWARD_UNPOOLED
        ),
    )


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

    def __post_init__(self) -> None:
        if self.fold_id not in _CANONICAL_FOLDS:
            raise CiboCompoundCapitalError(
                "compound economic fold result must be WF1..WF4"
            )
        if type(self.treatment_status) is not Genc9EconomicGateStatus:
            raise CiboCompoundCapitalError(
                "compound economic fold treatment status is invalid"
            )
        for name in (
            "safety_no_worse",
            "strict_growth_or_efficiency_improvement",
            "passed",
        ):
            if type(getattr(self, name)) is not bool:
                raise CiboCompoundCapitalError(
                    f"compound economic fold result {name} must be bool"
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
                "compound economic fold failed dimensions are invalid"
            )
        expected_pass = (
            self.treatment_status
            is Genc9EconomicGateStatus.ELIGIBLE_FOR_FURTHER_RESEARCH
            and self.safety_no_worse
            and self.strict_growth_or_efficiency_improvement
            and not self.failed_dimensions
        )
        if self.passed != expected_pass:
            raise CiboCompoundCapitalError(
                "compound economic fold pass/status drift"
            )


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



class TraderLabBurnedTemporalVerdict(StrEnum):
    """Technical Trader Lab verdict for reused temporal research only."""

    MECHANICS_REPLAYED = "MECHANICS_REPLAYED"
    MECHANICS_REJECTED = "MECHANICS_REJECTED"


@dataclass(frozen=True, slots=True)
class TraderLabBurnedTemporalReplicationGate:
    """Used-holdout temporal mechanics result; never economic replication."""

    research_id: str
    fold_count: int
    source_trace_sha256: str
    verdict: TraderLabBurnedTemporalVerdict
    dependency_breach_fold_count: int
    capacity_breach_fold_count: int
    burned_research: bool = True
    same_policy_mechanics: bool = True
    outcomes_pooled: bool = False
    forward_observed: bool = False
    economic_replication_claimed: bool = False
    production_policy_selected: bool = False
    certification_ready: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if not self.research_id:
            raise CiboCompoundCapitalError(
                "Trader Lab burned temporal research identity is required"
            )
        if (
            not isinstance(self.fold_count, int)
            or isinstance(self.fold_count, bool)
            or self.fold_count < 2
        ):
            raise CiboCompoundCapitalError(
                "Trader Lab burned temporal gate requires at least two folds"
            )
        _sha(self.source_trace_sha256, "source_trace_sha256")
        if type(self.verdict) is not TraderLabBurnedTemporalVerdict:
            raise CiboCompoundCapitalError(
                "Trader Lab burned temporal verdict is invalid"
            )
        for name in (
            "dependency_breach_fold_count",
            "capacity_breach_fold_count",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, int)
                or isinstance(value, bool)
                or value < 0
                or value > self.fold_count
            ):
                raise CiboCompoundCapitalError(
                    f"Trader Lab burned temporal {name} is invalid"
                )
        if not self.burned_research or not self.same_policy_mechanics:
            raise CiboCompoundCapitalError(
                "Trader Lab burned temporal gate must remain used-holdout mechanics"
            )
        for name in (
            "outcomes_pooled",
            "forward_observed",
            "economic_replication_claimed",
            "production_policy_selected",
            "certification_ready",
            "productive_authority",
        ):
            if type(getattr(self, name)) is not bool or getattr(self, name):
                raise CiboCompoundCapitalError(
                    "Trader Lab burned temporal gate cannot claim forward, "
                    "economic, production, certification, or productive authority"
                )
        expected = (
            TraderLabBurnedTemporalVerdict.MECHANICS_REPLAYED
            if self.same_policy_mechanics
            else TraderLabBurnedTemporalVerdict.MECHANICS_REJECTED
        )
        if self.verdict is not expected:
            raise CiboCompoundCapitalError(
                "Trader Lab burned temporal verdict/mechanics drift"
            )


def evaluate_trader_lab_burned_temporal_replication(
    *,
    report: CompoundTemporalReplicationReport,
    source_trace_sha256: str,
) -> TraderLabBurnedTemporalReplicationGate:
    """Approve temporal mechanics on a reused holdout without forward laundering."""

    if not isinstance(report, CompoundTemporalReplicationReport):
        raise CiboCompoundCapitalError(
            "Trader Lab burned temporal gate requires canonical replication report"
        )
    report.__post_init__()
    _sha(source_trace_sha256, "source_trace_sha256")
    if (
        report.outcomes_pooled_across_folds
        or report.economic_replication_claimed
        or report.certification_ready
    ):
        raise CiboCompoundCapitalError(
            "Trader Lab burned temporal gate rejects economic/certification claims"
        )
    verdict = (
        TraderLabBurnedTemporalVerdict.MECHANICS_REPLAYED
        if report.same_policy_mechanics_all_folds
        else TraderLabBurnedTemporalVerdict.MECHANICS_REJECTED
    )
    return TraderLabBurnedTemporalReplicationGate(
        research_id=report.research_id,
        fold_count=report.fold_count,
        source_trace_sha256=source_trace_sha256,
        verdict=verdict,
        dependency_breach_fold_count=report.dependency_breach_fold_count,
        capacity_breach_fold_count=report.capacity_breach_fold_count,
        burned_research=True,
        same_policy_mechanics=report.same_policy_mechanics_all_folds,
        outcomes_pooled=False,
        forward_observed=False,
        economic_replication_claimed=False,
        production_policy_selected=False,
        certification_ready=False,
        productive_authority=False,
    )
