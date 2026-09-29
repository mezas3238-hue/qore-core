from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab import (
    capitalizer_canonical_source_context_binders_v47_s0 as binders,
)
from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
)
from qore.infrastructure.trader_lab.capitalizer_full_ict_density_scanner_1y_v1 import (
    AggregatedBar,
)
from qore.infrastructure.trader_lab.capitalizer_source_observation_detectors_v2 import (
    CapitalizerSourceBar,
    CapitalizerSourceDirection,
    detect_candle2_reversal_closure,
)


def _source(open_: str, high: str, low: str, close: str) -> CapitalizerSourceBar:
    return CapitalizerSourceBar(
        open=Decimal(open_),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
    )


def _h1(
    opened_at: datetime,
    open_: str,
    high: str,
    low: str,
    close: str,
) -> AggregatedBar:
    return AggregatedBar(
        opened_at=opened_at,
        closed_at=opened_at + timedelta(hours=1),
        source=_source(open_, high, low, close),
        minute_count=60,
    )


def test_htf_event_binds_actual_causal_poi_and_candle2_closure() -> None:
    start = datetime(2025, 1, 6, 9, 0, tzinfo=UTC)
    h1 = (
        _h1(start, "100", "105", "95", "102"),
        _h1(start + timedelta(hours=1), "102", "102", "90", "100"),
        _h1(start + timedelta(hours=2), "100", "103", "96", "101"),
        _h1(start + timedelta(hours=3), "101", "102", "89", "99"),
    )

    events = binders._htf_events(h1)

    assert events
    event = events[-1]
    assert event.confirmed_at == start + timedelta(hours=4)
    assert event.closure.direction is CapitalizerSourceDirection.BULLISH
    assert event.closure.source_rule_satisfied is True
    assert len(event.pois) == 1
    assert event.pois[0].lower_price == Decimal("90")
    assert event.pois[0].upper_price == Decimal("90")


def _m1(
    opened_at: datetime,
    *,
    open_: str,
    high: str,
    low: str,
    close: str,
) -> CapitalizerM1Bar:
    return CapitalizerM1Bar(
        symbol="EURUSD",
        opened_at=opened_at,
        closed_at=opened_at + timedelta(minutes=1),
        open=Decimal(open_),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
        volume=None,
        digits=5,
    )


def _frame(
    start: datetime,
    *,
    open_: str,
    high: str,
    low: str,
    close: str,
) -> tuple[CapitalizerM1Bar, ...]:
    rows: list[CapitalizerM1Bar] = []
    for minute in range(15):
        row_open = open_ if minute == 0 else close
        row_close = close
        rows.append(
            _m1(
                start + timedelta(minutes=minute),
                open_=row_open,
                high=high,
                low=low,
                close=row_close,
            )
        )
    return tuple(rows)


def test_m15_cisd_binder_uses_opposing_series_then_first_confirming_close() -> None:
    start = datetime(2025, 1, 6, 10, 0, tzinfo=UTC)
    bars = (
        *_frame(
            start,
            open_="100",
            high="100.5",
            low="98.8",
            close="99",
        ),
        *_frame(
            start + timedelta(minutes=15),
            open_="99",
            high="99.2",
            low="98.2",
            close="98.5",
        ),
        *_frame(
            start + timedelta(minutes=30),
            open_="98.5",
            high="101",
            low="98.4",
            close="100.5",
        ),
    )
    htf = detect_candle2_reversal_closure(
        previous=_source("100", "102", "98", "99"),
        candle2=_source("99", "101", "97", "99.5"),
        point_of_interest_present=True,
    )
    assert htf is not None

    binding = binders.bind_first_m15_cisd(
        tuple(bars),
        direction=CapitalizerSourceDirection.BULLISH,
        higher_timeframe_closure=htf,
        after=start - timedelta(minutes=1),
        before=start + timedelta(minutes=45),
    )

    assert binding is not None
    assert binding.confirmed_at == start + timedelta(minutes=45)
    assert binding.cisd.setup_confirmed is True
    assert binding.cisd.causal_series_open == Decimal("100")
    assert binding.protected_swing.confirmed is True
    assert binding.protected_swing.swing_price == Decimal("98.2")
    assert binding.causal is True


def test_m15_cisd_binder_never_uses_confirmation_after_before() -> None:
    start = datetime(2025, 1, 6, 10, 0, tzinfo=UTC)
    bars = (
        *_frame(start, open_="100", high="100.5", low="98.8", close="99"),
        *_frame(
            start + timedelta(minutes=15),
            open_="99",
            high="99.2",
            low="98.2",
            close="98.5",
        ),
        *_frame(
            start + timedelta(minutes=30),
            open_="98.5",
            high="101",
            low="98.4",
            close="100.5",
        ),
    )
    htf = detect_candle2_reversal_closure(
        previous=_source("100", "102", "98", "99"),
        candle2=_source("99", "101", "97", "99.5"),
        point_of_interest_present=True,
    )
    assert htf is not None

    binding = binders.bind_first_m15_cisd(
        tuple(bars),
        direction=CapitalizerSourceDirection.BULLISH,
        higher_timeframe_closure=htf,
        after=start - timedelta(minutes=1),
        before=start + timedelta(minutes=44),
    )

    assert binding is None


def test_canonical_source_context_fails_closed_without_htf_context() -> None:
    decision = datetime(2025, 1, 6, 12, 0, tzinfo=UTC)

    binding = binders.bind_canonical_source_context(
        (),
        direction=CapitalizerSourceDirection.BULLISH,
        entry_price=Decimal("100"),
        decision_at=decision,
    )

    assert binding is None


def test_m1_structure_binds_cisd_mss_order_block_and_m1_protected_swing() -> None:
    start = datetime(2025, 1, 6, 9, 58, tzinfo=UTC)
    bars = (
        _m1(start, open_="99", high="100", low="98", close="99.5"),
        _m1(
            start + timedelta(minutes=1),
            open_="99.5",
            high="103",
            low="99",
            close="102",
        ),
        _m1(
            start + timedelta(minutes=2),
            open_="102",
            high="102.5",
            low="100",
            close="101",
        ),
        _m1(
            start + timedelta(minutes=3),
            open_="101",
            high="101.5",
            low="99",
            close="100",
        ),
        _m1(
            start + timedelta(minutes=4),
            open_="100",
            high="104.5",
            low="99.5",
            close="104",
        ),
    )
    htf = detect_candle2_reversal_closure(
        previous=_source("100", "102", "98", "99"),
        candle2=_source("99", "101", "97", "99.5"),
        point_of_interest_present=True,
    )
    assert htf is not None
    zone = binders.v3_source.M1EntryZone(
        ob_opened_at=start + timedelta(minutes=3),
        ob_low=Decimal("99"),
        ob_high=Decimal("101.5"),
        fvg_confirmed_at=start + timedelta(minutes=4),
        fvg_low=Decimal("101"),
        fvg_high=Decimal("102"),
        overlap_low=Decimal("101"),
        overlap_high=Decimal("101.5"),
    )

    result = binders.bind_m1_source_structure(
        bars,
        direction=CapitalizerSourceDirection.BULLISH,
        higher_timeframe_closure=htf,
        zone=zone,
        after=start - timedelta(minutes=1),
        before=start + timedelta(minutes=5),
    )

    assert result is not None
    assert result.m1_cisd.setup_confirmed is True
    assert result.m1_mss.confirmed is True
    assert result.order_block.confirmed is True
    assert result.protected_swing.confirmed is True
    assert result.protected_swing.swing_price == Decimal("99")
    assert result.confirmed_at == start + timedelta(minutes=5)
    assert result.fvg_confirmed is True
