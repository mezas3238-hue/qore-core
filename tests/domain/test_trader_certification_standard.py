from decimal import Decimal

from qore.domain.trader_certification_standard import (
    UniversalTraderCertificationEvidence,
    passes_universal_trader_certification,
    universal_acceptance_failures,
)


def _green() -> UniversalTraderCertificationEvidence:
    return UniversalTraderCertificationEvidence(
        oos_profit_factors=(Decimal("1.60"), Decimal("1.80")),
        combined_oos_profit_factor=Decimal("1.75"),
        oos_expectancies_r=(Decimal("0.10"), Decimal("0.12")),
        combined_oos_expectancy_r=Decimal("0.15"),
        oos_sharpes=(Decimal("1.60"), Decimal("1.70")),
        oos_sortinos=(Decimal("2.10"), Decimal("2.20")),
        observed_max_drawdown_r=Decimal("6.0"),
        monte_carlo_positive_probability=Decimal("0.91"),
        monte_carlo_p95_drawdown_r=Decimal("14.9"),
        payoff_ratio=Decimal("1.20"),
        post_cost_profit_factor=Decimal("1.10"),
        post_cost_expectancy_r=Decimal("0.01"),
        temporal_stability_passed=True,
        loss_cluster_gate_passed=True,
        fresh_holdout_integrity_passed=True,
        anti_leakage_audit_passed=True,
        density_sufficient_after_quality=True,
    )


def test_universal_standard_accepts_only_when_every_gate_passes() -> None:
    evidence = _green()

    assert passes_universal_trader_certification(evidence) is True
    assert universal_acceptance_failures(evidence) == ()


def test_density_cannot_rescue_weak_oos_profit_factor() -> None:
    green = _green()
    evidence = UniversalTraderCertificationEvidence(
        oos_profit_factors=(Decimal("2.20"), Decimal("1.49")),
        combined_oos_profit_factor=green.combined_oos_profit_factor,
        oos_expectancies_r=green.oos_expectancies_r,
        combined_oos_expectancy_r=green.combined_oos_expectancy_r,
        oos_sharpes=green.oos_sharpes,
        oos_sortinos=green.oos_sortinos,
        observed_max_drawdown_r=green.observed_max_drawdown_r,
        monte_carlo_positive_probability=green.monte_carlo_positive_probability,
        monte_carlo_p95_drawdown_r=green.monte_carlo_p95_drawdown_r,
        payoff_ratio=green.payoff_ratio,
        post_cost_profit_factor=green.post_cost_profit_factor,
        post_cost_expectancy_r=green.post_cost_expectancy_r,
        temporal_stability_passed=True,
        loss_cluster_gate_passed=True,
        fresh_holdout_integrity_passed=True,
        anti_leakage_audit_passed=True,
        density_sufficient_after_quality=True,
    )

    failures = universal_acceptance_failures(evidence)

    assert "OOS_PROFIT_FACTOR_BELOW_1_50" in failures
    assert passes_universal_trader_certification(evidence) is False


def test_global_average_cannot_hide_negative_oos_expectancy() -> None:
    green = _green()
    evidence = UniversalTraderCertificationEvidence(
        oos_profit_factors=green.oos_profit_factors,
        combined_oos_profit_factor=Decimal("2.20"),
        oos_expectancies_r=(Decimal("0.40"), Decimal("-0.01")),
        combined_oos_expectancy_r=Decimal("0.20"),
        oos_sharpes=green.oos_sharpes,
        oos_sortinos=green.oos_sortinos,
        observed_max_drawdown_r=green.observed_max_drawdown_r,
        monte_carlo_positive_probability=green.monte_carlo_positive_probability,
        monte_carlo_p95_drawdown_r=green.monte_carlo_p95_drawdown_r,
        payoff_ratio=green.payoff_ratio,
        post_cost_profit_factor=green.post_cost_profit_factor,
        post_cost_expectancy_r=green.post_cost_expectancy_r,
        temporal_stability_passed=True,
        loss_cluster_gate_passed=True,
        fresh_holdout_integrity_passed=True,
        anti_leakage_audit_passed=True,
        density_sufficient_after_quality=True,
    )

    assert "OOS_EXPECTANCY_NOT_POSITIVE" in universal_acceptance_failures(evidence)


def test_burned_holdout_or_leakage_blocks_acceptance() -> None:
    green = _green()
    evidence = UniversalTraderCertificationEvidence(
        oos_profit_factors=green.oos_profit_factors,
        combined_oos_profit_factor=green.combined_oos_profit_factor,
        oos_expectancies_r=green.oos_expectancies_r,
        combined_oos_expectancy_r=green.combined_oos_expectancy_r,
        oos_sharpes=green.oos_sharpes,
        oos_sortinos=green.oos_sortinos,
        observed_max_drawdown_r=green.observed_max_drawdown_r,
        monte_carlo_positive_probability=green.monte_carlo_positive_probability,
        monte_carlo_p95_drawdown_r=green.monte_carlo_p95_drawdown_r,
        payoff_ratio=green.payoff_ratio,
        post_cost_profit_factor=green.post_cost_profit_factor,
        post_cost_expectancy_r=green.post_cost_expectancy_r,
        temporal_stability_passed=True,
        loss_cluster_gate_passed=True,
        fresh_holdout_integrity_passed=False,
        anti_leakage_audit_passed=False,
        density_sufficient_after_quality=True,
    )

    failures = universal_acceptance_failures(evidence)

    assert "FRESH_HOLDOUT_INTEGRITY_NOT_PASSED" in failures
    assert "ANTI_LEAKAGE_AUDIT_NOT_PASSED" in failures
    assert passes_universal_trader_certification(evidence) is False


def test_costs_and_tail_survival_are_hard_gates() -> None:
    green = _green()
    evidence = UniversalTraderCertificationEvidence(
        oos_profit_factors=green.oos_profit_factors,
        combined_oos_profit_factor=green.combined_oos_profit_factor,
        oos_expectancies_r=green.oos_expectancies_r,
        combined_oos_expectancy_r=green.combined_oos_expectancy_r,
        oos_sharpes=green.oos_sharpes,
        oos_sortinos=green.oos_sortinos,
        observed_max_drawdown_r=Decimal("6.01"),
        monte_carlo_positive_probability=Decimal("0.899"),
        monte_carlo_p95_drawdown_r=Decimal("15.01"),
        payoff_ratio=green.payoff_ratio,
        post_cost_profit_factor=Decimal("1.00"),
        post_cost_expectancy_r=Decimal("0"),
        temporal_stability_passed=True,
        loss_cluster_gate_passed=True,
        fresh_holdout_integrity_passed=True,
        anti_leakage_audit_passed=True,
        density_sufficient_after_quality=True,
    )

    failures = universal_acceptance_failures(evidence)

    assert "OBSERVED_MAX_DRAWDOWN_ABOVE_6R" in failures
    assert "MONTE_CARLO_POSITIVE_PROBABILITY_BELOW_90_PERCENT" in failures
    assert "MONTE_CARLO_P95_DRAWDOWN_ABOVE_15R" in failures
    assert "POST_COST_PROFIT_FACTOR_NOT_ABOVE_1" in failures
    assert "POST_COST_EXPECTANCY_NOT_POSITIVE" in failures
