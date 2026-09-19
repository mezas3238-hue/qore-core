from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

import pytest

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
from qore.infrastructure.traders.contracts import DemoTradingDecision, DemoTradingSetupSide
from qore.infrastructure.traders.vt31_silver_bullet_v2 import (
    Vt31SilverBulletV2AbstainReason,
    Vt31SilverBulletV2Evaluation,
    Vt31SilverBulletV2Input,
    Vt31SilverBulletV2ValidationError,
    evaluate_vt31_silver_bullet_v2,
)

_NY = ZoneInfo("America/New_York")
_SOURCE = ExternalSourceDescriptor(
    adapter_id=AdapterId(UUID("73100000-0000-0000-0000-000000000001")),
    source_id=SourceId(UUID("73100000-0000-0000-0000-000000000002")),
    port_name=PortName("market-data.vt31-v2-fidelity-test"),
)


def _snapshot(
    *,
    suffix: int,
    instrument: str,
    opened_at: datetime,
    open_price: float,
    high: float,
    low: float,
    close: float,
    seconds: int = 60,
) -> OhlcSnapshot:
    return OhlcSnapshot(
        snapshot_id=MarketDataSnapshotId(
            UUID(f"73100000-0000-0000-0000-{suffix:012d}")
        ),
        instrument=Instrument(instrument),
        source=_SOURCE,
        timeframe=Timeframe(seconds),
        opened_at=opened_at.astimezone(UTC),
        closed_at=(opened_at + timedelta(seconds=seconds)).astimezone(UTC),
        open=open_price,
        high=high,
        low=low,
        close=close,
    )


def _reference_hour(*, day: datetime, instrument: str = "NAS100") -> tuple[OhlcSnapshot, ...]:
    start = day.replace(hour=9, minute=0, second=0, microsecond=0)
    bars: list[OhlcSnapshot] = []
    for minute in range(60):
        bars.append(
            _snapshot(
                suffix=minute + 1,
                instrument=instrument,
                opened_at=start + timedelta(minutes=minute),
                open_price=105.0,
                high=109.0 if minute != 10 else 110.0,
                low=101.0 if minute != 20 else 100.0,
                close=105.0,
            )
        )
    return tuple(bars)


def _short_confirmation(*, day: datetime, instrument: str = "NAS100") -> tuple[OhlcSnapshot, ...]:
    start = day.replace(hour=10, minute=0, second=0, microsecond=0)
    return (
        _snapshot(
            suffix=101,
            instrument=instrument,
            opened_at=start,
            open_price=108.0,
            high=112.0,
            low=107.0,
            close=111.0,
        ),
        _snapshot(
            suffix=102,
            instrument=instrument,
            opened_at=start + timedelta(minutes=1),
            open_price=111.0,
            high=113.0,
            low=108.0,
            close=109.0,
        ),
        _snapshot(
            suffix=103,
            instrument=instrument,
            opened_at=start + timedelta(minutes=2),
            open_price=109.0,
            high=109.5,
            low=106.0,
            close=107.0,
        ),
        _snapshot(
            suffix=104,
            instrument=instrument,
            opened_at=start + timedelta(minutes=3),
            open_price=107.0,
            high=107.0,
            low=105.0,
            close=106.0,
        ),
    )


def _long_confirmation(*, day: datetime) -> tuple[OhlcSnapshot, ...]:
    start = day.replace(hour=10, minute=0, second=0, microsecond=0)
    return (
        _snapshot(
            suffix=201,
            instrument="NAS100",
            opened_at=start,
            open_price=102.0,
            high=103.0,
            low=98.0,
            close=99.0,
        ),
        _snapshot(
            suffix=202,
            instrument="NAS100",
            opened_at=start + timedelta(minutes=1),
            open_price=99.0,
            high=102.0,
            low=97.0,
            close=101.0,
        ),
        _snapshot(
            suffix=203,
            instrument="NAS100",
            opened_at=start + timedelta(minutes=2),
            open_price=101.0,
            high=104.0,
            low=100.5,
            close=103.0,
        ),
        _snapshot(
            suffix=204,
            instrument="NAS100",
            opened_at=start + timedelta(minutes=3),
            open_price=103.0,
            high=106.0,
            low=103.0,
            close=105.0,
        ),
    )


def _evaluate(
    day: datetime,
    session: tuple[OhlcSnapshot, ...],
) -> Vt31SilverBulletV2Evaluation:
    evidence = (*_reference_hour(day=day), *session)
    return evaluate_vt31_silver_bullet_v2(
        Vt31SilverBulletV2Input(
            instrument=Instrument("NAS100"),
            as_of=session[-1].closed_at,
            m1_candles=evidence,
        )
    )


def test_source_golden_high_raid_structure_shift_post_confirmation_fvg_is_short() -> None:
    day = datetime(2026, 7, 8, tzinfo=_NY)

    result = _evaluate(day, _short_confirmation(day=day))

    assert result.decision is DemoTradingDecision.SETUP
    assert result.abstain_reason is None
    assert result.setup is not None
    assert result.setup.side is DemoTradingSetupSide.SHORT
    assert result.setup.reference_range.high == 110
    assert result.setup.reference_range.low == 100
    assert result.setup.entry_price == pytest.approx(107.5)
    assert result.setup.invalidation_price == 113
    assert result.setup.take_profit_price == 100
    assert result.setup.raid_at < result.setup.confirmation_at
    assert result.setup.expires_at.astimezone(_NY).hour == 11
    assert result.setup.expires_at.astimezone(_NY).minute == 0


def test_source_golden_low_raid_mirrors_to_long_and_targets_opposite_hour_side() -> None:
    day = datetime(2026, 7, 9, tzinfo=_NY)

    result = _evaluate(day, _long_confirmation(day=day))

    assert result.decision is DemoTradingDecision.SETUP
    assert result.setup is not None
    assert result.setup.side is DemoTradingSetupSide.LONG
    assert result.setup.invalidation_price == 97
    assert result.setup.take_profit_price == 110


def test_equal_high_touch_is_not_a_source_valid_raid() -> None:
    day = datetime(2026, 7, 10, tzinfo=_NY)
    start = day.replace(hour=10, minute=0)
    session = (
        _snapshot(
            suffix=301,
            instrument="NAS100",
            opened_at=start,
            open_price=108.0,
            high=110.0,
            low=106.0,
            close=109.0,
        ),
    )

    result = _evaluate(day, session)

    assert result.decision is DemoTradingDecision.ABSTAIN
    assert result.abstain_reason is Vt31SilverBulletV2AbstainReason.NO_RAID


def test_range_raid_without_post_raid_structure_shift_abstains() -> None:
    day = datetime(2026, 7, 13, tzinfo=_NY)
    start = day.replace(hour=10, minute=0)
    session = (
        _snapshot(
            suffix=401,
            instrument="NAS100",
            opened_at=start,
            open_price=108.0,
            high=112.0,
            low=107.0,
            close=111.0,
        ),
        _snapshot(
            suffix=402,
            instrument="NAS100",
            opened_at=start + timedelta(minutes=1),
            open_price=111.0,
            high=113.0,
            low=108.0,
            close=112.0,
        ),
        _snapshot(
            suffix=403,
            instrument="NAS100",
            opened_at=start + timedelta(minutes=2),
            open_price=112.0,
            high=112.5,
            low=108.5,
            close=109.0,
        ),
    )

    result = _evaluate(day, session)

    assert result.decision is DemoTradingDecision.ABSTAIN
    assert (
        result.abstain_reason
        is Vt31SilverBulletV2AbstainReason.NO_POST_RAID_STRUCTURE_SHIFT
    )


def test_structure_shift_without_post_confirmation_fvg_abstains() -> None:
    day = datetime(2026, 7, 14, tzinfo=_NY)
    start = day.replace(hour=10, minute=0)
    session = (
        _snapshot(
            suffix=501,
            instrument="NAS100",
            opened_at=start,
            open_price=108.0,
            high=112.0,
            low=107.0,
            close=111.0,
        ),
        _snapshot(
            suffix=502,
            instrument="NAS100",
            opened_at=start + timedelta(minutes=1),
            open_price=111.0,
            high=113.0,
            low=108.0,
            close=109.0,
        ),
        _snapshot(
            suffix=503,
            instrument="NAS100",
            opened_at=start + timedelta(minutes=2),
            open_price=109.0,
            high=110.0,
            low=106.0,
            close=107.0,
        ),
        _snapshot(
            suffix=504,
            instrument="NAS100",
            opened_at=start + timedelta(minutes=3),
            open_price=107.0,
            high=108.5,
            low=105.0,
            close=106.0,
        ),
    )

    result = _evaluate(day, session)

    assert result.decision is DemoTradingDecision.ABSTAIN
    assert result.abstain_reason is Vt31SilverBulletV2AbstainReason.NO_POST_CONFIRMATION_FVG


def test_non_nas100_market_is_explicitly_unsupported_not_backtested_as_a_trade() -> None:
    day = datetime(2026, 7, 15, tzinfo=_NY)
    result = evaluate_vt31_silver_bullet_v2(
        Vt31SilverBulletV2Input(
            instrument=Instrument("EURUSD"),
            as_of=day.replace(hour=10, minute=30),
            m1_candles=(),
        )
    )

    assert result.decision is DemoTradingDecision.ABSTAIN
    assert result.abstain_reason is Vt31SilverBulletV2AbstainReason.UNSUPPORTED_METHOD_MARKET


@pytest.mark.parametrize("month", [1, 7])
def test_new_york_wall_clock_window_is_dst_aware(month: int) -> None:
    day = datetime(2026, month, 15, tzinfo=_NY)

    result = _evaluate(day, _short_confirmation(day=day))

    assert result.decision is DemoTradingDecision.SETUP
    assert result.setup is not None
    assert result.setup.expires_at.astimezone(_NY).hour == 11


def test_missing_one_reference_minute_fails_closed() -> None:
    day = datetime(2026, 7, 16, tzinfo=_NY)
    session = _short_confirmation(day=day)
    result = evaluate_vt31_silver_bullet_v2(
        Vt31SilverBulletV2Input(
            instrument=Instrument("NAS100"),
            as_of=session[-1].closed_at,
            m1_candles=(*_reference_hour(day=day)[:-1], *session),
        )
    )

    assert result.decision is DemoTradingDecision.ABSTAIN
    assert result.abstain_reason is Vt31SilverBulletV2AbstainReason.REFERENCE_RANGE_MISSING


def test_outside_10_to_11_new_york_window_abstains_even_with_prior_valid_pattern() -> None:
    day = datetime(2026, 7, 17, tzinfo=_NY)
    session = _short_confirmation(day=day)
    as_of = day.replace(hour=11, minute=0).astimezone(UTC)
    result = evaluate_vt31_silver_bullet_v2(
        Vt31SilverBulletV2Input(
            instrument=Instrument("NAS100"),
            as_of=as_of,
            m1_candles=(*_reference_hour(day=day), *session),
        )
    )

    assert result.decision is DemoTradingDecision.ABSTAIN
    assert result.abstain_reason is Vt31SilverBulletV2AbstainReason.WINDOW_CLOSED


def test_future_or_still_open_m1_evidence_is_rejected() -> None:
    day = datetime(2026, 7, 20, tzinfo=_NY)
    session = _short_confirmation(day=day)
    with pytest.raises(Vt31SilverBulletV2ValidationError, match="future or still-open"):
        Vt31SilverBulletV2Input(
            instrument=Instrument("NAS100"),
            as_of=session[-2].closed_at,
            m1_candles=(*_reference_hour(day=day), *session),
        )


def test_m5_cannot_be_substituted_for_required_m1_execution_evidence() -> None:
    day = datetime(2026, 7, 21, tzinfo=_NY)
    wrong = _snapshot(
        suffix=601,
        instrument="NAS100",
        opened_at=day.replace(hour=10, minute=0),
        open_price=105.0,
        high=110.0,
        low=100.0,
        close=106.0,
        seconds=300,
    )
    with pytest.raises(Vt31SilverBulletV2ValidationError, match="exact M1"):
        Vt31SilverBulletV2Input(
            instrument=Instrument("NAS100"),
            as_of=wrong.closed_at,
            m1_candles=(wrong,),
        )


def test_methodology_and_config_fingerprints_are_deterministic() -> None:
    day = datetime(2026, 7, 22, tzinfo=_NY)
    session = _short_confirmation(day=day)

    first = _evaluate(day, session)
    second = _evaluate(day, session)

    assert first.config_fingerprint == second.config_fingerprint
    assert first.methodology_fingerprint == second.methodology_fingerprint
    assert len(first.methodology_fingerprint) == 64
