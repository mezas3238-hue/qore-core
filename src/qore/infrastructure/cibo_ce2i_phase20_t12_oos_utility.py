"""Fixed fresh-OOS utility analysis for CE2I T12 tool eligibility.

Treatment is the already-frozen V3 policy with regime-driven tool eligibility.
Control is the preregistered T12 shadow decision that neutralizes only the
enabled_tools intervention while preserving the same causal evidence, regime
posture and MPC plan.

Population membership is fixed by Phase20T12OosReadiness. Economic scoring
consumes only canonical Phase20QualificationRow outcomes plus the durable T12
shadow seals. Missing control-only outcomes are never imputed. The scorer
reuses Phase20D coverage/execution semantics and compares treatment directly
with the fixed T12-neutral control. It grants no runtime authority.
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
from qore.infrastructure.cibo_ce2i_phase20_t12_oos_readiness import (
    Phase20T12OosReadiness,
)
from qore.infrastructure.cibo_ce2i_phase20_t12_shadow_policy import (
    T12_SHADOW_POLICY_ID,
    t12_shadow_policy_sha256,
)
from qore.infrastructure.cibo_ce2i_phase20_t12_shadow_store import (
    T12ShadowDecisionSeal,
)

T12_UTILITY_CONTRACT_ID = "CIBO_T12_REGIME_TOOL_ELIGIBILITY_UTILITY_V1"


@dataclass(frozen=True, slots=True)
class Phase20T12UtilityReport:
    contract_id: str
    qualification_plan_sha256: str
    t12_policy_id: str
    t12_policy_sha256: str
    population_ready: bool
    decision_epochs: int
    candidate_instances: int
    treatment_selected_instances: int
    control_selected_instances: int
    candidate_outcome_coverage: Decimal
    treatment_selected_outcome_coverage: Decimal
    control_selected_outcome_coverage: Decimal
    treatment_net_delta_usd: Decimal
    control_net_delta_usd: Decimal
    treatment_settlement_cash_drawdown_usd: Decimal
    control_settlement_cash_drawdown_usd: Decimal
    treatment_capital_productivity: Decimal
    control_capital_productivity: Decimal
    fold_treatment_net_delta_usd: tuple[Decimal, ...]
    fold_control_net_delta_usd: tuple[Decimal, ...]
    fold_incremental_net_delta_usd: tuple[Decimal, ...]
    fresh_oos_utility_demonstrated: bool
    outcome_refit_performed: bool
    runtime_authority: bool
    blockers: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.contract_id != T12_UTILITY_CONTRACT_ID:
            raise CiboCapitalManagementError(
                "Phase20 T12 utility contract identity drift"
            )
        if self.qualification_plan_sha256 != phase20d_qualification_plan_sha256():
            raise CiboCapitalManagementError(
                "Phase20 T12 utility qualification plan digest drift"
            )
        if self.t12_policy_id != T12_SHADOW_POLICY_ID:
            raise CiboCapitalManagementError(
                "Phase20 T12 utility policy identity drift"
            )
        if self.t12_policy_sha256 != t12_shadow_policy_sha256():
            raise CiboCapitalManagementError(
                "Phase20 T12 utility policy digest drift"
            )
        for name in (
            "decision_epochs",
            "candidate_instances",
            "treatment_selected_instances",
            "control_selected_instances",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, int)
                or isinstance(value, bool)
                or value < 0
            ):
                raise CiboCapitalManagementError(
                    f"Phase20 T12 utility {name} must be non-negative int"
                )
        for name in (
            "candidate_outcome_coverage",
            "treatment_selected_outcome_coverage",
            "control_selected_outcome_coverage",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, Decimal)
                or not value.is_finite()
                or value < 0
                or value > 1
            ):
                raise CiboCapitalManagementError(
                    f"Phase20 T12 utility {name} must be Decimal in [0,1]"
                )
        for name in (
            "treatment_net_delta_usd",
            "control_net_delta_usd",
            "treatment_settlement_cash_drawdown_usd",
            "control_settlement_cash_drawdown_usd",
            "treatment_capital_productivity",
            "control_capital_productivity",
        ):
            value = getattr(self, name)
            if not isinstance(value, Decimal) or not value.is_finite():
                raise CiboCapitalManagementError(
                    f"Phase20 T12 utility {name} must be finite Decimal"
                )
        for values, label in (
            (
                self.fold_treatment_net_delta_usd,
                "treatment fold deltas",
            ),
            (
                self.fold_control_net_delta_usd,
                "control fold deltas",
            ),
            (
                self.fold_incremental_net_delta_usd,
                "incremental fold deltas",
            ),
        ):
            if any(
                not isinstance(item, Decimal) or not item.is_finite()
                for item in values
            ):
                raise CiboCapitalManagementError(
                    f"Phase20 T12 utility {label} must be finite Decimal"
                )
        if not (
            len(self.fold_treatment_net_delta_usd)
            == len(self.fold_control_net_delta_usd)
            == len(self.fold_incremental_net_delta_usd)
        ):
            raise CiboCapitalManagementError(
                "Phase20 T12 utility fold vector length drift"
            )
        fold_count = len(self.fold_treatment_net_delta_usd)
        if fold_count not in {
            0,
            FROZEN_PHASE20D_QUALIFICATION_PLAN.fold_count,
        }:
            raise CiboCapitalManagementError(
                "Phase20 T12 utility report requires frozen fold count"
            )
        if (
            self.population_ready
            and fold_count != FROZEN_PHASE20D_QUALIFICATION_PLAN.fold_count
        ):
            raise CiboCapitalManagementError(
                "Phase20 T12 ready report requires frozen fold count"
            )
        for name in (
            "population_ready",
            "fresh_oos_utility_demonstrated",
            "outcome_refit_performed",
            "runtime_authority",
        ):
            if type(getattr(self, name)) is not bool:
                raise CiboCapitalManagementError(
                    f"Phase20 T12 utility {name} must be bool"
                )
        if self.outcome_refit_performed:
            raise CiboCapitalManagementError(
                "Phase20 T12 utility cannot refit from outcomes"
            )
        if self.runtime_authority:
            raise CiboCapitalManagementError(
                "Phase20 T12 utility cannot grant runtime authority"
            )
        if not isinstance(self.blockers, tuple) or any(
            not isinstance(item, str) or not item for item in self.blockers
        ):
            raise CiboCapitalManagementError(
                "Phase20 T12 utility blockers must be non-empty strings"
            )
        if len(self.blockers) != len(set(self.blockers)):
            raise CiboCapitalManagementError(
                "Phase20 T12 utility blockers must be unique"
            )
        expected_incremental = tuple(
            treatment - control
            for treatment, control in zip(
                self.fold_treatment_net_delta_usd,
                self.fold_control_net_delta_usd,
                strict=True,
            )
        )
        if self.fold_incremental_net_delta_usd != expected_incremental:
            raise CiboCapitalManagementError(
                "Phase20 T12 utility fold incremental drift"
            )
        if self.fresh_oos_utility_demonstrated != (
            self.population_ready and not self.blockers
        ):
            raise CiboCapitalManagementError(
                "Phase20 T12 utility result/blocker drift"
            )
        if self.fresh_oos_utility_demonstrated:
            plan = FROZEN_PHASE20D_QUALIFICATION_PLAN
            if (
                self.candidate_instances <= 0
                or self.treatment_selected_instances <= 0
                or self.control_selected_instances <= 0
                or self.candidate_outcome_coverage
                < plan.minimum_candidate_outcome_coverage
                or self.treatment_selected_outcome_coverage
                < plan.required_selected_outcome_coverage
                or self.control_selected_outcome_coverage
                < plan.required_selected_outcome_coverage
                or any(
                    value < 0
                    for value in self.fold_incremental_net_delta_usd
                )
                or self.treatment_net_delta_usd
                < self.control_net_delta_usd
                or self.treatment_settlement_cash_drawdown_usd
                > self.control_settlement_cash_drawdown_usd
                or self.treatment_capital_productivity
                <= self.control_capital_productivity
            ):
                raise CiboCapitalManagementError(
                    "Phase20 T12 utility PASS metric drift"
                )


def assess_phase20_t12_oos_utility(
    *,
    qualification_rows: tuple[Phase20QualificationRow, ...],
    readiness: Phase20T12OosReadiness,
    shadow_decisions: tuple[T12ShadowDecisionSeal, ...],
) -> Phase20T12UtilityReport:
    """Score T12 treatment versus its frozen neutral control without refit."""

    if not isinstance(readiness, Phase20T12OosReadiness):
        raise CiboCapitalManagementError(
            "Phase20 T12 utility requires canonical readiness"
        )
    if not isinstance(qualification_rows, tuple) or any(
        not isinstance(item, Phase20QualificationRow)
        for item in qualification_rows
    ):
        raise CiboCapitalManagementError(
            "Phase20 T12 utility requires canonical qualification rows"
        )
    if not isinstance(shadow_decisions, tuple) or any(
        not isinstance(item, T12ShadowDecisionSeal)
        for item in shadow_decisions
    ):
        raise CiboCapitalManagementError(
            "Phase20 T12 utility requires canonical shadow decisions"
        )

    decision_set = set(readiness.decision_sha256s)
    shadow_by_sha = {
        item.decision_evidence_sha256: item
        for item in shadow_decisions
        if item.decision_evidence_sha256 in decision_set
    }
    if len(shadow_by_sha) != len(
        tuple(
            item
            for item in shadow_decisions
            if item.decision_evidence_sha256 in decision_set
        )
    ):
        raise CiboCapitalManagementError(
            "Phase20 T12 utility duplicate shadow evidence"
        )

    blockers = list(readiness.blockers)
    if readiness.ready_for_utility_analysis and (
        set(shadow_by_sha) != decision_set
    ):
        blockers.append("T12_UTILITY_SHADOW_DECISION_COVERAGE_INCOMPLETE")

    scoped = tuple(
        item
        for item in qualification_rows
        if item.decision_evidence_sha256 in decision_set
    )
    if len(scoped) != readiness.candidate_instances:
        blockers.append("T12_UTILITY_CANDIDATE_ROW_COVERAGE_INCOMPLETE")

    treatment_rows: list[Phase20QualificationRow] = []
    control_rows: list[Phase20QualificationRow] = []
    for row in scoped:
        shadow = shadow_by_sha.get(row.decision_evidence_sha256)
        if shadow is None:
            continue
        treatment_set = set(
            shadow.treatment_selected_signal_fingerprints
        )
        control_set = set(
            shadow.control_selected_signal_fingerprints
        )
        if row.policy_selected != (
            row.signal_fingerprint in treatment_set
        ):
            raise CiboCapitalManagementError(
                "Phase20 T12 utility treatment selection binding drift"
            )
        if row.signal_fingerprint in treatment_set:
            treatment_rows.append(row)
        if row.signal_fingerprint in control_set:
            control_rows.append(row)

    treatment = tuple(treatment_rows)
    control = tuple(control_rows)
    if len(treatment) != readiness.treatment_selected_instances:
        blockers.append("T12_UTILITY_TREATMENT_SELECTION_COVERAGE_INCOMPLETE")
    if len(control) != readiness.control_selected_instances:
        blockers.append("T12_UTILITY_CONTROL_SELECTION_COVERAGE_INCOMPLETE")

    candidate_coverage = _coverage(scoped)
    treatment_coverage = _coverage(treatment)
    control_coverage = _coverage(control)
    plan = FROZEN_PHASE20D_QUALIFICATION_PLAN

    if scoped and candidate_coverage < plan.minimum_candidate_outcome_coverage:
        blockers.append(
            "T12_CANDIDATE_OUTCOME_COVERAGE_AT_LEAST_95_PERCENT"
        )
    if not treatment:
        blockers.append("T12_NO_TREATMENT_SELECTED_ROWS")
    elif treatment_coverage < plan.required_selected_outcome_coverage:
        blockers.append("T12_TREATMENT_SELECTED_OUTCOME_COVERAGE_COMPLETE")
    if not control:
        blockers.append("T12_NO_CONTROL_SELECTED_ROWS")
    elif control_coverage < plan.required_selected_outcome_coverage:
        blockers.append("T12_CONTROL_SELECTED_OUTCOME_COVERAGE_COMPLETE")

    treatment_execution_complete = _execution_complete(treatment)
    control_execution_complete = _execution_complete(control)
    if scoped and (
        not treatment_execution_complete
        or not control_execution_complete
    ):
        blockers.append("T12_REALIZED_EXECUTION_ECONOMICS_COMPLETE")

    treatment_net = _net(treatment)
    control_net = _net(control)
    treatment_dd = _drawdown(treatment)
    control_dd = _drawdown(control)
    treatment_productivity = _productivity(treatment)
    control_productivity = _productivity(control)
    treatment_folds, control_folds = _fold_deltas(
        treatment=treatment,
        control=control,
        shadows=shadow_by_sha,
        decision_sha256s=readiness.decision_sha256s,
    )
    incremental_folds = tuple(
        treatment_value - control_value
        for treatment_value, control_value in zip(
            treatment_folds,
            control_folds,
            strict=True,
        )
    )

    can_score = (
        readiness.ready_for_utility_analysis
        and len(scoped) == readiness.candidate_instances
        and len(treatment) == readiness.treatment_selected_instances
        and len(control) == readiness.control_selected_instances
        and candidate_coverage >= plan.minimum_candidate_outcome_coverage
        and treatment_coverage >= plan.required_selected_outcome_coverage
        and control_coverage >= plan.required_selected_outcome_coverage
        and treatment_execution_complete
        and control_execution_complete
        and len(treatment_folds) == plan.fold_count
        and len(control_folds) == plan.fold_count
    )
    if can_score:
        if any(value < 0 for value in incremental_folds):
            blockers.append(
                "T12_EVERY_TEMPORAL_FOLD_TREATMENT_NOT_BELOW_CONTROL"
            )
        if treatment_net < control_net:
            blockers.append(
                "T12_AGGREGATE_TREATMENT_DELTA_NOT_BELOW_CONTROL"
            )
        if treatment_dd > control_dd:
            blockers.append(
                "T12_TREATMENT_SETTLEMENT_CASH_DRAWDOWN_NOT_ABOVE_CONTROL"
            )
        if treatment_productivity <= control_productivity:
            blockers.append(
                "T12_TREATMENT_CAPITAL_PRODUCTIVITY_STRICTLY_ABOVE_CONTROL"
            )
    elif (
        readiness.ready_for_utility_analysis
        and (
            len(treatment_folds) != plan.fold_count
            or len(control_folds) != plan.fold_count
        )
    ):
        blockers.append("T12_TEMPORAL_FOLD_COUNT_INCOMPLETE")

    blockers = list(dict.fromkeys(blockers))
    return Phase20T12UtilityReport(
        contract_id=T12_UTILITY_CONTRACT_ID,
        qualification_plan_sha256=phase20d_qualification_plan_sha256(),
        t12_policy_id=T12_SHADOW_POLICY_ID,
        t12_policy_sha256=t12_shadow_policy_sha256(),
        population_ready=readiness.ready_for_utility_analysis,
        decision_epochs=readiness.post_freeze_decision_epochs,
        candidate_instances=len(scoped),
        treatment_selected_instances=len(treatment),
        control_selected_instances=len(control),
        candidate_outcome_coverage=candidate_coverage,
        treatment_selected_outcome_coverage=treatment_coverage,
        control_selected_outcome_coverage=control_coverage,
        treatment_net_delta_usd=treatment_net,
        control_net_delta_usd=control_net,
        treatment_settlement_cash_drawdown_usd=treatment_dd,
        control_settlement_cash_drawdown_usd=control_dd,
        treatment_capital_productivity=treatment_productivity,
        control_capital_productivity=control_productivity,
        fold_treatment_net_delta_usd=treatment_folds,
        fold_control_net_delta_usd=control_folds,
        fold_incremental_net_delta_usd=incremental_folds,
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
    treatment: tuple[Phase20QualificationRow, ...],
    control: tuple[Phase20QualificationRow, ...],
    shadows: dict[str, T12ShadowDecisionSeal],
    decision_sha256s: tuple[str, ...],
) -> tuple[tuple[Decimal, ...], tuple[Decimal, ...]]:
    if not decision_sha256s:
        return (), ()
    times: dict[str, datetime] = {}
    for sha in decision_sha256s:
        shadow = shadows.get(sha)
        if shadow is None:
            return (), ()
        times[sha] = shadow.decision_at
    ordered = tuple(
        sorted(
            decision_sha256s,
            key=lambda sha: (times[sha], sha),
        )
    )
    fold_count = FROZEN_PHASE20D_QUALIFICATION_PLAN.fold_count
    base, remainder = divmod(len(ordered), fold_count)
    treatment_result: list[Decimal] = []
    control_result: list[Decimal] = []
    start = 0
    for index in range(fold_count):
        count = base + (1 if index < remainder else 0)
        fold_ids = set(ordered[start : start + count])
        start += count
        treatment_result.append(
            _net(
                tuple(
                    row
                    for row in treatment
                    if row.decision_evidence_sha256 in fold_ids
                )
            )
        )
        control_result.append(
            _net(
                tuple(
                    row
                    for row in control
                    if row.decision_evidence_sha256 in fold_ids
                )
            )
        )
    return tuple(treatment_result), tuple(control_result)
