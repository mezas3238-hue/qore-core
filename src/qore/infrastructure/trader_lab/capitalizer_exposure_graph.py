"""Underlying-factor exposure graph for the QORE Capitalizer."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum


class CapitalizerSide(StrEnum):
    LONG = "LONG"
    SHORT = "SHORT"


_FACTOR_MAP: dict[str, tuple[str, ...]] = {
    "USDJPY": ("USD", "JPY"),
    "AUDJPY": ("AUD", "JPY"),
    "AUDUSD": ("AUD", "USD"),
    "GBPJPY": ("GBP", "JPY"),
    "EURUSD": ("EUR", "USD"),
    "GBPUSD": ("GBP", "USD"),
    "XAUUSD": ("XAU", "USD"),
    "USDCAD": ("USD", "CAD"),
    "NAS100": ("NAS100",),
}


@dataclass(frozen=True, slots=True)
class CapitalizerExposurePosition:
    symbol: str
    side: CapitalizerSide
    risk_r: Decimal

    def __post_init__(self) -> None:
        if self.symbol not in _FACTOR_MAP:
            raise ValueError("unsupported Capitalizer symbol")
        if not isinstance(self.risk_r, Decimal) or not self.risk_r.is_finite():
            raise ValueError("risk_r must be finite")
        if self.risk_r <= 0:
            raise ValueError("risk_r must be positive")


@dataclass(frozen=True, slots=True)
class CapitalizerFactorExposure:
    factor: str
    net_r: Decimal
    gross_r: Decimal


def factor_exposures(
    positions: tuple[CapitalizerExposurePosition, ...],
) -> tuple[CapitalizerFactorExposure, ...]:
    """Aggregate economic legs so correlated tickets are visible to cognition/risk.

    For two-leg FX/metal symbols, LONG is +base/-quote and SHORT is the inverse.
    A single-factor instrument such as NAS100 contributes only to its named factor.
    """

    net: dict[str, Decimal] = {}
    gross: dict[str, Decimal] = {}
    for position in positions:
        factors = _FACTOR_MAP[position.symbol]
        direction = Decimal("1") if position.side is CapitalizerSide.LONG else Decimal("-1")
        if len(factors) == 1:
            legs = ((factors[0], direction * position.risk_r),)
        else:
            legs = (
                (factors[0], direction * position.risk_r),
                (factors[1], -direction * position.risk_r),
            )
        for factor, signed_r in legs:
            net[factor] = net.get(factor, Decimal("0")) + signed_r
            gross[factor] = gross.get(factor, Decimal("0")) + abs(signed_r)
    return tuple(
        CapitalizerFactorExposure(
            factor=factor,
            net_r=net[factor],
            gross_r=gross[factor],
        )
        for factor in sorted(net)
    )
