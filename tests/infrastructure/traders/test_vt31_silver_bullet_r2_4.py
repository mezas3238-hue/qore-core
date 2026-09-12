from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

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
from qore.infrastructure.traders.vt31_silver_bullet_r2_4 import (
    Vt31R24AbstainReason,
    evaluate_vt31_r2_4_exact,
)

_NY = ZoneInfo("America/New_York")
_SOURCE = ExternalSourceDescriptor(
    adapter_id=AdapterId(UUID("74200000-0000-0000-0000-000000000001")),
    source_id=SourceId(UUID("74200000-0000-0000-0000-000000000002")),
    port_name=PortName("market-data.vt31-r2-4-source-test"),
)


def _bar(
    *,
    suffix: int,
    opened_at: datetime,
    open_price: float,
    high: float,
    low_price: float,
    close: float,
) -> OhlcSnapshot:
    return OhlcSnapshot(
        snapshot_id=MarketDataSnapshotId(
            UUID(f"74200000-0000-0000-0000-{suffix:012d}")
        ),
        instrument=Instrument("NAS100"),
        source=_SOURCE,
        timeframe=Timeframe(60),
        opened_at=opened_at.astimezone(UTC),
        closed_at=(opened_at + timedelta(minutes=1)).astimezone(UTC),
        open=open_price,
        high=high,
        low=low_price,
        close=close,
    )


def _reference(day: datetime) -> tuple[OhlcSnapshot, ...]:
    start = day.replace(hour=9, minute=0, second=0, microsecond=0)
    bars: list[OhlcSnapshot] = []
    for minute in range(60):
        bars.append(
            _bar(
                suffix=minute + 1,
                opened_at=start + timedelta(minutes=minute),
                open_price=105.0,
                high=110.0 if minute == 10 else 109.0,
                low_price=100.0 if minute == 20 else 101.0,
                close=105.0,
            )
        )
    return tuple(bars)


def _short_exact_session(day: datetime) -> tuple[OhlcSnapshot, ...]:
    start = day.replace(hour=10, minute=0, second=0, microsecond=0)
    return (
        _bar(
            suffix=101,
            opened_at=start,
            open_price=109.8,
            high=111.0,
            low_price=109.8,
            close=110.8,
        ),
        _bar(
            suffix=102,
            opened_at=start + timedelta(minutes=1),
            open_price=110.8,
            high=110.9,
            low_price=109.2,
            close=109.5,
        ),
        _bar(
            suffix=103,
            opened_at=start + timedelta(minutes=2),
            open_price=109.5,
            high=109.6,
            low_price=108.8,
            close=109.0,
        ),
    )


def _evidence(day: datetime, *, midnight_open: float) -> tuple[OhlcSnapshot, ...]:
    midnight = _bar(
        suffix=900,
        opened_at=day.replace(hour=0, minute=0, second=0, microsecond=0),
        open_price=midnight_open,
        high=midnight_open + 0.2,
        low_price=midnight_open - 0.2,
        close=midnight_open,
    )
    return (midnight, *_reference(day), *_short_exact_session(day))


def test_r2_4_accepts_only_exact_midnight_ce_source_demonstrated_short_subset() -> None:
    day = datetime(2026, 6, 16, 0, 0, tzinfo=_NY)
    bars = _evidence(day, midnight_open=109.7)
    result = evaluate_vt31_r2_4_exact(
        instrument=Instrument("NAS100"),
        as_of=bars[-1].closed_at,
        m1_candles=bars,
        evidence_fingerprint="a" * 64,
    )

    assert result.abstain_reason is None
    assert result.setup is not None
    assert result.setup.entry_price.as_tuple() == result.setup.confluence.midnight_open.as_tuple()
    assert str(result.setup.entry_price) == "109.7"
    assert str(result.setup.stop_price) == "111.0"
    assert str(result.setup.target_price) == "100.0"
    assert result.setup.broker_order_type_resolved is False
    assert result.setup.live_stop_offset_resolved is False


def test_r2_4_does_not_invent_tolerance_around_midnight_ce_confluence() -> None:
    day = datetime(2026, 6, 16, 0, 0, tzinfo=_NY)
    bars = _evidence(day, midnight_open=109.71)
    result = evaluate_vt31_r2_4_exact(
        instrument=Instrument("NAS100"),
        as_of=bars[-1].closed_at,
        m1_candles=bars,
        evidence_fingerprint="b" * 64,
    )

    assert result.setup is None
    assert result.abstain_reason is Vt31R24AbstainReason.NO_EXACT_FVG_MIDNIGHT_CONFLUENCE


def test_r2_4_requires_midnight_open_evidence() -> None:
    day = datetime(2026, 6, 16, 0, 0, tzinfo=_NY)
    bars = (*_reference(day), *_short_exact_session(day))
    result = evaluate_vt31_r2_4_exact(
        instrument=Instrument("NAS100"),
        as_of=bars[-1].closed_at,
        m1_candles=bars,
        evidence_fingerprint="c" * 64,
    )

    assert result.setup is None
    assert result.abstain_reason is Vt31R24AbstainReason.MIDNIGHT_OPEN_MISSING
