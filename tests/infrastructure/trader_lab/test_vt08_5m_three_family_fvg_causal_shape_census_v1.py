"""Source FVG POI first-priority census: no future/ambiguous POI promotion."""
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab.vt08_5m_three_family_fvg_causal_shape_census_v1 import (
    available_unique_fvg,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt08_b01_r3_8 import Vt08B01Bar

BASE = datetime(2026, 1, 10, 12, tzinfo=UTC)


def b(i: int, o: str, h: str, low: str, c: str) -> Vt08B01Bar:
    x = BASE + timedelta(minutes=15*i)
    return Vt08B01Bar(
        opened_at=x, closed_at=x+timedelta(minutes=15),
        open=Decimal(o), high=Decimal(h), low=Decimal(low), close=Decimal(c),
    )


def test_one_bullish_fvg_reconstructed_from_closed_bars() -> None:
    bars = (
        b(0, "97", "98", "96", "97"),
        b(1, "98", "100", "97", "99"),
        b(2, "100", "101", "99", "100"),
    )
    poi, n = available_unique_fvg(bars, DemoTradingSetupSide.LONG)
    assert n == 1 and poi is not None
    assert poi.formed_at == bars[2].closed_at
    assert poi.fvg_proven_at(bars[2].closed_at)
    assert not poi.fvg_proven_at(bars[2].opened_at)
    assert (poi.lower, poi.upper) == (Decimal("98"), Decimal("99"))


def test_fvg_invalidated_by_later_extreme_is_rejected() -> None:
    bars = (
        b(0, "97", "98", "96", "97"),
        b(1, "98", "100", "97", "99"),
        b(2, "100", "101", "99", "100"),
        b(3, "100", "102", "97", "101"),
    )
    poi, n = available_unique_fvg(bars, DemoTradingSetupSide.LONG)
    assert poi is None and n == 0


def test_more_than_one_active_fvg_never_select_arbitrarily() -> None:
    bars = (
        b(0, "97", "98", "96", "97"),
        b(1, "98", "100", "97", "99"),
        b(2, "100", "101", "99", "100"),
        b(3, "101", "102", "100", "101"),
        b(4, "103", "104", "102", "103"),
    )
    poi, n = available_unique_fvg(bars, DemoTradingSetupSide.LONG)
    assert n >= 2 and poi is None


def test_non_fvg_source_no_proof() -> None:
    bars = (
        b(0, "97", "98", "96", "97"),
        b(1, "98", "100", "97", "99"),
        b(2, "100", "101", "99", "100"),
    )
    poi, count = available_unique_fvg(bars, DemoTradingSetupSide.SHORT)
    assert count == 0 and poi is None
