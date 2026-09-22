from datetime import UTC, datetime, timedelta

from qore.infrastructure.trader_lab.vt08_crt_pure_2y_replay import (
    AggregatedCandle,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2_model1_reference_lab import (
    M15Bar,
    ParentCrt,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2b_old_crt_boundary_replay import (
    CrtBoundaryKind,
    build_prior_crt_boundary_breaches,
    first_prior_crt_boundary_model1_trade,
)
from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket
from qore.infrastructure.traders.crt_pure_methodology_candidate import (
    CrtPureCandidateDirection,
)


def _m15(hour: int, minute: int, o: int, h: int, l: int, c: int) -> M15Bar:
    return M15Bar(
        opened_at=datetime(2026, 1, 2, hour, minute, tzinfo=UTC),
        open_price=o,
        high_price=h,
        low_price=l,
        close_price=c,
    )


def _agg(hour: int, o: int, h: int, l: int, c: int) -> AggregatedCandle:
    opened = datetime(2026, 1, 2, hour, 0, tzinfo=UTC)
    return AggregatedCandle(
        opened_at=opened,
        closed_at=opened + timedelta(hours=4),
        open_price=o,
        high_price=h,
        low_price=l,
        close_price=c,
        m5_count=48,
    )


def _parent(*, c3_hour: int, direction: CrtPureCandidateDirection) -> ParentCrt:
    c3 = datetime(2026, 1, 2, c3_hour, 0, tzinfo=UTC)
    return ParentCrt(
        market=CrtPureMarket.AUDUSD,
        direction=direction,
        triplet="1",
        c3_opened_at=c3,
        c3_closed_at=c3 + timedelta(hours=4),
        c1=_agg(c3_hour - 8, 100, 110, 90, 102),
        c2=_agg(c3_hour - 4, 102, 112, 95, 104),
        c3_m5=(),
    )


def test_prior_crt_boundaries_activate_and_consume_on_first_strict_breach() -> None:
    old_parent = _parent(c3_hour=4, direction=CrtPureCandidateDirection.BEARISH)
    bars = (
        _m15(4, 0, 100, 105, 95, 103),
        _m15(4, 15, 108, 111, 107, 110),
        _m15(4, 30, 110, 115, 109, 114),
    )
    breaches = build_prior_crt_boundary_breaches(
        parents=(old_parent,),
        m15=bars,
    )
    event = breaches[bars[1].opened_at][0]
    assert event.kind is CrtBoundaryKind.OLD_CRTH
    assert len(event.references) == 1
    assert event.references[0].price == 110
    assert bars[2].opened_at not in breaches


def test_current_parent_boundary_is_not_eligible_as_old_reference() -> None:
    current = _parent(c3_hour=8, direction=CrtPureCandidateDirection.BEARISH)
    bars = (
        _m15(8, 0, 105, 112, 103, 110),
        _m15(8, 15, 110, 113, 104, 109),
        _m15(8, 30, 109, 110, 98, 99),
        _m15(8, 45, 99, 101, 97, 100),
    )
    breaches = build_prior_crt_boundary_breaches(parents=(current,), m15=bars)
    trade, reason = first_prior_crt_boundary_model1_trade(
        parent=current,
        m15_by_time={item.opened_at: item for item in bars},
        breaches=breaches,
    )
    assert trade is None
    assert reason == "NO_PRIOR_CRT_BOUNDARY_MODEL1_SOURCE"


def test_prior_crth_model1_can_confirm_bearish_without_later_source_fallback() -> None:
    old_parent = _parent(c3_hour=4, direction=CrtPureCandidateDirection.BEARISH)
    current = _parent(c3_hour=8, direction=CrtPureCandidateDirection.BEARISH)
    bars = (
        _m15(4, 0, 100, 105, 95, 103),
        _m15(8, 0, 108, 112, 107, 111),
        _m15(8, 15, 110, 111, 101, 102),
        _m15(8, 30, 102, 103, 96, 98),
        _m15(8, 45, 98, 100, 95, 97),
    )
    breaches = build_prior_crt_boundary_breaches(
        parents=(old_parent, current),
        m15=bars,
    )
    trade, reason = first_prior_crt_boundary_model1_trade(
        parent=current,
        m15_by_time={item.opened_at: item for item in bars if item.opened_at.hour == 8},
        breaches=breaches,
    )
    assert reason == "TRADE_CREATED"
    assert trade is not None
    assert trade.reference_policy == "UNTOUCHED_PRIOR_PARENT_CRT_BOUNDARY"
    assert trade.reference_count == 1
    assert trade.stop_price_relative == 112
    assert trade.research_only is True
    assert trade.source_canonical is False
