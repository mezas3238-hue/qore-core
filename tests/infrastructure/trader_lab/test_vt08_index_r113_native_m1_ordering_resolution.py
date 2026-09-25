from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab import (
    vt08_index_r113_native_m1_ordering_resolution as r113,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt08_index_c2_positional_r1 import (
    Vt08IndexC2R1Bar,
)


def _bar(
    opened: datetime,
    *,
    open_: str,
    high: str,
    low: str,
    close: str,
) -> Vt08IndexC2R1Bar:
    return Vt08IndexC2R1Bar(
        opened_at=opened,
        closed_at=opened + timedelta(minutes=1),
        open=Decimal(open_),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
    )


def test_r113_resolves_target_before_later_stop() -> None:
    t0 = datetime(2026, 1, 1, tzinfo=UTC)
    bars = tuple(
        _bar(
            t0 + timedelta(minutes=i),
            open_="100",
            high=("105.5" if i == 3 else "101"),
            low=("97.5" if i == 8 else "99"),
            close="100",
        )
        for i in range(15)
    )
    result = r113._resolve_order(
        side=DemoTradingSetupSide.LONG,
        stop=Decimal("98"),
        target=Decimal("105"),
        bars=bars,
    )
    assert result["resolution"] == "TARGET_FIRST"
    assert result["minute_index"] == 3


def test_r113_resolves_stop_before_later_target() -> None:
    t0 = datetime(2026, 1, 1, tzinfo=UTC)
    bars = tuple(
        _bar(
            t0 + timedelta(minutes=i),
            open_="100",
            high=("105.5" if i == 8 else "101"),
            low=("97.5" if i == 3 else "99"),
            close="100",
        )
        for i in range(15)
    )
    result = r113._resolve_order(
        side=DemoTradingSetupSide.LONG,
        stop=Decimal("98"),
        target=Decimal("105"),
        bars=bars,
    )
    assert result["resolution"] == "STOP_FIRST"
    assert result["minute_index"] == 3


def test_r113_same_m1_both_levels_remains_ambiguous() -> None:
    t0 = datetime(2026, 1, 1, tzinfo=UTC)
    bars = tuple(
        _bar(
            t0 + timedelta(minutes=i),
            open_="100",
            high=("106" if i == 4 else "101"),
            low=("97" if i == 4 else "99"),
            close="100",
        )
        for i in range(15)
    )
    result = r113._resolve_order(
        side=DemoTradingSetupSide.LONG,
        stop=Decimal("98"),
        target=Decimal("105"),
        bars=bars,
    )
    assert result["resolution"] == "M1_STILL_AMBIGUOUS"
    assert result["minute_index"] == 4


def test_r113_aggregate_requires_contiguous_15_m1() -> None:
    t0 = datetime(2026, 1, 1, tzinfo=UTC)
    bars = tuple(
        _bar(
            t0 + timedelta(minutes=i),
            open_="100",
            high=str(101 + i),
            low=str(99 - i),
            close="100",
        )
        for i in range(15)
    )
    aggregate = r113._aggregate_m1(bars)
    assert aggregate.opened_at == t0
    assert aggregate.closed_at == t0 + timedelta(minutes=15)
    assert aggregate.open == Decimal("100")
    assert aggregate.high == Decimal("115")
    assert aggregate.low == Decimal("85")
    assert aggregate.close == Decimal("100")


def test_r113_source_r112_is_pinned() -> None:
    assert r113.SOURCE_R112_RUN_ID == 35661839898
    assert r113.SOURCE_R112_ARTIFACT_ID == 10667714516
    assert r113.SOURCE_R112_ARTIFACT_DIGEST == (
        "sha256:e0b2dfd0363c2920ba7566672ffef05264d69fbfb4778e81de8568dba05f0e53"
    )
