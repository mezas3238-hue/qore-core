"""QORE Alpha2 synthetic gross execution reference tests; no real PnL."""
from datetime import UTC, datetime

import pytest

from qore.research.alpha2_g1a_native_m5_gross import arm, validate_one_signal
from qore.research.alpha2_intermarket import H4, M5, Bar


def synthetic_bars():
    start = datetime(2020, 1, 2, 8, 5, tzinfo=UTC)
    return start, {start + k * M5: Bar(start + k * M5, 100.0, 100.2, 99.8, 100.0)
                   for k in range(145)}


def test_target_from_exact_first_future_m5_and_same_holding_horizon():
    start, bars = synthetic_bars()
    bars[start] = Bar(start, 100, 103, 99.5, 102)
    out = arm(m5=bars, entry_at=start, expire_at=start + M5 * 144,
              distance=1.0, direction=1)
    assert out["gross_R"] == 2.0
    assert out["reason"] == "TARGET_REFERENCE"
    assert out["gross_bps"] == pytest.approx(200.0)


def test_same_m5_stop_and_target_conservatively_stop_first():
    start, bars = synthetic_bars()
    bars[start] = Bar(start, 100.0, 104.0, 98.0, 100.0)
    out = arm(m5=bars, entry_at=start, expire_at=start + M5 * 144,
              distance=1, direction=1)
    assert out["gross_R"] == -1.0
    assert out["reason"] == "DOUBLE_TOUCH_STOP_FIRST"
    assert out["same_M5_stop_target_collision"] is True


def test_gap_through_stop_executes_at_adverse_open_not_at_stop():
    start, bars = synthetic_bars()
    bars[start + M5] = Bar(start + M5, 97.0, 98.0, 96.0, 97.0)
    out = arm(m5=bars, entry_at=start, expire_at=start + M5 * 144,
              distance=1, direction=1)
    assert out["gross_R"] == -3.0
    assert out["reason"] == "ADVERSE_GAP_STOP_AT_OPEN"


def test_no_replay_across_missing_m5_until_expiry():
    start, bars = synthetic_bars()
    bars.pop(start + M5 * 5)
    out = arm(m5=bars, entry_at=start, expire_at=start + M5 * 144,
              distance=2, direction=1)
    assert out["status"] == "PATH_GAP_CENSORED"


def test_expiry_uses_exact_available_open_not_lookahead_close():
    start, bars = synthetic_bars()
    expiry = start + 144 * M5
    bars[expiry] = Bar(expiry, 100.8, 101.8, 99.8, 101.2)
    out = arm(m5=bars, entry_at=start, expire_at=expiry,
              distance=2, direction=1)
    assert out["reason"] == "EXPIRE_NATIVE_M5_OPEN"
    assert out["gross_R"] == pytest.approx(0.4)


def test_missing_entry_or_expiry_fails_closed():
    start, bars = synthetic_bars()
    assert arm(m5={}, entry_at=start, expire_at=start + 144 * M5,
               distance=2, direction=1)["status"] == "NO_ENTRY_NATIVE_M5"
    bars.pop(start + 144 * M5)
    assert arm(m5=bars, entry_at=start, expire_at=start + 144 * M5,
               distance=2, direction=1)["status"] == "EXPIRY_OPEN_MISSING"


def test_short_direction_target_and_gap():
    start, bars = synthetic_bars()
    bars[start] = Bar(start, 100, 100.5, 97, 99)
    out = arm(m5=bars, entry_at=start, expire_at=start + 144 * M5,
              distance=1, direction=-1)
    assert out["gross_R"] == 2
    assert out["target_reference"] == 98


def test_signal_identity_first_online_and_nonzero_stop_enforced():
    start, _ = synthetic_bars()
    signal = {
        "symbol": "EURUSD",
        "bar_start_utc": (start - H4 - M5).isoformat(),
        "decision_utc": (start - M5).isoformat(),
        "earliest_entry_utc": start.isoformat(),
        "latest_exit_utc": (start + 144 * M5).isoformat(),
        "stop_distance_price": 1.25,
        "direction": 1, "baseline_direction": -1,
        "classification": "RESEARCH_SIGNAL_NOT_TRADE",
        "execution_status": "BLOCKED_NO_BID_ASK_NEWS_PIT_OR_FILL",
    }
    assert validate_one_signal(signal)[2] == 1.25
    signal["stop_distance_price"] = 0
    with pytest.raises(ValueError, match="drift"):
        validate_one_signal(signal)
    signal["stop_distance_price"] = 1.25
    signal["earliest_entry_utc"] = (start - M5).isoformat()
    with pytest.raises(ValueError, match="drift"):
        validate_one_signal(signal)
