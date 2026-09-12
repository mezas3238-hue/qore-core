from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import cast
from zoneinfo import ZoneInfo

from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_2_backtest import (
    run_vt31_r2_2_backtest,
)

_NY = ZoneInfo("America/New_York")


def _row(opened: datetime, o: float, h: float, l: float, c: float) -> dict[str, str]:
    return {
        "period": "M1",
        "opened_at": opened.astimezone(UTC).isoformat(timespec="microseconds"),
        "closed_at": (opened + timedelta(minutes=1)).astimezone(UTC).isoformat(timespec="microseconds"),
        "open": str(o),
        "high": str(h),
        "low": str(l),
        "close": str(c),
    }


def _payload(day: datetime, *, second_side_before_fill: bool = False) -> dict[str, object]:
    old = day - timedelta(days=731)
    rows = [_row(old.replace(hour=9, minute=0), 100, 101, 99, 100)]
    ref = day.replace(hour=9, minute=0, second=0, microsecond=0)
    for minute in range(60):
        rows.append(
            _row(
                ref + timedelta(minutes=minute),
                105,
                110 if minute == 10 else 109,
                100 if minute == 20 else 101,
                105,
            )
        )
    start = day.replace(hour=10, minute=0, second=0, microsecond=0)
    session = [
        _row(start, 109.5, 111, 108.8, 109),
        _row(start + timedelta(minutes=1), 109, 109.2, 108, 108.5),
        _row(start + timedelta(minutes=2), 108.5, 108.7, 107.8, 108),
    ]
    if second_side_before_fill:
        session.append(_row(start + timedelta(minutes=3), 101, 102, 99, 101))
    else:
        session.append(_row(start + timedelta(minutes=3), 108.8, 109, 108.7, 108.8))
        session.append(_row(start + timedelta(minutes=4), 105, 108, 99, 101))
    while len(session) < 60:
        minute = len(session)
        session.append(_row(start + timedelta(minutes=minute), 105, 106, 104, 105))
    rows.extend(session)
    checked = datetime.fromisoformat(rows[-1]["closed_at"])
    first = datetime.fromisoformat(rows[0]["opened_at"])
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
        "checked_at": checked.isoformat(timespec="microseconds"),
        "requested_opened_at": first.isoformat(timespec="microseconds"),
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
            "span_seconds": int((checked - first).total_seconds()),
            "observed_gap_count": 1,
            "observed_gap_seconds": 1,
            "maximum_observed_gap_seconds": 1,
            "gap_policy": "test",
        },
        "periods": {"M1": rows},
    }


def test_daily_ledger_enforces_one_fill_and_non_source_execution_policy(tmp_path: Path) -> None:
    day = datetime(2026, 7, 8, tzinfo=_NY)
    path = tmp_path / "evidence.json"
    path.write_text(json.dumps(_payload(day)), encoding="utf-8")
    result = run_vt31_r2_2_backtest(path).payload()
    assert result["daily_cardinality_violations"] == 0
    assert result["filled_count"] == 1
    assert result["maximum_possible_fills"] == result["eligible_market_days"]
    policy = cast(dict[str, object], result["execution_policy"])
    assert policy["source_rule"] is False
    ledgers = cast(list[object], result["ledgers"])
    day_ledger = cast(dict[str, object], ledgers[-1])
    assert day_ledger["filled"] is True
    assert day_ledger["selected_setup"] is True


def test_second_reference_side_sweep_before_fill_is_contained(tmp_path: Path) -> None:
    day = datetime(2026, 7, 9, tzinfo=_NY)
    path = tmp_path / "evidence.json"
    path.write_text(
        json.dumps(_payload(day, second_side_before_fill=True)), encoding="utf-8"
    )
    result = run_vt31_r2_2_backtest(path).payload()
    assert result["filled_count"] == 0
    containments = cast(dict[str, int], result["containment_counts"])
    assert containments["abstain-both-sides-swept-before-fill"] == 1
