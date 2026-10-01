"""Fixed fresh-OOS utility analysis for CE2I T13 Drawdown Reserve.

Treatment is the preregistered one-minimum-seed reserve shadow policy. Baseline
is the already-frozen V3 policy for the same sealed forward evidence.

T13 exists to keep capital unused when reserve has greater survival/optionality
value. The utility contract therefore does not require treatment to maximize
absolute dollars versus baseline. It requires:

- the frozen Phase20D population/coverage/execution gates;
- strictly positive treatment realized delta in every contiguous fold;
- strictly positive aggregate treatment realized delta;
- treatment settlement-cash drawdown no worse than baseline; and
- treatment capital productivity strictly above baseline.

Those sign/non-worse gates contain no fitted magnitude threshold. Missing
baseline/treatment outcomes are never imputed. Population membership comes only
from Phase20T13OosReadiness. The report grants no runtime authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_phase20_qualification import (
    Phase20QualificationRow,
)
from qore.infrastructure.cibo_ce2i_phase20_qualification_plan import (
    FROZEN_PHASE20D_QUALIFICATION_PLAN,
    phase20d_qualification_plan_sha256,
)
from qore.infrastructure.cibo_ce2i_phase20_t13_oos_readiness import (
    Phase20T13OosReadiness,
)
from qore.infrastructure.cibo_ce2i_phase20_t13_shadow_policy import (
    T13_SHADOW_POLICY_ID,
    t13_shadow_policy_sha256,
)
from qore.infrastructure.cibo_ce2i_phase20_t13_shadow_treatment_store import (
    T13ShadowTreatmentSeal,
)

T13_UTILITY_CONTRACT_ID = "CIBO_T13_DRAWDOWN_RESERVE_UTILITY_V1"


@dataclass(frozen=True, slots=True)
class Phase20T13UtilityReport:
    contract_id: str
    qualification_plan_sha256: str
    t13_policy_id: str
    t13_policy_sha256: str
    population_ready: bool
    decision_epochs: int
    candidate_instances: int
    baseline_selected_instances: int
    treatment_selected_instances: int
    selection_changed_epochs: int
    total_shadow_reserved_risk_usd: Decimal
    candidate_outcome_coverage: Decimal
    baseline_selected_outcome_coverage: Decimal
    treatment_selected_outcome_coverage: Decimal
    baseline_net_delta_usd: Decimal
    treatment_net_delta_usd: Decimal
    baseline_settlement_cash_drawdown_usd: Decimal
    treatment_settlement_cash_drawdown_usd: Decimal
    baseline_capital_productivity: Decimal
    treatment_capital_productivity: Decimal
    fold_baseline_net_delta_usd: tuple[Decimal, ...]
    fold_treatment_net_delta_usd: tuple[Decimal, ...]
    fresh_oos_utility_demonstrated: bool
    outcome_refit_performed: bool
    runtime_authority: bool
    blockers: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.contract_id != T13_UTILITY_CONTRACT_ID:
            raise CiboCapitalManagementError(
                "Phase20 T13 utility contract identity drift"
            )
        if (
            self.qualification_plan_sha256
            != phase20d_qualification_plan_sha256()
        ):
            raise CiboCapitalManagementError(
                "Phase20 T13 utility qualification plan digest drift"
            )
        if self.t13_policy_id != T13_SHADOW_POLICY_ID:
            raise CiboCapitalManagementError(
                "Phase20 T13 utility policy identity drift"
            )
        if self.t13_policy_sha256 != t13_shadow_policy_sha256():
            raise CiboCapitalManagementError(
                "Phase20 T13 utility policy digest drift"
            )
        for name in (
            "decision_epochs",
            "candidate_instances",
            "baseline_selected_instances",
            "treatment_selected_instances",
            "selection_changed_epochs",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, int)
                or isinstance(value, bool)
                or value < 0
            ):
                raise CiboCapitalManagementError(
                    f"Phase20 T13 utility {name} must be non-negative int"
                )
        for name in (
            "total_shadow_reserved_risk_usd",
            "baseline_net_delta_usd",
            "treatment_net_delta_usd",
            "baseline_settlement_cash_drawdown_usd",
            "treatment_settlement_cash_drawdown_usd",
            "baseline_capital_productivity",
            "treatment_capital_productivity",
        ):
            value = getattr(self, name)
            if not isinstance(value, Decimal) or not value.is_finite():
                raise CiboCapitalManagementError(
                    f"Phase20 T13 utility {name} must be finite Decimal"
                )
        if self.total_shadow_reserved_risk_usd < 0:
            raise CiboCapitalManagementError(
                "Phase20 T13 utility reserved risk must be non-negative"
            )
        for name in (
            "candidate_outcome_coverage",
            "baseline_selected_outcome_coverage",
            "treatment_selected_outcome_coverage",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, Decimal)
                or not value.is_finite()
                or value < 0
                or value > 1
            ):
                raise CiboCapitalManagementError(
                    f"Phase20 T13 utility {name} must be Decimal in [0,1]"
                )
        if len(self.fold_baseline_net_delta_usd) != len(
            self.fold_treatment_net_delta_usd
        ):
            raise CiboCapitalManagementError(
                "Phase20 T13 utility fold vector length drift"
            )
        if (
            len(self.fold_treatment_net_delta_usd)
            != FROZEN_PHASE20D_QUALIFICATION_PLAN.fold_count
        ):
            raise CiboCapitalManagementError(
                "Phase20 T13 utility report requires frozen fold count"
            )
        for values, label in (
            (self.fold_baseline_net_delta_usd, "baseline fold deltas"),
            (self.fold_treatment_net_delta_usd, "treatment fold deltas"),
        ):
            if any(
                not isinstance(item, Decimal) or not item.is_finite()
                for item in values
            ):
                raise CiboCapitalManagementError(
                    f"Phase20 T13 utility {label} must be finite Decimal"
                )
        for name in (
            "population_ready",
            "fresh_oos_utility_demonstrated",
            "outcome_refit_performed",
            "runtime_authority",
        ):
            if type(getattr(self, name)) is not bool:
                raise CiboCapitalManagementError(
                    f"Phase20 T13 utility {name} must be bool"
                )
        if self.outcome_refit_performed:
            raise CiboCapitalManagementError(
                "Phase20 T13 utility cannot refit from outcomes"
            )
        if self.runtime_authority:
            raise CiboCapitalManagementError(
                "Phase20 T13 utility cannot grant runtime authority"
            )
        if self.fresh_oos_utility_demonstrated != (
            self.population_ready and not self.blockers
        ):
            raise CiboCapitalManagementError(
                "Phase20 T13 utility result/blocker drift"
            )


def assess_phase20_t13_oos_utility(
    *,
    qualification_rows: tuple[Phase20QualificationRow, ...],
    readiness: Phase20T13OosReadiness,
    treatment_decisions: tuple[T13ShadowTreatmentSeal, ...],
) -> Phase20T13UtilityReport:
    """Score T13 baseline versus preregistered reserve treatment without refit."""

    if not isinstance(readiness, Phase20T13OosReadiness):
        raise CiboCapitalManagementError(
            "Phase20 T13 utility requires canonical readiness"
        )
    if not isinstance(qualification_rows, tuple) or any(
        not isinstance(item, Phase20QualificationRow)
        for item in qualification_rows
    ):
        raise CiboCapitalManagementError(
            "Phase20 T13 utility requires canonical qualification rows"
        )
    if not isinstance(treatment_decisions, tuple) or any(
        not isinstance(item, T13ShadowTreatmentSeal)
        for item in treatment_decisions
    ):
        raise CiboCapitalManagementError(
            "Phase20 T13 utility requires canonical treatment decisions"
        )

    decision_set = set(readiness.decision_sha256s)
    treatment_by_sha = {
        item.decision_evidence_sha256: item
        for item in treatment_decisions
        if item.decision_evidence_sha256 in decision_set
    }
    scoped_treatments = tuple(
        item
        for item in treatment_decisions
        if item.decision_evidence_sha256 in decision_set
    )
    if len(treatment_by_sha) != len(scoped_treatments):
        raise CiboCapitalManagementError(
            "Phase20 T13 utility duplicate treatment evidence"
        )

    blockers = list(readiness.blockers)
    if readiness.ready_for_utility_analysis and set(treatment_by_sha) != decision_set:
        blockers.append("T13_UTILITY_TREATMENT_DECISION_COVERAGE_INCOMPLETE")

    scoped = tuple(
        item
        for item in qualification_rows
        if item.decision_evidence_sha256 in decision_set
    )
    if len(scoped) != readiness.candidate_instances:
        blockers.append("T13_UTILITY_CANDIDATE_ROW_COVERAGE_INCOMPLETE")

    baseline_rows: list[Phase20QualificationRow] = []
    treatment_rows: list[Phase20QualificationRow] = []
    for row in scoped:
        treatment_seal = treatment_by_sha.get(row.decision_evidence_sha256)
        if treatment_seal is None:
            continue
        baseline_set = set(
            treatment_seal.baseline_selected_signal_fingerprints
        )
        treatment_set = set(
            treatment_seal.treatment_selected_signal_fingerprints
        )
        if row.policy_selected != (row.signal_fingerprint in baseline_set):
            raise CiboCapitalManagementError(
                "Phase20 T13 utility baseline selection binding drift"
            )
        if row.signal_fingerprint in baseline_set:
            baseline_rows.append(row)
        if row.signal_fingerprint in treatment_set:
            treatment_rows.append(row)

    baseline = tuple(baseline_rows)
    treatment = tuple(treatment_rows)
    if len(baseline) != readiness.baseline_selected_instances:
        blockers.append("T13_UTILITY_BASELINE_SELECTION_COVERAGE_INCOMPLETE")
    if len(treatment) != readiness.treatment_selected_instances:
        blockers.append("T13_UTILITY_TREATMENT_SELECTION_COVERAGE_INCOMPLETE")

    plan = FROZEN_PHASE20D_QUALIFICATION_PLAN
    candidate_coverage = _coverage(scoped)
    baseline_coverage = _coverage(baseline)
    treatment_coverage = _coverage(treatment)

    if scoped and candidate_coverage < plan.minimum_candidate_outcome_coverage:
        blockers.append(
            "T13_CANDIDATE_OUTCOME_COVERAGE_AT_LEAST_95_PERCENT"
        )
    if not baseline:
        blockers.append("T13_NO_BASELINE_SELECTED_ROWS")
    elif (
        baseline_coverage
        < plan.required_baseline_selected_outcome_coverage
    ):
        blockers.append("T13_BASELINE_SELECTED_OUTCOME_COVERAGE_COMPLETE")
    if not treatment:
        blockers.append("T13_NO_TREATMENT_SELECTED_ROWS")
    elif treatment_coverage < plan.required_selected_outcome_coverage:
        blockers.append("T13_TREATMENT_SELECTED_OUTCOME_COVERAGE_COMPLETE")

    baseline_execution_complete = _execution_complete(baseline)
    treatment_execution_complete = _execution_complete(treatment)
    if scoped and (
        not baseline_execution_complete
        or not treatment_execution_complete
    ):
        blockers.append("T13_REALIZED_EXECUTION_ECONOMICS_COMPLETE")

    baseline_net = _net(baseline)
    treatment_net = _net(treatment)
    baseline_dd = _drawdown(baseline)
    treatment_dd = _drawdown(treatment)
    baseline_productivity = _productivity(baseline)
    treatment_productivity = _productivity(treatment)
    baseline_folds, treatment_folds = _fold_deltas(
        baseline=baseline,
        treatment=treatment,
        treatments=treatment_by_sha,
        decision_sha256s=readiness.decision_sha256s,
    )
    total_reserved = sum(
        (
            item.shadow_reserved_risk_usd
            for item in scoped_treatments
        ),
        Decimal(0),
    )

    can_score = (
        readiness.ready_for_utility_analysis
        and len(scoped) == readiness.candidate_instances
        and len(baseline) == readiness.baseline_selected_instances
        and len(treatment) == readiness.treatment_selected_instances
        and candidate_coverage >= plan.minimum_candidate_outcome_coverage
        and baseline_coverage
        >= plan.required_baseline_selected_outcome_coverage
        and treatment_coverage >= plan.required_selected_outcome_coverage
        and baseline_execution_complete
        and treatment_execution_complete
        and len(baseline_folds) == plan.fold_count
        and len(treatment_folds) == plan.fold_count
    )

    if can_score:
        if total_reserved <= 0:
            blockers.append("T13_NO_POSITIVE_SHADOW_RESERVE_IN_OOS_POPULATION")
        if any(value <= 0 for value in treatment_folds):
            blockers.append("T13_EVERY_TEMPORAL_FOLD_TREATMENT_DELTA_POSITIVE")
        if treatment_net <= 0:
            blockers.append("T13_AGGREGATE_TREATMENT_DELTA_POSITIVE")
        if treatment_dd > baseline_dd:
            blockers.append(
                "T13_TREATMENT_SETTLEMENT_CASH_DRAWDOWN_NOT_ABOVE_BASELINE"
            )
        if treatment_productivity <= baseline_productivity:
            blockers.append(
                "T13_TREATMENT_CAPITAL_PRODUCTIVITY_STRICTLY_ABOVE_BASELINE"
            )
    elif (
        readiness.ready_for_utility_analysis
        and (
            len(baseline_folds) != plan.fold_count
            or len(treatment_folds) != plan.fold_count
        )
    ):
        blockers.append("T13_TEMPORAL_FOLD_COUNT_INCOMPLETE")

    blockers = list(dict.fromkeys(blockers))
    return Phase20T13UtilityReport(
        contract_id=T13_UTILITY_CONTRACT_ID,
        qualification_plan_sha256=phase20d_qualification_plan_sha256(),
        t13_policy_id=T13_SHADOW_POLICY_ID,
        t13_policy_sha256=t13_shadow_policy_sha256(),
        population_ready=readiness.ready_for_utility_analysis,
        decision_epochs=readiness.post_freeze_decision_epochs,
        candidate_instances=len(scoped),
        baseline_selected_instances=len(baseline),
        treatment_selected_instances=len(treatment),
        selection_changed_epochs=readiness.selection_changed_epochs,
        total_shadow_reserved_risk_usd=total_reserved,
        candidate_outcome_coverage=candidate_coverage,
        baseline_selected_outcome_coverage=baseline_coverage,
        treatment_selected_outcome_coverage=treatment_coverage,
        baseline_net_delta_usd=baseline_net,
        treatment_net_delta_usd=treatment_net,
        baseline_settlement_cash_drawdown_usd=baseline_dd,
        treatment_settlement_cash_drawdown_usd=treatment_dd,
        baseline_capital_productivity=baseline_productivity,
        treatment_capital_productivity=treatment_productivity,
        fold_baseline_net_delta_usd=baseline_folds,
        fold_treatment_net_delta_usd=treatment_folds,
        fresh_oos_utility_demonstrated=(
            readiness.ready_for_utility_analysis and not blockers
        ),
        outcome_refit_performed=False,
        runtime_authority=False,
        blockers=tuple(blockers),
    )


def _coverage(rows: tuple[Phase20QualificationRow, ...]) -> Decimal:
    if not rows:
        return Decimal(0)
    observed = sum(
        1 for item in rows if item.realized_net_pnl_usd is not None
    )
    return Decimal(observed) / Decimal(len(rows))


def _execution_complete(
    rows: tuple[Phase20QualificationRow, ...],
) -> bool:
    return bool(rows) and all(
        item.realized_net_pnl_usd is not None
        and item.executed_initial_stop_risk_usd == item.stop_risk_usd
        and item.capital_minutes is not None
        and item.capital_minutes > 0
        and item.outcome_observed_at is not None
        for item in rows
    )


def _net(rows: tuple[Phase20QualificationRow, ...]) -> Decimal:
    return sum(
        (
            item.realized_net_pnl_usd
            for item in rows
            if item.realized_net_pnl_usd is not None
        ),
        Decimal(0),
    )


def _productivity(
    rows: tuple[Phase20QualificationRow, ...],
) -> Decimal:
    denominator = sum(
        (
            item.executed_initial_stop_risk_usd * item.capital_minutes
            for item in rows
            if item.executed_initial_stop_risk_usd is not None
            and item.capital_minutes is not None
        ),
        Decimal(0),
    )
    return Decimal(0) if denominator <= 0 else _net(rows) / denominator


def _drawdown(
    rows: tuple[Phase20QualificationRow, ...],
) -> Decimal:
    events = tuple(
        sorted(
            (
                item.outcome_observed_at,
                item.signal_fingerprint,
                item.realized_net_pnl_usd,
            )
            for item in rows
            if item.outcome_observed_at is not None
            and item.realized_net_pnl_usd is not None
        )
    )
    cumulative = Decimal(0)
    peak = Decimal(0)
    maximum = Decimal(0)
    for _observed_at, _signal, pnl in events:
        cumulative += pnl
        peak = max(peak, cumulative)
        maximum = max(maximum, peak - cumulative)
    return maximum


def _fold_deltas(
    *,
    baseline: tuple[Phase20QualificationRow, ...],
    treatment: tuple[Phase20QualificationRow, ...],
    treatments: dict[str, T13ShadowTreatmentSeal],
    decision_sha256s: tuple[str, ...],
) -> tuple[tuple[Decimal, ...], tuple[Decimal, ...]]:
    if not decision_sha256s:
        return (), ()
    times: dict[str, datetime] = {}
    for sha in decision_sha256s:
        treatment_seal = treatments.get(sha)
        if treatment_seal is None:
            return (), ()
        times[sha] = treatment_seal.decision_at
    ordered = tuple(
        sorted(
            decision_sha256s,
            key=lambda sha: (times[sha], sha),
        )
    )
    fold_count = FROZEN_PHASE20D_QUALIFICATION_PLAN.fold_count
    base, remainder = divmod(len(ordered), fold_count)
    baseline_result: list[Decimal] = []
    treatment_result: list[Decimal] = []
    start = 0
    for index in range(fold_count):
        count = base + (1 if index < remainder else 0)
        fold_ids = set(ordered[start : start + count])
        start += count
        baseline_result.append(
            _net(
                tuple(
                    row
                    for row in baseline
                    if row.decision_evidence_sha256 in fold_ids
                )
            )
        )
        treatment_result.append(
            _net(
                tuple(
                    row
                    for row in treatment
                    if row.decision_evidence_sha256 in fold_ids
                )
            )
        )
    return tuple(baseline_result), tuple(treatment_result)
