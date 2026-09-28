from __future__ import annotations

from qore.infrastructure.trader_lab import (
    capitalizer_ctrader_historical_bidask_availability_census_v1 as census,
)


def test_census_scope_is_consumed_only() -> None:
    assert len(census.ANCHORS) == 6
    assert min(census.ANCHORS).year == 2020
    assert max(census.ANCHORS).year == 2025


def test_quote_types_are_bid_and_ask() -> None:
    assert census.QUOTE_TYPES == (("BID", 1), ("ASK", 2))


def test_rate_limit_is_below_documented_historical_ceiling() -> None:
    assert census.MIN_REQUEST_INTERVAL_SECONDS >= 0.25


def test_rows_never_retain_price_or_spread_economics() -> None:
    row = census.TickAvailabilityRow(
        canonical_symbol="EURUSD",
        provider_symbol="EURUSD",
        provider_symbol_id=1,
        digits=5,
        requested_start="2024-10-01T15:00:00+00:00",
        requested_end_exclusive="2024-10-01T15:05:00+00:00",
        quote_type="BID",
        request_succeeded=True,
        tick_count=10,
        has_more=False,
        failure_type=None,
    )

    assert row.prices_retained is False
    assert row.spread_computed is False
    assert row.trade_outcomes_read is False
    assert row.fresh_holdout_touched is False
