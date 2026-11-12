"""Deterministic cTrader ProtoOATrendbar relative-price conversion.

Source: https://help.ctrader.com/open-api/symbol-data/ (trendbar price scale).
Native source OHLC integer = real price * 100000. Decimal conversion requires
the actual symbol Digits metadata and tick size, NOT guessed from a ticker.
This does not produce bid/ask bars, verify provider identity, or certify trades.
NO BROKER CONNECTION, NO LIVE/DEMO ORDERS.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, Decimal
from typing import Any

SCALE = Decimal("100000")
D0 = Decimal("0")
PRICE_KEYS = frozenset((
    "c1_high", "c1_low", "sweep_high", "sweep_low",
    "terminal_high", "terminal_low", "terminal_close",
    "retest_high", "retest_low", "retest_close",
))


@dataclass(frozen=True)
class VerifiedUnitMetadata:
    """Explicit provider metadata; independent provider certification is external."""

    symbol: str
    provider_cohort: str
    provider_symbol_id: int
    digits: int
    tick_size: Decimal
    metadata_source_sha256: str

    def __post_init__(self) -> None:
        if (
            not isinstance(self.symbol, str) or not self.symbol
            or self.provider_cohort not in (
                "ICMARKETS_DEMO_CONFIRMED",
                "ATLAS_DEMO_BROKER_UNVERIFIED",
                "SYNTHETIC_TEST_ONLY",
            )
            or type(self.provider_symbol_id) is not int
            or self.provider_symbol_id <= 0
            or type(self.digits) is not int or not 0 <= self.digits <= 10
            or not isinstance(self.tick_size, Decimal)
            or not self.tick_size.is_finite() or self.tick_size <= 0
            or not isinstance(self.metadata_source_sha256, str)
            or len(self.metadata_source_sha256) != 64
            or any(x not in "0123456789abcdef"
                   for x in self.metadata_source_sha256)
        ):
            raise ValueError("incomplete provider symbol digits/tick provenance")
        unit = Decimal(1).scaleb(-self.digits)
        steps = self.tick_size / unit
        if steps != steps.to_integral_value():
            raise ValueError("tick size finer than declared symbol Digits")


def native_to_quote(native: str, *, metadata: VerifiedUnitMetadata) -> Decimal:
    """Convert integer source units to digit-rounded decimal trade quotation.

    Never infer Digits from the market name or use binary float division.
    Price outside the explicit tick grid is rejected (not silently rounded
    to a favorable entry), after the symbol-Digits normalization.
    """
    if not isinstance(native, str):
        raise ValueError("native source price must be Decimal string")
    try:
        n = Decimal(native)
    except (ValueError, ArithmeticError) as exc:
        raise ValueError("native source price is not Decimal") from exc
    if (
        not n.is_finite() or n <= 0
        or n != n.to_integral_value()
    ):
        raise ValueError("native source OHLC must be positive integer units")
    unit = Decimal(1).scaleb(-metadata.digits)
    price = (n / SCALE).quantize(unit, rounding=ROUND_HALF_EVEN)
    if price <= D0:
        raise ValueError("price rounds to zero after provider Digits")
    steps = price / metadata.tick_size
    if steps != steps.to_integral_value():
        raise ValueError("native quote not aligned to broker tick metadata")
    return price


def convert_structural_geometry(
    source_event: dict[str, Any], *, metadata: VerifiedUnitMetadata
) -> dict[str, Any]:
    """Non-destructive derived source-geometry conversion, never a trade order."""
    if (
        source_event.get("symbol") != metadata.symbol
        or source_event.get("provider_cohort") != metadata.provider_cohort
        or source_event.get("economic_ready") is not False
        or source_event.get("broker_orders_executed") != 0
    ):
        raise ValueError("structural event/source metadata identity mismatch")
    geometry = source_event.get("geometry")
    if not isinstance(geometry, dict) or not geometry:
        raise ValueError("event lacks own raw relative-price geometry")
    derived: dict[str, str] = {}
    for name, value in geometry.items():
        if name in PRICE_KEYS:
            derived[name] = str(native_to_quote(value, metadata=metadata))
        elif name != "retest_closed_at":
            raise ValueError("unknown source-owned geometry field")
    return {
        "source_event_id": source_event["source_event_id"],
        "symbol": metadata.symbol,
        "provider_cohort": metadata.provider_cohort,
        "raw_native_price_geometry": dict(geometry),
        "converted_quote_geometry": derived,
        "scale": str(SCALE),
        "symbol_digits": metadata.digits,
        "tick_size": str(metadata.tick_size),
        "provider_symbol_id": metadata.provider_symbol_id,
        "metadata_sha256": metadata.metadata_source_sha256,
        "broker_quote_source_matched": False,
        "bid_ask_historical_evidence": False,
        "contract_currency_conversion_certified": False,
        "pine_f_engine_parity_certified": False,
        "economic_ready": False,
        "broker_orders_executed": 0,
    }
