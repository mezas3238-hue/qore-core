from datetime import UTC, datetime, timedelta
from decimal import Decimal

from scripts.cibo_arch2_t16_fresh_oos_m1 import _aligned_returns
from qore.infrastructure.cibo_arch2_t16_fresh_oos_utility import (
    FROZEN_AT,
)


def _rows(
    *,
    start: datetime,
    prices: tuple[str, ...],
) -> tuple[tuple[datetime, Decimal], ...]:
    return tuple(
        (start + timedelta(minutes=index), Decimal(price))
        for index, price in enumerate(prices)
    )


def test_aligned_returns_preserve_only_contiguous_shared_minutes() -> None:
    start = FROZEN_AT + timedelta(minutes=1)
    target = _rows(start=start, prices=("100", "101", "102", "103"))
    hedge = _rows(start=start, prices=("200", "202", "204", "206"))

    observations = _aligned_returns(target, hedge)

    assert len(observations) == 3
    assert all(item.market_at > FROZEN_AT for item in observations)
    assert observations[0].target_return == Decimal("0.01")
    assert observations[0].hedge_return == Decimal("0.01")


def test_aligned_returns_drop_gapped_intervals() -> None:
    start = datetime(2026, 10, 1, 22, 21, tzinfo=UTC)
    target = (
        (start, Decimal("100")),
        (start + timedelta(minutes=2), Decimal("102")),
        (start + timedelta(minutes=3), Decimal("103")),
    )
    hedge = (
        (start, Decimal("200")),
        (start + timedelta(minutes=2), Decimal("204")),
        (start + timedelta(minutes=3), Decimal("206")),
    )

    observations = _aligned_returns(target, hedge)

    assert len(observations) == 1
    assert observations[0].market_at == start + timedelta(minutes=3)
