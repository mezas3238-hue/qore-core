from decimal import Decimal

from qore.infrastructure.trader_lab.vt08_cognitive_structural_bank_frontier_v1 import (
    DESTINATION_FRACTION,
    EQ_FRACTION,
    _ordered_path,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide


def test_structural_bank_fractions_are_complete() -> None:
    assert EQ_FRACTION == Decimal("0.50")
    assert DESTINATION_FRACTION == Decimal("0.50")
    assert EQ_FRACTION + DESTINATION_FRACTION == Decimal("1.00")


def test_long_path_requires_entry_then_eq_then_destination() -> None:
    assert _ordered_path(
        DemoTradingSetupSide.LONG,
        entry=Decimal("100"),
        equilibrium=Decimal("101"),
        destination=Decimal("102"),
    )
    assert not _ordered_path(
        DemoTradingSetupSide.LONG,
        entry=Decimal("100"),
        equilibrium=Decimal("103"),
        destination=Decimal("102"),
    )


def test_short_path_requires_entry_then_eq_then_destination() -> None:
    assert _ordered_path(
        DemoTradingSetupSide.SHORT,
        entry=Decimal("100"),
        equilibrium=Decimal("99"),
        destination=Decimal("98"),
    )
    assert not _ordered_path(
        DemoTradingSetupSide.SHORT,
        entry=Decimal("100"),
        equilibrium=Decimal("97"),
        destination=Decimal("98"),
    )
