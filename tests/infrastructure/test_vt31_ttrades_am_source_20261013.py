"""Adversarial contract tests for a NEW TTrades-inspired AM FVG-only source model.

These fixtures create no broker fills, order ACKs or economic trading PnL.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from scripts.vt31_ttrades_am_source_20261013 import (
    Bar,
    analyze,
    collect_days,
    diagnostic,
    displacement,
    forward_15,
    full_hour,
    fvg,
    single_day,
)


def ts(k: int) -> datetime:
    return datetime(2025, 7, 1, 13, 0, tzinfo=UTC) + timedelta(minutes=k)


def bar(k: int, o=30000., h=30002., low=29998., c=30000.) -> Bar:
    return Bar(ts(k), o, h, low, c)


def day_bars() -> dict[int, list[Bar]]:
    nine = [bar(i) for i in range(60)]
    nine[10] = bar(10, h=30030.)
    nine[20] = bar(20, low=29980.)
    ten = [bar(60+i) for i in range(60)]
    eleven = [bar(120+i) for i in range(16)]
    return {9: nine, 10: ten, 11: eleven}


def positive_fixture():
    z = day_bars()
    z[10][0] = bar(60, o=29985., h=29990., low=29979., c=29987.)
    z[10][1] = bar(61, o=29984., h=30002., low=29984., c=30000.)
    z[10][2] = bar(62, o=30000., h=30005., low=29994., c=30002.)
    return z


def test_synthetic_source_9am_low_sweep_displacement_fvg_opposite_target() -> None:
    z = positive_fixture()
    status, event = single_day("2025-07-01", z)
    assert status == "SOURCE_ONLY_CANDIDATE"
    assert event["side"] == "LONG"
    assert event["h1_9am_high"] == 30030.
    assert event["h1_9am_low"] == 29980.
    assert event["DOL_exact_opposite_9am_H1"] == 30030.
    assert event["sweep_extreme_reference_NOT_BROKER_SL"] == 29979.
    assert event["CE_reference_NOT_LIMIT_FILL"] == 29992.
    assert event["fvg_c3_close"] == ts(63).isoformat()
    assert event["source_only"] is True
    assert forward_15(event, z) is not None


def test_no_sweep_is_no_trade_not_signal() -> None:
    assert single_day("2025-07-01", day_bars()) == ("NO_SWEEP", None)


def test_two_sides_swept_in_same_m1_are_ambiguous_not_backfilled() -> None:
    z = day_bars()
    z[10][0] = bar(60, h=30031., low=29979.)
    assert single_day("2025-07-01", z) == ("DOUBLE_SWEEP_AMBIGUOUS", None)


def test_second_sweep_against_initial_side_before_fvg_is_veto() -> None:
    z = positive_fixture()
    z[10][1] = bar(61, h=30031., low=29984.)
    assert single_day("2025-07-01", z) == ("DOUBLE_SWEEP_AMBIGUOUS", None)


def test_incomplete_prior_hour_and_window_cannot_trade() -> None:
    z = positive_fixture()
    assert full_hour(z[9], 9)
    z[9].pop(20)
    assert single_day("2025-07-01", z) == ("MISSING_REFERENCE_H1", None)
    z = positive_fixture()
    z[10].pop(50)
    assert single_day("2025-07-01", z) == ("MISSING_SB_HOUR", None)


def test_displacement_cannot_use_candle_under_test_in_prior_atr() -> None:
    z = positive_fixture()
    history = z[9] + z[10][:1]
    assert displacement(history, z[10][1], "LONG", 30030., 29980.)
    assert not displacement(history, z[10][0], "SHORT", 30030., 29980.)
    assert not displacement(history[-10:], z[10][1], "LONG", 30030., 29980.)


def test_no_fvg_after_sweep_and_displacement_is_not_a_candidate() -> None:
    z = positive_fixture()
    z[10][2] = bar(62, low=29985.)
    assert single_day("2025-07-01", z)[0] != "SOURCE_ONLY_CANDIDATE"


def test_fvg_geometry_contiguity_not_lookahead() -> None:
    z = positive_fixture()
    assert fvg(z[10][0], z[10][1], z[10][2], "LONG") == (29990., 29994.)
    assert fvg(z[10][0], z[10][1], z[10][2], "SHORT") is None
    far = bar(70)
    assert fvg(z[10][0], z[10][1], far, "LONG") is None


def test_post_fvg_15m_missing_m1_is_not_interpolated() -> None:
    z = positive_fixture()
    _, e = single_day("2025-07-01", z)
    assert e is not None
    assert forward_15(e, z) is not None
    z[10].pop(10)
    assert forward_15(e, z) is None


def test_market_rejects_out_of_order_and_non_m1() -> None:
    row = {
        "opened_at": ts(1).isoformat(),
        "closed_at": ts(2).isoformat(),
        "open": "30000", "high": "30002", "low": "29998", "close": "30000",
    }
    with pytest.raises(ValueError, match="out-of-order"):
        collect_days([row, row], expected_m1=2)
    with pytest.raises(ValueError, match="M1 count mismatch"):
        collect_days([row], expected_m1=2)


def test_missing_prices_no_fabricated_edge_or_pf() -> None:
    r = diagnostic([])
    assert r["mean_gross_pts"] is None
    assert r["testable_samples"] is False
    z = analyze({"2025-07-01": positive_fixture()})
    assert z["source_candidates"] == 1
    assert z["quotes_bid_ask_and_order_ACK_count"] == 0
    assert z["economic_PF_drawdown_sharpe"] is None
    assert z["no_LIVE_or_order_authority"] is True
    assert z["historical_development_not_independent_holdout"] is True
    assert z["decision"] == "NO_GO_ECONOMIC_CERTIFICATION"
