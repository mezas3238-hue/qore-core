from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.trader_lab import (
    capitalizer_scalper_certification_standard_v2 as standard,
)


def _passing_era(name: str) -> standard.OosEraEvidence:
    return standard.OosEraEvidence(
        era=name,
        profit_factor=Decimal("1.80"),
        expectancy_r_per_trade=Decimal("0.20"),
        sharpe_annualized=Decimal("1.75"),
        sortino_annualized=Decimal("2.40"),
        observed_max_drawdown_r=Decimal("7.5"),
        payoff_ratio=Decimal("1.35"),
    )


def _passing_evidence() -> standard.CertificationEvidence:
    return standard.CertificationEvidence(
        oos_eras=(
            _passing_era("OOS_A"),
            _passing_era("OOS_B"),
        ),
        combined_oos_profit_factor=Decimal("1.85"),
        monte_carlo_positive_probability=Decimal("0.96"),
        monte_carlo_p95_drawdown_r=Decimal("11"),
        post_cost_profit_factor=Decimal("1.55"),
        post_cost_expectancy_r_per_trade=Decimal("0.12"),
        temporal_stability_verified=True,
        anti_leakage_audit_passed=True,
        catastrophic_loss_clustering_absent=True,
        mae_mfe_audit_complete=True,
        loser_anatomy_audit_complete=True,
        density_sufficient_after_quality=True,
        fresh_holdout_integrity_verified=True,
        fresh_holdout_evaluated_once=True,
        fresh_holdout_passed=True,
        winner_preservation_required=True,
        winner_count_preservation=Decimal("0.92"),
        winner_r_preservation=Decimal("0.97"),
        risk_review_passed=True,
        cibo_review_passed=True,
        independent_validation_passed=True,
    )


def test_all_mandatory_gates_are_required_for_acceptance() -> None:
    decision = standard.evaluate_certification(_passing_evidence())

    assert decision.classification is standard.CertificationClassification.ACCEPTED
    assert decision.accepted is True
    assert decision.failed_gate_count == 0
    assert decision.missing_gate_count == 0


def test_missing_metrics_fail_closed_to_intervention() -> None:
    evidence = standard.CertificationEvidence(
        oos_eras=(
            standard.OosEraEvidence(
                era="CONSUMED_VALIDATION_2022_2024",
                profit_factor=Decimal("1.789"),
                observed_max_drawdown_r=Decimal("6.636"),
            ),
        ),
        combined_oos_profit_factor=None,
        fresh_holdout_integrity_verified=True,
        fresh_holdout_evaluated_once=False,
        fresh_holdout_passed=None,
    )

    decision = standard.evaluate_certification(evidence)

    assert decision.classification is (
        standard.CertificationClassification.INTERVENTION
    )
    assert decision.accepted is False
    assert decision.missing_gate_count > 0


def test_failed_nonfatal_gate_is_intervention_not_automatic_rejection() -> None:
    passing = _passing_evidence()
    weak_reserved = standard.OosEraEvidence(
        era="CONSUMED_RESERVED_2020_2022",
        profit_factor=Decimal("1.4267"),
        expectancy_r_per_trade=Decimal("0.052"),
        sharpe_annualized=Decimal("1.70"),
        sortino_annualized=Decimal("2.10"),
        observed_max_drawdown_r=Decimal("7.26"),
        payoff_ratio=Decimal("1.30"),
    )
    evidence = standard.CertificationEvidence(
        oos_eras=(
            passing.oos_eras[0],
            weak_reserved,
        ),
        combined_oos_profit_factor=passing.combined_oos_profit_factor,
        monte_carlo_positive_probability=passing.monte_carlo_positive_probability,
        monte_carlo_p95_drawdown_r=passing.monte_carlo_p95_drawdown_r,
        post_cost_profit_factor=passing.post_cost_profit_factor,
        post_cost_expectancy_r_per_trade=(
            passing.post_cost_expectancy_r_per_trade
        ),
        temporal_stability_verified=True,
        anti_leakage_audit_passed=True,
        catastrophic_loss_clustering_absent=True,
        mae_mfe_audit_complete=True,
        loser_anatomy_audit_complete=True,
        density_sufficient_after_quality=True,
        fresh_holdout_integrity_verified=True,
        fresh_holdout_evaluated_once=True,
        fresh_holdout_passed=True,
        winner_preservation_required=True,
        winner_count_preservation=Decimal("0.92"),
        winner_r_preservation=Decimal("0.97"),
        risk_review_passed=True,
        cibo_review_passed=True,
        independent_validation_passed=True,
    )

    decision = standard.evaluate_certification(evidence)

    assert decision.classification is (
        standard.CertificationClassification.INTERVENTION
    )
    failed = {gate.gate for gate in decision.gates if gate.status is standard.GateStatus.FAIL}
    assert "OOS[CONSUMED_RESERVED_2020_2022].profit_factor" in failed


def test_outcome_aware_runtime_logic_is_rejected() -> None:
    passing = _passing_evidence()
    evidence = standard.CertificationEvidence(
        oos_eras=passing.oos_eras,
        combined_oos_profit_factor=passing.combined_oos_profit_factor,
        monte_carlo_positive_probability=passing.monte_carlo_positive_probability,
        monte_carlo_p95_drawdown_r=passing.monte_carlo_p95_drawdown_r,
        post_cost_profit_factor=passing.post_cost_profit_factor,
        post_cost_expectancy_r_per_trade=(
            passing.post_cost_expectancy_r_per_trade
        ),
        temporal_stability_verified=True,
        anti_leakage_audit_passed=True,
        prohibited_outcome_aware_logic_detected=True,
        catastrophic_loss_clustering_absent=True,
        mae_mfe_audit_complete=True,
        loser_anatomy_audit_complete=True,
        density_sufficient_after_quality=True,
        fresh_holdout_integrity_verified=True,
        fresh_holdout_evaluated_once=True,
        fresh_holdout_passed=True,
        winner_preservation_required=True,
        winner_count_preservation=Decimal("0.92"),
        winner_r_preservation=Decimal("0.97"),
        risk_review_passed=True,
        cibo_review_passed=True,
        independent_validation_passed=True,
    )

    decision = standard.evaluate_certification(evidence)

    assert decision.classification is standard.CertificationClassification.REJECTED
    assert decision.accepted is False


def test_winner_preservation_is_conditional_but_fail_closed_when_required() -> None:
    passing = _passing_evidence()
    evidence = standard.CertificationEvidence(
        oos_eras=passing.oos_eras,
        combined_oos_profit_factor=passing.combined_oos_profit_factor,
        monte_carlo_positive_probability=passing.monte_carlo_positive_probability,
        monte_carlo_p95_drawdown_r=passing.monte_carlo_p95_drawdown_r,
        post_cost_profit_factor=passing.post_cost_profit_factor,
        post_cost_expectancy_r_per_trade=(
            passing.post_cost_expectancy_r_per_trade
        ),
        temporal_stability_verified=True,
        anti_leakage_audit_passed=True,
        catastrophic_loss_clustering_absent=True,
        mae_mfe_audit_complete=True,
        loser_anatomy_audit_complete=True,
        density_sufficient_after_quality=True,
        fresh_holdout_integrity_verified=True,
        fresh_holdout_evaluated_once=True,
        fresh_holdout_passed=True,
        winner_preservation_required=True,
        winner_count_preservation=Decimal("0.79"),
        winner_r_preservation=Decimal("0.89"),
        risk_review_passed=True,
        cibo_review_passed=True,
        independent_validation_passed=True,
    )

    decision = standard.evaluate_certification(evidence)

    assert decision.classification is (
        standard.CertificationClassification.INTERVENTION
    )
    failed = {gate.gate for gate in decision.gates if gate.status is standard.GateStatus.FAIL}
    assert "winner_count_preservation" in failed
    assert "winner_r_preservation" in failed


def test_fatal_fresh_holdout_falsification_can_be_rejected_explicitly() -> None:
    passing = _passing_evidence()
    evidence = standard.CertificationEvidence(
        oos_eras=passing.oos_eras,
        combined_oos_profit_factor=passing.combined_oos_profit_factor,
        monte_carlo_positive_probability=passing.monte_carlo_positive_probability,
        monte_carlo_p95_drawdown_r=passing.monte_carlo_p95_drawdown_r,
        post_cost_profit_factor=passing.post_cost_profit_factor,
        post_cost_expectancy_r_per_trade=(
            passing.post_cost_expectancy_r_per_trade
        ),
        temporal_stability_verified=True,
        anti_leakage_audit_passed=True,
        catastrophic_loss_clustering_absent=True,
        mae_mfe_audit_complete=True,
        loser_anatomy_audit_complete=True,
        density_sufficient_after_quality=True,
        fresh_holdout_integrity_verified=True,
        fresh_holdout_evaluated_once=True,
        fresh_holdout_passed=False,
        winner_preservation_required=False,
        risk_review_passed=True,
        cibo_review_passed=True,
        independent_validation_passed=True,
        fatal_falsification=True,
        fatal_falsification_reason="fresh holdout falsified frozen candidate",
    )

    decision = standard.evaluate_certification(evidence)

    assert decision.classification is standard.CertificationClassification.REJECTED


def test_winner_r_preservation_may_exceed_one() -> None:
    passing = _passing_evidence()
    evidence = standard.CertificationEvidence(
        oos_eras=passing.oos_eras,
        combined_oos_profit_factor=passing.combined_oos_profit_factor,
        monte_carlo_positive_probability=passing.monte_carlo_positive_probability,
        monte_carlo_p95_drawdown_r=passing.monte_carlo_p95_drawdown_r,
        post_cost_profit_factor=passing.post_cost_profit_factor,
        post_cost_expectancy_r_per_trade=(
            passing.post_cost_expectancy_r_per_trade
        ),
        temporal_stability_verified=True,
        anti_leakage_audit_passed=True,
        catastrophic_loss_clustering_absent=True,
        mae_mfe_audit_complete=True,
        loser_anatomy_audit_complete=True,
        density_sufficient_after_quality=True,
        fresh_holdout_integrity_verified=True,
        fresh_holdout_evaluated_once=True,
        fresh_holdout_passed=True,
        winner_preservation_required=True,
        winner_count_preservation=Decimal("0.95"),
        winner_r_preservation=Decimal("1.20"),
        risk_review_passed=True,
        cibo_review_passed=True,
        independent_validation_passed=True,
    )

    decision = standard.evaluate_certification(evidence)

    assert decision.classification is standard.CertificationClassification.ACCEPTED
    winner_r = next(
        gate for gate in decision.gates if gate.gate == "winner_r_preservation"
    )
    assert winner_r.status is standard.GateStatus.PASS
