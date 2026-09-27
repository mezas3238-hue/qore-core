"""Pre-registered Phase20D economic qualification protocol for frozen CIBO V2.

The thresholds and pass/fail rules in this module are frozen before any fresh
forward outcome is consumed. They may not be tuned against the qualification
population. A failed candidate is falsified; a successor requires a new
candidate and a new legal research cycle.

This protocol evaluates observational/shadow economics only. Decision-time
provider costs are explicit proxies from contemporaneous provider observations;
they are not relabeled as realized execution costs.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from hashlib import sha256

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_phase20_policy_candidate import (
    FROZEN_PHASE20_POLICY_CANDIDATE,
)

_QUALIFICATION_ID = "CIBO_PHASE20D_V2_FORWARD_QUALIFICATION_PLAN_V1"


@dataclass(frozen=True, slots=True)
class Phase20ForwardQualificationPlan:
    plan_id: str
    candidate_id: str
    candidate_parameter_sha256: str
    frozen_at: datetime
    baseline_policy_id: str
    fold_count: int
    minimum_decision_epochs: int
    minimum_candidate_outcomes: int
    minimum_selected_outcomes: int
    minimum_calendar_span_days: int
    minimum_distinct_trading_days: int
    minimum_fold_candidate_outcomes: int
    minimum_global_lineages: int
    minimum_outcomes_per_lineage: int
    minimum_fold_lineages: int
    minimum_candidate_outcome_coverage: Decimal
    required_selected_outcome_coverage: Decimal
    required_baseline_selected_outcome_coverage: Decimal
    no_refit_between_folds: bool
    burned_phase19j_reuse_allowed: bool
    synthetic_evidence_allowed: bool
    decision_time_provider_cost_proxy_only: bool
    metrics: tuple[str, ...]
    hard_gates: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.plan_id or not self.candidate_id or not self.baseline_policy_id:
            raise CiboCapitalManagementError(
                "Phase20D qualification identity is required"
            )
        if self.candidate_id != FROZEN_PHASE20_POLICY_CANDIDATE.candidate_id:
            raise CiboCapitalManagementError(
                "Phase20D qualification candidate drift"
            )
        if (
            self.candidate_parameter_sha256
            != FROZEN_PHASE20_POLICY_CANDIDATE.parameter_sha256()
        ):
            raise CiboCapitalManagementError(
                "Phase20D qualification parameter digest drift"
            )
        if self.frozen_at.tzinfo is None or self.frozen_at.utcoffset() is None:
            raise CiboCapitalManagementError(
                "Phase20D qualification frozen_at must be timezone-aware"
            )
        for name in (
            "fold_count",
            "minimum_decision_epochs",
            "minimum_candidate_outcomes",
            "minimum_selected_outcomes",
            "minimum_calendar_span_days",
            "minimum_distinct_trading_days",
            "minimum_fold_candidate_outcomes",
            "minimum_global_lineages",
            "minimum_outcomes_per_lineage",
            "minimum_fold_lineages",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, int)
                or isinstance(value, bool)
                or value <= 0
            ):
                raise CiboCapitalManagementError(
                    f"Phase20D qualification {name} must be positive int"
                )
        for name in (
            "minimum_candidate_outcome_coverage",
            "required_selected_outcome_coverage",
            "required_baseline_selected_outcome_coverage",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, Decimal)
                or not value.is_finite()
                or value <= 0
                or value > 1
            ):
                raise CiboCapitalManagementError(
                    f"Phase20D qualification {name} must be Decimal in (0,1]"
                )
        for name in (
            "no_refit_between_folds",
            "burned_phase19j_reuse_allowed",
            "synthetic_evidence_allowed",
            "decision_time_provider_cost_proxy_only",
        ):
            if type(getattr(self, name)) is not bool:
                raise CiboCapitalManagementError(
                    f"Phase20D qualification {name} must be bool"
                )
        if not self.no_refit_between_folds:
            raise CiboCapitalManagementError(
                "Phase20D qualification requires no-refit WFO"
            )
        if self.burned_phase19j_reuse_allowed or self.synthetic_evidence_allowed:
            raise CiboCapitalManagementError(
                "Phase20D qualification cannot reuse burned/synthetic evidence"
            )
        if not self.decision_time_provider_cost_proxy_only:
            raise CiboCapitalManagementError(
                "Phase20D cannot relabel provider cost proxy as realized cost"
            )
        if not self.metrics or not self.hard_gates:
            raise CiboCapitalManagementError(
                "Phase20D qualification metrics/gates are required"
            )


FROZEN_PHASE20D_QUALIFICATION_PLAN = Phase20ForwardQualificationPlan(
    plan_id=_QUALIFICATION_ID,
    candidate_id=FROZEN_PHASE20_POLICY_CANDIDATE.candidate_id,
    candidate_parameter_sha256=(
        FROZEN_PHASE20_POLICY_CANDIDATE.parameter_sha256()
    ),
    frozen_at=datetime(2026, 9, 27, 16, 33, tzinfo=UTC),
    baseline_policy_id=(
        "CMA_MINIMAL_SEED_HARD_CONSTRAINTS_CANONICAL_ORDER_V1"
    ),
    fold_count=4,
    minimum_decision_epochs=80,
    minimum_candidate_outcomes=200,
    minimum_selected_outcomes=60,
    minimum_calendar_span_days=28,
    minimum_distinct_trading_days=20,
    minimum_fold_candidate_outcomes=40,
    minimum_global_lineages=7,
    minimum_outcomes_per_lineage=8,
    minimum_fold_lineages=4,
    minimum_candidate_outcome_coverage=Decimal("0.95"),
    required_selected_outcome_coverage=Decimal("1.00"),
    required_baseline_selected_outcome_coverage=Decimal("1.00"),
    no_refit_between_folds=True,
    burned_phase19j_reuse_allowed=False,
    synthetic_evidence_allowed=False,
    decision_time_provider_cost_proxy_only=True,
    metrics=(
        "STRUCTURAL_GROSS_DELTA_USD",
        "DECISION_TIME_PROVIDER_COST_ADJUSTED_DELTA_USD",
        "TEMPORAL_FOLD_DELTA_USD",
        "CAPITAL_MAX_DRAWDOWN_USD",
        "CAPITAL_PRODUCTIVITY_USD_PER_RISK_MINUTE",
        "OPPORTUNITY_ACCEPTANCE_RATE",
        "CAPITAL_UTILIZATION",
        "CAPITAL_STARVATION_RATE",
        "MPC_RESERVE_EFFICIENCY",
        "OPTIONALITY_PRESERVED_RATE",
        "CONCENTRATION_UTILIZATION",
        "PROVIDER_FAILURE_INCIDENCE",
        "EVIDENCE_MISSINGNESS",
    ),
    hard_gates=(
        "ZERO_CAUSAL_CONTAMINATION",
        "ZERO_DECISION_REWRITES",
        "ZERO_CAPITAL_CONSERVATION_BREACHES",
        "ZERO_CONCENTRATION_BREACHES",
        "ZERO_PROVIDER_CONSTRAINT_BYPASSES",
        "ALL_TEMPORAL_FOLDS_POLICY_DELTA_POSITIVE",
        "AGGREGATE_POLICY_DELTA_POSITIVE",
        "POLICY_DELTA_NOT_BELOW_FIXED_BASELINE",
        "POLICY_MAX_DRAWDOWN_NOT_ABOVE_FIXED_BASELINE",
        "POLICY_CAPITAL_PRODUCTIVITY_STRICTLY_ABOVE_FIXED_BASELINE",
        "MINIMUM_POPULATION_AND_TEMPORAL_COVERAGE_MET",
        "SELECTED_OUTCOME_COVERAGE_COMPLETE",
        "BASELINE_SELECTED_OUTCOME_COVERAGE_COMPLETE",
        "CANDIDATE_OUTCOME_COVERAGE_AT_LEAST_95_PERCENT",
    ),
)


def phase20d_qualification_plan_sha256() -> str:
    plan = FROZEN_PHASE20D_QUALIFICATION_PLAN
    payload = {
        "plan_id": plan.plan_id,
        "candidate_id": plan.candidate_id,
        "candidate_parameter_sha256": plan.candidate_parameter_sha256,
        "frozen_at": plan.frozen_at.isoformat(),
        "baseline_policy_id": plan.baseline_policy_id,
        "fold_count": plan.fold_count,
        "minimum_decision_epochs": plan.minimum_decision_epochs,
        "minimum_candidate_outcomes": plan.minimum_candidate_outcomes,
        "minimum_selected_outcomes": plan.minimum_selected_outcomes,
        "minimum_calendar_span_days": plan.minimum_calendar_span_days,
        "minimum_distinct_trading_days": plan.minimum_distinct_trading_days,
        "minimum_fold_candidate_outcomes": (
            plan.minimum_fold_candidate_outcomes
        ),
        "minimum_global_lineages": plan.minimum_global_lineages,
        "minimum_outcomes_per_lineage": plan.minimum_outcomes_per_lineage,
        "minimum_fold_lineages": plan.minimum_fold_lineages,
        "minimum_candidate_outcome_coverage": format(
            plan.minimum_candidate_outcome_coverage,
            "f",
        ),
        "required_selected_outcome_coverage": format(
            plan.required_selected_outcome_coverage,
            "f",
        ),
        "required_baseline_selected_outcome_coverage": format(
            plan.required_baseline_selected_outcome_coverage,
            "f",
        ),
        "no_refit_between_folds": plan.no_refit_between_folds,
        "burned_phase19j_reuse_allowed": (
            plan.burned_phase19j_reuse_allowed
        ),
        "synthetic_evidence_allowed": plan.synthetic_evidence_allowed,
        "decision_time_provider_cost_proxy_only": (
            plan.decision_time_provider_cost_proxy_only
        ),
        "metrics": list(plan.metrics),
        "hard_gates": list(plan.hard_gates),
    }
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return f"sha256:{sha256(raw).hexdigest()}"
