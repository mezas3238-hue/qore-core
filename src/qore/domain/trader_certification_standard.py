"""Universal QORE Trader certification gates (UTC-001).

This module is intentionally strategy-agnostic. It encodes only the universal
acceptance floors that every Trader must satisfy before it can be called
ACCEPTED. Strategy-specific methodology and sample-sufficiency rules live
outside this module and may only tighten these gates, never weaken them.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

MIN_OOS_PROFIT_FACTOR = Decimal("1.50")
MIN_COMBINED_OOS_PROFIT_FACTOR = Decimal("1.70")
MIN_COMBINED_OOS_EXPECTANCY_R = Decimal("0.15")
MIN_OOS_SHARPE = Decimal("1.50")
MIN_OOS_SORTINO = Decimal("2.00")
MAX_OBSERVED_DRAWDOWN_R = Decimal("6")
MIN_MONTE_CARLO_POSITIVE_PROBABILITY = Decimal("0.90")
MAX_MONTE_CARLO_P95_DRAWDOWN_R = Decimal("15")
MIN_PAYOFF_RATIO = Decimal("1.20")
MIN_POST_COST_PROFIT_FACTOR_EXCLUSIVE = Decimal("1.00")


@dataclass(frozen=True, slots=True)
class UniversalTraderCertificationEvidence:
    """Strategy-independent evidence required by UTC-001."""

    oos_profit_factors: tuple[Decimal, ...]
    combined_oos_profit_factor: Decimal
    oos_expectancies_r: tuple[Decimal, ...]
    combined_oos_expectancy_r: Decimal
    oos_sharpes: tuple[Decimal, ...]
    oos_sortinos: tuple[Decimal, ...]
    observed_max_drawdown_r: Decimal
    monte_carlo_positive_probability: Decimal
    monte_carlo_p95_drawdown_r: Decimal
    payoff_ratio: Decimal
    post_cost_profit_factor: Decimal
    post_cost_expectancy_r: Decimal
    temporal_stability_passed: bool
    loss_cluster_gate_passed: bool
    fresh_holdout_integrity_passed: bool
    anti_leakage_audit_passed: bool
    density_sufficient_after_quality: bool

    def __post_init__(self) -> None:
        required_series = (
            ("oos_profit_factors", self.oos_profit_factors),
            ("oos_expectancies_r", self.oos_expectancies_r),
            ("oos_sharpes", self.oos_sharpes),
            ("oos_sortinos", self.oos_sortinos),
        )
        for name, values in required_series:
            if not values:
                raise ValueError(f"{name} must contain independent OOS evidence")

        if not Decimal("0") <= self.monte_carlo_positive_probability <= Decimal("1"):
            raise ValueError("monte_carlo_positive_probability must be in [0, 1]")

        non_negative = (
            ("observed_max_drawdown_r", self.observed_max_drawdown_r),
            ("monte_carlo_p95_drawdown_r", self.monte_carlo_p95_drawdown_r),
        )
        for name, value in non_negative:
            if value < 0:
                raise ValueError(f"{name} cannot be negative")

        for name in (
            "temporal_stability_passed",
            "loss_cluster_gate_passed",
            "fresh_holdout_integrity_passed",
            "anti_leakage_audit_passed",
            "density_sufficient_after_quality",
        ):
            if type(getattr(self, name)) is not bool:
                raise ValueError(f"{name} must be bool")


def universal_acceptance_failures(
    evidence: UniversalTraderCertificationEvidence,
) -> tuple[str, ...]:
    """Return every UTC-001 acceptance failure without averaging it away."""

    failures: list[str] = []

    if any(value < MIN_OOS_PROFIT_FACTOR for value in evidence.oos_profit_factors):
        failures.append("OOS_PROFIT_FACTOR_BELOW_1_50")
    if evidence.combined_oos_profit_factor < MIN_COMBINED_OOS_PROFIT_FACTOR:
        failures.append("COMBINED_OOS_PROFIT_FACTOR_BELOW_1_70")

    if any(value <= 0 for value in evidence.oos_expectancies_r):
        failures.append("OOS_EXPECTANCY_NOT_POSITIVE")
    if evidence.combined_oos_expectancy_r < MIN_COMBINED_OOS_EXPECTANCY_R:
        failures.append("COMBINED_OOS_EXPECTANCY_BELOW_0_15R")

    if any(value < MIN_OOS_SHARPE for value in evidence.oos_sharpes):
        failures.append("OOS_SHARPE_BELOW_1_50")
    if any(value < MIN_OOS_SORTINO for value in evidence.oos_sortinos):
        failures.append("OOS_SORTINO_BELOW_2_00")

    if evidence.observed_max_drawdown_r > MAX_OBSERVED_DRAWDOWN_R:
        failures.append("OBSERVED_MAX_DRAWDOWN_ABOVE_6R")

    if (
        evidence.monte_carlo_positive_probability
        < MIN_MONTE_CARLO_POSITIVE_PROBABILITY
    ):
        failures.append("MONTE_CARLO_POSITIVE_PROBABILITY_BELOW_90_PERCENT")
    if evidence.monte_carlo_p95_drawdown_r > MAX_MONTE_CARLO_P95_DRAWDOWN_R:
        failures.append("MONTE_CARLO_P95_DRAWDOWN_ABOVE_15R")

    if evidence.payoff_ratio < MIN_PAYOFF_RATIO:
        failures.append("PAYOFF_RATIO_BELOW_1_20")

    if evidence.post_cost_profit_factor <= MIN_POST_COST_PROFIT_FACTOR_EXCLUSIVE:
        failures.append("POST_COST_PROFIT_FACTOR_NOT_ABOVE_1")
    if evidence.post_cost_expectancy_r <= 0:
        failures.append("POST_COST_EXPECTANCY_NOT_POSITIVE")

    boolean_gates = (
        (
            evidence.temporal_stability_passed,
            "TEMPORAL_STABILITY_NOT_PROVEN",
        ),
        (
            evidence.loss_cluster_gate_passed,
            "LOSS_CLUSTER_GATE_NOT_PASSED",
        ),
        (
            evidence.fresh_holdout_integrity_passed,
            "FRESH_HOLDOUT_INTEGRITY_NOT_PASSED",
        ),
        (
            evidence.anti_leakage_audit_passed,
            "ANTI_LEAKAGE_AUDIT_NOT_PASSED",
        ),
        (
            evidence.density_sufficient_after_quality,
            "DENSITY_NOT_SUFFICIENT_AFTER_QUALITY",
        ),
    )
    failures.extend(reason for passed, reason in boolean_gates if not passed)

    return tuple(failures)


def passes_universal_trader_certification(
    evidence: UniversalTraderCertificationEvidence,
) -> bool:
    """Return True only when every universal UTC-001 gate passes."""

    return not universal_acceptance_failures(evidence)
