from datetime import UTC, datetime
from decimal import Decimal

from qore.infrastructure.trader_lab.capitalizer_v54_causal_m1_stop_ladder_rescue import (
    _choose_rescue,
)


def test_stop_ladder_uses_newest_eligible_deeper_pivot() -> None:
    at = datetime(2026, 1, 5, 12, 0, tzinfo=UTC)
    pivots = (
        (at, Decimal("95")),
        (at.replace(minute=1), Decimal("97")),
        (at.replace(minute=2), Decimal("99.5")),
    )
    rescue = _choose_rescue(
        pivots,
        entry_price=Decimal("100"),
        thesis_stop_price=Decimal("94"),
        recent_range_ticks=Decimal("10"),
        tick=Decimal("0.01"),
        target_prices=(Decimal("104"), Decimal("106")),
    )
    assert rescue is not None
    _, stop, noise, target, reward_r = rescue
    assert stop == Decimal("99.5")
    assert noise == Decimal("5")
    assert target == Decimal("104")
    assert reward_r == Decimal("8")


def test_stop_ladder_never_uses_thesis_scale_or_wider_pivot() -> None:
    at = datetime(2026, 1, 5, 12, 0, tzinfo=UTC)
    rescue = _choose_rescue(
        ((at, Decimal("93")),),
        entry_price=Decimal("100"),
        thesis_stop_price=Decimal("94"),
        recent_range_ticks=Decimal("10"),
        tick=Decimal("0.01"),
        target_prices=(Decimal("110"),),
    )
    assert rescue is None
