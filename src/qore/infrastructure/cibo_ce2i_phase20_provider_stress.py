"""Counterfactual provider-economic stress for CIBO Phase 20.

This module exists because exact historical provider economics may be absent
while current provider facts are observable. It permits a clearly-labelled
counterfactual stress experiment using an explicit provider observation and
predeclared non-improving stress parameters.

It MUST NOT be used to claim historical provider economics, historical causal
decision replay, LIVE authority, Risk authority or execution authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
    TraderOpportunityEnvelope,
)
from qore.infrastructure.cibo_ce2i_chronological_replay import (
    CiboReplayCausalTrade,
)
from qore.infrastructure.cibo_provider_economic_normalization import (
    ProviderEconomicObservation,
)


def _finite_nonnegative(value: Decimal, *, name: str) -> None:
    if not isinstance(value, Decimal) or not value.is_finite() or value < 0:
        raise CiboCapitalManagementError(
            f"{name} must be finite non-negative Decimal"
        )


def _finite_at_least_one(value: Decimal, *, name: str) -> None:
    if not isinstance(value, Decimal) or not value.is_finite() or value < 1:
        raise CiboCapitalManagementError(
            f"{name} must be finite Decimal >= 1"
        )


@dataclass(frozen=True, slots=True)
class Phase20ProviderStressScenario:
    scenario_id: str
    evidence_id: str
    minimum_spread_ticks: Decimal
    spread_multiplier: Decimal
    commission_multiplier: Decimal
    minimum_slippage_reserve_per_volume_usd: Decimal
    margin_multiplier: Decimal
    broker_risk_buffer: Decimal

    def __post_init__(self) -> None:
        if not self.scenario_id or not self.evidence_id:
            raise CiboCapitalManagementError(
                "Phase 20 provider stress identity is required"
            )
        _finite_nonnegative(
            self.minimum_spread_ticks,
            name="minimum_spread_ticks",
        )
        _finite_nonnegative(
            self.minimum_slippage_reserve_per_volume_usd,
            name="minimum_slippage_reserve_per_volume_usd",
        )
        for name in (
            "spread_multiplier",
            "commission_multiplier",
            "margin_multiplier",
            "broker_risk_buffer",
        ):
            _finite_at_least_one(getattr(self, name), name=name)


@dataclass(frozen=True, slots=True)
class Phase20CounterfactualProviderEconomics:
    scenario_id: str
    provider_key: str
    provider_symbol: str
    source_observed_at_iso: str
    stressed_spread_ticks: Decimal
    stressed_spread_cost_per_volume_usd: Decimal
    stressed_commission_per_volume_usd: Decimal
    stressed_slippage_reserve_per_volume_usd: Decimal
    stressed_execution_cost_per_volume_usd: Decimal
    stressed_margin_per_volume_usd: Decimal
    tick_size: Decimal
    tick_value: Decimal
    minimum_volume: Decimal
    maximum_volume: Decimal
    volume_step: Decimal
    broker_risk_buffer: Decimal
    source_evidence_id: str
    historical_provider_economics_claimed: bool = False
    historical_causality_claimed: bool = False
    allocation_authority: bool = False
    risk_authority: bool = False
    execution_authority: bool = False

    def __post_init__(self) -> None:
        if (
            self.historical_provider_economics_claimed
            or self.historical_causality_claimed
            or self.allocation_authority
            or self.risk_authority
            or self.execution_authority
        ):
            raise CiboCapitalManagementError(
                "counterfactual provider stress cannot claim historical or trading authority"
            )


@dataclass(frozen=True, slots=True)
class Phase20CounterfactualOpportunity:
    opportunity: TraderOpportunityEnvelope
    economics: Phase20CounterfactualProviderEconomics
    research_only: bool = True
    demo_execution_authorized: bool = False
    live_authorized: bool = False
    real_capital_authorized: bool = False

    def __post_init__(self) -> None:
        if (
            not self.research_only
            or self.demo_execution_authorized
            or self.live_authorized
            or self.real_capital_authorized
        ):
            raise CiboCapitalManagementError(
                "Phase 20 counterfactual opportunity governance drift"
            )


def build_phase20_counterfactual_provider_stress(
    *,
    causal: CiboReplayCausalTrade,
    observation: ProviderEconomicObservation,
    scenario: Phase20ProviderStressScenario,
) -> Phase20CounterfactualOpportunity:
    """Apply an explicit current-provider stress scenario to historical geometry.

    The historical signal/entry/stop/target remain unchanged. Provider economics
    come from the supplied observation and stress scenario, so the result is a
    counterfactual robustness experiment, not an exact historical replay.
    """

    if not isinstance(causal, CiboReplayCausalTrade):
        raise CiboCapitalManagementError(
            "causal must be CiboReplayCausalTrade"
        )
    if not isinstance(observation, ProviderEconomicObservation):
        raise CiboCapitalManagementError(
            "observation must be ProviderEconomicObservation"
        )
    if not isinstance(scenario, Phase20ProviderStressScenario):
        raise CiboCapitalManagementError(
            "scenario must be Phase20ProviderStressScenario"
        )
    if causal.qore_symbol != observation.qore_symbol:
        raise CiboCapitalManagementError(
            "counterfactual provider stress QORE symbol mismatch"
        )

    observed_spread_ticks = (
        observation.ask - observation.bid
    ) / observation.tick_size
    stressed_spread_ticks = max(
        scenario.minimum_spread_ticks,
        observed_spread_ticks * scenario.spread_multiplier,
    )
    stressed_spread_cost = stressed_spread_ticks * observation.tick_value
    stressed_commission = (
        observation.commission_per_volume_usd
        * scenario.commission_multiplier
    )
    stressed_slippage = max(
        observation.slippage_reserve_per_volume_usd,
        scenario.minimum_slippage_reserve_per_volume_usd,
    )
    stressed_execution_cost = (
        stressed_spread_cost
        + stressed_commission
        + stressed_slippage
    )
    stressed_margin = (
        observation.margin_per_volume * scenario.margin_multiplier
    )

    stop_ticks = (
        abs(causal.entry_price - causal.structural_stop)
        / observation.tick_size
    )
    raw_stop_loss_per_volume_usd = stop_ticks * observation.tick_value
    stop_loss_per_volume = (
        raw_stop_loss_per_volume_usd + stressed_execution_cost
    ) * scenario.broker_risk_buffer
    if stop_loss_per_volume <= 0:
        raise CiboCapitalManagementError(
            "counterfactual stop loss per volume must be positive"
        )

    opportunity = TraderOpportunityEnvelope(
        trader_id=causal.trader_id,
        signal_fingerprint=causal.signal_fingerprint,
        qore_symbol=causal.qore_symbol,
        provider_symbol=observation.provider_symbol,
        side=causal.side,
        entry_type="counterfactual_provider_stress",
        intended_entry=causal.entry_price,
        stop_loss=causal.structural_stop,
        take_profit=causal.technical_target,
        stop_loss_per_volume=stop_loss_per_volume,
        margin_per_volume=stressed_margin,
        volume_step=observation.volume_step,
        minimum_volume=observation.minimum_volume,
        maximum_volume=observation.maximum_volume,
        minimum_execution_steps=causal.minimum_execution_steps,
    )
    economics = Phase20CounterfactualProviderEconomics(
        scenario_id=scenario.scenario_id,
        provider_key=observation.provider_key,
        provider_symbol=observation.provider_symbol,
        source_observed_at_iso=observation.observed_at.isoformat(),
        stressed_spread_ticks=stressed_spread_ticks,
        stressed_spread_cost_per_volume_usd=stressed_spread_cost,
        stressed_commission_per_volume_usd=stressed_commission,
        stressed_slippage_reserve_per_volume_usd=stressed_slippage,
        stressed_execution_cost_per_volume_usd=stressed_execution_cost,
        stressed_margin_per_volume_usd=stressed_margin,
        tick_size=observation.tick_size,
        tick_value=observation.tick_value,
        minimum_volume=observation.minimum_volume,
        maximum_volume=observation.maximum_volume,
        volume_step=observation.volume_step,
        broker_risk_buffer=scenario.broker_risk_buffer,
        source_evidence_id=(
            f"{scenario.evidence_id}|provider:{observation.provider_key}:"
            f"{observation.observed_at.isoformat()}"
        ),
    )
    return Phase20CounterfactualOpportunity(
        opportunity=opportunity,
        economics=economics,
    )
