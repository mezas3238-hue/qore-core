from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from qore.infrastructure.market_data import (
    Instrument,
    MarketDataSnapshotId,
    OhlcSnapshot,
    Timeframe,
)
from qore.infrastructure.ports import (
    AdapterId,
    ExternalSourceDescriptor,
    PortName,
    SourceId,
)
from qore.infrastructure.traders.vt31_nas100_market_context_runtime import (
    build_higher_context,
)

_SOURCE = ExternalSourceDescriptor(
    adapter_id=AdapterId(UUID("77400000-0000-0000-0000-000000000001")),
    source_id=SourceId(UUID("77400000-0000-0000-0000-000000000002")),
    port_name=PortName("market-data.vt31-context-runtime-test"),
)


def _bar(
    suffix: int,
    opened_at: datetime,
    *,
    open_price: float = 105.0,
    high: float = 106.0,
    low: float = 104.0,
    close: float = 105.0,
) -> OhlcSnapshot:
    return OhlcSnapshot(
        snapshot_id=MarketDataSnapshotId(
            UUID(f"77400000-0000-0000-0000-{suffix:012d}")
        ),
        instrument=Instrument("NAS100"),
        source=_SOURCE,
        timeframe=Timeframe(60),
        opened_at=opened_at,
        closed_at=opened_at + timedelta(minutes=1),
        open=open_price,
        high=high,
        low=low,
        close=close,
    )


def test_future_bar_cannot_change_causal_higher_context() -> None:
    start = datetime(2026, 1, 5, 13, 0, tzinfo=UTC)  # 08:00 NY
    current: list[OhlcSnapshot] = []
    for minute in range(135):
        opened = start + timedelta(minutes=minute)
        kwargs: dict[str, float] = {}
        if minute == 125:
            kwargs = {"high": 112.0, "close": 109.0}
        current.append(_bar(minute + 1, opened, **kwargs))

    decision_at = current[-1].closed_at
    future = _bar(
        999,
        decision_at,
        open_price=105.0,
        high=1000.0,
        low=1.0,
        close=500.0,
    )
    prior = (
        _bar(
            1001,
            datetime(2026, 1, 2, 14, 0, tzinfo=UTC),
            open_price=100.0,
            high=111.0,
            low=99.0,
            close=110.0,
        ),
    )

    before = build_higher_context(
        day_bars=tuple(current),
        prior_admitted_day_bars=prior,
        decision_at=decision_at,
        side="short",
        reference_high=Decimal("110"),
        reference_low=Decimal("100"),
    )
    after = build_higher_context(
        day_bars=tuple([*current, future]),
        prior_admitted_day_bars=prior,
        decision_at=decision_at,
        side="short",
        reference_high=Decimal("110"),
        reference_low=Decimal("100"),
    )

    assert before == after
    assert before.raid_depth_ref is not None
    assert before.raid_depth_ref > 0
    assert before.h1_state != "unavailable"
