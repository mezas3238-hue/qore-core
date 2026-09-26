from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.trader_lab import (
    capitalizer_cross_market_factor_pressure_v3 as lab,
)


def test_symbol_factor_map_covers_all_nine_markets() -> None:
    assert set(lab.SYMBOL_FACTORS) == {
        "USDJPY", "AUDJPY", "AUDUSD", "GBPJPY", "EURUSD",
        "GBPUSD", "XAUUSD", "USDCAD", "NAS100",
    }


def test_factor_gated_localizes_pressure() -> None:
    assert lab._multiplier(
        policy="FACTOR_GATED",
        current_dd=Decimal("5.2"),
        pressure_votes=2,
        symbol_adverse=True,
    ) == Decimal("0.20")
    assert lab._multiplier(
        policy="FACTOR_GATED",
        current_dd=Decimal("4.2"),
        pressure_votes=0,
        symbol_adverse=False,
    ) == Decimal("1")


def test_symbol_consensus_requires_local_symbol_deterioration() -> None:
    assert lab._multiplier(
        policy="FACTOR_SYMBOL_CONSENSUS",
        current_dd=Decimal("5.2"),
        pressure_votes=2,
        symbol_adverse=False,
    ) == Decimal("1")
    assert lab._multiplier(
        policy="FACTOR_SYMBOL_CONSENSUS",
        current_dd=Decimal("5.2"),
        pressure_votes=2,
        symbol_adverse=True,
    ) == Decimal("0.15")
