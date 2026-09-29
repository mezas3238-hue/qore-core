from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab import (
    capitalizer_ftm_raw_population_v47_s1r_c as ftm,
)
from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
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


def _bar(
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


def _bullish_htf():
    result = detect_candle2_reversal_closure(
        previous=_source("100", "102", "98", "99"),
        candle2=_source("99", "101", "97", "99.5"),
        point_of_interest_present=True,
    )
    assert result is not None
    return result


def test_taken_side_maps_expected_reversal_and_continuation_deterministically() -> None:
    high_expected, high_continuation = ftm._direction_pair(ftm.FTMTakenSide.HIGH)
    low_expected, low_continuation = ftm._direction_pair(ftm.FTMTakenSide.LOW)

    assert high_expected is CapitalizerSourceDirection.BEARISH
    assert high_continuation is CapitalizerSourceDirection.BULLISH
    assert low_expected is CapitalizerSourceDirection.BULLISH
    assert low_continuation is CapitalizerSourceDirection.BEARISH


def test_first_structural_cisd_does_not_require_htf_alignment_for_raw_structure() -> None:
    start = datetime(2025, 1, 6, 12, 0, tzinfo=UTC)
    bars = (
        _bar(start, open_="100", high="100.2", low="99", close="99.5"),
        _bar(
            start + timedelta(minutes=1),
            open_="99.5",
            high="99.7",
            low="98.8",
            close="99",
        ),
        _bar(
            start + timedelta(minutes=2),
            open_="99",
            high="101",
            low="98.9",
            close="100.5",
        ),
    )

    confirmed = ftm.first_structural_m1_cisd(
        bars,
        direction=CapitalizerSourceDirection.BULLISH,
        after=start - timedelta(seconds=1),
        before=start + timedelta(minutes=3),
        htf_closure=_bullish_htf(),
    )

    assert confirmed == start + timedelta(minutes=3)


def test_raw_report_requires_exhaustive_classification() -> None:
    try:
        ftm.FTMRawPeriodMarketReport(
            identity=ftm.IDENTITY,
            period="development",
            symbol="EURUSD",
            session="LONDON",
            raw_liquidity_sweeps=2,
            classification_counts={
                ftm.FTMRawClassification.HTF_CONTEXT_UNRESOLVED.value: 1
            },
            continuation_first_raw_support=0,
        )
    except ValueError as error:
        assert "classification coverage drift" in str(error)
    else:
        raise AssertionError("raw FTM census must classify every sweep")
