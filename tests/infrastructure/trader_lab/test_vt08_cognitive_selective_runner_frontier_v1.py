from datetime import UTC, datetime
from decimal import Decimal

from qore.infrastructure.trader_lab.vt08_cognitive_selective_runner_frontier_v1 import (
    DESTINATION_BANK_FRACTION,
    EQ_FRACTION,
    RUNNER_FRACTION,
    _runner_room,
    destination_accepts,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt08_b01_r3_8 import Vt08B01Bar


def _bar(close: str) -> Vt08B01Bar:
    return Vt08B01Bar(
        opened_at=datetime(2026, 9, 23, 12, 0, tzinfo=UTC),
        closed_at=datetime(2026, 9, 23, 12, 15, tzinfo=UTC),
        open=Decimal("100"),
        high=Decimal("103"),
        low=Decimal("97"),
        close=Decimal(close),
    )


def test_runner_fractions_sum_to_one() -> None:
    assert EQ_FRACTION == Decimal("0.50")
    assert DESTINATION_BANK_FRACTION == Decimal("0.25")
    assert RUNNER_FRACTION == Decimal("0.25")
    assert EQ_FRACTION + DESTINATION_BANK_FRACTION + RUNNER_FRACTION == Decimal("1")


def test_destination_acceptance_requires_close_beyond() -> None:
    assert destination_accepts(
        _bar("102"),
        side=DemoTradingSetupSide.LONG,
        destination=Decimal("101"),
    )
    assert not destination_accepts(
        _bar("100"),
        side=DemoTradingSetupSide.LONG,
        destination=Decimal("101"),
    )
    assert destination_accepts(
        _bar("98"),
        side=DemoTradingSetupSide.SHORT,
        destination=Decimal("99"),
    )


def test_runner_requires_original_target_farther_forward() -> None:
    assert _runner_room(
        DemoTradingSetupSide.LONG,
        destination=Decimal("101"),
        target=Decimal("102"),
    )
    assert not _runner_room(
        DemoTradingSetupSide.LONG,
        destination=Decimal("102"),
        target=Decimal("101"),
    )
    assert _runner_room(
        DemoTradingSetupSide.SHORT,
        destination=Decimal("99"),
        target=Decimal("98"),
    )
