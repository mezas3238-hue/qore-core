from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab.capitalizer_contract import CapitalizerSession
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_full_ict_density_scanner_1y_v1 import (
    AggregatedBar,
    HTFBiasEvent,
)
from qore.infrastructure.trader_lab.capitalizer_source_observation_detectors_v2 import (
    CapitalizerSourceBar,
    CapitalizerSourceDirection,
)
from qore.infrastructure.trader_lab.capitalizer_strict_htf_gate_1y_v1 import (
    Pivot,
    ReferenceLiquidity,
    TFBar,
    _find_structure_event,
    _immediate_h1_bias,
    _sweep_confirmed,
    _window_local,
)


def _source(o: str, h: str, l: str, c: str) -> CapitalizerSourceBar:
    return CapitalizerSourceBar(
        open=Decimal(o),
        high=Decimal(h),
        low=Decimal(l),
        close=Decimal(c),
    )


def test_execution_windows_are_source_declared_broad_windows() -> None:
    day = datetime(2026, 1, 5).date()
    asia_start, asia_end = _window_local(day, session=CapitalizerSession.ASIA)
    london_start, london_end = _window_local(day, session=CapitalizerSession.LONDON)
    ny_start, ny_end = _window_local(day, session=CapitalizerSession.NEW_YORK)

    assert (asia_start.hour, asia_end.hour) == (20, 0)
    assert (london_start.hour, london_end.hour) == (2, 5)
    assert (ny_start.hour, ny_start.minute, ny_end.hour, ny_end.minute) == (
        8,
        30,
        11,
        0,
    )


def test_h1_gate_rejects_stale_bias_when_latest_completed_h1_has_no_event() -> None:
    t0 = datetime(2026, 1, 5, 12, 0, tzinfo=UTC)
    first = AggregatedBar(
        opened_at=t0,
        closed_at=t0 + timedelta(hours=1),
        source=_source("100", "102", "99", "101"),
        minute_count=60,
    )
    second = AggregatedBar(
        opened_at=t0 + timedelta(hours=1),
        closed_at=t0 + timedelta(hours=2),
        source=_source("101", "103", "100", "102"),
        minute_count=60,
    )
    event = HTFBiasEvent(
        confirmed_at=first.closed_at,
        direction=CapitalizerSourceDirection.BULLISH,
        closure_kind="CANDLE2_REVERSAL",
        poi_kind="SWING_LOW",
    )

    assert _immediate_h1_bias((first, second), (event,), first.closed_at) == event
    assert _immediate_h1_bias(
        (first, second),
        (event,),
        second.closed_at,
    ) is None


def test_prior_session_sweep_requires_close_back_through_reference_level() -> None:
    at = datetime(2026, 1, 5, 13, 0, tzinfo=UTC)
    reference = ReferenceLiquidity(
        opened_at=at - timedelta(hours=4),
        closed_at=at - timedelta(hours=1),
        high=Decimal("110"),
        low=Decimal("90"),
        source="TEST",
    )
    bullish = type(
        "Bar",
        (),
        {
            "low": Decimal("89"),
            "high": Decimal("101"),
            "close": Decimal("91"),
        },
    )()
    failed = type(
        "Bar",
        (),
        {
            "low": Decimal("89"),
            "high": Decimal("101"),
            "close": Decimal("89.5"),
        },
    )()

    assert _sweep_confirmed(
        bullish,
        side=CapitalizerSide.LONG,
        reference=reference,
    )
    assert not _sweep_confirmed(
        failed,
        side=CapitalizerSide.LONG,
        reference=reference,
    )


def test_structure_event_requires_close_through_prior_confirmed_swing() -> None:
    t0 = datetime(2026, 1, 5, 12, 0, tzinfo=UTC)
    bars = (
        TFBar(t0, t0 + timedelta(minutes=15), _source("100", "101", "99", "100")),
        TFBar(
            t0 + timedelta(minutes=15),
            t0 + timedelta(minutes=30),
            _source("100", "102", "99.5", "101.5"),
        ),
        TFBar(
            t0 + timedelta(minutes=30),
            t0 + timedelta(minutes=45),
            _source("101.5", "103", "101", "102.5"),
        ),
    )
    pivots = (
        Pivot(
            occurred_at=t0 - timedelta(minutes=30),
            confirmed_at=t0 - timedelta(minutes=15),
            price=Decimal("102"),
            kind="HIGH",
        ),
        Pivot(
            occurred_at=t0 - timedelta(minutes=20),
            confirmed_at=t0 - timedelta(minutes=10),
            price=Decimal("99"),
            kind="LOW",
        ),
    )
    event = _find_structure_event(
        bars,
        pivots,
        after=t0,
        before=t0 + timedelta(hours=1),
        side=CapitalizerSide.LONG,
        timeframe="M15",
    )
    assert event is not None
    assert event.break_price == Decimal("102")
    assert event.protected_swing_price == Decimal("99")
