"""Broker-normalized remaining-stop economics for CIBO CMA."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


class CmaPositionFloorError(ValueError):
    """Open-position evidence cannot safely produce a stop economic floor."""


@dataclass(frozen=True, slots=True)
class OpenPositionStopEvidence:
    side: str
    entry_price: Decimal
    current_stop: Decimal
    remaining_volume: Decimal
    tick_size: Decimal
    tick_value: Decimal
    broker_position_reconciled: bool
    broker_stop_reconciled: bool

    def __post_init__(self) -> None:
        if self.side not in {"long", "short"}:
            raise CmaPositionFloorError("side must be long/short")
        for name in (
            "entry_price",
            "current_stop",
            "remaining_volume",
            "tick_size",
            "tick_value",
        ):
            value = getattr(self, name)
            if not isinstance(value, Decimal) or not value.is_finite() or value <= 0:
                raise CmaPositionFloorError(
                    f"{name} must be finite positive Decimal"
                )
        for name in ("broker_position_reconciled", "broker_stop_reconciled"):
            if type(getattr(self, name)) is not bool:
                raise CmaPositionFloorError(f"{name} must be bool")


@dataclass(frozen=True, slots=True)
class RemainingStopFloor:
    evidence_sufficient: bool
    remaining_stop_worst_case_pnl_usd: Decimal | None
    stop_distance_ticks: Decimal | None
    reason: str


def evaluate_remaining_stop_floor(
    evidence: OpenPositionStopEvidence,
) -> RemainingStopFloor:
    """Convert broker-confirmed entry/stop/volume into worst-case stop PnL."""

    if not isinstance(evidence, OpenPositionStopEvidence):
        raise CmaPositionFloorError(
            "evidence must be OpenPositionStopEvidence"
        )
    if not evidence.broker_position_reconciled:
        return RemainingStopFloor(
            evidence_sufficient=False,
            remaining_stop_worst_case_pnl_usd=None,
            stop_distance_ticks=None,
            reason="broker position not reconciled",
        )
    if not evidence.broker_stop_reconciled:
        return RemainingStopFloor(
            evidence_sufficient=False,
            remaining_stop_worst_case_pnl_usd=None,
            stop_distance_ticks=None,
            reason="broker stop not reconciled",
        )

    signed_distance = (
        evidence.current_stop - evidence.entry_price
        if evidence.side == "long"
        else evidence.entry_price - evidence.current_stop
    )
    signed_ticks = signed_distance / evidence.tick_size
    stop_pnl = signed_ticks * evidence.tick_value * evidence.remaining_volume
    return RemainingStopFloor(
        evidence_sufficient=True,
        remaining_stop_worst_case_pnl_usd=stop_pnl,
        stop_distance_ticks=signed_ticks,
        reason="broker-confirmed remaining stop economics",
    )
