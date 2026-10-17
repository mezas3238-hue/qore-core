"""No-lookahead and overlapping-window guards for N2 CRT casebook."""

from datetime import UTC, datetime, timedelta

import pytest

from qore.infrastructure.trader_lab.vt08_crt_pure_n2_57_casebook import (
    forensic_casebook_57,
    interval_overlap,
    micro_target_context,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2_model1_reference_lab import M15Bar
from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket

BASE = datetime(2026, 1, 12, 10, 0, tzinfo=UTC)


def bar(index: int, hi: int, low: int, close: int) -> M15Bar:
    return M15Bar(
        opened_at=BASE + timedelta(minutes=15 * index),
        open_price=100, high_price=hi, low_price=low, close_price=close
    )


def test_overlapping_micro_triplets_are_detected() -> None:
    assert interval_overlap(
        BASE, BASE + timedelta(minutes=45),
        BASE + timedelta(minutes=15), BASE + timedelta(minutes=60),
    )


def test_touching_endpoints_are_not_overlap() -> None:
    assert not interval_overlap(
        BASE, BASE + timedelta(minutes=45),
        BASE + timedelta(minutes=45), BASE + timedelta(minutes=90),
    )


def test_invalid_interval_refused() -> None:
    with pytest.raises(ValueError, match="invalid micro-event interval"):
        interval_overlap(BASE, BASE, BASE, BASE + timedelta(minutes=15))


def test_bullish_midpoint_already_consumed_but_far_high_can_remain() -> None:
    result = micro_target_context(
        bullish=True, own_high=110, own_low=90,
        micro_c1=bar(0, 110, 90, 100),
        micro_c2=bar(1, 105, 85, 95),
        micro_c3=bar(2, 109, 93, 104),
        next_open=104, parent_high=120, parent_low=80,
    )
    assert result["own_micro_midpoint_already_closed_through"]
    assert not result["own_far_boundary_touched_by_micro_c3_wick"]
    assert not result["own_far_boundary_already_closed_through"]
    assert result["own_far_boundary_ahead_at_next_open"]
    assert result["micro_c1_range_inside_parent_h4_c1"]


def test_bullish_far_high_touched_intrabar_even_if_close_below() -> None:
    result = micro_target_context(
        bullish=True, own_high=110, own_low=90,
        micro_c1=bar(0, 110, 90, 100),
        micro_c2=bar(1, 105, 85, 95),
        micro_c3=bar(2, 112, 93, 104),
        next_open=103, parent_high=120, parent_low=80,
    )
    assert result["own_far_boundary_touched_by_micro_c3_wick"]
    assert not result["own_far_boundary_already_closed_through"]
    assert result["own_far_boundary_ahead_at_next_open"]


def test_bullish_far_high_not_ahead_after_next_open_gaps() -> None:
    result = micro_target_context(
        bullish=True, own_high=110, own_low=90,
        micro_c1=bar(0, 110, 90, 100),
        micro_c2=bar(1, 105, 85, 95),
        micro_c3=bar(2, 112, 93, 111),
        next_open=111, parent_high=120, parent_low=80,
    )
    assert result["own_far_boundary_already_closed_through"]
    assert result["own_far_boundary_not_ahead_at_next_open"]
    assert not result["own_far_boundary_ahead_at_next_open"]


def test_bearish_dol_low_remains_when_c3_and_next_open_above() -> None:
    result = micro_target_context(
        bullish=False, own_high=110, own_low=90,
        micro_c1=bar(0, 110, 90, 100),
        micro_c2=bar(1, 115, 94, 105),
        micro_c3=bar(2, 103, 92, 95),
        next_open=96, parent_high=120, parent_low=80,
    )
    assert result["own_micro_midpoint_already_closed_through"]
    assert not result["own_far_boundary_touched_by_micro_c3_wick"]
    assert result["own_far_boundary_ahead_at_next_open"]


def test_micro_confirmation_at_exact_midpoint_rejected_as_unconfirmed() -> None:
    with pytest.raises(ValueError, match="unconfirmed micro"):
        micro_target_context(
            bullish=True, own_high=110, own_low=90,
            micro_c1=bar(0, 110, 90, 100),
            micro_c2=bar(1, 105, 85, 95),
            micro_c3=bar(2, 110, 90, 100),
            next_open=102, parent_high=120, parent_low=80,
        )


def test_invalid_micro_range_refused() -> None:
    with pytest.raises(ValueError, match="range nonpositive"):
        micro_target_context(
            bullish=True, own_high=90, own_low=90,
            micro_c1=bar(0, 90, 90, 90),
            micro_c2=bar(1, 91, 80, 90),
            micro_c3=bar(2, 95, 80, 92),
            next_open=93, parent_high=120, parent_low=80,
        )


def test_parent_side_sweep_and_close_alerts_have_distinct_semantics() -> None:
    result = micro_target_context(
        bullish=True, own_high=110, own_low=90,
        micro_c1=bar(0, 110, 90, 100),
        micro_c2=bar(1, 108, 74, 93),
        micro_c3=bar(2, 109, 82, 104),
        next_open=104, parent_high=120, parent_low=80,
    )
    assert result["micro_c2_swept_original_h4_c1_side"]
    assert not result["micro_c3_close_against_h4_original_thesis"]


def test_btcusd_frozen_before_any_casebook_market_access() -> None:
    with pytest.raises(ValueError, match="BTCUSD frozen"):
        forensic_casebook_57(CrtPureMarket.BTCUSD, ())
