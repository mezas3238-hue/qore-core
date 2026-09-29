from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.trader_lab import (
    capitalizer_canonical_source_candidate_assembly_v47_s0 as s0,
)
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import (
    CapitalizerSide,
)


@dataclass(frozen=True)
class _Tick:
    timestamp: int
    tick: int


def _ms(value: datetime) -> int:
    return int(value.timestamp() * 1000)


def test_decode_provider_tick_interval_returns_chronological_ticks() -> None:
    start = datetime(2025, 1, 2, 10, 0, tzinfo=UTC)
    end = start + timedelta(minutes=1)
    newest = start + timedelta(seconds=50)
    ticks = (
        _Tick(timestamp=_ms(newest), tick=120_000),
        _Tick(timestamp=-20_000, tick=-10),
        _Tick(timestamp=-20_000, tick=5),
    )

    decoded = s0.decode_provider_tick_interval(
        ticks,
        interval_start=start,
        interval_end=end,
        digits=5,
        has_more=False,
    )

    assert tuple(row.observed_at for row in decoded) == (
        start + timedelta(seconds=10),
        start + timedelta(seconds=30),
        start + timedelta(seconds=50),
    )
    assert tuple(row.price for row in decoded) == (
        Decimal("1.19995"),
        Decimal("1.19990"),
        Decimal("1.20000"),
    )


def test_long_fill_uses_first_ask_tick_at_or_below_level() -> None:
    start = datetime(2025, 1, 2, 10, 0, tzinfo=UTC)
    end = start + timedelta(minutes=1)
    newest = start + timedelta(seconds=50)
    ticks = (
        _Tick(timestamp=_ms(newest), tick=120_000),
        _Tick(timestamp=-20_000, tick=-10),
        _Tick(timestamp=-20_000, tick=15),
    )

    result = s0.resolve_exact_provider_fill(
        side=CapitalizerSide.LONG,
        armed_level=Decimal("1.20000"),
        interval_start=start,
        interval_end=end,
        ticks=ticks,
        digits=5,
        has_more=False,
    )

    assert result.quote_side == "ASK"
    assert result.filled is True
    assert result.fill_at == start + timedelta(seconds=30)
    assert result.fill_price == Decimal("1.19990")
    assert result.fill_at != start


def test_long_fill_first_matching_tick_is_not_m1_open() -> None:
    start = datetime(2025, 1, 2, 10, 0, tzinfo=UTC)
    end = start + timedelta(minutes=1)
    newest = start + timedelta(seconds=50)
    ticks = (
        _Tick(timestamp=_ms(newest), tick=120_010),
        _Tick(timestamp=-20_000, tick=-20),
        _Tick(timestamp=-20_000, tick=15),
    )

    result = s0.resolve_exact_provider_fill(
        side=CapitalizerSide.LONG,
        armed_level=Decimal("1.20000"),
        interval_start=start,
        interval_end=end,
        ticks=ticks,
        digits=5,
        has_more=False,
    )

    assert result.filled is True
    assert result.fill_at == start + timedelta(seconds=30)
    assert result.fill_price == Decimal("1.19990")
    assert result.m1_open_backdating_used is False


def test_short_fill_uses_first_bid_tick_at_or_above_level() -> None:
    start = datetime(2025, 1, 2, 10, 0, tzinfo=UTC)
    end = start + timedelta(minutes=1)
    newest = start + timedelta(seconds=45)
    ticks = (
        _Tick(timestamp=_ms(newest), tick=120_020),
        _Tick(timestamp=-15_000, tick=-5),
        _Tick(timestamp=-15_000, tick=-20),
    )

    result = s0.resolve_exact_provider_fill(
        side=CapitalizerSide.SHORT,
        armed_level=Decimal("1.20000"),
        interval_start=start,
        interval_end=end,
        ticks=ticks,
        digits=5,
        has_more=False,
    )

    assert result.quote_side == "BID"
    assert result.filled is True
    assert result.fill_at == start + timedelta(seconds=30)
    assert result.fill_price == Decimal("1.20015")
    assert result.fill_at != start


def test_no_provider_touch_means_no_fill() -> None:
    start = datetime(2025, 1, 2, 10, 0, tzinfo=UTC)
    end = start + timedelta(minutes=1)
    newest = start + timedelta(seconds=40)
    ticks = (
        _Tick(timestamp=_ms(newest), tick=120_030),
        _Tick(timestamp=-20_000, tick=-10),
    )

    result = s0.resolve_exact_provider_fill(
        side=CapitalizerSide.LONG,
        armed_level=Decimal("1.19900"),
        interval_start=start,
        interval_end=end,
        ticks=ticks,
        digits=5,
        has_more=False,
    )

    assert result.filled is False
    assert result.fill_at is None
    assert result.fill_price is None


def test_incomplete_provider_tick_response_fails_closed() -> None:
    start = datetime(2025, 1, 2, 10, 0, tzinfo=UTC)
    with pytest.raises(ValueError, match="complete tick response"):
        s0.decode_provider_tick_interval(
            (),
            interval_start=start,
            interval_end=start + timedelta(minutes=1),
            digits=5,
            has_more=True,
        )


def test_s0_readiness_stays_pre_economic_and_not_ready_yet() -> None:
    report = s0.build_readiness_report()
    assert report["exact_provider_tick_fill_ready"] is True
    assert report["legacy_m1_open_backdating_allowed"] is False
    assert report["v41_30s_threshold_reused"] is False
    assert report["v41_features_used"] is False
    assert report["strategy_economics_calculated"] is False
    assert report["exit_simulation_run"] is False
    assert report["realized_r_read"] is False
    assert report["fresh_holdout_opened"] is False
    assert report["candidate_count"] == 0
    assert report["trader_certified"] is False
    assert report["blocking_binder_count"] > 0
    assert report["next_phase"] == "CANONICAL_SOURCE_CANDIDATE_ASSEMBLY_GAPS_REMAIN"
