"""Terminal semantics for CE2I T08/T12/T13 fresh-OOS utility reports.

These reports already separate population/readiness failures from economic
failures.  Architect 2 must not keep a sufficiently observed hypothesis open
forever: once the preregistered evidence surface is complete, economic failure
is a valid falsification.

This module does not build the fresh population, consume Phase22 V2, refit a
policy, authorize runtime behavior, or mutate the canonical ledger.
"""

from __future__ import annotations

from dataclasses import dataclass

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_phase20_qualification_plan import (
    FROZEN_PHASE20D_QUALIFICATION_PLAN,
)
from qore.infrastructure.cibo_ce2i_phase20_t08_oos_ablation import (
    T08NettingOosAblationReport,
)
from qore.infrastructure.cibo_ce2i_phase20_t12_oos_utility import (
    Phase20T12UtilityReport,
)
from qore.infrastructure.cibo_ce2i_phase20_t13_oos_utility import (
    Phase20T13UtilityReport,
)

COMPLETED = "COMPLETED_AND_PROVEN"
FALSIFIED = "FALSIFIED_AND_CLOSED"
WAITING = "EXTERNAL_DEPENDENCY_BLOCKED"


@dataclass(frozen=True, slots=True)
class Ce2iFreshUtilityTerminalResult:
    workstream_id: str
    evidence_surface_complete: bool
    fresh_oos_utility_demonstrated: bool
    terminal_ready: bool
    terminal_recommendation: str | None
    remaining_blockers: tuple[str, ...]
    outcome_refit_performed: bool
    canonical_ledger_modified: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if self.workstream_id not in {"T08", "T12", "T13"}:
            raise CiboCapitalManagementError(
                "CE2I fresh utility terminal workstream unsupported"
            )
        expected_terminal = self.evidence_surface_complete
        if self.terminal_ready != expected_terminal:
            raise CiboCapitalManagementError(
                "CE2I fresh utility terminal readiness drift"
            )
        expected: str | None = None
        if expected_terminal:
            expected = (
                COMPLETED
                if self.fresh_oos_utility_demonstrated
                else FALSIFIED
            )
        if self.terminal_recommendation != expected:
            raise CiboCapitalManagementError(
                "CE2I fresh utility terminal recommendation drift"
            )
        if self.outcome_refit_performed:
            raise CiboCapitalManagementError(
                "CE2I fresh utility terminal result cannot use outcome refit"
            )
        if self.canonical_ledger_modified or self.productive_authority:
            raise CiboCapitalManagementError(
                "CE2I fresh utility terminal result exceeded authority"
            )


def terminalize_t08(
    report: T08NettingOosAblationReport,
) -> Ce2iFreshUtilityTerminalResult:
    if not isinstance(report, T08NettingOosAblationReport):
        raise CiboCapitalManagementError(
            "T08 terminalization requires canonical OOS report"
        )
    complete = (
        report.sample_size >= report.minimum_epochs
        and len(report.folds) == report.required_folds
        and report.mapping_evidence_bound
        and report.correlation_evidence_bound
    )
    remaining = () if complete else tuple(
        item
        for item in report.blockers
        if (
            item.startswith("T08_OOS_MINIMUM_EPOCHS_NOT_MET")
            or item.startswith("T08_OOS_FOLD_COVERAGE_NOT_MET")
            or item == "T08_OOS_RISK_MAPPING_EVIDENCE_NOT_BOUND"
            or item == "T08_OOS_CORRELATION_EVIDENCE_NOT_BOUND"
        )
    )
    return Ce2iFreshUtilityTerminalResult(
        workstream_id="T08",
        evidence_surface_complete=complete,
        fresh_oos_utility_demonstrated=report.fresh_oos_utility_demonstrated,
        terminal_ready=complete,
        terminal_recommendation=(
            COMPLETED
            if complete and report.fresh_oos_utility_demonstrated
            else FALSIFIED if complete else None
        ),
        remaining_blockers=remaining,
        outcome_refit_performed=False,
    )


def terminalize_t12(
    report: Phase20T12UtilityReport,
) -> Ce2iFreshUtilityTerminalResult:
    if not isinstance(report, Phase20T12UtilityReport):
        raise CiboCapitalManagementError(
            "T12 terminalization requires canonical OOS utility report"
        )
    data_blockers = tuple(
        item
        for item in report.blockers
        if _is_t12_data_blocker(item)
    )
    complete = (
        report.population_ready
        and report.candidate_instances > 0
        and report.treatment_selected_instances > 0
        and report.control_selected_instances > 0
        and report.candidate_outcome_coverage
        >= FROZEN_PHASE20D_QUALIFICATION_PLAN.minimum_candidate_outcome_coverage
        and report.treatment_selected_outcome_coverage
        >= FROZEN_PHASE20D_QUALIFICATION_PLAN.required_selected_outcome_coverage
        and report.control_selected_outcome_coverage
        >= FROZEN_PHASE20D_QUALIFICATION_PLAN.required_selected_outcome_coverage
        and len(report.fold_treatment_net_delta_usd)
        == FROZEN_PHASE20D_QUALIFICATION_PLAN.fold_count
        and len(report.fold_control_net_delta_usd)
        == FROZEN_PHASE20D_QUALIFICATION_PLAN.fold_count
        and not data_blockers
    )
    return Ce2iFreshUtilityTerminalResult(
        workstream_id="T12",
        evidence_surface_complete=complete,
        fresh_oos_utility_demonstrated=report.fresh_oos_utility_demonstrated,
        terminal_ready=complete,
        terminal_recommendation=(
            COMPLETED
            if complete and report.fresh_oos_utility_demonstrated
            else FALSIFIED if complete else None
        ),
        remaining_blockers=data_blockers,
        outcome_refit_performed=report.outcome_refit_performed,
    )


def terminalize_t13(
    report: Phase20T13UtilityReport,
) -> Ce2iFreshUtilityTerminalResult:
    if not isinstance(report, Phase20T13UtilityReport):
        raise CiboCapitalManagementError(
            "T13 terminalization requires canonical OOS utility report"
        )
    data_blockers = tuple(
        item
        for item in report.blockers
        if _is_t13_data_blocker(item)
    )
    complete = (
        report.population_ready
        and report.candidate_instances > 0
        and report.baseline_selected_instances > 0
        and report.treatment_selected_instances > 0
        and report.candidate_outcome_coverage
        >= FROZEN_PHASE20D_QUALIFICATION_PLAN.minimum_candidate_outcome_coverage
        and report.baseline_selected_outcome_coverage
        >= FROZEN_PHASE20D_QUALIFICATION_PLAN.required_baseline_selected_outcome_coverage
        and report.treatment_selected_outcome_coverage
        >= FROZEN_PHASE20D_QUALIFICATION_PLAN.required_selected_outcome_coverage
        and len(report.fold_baseline_net_delta_usd)
        == FROZEN_PHASE20D_QUALIFICATION_PLAN.fold_count
        and len(report.fold_treatment_net_delta_usd)
        == FROZEN_PHASE20D_QUALIFICATION_PLAN.fold_count
        and not data_blockers
    )
    return Ce2iFreshUtilityTerminalResult(
        workstream_id="T13",
        evidence_surface_complete=complete,
        fresh_oos_utility_demonstrated=report.fresh_oos_utility_demonstrated,
        terminal_ready=complete,
        terminal_recommendation=(
            COMPLETED
            if complete and report.fresh_oos_utility_demonstrated
            else FALSIFIED if complete else None
        ),
        remaining_blockers=data_blockers,
        outcome_refit_performed=report.outcome_refit_performed,
    )


def _is_t12_data_blocker(value: str) -> bool:
    return (
        "COVERAGE_INCOMPLETE" in value
        or "OUTCOME_COVERAGE" in value
        or value
        in {
            "T12_NO_TREATMENT_SELECTED_ROWS",
            "T12_NO_CONTROL_SELECTED_ROWS",
            "T12_REALIZED_EXECUTION_ECONOMICS_COMPLETE",
            "T12_TEMPORAL_FOLD_COUNT_INCOMPLETE",
        }
    )


def _is_t13_data_blocker(value: str) -> bool:
    return (
        "COVERAGE_INCOMPLETE" in value
        or "OUTCOME_COVERAGE" in value
        or value
        in {
            "T13_NO_BASELINE_SELECTED_ROWS",
            "T13_NO_TREATMENT_SELECTED_ROWS",
            "T13_REALIZED_EXECUTION_ECONOMICS_COMPLETE",
            "T13_TEMPORAL_FOLD_COUNT_INCOMPLETE",
        }
    )
