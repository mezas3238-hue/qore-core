"""Shared live opportunity-geometry primitive for CIBO CMA migration.

This primitive performs no sizing. It normalizes already-valid Trader geometry
and provider economics into a TraderOpportunityEnvelope.
"""

from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
    TraderOpportunityEnvelope,
)


def build_live_opportunity(
    *,
    trader_id: TraderLineage,
    signal_fingerprint: str,
    qore_symbol: str,
    provider_symbol: str,
    side: str,
    entry_type: str,
    certified_entry: Decimal,
    execution_entry: Decimal,
    stop_loss: Decimal,
    take_profit: Decimal,
    tick_size: Decimal,
    tick_value: Decimal,
    margin_per_volume: Decimal,
    volume_step: Decimal,
    minimum_volume: Decimal,
    maximum_volume: Decimal,
    broker_risk_buffer: Decimal,
    commission_per_volume_usd: Decimal,
    maximum_adverse_entry_drift_r: Decimal | None,
    minimum_execution_steps: int = 1,
) -> TraderOpportunityEnvelope:
    """Normalize Trader geometry/provider economics without selecting volume."""

    for name, value in (
        ("certified_entry", certified_entry),
        ("execution_entry", execution_entry),
        ("stop_loss", stop_loss),
        ("take_profit", take_profit),
        ("tick_size", tick_size),
        ("tick_value", tick_value),
        ("margin_per_volume", margin_per_volume),
        ("volume_step", volume_step),
        ("minimum_volume", minimum_volume),
        ("maximum_volume", maximum_volume),
        ("broker_risk_buffer", broker_risk_buffer),
    ):
        if not isinstance(value, Decimal) or not value.is_finite() or value <= 0:
            raise CiboCapitalManagementError(f"{name} must be finite positive Decimal")
    if (
        not isinstance(commission_per_volume_usd, Decimal)
        or not commission_per_volume_usd.is_finite()
        or commission_per_volume_usd < 0
    ):
        raise CiboCapitalManagementError(
            "commission_per_volume_usd must be finite non-negative Decimal"
        )
    if maximum_volume < minimum_volume:
        raise CiboCapitalManagementError("provider volume range invalid")
    if minimum_volume < volume_step:
        raise CiboCapitalManagementError("provider minimum cannot be below volume step")

    certified_risk = abs(certified_entry - stop_loss)
    if certified_risk <= 0:
        raise CiboCapitalManagementError("certified risk must be positive")

    if maximum_adverse_entry_drift_r is not None:
        if (
            not isinstance(maximum_adverse_entry_drift_r, Decimal)
            or not maximum_adverse_entry_drift_r.is_finite()
            or maximum_adverse_entry_drift_r < 0
        ):
            raise CiboCapitalManagementError("maximum adverse drift must be non-negative")
        adverse = (
            max(Decimal(0), execution_entry - certified_entry)
            if side == "long"
            else max(Decimal(0), certified_entry - execution_entry)
        )
        if adverse / certified_risk > maximum_adverse_entry_drift_r:
            raise CiboCapitalManagementError(
                "execution entry drift exceeds certified maximum"
            )

    if side == "long":
        if not stop_loss < execution_entry < take_profit:
            raise CiboCapitalManagementError("invalid long execution geometry")
    elif side == "short":
        if not take_profit < execution_entry < stop_loss:
            raise CiboCapitalManagementError("invalid short execution geometry")
    else:
        raise CiboCapitalManagementError("side must be long/short")

    ticks = abs(execution_entry - stop_loss) / tick_size
    stop_loss_per_volume = (
        ticks * tick_value + commission_per_volume_usd
    ) * broker_risk_buffer
    if stop_loss_per_volume <= 0:
        raise CiboCapitalManagementError("stop economics must be positive")

    return TraderOpportunityEnvelope(
        trader_id=trader_id,
        signal_fingerprint=signal_fingerprint,
        qore_symbol=qore_symbol,
        provider_symbol=provider_symbol,
        side=side,
        entry_type=entry_type,
        intended_entry=execution_entry,
        stop_loss=stop_loss,
        take_profit=take_profit,
        stop_loss_per_volume=stop_loss_per_volume,
        margin_per_volume=margin_per_volume,
        volume_step=volume_step,
        minimum_volume=minimum_volume,
        maximum_volume=maximum_volume,
        minimum_execution_steps=minimum_execution_steps,
    )
