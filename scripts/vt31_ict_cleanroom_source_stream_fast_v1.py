#!/usr/bin/env python3
"""Actual frozen NAS100 3Y M1 input → *NEW* VT31 OPS negative-control replay.

Deliberately supplies NO cognitive decision. Original ICT raw FVG source
clock is observable, but trades MUST remain zero until COG producer is
scientifically connected. One trader identity, separate window counters.
This does not reuse old VT31 strategy modules or frozen old trade ledger.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterable
from zoneinfo import ZoneInfo

from qore.infrastructure.traders.vt31_ict_cleanroom.contracts import (
    M1Bar,
    SessionId,
    window_bounds,
)
from qore.infrastructure.traders.vt31_ict_cleanroom.operations import (
    IctSilverBulletOperations,
)

NY = ZoneInfo("America/New_York")
HOURS = {3: SessionId.LONDON, 10: SessionId.NY_AM, 14: SessionId.NY_PM}
BASE = "VT31_NAS100_OWNER_3Y_BASE_001"
START = "2023-10-01T00:00:00+00:00"
END = "2026-10-01T00:00:00+00:00"


def _dt(value: object) -> datetime:
    t = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if t.tzinfo is None or t.utcoffset() is None:
        raise ValueError("UTC-aware bar time required")
    return t.astimezone(UTC)


def _bar(row: dict[str, Any]) -> M1Bar:
    return M1Bar(
        _dt(row["opened_at"]), _dt(row["closed_at"]),
        Decimal(str(row["open"])), Decimal(str(row["high"])),
        Decimal(str(row["low"])), Decimal(str(row["close"])),
    )


def scan(rows: Iterable[dict[str, Any]]) -> dict[str, object]:
    full: Counter[str] = Counter()
    partial: Counter[str] = Counter()
    raw: Counter[str] = Counter()
    last: datetime | None = None
    active: tuple[str, SessionId] | None = None
    buffer: list[M1Bar] = []
    total = 0

    def flush() -> None:
        nonlocal active, buffer
        if active is None:
            return
        session = active[1]
        start, end = window_bounds(buffer[0].opened_at, session)
        is_complete = (
            len(buffer) == 60
            and buffer[-1].closed_at == end
            and all(b.opened_at == start + timedelta(minutes=i)
                    for i, b in enumerate(buffer))
        )
        if is_complete:
            ops = IctSilverBulletOperations(session=session, day=start)
            for bar in buffer:
                ops.on_closed_m1(bar, cognition=None)
            if ops.first_suitable is not None or ops.snapshot()["trading_authorized"]:
                raise AssertionError("cognition absent: cannot claim a trade")
            full[session.value] += 1
            raw[session.value] += ops.intrawindow_raw_fvg_count
        else:
            partial[session.value] += 1
        active = None
        buffer = []

    for row in rows:
        bar = _bar(row)
        if last is not None and bar.opened_at <= last:
            raise ValueError("3Y evidence M1 out-of-order / duplicate")
        last = bar.opened_at
        total += 1
        ny = bar.opened_at.astimezone(NY)
        session = HOURS.get(ny.hour)
        key = (ny.date().isoformat(), session) if session else None
        if key != active:
            flush()
        if key is not None:
            active = key
            buffer.append(bar)
    flush()
    if total == 0:
        raise ValueError("empty frozen market evidence")
    return {
        "schema": "qore.vt31.ict_cleanroom.3y_real_m1_no_cognition.v1",
        "source_base": BASE, "source_m1": total, "trader_id": "VT31",
        "session_model_count": 2, "source_window_count": 3,
        "full_source_window_days": {s.value: full[s.value] for s in SessionId},
        "partial_source_window_days": {s.value: partial[s.value] for s in SessionId},
        "raw_inside_hour_FVG_not_trades": {s.value: raw[s.value] for s in SessionId},
        "cognitive_decisions": 0, "filled_trades": 0, "paper_or_live_orders": 0,
        "profit_factor": "UNAVAILABLE_NO_TRADES",
        "drawdown": "UNAVAILABLE_NO_TRADES",
        "fresh_holdout_opened": False, "live_authorized": False,
        "source_only_negative_control": True,
    }


def _stream(path: Path) -> Iterable[dict[str, Any]]:
    import ijson

    for field, want in (
        ("base_id", BASE), ("market", "NAS100"),
        ("base_start_at", START), ("base_end_exclusive", END),
    ):
        with path.open("rb") as f:
            if next(ijson.items(f, field), None) != want:
                raise ValueError(f"frozen market evidence {field} identity drift")
    with path.open("rb") as f:
        yield from ijson.items(f, "periods.M1.item")


def self_test() -> None:
    start = datetime(2025, 7, 7, 14, tzinfo=UTC)
    rows = [{
        "opened_at": (start + timedelta(minutes=i)).isoformat(),
        "closed_at": (start + timedelta(minutes=i + 1)).isoformat(),
        "open": "100", "high": "101", "low": "99", "close": "100",
    } for i in range(60)]
    result = scan(rows)
    assert result["full_source_window_days"]["VT31_NY_AM"] == 1
    assert result["cognitive_decisions"] == result["filled_trades"] == 0
    try:
        scan(rows + rows[:1])
    except ValueError:
        pass
    else:
        raise AssertionError("duplicate M1 accepted")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--self-test", action="store_true")
    p.add_argument("--evidence", type=Path)
    p.add_argument("--output", type=Path)
    x = p.parse_args()
    if x.self_test:
        self_test()
        print("VT31 CLEANROOM 3Y M1 no-cognition test: PASS")
        return
    if x.evidence is None or x.output is None:
        p.error("--evidence and --output required")
    result = scan(_stream(x.evidence))
    x.output.parent.mkdir(parents=True, exist_ok=True)
    x.output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
