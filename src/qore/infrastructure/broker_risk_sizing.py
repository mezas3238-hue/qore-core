"""Broker-volume sizing that preserves the sovereign monetary-risk ceiling."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_FLOOR, Decimal


@dataclass(frozen=True, slots=True)
class BrokerRiskSizing:
    requested_risk_usd: Decimal
    stop_loss_per_volume: Decimal
    raw_volume: Decimal
    floored_volume: Decimal
    minimum_volume: Decimal
    maximum_volume: Decimal
    volume_step: Decimal
    risk_at_minimum_volume_usd: Decimal
    authorized_volume: Decimal
    minimum_volume_uplifted: bool


class BrokerMinimumVolumeRiskRejectError(ValueError):
    """A valid candidate whose broker minimum would exceed authorized risk."""

    def __init__(self, sizing: BrokerRiskSizing) -> None:
        self.sizing = sizing
        super().__init__(
            "risk maps below broker minimum volume; minimum volume exceeds authorized risk"
        )

    def telemetry(self) -> dict[str, str]:
        sizing = self.sizing
        excess = sizing.risk_at_minimum_volume_usd - sizing.requested_risk_usd
        fraction = excess / sizing.requested_risk_usd
        return {
            "risk_decision": "RISK_REJECT_MINIMUM_BROKER_VOLUME",
            "requested_risk_usd": str(sizing.requested_risk_usd),
            "stop_loss_per_volume": str(sizing.stop_loss_per_volume),
            "raw_volume": str(sizing.raw_volume),
            "floored_volume": str(sizing.floored_volume),
            "broker_min_volume": str(sizing.minimum_volume),
            "broker_max_volume": str(sizing.maximum_volume),
            "volume_step": str(sizing.volume_step),
            "risk_at_broker_min_volume": str(sizing.risk_at_minimum_volume_usd),
            "risk_excess_usd": str(excess),
            "risk_excess_fraction": str(fraction),
        }


def size_volume_for_risk(
    *,
    requested_risk_usd: Decimal,
    stop_loss_per_volume: Decimal,
    volume_step: Decimal,
    minimum_volume: Decimal,
    maximum_volume: Decimal,
    allow_minimum_volume_uplift: bool = True,
) -> BrokerRiskSizing:
    for name, value in (
        ("requested_risk_usd", requested_risk_usd),
        ("stop_loss_per_volume", stop_loss_per_volume),
        ("volume_step", volume_step),
        ("minimum_volume", minimum_volume),
        ("maximum_volume", maximum_volume),
    ):
        if not isinstance(value, Decimal) or not value.is_finite() or value <= 0:
            raise ValueError(f"{name} must be positive finite Decimal")
    if maximum_volume < minimum_volume:
        raise ValueError("maximum volume cannot be below minimum volume")

    raw_volume = requested_risk_usd / stop_loss_per_volume
    units = (raw_volume / volume_step).to_integral_value(rounding=ROUND_FLOOR)
    floored_volume = units * volume_step
    risk_at_minimum = minimum_volume * stop_loss_per_volume
    minimum_volume_uplifted = floored_volume < minimum_volume
    if minimum_volume_uplifted and (
        allow_minimum_volume_uplift or requested_risk_usd >= risk_at_minimum
    ):
        # The shared QORE Risk engine remains sovereign over the actual minimum-lot
        # monetary risk and aggregate account headroom.
        floored_volume = minimum_volume
    authorized_volume = min(floored_volume, maximum_volume)
    sizing = BrokerRiskSizing(
        requested_risk_usd=requested_risk_usd,
        stop_loss_per_volume=stop_loss_per_volume,
        raw_volume=raw_volume,
        floored_volume=floored_volume,
        minimum_volume=minimum_volume,
        maximum_volume=maximum_volume,
        volume_step=volume_step,
        risk_at_minimum_volume_usd=risk_at_minimum,
        authorized_volume=authorized_volume,
        minimum_volume_uplifted=minimum_volume_uplifted,
    )
    if authorized_volume < minimum_volume:
        raise BrokerMinimumVolumeRiskRejectError(sizing)
    return sizing
