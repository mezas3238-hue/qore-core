from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.trader_lab import (
    universal_trader_certification_standard_001 as utc,
)


def _passing_period(
    period_id: str,
    *,
    kind: utc.PeriodKind = utc.PeriodKind.YEAR,
) -> utc.TemporalPeriodEvidence:
    return utc.TemporalPeriodEvidence(
        period_id=period_id,
        kind=kind,
        window_start="2024-09-17",
        window_end_exclusive="2025-09-17",
        certification_required=True,
        trades=250,
        wins=130,
        losses=115,
        breakeven=5,
        win_rate=Decimal("0.52"),
        profit_factor=Decimal("1.80"),
        expectancy_r_per_trade=Decimal("0.20"),
        sharpe_annualized=Decimal("1.75"),
        sortino_annualized=Decimal("2.40"),
        observed_max_drawdown_r=Decimal("6.00"),
        average_winner_r=Decimal("0.90"),
        average_loser_r_abs=Decimal("0.55"),
        payoff_ratio=Decimal("1.636"),
        longest_losing_streak=5,
        monte_carlo_positive_probability=Decimal("0.94"),
        monte_carlo_p95_drawdown_r=Decimal("12"),
        post_cost_profit_factor=Decimal("1.35"),
        post_cost_expectancy_r_per_trade=Decimal("0.11"),
        loss_cluster_gate_passed=True,
        sample_sufficiency_passed=True,
        cost_evidence_bound=True,
    )


def _passing_evidence(
    periods: tuple[utc.TemporalPeriodEvidence, ...] | None = None,
) -> utc.CandidateEvidence:
    return utc.CandidateEvidence(
        periods=periods or (
            _passing_period("YEAR_1"),
            _passing_period("YEAR_2"),
            _passing_period("FOLD_1", kind=utc.PeriodKind.OOS_FOLD),
        ),
        fresh_holdout_integrity_passed=True,
        fresh_holdout_opened_once=True,
        fresh_holdout_passed=True,
        anti_leakage_audit_passed=True,
        winner_preservation_required=True,
        winner_count_preservation=Decimal("0.91"),
        winner_r_preservation=Decimal("0.96"),
        temporal_stability_review_passed=True,
        mae_mfe_audit_complete=True,
        loser_anatomy_audit_complete=True,
        density_sufficient_after_quality=True,
        risk_review_passed=True,
        cibo_review_passed=True,
        independent_validation_passed=True,
    )


def _replace_period(
    row: utc.TemporalPeriodEvidence,
    **changes: object,
) -> utc.TemporalPeriodEvidence:
    values = {
        field: getattr(row, field)
        for field in row.__dataclass_fields__
    }
    values.update(changes)
    return utc.TemporalPeriodEvidence(**values)


def test_all_required_periods_and_candidate_gates_are_conjunctive() -> None:
    decision = utc.evaluate_certification(_passing_evidence())

    assert decision.classification is utc.CertificationClassification.ACCEPTED
    assert decision.accepted is True
    assert decision.failed_gate_count == 0
    assert decision.missing_gate_count == 0
    assert decision.required_period_count == 3
    assert decision.passed_period_count == 3
    assert decision.global_compensation_allowed is False
    assert decision.temporal_compensation_allowed is False
    assert decision.gate_compensation_allowed is False


def test_one_failed_year_prevents_acceptance_without_global_rescue() -> None:
    good = _passing_period("YEAR_1")
    bad = _replace_period(
        _passing_period("YEAR_2"),
        profit_factor=Decimal("1.49"),
    )
    evidence = _passing_evidence((good, bad))
    evidence = utc.CandidateEvidence(
        **{
            field: getattr(evidence, field)
            for field in evidence.__dataclass_fields__
            if field != "descriptive_global_profit_factor"
        },
        descriptive_global_profit_factor=Decimal("3.50"),
    )

    decision = utc.evaluate_certification(evidence)

    assert decision.accepted is False
    assert decision.classification is (
        utc.CertificationClassification.INTERVENTION
    )
    assert decision.failed_period_count == 1
    failed = {
        (gate.period_id, gate.gate)
        for gate in decision.gates
        if gate.status is utc.GateStatus.FAIL
    }
    assert ("YEAR_2", "profit_factor") in failed


def test_utc001_exact_hard_edges() -> None:
    edge = _replace_period(
        _passing_period("YEAR_EDGE"),
        profit_factor=Decimal("1.50"),
        expectancy_r_per_trade=Decimal("0.15"),
        sharpe_annualized=Decimal("1.50"),
        sortino_annualized=Decimal("2.00"),
        payoff_ratio=Decimal("1.50"),
        observed_max_drawdown_r=Decimal("6.00"),
        monte_carlo_positive_probability=Decimal("0.90"),
        monte_carlo_p95_drawdown_r=Decimal("15"),
        post_cost_profit_factor=Decimal("1.0000001"),
        post_cost_expectancy_r_per_trade=Decimal("0.0000001"),
    )

    decision = utc.evaluate_certification(_passing_evidence((edge,)))

    assert decision.accepted is True


def test_expectancy_below_point_15_fails_even_if_positive() -> None:
    weak = _replace_period(
        _passing_period("YEAR_WEAK"),
        expectancy_r_per_trade=Decimal("0.149999"),
    )

    decision = utc.evaluate_certification(_passing_evidence((weak,)))

    assert decision.accepted is False
    failed = {
        gate.gate
        for gate in decision.gates
        if gate.status is utc.GateStatus.FAIL
    }
    assert "expectancy_r_per_trade" in failed


def test_drawdown_above_6r_fails() -> None:
    weak = _replace_period(
        _passing_period("YEAR_WEAK"),
        observed_max_drawdown_r=Decimal("6.000001"),
    )

    decision = utc.evaluate_certification(_passing_evidence((weak,)))

    assert decision.accepted is False
    assert decision.failed_period_count == 1


def test_payoff_below_1_5_has_no_compensation() -> None:
    weak = _replace_period(
        _passing_period("YEAR_WEAK"),
        payoff_ratio=Decimal("1.4999"),
        profit_factor=Decimal("4.00"),
        win_rate=Decimal("0.80"),
    )

    decision = utc.evaluate_certification(_passing_evidence((weak,)))

    assert decision.accepted is False
    failed = {
        gate.gate
        for gate in decision.gates
        if gate.status is utc.GateStatus.FAIL
    }
    assert "payoff_ratio" in failed


def test_missing_bound_cost_evidence_blocks_certification() -> None:
    blocked = _replace_period(
        _passing_period("YEAR_COST_BLOCKED"),
        cost_evidence_bound=False,
        cost_certification_blocked=True,
        post_cost_profit_factor=None,
        post_cost_expectancy_r_per_trade=None,
    )

    decision = utc.evaluate_certification(
        _passing_evidence((blocked,))
    )

    assert decision.accepted is False
    missing = {
        gate.gate
        for gate in decision.gates
        if gate.status is utc.GateStatus.MISSING
    }
    assert "post_cost_profit_factor" in missing
    assert "post_cost_expectancy_r_per_trade" in missing


def test_development_has_zero_certification_authority() -> None:
    development = utc.TemporalPeriodEvidence(
        period_id="DEVELOPMENT",
        kind=utc.PeriodKind.YEAR,
        window_start="2024-09-17",
        window_end_exclusive="2025-09-17",
        certification_required=False,
        development_only=True,
        profit_factor=Decimal("99"),
    )
    evidence = _passing_evidence((_passing_period("YEAR_1"),))
    evidence = utc.CandidateEvidence(
        **{
            field: getattr(evidence, field)
            for field in evidence.__dataclass_fields__
            if field != "periods"
        },
        periods=(development, _passing_period("YEAR_1")),
    )

    decision = utc.evaluate_certification(evidence)

    assert decision.accepted is True
    development_gate = next(
        gate
        for gate in decision.gates
        if gate.period_id == "DEVELOPMENT"
    )
    assert development_gate.status is utc.GateStatus.NOT_APPLICABLE


def test_missing_fresh_holdout_gate_keeps_intervention() -> None:
    evidence = _passing_evidence()
    evidence = utc.CandidateEvidence(
        **{
            field: getattr(evidence, field)
            for field in evidence.__dataclass_fields__
            if field != "fresh_holdout_passed"
        },
        fresh_holdout_passed=None,
    )

    decision = utc.evaluate_certification(evidence)

    assert decision.accepted is False
    assert decision.classification is (
        utc.CertificationClassification.INTERVENTION
    )


def test_outcome_aware_runtime_logic_is_rejected() -> None:
    evidence = _passing_evidence()
    evidence = utc.CandidateEvidence(
        **{
            field: getattr(evidence, field)
            for field in evidence.__dataclass_fields__
            if field != "prohibited_outcome_aware_logic_detected"
        },
        prohibited_outcome_aware_logic_detected=True,
    )

    decision = utc.evaluate_certification(evidence)

    assert decision.classification is utc.CertificationClassification.REJECTED
    assert decision.accepted is False


def test_holdout_mining_is_rejected() -> None:
    evidence = _passing_evidence()
    evidence = utc.CandidateEvidence(
        **{
            field: getattr(evidence, field)
            for field in evidence.__dataclass_fields__
            if field != "holdout_mining_detected"
        },
        holdout_mining_detected=True,
    )

    decision = utc.evaluate_certification(evidence)

    assert decision.classification is utc.CertificationClassification.REJECTED
    assert decision.accepted is False
