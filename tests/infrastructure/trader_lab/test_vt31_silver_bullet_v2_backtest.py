from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from qore.infrastructure.trader_lab.vt31_silver_bullet_v2_backtest import (
    run_vt31_silver_bullet_v2_backtest,
)

_NY = ZoneInfo("America/New_York")


def _row(opened_at: datetime, *, high: float, low: float, close: float) -> dict[str, str]:
    opened = opened_at.astimezone(UTC)
    closed = (opened_at + timedelta(minutes=1)).astimezone(UTC)
    open_price = min(max(close, low), high)
    return {
        "period": "M1",
        "opened_at": opened.isoformat(timespec="microseconds"),
        "closed_at": closed.isoformat(timespec="microseconds"),
        "open": str(open_price),
        "high": str(high),
        "low": str(low),
        "close": str(close),
    }


def _reference(day: datetime) -> list[dict[str, str]]:
    start = day.replace(hour=9, minute=0, second=0, microsecond=0)
    rows: list[dict[str, str]] = []
    for minute in range(60):
        rows.append(
            _row(
                start + timedelta(minutes=minute),
                high=110.0 if minute == 10 else 109.0,
                low=100.0 if minute == 20 else 101.0,
                close=105.0,
            )
        )
    return rows


def _short_setup(day: datetime) -> list[dict[str, str]]:
    start = day.replace(hour=10, minute=0, second=0, microsecond=0)
    return [
        _row(start, high=112.0, low=107.0, close=111.0),
        _row(start + timedelta(minutes=1), high=113.0, low=108.0, close=109.0),
        _row(start + timedelta(minutes=2), high=109.5, low=106.0, close=107.0),
        _row(start + timedelta(minutes=3), high=107.0, low=105.0, close=106.0),
    ]


def _payload(day: datetime, tail: list[dict[str, str]]) -> dict[str, object]:
    old = day - timedelta(days=731)
    rows = [
        _row(old.replace(hour=9, minute=0), high=101.0, low=99.0, close=100.0),
        *_reference(day),
        *_short_setup(day),
        *tail,
    ]
    checked_at = datetime.fromisoformat(rows[-1]["closed_at"])
    first_open = datetime.fromisoformat(rows[0]["opened_at"])
    return {
        "schema": "qore.ctrader_demo.vt31_silver_bullet_v2_m1_evidence.v1",
        "environment": "demo",
        "read_only": True,
        "account_is_live": False,
        "trading_permission_verified": True,
        "account_fingerprint": "a" * 64,
        "symbol": {
            "symbol_id": 1,
            "symbol_name": "NAS100",
            "digits": 2,
            "min_volume_units": 100,
            "max_volume_units": 100000,
            "step_volume_units": 100,
        },
        "checked_at": checked_at.isoformat(timespec="microseconds"),
        "requested_opened_at": first_open.isoformat(timespec="microseconds"),
        "required_coverage_days": 730,
        "historical_chunk_days": 14,
        "historical_page_count": 5000,
        "decision_timeframe": "M1",
        "source_authorized_market": "NAS100",
        "requested_lookback_days": 760,
        "software_sha": "b" * 40,
        "coverage": {
            "bar_count": len(rows),
            "first_opened_at": rows[0]["opened_at"],
            "last_closed_at": rows[-1]["closed_at"],
            "span_seconds": int((checked_at - first_open).total_seconds()),
            "observed_gap_count": 1,
            "observed_gap_seconds": 1,
            "maximum_observed_gap_seconds": 1,
            "gap_policy": "test",
        },
        "periods": {"M1": rows},
    }


def _write(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_source_setup_fills_after_decision_and_reaches_opposite_range_target(
    tmp_path: Path,
) -> None:
    day = datetime(2026, 7, 8, tzinfo=_NY)
    start = day.replace(hour=10, minute=4)
    payload = _payload(
        day,
        [
            _row(start, high=108.0, low=107.0, close=107.5),
            _row(start + timedelta(minutes=1), high=108.0, low=99.0, close=101.0),
        ],
    )
    path = tmp_path / "evidence.json"
    _write(path, payload)

    report = run_vt31_silver_bullet_v2_backtest(path)
    result = report.payload()

    assert result["setup_count"] == 1
    assert result["filled_count"] == 1
    assert result["terminal_sample_size"] == 1
    assert result["target_count"] == 1
    assert result["stop_count"] == 0
    assert result["win_rate"] == "1"
    assert result["fill_rate"] == "1"


def test_unfilled_limit_is_cancelled_at_window_end_not_filled_later(tmp_path: Path) -> None:
    day = datetime(2026, 7, 9, tzinfo=_NY)
    start = day.replace(hour=10, minute=4)
    tail = [
        _row(start + timedelta(minutes=minute), high=112.0, low=109.0, close=110.0)
        for minute in range(56)
    ]
    payload = _payload(day, tail)
    path = tmp_path / "evidence.json"
    _write(path, payload)

    result = run_vt31_silver_bullet_v2_backtest(path).payload()

    assert result["setup_count"] == 1
    assert result["filled_count"] == 0
    assert result["unfilled_setup_count"] == 1
    assert result["terminal_sample_size"] == 0


def test_stop_first_convention_is_conservative_when_terminal_levels_share_fill_bar(
    tmp_path: Path,
) -> None:
    day = datetime(2026, 7, 10, tzinfo=_NY)
    start = day.replace(hour=10, minute=4)
    payload = _payload(
        day,
        [_row(start, high=114.0, low=99.0, close=107.5)],
    )
    path = tmp_path / "evidence.json"
    _write(path, payload)

    result = run_vt31_silver_bullet_v2_backtest(path).payload()

    assert result["stop_count"] == 1
    assert result["target_count"] == 0
    assert result["expectancy_r"] == "-1"


def test_eleven_market_matrix_does_not_force_unsupported_markets_to_trade(
    tmp_path: Path,
) -> None:
    day = datetime(2026, 7, 13, tzinfo=_NY)
    start = day.replace(hour=10, minute=4)
    payload = _payload(
        day,
        [
            _row(start, high=108.0, low=107.0, close=107.5),
            _row(start + timedelta(minutes=1), high=108.0, low=99.0, close=101.0),
        ],
    )
    path = tmp_path / "evidence.json"
    _write(path, payload)

    matrix = run_vt31_silver_bullet_v2_backtest(path).payload()["market_matrix"]

    assert isinstance(matrix, list)
    assert len(matrix) == 11
    supported = [item for item in matrix if item["status"] == "source-authorized"]
    unsupported = [
        item for item in matrix if item["status"] == "unsupported-method-market"
    ]
    assert supported == [{"symbol": "NAS100", "status": "source-authorized"}]
    assert len(unsupported) == 10
