"""Phase 20A/B provider ambiguity sets and partial-identification bounds.

Exact historical provider economics are not available for the sealed Phase-18
population. This module therefore represents provider facts as explicit bounded
sets and asks a narrow question: is the methodology/provider minimum seed
robustly feasible, robustly infeasible, or only partially identified across
every admissible combination?

The contract never promotes current observations or research assumptions to
historical truth and owns no allocation, QORE Risk, or execution authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_chronological_replay import (
    CiboReplayCausalTrade,
)


def _finite(value: Decimal, *, name: str) -> None:
    if not isinstance(value, Decimal) or not value.is_finite():
        raise CiboCapitalManagementError(f"{name} must be finite Decimal")


@dataclass(frozen=True, slots=True)
class Phase20DecimalInterval:
    lower: Decimal
    upper: Decimal

    def __post_init__(self) -> None:
        _finite(self.lower, name="interval.lower")
        _finite(self.upper, name="interval.upper")
        if self.lower > self.upper:
            raise CiboCapitalManagementError(
                "provider ambiguity interval lower cannot exceed upper"
            )

    @classmethod
    def nonnegative(
        cls,
        lower: Decimal,
        upper: Decimal,
    ) -> Phase20DecimalInterval:
        interval = cls(lower=lower, upper=upper)
        if interval.lower < 0:
            raise CiboCapitalManagementError(
                "provider ambiguity interval must be non-negative"
            )
        return interval

    @classmethod
    def positive(
        cls,
        lower: Decimal,
        upper: Decimal,
    ) -> Phase20DecimalInterval:
        interval = cls(lower=lower, upper=upper)
        if interval.lower <= 0:
            raise CiboCapitalManagementError(
                "provider ambiguity interval must be positive"
            )
        return interval


class Phase20AmbiguityEvidenceClass(StrEnum):
    PROVIDER_DOCUMENTED_BOUND = "PROVIDER_DOCUMENTED_BOUND"
    FORWARD_OBSERVED_BOUND = "FORWARD_OBSERVED_BOUND"
    EXPLICIT_COUNTERFACTUAL_BOUND = "EXPLICIT_COUNTERFACTUAL_BOUND"
    MIXED_NON_HISTORICAL_BOUND = "MIXED_NON_HISTORICAL_BOUND"


class Phase20PartialIdentificationStatus(StrEnum):
    ROBUSTLY_FEASIBLE = "ROBUSTLY_FEASIBLE"
    ROBUSTLY_INFEASIBLE = "ROBUSTLY_INFEASIBLE"
    PARTIALLY_IDENTIFIED = "PARTIALLY_IDENTIFIED"


@dataclass(frozen=True, slots=True)
class Phase20ProviderAmbiguitySet:
    ambiguity_id: str
    evidence_id: str
    evidence_class: Phase20AmbiguityEvidenceClass
    provider_key: str
    qore_symbol: str
    provider_symbol: str
    tick_size: Phase20DecimalInterval
    tick_value: Phase20DecimalInterval
    spread_ticks: Phase20DecimalInterval
    commission_per_volume_usd: Phase20DecimalInterval
    slippage_reserve_per_volume_usd: Phase20DecimalInterval
    margin_per_volume_usd: Phase20DecimalInterval
    minimum_volume: Phase20DecimalInterval
    maximum_volume: Phase20DecimalInterval
    volume_step: Phase20DecimalInterval
    available_liquidity_volume: Phase20DecimalInterval
    execution_delay_ms: Phase20DecimalInterval
    historical_exact_claimed: bool = False
    outcome_tuned: bool = False
    policy_pass_tuned: bool = False
    allocation_authority: bool = False
    risk_authority: bool = False
    execution_authority: bool = False

    def __post_init__(self) -> None:
        if (
            not self.ambiguity_id
            or not self.evidence_id
            or not self.provider_key
            or not self.qore_symbol
            or not self.provider_symbol
        ):
            raise CiboCapitalManagementError(
                "Phase 20 provider ambiguity identity is required"
            )
        if type(self.evidence_class) is not Phase20AmbiguityEvidenceClass:
            raise CiboCapitalManagementError(
                "Phase 20 provider ambiguity evidence class is invalid"
            )
        for name in (
            "tick_size",
            "tick_value",
            "margin_per_volume_usd",
            "minimum_volume",
            "maximum_volume",
            "volume_step",
        ):
            interval = getattr(self, name)
            if interval.lower <= 0:
                raise CiboCapitalManagementError(
                    f"Phase 20 ambiguity {name} must be positive"
                )
        for name in (
            "spread_ticks",
            "commission_per_volume_usd",
            "slippage_reserve_per_volume_usd",
            "available_liquidity_volume",
            "execution_delay_ms",
        ):
            interval = getattr(self, name)
            if interval.lower < 0:
                raise CiboCapitalManagementError(
                    f"Phase 20 ambiguity {name} must be non-negative"
                )
        if self.minimum_volume.upper > self.maximum_volume.lower:
            raise CiboCapitalManagementError(
                "ambiguity volume rectangle can contain invalid provider bounds"
            )
        if self.volume_step.upper > self.maximum_volume.lower:
            raise CiboCapitalManagementError(
                "ambiguity volume step can exceed guaranteed maximum volume"
            )
        if (
            self.historical_exact_claimed
            or self.outcome_tuned
            or self.policy_pass_tuned
            or self.allocation_authority
            or self.risk_authority
            or self.execution_authority
        ):
            raise CiboCapitalManagementError(
                "Phase 20 provider ambiguity governance drift"
            )


@dataclass(frozen=True, slots=True)
class Phase20PartialIdentificationBounds:
    ambiguity_id: str
    status: Phase20PartialIdentificationStatus
    minimum_executable_volume_lower: Decimal
    minimum_executable_volume_upper: Decimal
    stop_loss_per_volume_usd_lower: Decimal
    stop_loss_per_volume_usd_upper: Decimal
    minimum_stop_risk_usd_lower: Decimal
    minimum_stop_risk_usd_upper: Decimal
    minimum_margin_usd_lower: Decimal
    minimum_margin_usd_upper: Decimal
    guaranteed_maximum_volume: Decimal
    possible_maximum_volume: Decimal
    guaranteed_liquidity_volume: Decimal
    possible_liquidity_volume: Decimal
    execution_delay_ms_lower: Decimal
    execution_delay_ms_upper: Decimal
    hard_risk_headroom_usd: Decimal
    margin_headroom_usd: Decimal
    reason: str
    historical_exact_claimed: bool = False
    allocation_authority: bool = False
    risk_authority: bool = False
    execution_authority: bool = False

    def __post_init__(self) -> None:
        if not self.ambiguity_id or not self.reason:
            raise CiboCapitalManagementError(
                "partial-identification identity/reason is required"
            )
        for name in (
            "minimum_executable_volume_lower",
            "minimum_executable_volume_upper",
            "stop_loss_per_volume_usd_lower",
            "stop_loss_per_volume_usd_upper",
            "minimum_stop_risk_usd_lower",
            "minimum_stop_risk_usd_upper",
            "minimum_margin_usd_lower",
            "minimum_margin_usd_upper",
            "guaranteed_maximum_volume",
            "possible_maximum_volume",
            "guaranteed_liquidity_volume",
            "possible_liquidity_volume",
            "execution_delay_ms_lower",
            "execution_delay_ms_upper",
            "hard_risk_headroom_usd",
            "margin_headroom_usd",
        ):
            _finite(getattr(self, name), name=name)
            if getattr(self, name) < 0:
                raise CiboCapitalManagementError(
                    f"{name} must be non-negative"
                )
        if (
            self.minimum_executable_volume_lower
            > self.minimum_executable_volume_upper
        ):
            raise CiboCapitalManagementError(
                "minimum executable volume bounds are invalid"
            )
        if self.stop_loss_per_volume_usd_lower > self.stop_loss_per_volume_usd_upper:
            raise CiboCapitalManagementError(
                "stop-loss-per-volume bounds are invalid"
            )
        if self.minimum_stop_risk_usd_lower > self.minimum_stop_risk_usd_upper:
            raise CiboCapitalManagementError(
                "minimum stop-risk bounds are invalid"
            )
        if self.minimum_margin_usd_lower > self.minimum_margin_usd_upper:
            raise CiboCapitalManagementError(
                "minimum margin bounds are invalid"
            )
        if (
            self.historical_exact_claimed
            or self.allocation_authority
            or self.risk_authority
            or self.execution_authority
        ):
            raise CiboCapitalManagementError(
                "partial-identification governance drift"
            )


def partially_identify_phase20_minimum_seed(
    *,
    causal: CiboReplayCausalTrade,
    ambiguity: Phase20ProviderAmbiguitySet,
    hard_risk_headroom_usd: Decimal,
    margin_headroom_usd: Decimal,
) -> Phase20PartialIdentificationBounds:
    """Bound minimum-seed feasibility over an admissible provider rectangle."""

    if not isinstance(causal, CiboReplayCausalTrade):
        raise CiboCapitalManagementError(
            "causal must be CiboReplayCausalTrade"
        )
    if not isinstance(ambiguity, Phase20ProviderAmbiguitySet):
        raise CiboCapitalManagementError(
            "ambiguity must be Phase20ProviderAmbiguitySet"
        )
    if causal.qore_symbol != ambiguity.qore_symbol:
        raise CiboCapitalManagementError(
            "provider ambiguity QORE symbol mismatch"
        )
    for name, value in (
        ("hard_risk_headroom_usd", hard_risk_headroom_usd),
        ("margin_headroom_usd", margin_headroom_usd),
    ):
        _finite(value, name=name)
        if value < 0:
            raise CiboCapitalManagementError(
                f"{name} must be non-negative"
            )

    distance = abs(causal.entry_price - causal.structural_stop)
    if distance <= 0:
        raise CiboCapitalManagementError(
            "partial identification requires positive structural stop distance"
        )

    stop_ticks_lower = distance / ambiguity.tick_size.upper
    stop_ticks_upper = distance / ambiguity.tick_size.lower
    raw_stop_lower = stop_ticks_lower * ambiguity.tick_value.lower
    raw_stop_upper = stop_ticks_upper * ambiguity.tick_value.upper

    spread_cost_lower = (
        ambiguity.spread_ticks.lower * ambiguity.tick_value.lower
    )
    spread_cost_upper = (
        ambiguity.spread_ticks.upper * ambiguity.tick_value.upper
    )
    execution_cost_lower = (
        spread_cost_lower
        + ambiguity.commission_per_volume_usd.lower
        + ambiguity.slippage_reserve_per_volume_usd.lower
    )
    execution_cost_upper = (
        spread_cost_upper
        + ambiguity.commission_per_volume_usd.upper
        + ambiguity.slippage_reserve_per_volume_usd.upper
    )
    stop_loss_per_volume_lower = raw_stop_lower + execution_cost_lower
    stop_loss_per_volume_upper = raw_stop_upper + execution_cost_upper

    steps = Decimal(causal.minimum_execution_steps)
    minimum_raw_lower = ambiguity.minimum_volume.lower * steps
    minimum_raw_upper = ambiguity.minimum_volume.upper * steps
    minimum_executable_volume_lower = minimum_raw_lower
    minimum_executable_volume_upper = (
        minimum_raw_upper + ambiguity.volume_step.upper
    )

    minimum_stop_risk_lower = (
        minimum_executable_volume_lower * stop_loss_per_volume_lower
    )
    minimum_stop_risk_upper = (
        minimum_executable_volume_upper * stop_loss_per_volume_upper
    )
    minimum_margin_lower = (
        minimum_executable_volume_lower * ambiguity.margin_per_volume_usd.lower
    )
    minimum_margin_upper = (
        minimum_executable_volume_upper * ambiguity.margin_per_volume_usd.upper
    )

    guaranteed_maximum_volume = ambiguity.maximum_volume.lower
    possible_maximum_volume = ambiguity.maximum_volume.upper
    guaranteed_liquidity = ambiguity.available_liquidity_volume.lower
    possible_liquidity = ambiguity.available_liquidity_volume.upper

    robust_feasible = (
        minimum_stop_risk_upper <= hard_risk_headroom_usd
        and minimum_margin_upper <= margin_headroom_usd
        and minimum_executable_volume_upper <= guaranteed_maximum_volume
        and minimum_executable_volume_upper <= guaranteed_liquidity
    )
    robust_infeasible = (
        minimum_stop_risk_lower > hard_risk_headroom_usd
        or minimum_margin_lower > margin_headroom_usd
        or minimum_executable_volume_lower > possible_maximum_volume
        or minimum_executable_volume_lower > possible_liquidity
    )

    if robust_feasible:
        status = Phase20PartialIdentificationStatus.ROBUSTLY_FEASIBLE
        reason = "minimum seed fits every admissible provider state"
    elif robust_infeasible:
        status = Phase20PartialIdentificationStatus.ROBUSTLY_INFEASIBLE
        reason = "minimum seed fails every admissible provider state"
    else:
        status = Phase20PartialIdentificationStatus.PARTIALLY_IDENTIFIED
        reason = "minimum seed feasibility changes within admissible provider states"

    return Phase20PartialIdentificationBounds(
        ambiguity_id=ambiguity.ambiguity_id,
        status=status,
        minimum_executable_volume_lower=minimum_executable_volume_lower,
        minimum_executable_volume_upper=minimum_executable_volume_upper,
        stop_loss_per_volume_usd_lower=stop_loss_per_volume_lower,
        stop_loss_per_volume_usd_upper=stop_loss_per_volume_upper,
        minimum_stop_risk_usd_lower=minimum_stop_risk_lower,
        minimum_stop_risk_usd_upper=minimum_stop_risk_upper,
        minimum_margin_usd_lower=minimum_margin_lower,
        minimum_margin_usd_upper=minimum_margin_upper,
        guaranteed_maximum_volume=guaranteed_maximum_volume,
        possible_maximum_volume=possible_maximum_volume,
        guaranteed_liquidity_volume=guaranteed_liquidity,
        possible_liquidity_volume=possible_liquidity,
        execution_delay_ms_lower=ambiguity.execution_delay_ms.lower,
        execution_delay_ms_upper=ambiguity.execution_delay_ms.upper,
        hard_risk_headroom_usd=hard_risk_headroom_usd,
        margin_headroom_usd=margin_headroom_usd,
        reason=reason,
    )
