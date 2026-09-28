from dataclasses import fields
from decimal import Decimal

import pytest

from qore.domain.trader_certification_standard import (
    CertificationPeriodEvidence,
    CertificationPeriodKind,
    UniversalTraderCertificationEvidence,
    passes_universal_trader_certification,
    universal_acceptance_failures,
)


def _period(
    period_id: str,
    kind: CertificationPeriodKind,
    **overrides: object,
) -> CertificationPeriodEvidence:
    values: dict[str, object] = {
        "period_id": period_id,
        "kind": kind,
        "profit_factor": Decimal("1.80"),
        "expectancy_r": Decimal("0.20"),
        "sharpe": Decimal("1.70"),
        "sortino": Decimal("2.20"),
        "observed_max_drawdown_r": Decimal("6.0"),
        "monte_carlo_positive_probability": Decimal("0.91"),
        "monte_carlo_p95_drawdown_r": Decimal("14.9"),
        "payoff_ratio": Decimal("1.25"),
        "post_cost_profit_factor": Decimal("1.10"),
        "post_cost_expectancy_r": Decimal("0.01"),
        "loss_cluster_gate_passed": True,
        "density_sufficient_after_quality": True,
    }
    values.update(overrides)
    return CertificationPeriodEvidence(**values)  # type: ignore[arg-type]


def _green() -> UniversalTraderCertificationEvidence:
    return UniversalTraderCertificationEvidence(
        required_annual_period_ids=("2022", "2023"),
        required_oos_fold_ids=("WF1", "WF2"),
        periods=(
            _period("2022", CertificationPeriodKind.ANNUAL),
            _period("2023", CertificationPeriodKind.ANNUAL),
            _period("WF1", CertificationPeriodKind.OOS_FOLD),
            _period("WF2", CertificationPeriodKind.OOS_FOLD),
        ),
        fresh_holdout_integrity_passed=True,
        anti_leakage_audit_passed=True,
    )


def test_universal_standard_accepts_only_when_every_year_and_fold_passes() -> None:
    evidence = _green()

    assert passes_universal_trader_certification(evidence) is True
    assert universal_acceptance_failures(evidence) == ()


def test_no_combined_or_global_metric_has_acceptance_authority() -> None:
    names = {field.name for field in fields(UniversalTraderCertificationEvidence)}

    assert not any("combined" in name or "global" in name for name in names)


def test_one_bad_year_blocks_certification_even_if_other_year_is_strong() -> None:
    evidence = UniversalTraderCertificationEvidence(
        required_annual_period_ids=("2022", "2023"),
        required_oos_fold_ids=("WF1",),
        periods=(
            _period(
                "2022",
                CertificationPeriodKind.ANNUAL,
                profit_factor=Decimal("3.00"),
                expectancy_r=Decimal("0.60"),
            ),
            _period(
                "2023",
                CertificationPeriodKind.ANNUAL,
                profit_factor=Decimal("1.49"),
            ),
            _period("WF1", CertificationPeriodKind.OOS_FOLD),
        ),
        fresh_holdout_integrity_passed=True,
        anti_leakage_audit_passed=True,
    )

    failures = universal_acceptance_failures(evidence)

    assert "2023:PROFIT_FACTOR_BELOW_1_50" in failures
    assert passes_universal_trader_certification(evidence) is False


def test_each_year_must_meet_full_expectancy_gate() -> None:
    green = _green()
    periods = tuple(
        _period(
            period.period_id,
            period.kind,
            expectancy_r=(
                Decimal("0.149")
                if period.period_id == "2023"
                else period.expectancy_r
            ),
        )
        for period in green.periods
    )
    evidence = UniversalTraderCertificationEvidence(
        required_annual_period_ids=green.required_annual_period_ids,
        required_oos_fold_ids=green.required_oos_fold_ids,
        periods=periods,
        fresh_holdout_integrity_passed=True,
        anti_leakage_audit_passed=True,
    )

    assert "2023:EXPECTANCY_BELOW_0_15R" in universal_acceptance_failures(evidence)


def test_each_fold_is_a_hard_gate_too() -> None:
    green = _green()
    periods = tuple(
        _period(
            period.period_id,
            period.kind,
            sharpe=Decimal("1.49") if period.period_id == "WF2" else period.sharpe,
        )
        for period in green.periods
    )
    evidence = UniversalTraderCertificationEvidence(
        required_annual_period_ids=green.required_annual_period_ids,
        required_oos_fold_ids=green.required_oos_fold_ids,
        periods=periods,
        fresh_holdout_integrity_passed=True,
        anti_leakage_audit_passed=True,
    )

    assert "WF2:SHARPE_BELOW_1_50" in universal_acceptance_failures(evidence)


def test_missing_annual_slice_is_rejected_before_scoring() -> None:
    with pytest.raises(ValueError, match="annual certification coverage"):
        UniversalTraderCertificationEvidence(
            required_annual_period_ids=("2022", "2023"),
            required_oos_fold_ids=("WF1",),
            periods=(
                _period("2022", CertificationPeriodKind.ANNUAL),
                _period("WF1", CertificationPeriodKind.OOS_FOLD),
            ),
            fresh_holdout_integrity_passed=True,
            anti_leakage_audit_passed=True,
        )


def test_drawdown_costs_and_tail_survival_are_per_period_hard_gates() -> None:
    evidence = UniversalTraderCertificationEvidence(
        required_annual_period_ids=("2022",),
        required_oos_fold_ids=("WF1",),
        periods=(
            _period(
                "2022",
                CertificationPeriodKind.ANNUAL,
                observed_max_drawdown_r=Decimal("6.01"),
                monte_carlo_positive_probability=Decimal("0.899"),
                monte_carlo_p95_drawdown_r=Decimal("15.01"),
                post_cost_profit_factor=Decimal("1.00"),
                post_cost_expectancy_r=Decimal("0"),
            ),
            _period("WF1", CertificationPeriodKind.OOS_FOLD),
        ),
        fresh_holdout_integrity_passed=True,
        anti_leakage_audit_passed=True,
    )

    failures = universal_acceptance_failures(evidence)

    assert "2022:OBSERVED_MAX_DRAWDOWN_ABOVE_6R" in failures
    assert "2022:MONTE_CARLO_POSITIVE_BELOW_90_PERCENT" in failures
    assert "2022:MONTE_CARLO_P95_DRAWDOWN_ABOVE_15R" in failures
    assert "2022:POST_COST_PROFIT_FACTOR_NOT_ABOVE_1" in failures
    assert "2022:POST_COST_EXPECTANCY_NOT_POSITIVE" in failures


def test_burned_holdout_or_leakage_blocks_acceptance() -> None:
    green = _green()
    evidence = UniversalTraderCertificationEvidence(
        required_annual_period_ids=green.required_annual_period_ids,
        required_oos_fold_ids=green.required_oos_fold_ids,
        periods=green.periods,
        fresh_holdout_integrity_passed=False,
        anti_leakage_audit_passed=False,
    )

    failures = universal_acceptance_failures(evidence)

    assert "FRESH_HOLDOUT_INTEGRITY_NOT_PASSED" in failures
    assert "ANTI_LEAKAGE_AUDIT_NOT_PASSED" in failures
    assert passes_universal_trader_certification(evidence) is False
