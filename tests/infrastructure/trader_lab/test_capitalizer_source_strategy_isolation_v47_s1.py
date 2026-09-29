from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab import (
    capitalizer_source_strategy_isolation_v47_s1 as s1,
)
from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
)
from qore.infrastructure.trader_lab.capitalizer_contract import CapitalizerSession
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide


def _m1(
    opened_at: datetime,
    *,
    symbol: str = "EURUSD",
    open_: str = "1.1000",
    high: str = "1.1010",
    low: str = "1.0990",
    close: str = "1.1005",
) -> CapitalizerM1Bar:
    return CapitalizerM1Bar(
        symbol=symbol,
        opened_at=opened_at,
        closed_at=opened_at + timedelta(minutes=1),
        open=Decimal(open_),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
        volume=1,
        digits=5,
    )


def _row(
    *,
    symbol: str,
    session: str,
    operating_date: str,
    entry_at: str,
) -> s1.S1AdmittedFillRow:
    return s1.S1AdmittedFillRow(
        identity=s1.IDENTITY,
        period="development",
        symbol=symbol,
        session=session,
        operating_date=operating_date,
        side="LONG",
        route="FRACTAL_SCALP_CONTINUATION",
        armed_at=entry_at,
        entry_at=entry_at,
        entry_price="100",
        armed_level_used="100",
        entry_mode="FVG_CE_50",
        stop_price="99",
        target_price="102",
        target_kind="HIGHER_TIMEFRAME_STRUCTURAL_OBJECTIVE",
        provider_tick_count=1,
        provider_request_count=1,
    )


def test_source_session_bounds_use_official_v46_windows() -> None:
    london_start, london_end = s1.source_session_bounds(
        date(2025, 7, 15),
        session=CapitalizerSession.LONDON,
    )
    ny_start, ny_end = s1.source_session_bounds(
        date(2025, 7, 15),
        session=CapitalizerSession.NEW_YORK,
    )

    assert london_start.astimezone(s1.NEW_YORK).hour == 2
    assert london_end.astimezone(s1.NEW_YORK).hour == 5
    assert ny_start.astimezone(s1.NEW_YORK).hour == 7
    assert ny_end.astimezone(s1.NEW_YORK).hour == 9


def test_asian_open_is_dst_aware_and_always_midnight_utc() -> None:
    winter_start, winter_end = s1.source_session_bounds(
        date(2025, 1, 15),
        session=CapitalizerSession.ASIA,
    )
    summer_start, summer_end = s1.source_session_bounds(
        date(2025, 7, 15),
        session=CapitalizerSession.ASIA,
    )

    assert winter_start == datetime(2025, 1, 16, 0, 0, tzinfo=UTC)
    assert summer_start == datetime(2025, 7, 16, 0, 0, tzinfo=UTC)
    assert winter_start.astimezone(s1.NEW_YORK).hour == 19
    assert summer_start.astimezone(s1.NEW_YORK).hour == 20
    assert winter_end - winter_start == timedelta(hours=2)
    assert summer_end - summer_start == timedelta(hours=2)


def test_prior_source_session_is_immediately_completed_source_window() -> None:
    london_prior = s1.prior_source_session_bounds(
        date(2025, 7, 16),
        session=CapitalizerSession.LONDON,
    )
    expected_asia = s1.source_session_bounds(
        date(2025, 7, 15),
        session=CapitalizerSession.ASIA,
    )
    ny_prior = s1.prior_source_session_bounds(
        date(2025, 7, 16),
        session=CapitalizerSession.NEW_YORK,
    )
    expected_london = s1.source_session_bounds(
        date(2025, 7, 16),
        session=CapitalizerSession.LONDON,
    )

    assert london_prior == expected_asia
    assert ny_prior == expected_london


def test_possible_touch_intervals_are_only_necessary_condition_minutes() -> None:
    start = datetime(2025, 1, 6, 12, 0, tzinfo=UTC)
    bars = (
        _m1(start, high="1.1010", low="1.1000"),
        _m1(
            start + timedelta(minutes=1),
            high="1.1005",
            low="1.0980",
        ),
        _m1(
            start + timedelta(minutes=2),
            high="1.1030",
            low="1.1000",
        ),
    )

    long_rows = s1.possible_touch_intervals(
        bars,
        side=CapitalizerSide.LONG,
        level=Decimal("1.0990"),
        start=start,
        end=start + timedelta(minutes=3),
    )
    short_rows = s1.possible_touch_intervals(
        bars,
        side=CapitalizerSide.SHORT,
        level=Decimal("1.1020"),
        start=start,
        end=start + timedelta(minutes=3),
    )

    assert len(long_rows) == 1
    assert long_rows[0][0] == start + timedelta(minutes=1)
    assert len(short_rows) == 1
    assert short_rows[0][0] == start + timedelta(minutes=2)


def test_max3_uses_entry_time_then_symbol_without_outcome_ranking() -> None:
    rows = (
        _row(
            symbol="GBPJPY",
            session="ASIA",
            operating_date="2025-01-06",
            entry_at="2025-01-07T00:03:00+00:00",
        ),
        _row(
            symbol="USDJPY",
            session="ASIA",
            operating_date="2025-01-06",
            entry_at="2025-01-07T00:01:00+00:00",
        ),
        _row(
            symbol="AUDUSD",
            session="ASIA",
            operating_date="2025-01-06",
            entry_at="2025-01-07T00:02:00+00:00",
        ),
        _row(
            symbol="AUDJPY",
            session="ASIA",
            operating_date="2025-01-06",
            entry_at="2025-01-07T00:02:00+00:00",
        ),
    )

    selected = s1.select_max3(rows)

    assert [row.symbol for row in selected] == [
        "USDJPY",
        "AUDJPY",
        "AUDUSD",
    ]
    assert all(row.outcome_used_for_selection is False for row in selected)


def test_market_report_rejects_fill_classification_drift() -> None:
    try:
        s1.S1PeriodMarketReport(
            identity=s1.IDENTITY,
            period="development",
            symbol="EURUSD",
            session="LONDON",
            period_start="2024-09-17T00:00:00+00:00",
            period_end_exclusive="2026-09-17T00:00:00+00:00",
            operating_days_scanned=1,
            routed_armed_candidates=2,
            primary_fill_passes=1,
            fallback_fill_passes=0,
            no_provider_fill=0,
            v46_rejected_after_fill=0,
            admitted_exact_fills=1,
            provider_tick_requests=1,
        )
    except ValueError as error:
        assert "fill classification count drift" in str(error)
    else:
        raise AssertionError("classification drift must fail closed")
