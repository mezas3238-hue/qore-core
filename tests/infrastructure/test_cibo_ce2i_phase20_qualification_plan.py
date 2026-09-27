from qore.infrastructure.cibo_ce2i_phase20_policy_candidate import (
    FROZEN_PHASE20_POLICY_CANDIDATE,
)
from qore.infrastructure.cibo_ce2i_phase20_qualification_plan import (
    FROZEN_PHASE20D_QUALIFICATION_PLAN,
    phase20d_qualification_plan_sha256,
)


def test_phase20d_qualification_plan_is_bound_to_frozen_v2() -> None:
    plan = FROZEN_PHASE20D_QUALIFICATION_PLAN

    assert plan.candidate_id == FROZEN_PHASE20_POLICY_CANDIDATE.candidate_id
    assert plan.candidate_parameter_sha256 == (
        FROZEN_PHASE20_POLICY_CANDIDATE.parameter_sha256()
    )
    assert plan.no_refit_between_folds is True
    assert plan.burned_phase19j_reuse_allowed is False
    assert plan.synthetic_evidence_allowed is False
    assert plan.decision_time_provider_cost_proxy_only is True
    assert plan.realized_execution_economics_required is True
    assert plan.plan_id == "CIBO_PHASE20D_V2_FORWARD_QUALIFICATION_PLAN_V3"


def test_phase20d_qualification_plan_prevents_tiny_or_narrow_population() -> None:
    plan = FROZEN_PHASE20D_QUALIFICATION_PLAN

    assert plan.fold_count == 4
    assert plan.minimum_decision_epochs == 80
    assert plan.minimum_candidate_outcomes == 200
    assert plan.minimum_selected_outcomes == 60
    assert plan.minimum_calendar_span_days == 28
    assert plan.minimum_distinct_trading_days == 20
    assert plan.minimum_fold_candidate_outcomes == 40
    assert plan.minimum_global_lineages == 7
    assert plan.minimum_outcomes_per_lineage == 8
    assert plan.minimum_fold_lineages == 4
    assert str(plan.minimum_candidate_outcome_coverage) == "0.95"
    assert str(plan.required_selected_outcome_coverage) == "1.00"
    assert str(plan.required_baseline_selected_outcome_coverage) == "1.00"


def test_phase20d_qualification_plan_has_economic_and_safety_gates() -> None:
    plan = FROZEN_PHASE20D_QUALIFICATION_PLAN

    assert "ALL_TEMPORAL_FOLDS_POLICY_DELTA_POSITIVE" in plan.hard_gates
    assert "POLICY_DELTA_NOT_BELOW_FIXED_BASELINE" in plan.hard_gates
    assert "POLICY_SETTLEMENT_CASH_DRAWDOWN_NOT_ABOVE_FIXED_BASELINE" in plan.hard_gates
    assert (
        "POLICY_CAPITAL_PRODUCTIVITY_STRICTLY_ABOVE_FIXED_BASELINE"
        in plan.hard_gates
    )
    assert "ZERO_CAUSAL_CONTAMINATION" in plan.hard_gates
    assert "ZERO_CAPITAL_CONSERVATION_BREACHES" in plan.hard_gates
    assert "REALIZED_EXECUTION_ECONOMICS_COMPLETE" in plan.hard_gates
    assert "BASELINE_SELECTED_OUTCOME_COVERAGE_COMPLETE" in plan.hard_gates
    assert "REALIZED_NET_DELTA_USD" in plan.metrics
    assert "EXECUTED_INITIAL_STOP_RISK_USD" in plan.metrics
    assert "DECISION_TIME_PROVIDER_COST_PROXY_USD" in plan.metrics
    assert "TERMINAL_SETTLEMENT_CASH_PATH_DRAWDOWN_USD" in plan.metrics
    assert "EVIDENCE_MISSINGNESS" in plan.metrics
    assert "MPC_RESERVE_EFFICIENCY" in plan.metrics


def test_phase20d_qualification_plan_digest_is_deterministic() -> None:
    left = phase20d_qualification_plan_sha256()
    right = phase20d_qualification_plan_sha256()

    assert left == right
    assert left.startswith("sha256:")
    assert len(left) == 71
