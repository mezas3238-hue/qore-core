"""Fixed fresh-OOS scarcity utility analysis for CE2I T09 and T18.

Population membership comes only from the preregistered scarcity-readiness
audit. Economic scoring consumes Phase20QualificationRow objects emitted by the
frozen Phase20D qualification runner and reuses its hard-gate semantics against
the fixed minimal-seed baseline. No threshold is fitted from outcomes.

T18 applies the same test only to cross-Trader scarcity epochs. Passing this
analysis demonstrates utility only for the frozen fresh-OOS scarcity population
and grants no runtime allocation authority.
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
from qore.infrastructure.cibo_ce2i_phase20_t09_t18_scarcity_readiness import (
    Phase20T09T18ScarcityReadiness,
)

SCARCITY_UTILITY_CONTRACT_ID = "CIBO_T09_T18_SCARCITY_UTILITY_V1"


@dataclass(frozen=True, slots=True)
class Phase20ScarcityUtilityScope:
    tool_code: str
    population_ready: bool
    decision_epochs: int
    candidate_instances: int
    policy_selected_instances: int
    baseline_selected_instances: int
    candidate_outcome_coverage: Decimal
    policy_selected_outcome_coverage: Decimal
    baseline_selected_outcome_coverage: Decimal
    policy_net_delta_usd: Decimal
    baseline_net_delta_usd: Decimal
    policy_settlement_cash_drawdown_usd: Decimal
    baseline_settlement_cash_drawdown_usd: Decimal
    policy_capital_productivity: Decimal
    baseline_capital_productivity: Decimal
    fold_policy_net_delta_usd: tuple[Decimal, ...]
    fresh_oos_utility_demonstrated: bool
    runtime_authority: bool
    blockers: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.tool_code not in {"T09", "T18"}:
            raise CiboCapitalManagementError(
                "Phase20 scarcity utility tool code is invalid"
            )
        for name in (
            "decision_epochs",
            "candidate_instances",
            "policy_selected_instances",
            "baseline_selected_instances",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, int)
                or isinstance(value, bool)
                or value < 0
            ):
                raise CiboCapitalManagementError(
                    f"Phase20 scarcity utility {name} must be non-negative int"
                )
        for name in (
            "candidate_outcome_coverage",
            "policy_selected_outcome_coverage",
            "baseline_selected_outcome_coverage",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, Decimal)
                or not value.is_finite()
                or value < 0
                or value > 1
            ):
                raise CiboCapitalManagementError(
                    f"Phase20 scarcity utility {name} must be in [0,1]"
                )
        for name in (
            "policy_net_delta_usd",
            "baseline_net_delta_usd",
            "policy_settlement_cash_drawdown_usd",
            "baseline_settlement_cash_drawdown_usd",
            "policy_capital_productivity",
            "baseline_capital_productivity",
        ):
            value = getattr(self, name)
            if not isinstance(value, Decimal) or not value.is_finite():
                raise CiboCapitalManagementError(
                    f"Phase20 scarcity utility {name} must be finite Decimal"
                )
        if any(
            not isinstance(item, Decimal) or not item.is_finite()
            for item in self.fold_policy_net_delta_usd
        ):
            raise CiboCapitalManagementError(
                "Phase20 scarcity utility fold deltas must be finite Decimal"
            )
        fold_count = len(self.fold_policy_net_delta_usd)
        if fold_count not in {
            0,
            FROZEN_PHASE20D_QUALIFICATION_PLAN.fold_count,
        }:
            raise CiboCapitalManagementError(
                "Phase20 scarcity utility report requires frozen fold count"
            )
        if (
            self.population_ready
            and fold_count != FROZEN_PHASE20D_QUALIFICATION_PLAN.fold_count
        ):
            raise CiboCapitalManagementError(
                "Phase20 scarcity ready report requires frozen fold count"
            )
        for name in (
            "population_ready",
            "fresh_oos_utility_demonstrated",
            "runtime_authority",
        ):
            if type(getattr(self, name)) is not bool:
                raise CiboCapitalManagementError(
                    f"Phase20 scarcity utility {name} must be bool"
                )
        if self.runtime_authority:
            raise CiboCapitalManagementError(
                "Phase20 scarcity utility cannot grant runtime authority"
            )
        if self.fresh_oos_utility_demonstrated != (
            self.population_ready and not self.blockers
        ):
            raise CiboCapitalManagementError(
                "Phase20 scarcity utility result/blocker drift"
            )


@dataclass(frozen=True, slots=True)
class Phase20T09T18ScarcityUtilityReport:
    contract_id: str
    qualification_plan_sha256: str
    baseline_policy_id: str
    outcome_refit_performed: bool
    t09: Phase20ScarcityUtilityScope
    t18: Phase20ScarcityUtilityScope

    def __post_init__(self) -> None:
        if self.contract_id != SCARCITY_UTILITY_CONTRACT_ID:
            raise CiboCapitalManagementError(
                "Phase20 scarcity utility contract identity drift"
            )
        if self.qualification_plan_sha256 != phase20d_qualification_plan_sha256():
            raise CiboCapitalManagementError(
                "Phase20 scarcity utility qualification plan digest drift"
            )
        if (
            self.baseline_policy_id
            != FROZEN_PHASE20D_QUALIFICATION_PLAN.baseline_policy_id
        ):
            raise CiboCapitalManagementError(
                "Phase20 scarcity utility baseline identity drift"
            )
        if self.outcome_refit_performed:
            raise CiboCapitalManagementError(
                "Phase20 scarcity utility cannot refit from outcomes"
            )


def assess_phase20_t09_t18_scarcity_utility(
    *,
    qualification_rows: tuple[Phase20QualificationRow, ...],
    scarcity_readiness: Phase20T09T18ScarcityReadiness,
) -> Phase20T09T18ScarcityUtilityReport:
    """Apply frozen Phase20D hard-gate semantics to scarcity scopes."""

    if any(
        not isinstance(item, Phase20QualificationRow)
        for item in qualification_rows
    ):
        raise CiboCapitalManagementError(
            "Phase20 scarcity utility requires canonical qualification rows"
        )
    if not isinstance(scarcity_readiness, Phase20T09T18ScarcityReadiness):
        raise CiboCapitalManagementError(
            "Phase20 scarcity utility requires canonical readiness audit"
        )
    return Phase20T09T18ScarcityUtilityReport(
        contract_id=SCARCITY_UTILITY_CONTRACT_ID,
        qualification_plan_sha256=phase20d_qualification_plan_sha256(),
        baseline_policy_id=FROZEN_PHASE20D_QUALIFICATION_PLAN.baseline_policy_id,
        outcome_refit_performed=False,
        t09=_scope(
            tool_code="T09",
            rows=qualification_rows,
            decision_sha256s=scarcity_readiness.t09_scarce_decision_sha256s,
            population_ready=scarcity_readiness.t09_ready_for_utility_analysis,
            population_blockers=scarcity_readiness.t09_blockers,
        ),
        t18=_scope(
            tool_code="T18",
            rows=qualification_rows,
            decision_sha256s=(
                scarcity_readiness.t18_cross_trader_scarce_decision_sha256s
            ),
            population_ready=scarcity_readiness.t18_ready_for_utility_analysis,
            population_blockers=scarcity_readiness.t18_blockers,
        ),
    )


def _scope(
    *,
    tool_code: str,
    rows: tuple[Phase20QualificationRow, ...],
    decision_sha256s: tuple[str, ...],
    population_ready: bool,
    population_blockers: tuple[str, ...],
) -> Phase20ScarcityUtilityScope:
    decision_set = set(decision_sha256s)
    scoped = tuple(
        item for item in rows if item.decision_evidence_sha256 in decision_set
    )
    represented = {item.decision_evidence_sha256 for item in scoped}
    blockers = list(population_blockers)
    if population_ready and not decision_sha256s:
        blockers.append(f"{tool_code}_SCARCITY_DECISION_IDENTITY_SET_MISSING")
    if represented != decision_set:
        blockers.append(
            f"{tool_code}_SCARCITY_QUALIFICATION_ROW_COVERAGE_INCOMPLETE"
        )

    policy_rows = tuple(item for item in scoped if item.policy_selected)
    baseline_rows = tuple(item for item in scoped if item.baseline_selected)
    candidate_coverage = _coverage(scoped)
    policy_coverage = _coverage(policy_rows)
    baseline_coverage = _coverage(baseline_rows)
    plan = FROZEN_PHASE20D_QUALIFICATION_PLAN

    if scoped and candidate_coverage < plan.minimum_candidate_outcome_coverage:
        blockers.append(
            f"{tool_code}_CANDIDATE_OUTCOME_COVERAGE_AT_LEAST_95_PERCENT"
        )
    if not policy_rows:
        blockers.append(f"{tool_code}_NO_POLICY_SELECTED_SCARCITY_ROWS")
    elif policy_coverage < plan.required_selected_outcome_coverage:
        blockers.append(f"{tool_code}_SELECTED_OUTCOME_COVERAGE_COMPLETE")
    if not baseline_rows:
        blockers.append(f"{tool_code}_NO_BASELINE_SELECTED_SCARCITY_ROWS")
    elif baseline_coverage < plan.required_baseline_selected_outcome_coverage:
        blockers.append(
            f"{tool_code}_BASELINE_SELECTED_OUTCOME_COVERAGE_COMPLETE"
        )

    execution_complete = _execution_complete(policy_rows) and _execution_complete(
        baseline_rows
    )
    if scoped and not execution_complete:
        blockers.append(f"{tool_code}_REALIZED_EXECUTION_ECONOMICS_COMPLETE")

    policy_net = _net(policy_rows)
    baseline_net = _net(baseline_rows)
    policy_dd = _drawdown(policy_rows)
    baseline_dd = _drawdown(baseline_rows)
    policy_productivity = _productivity(policy_rows)
    baseline_productivity = _productivity(baseline_rows)
    fold_deltas = _fold_deltas(scoped, decision_sha256s)

    can_score = (
        population_ready
        and bool(scoped)
        and represented == decision_set
        and candidate_coverage >= plan.minimum_candidate_outcome_coverage
        and bool(policy_rows)
        and policy_coverage >= plan.required_selected_outcome_coverage
        and bool(baseline_rows)
        and baseline_coverage
        >= plan.required_baseline_selected_outcome_coverage
        and execution_complete
        and len(fold_deltas) == plan.fold_count
    )
    if can_score:
        if any(value <= 0 for value in fold_deltas):
            blockers.append(
                f"{tool_code}_ALL_TEMPORAL_FOLDS_POLICY_DELTA_POSITIVE"
            )
        if policy_net <= 0:
            blockers.append(f"{tool_code}_AGGREGATE_POLICY_DELTA_POSITIVE")
        if policy_net < baseline_net:
            blockers.append(
                f"{tool_code}_POLICY_DELTA_NOT_BELOW_FIXED_BASELINE"
            )
        if policy_dd > baseline_dd:
            blockers.append(
                f"{tool_code}_POLICY_SETTLEMENT_CASH_DRAWDOWN_"
                "NOT_ABOVE_FIXED_BASELINE"
            )
        if policy_productivity <= baseline_productivity:
            blockers.append(
                f"{tool_code}_POLICY_CAPITAL_PRODUCTIVITY_"
                "STRICTLY_ABOVE_FIXED_BASELINE"
            )
    elif population_ready and len(fold_deltas) != plan.fold_count:
        blockers.append(f"{tool_code}_TEMPORAL_FOLD_COUNT_INCOMPLETE")

    blockers = list(dict.fromkeys(blockers))
    return Phase20ScarcityUtilityScope(
        tool_code=tool_code,
        population_ready=population_ready,
        decision_epochs=len(decision_set),
        candidate_instances=len(scoped),
        policy_selected_instances=len(policy_rows),
        baseline_selected_instances=len(baseline_rows),
        candidate_outcome_coverage=candidate_coverage,
        policy_selected_outcome_coverage=policy_coverage,
        baseline_selected_outcome_coverage=baseline_coverage,
        policy_net_delta_usd=policy_net,
        baseline_net_delta_usd=baseline_net,
        policy_settlement_cash_drawdown_usd=policy_dd,
        baseline_settlement_cash_drawdown_usd=baseline_dd,
        policy_capital_productivity=policy_productivity,
        baseline_capital_productivity=baseline_productivity,
        fold_policy_net_delta_usd=fold_deltas,
        fresh_oos_utility_demonstrated=population_ready and not blockers,
        runtime_authority=False,
        blockers=tuple(blockers),
    )


def _coverage(rows: tuple[Phase20QualificationRow, ...]) -> Decimal:
    if not rows:
        return Decimal(0)
    observed = sum(1 for item in rows if item.realized_net_pnl_usd is not None)
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
    rows: tuple[Phase20QualificationRow, ...],
    decision_sha256s: tuple[str, ...],
) -> tuple[Decimal, ...]:
    if not decision_sha256s:
        return ()
    times: dict[str, datetime] = {}
    for item in rows:
        previous = times.get(item.decision_evidence_sha256)
        if previous is not None and previous != item.decision_at:
            raise CiboCapitalManagementError(
                "Phase20 scarcity utility decision time drift"
            )
        times[item.decision_evidence_sha256] = item.decision_at
    if set(times) != set(decision_sha256s):
        return ()
    ordered = tuple(
        sorted(
            decision_sha256s,
            key=lambda sha: (times[sha], sha),
        )
    )
    fold_count = FROZEN_PHASE20D_QUALIFICATION_PLAN.fold_count
    base, remainder = divmod(len(ordered), fold_count)
    result: list[Decimal] = []
    start = 0
    for index in range(fold_count):
        count = base + (1 if index < remainder else 0)
        fold_set = set(ordered[start : start + count])
        start += count
        if not fold_set:
            continue
        result.append(
            sum(
                (
                    item.realized_net_pnl_usd
                    for item in rows
                    if item.decision_evidence_sha256 in fold_set
                    and item.policy_selected
                    and item.realized_net_pnl_usd is not None
                ),
                Decimal(0),
            )
        )
    return tuple(result)
