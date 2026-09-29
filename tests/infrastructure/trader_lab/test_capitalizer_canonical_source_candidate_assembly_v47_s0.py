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
from qore.infrastructure.trader_lab.capitalizer_source_cisd_ftm_v2 import (
    CapitalizerCausalSeriesKind,
    CapitalizerCISDObservation,
    CapitalizerLiquiditySideTaken,
)
from qore.infrastructure.trader_lab.capitalizer_source_daily_bias_v2 import (
    derive_daily_bias,
)
from qore.infrastructure.trader_lab.capitalizer_source_observation_detectors_v2 import (
    CapitalizerProtectedSwingOrigin,
    CapitalizerSourceBar,
    CapitalizerSourceDirection,
    confirm_protected_swing,
    detect_candle2_reversal_closure,
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


def test_s0_readiness_passes_without_opening_economics() -> None:
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
    assert report["canonical_source_context_binding_ready"] is True
    assert report["canonical_prefill_candidate_path_ready"] is True
    assert report["deterministic_route_and_wick_binding_ready"] is True
    assert report["no_chase_execution_area_bound"] is True
    assert report["blocking_binder_count"] == 0
    assert report["blocking_binders"] == ()
    assert report["next_phase"] == (
        "CANONICAL_SOURCE_CANDIDATE_ASSEMBLY_READY_FOR_ISOLATION_REPLAY"
    )


def test_a1_armed_level_prefers_directional_overlap_then_ce() -> None:
    start = datetime(2025, 1, 2, 10, 0, tzinfo=UTC)
    zone = s0.v3_source.M1EntryZone(
        ob_opened_at=start,
        ob_low=Decimal("99"),
        ob_high=Decimal("101"),
        fvg_confirmed_at=start + timedelta(minutes=3),
        fvg_low=Decimal("100"),
        fvg_high=Decimal("102"),
        overlap_low=Decimal("100"),
        overlap_high=Decimal("101"),
    )

    long_primary, long_fallback, long_mode = s0.resolve_s0_armed_levels(
        side=CapitalizerSide.LONG,
        zone=zone,
    )
    short_primary, short_fallback, short_mode = s0.resolve_s0_armed_levels(
        side=CapitalizerSide.SHORT,
        zone=zone,
    )

    assert long_primary == Decimal("101")
    assert long_fallback is None
    assert long_mode == "OB_FVG_RETEST"
    assert short_primary == Decimal("100")
    assert short_fallback == Decimal("101")
    assert short_mode == "OB_FVG_RETEST"


def _source_bar(open_: str, high: str, low: str, close: str) -> CapitalizerSourceBar:
    return CapitalizerSourceBar(
        open=Decimal(open_),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
    )


def _confirmed_cisd(direction: CapitalizerSourceDirection) -> CapitalizerCISDObservation:
    return CapitalizerCISDObservation(
        direction=direction,
        causal_series_kind=(
            CapitalizerCausalSeriesKind.DOWN_CLOSE_SERIES
            if direction is CapitalizerSourceDirection.BULLISH
            else CapitalizerCausalSeriesKind.UP_CLOSE_SERIES
        ),
        causal_series_open=Decimal("100"),
        confirmation_close=(
            Decimal("101")
            if direction is CapitalizerSourceDirection.BULLISH
            else Decimal("99")
        ),
        important_level_reached=True,
        higher_timeframe_closure_confirmed=True,
        structural_confirmed=True,
        setup_confirmed=True,
        reasons=("TEST_SOURCE_CONFIRMED",),
    )


def test_route_wick_resolves_fractal_without_priority_and_fails_closed_on_both() -> None:
    htf = detect_candle2_reversal_closure(
        previous=_source_bar("100", "102", "98", "99"),
        candle2=_source_bar("99", "101", "97", "99.5"),
        point_of_interest_present=True,
    )
    assert htf is not None
    assert htf.direction is CapitalizerSourceDirection.BULLISH
    bias = derive_daily_bias(htf)
    cisd = _confirmed_cisd(CapitalizerSourceDirection.BULLISH)
    protected = confirm_protected_swing(
        direction=CapitalizerSourceDirection.BULLISH,
        swing_price=Decimal("98"),
        origin=CapitalizerProtectedSwingOrigin.LIQUIDITY_SWEEP,
        closure_through_causal_series_confirmed=True,
    )

    reversal = s0.resolve_s0_route_and_wick(
        direction=CapitalizerSourceDirection.BULLISH,
        h1_closure=htf,
        daily_bias=bias,
        m15_cisd=cisd,
        m1_cisd=cisd,
        m1_protected_swing=protected,
        liquidity_side_taken=CapitalizerLiquiditySideTaken.LOW,
    )
    assert reversal.fractal_alignment.confirmed is True
    assert reversal.failure_to_manipulate.confirmed is False
    assert reversal.wick_formation.confirmed is True
    assert reversal.route_resolution.resolved is True
    assert reversal.route_resolution.numeric_score_used is False

    ambiguous = s0.resolve_s0_route_and_wick(
        direction=CapitalizerSourceDirection.BULLISH,
        h1_closure=htf,
        daily_bias=bias,
        m15_cisd=cisd,
        m1_cisd=cisd,
        m1_protected_swing=protected,
        liquidity_side_taken=CapitalizerLiquiditySideTaken.HIGH,
    )
    assert ambiguous.fractal_alignment.confirmed is True
    assert ambiguous.failure_to_manipulate.confirmed is True
    assert ambiguous.route_resolution.resolved is False
    assert ambiguous.route_resolution.route is None
