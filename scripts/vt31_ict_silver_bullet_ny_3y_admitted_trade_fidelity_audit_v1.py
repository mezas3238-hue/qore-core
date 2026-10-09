#!/usr/bin/env python3
"""READ-ONLY source-provenance audit of all 55 frozen VT31_NY 3Y trades.

Checks whether a same-direction 3-candle FVG was already *closed* inside
10:00-11:00 NY by each existing admitted signal timestamp. This is ONLY raw
context support, not proof the trade used the FVG or the required DOL.
No retrospective outcome may ever become a new runtime filter.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, deque
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

BASE_ID = "VT31_NAS100_OWNER_3Y_BASE_001"
SCHEMA = "qore.vt31.ict_silver_bullet_ny_admitted_source_audit.v1"
NY = ZoneInfo("America/New_York")


def _dt(value: object) -> datetime:
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("naive timestamp")
    return parsed.astimezone(UTC)


def _control_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    if payload.get("schema") != "qore.vt31.nas100.owner_3y_replay.v1":
        raise ValueError("unexpected frozen 3Y replay")
    if payload.get("base_id") != BASE_ID:
        raise ValueError("wrong 3Y base")
    if payload.get("governance", {}).get("fresh_independent_holdout_claimed") is not False:
        raise ValueError("unsealed holdout")
    stack = payload["current_stack"]
    rows = stack["variants"][stack["lab_control_alias"]]["candidate_rows"]
    if len(rows) != 55:
        raise ValueError("frozen NY control must contain exactly 55 trades")
    if len({row["signal_at"] for row in rows}) != len(rows):
        raise ValueError("duplicate admitted identity")
    return rows


def _side(row: dict[str, Any]) -> str:
    value = str(row["side"]).upper()
    if value == "LONG":
        return "LONG"
    if value == "SHORT":
        return "SHORT"
    raise ValueError("unknown admitted side")


def audit_rows(
    rows: list[dict[str, Any]],
    m1_rows: Any,
) -> dict[str, object]:
    """All FVG events are strictly closed before the historical signal."""
    lookups = [
        {
            "signal_at": _dt(row["signal_at"]),
            "source_family": str(row.get("entry_family", "UNSPECIFIED")),
            "side": _side(row),
            "r_multiple": str(row["r_multiple"]),  # postoutcome attribution only
            "source_row": row,
        }
        for row in rows
    ]
    dates = {
        item["signal_at"].astimezone(NY).date().isoformat()
        for item in lookups
    }
    events: dict[str, list[dict[str, Any]]] = {day: [] for day in dates}
    previous: deque[dict[str, Any]] = deque(maxlen=3)
    last_open: datetime | None = None
    for raw in m1_rows:
        opened = _dt(raw["opened_at"])
        closed = _dt(raw["closed_at"])
        if closed - opened != timedelta(minutes=1):
            raise ValueError("bad M1 evidence")
        if last_open is not None and opened <= last_open:
            raise ValueError("unsorted/duplicate M1")
        if last_open is None or opened - last_open != timedelta(minutes=1):
            previous.clear()
        last_open = opened
        previous.append({
            "opened": opened,
            "closed": closed,
            "high": Decimal(str(raw["high"])),
            "low": Decimal(str(raw["low"])),
        })
        if len(previous) != 3:
            continue
        f, _, t = tuple(previous)
        if f["closed"] + timedelta(minutes=1) != t["opened"]:
            continue
        ny = opened.astimezone(NY)
        day = ny.date().isoformat()
        if day not in dates or ny.hour != 10:
            continue
        side = (
            "LONG" if t["low"] > f["high"] else
            "SHORT" if t["high"] < f["low"] else None
        )
        if side is not None:
            events[day].append({
                "formed_at": closed,
                "side": side,
            })

    result_rows: list[dict[str, Any]] = []
    for item in lookups:
        signal = item["signal_at"]
        day = signal.astimezone(NY).date().isoformat()
        source_hour = signal.astimezone(NY).hour
        same_direction = [
            ev for ev in events[day]
            if ev["formed_at"] <= signal and ev["side"] == item["side"]
        ]
        latest = max((ev["formed_at"] for ev in same_direction), default=None)
        support = "RAW_FVG_CLOSED_BY_SIGNAL_UNLINKED" if latest else "NO_RAW_DIRECTIONAL_FVG_BY_SIGNAL"
        if source_hour != 10:
            support = "SIGNAL_OUTSIDE_ICT_10_11_NY_SOURCE_HOUR"
        result_rows.append({
            "signal_at": signal.isoformat(),
            "local_ny_date": day,
            "entry_family": item["source_family"],
            "side": item["side"],
            "source_support": support,
            "same_direction_closed_fvg_count_by_signal": len(same_direction),
            "latest_raw_fvg_closed_at": None if latest is None else latest.isoformat(),
            "signal_to_latest_fvg_minutes": (
                None if latest is None else
                str(int((signal - latest).total_seconds() / 60))
            ),
            "fvg_selected_source_identity_proven": False,
            "next_draw_on_liquidity_proven": False,
            "projected_10_point_framework_proven": False,
            "post_outcome_r_attribution_only": item["r_multiple"],
        })
    by_status = Counter(x["source_support"] for x in result_rows)
    by_family: dict[str, dict[str, int]] = {}
    for family in sorted({x["entry_family"] for x in result_rows}):
        by_family[family] = dict(Counter(
            x["source_support"] for x in result_rows if x["entry_family"] == family
        ))
    return {
        "schema": SCHEMA,
        "base_id": BASE_ID,
        "frozen_control_trade_count": len(rows),
        "source_2023": "youtube:tRq1hyGGtl4",
        "existing_ttrades_variant_source": "youtube:o0v4KQxZbpU",
        "status": "READ_ONLY_SOURCE_FIDELITY_DIAGNOSTIC",
        "counts_by_source_support": dict(by_status),
        "counts_by_entry_family": by_family,
        "annotated_frozen_trades": result_rows,
        "governance": {
            "observed_fvg_not_proof_selected_thesis": True,
            "full_ict_source_fidelity_certified": False,
            "ttrades_variant_is_not_primary_ict_2023": True,
            "no_runtime_use_of_outcome": True,
            "no_trade_modified": True,
            "fresh_holdout_opened": False,
            "live_authorized": False,
        },
    }


def _evidence(path: Path) -> Any:
    import ijson

    expected = {
        "base_id": BASE_ID,
        "base_start_at": "2023-10-01T00:00:00+00:00",
        "base_end_exclusive": "2026-10-01T00:00:00+00:00",
        "market": "NAS100",
    }
    for key, val in expected.items():
        with path.open("rb") as handle:
            actual = next(ijson.items(handle, key), None)
        if actual != val:
            raise ValueError(f"evidence {key} != immutable 3Y truth")
    with path.open("rb") as handle:
        yield from ijson.items(handle, "periods.M1.item")


def self_test() -> None:
    base = datetime(2025, 5, 6, 14, tzinfo=UTC)
    def cand(i: int, high: int, low: int) -> dict[str, object]:
        a = base + timedelta(minutes=i)
        return {
            "opened_at": a.isoformat(),
            "closed_at": (a + timedelta(minutes=1)).isoformat(),
            "high": high,
            "low": low,
        }
    rows = [{
        "signal_at": (base + timedelta(minutes=3)).isoformat(),
        "entry_family": "breaker", "side": "short", "r_multiple": "-1",
    }]
    result = audit_rows(rows, [
        cand(0, 110, 100), cand(1, 108, 99), cand(2, 97, 94)
    ])
    assert result["counts_by_source_support"] == {
        "RAW_FVG_CLOSED_BY_SIGNAL_UNLINKED": 1
    }
    early = [{**rows[0], "signal_at": (
        base + timedelta(minutes=2)
    ).isoformat()}]
    assert audit_rows(early, [
        cand(0, 110, 100), cand(1, 108, 99), cand(2, 97, 94)
    ])["counts_by_source_support"] == {"NO_RAW_DIRECTIONAL_FVG_BY_SIGNAL": 1}
    try:
        audit_rows(rows, [cand(0, 110, 100), cand(0, 110, 100)])
    except ValueError:
        pass
    else:
        raise AssertionError("duplicate candle")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence", type=Path)
    parser.add_argument("--frozen-replay", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        print(json.dumps({"self_test": "PASS", "schema": SCHEMA}))
        return
    if not args.evidence or not args.frozen_replay or not args.output:
        parser.error("--evidence, --frozen-replay, --output are required")
    rows = _control_rows(json.loads(args.frozen_replay.read_text()))
    result = audit_rows(rows, _evidence(args.evidence))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print(json.dumps({
        "schema": SCHEMA,
        "frozen_trades": result["frozen_control_trade_count"],
        "raw_ict_fvg_context_by_trade": result["counts_by_source_support"],
        "raw_ict_fvg_context_by_family": result["counts_by_entry_family"],
        "certified": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
