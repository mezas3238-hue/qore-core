"""Adversarial tests for all four *source-only* AM entry families."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from scripts.vt31_ttrades_am_all_entry_sources_20261013 import (
    FAMILIES,
    analyze,
    context,
    emit_day,
    find_pivot,
    forward_15,
)
from scripts.vt31_ttrades_am_source_20261013 import Bar


T = datetime(2025, 7, 1, 13, tzinfo=UTC)


def b(k, o=30000., h=30002., lo=29998., c=30000.) -> Bar:
    return Bar(T + timedelta(minutes=k), o, h, lo, c)


def hours(side="LONG") -> dict[int, list[Bar]]:
    nine = [b(k) for k in range(60)]
    nine[10] = b(10, h=30030.)
    nine[20] = b(20, lo=29980.)
    nine[50] = b(50, lo=29995., h=30001.)
    nine[49] = b(49, lo=29998., h=30002.)
    nine[51] = b(51, lo=29998., h=30002.)
    # For shorts, supply a late, causally confirmed local swing high.
    nine[52] = b(52, h=30005.)
    ten = [b(60+i) for i in range(60)]
    if side == "LONG":
        ten[0] = b(60, o=29989., h=29990., lo=29979., c=29987.)
        ten[1] = b(61, o=29984., h=30006., lo=29984., c=30004.)
        ten[2] = b(62, o=30000., h=30008., lo=29995., c=30007.)
        # OB body midpoint 29988 and breaker level 29995 retested AFTER disp.
        ten[3] = b(63, o=30006., h=30009., lo=29987., c=30002.)
    else:
        ten[0] = b(60, o=30015., h=30031., lo=30011., c=30017.)
        ten[1] = b(61, o=30020., h=30020., lo=29990., c=29993.)
        ten[2] = b(62, o=29994., h=30005., lo=29988., c=29991.)
        ten[3] = b(63, o=29990., h=30017., lo=29987., c=29994.)
    return {
        9: nine, 10: ten,
        11: [b(120+i) for i in range(16)],
    }


def test_all_four_long_families_from_real_closed_bar_order() -> None:
    source = hours()
    status, signals, reasons = emit_day("2025-07-01", source)
    assert status == "CONTEXT_CONFIRMED"
    assert set(signals) == set(FAMILIES)
    assert all(reasons[x] == "SOURCE_ONLY_CANDIDATE" for x in FAMILIES)
    assert signals["DISPLACEMENT_DIRECT"]["confirmed_at"] == (
        T + timedelta(minutes=62)
    ).isoformat()
    assert signals["FVG_3M1"]["zone_low_high"] == [29990., 29995.]
    assert signals["FVG_3M1"]["confirmed_at"] == (
        T + timedelta(minutes=63)
    ).isoformat()
    assert signals["ORDER_BLOCK_RETEST"]["reference_price_NOT_FILL"] == 29988.
    assert signals["BREAKER_RETEST"]["reference_price_NOT_FILL"] == 29995.
    assert signals["ORDER_BLOCK_RETEST"]["confirmed_at"] == (
        T + timedelta(minutes=64)
    ).isoformat()
    assert all(e["source_only_NO_EXECUTION"] for e in signals.values())


def test_all_four_short_side_definitions() -> None:
    _, signals, _ = emit_day("2025-07-01", hours("SHORT"))
    assert set(signals) == set(FAMILIES)
    assert all(e["side"] == "SHORT" for e in signals.values())
    assert all(e["DOL_opposite_9am_H1"] == 29980 for e in signals.values())
    assert signals["FVG_3M1"]["zone_low_high"] == [30005., 30011.]


def test_no_9am_60_candles_and_no_10am_60_candles_fail() -> None:
    z = hours()
    z[9].pop(22)
    status, signals, _ = emit_day("2025-07-01", z)
    assert status == "MISSING_REFERENCE_H1" and not signals
    z = hours()
    z[10].pop(22)
    status, signals, _ = emit_day("2025-07-01", z)
    assert status == "MISSING_SB_HOUR" and not signals


def test_double_sweep_same_m1_is_not_directionally_ranked() -> None:
    z = hours()
    z[10][0] = b(60, h=30031., lo=29979.)
    status, signals, _ = emit_day("2025-07-01", z)
    assert status == "DOUBLE_SWEEP_AMBIGUOUS" and not signals


def test_opposite_raid_before_displacement_vetoes_day() -> None:
    z = hours()
    z[10][1] = b(61, h=30031., lo=29984., o=30003., c=30004.)
    status, signals, _ = emit_day("2025-07-01", z)
    assert status == "DOUBLE_SWEEP_BEFORE_DISPLACEMENT" and not signals


def test_post_reversal_ob_and_breaker_cannot_backdate_retests() -> None:
    z = hours()
    z[10][3] = b(63, o=30002., h=30009., lo=30001., c=30007.)
    _, signals, _ = emit_day("2025-07-01", z)
    assert "DISPLACEMENT_DIRECT" in signals
    assert "FVG_3M1" in signals
    assert "ORDER_BLOCK_RETEST" not in signals
    assert "BREAKER_RETEST" not in signals


def test_breaker_swing_requires_right_candle_closed_before_sweep() -> None:
    z = hours()
    assert find_pivot(z[9], "LONG") is not None
    # A monotone high/low prior hour has no confirmed strict local lows:
    z[9] = [
        b(i, o=30000+i*0.5, h=30002+i*0.5,
          lo=29998+i*0.5, c=30000+i*0.5)
        for i in range(60)
    ]
    assert find_pivot(z[9], "LONG") is None
    assert context(z[9], z[10])[0] in (
        "CONTEXT_CONFIRMED", "NO_SWEEP", "NO_DISPLACEMENT_IN_RANGE",
    )


def test_retest_m1_with_stop_or_target_is_ambiguous_not_a_fill() -> None:
    z = hours()
    z[10][3] = b(63, o=30006., h=30031., lo=29978., c=30002.)
    _, signals, _ = emit_day("2025-07-01", z)
    # Same M1 can touch reference and stop/target, but cannot certify an order.
    assert "DISPLACEMENT_DIRECT" in signals
    assert signals["DISPLACEMENT_DIRECT"]["source_only_NO_EXECUTION"]


def test_forward_return_uses_after_close_only_and_never_reference_price() -> None:
    z = hours()
    _, signals, _ = emit_day("2025-07-01", z)
    x = signals["DISPLACEMENT_DIRECT"]
    value = forward_15(x, z)
    assert value is not None
    z[10].pop(15)
    assert forward_15(x, z) is None


def test_no_economic_claim_and_all_families_always_accounted() -> None:
    r = analyze({"2025-07-01": hours()})
    assert r["source_days_ny"] == 1
    assert r["days_with_at_least_one_family"] == 1
    assert all(
        r["family_source_counts"][name]["SOURCE_ONLY_CANDIDATE"] == 1
        for name in FAMILIES
    )
    assert r["broker_quotes_order_ack"] == 0
    assert r["economic_pf_dd_sharpe"] is None
    assert r["economic_edge"] == "NOT_IDENTIFIED"
    assert r["fresh_holdout_opened"] is False
    assert r["multiple_families_same_day_are_not_multiple_trades"] is True


def test_no_source_data_may_be_treated_as_valid_evidence() -> None:
    with pytest.raises(ValueError, match="M1 day"):
        analyze({})
