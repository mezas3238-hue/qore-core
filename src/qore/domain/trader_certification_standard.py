"""Universal QORE Trader certification gates (UTC-001).

UTC-001 is intentionally strategy-agnostic and temporally strict. Acceptance is
evaluated independently for every predeclared annual slice and every predeclared
OOS fold. Global/combined metrics have no certification authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

MIN_PROFIT_FACTOR = Decimal("1.50")
MIN_EXPECTANCY_R = Decimal("0.15")
MIN_SHARPE = Decimal("1.50")
MIN_SORTINO = Decimal("2.00")
MAX_OBSERVED_DRAWDOWN_R = Decimal("6")
MIN_MONTE_CARLO_POSITIVE_PROBABILITY = Decimal("0.90")
MAX_MONTE_CARLO_P95_DRAWDOWN_R = Decimal("15")
MIN_PAYOFF_RATIO = Decimal("1.20")
MIN_POST_COST_PROFIT_FACTOR_EXCLUSIVE = Decimal("1.00")


class CertificationPeriodKind(StrEnum):
    """Mandatory temporal unit evaluated independently by UTC-001."""

    ANNUAL = "ANNUAL"
    OOS_FOLD = "OOS_FOLD"


@dataclass(frozen=True, slots=True)
class CertificationPeriodEvidence:
    """Complete UTC-001 evidence for one required year or OOS fold."""

    period_id: str
    kind: CertificationPeriodKind
    profit_factor: Decimal
    expectancy_r: Decimal
    sharpe: Decimal
    sortino: Decimal
    observed_max_drawdown_r: Decimal
    monte_carlo_positive_probability: Decimal
    monte_carlo_p95_drawdown_r: Decimal
    payoff_ratio: Decimal
    post_cost_profit_factor: Decimal
    post_cost_expectancy_r: Decimal
    loss_cluster_gate_passed: bool
    density_sufficient_after_quality: bool

    def __post_init__(self) -> None:
        if not self.period_id.strip():
            raise ValueError("period_id is required")
        if type(self.kind) is not CertificationPeriodKind:
            raise ValueError("kind must be CertificationPeriodKind")
        if not Decimal("0") <= self.monte_carlo_positive_probability <= Decimal("1"):
            raise ValueError("monte_carlo_positive_probability must be in [0, 1]")
        if self.observed_max_drawdown_r < 0:
            raise ValueError("observed_max_drawdown_r cannot be negative")
        if self.monte_carlo_p95_drawdown_r < 0:
            raise ValueError("monte_carlo_p95_drawdown_r cannot be negative")
        for name in (
            "loss_cluster_gate_passed",
            "density_sufficient_after_quality",
        ):
            if type(getattr(self, name)) is not bool:
                raise ValueError(f"{name} must be bool")


@dataclass(frozen=True, slots=True)
class UniversalTraderCertificationEvidence:
    """Predeclared temporal evidence required for universal acceptance."""

    required_annual_period_ids: tuple[str, ...]
    required_oos_fold_ids: tuple[str, ...]
    periods: tuple[CertificationPeriodEvidence, ...]
    fresh_holdout_integrity_passed: bool
    anti_leakage_audit_passed: bool

    def __post_init__(self) -> None:
        if not self.required_annual_period_ids:
            raise ValueError("at least one required annual period is mandatory")
        if not self.required_oos_fold_ids:
            raise ValueError("at least one required OOS fold is mandatory")
        if len(set(self.required_annual_period_ids)) != len(self.required_annual_period_ids):
            raise ValueError("required annual period IDs must be unique")
        if len(set(self.required_oos_fold_ids)) != len(self.required_oos_fold_ids):
            raise ValueError("required OOS fold IDs must be unique")
        if not self.periods:
            raise ValueError("periods cannot be empty")

        period_ids = tuple(period.period_id for period in self.periods)
        if len(set(period_ids)) != len(period_ids):
            raise ValueError("period IDs must be unique")

        actual_annual = {
            period.period_id
            for period in self.periods
            if period.kind is CertificationPeriodKind.ANNUAL
        }
        actual_folds = {
            period.period_id
            for period in self.periods
            if period.kind is CertificationPeriodKind.OOS_FOLD
        }
        if actual_annual != set(self.required_annual_period_ids):
            raise ValueError("annual certification coverage is incomplete or unexpected")
        if actual_folds != set(self.required_oos_fold_ids):
            raise ValueError("OOS fold certification coverage is incomplete or unexpected")

        for name in (
            "fresh_holdout_integrity_passed",
            "anti_leakage_audit_passed",
        ):
            if type(getattr(self, name)) is not bool:
                raise ValueError(f"{name} must be bool")


def _period_failures(period: CertificationPeriodEvidence) -> tuple[str, ...]:
    prefix = period.period_id
    failures: list[str] = []

    if period.profit_factor < MIN_PROFIT_FACTOR:
        failures.append(f"{prefix}:PROFIT_FACTOR_BELOW_1_50")
    if period.expectancy_r < MIN_EXPECTANCY_R:
        failures.append(f"{prefix}:EXPECTANCY_BELOW_0_15R")
    if period.sharpe < MIN_SHARPE:
        failures.append(f"{prefix}:SHARPE_BELOW_1_50")
    if period.sortino < MIN_SORTINO:
        failures.append(f"{prefix}:SORTINO_BELOW_2_00")
    if period.observed_max_drawdown_r > MAX_OBSERVED_DRAWDOWN_R:
        failures.append(f"{prefix}:OBSERVED_MAX_DRAWDOWN_ABOVE_6R")
    if (
        period.monte_carlo_positive_probability
        < MIN_MONTE_CARLO_POSITIVE_PROBABILITY
    ):
        failures.append(f"{prefix}:MONTE_CARLO_POSITIVE_BELOW_90_PERCENT")
    if period.monte_carlo_p95_drawdown_r > MAX_MONTE_CARLO_P95_DRAWDOWN_R:
        failures.append(f"{prefix}:MONTE_CARLO_P95_DRAWDOWN_ABOVE_15R")
    if period.payoff_ratio < MIN_PAYOFF_RATIO:
        failures.append(f"{prefix}:PAYOFF_RATIO_BELOW_1_20")
    if period.post_cost_profit_factor <= MIN_POST_COST_PROFIT_FACTOR_EXCLUSIVE:
        failures.append(f"{prefix}:POST_COST_PROFIT_FACTOR_NOT_ABOVE_1")
    if period.post_cost_expectancy_r <= 0:
        failures.append(f"{prefix}:POST_COST_EXPECTANCY_NOT_POSITIVE")
    if not period.loss_cluster_gate_passed:
        failures.append(f"{prefix}:LOSS_CLUSTER_GATE_NOT_PASSED")
    if not period.density_sufficient_after_quality:
        failures.append(f"{prefix}:DENSITY_NOT_SUFFICIENT_AFTER_QUALITY")

    return tuple(failures)


def universal_acceptance_failures(
    evidence: UniversalTraderCertificationEvidence,
) -> tuple[str, ...]:
    """Return all strict temporal failures; no period may be averaged away."""

    failures: list[str] = []
    for period in evidence.periods:
        failures.extend(_period_failures(period))

    if not evidence.fresh_holdout_integrity_passed:
        failures.append("FRESH_HOLDOUT_INTEGRITY_NOT_PASSED")
    if not evidence.anti_leakage_audit_passed:
        failures.append("ANTI_LEAKAGE_AUDIT_NOT_PASSED")

    return tuple(failures)


def passes_universal_trader_certification(
    evidence: UniversalTraderCertificationEvidence,
) -> bool:
    """Return True only when every required year/fold passes every UTC-001 gate."""

    return not universal_acceptance_failures(evidence)
