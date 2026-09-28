"""Frozen protocol for CIBO USD60 / six-month maximum-capability certification.

This module defines the experiment contract only. It does not claim empirical
certification, does not mutate a broker, and does not give CIBO an economic target.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_tool_registry import CE2I_TOOL_REGISTRY


class CiboMaximumCapabilityClassification(StrEnum):
    CERTIFIED = "CERTIFIED"
    INTERVENTION_CONTINUE_ENGINEERING = "INTERVENTION_CONTINUE_ENGINEERING"
    REJECTED = "REJECTED"


@dataclass(frozen=True, slots=True)
class CiboMaximumCapabilityProtocol:
    protocol_id: str
    initial_capital_usd: Decimal
    duration_months: int
    trader_lineage_count: int
    tool_codes: tuple[str, ...]
    economic_target_usd: Decimal | None
    milestones_usd: tuple[Decimal, ...]
    baselines: tuple[str, ...]
    stress_scenarios: tuple[str, ...]
    monte_carlo_dimensions: tuple[str, ...]
    failure_scenarios: tuple[str, ...]
    mandatory_metrics: tuple[str, ...]
    frozen_at: datetime

    def __post_init__(self) -> None:
        if not self.protocol_id:
            raise CiboCapitalManagementError("capability protocol id is required")
        if self.initial_capital_usd != Decimal("60"):
            raise CiboCapitalManagementError(
                "maximum-capability protocol must start with exactly USD60"
            )
        if self.duration_months != 6:
            raise CiboCapitalManagementError(
                "maximum-capability protocol must run six complete months"
            )
        if self.trader_lineage_count != 7:
            raise CiboCapitalManagementError(
                "maximum-capability protocol requires all seven Trader lineages"
            )
        canonical = tuple(f"T{index:02d}" for index in range(1, 21))
        if self.tool_codes != canonical:
            raise CiboCapitalManagementError(
                "maximum-capability protocol requires canonical T01..T20"
            )
        registry_codes = tuple(tool.code for tool in CE2I_TOOL_REGISTRY)
        if registry_codes != canonical:
            raise CiboCapitalManagementError(
                "CE2I registry drift prevents capability protocol freeze"
            )
        if self.economic_target_usd is not None:
            raise CiboCapitalManagementError(
                "CIBO certification cannot contain an economic target"
            )
        if not self.milestones_usd:
            raise CiboCapitalManagementError(
                "observation-only milestones are required"
            )
        if tuple(sorted(set(self.milestones_usd))) != self.milestones_usd:
            raise CiboCapitalManagementError(
                "milestones must be unique and strictly ordered"
            )
        if any(item <= self.initial_capital_usd for item in self.milestones_usd):
            raise CiboCapitalManagementError(
                "milestones must exceed initial capital"
            )
        if self.baselines != (
            "MINIMAL_SEED_ONLY",
            "PREVIOUS_CIBO_CORE",
            "FULL_CIBO_T01_T20",
        ):
            raise CiboCapitalManagementError(
                "canonical baseline set is required"
            )
        _unique_nonempty(self.stress_scenarios, "stress scenarios")
        _unique_nonempty(self.monte_carlo_dimensions, "Monte Carlo dimensions")
        _unique_nonempty(self.failure_scenarios, "failure scenarios")
        _unique_nonempty(self.mandatory_metrics, "mandatory metrics")
        if self.frozen_at.tzinfo is None or self.frozen_at.utcoffset() is None:
            raise CiboCapitalManagementError(
                "capability protocol freeze must be timezone-aware"
            )


@dataclass(frozen=True, slots=True)
class CiboToolEmpiricalStatus:
    tool_code: str
    causal_input_evidence: bool
    correct_capital_source: bool
    correct_action: bool
    rollback_verified: bool
    fail_closed_verified: bool
    incremental_behavior_measured: bool
    activated_count: int
    blocked_count: int
    fail_closed_count: int

    def __post_init__(self) -> None:
        if self.tool_code not in FROZEN_CIBO_USD60_SIX_MONTH_PROTOCOL.tool_codes:
            raise CiboCapitalManagementError("unknown CE2I tool code")
        for name in (
            "causal_input_evidence",
            "correct_capital_source",
            "correct_action",
            "rollback_verified",
            "fail_closed_verified",
            "incremental_behavior_measured",
        ):
            if type(getattr(self, name)) is not bool:
                raise CiboCapitalManagementError(f"{name} must be bool")
        for name in ("activated_count", "blocked_count", "fail_closed_count"):
            value = getattr(self, name)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise CiboCapitalManagementError(
                    f"{name} must be non-negative int"
                )

    @property
    def empirically_complete(self) -> bool:
        return all(
            (
                self.causal_input_evidence,
                self.correct_capital_source,
                self.correct_action,
                self.rollback_verified,
                self.fail_closed_verified,
                self.incremental_behavior_measured,
            )
        )


@dataclass(frozen=True, slots=True)
class CiboMaximumCapabilityGateSet:
    six_complete_months: bool
    exact_initial_capital: bool
    survival: bool
    robust_economic_maximization: bool
    full_t01_t20_integration: bool
    capital_source_integrity: bool
    zero_double_spend: bool
    zero_outcome_awareness: bool
    zero_future_leakage: bool
    zero_martingale: bool
    zero_loss_recovery_sizing: bool
    risk_sovereignty: bool
    provider_constraint_integrity: bool
    fresh_oos_generalization: bool
    failure_resilience: bool
    baseline_comparison_complete: bool
    ablation_complete: bool
    stress_complete: bool
    monte_carlo_complete: bool
    trajectory_complete: bool
    all_tool_empirical_status_complete: bool

    def __post_init__(self) -> None:
        for name in self.__dataclass_fields__:
            if type(getattr(self, name)) is not bool:
                raise CiboCapitalManagementError(f"{name} must be bool")

    @property
    def all_pass(self) -> bool:
        return all(getattr(self, name) for name in self.__dataclass_fields__)


def classify_cibo_maximum_capability(
    gates: CiboMaximumCapabilityGateSet,
    *,
    hard_integrity_breach: bool,
    architecture_or_calibration_intervention_possible: bool,
) -> CiboMaximumCapabilityClassification:
    """Classify only after the complete experiment has been evaluated."""

    if not isinstance(gates, CiboMaximumCapabilityGateSet):
        raise CiboCapitalManagementError("canonical gate set is required")
    if type(hard_integrity_breach) is not bool:
        raise CiboCapitalManagementError("hard_integrity_breach must be bool")
    if type(architecture_or_calibration_intervention_possible) is not bool:
        raise CiboCapitalManagementError(
            "architecture_or_calibration_intervention_possible must be bool"
        )
    if hard_integrity_breach:
        return CiboMaximumCapabilityClassification.REJECTED
    if gates.all_pass:
        return CiboMaximumCapabilityClassification.CERTIFIED
    if architecture_or_calibration_intervention_possible:
        return (
            CiboMaximumCapabilityClassification.INTERVENTION_CONTINUE_ENGINEERING
        )
    return CiboMaximumCapabilityClassification.REJECTED


FROZEN_CIBO_USD60_SIX_MONTH_PROTOCOL = CiboMaximumCapabilityProtocol(
    protocol_id="CIBO_USD60_6M_MAXIMUM_REAL_CAPABILITY_V1",
    initial_capital_usd=Decimal("60"),
    duration_months=6,
    trader_lineage_count=7,
    tool_codes=tuple(f"T{index:02d}" for index in range(1, 21)),
    economic_target_usd=None,
    milestones_usd=tuple(
        Decimal(value)
        for value in ("100", "150", "200", "300", "500", "1000", "2500", "5000", "10000")
    ),
    baselines=(
        "MINIMAL_SEED_ONLY",
        "PREVIOUS_CIBO_CORE",
        "FULL_CIBO_T01_T20",
    ),
    stress_scenarios=(
        "LOSS_CLUSTERS",
        "BAD_TRADERS",
        "MULTIPLE_SIMULTANEOUS_LOSERS",
        "CORRELATION_SPIKES",
        "VOLATILITY_CHANGES",
        "SPREAD_DEGRADATION",
        "COMMISSION_DEGRADATION",
        "SLIPPAGE_DEGRADATION",
        "MARGIN_COMPRESSION",
        "CAPITAL_STARVATION",
        "PROVIDER_DEGRADATION",
        "STALE_EVIDENCE",
        "POSITION_RECONCILIATION_FAULTS",
        "RESERVATION_COLLISIONS",
    ),
    monte_carlo_dimensions=(
        "TRADE_ORDERING",
        "LOSS_CLUSTERING",
        "CAPITAL_PATH_DEPENDENCE",
        "OPPORTUNITY_TIMING",
        "CAPITAL_RELEASE_TIMING",
    ),
    failure_scenarios=(
        "RESTART",
        "DUPLICATE_EVENT",
        "DUPLICATE_RESERVATION",
        "PARTIAL_SETTLEMENT",
        "LEDGER_CRASH",
        "MUTATION_OUTCOME_UNKNOWN",
        "RECONCILIATION_MISMATCH",
        "STALE_SNAPSHOT",
        "PROVIDER_UNAVAILABLE",
        "CAPITAL_SOURCE_MISMATCH",
        "RELEASE_BEFORE_RECONCILIATION",
        "CONCURRENT_ALLOCATION",
    ),
    mandatory_metrics=(
        "INITIAL_CAPITAL",
        "ENDING_CAPITAL",
        "NET_REALIZED_PROFIT",
        "RETURN_ON_INITIAL_CAPITAL",
        "PEAK_CAPITAL",
        "MINIMUM_CAPITAL",
        "MAXIMUM_REALIZED_DRAWDOWN",
        "MAXIMUM_ECONOMIC_DRAWDOWN",
        "DRAWDOWN_DURATION",
        "OPPORTUNITY_COUNT",
        "EXECUTED_COUNT",
        "REDUCED_COUNT",
        "RISK_REJECTED_COUNT",
        "CIBO_HELD_COUNT",
        "EXPANDED_COUNT",
        "DERISKED_COUNT",
        "CAPITAL_UTILIZATION",
        "MARGIN_UTILIZATION",
        "RISK_UTILIZATION",
        "PROFIT_PER_RISK_DOLLAR",
        "PROFIT_PER_MARGIN_DOLLAR",
        "PROFIT_PER_CAPITAL_DAY",
        "CAPITAL_VELOCITY",
        "RECYCLED_RISK_CAPACITY",
        "RECYCLED_MARGIN_CAPACITY",
        "REALIZED_PROFIT_DEPLOYMENT",
        "PROTECTED_CAPACITY_DEPLOYMENT",
        "RESERVE_UTILIZATION",
        "OPTIONALITY_PRESERVATION",
        "CROSS_TRADER_REALLOCATIONS",
        "NETTING_EVENTS",
        "HEDGE_EVENTS",
        "CONVEX_EVENTS",
        "T01_T20_ACTIVATION_COUNTS",
        "T01_T20_BLOCKED_COUNTS",
        "T01_T20_FAIL_CLOSED_COUNTS",
        "FULL_CAPITAL_TRAJECTORY",
    ),
    frozen_at=datetime(2026, 9, 28, 11, 30, tzinfo=UTC),
)


def _unique_nonempty(values: tuple[str, ...], label: str) -> None:
    if not values or len(values) != len(set(values)) or any(not item for item in values):
        raise CiboCapitalManagementError(
            f"{label} must be unique and non-empty"
        )
