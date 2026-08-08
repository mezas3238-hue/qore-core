from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import cast

import pytest

from qore.infrastructure.historical_market_data import (
    HistoricalMarketDataPlanningValidationError,
    HistoricalOhlcPlanningPolicy,
    HistoricalOhlcRequestPlan,
    HistoricalOhlcWindow,
    plan_historical_ohlc_requests,
)
from qore.infrastructure.market_data import Instrument, OhlcRequest, Timeframe
from qore.kernel.result import Failure, Success

_BASE = datetime(2026, 8, 8, 12, 0, tzinfo=UTC)


def test_one_hour_m15_window_plans_four_contiguous_requests() -> None:
    window = HistoricalOhlcWindow(
        instrument=Instrument("EUR_USD"),
        timeframe=Timeframe(900),
        opened_at=_BASE,
        closed_at=_BASE + timedelta(hours=1),
    )
    policy = HistoricalOhlcPlanningPolicy(maximum_intervals=4)

    result = plan_historical_ohlc_requests(window, policy=policy)

    assert isinstance(result, Success)
    plan = result.value
    assert plan.window == window
    assert plan.policy == policy
    assert window.interval_count == 4
    assert len(plan.requests) == 4
    assert tuple(request.opened_at for request in plan.requests) == (
        _BASE,
        _BASE + timedelta(minutes=15),
        _BASE + timedelta(minutes=30),
        _BASE + timedelta(minutes=45),
    )
    assert tuple(request.closed_at for request in plan.requests) == (
        _BASE + timedelta(minutes=15),
        _BASE + timedelta(minutes=30),
        _BASE + timedelta(minutes=45),
        _BASE + timedelta(hours=1),
    )
    assert all(request.instrument == Instrument("EUR_USD") for request in plan.requests)
    assert all(request.timeframe == Timeframe(900) for request in plan.requests)


def test_m5_window_plans_exact_stable_sequence() -> None:
    window = HistoricalOhlcWindow(
        instrument=Instrument("GBP_USD"),
        timeframe=Timeframe(300),
        opened_at=_BASE,
        closed_at=_BASE + timedelta(minutes=30),
    )
    policy = HistoricalOhlcPlanningPolicy(maximum_intervals=10)

    first = plan_historical_ohlc_requests(window, policy=policy)
    second = plan_historical_ohlc_requests(window, policy=policy)

    assert isinstance(first, Success)
    assert isinstance(second, Success)
    assert len(first.value.requests) == 6
    assert first.value.logical_values() == second.value.logical_values()
    for index, request in enumerate(first.value.requests):
        assert request.opened_at == _BASE + timedelta(minutes=index * 5)
        assert request.closed_at == _BASE + timedelta(minutes=(index + 1) * 5)


def test_window_rejects_naive_or_non_integral_boundaries() -> None:
    with pytest.raises(
        HistoricalMarketDataPlanningValidationError,
        match="timezone-aware",
    ):
        HistoricalOhlcWindow(
            instrument=Instrument("EUR_USD"),
            timeframe=Timeframe(900),
            opened_at=datetime(2026, 8, 8, 12, 0),
            closed_at=datetime(2026, 8, 8, 13, 0),
        )

    with pytest.raises(
        HistoricalMarketDataPlanningValidationError,
        match="whole number of timeframes",
    ):
        HistoricalOhlcWindow(
            instrument=Instrument("EUR_USD"),
            timeframe=Timeframe(900),
            opened_at=_BASE,
            closed_at=_BASE + timedelta(minutes=20),
        )

    with pytest.raises(
        HistoricalMarketDataPlanningValidationError,
        match="whole seconds",
    ):
        HistoricalOhlcWindow(
            instrument=Instrument("EUR_USD"),
            timeframe=Timeframe(900),
            opened_at=_BASE,
            closed_at=_BASE + timedelta(minutes=15, microseconds=1),
        )


def test_policy_rejects_bool_zero_and_negative_limits() -> None:
    for invalid in (cast(int, True), 0, -1):
        with pytest.raises(
            HistoricalMarketDataPlanningValidationError,
            match="positive int",
        ):
            HistoricalOhlcPlanningPolicy(maximum_intervals=invalid)


def test_planner_fails_closed_before_partial_plan_when_limit_is_exceeded() -> None:
    window = HistoricalOhlcWindow(
        instrument=Instrument("EUR_USD"),
        timeframe=Timeframe(900),
        opened_at=_BASE,
        closed_at=_BASE + timedelta(hours=1),
    )

    result = plan_historical_ohlc_requests(
        window,
        policy=HistoricalOhlcPlanningPolicy(maximum_intervals=3),
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, HistoricalMarketDataPlanningValidationError)
    assert "exceeds maximum_intervals" in str(result.error)


def test_plan_contract_rejects_noncontiguous_or_wrong_requests() -> None:
    window = HistoricalOhlcWindow(
        instrument=Instrument("EUR_USD"),
        timeframe=Timeframe(900),
        opened_at=_BASE,
        closed_at=_BASE + timedelta(minutes=30),
    )
    policy = HistoricalOhlcPlanningPolicy(maximum_intervals=2)
    first = OhlcRequest(
        instrument=Instrument("EUR_USD"),
        timeframe=Timeframe(900),
        opened_at=_BASE,
        closed_at=_BASE + timedelta(minutes=15),
    )
    wrong_second = OhlcRequest(
        instrument=Instrument("EUR_USD"),
        timeframe=Timeframe(900),
        opened_at=_BASE + timedelta(minutes=30),
        closed_at=_BASE + timedelta(minutes=45),
    )

    with pytest.raises(
        HistoricalMarketDataPlanningValidationError,
        match="contiguous and stably ordered",
    ):
        HistoricalOhlcRequestPlan(
            window=window,
            policy=policy,
            requests=(first, wrong_second),
        )


def test_planner_rejects_wrong_runtime_types() -> None:
    window = HistoricalOhlcWindow(
        instrument=Instrument("EUR_USD"),
        timeframe=Timeframe(900),
        opened_at=_BASE,
        closed_at=_BASE + timedelta(minutes=15),
    )
    policy = HistoricalOhlcPlanningPolicy(maximum_intervals=1)

    wrong_window = plan_historical_ohlc_requests(
        cast(HistoricalOhlcWindow, "not-a-window"),
        policy=policy,
    )
    wrong_policy = plan_historical_ohlc_requests(
        window,
        policy=cast(HistoricalOhlcPlanningPolicy, "not-a-policy"),
    )

    assert isinstance(wrong_window, Failure)
    assert isinstance(wrong_window.error, HistoricalMarketDataPlanningValidationError)
    assert isinstance(wrong_policy, Failure)
    assert isinstance(wrong_policy.error, HistoricalMarketDataPlanningValidationError)
