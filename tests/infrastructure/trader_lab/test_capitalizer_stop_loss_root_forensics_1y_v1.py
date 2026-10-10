from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_stop_loss_root_forensics_1y_v1 import (
    DailyExtreme,
    Pivot,
    SessionExtreme,
    TradeForensics,
    _after_stop,
    _before_stop,
    _cohort_metrics,
    _liquidity_class,
)


def test_stop_first_ordering_is_not_optimistic() -> None:
    assert _before_stop(2, 3) is True
    assert _before_stop(3, 3) is False
    assert _before_stop(4, 3) is False
    assert _after_stop(4, 3) is True
    assert _after_stop(3, 3) is False


def test_liquidity_class_prioritizes_previous_day_then_session_then_parent_swings() -> None:
    at = datetime(2026, 1, 5, 12, 0, tzinfo=UTC)
    day = DailyExtreme("2026-01-04", Decimal("110"), Decimal("90"))
    session = SessionExtreme(
        session="LONDON",
        operating_date="2026-01-05",
        opened_at=at - timedelta(hours=4),
        closed_at=at - timedelta(hours=1),
        high=Decimal("108"),
        low=Decimal("92"),
    )
    m15 = (
        Pivot(at - timedelta(hours=2), at - timedelta(hours=1), Decimal("95"), "LOW"),
    )
    m5 = (
        Pivot(at - timedelta(minutes=30), at - timedelta(minutes=20), Decimal("96"), "LOW"),
    )

    label, _ = _liquidity_class(
        swept_price=Decimal("90"),
        raid_at=at,
        side=CapitalizerSide.LONG,
        previous_day=day,
        previous_session=session,
        m5_pivots=m5,
        m15_pivots=m15,
        tolerance=Decimal("0.01"),
    )
    assert label == "PREVIOUS_NY_DAY_EXTREME"

    label, _ = _liquidity_class(
        swept_price=Decimal("92"),
        raid_at=at,
        side=CapitalizerSide.LONG,
        previous_day=day,
        previous_session=session,
        m5_pivots=m5,
        m15_pivots=m15,
        tolerance=Decimal("0.01"),
    )
    assert label == "PRIOR_RESEARCH_SESSION_EXTREME"

    label, _ = _liquidity_class(
        swept_price=Decimal("95"),
        raid_at=at,
        side=CapitalizerSide.LONG,
        previous_day=day,
        previous_session=session,
        m5_pivots=m5,
        m15_pivots=m15,
        tolerance=Decimal("0.01"),
    )
    assert label == "M15_CONFIRMED_SWING"


def _trade(exit_reason: str, realized_r: str) -> TradeForensics:
    return TradeForensics(
        symbol="NAS100",
        session="NEW_YORK",
        operating_date="2026-01-05",
        side="LONG",
        entry_at="2026-01-05T14:00:00+00:00",
        exit_at="2026-01-05T14:10:00+00:00",
        original_exit_reason=exit_reason,
        original_realized_r=realized_r,
        original_planned_reward_r="3",
        entry_price="100",
        original_stop_price="99",
        original_macro_target_price="103",
        ny_entry_hour=9,
        ny_entry_minute=0,
        session_elapsed_minutes=30,
        session_remaining_minutes=420,
        htf_bias_age_minutes=120,
        raid_at="2026-01-05T13:55:00+00:00",
        swept_pivot_price="99.5",
        raid_extreme="99",
        raid_depth_r="0.5",
        raid_close_back_inside=True,
        liquidity_level_class="M15_CONFIRMED_SWING",
        liquidity_level_distance_provider_increments="0",
        displacement_at="2026-01-05T13:58:00+00:00",
        displacement_body_ratio="0.7",
        displacement_range_r="1.2",
        displacement_body_r="0.84",
        displacement_range_vs_prior20_median="1.5",
        displacement_body_vs_prior20_median="1.6",
        mss_level="100.5",
        mss_break_close_r="0.2",
        mss_level_visible_m5=True,
        mss_level_visible_m15=True,
        fvg_low="100",
        fvg_high="100.5",
        fvg_width_r="0.5",
        fvg_entry_depth_fraction="0",
        fvg_far_edge="100",
        m15_parent_state="ALIGNED",
        h1_parent_state="RANGE",
        h4_parent_state="ALIGNED",
        m15_range_position="0.3",
        protected_swing_price="99.4",
        protected_swing_distance_r="0.6",
        nearest_causal_liquidity_price="102",
        nearest_causal_liquidity_type="M15_SWING",
        nearest_causal_liquidity_r="2",
        two_r_price="102",
        nearest_liquidity_before_original_stop=True,
        two_r_before_original_stop=True,
        macro_target_before_original_stop=False,
        nearest_liquidity_after_stop_before_session_end=False,
        two_r_after_stop_before_session_end=False,
        macro_target_after_stop_before_session_end=False,
        original_stop_wick_only_reclaim=False,
        raid_extreme_close_invalidated_before_session_end=True,
        fvg_far_edge_close_invalidated_before_original_stop=False,
        protected_swing_touched_before_original_stop=False,
        protected_swing_close_invalidated_before_original_stop=False,
    )


def test_cohort_metrics_preserve_original_economics() -> None:
    rows = [_trade("TARGET", "3"), _trade("STOP", "-1")]
    report = _cohort_metrics("TEST", rows)
    assert report.trades == 2
    assert report.stops == 1
    assert report.targets == 1
    assert report.total_r == "2"
    assert report.mean_r == "1"
    assert report.profit_factor == "3"
