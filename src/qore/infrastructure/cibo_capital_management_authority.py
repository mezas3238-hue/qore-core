"""CIBO Capital Management Authority research contracts.

CIBO owns capital-management decisions around a Trader opportunity.
The Trader owns market methodology. QORE Risk remains the hard survivability
governor. This module is research-only and performs no broker mutation.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_CEILING, ROUND_FLOOR, Decimal
from enum import StrEnum

from qore.infrastructure.account_wide_risk import TraderLineage


class CiboCapitalManagementError(ValueError):
    """CMA input or transition violates a fail-closed invariant."""


class CapitalStage(StrEnum):
    MINIMAL_SEED = "MINIMAL_SEED"
    OBSERVE = "OBSERVE"
    PROTECT_BASE = "PROTECT_BASE"
    BASE_RECOVERED = "BASE_RECOVERED"
    CAPITALIZE = "CAPITALIZE"
    COMPOUND_OR_RESERVE = "COMPOUND_OR_RESERVE"
    RELEASE = "RELEASE"


class CapitalAction(StrEnum):
    OPEN_MINIMAL_SEED = "OPEN_MINIMAL_SEED"
    HOLD = "HOLD"
    REDUCE = "REDUCE"
    EXPAND = "EXPAND"
    RESERVE = "RESERVE"
    RELEASE = "RELEASE"


class CapitalSource(StrEnum):
    ORIGINAL_BASE_CAPITAL = "ORIGINAL_BASE_CAPITAL"
    REALIZED_PROFIT = "REALIZED_PROFIT"
    PROTECTED_ECONOMIC_FLOOR = "PROTECTED_ECONOMIC_FLOOR"
    RELEASED_RISK_CAPACITY = "RELEASED_RISK_CAPACITY"
    RELEASED_MARGIN_CAPACITY = "RELEASED_MARGIN_CAPACITY"
    TRUE_PORTFOLIO_NETTING = "TRUE_PORTFOLIO_NETTING"
    REDUCED_OTHER_EXPOSURE = "REDUCED_OTHER_EXPOSURE"
    CERTIFIED_LIMITED_DOWNSIDE_CAPACITY = "CERTIFIED_LIMITED_DOWNSIDE_CAPACITY"


@dataclass(frozen=True, slots=True)
class TraderOpportunityEnvelope:
    """Trader-owned opportunity facts with intentionally no sizing field."""

    trader_id: TraderLineage
    signal_fingerprint: str
    qore_symbol: str
    provider_symbol: str
    side: str
    intended_entry: Decimal
    stop_loss: Decimal
    take_profit: Decimal
    stop_loss_per_volume: Decimal
    margin_per_volume: Decimal
    volume_step: Decimal
    minimum_volume: Decimal
    maximum_volume: Decimal
    minimum_execution_steps: int = 1

    def __post_init__(self) -> None:
        if type(self.trader_id) is not TraderLineage:
            raise CiboCapitalManagementError("trader_id must be TraderLineage")
        for name in ("signal_fingerprint", "qore_symbol", "provider_symbol", "side"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise CiboCapitalManagementError(f"{name} must be non-empty")
        for name in (
            "intended_entry",
            "stop_loss",
            "take_profit",
            "stop_loss_per_volume",
            "margin_per_volume",
            "volume_step",
            "minimum_volume",
            "maximum_volume",
        ):
            _positive(getattr(self, name), name)
        if self.minimum_volume < self.volume_step:
            raise CiboCapitalManagementError("minimum_volume cannot be below volume_step")
        if self.maximum_volume < self.minimum_volume:
            raise CiboCapitalManagementError("maximum_volume below minimum_volume")
        if (
            not isinstance(self.minimum_execution_steps, int)
            or isinstance(self.minimum_execution_steps, bool)
            or self.minimum_execution_steps < 1
        ):
            raise CiboCapitalManagementError("minimum_execution_steps must be positive int")
        if self.side == "long":
            if not self.stop_loss < self.intended_entry < self.take_profit:
                raise CiboCapitalManagementError("invalid long geometry")
        elif self.side == "short":
            if not self.take_profit < self.intended_entry < self.stop_loss:
                raise CiboCapitalManagementError("invalid short geometry")
        else:
            raise CiboCapitalManagementError("side must be long/short")


@dataclass(frozen=True, slots=True)
class CapitalSourceLot:
    source: CapitalSource
    amount_usd: Decimal
    source_id: str

    def __post_init__(self) -> None:
        if type(self.source) is not CapitalSource:
            raise CiboCapitalManagementError("source must be CapitalSource")
        _nonnegative(self.amount_usd, "amount_usd")
        if not self.source_id:
            raise CiboCapitalManagementError("source_id is required")


@dataclass(frozen=True, slots=True)
class CiboCapitalState:
    assigned_capital_usd: Decimal
    hard_risk_headroom_usd: Decimal
    margin_headroom_usd: Decimal
    base_capital_at_risk_usd: Decimal
    realized_net_profit_usd: Decimal
    protected_economic_floor_usd: Decimal
    reserved_expansion_risk_usd: Decimal
    cost_reserve_usd: Decimal

    def __post_init__(self) -> None:
        for name in (
            "assigned_capital_usd",
            "hard_risk_headroom_usd",
            "margin_headroom_usd",
        ):
            _positive(getattr(self, name), name)
        for name in (
            "base_capital_at_risk_usd",
            "realized_net_profit_usd",
            "protected_economic_floor_usd",
            "reserved_expansion_risk_usd",
            "cost_reserve_usd",
        ):
            _nonnegative(getattr(self, name), name)

    @property
    def base_recovered(self) -> bool:
        return self.base_capital_at_risk_usd == 0

    @property
    def proven_self_financing_capacity_usd(self) -> Decimal:
        gross = (
            self.realized_net_profit_usd
            + self.protected_economic_floor_usd
            - self.reserved_expansion_risk_usd
            - self.cost_reserve_usd
        )
        return max(Decimal(0), gross)


@dataclass(frozen=True, slots=True)
class CiboCapitalActionPlan:
    trader_id: TraderLineage
    qore_symbol: str
    stage: CapitalStage
    action: CapitalAction
    volume: Decimal
    stop_risk_usd: Decimal
    margin_usd: Decimal
    capital_source: CapitalSource | None
    capital_source_amount_usd: Decimal
    reason: str

    def __post_init__(self) -> None:
        for name in ("volume", "stop_risk_usd", "margin_usd", "capital_source_amount_usd"):
            _nonnegative(getattr(self, name), name)
        if self.action in {CapitalAction.OPEN_MINIMAL_SEED, CapitalAction.EXPAND}:
            if self.volume <= 0:
                raise CiboCapitalManagementError("capital deployment requires positive volume")
            if self.capital_source is None:
                raise CiboCapitalManagementError("capital deployment requires source")
        if self.action is CapitalAction.EXPAND:
            if self.capital_source is CapitalSource.ORIGINAL_BASE_CAPITAL:
                raise CiboCapitalManagementError(
                    "expansion cannot consume original base capital in CMA V1"
                )


def minimum_seed_volume(opportunity: TraderOpportunityEnvelope) -> Decimal:
    """Smallest step-aligned volume compatible with provider/methodology constraints."""

    lifecycle_floor = (
        opportunity.volume_step * Decimal(opportunity.minimum_execution_steps)
    )
    raw = max(opportunity.minimum_volume, lifecycle_floor)
    steps = (raw / opportunity.volume_step).to_integral_value(rounding=ROUND_CEILING)
    return steps * opportunity.volume_step


def plan_minimal_seed(
    opportunity: TraderOpportunityEnvelope,
    capital: CiboCapitalState,
) -> CiboCapitalActionPlan:
    """Ignore legacy Trader sizing and open the smallest viable exposure."""

    volume = minimum_seed_volume(opportunity)
    if volume > opportunity.maximum_volume:
        return _hold(opportunity, CapitalStage.MINIMAL_SEED, "minimum seed exceeds provider maximum")
    risk = volume * opportunity.stop_loss_per_volume
    margin = volume * opportunity.margin_per_volume
    if risk > capital.hard_risk_headroom_usd:
        return _hold(opportunity, CapitalStage.MINIMAL_SEED, "minimum seed exceeds hard risk headroom")
    if margin > capital.margin_headroom_usd:
        return _hold(opportunity, CapitalStage.MINIMAL_SEED, "minimum seed exceeds margin headroom")
    return CiboCapitalActionPlan(
        trader_id=opportunity.trader_id,
        qore_symbol=opportunity.qore_symbol,
        stage=CapitalStage.MINIMAL_SEED,
        action=CapitalAction.OPEN_MINIMAL_SEED,
        volume=volume,
        stop_risk_usd=risk,
        margin_usd=margin,
        capital_source=CapitalSource.ORIGINAL_BASE_CAPITAL,
        capital_source_amount_usd=risk,
        reason="minimum viable executable seed selected by CIBO",
    )


def plan_self_financing_expansion(
    opportunity: TraderOpportunityEnvelope,
    capital: CiboCapitalState,
) -> CiboCapitalActionPlan:
    """Expand only from proven economic capacity after base-capital recovery."""

    if not capital.base_recovered:
        return _hold(
            opportunity,
            CapitalStage.PROTECT_BASE,
            "base capital remains at risk; expansion locked",
        )

    capacity = min(
        capital.proven_self_financing_capacity_usd,
        capital.hard_risk_headroom_usd,
    )
    if capacity <= 0:
        return _hold(
            opportunity,
            CapitalStage.BASE_RECOVERED,
            "base recovered but no proven self-financing capacity",
        )

    by_risk = capacity / opportunity.stop_loss_per_volume
    by_margin = capital.margin_headroom_usd / opportunity.margin_per_volume
    raw_volume = min(by_risk, by_margin, opportunity.maximum_volume)
    steps = (raw_volume / opportunity.volume_step).to_integral_value(
        rounding=ROUND_FLOOR
    )
    volume = steps * opportunity.volume_step
    if volume < opportunity.minimum_volume:
        return _hold(
            opportunity,
            CapitalStage.BASE_RECOVERED,
            "self-financing capacity cannot express provider minimum volume",
        )

    risk = volume * opportunity.stop_loss_per_volume
    margin = volume * opportunity.margin_per_volume
    source = (
        CapitalSource.REALIZED_PROFIT
        if capital.realized_net_profit_usd > 0
        else CapitalSource.PROTECTED_ECONOMIC_FLOOR
    )
    return CiboCapitalActionPlan(
        trader_id=opportunity.trader_id,
        qore_symbol=opportunity.qore_symbol,
        stage=CapitalStage.CAPITALIZE,
        action=CapitalAction.EXPAND,
        volume=volume,
        stop_risk_usd=risk,
        margin_usd=margin,
        capital_source=source,
        capital_source_amount_usd=risk,
        reason="expansion funded only from proven non-base economic capacity",
    )


def _hold(
    opportunity: TraderOpportunityEnvelope,
    stage: CapitalStage,
    reason: str,
) -> CiboCapitalActionPlan:
    return CiboCapitalActionPlan(
        trader_id=opportunity.trader_id,
        qore_symbol=opportunity.qore_symbol,
        stage=stage,
        action=CapitalAction.HOLD,
        volume=Decimal(0),
        stop_risk_usd=Decimal(0),
        margin_usd=Decimal(0),
        capital_source=None,
        capital_source_amount_usd=Decimal(0),
        reason=reason,
    )


def _positive(value: Decimal, field: str) -> None:
    if not isinstance(value, Decimal) or not value.is_finite() or value <= 0:
        raise CiboCapitalManagementError(f"{field} must be finite positive Decimal")


def _nonnegative(value: Decimal, field: str) -> None:
    if not isinstance(value, Decimal) or not value.is_finite() or value < 0:
        raise CiboCapitalManagementError(
            f"{field} must be finite non-negative Decimal"
        )
