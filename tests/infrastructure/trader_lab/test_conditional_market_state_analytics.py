from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import cast
from uuid import UUID

from qore.infrastructure.market_data import (
    Instrument,
    MarketDataSnapshotId,
    OhlcSnapshot,
    Timeframe,
)
from qore.infrastructure.ports import (
    AdapterId,
    ExternalSourceDescriptor,
    PortName,
    SourceId,
)
from qore.infrastructure.trader_lab.conditional_market_state_features import (
    event_fingerprint,
    expansion_state,
    market_state,
    momentum_regime,
    range_position,
    session_context,
    trade_excursions,
    trend_regime,
    trend_transition,
    volatility_percentile,
    volatility_regime,
)
from qore.infrastructure.trader_lab.conditional_market_state_surfaces import (
    build_conditional_surface,
)
from qore.infrastructure.trader_lab.first_cohort_backtest import (
    FirstCohortBacktestTrade,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide

_SOURCE = ExternalSourceDescriptor(
    adapter_id=AdapterId(UUID("7a000000-0000-0000-0000-000000000001")),
    source_id=SourceId(UUID("7a000000-0000-0000-0000-000000000002")),
    port_name=PortName("market-data.conditional-analytics-test"),
)


def _bar(
    index: int,
    close: float,
    *,
    spread: float = 0.001,
    start: datetime | None = None,
) -> OhlcSnapshot:
    origin = start or datetime(2026, 1, 1, tzinfo=UTC)
    opened_at = origin + timedelta(minutes=5 * index)
    return OhlcSnapshot(
        snapshot_id=MarketDataSnapshotId(
            UUID(f"7a000000-0000-0000-0001-{index + 1:012d}")
        ),
        instrument=Instrument("EURUSD"),
        source=_SOURCE,
        timeframe=Timeframe(300),
        opened_at=opened_at,
        closed_at=opened_at + timedelta(minutes=5),
        open=close,
        high=close + spread,
        low=close - spread,
        close=close,
    )


def _observation(
    *,
    side: str | None,
    status: str,
    rate: str | None,
    trend: str = "trend_up",
    volatility: str = "normal",
) -> dict[str, object]:
    return {
        "decision_time_state": {
            "trend_regime": trend,
            "trend_transition": "stable_trend",
            "volatility_regime": volatility,
            "volatility_percentile_bucket": "p40_60",
            "session_context": "london+new_york",
            "hour_utc": "14",
            "weekday_utc": "2",
            "momentum_regime": "up",
            "range_position": "upper_third",
            "expansion_state": "stable",
        },
        "decision": {"status": status, "side": side},
        "outcome_evaluation": {
            "trade_filled": rate is not None,
            "trade_return_rate": rate,
            "mfe_fraction": "0.02" if rate is not None else None,
            "mae_fraction": "0.01" if rate is not None else None,
            "exit_reason": (
                "target" if rate is not None and Decimal(rate) > 0 else "stop"
            ),
        },
    }


def _first_cell(surface: dict[str, object]) -> dict[str, object]:
    cells = cast(list[dict[str, object]], surface["cells"])
    return cells[0]


def test_session_context_is_dst_aware() -> None:
    winter = datetime(2026, 1, 15, 12, 30, tzinfo=UTC)
    summer = datetime(2026, 7, 15, 12, 30, tzinfo=UTC)

    winter_context, winter_overlap = session_context(winter)
    summer_context, summer_overlap = session_context(summer)

    assert winter_context == "london"
    assert winter_overlap is False
    assert summer_context == "london+new_york"
    assert summer_overlap is True


def test_trend_regime_and_transition_use_only_closed_history() -> None:
    rising = tuple(_bar(index, 1.0 + index * 0.001) for index in range(20))
    ranging = tuple(
        _bar(20 + index, 1.020 + (0.001 if index % 2 else -0.001))
        for index in range(20)
    )
    history = rising + ranging

    assert trend_regime(rising) == "trend_up"
    assert trend_regime(ranging) == "range"
    assert trend_transition(history) == "transition"


def test_volatility_percentile_and_regime_are_past_only() -> None:
    quiet = tuple(_bar(index, 1.0, spread=0.0005) for index in range(40))
    active = tuple(_bar(40 + index, 1.0, spread=0.0015) for index in range(10))
    history = quiet + active

    percentile = volatility_percentile(history)

    assert percentile is not None
    assert percentile > Decimal(80)
    assert volatility_regime(history) == "high"


def test_expansion_momentum_and_range_position_are_classified() -> None:
    baseline = tuple(
        _bar(index, 1.0 + index * 0.0001, spread=0.0005)
        for index in range(20)
    )
    recent = tuple(
        _bar(20 + index, 1.002 + index * 0.002, spread=0.0015) for index in range(3)
    )
    history = baseline + recent

    assert expansion_state(history) == "expansion"
    assert momentum_regime(history) == "up"
    assert range_position(history) == "upper_third"


def test_market_state_does_not_depend_on_future_rows() -> None:
    history = tuple(_bar(index, 1.0 + index * 0.0005) for index in range(60))
    as_of = history[-1].closed_at
    before = market_state(
        history, context_history=history, as_of=as_of, execution_period="M5"
    )
    future = tuple(_bar(60 + index, 1.5 - index * 0.01) for index in range(10))

    after = market_state(
        (history + future)[:60],
        context_history=history,
        as_of=as_of,
        execution_period="M5",
    )

    assert before == after
    assert before["available_at_only"] is True


def test_trade_excursions_use_ohlc_extrema_not_only_closes() -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    execution = (
        _bar(0, 1.00, spread=0.01, start=start),
        _bar(1, 1.01, spread=0.03, start=start),
        _bar(2, 1.00, spread=0.02, start=start),
    )
    trade = FirstCohortBacktestTrade(
        trader_code="vt-01",
        signal_at=execution[0].closed_at,
        filled_at=execution[1].closed_at,
        exited_at=execution[2].closed_at,
        side=DemoTradingSetupSide.LONG,
        entry_price=Decimal("1.00"),
        stop_loss=Decimal("0.95"),
        take_profit=Decimal("1.10"),
        exit_price=Decimal("1.00"),
        return_rate=Decimal("0"),
        exit_reason="time_exit",
    )
    closed_index = {bar.closed_at: index for index, bar in enumerate(execution)}

    mfe, mae = trade_excursions(trade, execution, closed_index)

    assert mfe == Decimal("0.04")
    assert mae == Decimal("0.02")


def test_surface_retains_opportunity_denominator_and_fill_funnel() -> None:
    observations = (
        *(_observation(side=None, status="abstain", rate=None) for _ in range(5)),
        *(_observation(side="long", status="setup", rate="0.01") for _ in range(10)),
        *(_observation(side="long", status="setup", rate=None) for _ in range(2)),
    )

    surface = build_conditional_surface(tuple(observations), ("trend_regime",))
    cell = _first_cell(surface)

    assert cell["opportunity_count"] == 17
    assert cell["abstain_count"] == 5
    assert cell["setup_count"] == 12
    assert cell["filled_count"] == 10
    assert cell["evidence_state"] == "FAVORABLE_EXPLORATORY"
    assert cell["certified"] is False
    assert cell["fresh_holdout_required_for_promotion"] is True


def test_surface_marks_small_positive_niche_insufficient() -> None:
    observations = tuple(
        _observation(side="short", status="setup", rate="0.03") for _ in range(9)
    )

    surface = build_conditional_surface(observations, ("side", "volatility_regime"))
    cell = _first_cell(surface)

    assert cell["filled_count"] == 9
    assert cell["evidence_state"] == "INSUFFICIENT_EVIDENCE"


def test_surface_separates_adverse_conditional_region() -> None:
    observations = tuple(
        _observation(side="short", status="setup", rate="-0.01") for _ in range(10)
    )

    surface = build_conditional_surface(observations, ("side", "trend_regime"))

    assert _first_cell(surface)["evidence_state"] == "ADVERSE_EXPLORATORY"


def test_event_fingerprint_is_deterministic_and_trader_isolated() -> None:
    decision_at = datetime(2026, 1, 1, 10, tzinfo=UTC)
    first = event_fingerprint(
        trader_code="vt-01",
        symbol="GBPUSD",
        software_sha="a" * 40,
        decision_at=decision_at,
        execution_period="M5",
    )
    repeated = event_fingerprint(
        trader_code="vt-01",
        symbol="GBPUSD",
        software_sha="a" * 40,
        decision_at=decision_at,
        execution_period="M5",
    )
    other_trader = event_fingerprint(
        trader_code="vt-08",
        symbol="GBPUSD",
        software_sha="a" * 40,
        decision_at=decision_at,
        execution_period="M5",
    )

    assert first == repeated
    assert first != other_trader
    assert len(first) == 64
