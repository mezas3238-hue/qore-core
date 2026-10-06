"""Provider-economic normalization for CIBO CMA.

The normalizer converts provider/broker contract facts plus a volume-free
TraderOpportunityEnvelope into comparable USD economics. It never chooses a
Trader risk budget and never owns technical geometry.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import ROUND_CEILING, Decimal

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
    TraderOpportunityEnvelope,
)
from qore.infrastructure.cibo_fundednext_provider import (
    FundedNextCiboSymbolSpecification,
)
from qore.infrastructure.ctrader_demo_compat import CTraderDemoSymbolSpecification


@dataclass(frozen=True, slots=True)
class ProviderEconomicObservation:
    provider_key: str
    qore_symbol: str
    provider_symbol: str
    bid: Decimal
    ask: Decimal
    contract_size: Decimal
    tick_size: Decimal
    tick_value: Decimal
    minimum_volume: Decimal
    maximum_volume: Decimal
    volume_step: Decimal
    margin_per_volume: Decimal
    commission_per_volume_usd: Decimal
    slippage_reserve_per_volume_usd: Decimal
    observed_at: datetime

    def __post_init__(self) -> None:
        if not self.provider_key or not self.qore_symbol or not self.provider_symbol:
            raise CiboCapitalManagementError(
                "provider/symbol identity is required"
            )
        for name in (
            "bid",
            "ask",
            "contract_size",
            "tick_size",
            "tick_value",
            "minimum_volume",
            "maximum_volume",
            "volume_step",
            "margin_per_volume",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, Decimal)
                or not value.is_finite()
                or value <= 0
            ):
                raise CiboCapitalManagementError(
                    f"{name} must be finite positive Decimal"
                )
        for name in (
            "commission_per_volume_usd",
            "slippage_reserve_per_volume_usd",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, Decimal)
                or not value.is_finite()
                or value < 0
            ):
                raise CiboCapitalManagementError(
                    f"{name} must be finite non-negative Decimal"
                )
        if self.ask < self.bid:
            raise CiboCapitalManagementError("ask cannot be below bid")
        if self.maximum_volume < self.minimum_volume:
            raise CiboCapitalManagementError("provider volume bounds invalid")
        if (
            self.observed_at.tzinfo is None
            or self.observed_at.utcoffset() is None
        ):
            raise CiboCapitalManagementError(
                "provider observation time must be timezone-aware"
            )


@dataclass(frozen=True, slots=True)
class ProviderEconomicEnvelope:
    provider_key: str
    qore_symbol: str
    provider_symbol: str
    side: str
    intended_entry: Decimal
    stop_loss: Decimal
    contract_size: Decimal
    notional_per_volume_usd: Decimal
    provider_units_per_volume: Decimal
    raw_stop_loss_per_volume_usd: Decimal
    cibo_stop_loss_per_volume_usd: Decimal
    spread_cost_per_volume_usd: Decimal
    commission_per_volume_usd: Decimal
    slippage_reserve_per_volume_usd: Decimal
    execution_cost_per_volume_usd: Decimal
    margin_per_volume_usd: Decimal
    minimum_execution_steps: int
    minimum_executable_volume: Decimal
    minimum_provider_units: Decimal
    minimum_stop_risk_usd: Decimal
    minimum_margin_usd: Decimal
    minimum_execution_cost_usd: Decimal
    maximum_volume: Decimal
    volume_step: Decimal
    observed_at: datetime


@dataclass(frozen=True, slots=True)
class ProviderSeedFeasibility:
    executable: bool
    minimum_executable_volume: Decimal
    minimum_stop_risk_usd: Decimal
    minimum_margin_usd: Decimal
    hard_risk_headroom_usd: Decimal
    margin_headroom_usd: Decimal
    reason: str


def normalize_provider_economics(
    *,
    opportunity: TraderOpportunityEnvelope,
    observation: ProviderEconomicObservation,
) -> ProviderEconomicEnvelope:
    """Normalize one opportunity into comparable provider USD economics."""

    if not isinstance(opportunity, TraderOpportunityEnvelope):
        raise CiboCapitalManagementError(
            "opportunity must be TraderOpportunityEnvelope"
        )
    if not isinstance(observation, ProviderEconomicObservation):
        raise CiboCapitalManagementError(
            "observation must be ProviderEconomicObservation"
        )
    if opportunity.qore_symbol != observation.qore_symbol:
        raise CiboCapitalManagementError("provider QORE symbol mismatch")
    if opportunity.provider_symbol != observation.provider_symbol:
        raise CiboCapitalManagementError("provider symbol mismatch")

    for name, expected, observed in (
        ("minimum_volume", opportunity.minimum_volume, observation.minimum_volume),
        ("maximum_volume", opportunity.maximum_volume, observation.maximum_volume),
        ("volume_step", opportunity.volume_step, observation.volume_step),
        (
            "margin_per_volume",
            opportunity.margin_per_volume,
            observation.margin_per_volume,
        ),
    ):
        if expected != observed:
            raise CiboCapitalManagementError(
                f"opportunity/provider {name} drift"
            )

    raw_stop_ticks = (
        abs(opportunity.intended_entry - opportunity.stop_loss)
        / observation.tick_size
    )
    raw_stop_per_volume = raw_stop_ticks * observation.tick_value
    if raw_stop_per_volume <= 0:
        raise CiboCapitalManagementError(
            "provider raw stop economics must be positive"
        )
    if opportunity.stop_loss_per_volume < raw_stop_per_volume:
        raise CiboCapitalManagementError(
            "CIBO opportunity understates provider raw stop risk"
        )

    spread_ticks = (observation.ask - observation.bid) / observation.tick_size
    spread_cost_per_volume = spread_ticks * observation.tick_value
    execution_cost_per_volume = (
        spread_cost_per_volume
        + observation.commission_per_volume_usd
        + observation.slippage_reserve_per_volume_usd
    )

    minimum_raw = (
        observation.minimum_volume
        * Decimal(opportunity.minimum_execution_steps)
    )
    minimum_steps = (
        minimum_raw / observation.volume_step
    ).to_integral_value(rounding=ROUND_CEILING)
    minimum_executable_volume = minimum_steps * observation.volume_step
    if minimum_executable_volume > observation.maximum_volume:
        raise CiboCapitalManagementError(
            "methodology minimum execution exceeds provider maximum volume"
        )

    provider_units_per_volume = observation.contract_size
    minimum_provider_units = (
        minimum_executable_volume * provider_units_per_volume
    )
    minimum_stop_risk = (
        minimum_executable_volume * opportunity.stop_loss_per_volume
    )
    minimum_margin = (
        minimum_executable_volume * observation.margin_per_volume
    )
    minimum_execution_cost = (
        minimum_executable_volume * execution_cost_per_volume
    )

    return ProviderEconomicEnvelope(
        provider_key=observation.provider_key,
        qore_symbol=observation.qore_symbol,
        provider_symbol=observation.provider_symbol,
        side=opportunity.side,
        intended_entry=opportunity.intended_entry,
        stop_loss=opportunity.stop_loss,
        contract_size=observation.contract_size,
        notional_per_volume_usd=(
            opportunity.intended_entry * observation.contract_size
        ),
        provider_units_per_volume=provider_units_per_volume,
        raw_stop_loss_per_volume_usd=raw_stop_per_volume,
        cibo_stop_loss_per_volume_usd=opportunity.stop_loss_per_volume,
        spread_cost_per_volume_usd=spread_cost_per_volume,
        commission_per_volume_usd=observation.commission_per_volume_usd,
        slippage_reserve_per_volume_usd=(
            observation.slippage_reserve_per_volume_usd
        ),
        execution_cost_per_volume_usd=execution_cost_per_volume,
        margin_per_volume_usd=observation.margin_per_volume,
        minimum_execution_steps=opportunity.minimum_execution_steps,
        minimum_executable_volume=minimum_executable_volume,
        minimum_provider_units=minimum_provider_units,
        minimum_stop_risk_usd=minimum_stop_risk,
        minimum_margin_usd=minimum_margin,
        minimum_execution_cost_usd=minimum_execution_cost,
        maximum_volume=observation.maximum_volume,
        volume_step=observation.volume_step,
        observed_at=observation.observed_at,
    )


def evaluate_minimum_seed_feasibility(
    envelope: ProviderEconomicEnvelope,
    *,
    hard_risk_headroom_usd: Decimal,
    margin_headroom_usd: Decimal,
) -> ProviderSeedFeasibility:
    """Check whether the provider/methodology minimum can fit current headroom."""

    if not isinstance(envelope, ProviderEconomicEnvelope):
        raise CiboCapitalManagementError(
            "envelope must be ProviderEconomicEnvelope"
        )
    for name, value in (
        ("hard_risk_headroom_usd", hard_risk_headroom_usd),
        ("margin_headroom_usd", margin_headroom_usd),
    ):
        if (
            not isinstance(value, Decimal)
            or not value.is_finite()
            or value < 0
        ):
            raise CiboCapitalManagementError(
                f"{name} must be finite non-negative Decimal"
            )

    if envelope.minimum_stop_risk_usd > hard_risk_headroom_usd:
        return ProviderSeedFeasibility(
            executable=False,
            minimum_executable_volume=envelope.minimum_executable_volume,
            minimum_stop_risk_usd=envelope.minimum_stop_risk_usd,
            minimum_margin_usd=envelope.minimum_margin_usd,
            hard_risk_headroom_usd=hard_risk_headroom_usd,
            margin_headroom_usd=margin_headroom_usd,
            reason="provider/methodology minimum exceeds hard risk headroom",
        )
    if envelope.minimum_margin_usd > margin_headroom_usd:
        return ProviderSeedFeasibility(
            executable=False,
            minimum_executable_volume=envelope.minimum_executable_volume,
            minimum_stop_risk_usd=envelope.minimum_stop_risk_usd,
            minimum_margin_usd=envelope.minimum_margin_usd,
            hard_risk_headroom_usd=hard_risk_headroom_usd,
            margin_headroom_usd=margin_headroom_usd,
            reason="provider/methodology minimum exceeds margin headroom",
        )
    return ProviderSeedFeasibility(
        executable=True,
        minimum_executable_volume=envelope.minimum_executable_volume,
        minimum_stop_risk_usd=envelope.minimum_stop_risk_usd,
        minimum_margin_usd=envelope.minimum_margin_usd,
        hard_risk_headroom_usd=hard_risk_headroom_usd,
        margin_headroom_usd=margin_headroom_usd,
        reason="provider/methodology minimum fits CIBO headroom",
    )


def ctrader_demo_economic_observation(
    *,
    qore_symbol: str,
    provider_key: str,
    spec: CTraderDemoSymbolSpecification,
    slippage_reserve_per_volume_usd: Decimal = Decimal(0),
) -> ProviderEconomicObservation:
    """Adapt the current cTrader DEMO symbol specification without sizing."""

    if not isinstance(spec, CTraderDemoSymbolSpecification):
        raise CiboCapitalManagementError(
            "spec must be CTraderDemoSymbolSpecification"
        )
    return ProviderEconomicObservation(
        provider_key=provider_key,
        qore_symbol=qore_symbol,
        provider_symbol=spec.provider_symbol,
        bid=spec.bid,
        ask=spec.ask,
        contract_size=spec.contract_size,
        tick_size=spec.tick_size,
        tick_value=spec.tick_value,
        minimum_volume=spec.minimum_volume,
        maximum_volume=spec.maximum_volume,
        volume_step=spec.volume_step,
        margin_per_volume=spec.margin_per_volume,
        commission_per_volume_usd=spec.open_commission_per_lot_usd,
        slippage_reserve_per_volume_usd=slippage_reserve_per_volume_usd,
        observed_at=spec.observed_at,
    )



def fundednext_economic_observation(
    *,
    qore_symbol: str,
    provider_key: str,
    spec: FundedNextCiboSymbolSpecification,
    slippage_reserve_per_volume_usd: Decimal = Decimal(0),
) -> ProviderEconomicObservation:
    """Adapt normalized FundedNext MT5 facts into the common CIBO envelope."""

    if not isinstance(spec, FundedNextCiboSymbolSpecification):
        raise CiboCapitalManagementError(
            "spec must be FundedNextCiboSymbolSpecification"
        )
    return ProviderEconomicObservation(
        provider_key=provider_key,
        qore_symbol=qore_symbol,
        provider_symbol=spec.provider_symbol,
        bid=spec.bid,
        ask=spec.ask,
        contract_size=spec.contract_size,
        tick_size=spec.tick_size,
        tick_value=spec.tick_value,
        minimum_volume=spec.minimum_volume,
        maximum_volume=spec.maximum_volume,
        volume_step=spec.volume_step,
        margin_per_volume=spec.margin_per_volume,
        commission_per_volume_usd=spec.open_commission_per_lot_usd,
        slippage_reserve_per_volume_usd=slippage_reserve_per_volume_usd,
        observed_at=spec.observed_at,
    )
