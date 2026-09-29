from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.trader_lab import (
    capitalizer_source_semantics_root_cause_v47_s1r as s1r,
)
from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
)
from qore.infrastructure.trader_lab.capitalizer_source_observation_detectors_v2 import (
    CapitalizerSourceBar,
    CapitalizerSourceDirection,
    detect_candle2_reversal_closure,
)
from qore.infrastructure.trader_lab.capitalizer_source_poi_v2 import (
    CapitalizerSourcePOI,
    CapitalizerSourcePOIKind,
)


def _source(open_: str, high: str, low: str, close: str) -> CapitalizerSourceBar:
    return CapitalizerSourceBar(
        open=Decimal(open_),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
    )


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
    result: list[CapitalizerM1Bar] = []
    for minute in range(15):
        result.append(
            _m1(
                start + timedelta(minutes=minute),
                open_=open_ if minute == 0 else close,
                high=high,
                low=low,
                close=close,
            )
        )
    return tuple(result)


def _bullish_htf():
    observed = detect_candle2_reversal_closure(
        previous=_source("100", "102", "98", "99"),
        candle2=_source("99", "101", "97", "99.5"),
        point_of_interest_present=True,
    )
    assert observed is not None
    assert observed.direction is CapitalizerSourceDirection.BULLISH
    return observed


def test_m15_scan_separates_structural_cisd_from_same_h1_poi_reinteraction() -> None:
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
    far_poi = CapitalizerSourcePOI(
        kind=CapitalizerSourcePOIKind.SWING_LOW,
        lower_price=Decimal("90"),
        upper_price=Decimal("90"),
        source_bar_count=3,
    )

    scan = s1r._scan_m15(
        tuple(bars),
        direction=CapitalizerSourceDirection.BULLISH,
        htf=_bullish_htf(),
        pois=(far_poi,),
        after=start - timedelta(minutes=1),
        before=start + timedelta(minutes=45),
    )

    assert scan.strict_confirmed is False
    assert scan.structural_without_poi_confirmed is True
    assert scan.opposing_series_seen is True
    assert scan.close_through_seen is True


def test_m15_scan_retains_strict_pass_when_source_poi_is_interacted() -> None:
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
    interacted = CapitalizerSourcePOI(
        kind=CapitalizerSourcePOIKind.SWING_LOW,
        lower_price=Decimal("99"),
        upper_price=Decimal("99"),
        source_bar_count=3,
    )

    scan = s1r._scan_m15(
        tuple(bars),
        direction=CapitalizerSourceDirection.BULLISH,
        htf=_bullish_htf(),
        pois=(interacted,),
        after=start - timedelta(minutes=1),
        before=start + timedelta(minutes=45),
    )

    assert scan.strict_confirmed is True
    assert scan.opposing_series_seen is True
    assert scan.close_through_seen is True


def test_s1r_report_requires_complete_reason_partition() -> None:
    with pytest.raises(ValueError, match="cover every source event"):
        s1r.S1RPeriodMarketReport(
            identity=s1r.IDENTITY,
            period="development",
            symbol="EURUSD",
            session="LONDON",
            source_events=2,
            m15_failure_classes={"HTF_UNRESOLVED": 1},
            current_context_passes=0,
            current_m1_passes=0,
            current_m1_failures_audited=0,
            independent_m1_local_sweep_cisd=0,
            independent_m1_validated_ob=0,
            independent_m1_mss=0,
            independent_m1_displacement_fvg=0,
            independent_m1_owner_triad_complete=0,
        )


def test_directional_fvg_requires_matching_gap_direction() -> None:
    assert s1r._directional_fvg(
        _source("100", "101", "99", "100"),
        _source("101", "105", "100", "104"),
        _source("104", "106", "102", "105"),
        direction=CapitalizerSourceDirection.BULLISH,
    )
    assert not s1r._directional_fvg(
        _source("100", "101", "99", "100"),
        _source("101", "105", "100", "104"),
        _source("104", "106", "102", "105"),
        direction=CapitalizerSourceDirection.BEARISH,
    )
