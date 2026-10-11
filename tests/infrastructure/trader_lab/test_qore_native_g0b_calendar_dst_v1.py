"""Tests G0B: DST, exact-minute pairing, witness integrity, no artificial fill."""
import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest

from qore.infrastructure.trader_lab.qore_native_g0b_calendar_dst_v1 import (
    SOURCE_RUN,
    UNIVERSE,
    WINDOWS,
    audit,
    bucket_stats,
    load_bitmaps,
    mask_contains,
    utc_candidate_minutes,
)


def _make_source(root: Path, day: str = "2026-03-09") -> None:
    for symbol in UNIVERSE:
        # A single naturally incomplete day; all other dates remain absent.
        bits = (1 << (14 * 60 + 30)) | (1 << (14 * 60 + 31))
        raw = {
            "identity": "QORE_NATIVE_G0_NINE_MARKET_M1_SOURCE_AUDIT_V1",
            "symbol": symbol,
            "days": {day: format(bits, "0360x")},
            "minutes_by_day": {day: 2},
        }
        (root / f"qore-native-G0-{symbol}-minute-bitmaps.json").write_text(
            json.dumps(raw), encoding="utf-8"
        )


def test_dst_new_york_spring_shift() -> None:
    spec = WINDOWS["DRIVE_NY_AM"]
    before = utc_candidate_minutes(date(2026, 3, 6), spec)
    after = utc_candidate_minutes(date(2026, 3, 9), spec)
    assert len(before) == len(after) == 90
    assert before[0] == datetime(2026, 3, 6, 14, 30, tzinfo=UTC)
    assert after[0] == datetime(2026, 3, 9, 13, 30, tzinfo=UTC)
    assert utc_candidate_minutes(date(2026, 3, 8), spec) == []


def test_dst_london_spring_shift() -> None:
    spec = WINDOWS["RESET_LDN_FIX_CONTEXT"]
    before = utc_candidate_minutes(date(2026, 3, 27), spec)
    after = utc_candidate_minutes(date(2026, 3, 30), spec)
    assert len(before) == len(after) == 30
    assert before[15] == datetime(2026, 3, 27, 16, 0, tzinfo=UTC)
    assert after[15] == datetime(2026, 3, 30, 15, 0, tzinfo=UTC)


def test_minute_bit_exact_utc_and_no_fill() -> None:
    minute = datetime(2026, 3, 9, 13, 30, tzinfo=UTC)
    key = minute.date().isoformat()
    bit = 1 << (13 * 60 + 30)
    assert mask_contains({key: bit}, minute)
    assert not mask_contains({key: bit}, minute + timedelta(minutes=1))
    assert not mask_contains({}, minute)


def test_bucket_stats_only_whole_completed_contained_bars() -> None:
    first = datetime(2026, 3, 9, 13, 30, tzinfo=UTC)
    scheduled = [first + timedelta(minutes=i) for i in range(15)]
    bits = sum(1 << (m.hour * 60 + m.minute) for m in scheduled)
    masks = {first.date().isoformat(): bits}
    assert bucket_stats(scheduled, masks, 15) == {
        "fully_contained_buckets": 1, "complete_buckets": 1, "incomplete_buckets": 0}
    assert bucket_stats(scheduled[:-1], masks, 15)["fully_contained_buckets"] == 0
    assert bucket_stats(scheduled, masks, 60)["fully_contained_buckets"] == 0
    masks[first.date().isoformat()] &= ~(1 << (13 * 60 + 32))
    assert bucket_stats(scheduled, masks, 15)["incomplete_buckets"] == 1


def test_invalid_bit_count_rejected(tmp_path: Path) -> None:
    _make_source(tmp_path)
    path = tmp_path / "qore-native-G0-EURUSD-minute-bitmaps.json"
    obj = json.loads(path.read_text())
    obj["minutes_by_day"]["2026-03-09"] = 3
    path.write_text(json.dumps(obj))
    with pytest.raises(ValueError, match="bit count witness disagreement"):
        load_bitmaps(tmp_path)


def test_nine_source_audit_stays_non_economic(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    _make_source(source)
    masks, sha = load_bitmaps(source)
    assert set(masks) == set(UNIVERSE)
    assert len(sha) == len(UNIVERSE)
    result = audit(source, tmp_path / "out")
    assert result["G0_source_run"] == SOURCE_RUN
    assert result["future_returns_or_PnL_measured"] is False
    assert result["live_authorized"] is False
    assert result["provider_broker_calendar_verified"] is False
    assert set(result["windows"]) == set(WINDOWS)
    drive = result["windows"]["DRIVE_NY_AM"]["symbols"]["NAS100"]
    assert drive["nominal_weekdays"] > 200
    assert drive["fully_observed_days"] == 0
    assert drive["status"] == "SOURCE_PARTIAL_PROVIDER_UNVERIFIED"
    relative = result["windows"]["RELATIVE_LDN_AM"]["pairs"]["EURUSD|GBPUSD"]
    assert relative["observed_minutes"] >= 0
    assert relative["never_forward_filled"]
    assert (tmp_path/"out"/"qore-native-G0B-per-day-window-census.csv").exists()
