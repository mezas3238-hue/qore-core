"""Preregistered non-compensatory economic gate for GEN-C9.

The gate compares every treatment to the single GEN-C9 control without a
weighted score. Safety deterioration cannot be compensated by higher return.
Passing this gate is research eligibility only, never production promotion.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum

from qore.infrastructure.cibo_compound_capital import CiboCompoundCapitalError
from qore.infrastructure.cibo_robust_growth_ruin_capacity import (
    Genc9CandidateRole,
    Genc9CandidateSummary,
    Genc9ResearchReport,
)

GENC9_ECONOMIC_GATE_ID = "CIBO_GENC9_NONCOMPENSATORY_ECONOMIC_GATE_V1"
GENC9_ECONOMIC_GATE_FROZEN_AT = datetime(2026, 9, 30, 13, 40, tzinfo=UTC)
GENC9_ECONOMIC_GATE_SHA256 = (
    "sha256:ab3152b1b17ec4fbc740608c46884aa482589c1ec62af92735b81e06c2763889"
)


class Genc9EconomicGateStatus(StrEnum):
    CONTROL = "CONTROL"
    ELIGIBLE_FOR_FURTHER_RESEARCH = "ELIGIBLE_FOR_FURTHER_RESEARCH"
    REJECTED_SAFETY_DETERIORATION = "REJECTED_SAFETY_DETERIORATION"
    REJECTED_NO_STRICT_ECONOMIC_IMPROVEMENT = (
        "REJECTED_NO_STRICT_ECONOMIC_IMPROVEMENT"
    )


@dataclass(frozen=True, slots=True)
class Genc9EconomicGateRow:
    candidate_id: str
    status: Genc9EconomicGateStatus
    safety_no_worse: bool
    strict_growth_or_efficiency_improvement: bool
    failed_dimensions: tuple[str, ...]
    weighted_score_used: bool = False
    production_promotion: bool = False

    def __post_init__(self) -> None:
        if not self.candidate_id:
            raise CiboCompoundCapitalError(
                "GEN-C9 economic gate candidate_id is required"
            )
        if type(self.status) is not Genc9EconomicGateStatus:
            raise CiboCompoundCapitalError(
                "GEN-C9 economic gate status is invalid"
            )
        if len(self.failed_dimensions) != len(set(self.failed_dimensions)):
            raise CiboCompoundCapitalError(
                "GEN-C9 failed dimensions must be unique"
            )
        if self.weighted_score_used or self.production_promotion:
            raise CiboCompoundCapitalError(
                "GEN-C9 economic gate cannot score/promote production"
            )


@dataclass(frozen=True, slots=True)
class Genc9EconomicGateReport:
    research_id: str
    gate_id: str
    gate_sha256: str
    gate_frozen_at: datetime
    control_candidate_id: str
    rows: tuple[Genc9EconomicGateRow, ...]
    economic_gate_preregistered: bool = True
    winner_candidate_id: None = None
    weighted_score_used: bool = False
    production_policy_selected: bool = False
    certification_ready: bool = False

    def __post_init__(self) -> None:
        if not self.research_id or not self.control_candidate_id:
            raise CiboCompoundCapitalError(
                "GEN-C9 economic gate report identity is required"
            )
        if self.gate_id != GENC9_ECONOMIC_GATE_ID:
            raise CiboCompoundCapitalError(
                "GEN-C9 economic gate identity drift"
            )
        if self.gate_sha256 != GENC9_ECONOMIC_GATE_SHA256:
            raise CiboCompoundCapitalError(
                "GEN-C9 economic gate digest drift"
            )
        if self.gate_frozen_at != GENC9_ECONOMIC_GATE_FROZEN_AT:
            raise CiboCompoundCapitalError(
                "GEN-C9 economic gate freeze drift"
            )
        candidate_ids = tuple(item.candidate_id for item in self.rows)
        if len(candidate_ids) != len(set(candidate_ids)):
            raise CiboCompoundCapitalError(
                "GEN-C9 economic gate rows must be unique"
            )
        if self.control_candidate_id not in candidate_ids:
            raise CiboCompoundCapitalError(
                "GEN-C9 economic gate control row is missing"
            )
        if (
            not self.economic_gate_preregistered
            or self.winner_candidate_id is not None
            or self.weighted_score_used
            or self.production_policy_selected
            or self.certification_ready
        ):
            raise CiboCompoundCapitalError(
                "GEN-C9 economic gate governance drift"
            )


def evaluate_genc9_economic_gate(
    report: Genc9ResearchReport,
) -> Genc9EconomicGateReport:
    """Apply the frozen non-compensatory gate to a descriptive GEN-C9 report."""

    if not isinstance(report, Genc9ResearchReport):
        raise CiboCompoundCapitalError(
            "GEN-C9 economic gate requires canonical research report"
        )
    controls = tuple(
        item
        for item in report.summaries
        if item.role is Genc9CandidateRole.CONTROL
    )
    if len(controls) != 1:
        raise CiboCompoundCapitalError(
            "GEN-C9 economic gate requires exactly one control summary"
        )
    control = controls[0]
    rows = tuple(
        _evaluate(control=control, candidate=item)
        for item in report.summaries
    )
    return Genc9EconomicGateReport(
        research_id=report.research_id,
        gate_id=GENC9_ECONOMIC_GATE_ID,
        gate_sha256=GENC9_ECONOMIC_GATE_SHA256,
        gate_frozen_at=GENC9_ECONOMIC_GATE_FROZEN_AT,
        control_candidate_id=control.candidate_id,
        rows=rows,
        economic_gate_preregistered=True,
        winner_candidate_id=None,
        weighted_score_used=False,
        production_policy_selected=False,
        certification_ready=False,
    )


def _evaluate(
    *,
    control: Genc9CandidateSummary,
    candidate: Genc9CandidateSummary,
) -> Genc9EconomicGateRow:
    if candidate.candidate_id == control.candidate_id:
        return Genc9EconomicGateRow(
            candidate_id=candidate.candidate_id,
            status=Genc9EconomicGateStatus.CONTROL,
            safety_no_worse=True,
            strict_growth_or_efficiency_improvement=False,
            failed_dimensions=(),
        )
    if candidate.numeraire is not control.numeraire:
        raise CiboCompoundCapitalError(
            "GEN-C9 economic gate cannot compare mixed numeraires"
        )
    if candidate.scenario_ids != control.scenario_ids:
        raise CiboCompoundCapitalError(
            "GEN-C9 economic gate requires identical scenario coverage"
        )

    failed: list[str] = []
    _no_more(
        failed,
        "ruin_path_count",
        candidate.ruin_path_count,
        control.ruin_path_count,
    )
    _no_more(
        failed,
        "capacity_breach_path_count",
        candidate.capacity_breach_path_count,
        control.capacity_breach_path_count,
    )
    _no_more(
        failed,
        "p99_max_drawdown",
        candidate.p99_max_drawdown,
        control.p99_max_drawdown,
    )
    _no_more(
        failed,
        "maximum_drawdown",
        candidate.maximum_drawdown,
        control.maximum_drawdown,
    )
    _no_more(
        failed,
        "maximum_time_underwater_minutes",
        candidate.maximum_time_underwater_minutes,
        control.maximum_time_underwater_minutes,
    )
    _no_more(
        failed,
        "p95_recovery_minutes",
        candidate.p95_recovery_minutes,
        control.p95_recovery_minutes,
    )
    _no_more(
        failed,
        "maximum_peak_plausible_loss",
        candidate.maximum_peak_plausible_loss,
        control.maximum_peak_plausible_loss,
    )
    _no_less(
        failed,
        "minimum_realized_capital",
        candidate.minimum_realized_capital,
        control.minimum_realized_capital,
    )
    _no_less(
        failed,
        "minimum_ending_capital",
        candidate.minimum_ending_capital,
        control.minimum_ending_capital,
    )
    _no_less(
        failed,
        "positive_ending_delta_paths",
        candidate.positive_ending_delta_paths,
        control.positive_ending_delta_paths,
    )
    safety_no_worse = not failed

    strict_improvement = any(
        (
            candidate.median_ending_capital
            > control.median_ending_capital,
            candidate.minimum_ending_multiple
            > control.minimum_ending_multiple,
            candidate.median_ending_multiple
            > control.median_ending_multiple,
            candidate.minimum_return_per_peak_plausible_loss
            > control.minimum_return_per_peak_plausible_loss,
        )
    )

    if not safety_no_worse:
        status = Genc9EconomicGateStatus.REJECTED_SAFETY_DETERIORATION
    elif not strict_improvement:
        status = (
            Genc9EconomicGateStatus.REJECTED_NO_STRICT_ECONOMIC_IMPROVEMENT
        )
    else:
        status = Genc9EconomicGateStatus.ELIGIBLE_FOR_FURTHER_RESEARCH

    return Genc9EconomicGateRow(
        candidate_id=candidate.candidate_id,
        status=status,
        safety_no_worse=safety_no_worse,
        strict_growth_or_efficiency_improvement=strict_improvement,
        failed_dimensions=tuple(failed),
        weighted_score_used=False,
        production_promotion=False,
    )


def _no_more(
    failed: list[str],
    name: str,
    candidate: object,
    control: object,
) -> None:
    if candidate > control:
        failed.append(name)


def _no_less(
    failed: list[str],
    name: str,
    candidate: object,
    control: object,
) -> None:
    if candidate < control:
        failed.append(name)
