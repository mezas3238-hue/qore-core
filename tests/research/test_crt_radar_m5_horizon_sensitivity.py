"""Strict negative/positive controls for history-window sensitivity.

Synthetic bars only; never evidence of actual financial market skill.
"""
from __future__ import annotations

import importlib
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from scripts.crt_radar_archived_m5_prescreen import M5
    from scripts.crt_radar_m5_horizon_sensitivity import measure
else:
    # Existing QORE CI launches pytest as a console script, where the
    # non-packaged research scripts directory is not an import root.
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    M5 = importlib.import_module("scripts.crt_radar_archived_m5_prescreen").M5
    measure = importlib.import_module("scripts.crt_radar_m5_horizon_sensitivity").measure

START = datetime(2026, 10, 26, 5, tzinfo=UTC)
M5_DELTA = timedelta(minutes=5)


def h4_group(index: int, high: int, low: int, close: int) -> list[M5]:
    start = START + timedelta(hours=4 * index)
    bars = []
    for j in range(48):
        at = start + j * M5_DELTA
        bars.append(M5(at, close, max(close, low), min(close, high), close))
    # Ensure aggregate C1 and C2 highs/lows come from actual closed M5.
    bars[0] = M5(start, close, high, low, close)
    return bars


def test_synthetic_2c_single_sweep_and_unrelated_3c_not_trade() -> None:
    rows = h4_group(0, 110, 100, 105) + h4_group(1, 109, 98, 104)
    result = measure(rows, "forex")
    assert result["observed_m5"] == 96
    assert result["h4_closed"] == 2
    assert result["eligible_c1"] == 2
    assert result["structural_2c_historical"] == 1
    assert result["structural_3c_followup"] == 0


def test_double_sweep_rejected_and_m5_gap_never_stitched() -> None:
    rows = h4_group(0, 110, 100, 105) + h4_group(1, 111, 98, 105)
    assert measure(rows, "forex")["structural_2c_historical"] == 0
    broken = rows[:60] + rows[61:]
    r = measure(broken, "forex")
    assert r["structural_2c_historical"] == 0
    assert r["h4_internal_gap"] == 1


def test_index_default_c1_differs_from_forex() -> None:
    # 06:00 NY C1 exists for index, but this 06:00 is not a Forex NY C1.
    start = datetime(2026, 10, 26, 10, tzinfo=UTC)
    rows = []
    for i in range(96):
        at = start + i * M5_DELTA
        rows.append(M5(at, 105, 110 if i == 0 else 108,
                       98 if i == 48 else 100, 104))
    assert measure(rows, "index")["structural_2c_historical"] == 1
    assert measure(rows, "forex")["structural_2c_historical"] == 0


def test_empty_no_history_does_not_create_signal() -> None:
    r = measure([], "forex")
    assert r["observed_m5"] == 0
    assert r["structural_2c_historical"] == 0
    assert r["last_c2_close_utc_ms"] is None


def test_bad_family_fails_closed() -> None:
    with pytest.raises(ValueError, match="BAD_FAMILY"):
        measure([], "unknown")
