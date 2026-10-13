"""Execution safety witnesses. Every result is synthetic, not a broker fill."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.research_accelerator.core import Quote, ResearchDataError
from qore.infrastructure.research_accelerator.execution import LimitOrder, simulate_ticks


ZERO = datetime(2024, 1, 8, 15, 0, tzinfo=UTC)
TICK = Decimal("0.1")


def _time(n: int) -> datetime:
    return ZERO + timedelta(minutes=n)


def test_never_fill_with_quote_before_order_activation() -> None:
    quotes = (
        Quote(_time(0), Decimal("99"), Decimal("99.2")),
        Quote(_time(1), Decimal("101"), Decimal("101.2")),
        Quote(_time(2), Decimal("101"), Decimal("101.3")),
    )
    order = LimitOrder(
        "pre_only", _time(1), _time(2), _time(2), "long",
        Decimal("100"), Decimal("98"), Decimal("103"),
    )
    assert simulate_ticks(quotes, (order,), tick_size=TICK) == [
        {"event_id": "pre_only", "status": "UNFILLED_OBSERVED_ONLY"}
    ]


def test_short_ask_exit_target_and_two_sided_fees() -> None:
    quotes = (
        Quote(_time(0), Decimal("100.2"), Decimal("100.4")),
        Quote(_time(1), Decimal("101.0"), Decimal("101.2")),
        Quote(_time(2), Decimal("99.0"), Decimal("99.2")),
    )
    order = LimitOrder(
        "sell", _time(0), _time(2), _time(2), "short",
        Decimal("100.8"), Decimal("102"), Decimal("99.5"),
    )
    ledger = simulate_ticks(
        quotes, (order,), tick_size=TICK,
        slippage_ticks=Decimal("1"), commission_per_unit=Decimal("0.2"),
    )
    record = ledger[0]
    assert record["exit_reason"] == "TARGET"
    assert record["fill_price"] == "100.9"  # BID at entry minus adverse slip
    assert record["exit_price"] == "99.6"  # target (not ASK improvement) plus slip
    assert Decimal(record["gross_price_points_per_unit"]) == Decimal("1.3")
    assert Decimal(record["net_price_points_per_unit"]) == Decimal("0.9")


def test_time_exit_only_on_real_observation_at_deadline() -> None:
    quotes = (
        Quote(_time(0), Decimal("99.8"), Decimal("100")),
        Quote(_time(1), Decimal("100.8"), Decimal("101")),
        Quote(_time(2), Decimal("101"), Decimal("101.2")),
    )
    order = LimitOrder(
        "timed", _time(0), _time(1), _time(2), "long",
        Decimal("100"), Decimal("98"), Decimal("103"),
    )
    row = simulate_ticks(quotes, (order,), tick_size=TICK)[0]
    assert row["exit_reason"] == "TIME"
    assert row["closed_at"] == _time(2).isoformat()
    assert Decimal(row["gross_price_points_per_unit"]) == Decimal("1")
    assert Decimal(row["net_price_points_per_unit"]) == Decimal("1")


def test_missing_exit_quote_is_incomplete_not_a_zero_pnl_trade() -> None:
    quotes = (
        Quote(_time(0), Decimal("99.8"), Decimal("100")),
        Quote(_time(3), Decimal("100.4"), Decimal("100.6")),
    )
    order = LimitOrder(
        "gap", _time(0), _time(1), _time(2), "long",
        Decimal("100"), Decimal("98"), Decimal("103"),
    )
    row = simulate_ticks(quotes, (order,), tick_size=TICK)[0]
    assert row["status"] == "INCOMPLETE_NO_EXIT_QUOTE"
    assert "net_price_points_per_unit" not in row


def test_stop_first_at_fill_and_worst_observed_bid_slippage() -> None:
    quotes = (
        Quote(_time(0), Decimal("98.5"), Decimal("99.9")),
        Quote(_time(1), Decimal("97"), Decimal("97.2")),
    )
    order = LimitOrder(
        "stop", _time(0), _time(1), _time(1), "long",
        Decimal("100"), Decimal("99"), Decimal("103"),
    )
    row = simulate_ticks(
        quotes, (order,), tick_size=TICK, slippage_ticks=Decimal("0.5"),
    )[0]
    assert row["exit_reason"] == "STOP"
    assert row["duration_seconds"] == "0"
    assert row["fill_price"] == "99.95"
    assert row["exit_price"] == "98.45"
    assert Decimal(row["net_price_points_per_unit"]) < 0


def test_invalid_order_chronology_rejected_fail_closed() -> None:
    invalid = LimitOrder(
        "invalid", _time(1), _time(1), _time(2), "short",
        Decimal("100"), Decimal("102"), Decimal("98"),
    )
    with pytest.raises(ResearchDataError, match="chronology"):
        simulate_ticks((), (invalid,), tick_size=TICK)
