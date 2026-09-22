from datetime import UTC, datetime, timedelta

from qore.infrastructure.trader_lab.vt08_crt_pure_2y_replay import (
    AggregatedCandle,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2_model1_reference_lab import (
    BreachGroup,
    M15Bar,
    OldLevel,
    ParentCrt,
    ReferenceKind,
    ReferencePolicy,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2a_model1_replay import (
    first_eligible_model1_trade,
)
from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket
from qore.infrastructure.traders.crt_pure_methodology_candidate import (
    CrtPureCandidateDirection,
)


def _m15(minute: int, opened: int, high: int, low: int, closed: int) -> M15Bar:
    return M15Bar(
        opened_at=datetime(2026, 1, 2, 10, minute, tzinfo=UTC),
        open_price=opened,
        high_price=high,
        low_price=low,
        close_price=closed,
    )


def _agg(opened_at: datetime, high: int, low: int, close: int) -> AggregatedCandle:
    return AggregatedCandle(
        opened_at=opened_at,
        closed_at=opened_at + timedelta(hours=4),
        open_price=100,
        high_price=high,
        low_price=low,
        close_price=close,
        m5_count=48,
    )


def _parent() -> ParentCrt:
    opened = datetime(2026, 1, 2, 10, 0, tzinfo=UTC)
    return ParentCrt(
        market=CrtPureMarket.AUDUSD,
        direction=CrtPureCandidateDirection.BEARISH,
        triplet="1",
        c3_opened_at=opened,
        c3_closed_at=opened + timedelta(hours=4),
        c1=_agg(opened - timedelta(hours=8), 120, 80, 100),
        c2=_agg(opened - timedelta(hours=4), 125, 90, 110),
        c3_m5=(),
    )


def _group(source: M15Bar, suffix: str) -> BreachGroup:
    ref = OldLevel(
        kind=ReferenceKind.OLD_HIGH,
        price=source.high_price - 1,
        pivot_opened_at=source.opened_at - timedelta(hours=1),
        confirmed_at=source.opened_at - timedelta(minutes=15),
        policy=ReferencePolicy.UNTOUCHED_SWING_STRENGTH_1,
    )
    return BreachGroup(
        source_candle=source,
        kind=ReferenceKind.OLD_HIGH,
        policy=ReferencePolicy.UNTOUCHED_SWING_STRENGTH_1,
        references=(ref,),
    )


def test_first_source_without_confirmation_blocks_later_fallback() -> None:
    first = _m15(0, 108, 116, 107, 115)
    second = _m15(15, 114, 117, 109, 113)
    later_source = _m15(30, 111, 118, 110, 117)
    later_confirm = _m15(45, 116, 116, 104, 109)
    next_bar = M15Bar(
        opened_at=datetime(2026, 1, 2, 11, 0, tzinfo=UTC),
        open_price=109,
        high_price=110,
        low_price=95,
        close_price=100,
    )
    bars = (first, second, later_source, later_confirm, next_bar)
    by_time = {item.opened_at: item for item in bars}
    breaches = {
        first.opened_at: (_group(first, "first"),),
        later_source.opened_at: (_group(later_source, "later"),),
    }
    trade, reason = first_eligible_model1_trade(
        parent=_parent(),
        m15_by_time=by_time,
        breaches=breaches,
    )
    assert trade is None
    assert reason == "FIRST_MODEL1_SOURCE_NOT_CONFIRMED"


def test_first_confirmed_source_creates_at_most_one_trade() -> None:
    source = _m15(0, 110, 116, 108, 115)
    confirm = _m15(15, 114, 114, 100, 109)
    entry = _m15(30, 109, 110, 90, 95)
    later = _m15(45, 100, 120, 90, 118)
    bars = (source, confirm, entry, later)
    by_time = {item.opened_at: item for item in bars}
    breaches = {
        source.opened_at: (_group(source, "first"),),
        later.opened_at: (_group(later, "later"),),
    }
    trade, reason = first_eligible_model1_trade(
        parent=_parent(),
        m15_by_time=by_time,
        breaches=breaches,
    )
    assert trade is not None
    assert reason == "TRADE_CREATED"
    assert trade.source_opened_at == source.opened_at.isoformat()
