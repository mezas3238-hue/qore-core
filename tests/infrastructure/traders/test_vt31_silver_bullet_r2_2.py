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
from qore.infrastructure.ports import AdapterId, ExternalSourceDescriptor, PortName, SourceId
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt31_silver_bullet_r2_2 import (
    Vt31R22AbstainReason,
    Vt31R22EntryFamily,
    Vt31R22ExecutionPolicy,
    evaluate_vt31_r2_2_source,
    make_executable_setup,
)

_NY = ZoneInfo("America/New_York")
_SOURCE = ExternalSourceDescriptor(
    adapter_id=AdapterId(UUID("73120000-0000-0000-0000-000000000001")),
    source_id=SourceId(UUID("73120000-0000-0000-0000-000000000002")),
    port_name=PortName("market-data.vt31-r2-2-test"),
)


def _bar(
    suffix: int,
    opened: datetime,
    o: float,
    h: float,
    l: float,
    c: float,
) -> OhlcSnapshot:
    return OhlcSnapshot(
        snapshot_id=MarketDataSnapshotId(
            UUID(f"73120000-0000-0000-0000-{suffix:012d}")
        ),
        instrument=Instrument("NAS100"),
        source=_SOURCE,
        timeframe=Timeframe(60),
        opened_at=opened.astimezone(UTC),
        closed_at=(opened + timedelta(minutes=1)).astimezone(UTC),
        open=o,
        high=h,
        low=l,
        close=c,
    )


def _reference(day: datetime) -> tuple[OhlcSnapshot, ...]:
    start = day.replace(hour=9, minute=0, second=0, microsecond=0)
    return tuple(
        _bar(
            minute + 1,
            start + timedelta(minutes=minute),
            105,
            110 if minute == 10 else 109,
            100 if minute == 20 else 101,
            105,
        )
        for minute in range(60)
    )


def _short_fvg(day: datetime) -> tuple[OhlcSnapshot, ...]:
    start = day.replace(hour=10, minute=0, second=0, microsecond=0)
    return (
        _bar(101, start, 109.5, 111, 108.8, 109),
        _bar(102, start + timedelta(minutes=1), 109, 109.2, 108, 108.5),
        _bar(103, start + timedelta(minutes=2), 108.5, 108.7, 107.8, 108),
    )


def _eval(day: datetime, session: tuple[OhlcSnapshot, ...]):
    bars = (*_reference(day), *session)
    return evaluate_vt31_r2_2_source(
        instrument=Instrument("NAS100"),
        as_of=session[-1].closed_at,
        m1_candles=bars,
        evidence_fingerprint="1" * 64,
    )


def test_strict_high_raid_builds_short_source_setup_with_opposite_range_target() -> None:
    day = datetime(2026, 7, 8, tzinfo=_NY)
    result = _eval(day, _short_fvg(day))
    assert result.setup is not None
    assert result.setup.side is DemoTradingSetupSide.SHORT
    assert result.setup.target_price == 100
    assert any(
        item.family is Vt31R22EntryFamily.FAIR_VALUE_GAP
        for item in result.setup.candidates
    )
    assert all(not hasattr(item, "entry_price") for item in result.setup.candidates)


def test_equal_high_is_not_a_sweep() -> None:
    day = datetime(2026, 7, 9, tzinfo=_NY)
    start = day.replace(hour=10, minute=0)
    result = _eval(day, (_bar(201, start, 109, 110, 108, 109),))
    assert result.setup is None
    assert result.abstain_reason is Vt31R22AbstainReason.NO_RAID


def test_both_reference_sides_swept_fails_closed() -> None:
    day = datetime(2026, 7, 10, tzinfo=_NY)
    start = day.replace(hour=10, minute=0)
    session = (
        _bar(301, start, 109, 111, 108, 109),
        _bar(302, start + timedelta(minutes=1), 101, 102, 99, 101),
    )
    result = _eval(day, session)
    assert result.setup is None
    assert result.both_sides_swept is True
    assert result.abstain_reason is Vt31R22AbstainReason.BOTH_SIDES_SWEPT


def test_execution_price_policy_is_explicitly_not_a_source_rule() -> None:
    policy = Vt31R22ExecutionPolicy()
    assert policy.source_rule is False
    assert policy.breaker_price_policy == "body-midpoint"
    assert policy.fvg_price_policy == "consequent-encroachment"
    assert len(policy.fingerprint()) == 64


def test_source_zone_becomes_executable_only_through_versioned_policy() -> None:
    day = datetime(2026, 7, 13, tzinfo=_NY)
    result = _eval(day, _short_fvg(day))
    assert result.setup is not None
    executable, reason = make_executable_setup(result.setup)
    assert reason is None
    assert executable is not None
    assert executable.target_price == result.setup.reference.low
    assert executable.stop_price == result.setup.structure.swing_extreme
    assert len(executable.execution_policy_fingerprint) == 64
