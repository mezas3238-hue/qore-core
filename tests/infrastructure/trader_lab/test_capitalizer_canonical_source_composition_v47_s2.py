from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.trader_lab import (
    capitalizer_canonical_source_composition_v47_s2 as s2,
)
from qore.infrastructure.trader_lab import (
    capitalizer_source_strategy_isolation_v47_s2 as isolation,
)
from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
)
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
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


def _bullish_htf():
    observed = detect_candle2_reversal_closure(
        previous=_source("100", "102", "98", "99"),
        candle2=_source("99", "101", "97", "99.5"),
        point_of_interest_present=True,
    )
    assert observed is not None
    assert observed.direction is CapitalizerSourceDirection.BULLISH
    return observed


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
        rows.append(
            _m1(
                start + timedelta(minutes=minute),
                open_=open_ if minute == 0 else close,
                high=high,
                low=low,
                close=close,
            )
        )
    return tuple(rows)


def test_s2_m15_does_not_require_second_touch_of_same_h1_poi() -> None:
    start = datetime(2025, 1, 6, 10, 0, tzinfo=UTC)
    bars = (
        *_frame(start, open_="100", high="100.2", low="98.8", close="99"),
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

    bound = s2.bind_s2_m15_cisd(
        tuple(bars),
        direction=CapitalizerSourceDirection.BULLISH,
        higher_timeframe_closure=_bullish_htf(),
        after=start - timedelta(minutes=1),
        before=start + timedelta(minutes=45),
    )

    assert bound is not None
    assert bound.cisd.setup_confirmed is True
    assert bound.cisd.important_level_reached is True
    assert bound.confirmed_at == start + timedelta(minutes=45)


def test_s2_independent_m1_builds_own_sweep_mss_fvg_and_ob() -> None:
    start = datetime(2025, 1, 6, 11, 0, tzinfo=UTC)
    bars = (
        _m1(start, open_="100", high="101", low="99", close="100.5"),
        _m1(
            start + timedelta(minutes=1),
            open_="100.5",
            high="101",
            low="98",
            close="99.5",
        ),
        _m1(
            start + timedelta(minutes=2),
            open_="99.5",
            high="101.5",
            low="99",
            close="100",
        ),
        _m1(
            start + timedelta(minutes=3),
            open_="99.5",
            high="100",
            low="97.5",
            close="98.5",
        ),
        _m1(
            start + timedelta(minutes=4),
            open_="98.5",
            high="102.2",
            low="98.4",
            close="102",
        ),
        _m1(
            start + timedelta(minutes=5),
            open_="102",
            high="103",
            low="100.5",
            close="102.5",
        ),
        _m1(
            start + timedelta(minutes=6),
            open_="102.5",
            high="103.2",
            low="102",
            close="103",
        ),
    )

    bound = s2.bind_independent_m1_structure(
        bars,
        side=CapitalizerSide.LONG,
        higher_timeframe_closure=_bullish_htf(),
        after=start - timedelta(minutes=1),
        before=start + timedelta(minutes=7),
    )

    assert bound is not None
    assert bound.legacy_m3_zone_inherited is False
    assert bound.binding.m1_cisd.setup_confirmed is True
    assert bound.binding.m1_mss.confirmed is True
    assert bound.binding.order_block.confirmed is True
    assert bound.binding.fvg_confirmed is True
    assert bound.zone.fvg_low == Decimal("100")
    assert bound.zone.fvg_high == Decimal("100.5")
    assert bound.zone.overlap_low == Decimal("100")
    assert bound.zone.overlap_high == Decimal("100")
    assert bound.armed_at == start + timedelta(minutes=6)


def test_s2_report_enforces_monotone_pre_fill_funnel() -> None:
    with pytest.raises(ValueError, match="funnel monotonicity"):
        isolation.S2PeriodMarketReport(
            identity=isolation.IDENTITY,
            period="development",
            symbol="EURUSD",
            session="LONDON",
            period_start="2024-09-17T00:00:00+00:00",
            period_end_exclusive="2026-09-17T00:00:00+00:00",
            operating_days_scanned=1,
            upstream_events=1,
            htf_aligned=2,
            m15_bound=0,
            independent_m1_bound=0,
            event_target_bound=0,
            routed_fractal_candidates=0,
            exact_fills=0,
            v46_rejected_after_fill=0,
            admitted_exact_fills=0,
            provider_tick_requests=0,
        )
