"""Synthetic-only constitutional gate tests: NOT a certification claim."""
from dataclasses import replace

from qore.research.alpha2_utc001_gates import PeriodEvidence, certify


def passing_fixture() -> PeriodEvidence:
    return PeriodEvidence(
        trades=120, pf=1.75, expectancy_r=0.20, sharpe=1.75, sortino=2.20,
        payoff=1.60, observed_dd_r=5.50, mc_positive_probability=0.95,
        mc_p95_dd_r=11.5, net_pf=1.60, net_expectancy_r=0.17,
        sample_sufficient=True, loss_cluster_survived=True,
        returns_frequency_verified=True, monte_carlo_provenance_verified=True,
        transaction_costs_verified=True, anti_lookahead_verified=True,
        source_provenance_verified=True,
    )


def run_gate(periods=None, **overrides):
    kwargs = dict(
        required_period_ids=("YEAR_1", "YEAR_2", "FOLD_1"),
        period_evidence=periods or {key: passing_fixture() for key in
                                    ("YEAR_1", "YEAR_2", "FOLD_1")},
        fresh_holdout_passed=True, fresh_holdout_is_independent=True,
        news_asof_verified=True, risk_review_approved=True,
        cibo_review_approved=True, independent_validation_approved=True,
        winner_preservation_required=True, winner_count_preservation=0.90,
        winner_r_preservation=0.95, mae_mfe_complete=True,
        loser_anatomy_complete=True,
    )
    kwargs.update(overrides)
    return certify(**kwargs)


def test_only_fully_documented_synthetic_fixture_passes() -> None:
    assert run_gate().status == "ACCEPTED"


def test_one_failing_year_cannot_be_compensated_by_others() -> None:
    periods = {key: passing_fixture() for key in ("YEAR_1", "YEAR_2", "FOLD_1")}
    periods["YEAR_2"] = replace(passing_fixture(), pf=1.49)
    r = run_gate(periods)
    assert r.status != "ACCEPTED"
    assert "YEAR_2:PF_FAIL" in r.failed_gates


def test_exact_observed_dd_boundary_and_failing_above_six() -> None:
    periods = {key: passing_fixture() for key in ("YEAR_1", "YEAR_2", "FOLD_1")}
    periods["FOLD_1"] = replace(passing_fixture(), observed_dd_r=6.00)
    assert run_gate(periods).status == "ACCEPTED"
    periods["FOLD_1"] = replace(passing_fixture(), observed_dd_r=6.01)
    assert "FOLD_1:OBSERVED_DD_R_FAIL" in run_gate(periods).failed_gates


def test_missing_costs_and_fresh_holdout_fail_closed() -> None:
    periods = {key: passing_fixture() for key in ("YEAR_1", "YEAR_2", "FOLD_1")}
    periods["FOLD_1"] = replace(passing_fixture(), net_pf=None,
                                transaction_costs_verified=False)
    r = run_gate(periods, fresh_holdout_is_independent=False)
    assert "FOLD_1:POST_COST_PF_MISSING_OR_NONFINITE" in r.failed_gates
    assert "FOLD_1:TRANSACTION_COSTS_VERIFIED_FAIL" in r.failed_gates
    assert "FRESH_HOLDOUT_INDEPENDENT_FAIL" in r.failed_gates


def test_missing_required_fold_and_winner_preservation_are_blocking() -> None:
    r = run_gate(
        {"YEAR_1": passing_fixture(), "YEAR_2": passing_fixture()},
        winner_count_preservation=0.79,
    )
    assert "FOLD_1:MISSING_REQUIRED_PERIOD" in r.failed_gates
    assert "WINNER_COUNT_PRESERVATION_FAIL" in r.failed_gates


def test_zero_years_never_auto_certify() -> None:
    r = run_gate(required_period_ids=(), period_evidence={})
    assert "PERIOD_MANIFEST_INVALID" in r.failed_gates
