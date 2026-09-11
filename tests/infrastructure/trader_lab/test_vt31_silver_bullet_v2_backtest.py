from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import cast
from zoneinfo import ZoneInfo

from qore.infrastructure.trader_lab.vt31_silver_bullet_v2_backtest import (
    run_vt31_silver_bullet_v2_backtest,
)

_NY = ZoneInfo("America/New_York")


def _row(
    opened_at: datetime,
    *,
    open_price: float,
    high: float,
    low: float,
    close: float,
) -> dict[str, str]:
    opened = opened_at.astimezone(UTC)
    closed = (opened_at + timedelta(minutes=1)).astimezone(UTC)
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
                open_price=105.0,
                high=110.0 if minute == 10 else 109.0,
                low=100.0 if minute == 20 else 101.0,
                close=105.0,
            )
        )
    return rows


def _short_setup(day: datetime, *, start_minute: int = 0) -> list[dict[str, str]]:
    start = day.replace(hour=10, minute=start_minute, second=0, microsecond=0)
    return [
        _row(start, open_price=109.5, high=111.0, low=108.8, close=109.0),
        _row(
            start + timedelta(minutes=1),
            open_price=109.0,
            high=109.2,
            low=108.0,
            close=108.5,
        ),
        _row(
            start + timedelta(minutes=2),
            open_price=108.5,
            high=108.7,
            low=107.8,
            close=108.0,
        ),
    ]


def _neutral(day: datetime, start_minute: int, end_minute: int) -> list[dict[str, str]]:
    start = day.replace(hour=10, minute=0, second=0, microsecond=0)
    return [
        _row(
            start + timedelta(minutes=minute),
            open_price=105.0,
            high=106.0,
            low=104.0,
            close=105.0,
        )
        for minute in range(start_minute, end_minute)
    ]


def _payload(
    day: datetime,
    session: list[dict[str, str]],
    tail: list[dict[str, str]],
) -> dict[str, object]:
    old = day - timedelta(days=731)
    rows = [
        _row(
            old.replace(hour=9, minute=0),
            open_price=100.0,
            high=101.0,
            low=99.0,
            close=100.0,
        ),
        *_reference(day),
        *session,
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
        "provider_symbol_name": "USTEC",
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


def _first_trade(result: dict[str, object]) -> dict[str, object]:
    trades = cast(list[object], result["trades"])
    return cast(dict[str, object], trades[0])


def test_video_like_winner_fills_limit_after_decision_and_hits_opposite_range_target(
    tmp_path: Path,
) -> None:
    day = datetime(2026, 7, 8, tzinfo=_NY)
    start = day.replace(hour=10, minute=3)
    payload = _payload(
        day,
        _short_setup(day),
        [
            _row(start, open_price=108.9, high=109.0, low=108.7, close=108.8),
            _row(
                start + timedelta(minutes=1),
                open_price=108.0,
                high=108.2,
                low=99.0,
                close=101.0,
            ),
        ],
    )
    path = tmp_path / "evidence.json"
    _write(path, payload)

    result = run_vt31_silver_bullet_v2_backtest(path).payload()

    assert result["symbol"] == "NAS100"
    assert result["setup_count"] == 1
    assert result["filled_count"] == 1
    assert result["target_count"] == 1
    assert result["stop_count"] == 0
    assert result["breakeven_count"] == 0
    assert result["win_rate"] == "1"
    assert result["position_management"] == "source-3r-to-breakeven-v1"


def test_video_like_loser_remains_valid_and_initial_stop_wins(tmp_path: Path) -> None:
    day = datetime(2026, 7, 9, tzinfo=_NY)
    start = day.replace(hour=10, minute=3)
    payload = _payload(
        day,
        _short_setup(day),
        [
            _row(start, open_price=108.9, high=109.0, low=108.7, close=108.8),
            _row(
                start + timedelta(minutes=1),
                open_price=109.0,
                high=112.0,
                low=108.0,
                close=111.0,
            ),
        ],
    )
    path = tmp_path / "evidence.json"
    _write(path, payload)

    result = run_vt31_silver_bullet_v2_backtest(path).payload()

    assert result["filled_count"] == 1
    assert result["stop_count"] == 1
    assert result["target_count"] == 0
    assert result["expectancy_r"] == "-1"


def test_three_r_arms_break_even_only_after_closed_bar_then_be_can_exit(
    tmp_path: Path,
) -> None:
    day = datetime(2026, 7, 10, tzinfo=_NY)
    start = day.replace(hour=10, minute=3)
    payload = _payload(
        day,
        _short_setup(day),
        [
            _row(start, open_price=108.9, high=109.0, low=108.7, close=108.8),
            _row(
                start + timedelta(minutes=1),
                open_price=107.0,
                high=108.0,
                low=101.9,
                close=102.5,
            ),
            _row(
                start + timedelta(minutes=2),
                open_price=103.0,
                high=109.0,
                low=102.5,
                close=108.0,
            ),
        ],
    )
    path = tmp_path / "evidence.json"
    _write(path, payload)

    result = run_vt31_silver_bullet_v2_backtest(path).payload()
    trade = _first_trade(result)

    assert result["breakeven_count"] == 1
    assert result["stop_count"] == 0
    assert trade["outcome"] == "breakeven"
    assert trade["r_multiple"] == "0"
    assert trade["breakeven_armed_at"] is not None
    assert trade["exit_price"] == trade["entry_price"]


def test_stop_wins_if_stop_and_three_r_or_target_share_same_pre_be_bar(
    tmp_path: Path,
) -> None:
    day = datetime(2026, 7, 13, tzinfo=_NY)
    start = day.replace(hour=10, minute=3)
    payload = _payload(
        day,
        _short_setup(day),
        [
            _row(
                start,
                open_price=108.9,
                high=112.0,
                low=99.0,
                close=108.0,
            )
        ],
    )
    path = tmp_path / "evidence.json"
    _write(path, payload)

    result = run_vt31_silver_bullet_v2_backtest(path).payload()

    assert result["stop_count"] == 1
    assert result["target_count"] == 0
    assert result["breakeven_count"] == 0


def test_unfilled_limit_is_cancelled_at_11_not_filled_later(tmp_path: Path) -> None:
    day = datetime(2026, 7, 14, tzinfo=_NY)
    start = day.replace(hour=10, minute=3)
    tail = [
        _row(
            start + timedelta(minutes=minute),
            open_price=109.5,
            high=110.0,
            low=109.0,
            close=109.5,
        )
        for minute in range(57)
    ]
    tail.append(
        _row(
            day.replace(hour=11, minute=0),
            open_price=108.8,
            high=109.0,
            low=108.0,
            close=108.5,
        )
    )
    payload = _payload(day, _short_setup(day), tail)
    path = tmp_path / "evidence.json"
    _write(path, payload)

    result = run_vt31_silver_bullet_v2_backtest(path).payload()

    assert result["setup_count"] == 1
    assert result["filled_count"] == 0
    assert result["unfilled_setup_count"] == 1


def test_filled_position_is_not_closed_at_11_and_can_hit_target_after_window(
    tmp_path: Path,
) -> None:
    day = datetime(2026, 7, 15, tzinfo=_NY)
    start = day.replace(hour=10, minute=3)
    tail = [
        _row(start, open_price=108.9, high=109.0, low=108.7, close=108.8),
    ]
    tail.extend(
        _row(
            day.replace(hour=10, minute=minute),
            open_price=106.0,
            high=108.0,
            low=101.5,
            close=105.0,
        )
        for minute in range(4, 60)
    )
    tail.append(
        _row(
            day.replace(hour=11, minute=0),
            open_price=101.5,
            high=102.0,
            low=99.0,
            close=100.5,
        )
    )
    payload = _payload(day, _short_setup(day), tail)
    path = tmp_path / "evidence.json"
    _write(path, payload)

    result = run_vt31_silver_bullet_v2_backtest(path).payload()
    trade = _first_trade(result)

    assert result["target_count"] == 1
    resolved_at = cast(str, trade["resolved_at"])
    assert datetime.fromisoformat(resolved_at).astimezone(_NY).hour == 11


def test_signal_completed_at_1059_can_fill_in_last_admissible_minute(
    tmp_path: Path,
) -> None:
    day = datetime(2026, 7, 16, tzinfo=_NY)
    session = [*_neutral(day, 0, 56), *_short_setup(day, start_minute=56)]
    fill = _row(
        day.replace(hour=10, minute=59),
        open_price=108.9,
        high=109.0,
        low=108.7,
        close=108.8,
    )
    after = _row(
        day.replace(hour=11, minute=0),
        open_price=108.0,
        high=108.0,
        low=99.0,
        close=101.0,
    )
    payload = _payload(day, session, [fill, after])
    path = tmp_path / "evidence.json"
    _write(path, payload)

    result = run_vt31_silver_bullet_v2_backtest(path).payload()
    trade = _first_trade(result)

    assert result["filled_count"] == 1
    fill_open = datetime.fromisoformat(
        cast(str, trade["fill_interval_opened_at"])
    ).astimezone(_NY)
    fill_close = datetime.fromisoformat(
        cast(str, trade["fill_interval_closed_at"])
    ).astimezone(_NY)
    assert (fill_open.hour, fill_open.minute) == (10, 59)
    assert (fill_close.hour, fill_close.minute) == (11, 0)
    assert trade["fill_time_precision"] == "M1-half-open-interval"
    signal_at = datetime.fromisoformat(cast(str, trade["signal_at"])).astimezone(_NY)
    assert signal_at.minute == 59


def test_backtester_retains_only_one_fill_per_instrument_session(tmp_path: Path) -> None:
    day = datetime(2026, 7, 17, tzinfo=_NY)
    start = day.replace(hour=10, minute=3)
    first_fill_and_stop = [
        _row(start, open_price=108.9, high=109.0, low=108.7, close=108.8),
        _row(
            start + timedelta(minutes=1),
            open_price=109.0,
            high=112.0,
            low=108.0,
            close=111.0,
        ),
    ]
    second_pattern = _short_setup(day, start_minute=20)
    payload = _payload(day, _short_setup(day), [*first_fill_and_stop, *second_pattern])
    path = tmp_path / "evidence.json"
    _write(path, payload)

    result = run_vt31_silver_bullet_v2_backtest(path).payload()

    assert result["setup_count"] == 1
    assert result["filled_count"] == 1
    assert result["one_fill_per_session"] is True


def test_abstention_reason_counts_are_retained_for_auditing(tmp_path: Path) -> None:
    day = datetime(2026, 7, 20, tzinfo=_NY)
    session = _neutral(day, 0, 5)
    payload = _payload(day, session, [])
    path = tmp_path / "evidence.json"
    _write(path, payload)

    result = run_vt31_silver_bullet_v2_backtest(path).payload()
    abstain_counts = cast(dict[str, int], result["abstain_evaluation_counts"])
    session_counts = cast(dict[str, int], result["session_abstain_counts"])

    assert result["setup_count"] == 0
    assert abstain_counts["no-raid"] >= 1
    assert session_counts["no-raid"] == 1


def test_provider_alias_never_changes_canonical_nas100_identity(tmp_path: Path) -> None:
    day = datetime(2026, 7, 21, tzinfo=_NY)
    start = day.replace(hour=10, minute=3)
    payload = _payload(
        day,
        _short_setup(day),
        [_row(start, open_price=108.9, high=109.0, low=108.7, close=108.8)],
    )
    payload["provider_symbol_name"] = "US100"
    path = tmp_path / "evidence.json"
    _write(path, payload)

    result = run_vt31_silver_bullet_v2_backtest(path).payload()

    assert result["symbol"] == "NAS100"
    assert result["source_authorized_market"] == "NAS100"
    assert "market_matrix" not in result
