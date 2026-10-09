#!/usr/bin/env python3
"""Fast read-only forensics of the frozen VT31_NY continuous 3Y control ledger.

No market-data fetch, policy change, new trades, position sizing, or fresh
holdout access. Uses the existing immutable baseline replay and adjudication.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from decimal import Decimal
from pathlib import Path
from typing import Any

SCHEMA = "qore.vt31.nas100.owner_3y_loss_cluster_fast_audit.v1"
BASE_ID = "VT31_NAS100_OWNER_3Y_BASE_001"
FRICTION = Decimal("0.05")
EXPECTED = {
    "trade_count": 55,
    "max_drawdown_r": Decimal("21.3585957183"),
    "total_r": Decimal("25.4956512133"),
    "max_losing_streak": 23,
}
TOLERANCE = Decimal("0.000001")


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _s(value: Decimal) -> str:
    return format(value, "f")


def _identity(row: dict[str, Any] | None) -> dict[str, object] | None:
    if row is None:
        return None
    return {
        "signal_at": row["signal_at"],
        "local_date": row["local_date"],
        "entry_family": row.get("entry_family"),
        "side": row.get("side"),
        "exit_reason": row.get("exit_reason"),
    }


def _breakdown(
    rows: list[dict[str, Any]], *,
    field: str,
) -> dict[str, dict[str, object]]:
    groups: dict[str, list[Decimal]] = defaultdict(list)
    for row in rows:
        groups[str(row.get(field) or "UNSPECIFIED")].append(
            _d(row["r_multiple"]) - FRICTION
        )
    return {
        label: {
            "trades": len(values),
            "wins": sum(v > 0 for v in values),
            "losses": sum(v < 0 for v in values),
            "net_r": _s(sum(values, Decimal(0))),
            "negative_mass_r": _s(-sum(
                (v for v in values if v < 0), Decimal(0)
            )),
            "positive_mass_r": _s(sum(
                (v for v in values if v > 0), Decimal(0)
            )),
        }
        for label, values in sorted(groups.items())
    }


def analyze_rows(rows: list[dict[str, Any]]) -> dict[str, object]:
    """Reproduce frozen Comparator-009/3Y DD convention, chronological by signal."""
    ordered = sorted(rows, key=lambda row: str(row["signal_at"]))
    keys = [str(row["signal_at"]) for row in ordered]
    if len(keys) != len(set(keys)):
        raise ValueError("duplicate signal identity: cannot audit")
    if any(
        not str(row["local_date"]).startswith(("2023-", "2024-", "2025-", "2026-"))
        for row in ordered
    ):
        raise ValueError("unexpected trade date")

    equity = Decimal(0)
    peak = Decimal(0)
    current_peak_idx: int | None = None
    dd_peak_idx: int | None = None
    dd_trough_idx: int | None = None
    max_dd = Decimal(0)
    worst_streak = 0
    active_streak = 0
    streak_start = 0
    worst_streak_range: tuple[int, int] | None = None
    ledger: list[dict[str, object]] = []
    for index, row in enumerate(ordered):
        net = _d(row["r_multiple"]) - FRICTION
        equity += net
        if equity > peak:
            peak = equity
            current_peak_idx = index
        dd = peak - equity
        if dd > max_dd:
            max_dd = dd
            dd_peak_idx = current_peak_idx
            dd_trough_idx = index
        if net < 0:
            if active_streak == 0:
                streak_start = index
            active_streak += 1
            if active_streak > worst_streak:
                worst_streak = active_streak
                worst_streak_range = (streak_start, index)
        else:
            active_streak = 0
        ledger.append({
            **_identity(row), "index": index,
            "net_r": _s(net), "equity_r": _s(equity),
            "running_peak_r": _s(peak), "underwater_r": _s(dd),
        })

    start = 0 if dd_peak_idx is None else dd_peak_idx + 1
    end = -1 if dd_trough_idx is None else dd_trough_idx
    dd_rows = ordered[start:end + 1] if end >= start else []
    values = [_d(row["r_multiple"]) - FRICTION for row in ordered]
    worst_streak_rows = (
        ordered[worst_streak_range[0]:worst_streak_range[1] + 1]
        if worst_streak_range is not None else []
    )
    return {
        "trade_count": len(ordered),
        "total_r": _s(sum(values, Decimal(0))),
        "wins": sum(v > 0 for v in values),
        "losses": sum(v < 0 for v in values),
        "max_drawdown_r": _s(max_dd),
        "max_losing_streak": worst_streak,
        "worst_losing_streak": {
            "first": _identity(worst_streak_rows[0]) if worst_streak_rows else None,
            "last": _identity(worst_streak_rows[-1]) if worst_streak_rows else None,
            "length": len(worst_streak_rows),
            "net_r": _s(sum(
                (_d(x["r_multiple"]) - FRICTION for x in worst_streak_rows),
                Decimal(0),
            )),
        },
        "max_drawdown_episode": {
            "peak_index": dd_peak_idx,
            "trough_index": dd_trough_idx,
            "peak_trade": (
                _identity(ordered[dd_peak_idx])
                if dd_peak_idx is not None else None
            ),
            "trough_trade": (
                _identity(ordered[dd_trough_idx])
                if dd_trough_idx is not None else None
            ),
            "trades_after_peak_through_trough": len(dd_rows),
            "wins": sum((_d(x["r_multiple"]) - FRICTION) > 0 for x in dd_rows),
            "losses": sum((_d(x["r_multiple"]) - FRICTION) < 0 for x in dd_rows),
            "gross_negative_mass_r": _s(-sum(
                (_d(x["r_multiple"]) - FRICTION for x in dd_rows
                 if _d(x["r_multiple"]) - FRICTION < 0),
                Decimal(0),
            )),
            "positive_offset_r": _s(sum(
                (_d(x["r_multiple"]) - FRICTION for x in dd_rows
                 if _d(x["r_multiple"]) - FRICTION > 0),
                Decimal(0),
            )),
            "by_entry_family": _breakdown(dd_rows, field="entry_family"),
            "by_exit_reason": _breakdown(dd_rows, field="exit_reason"),
            "by_side": _breakdown(dd_rows, field="side"),
        },
        "all_trades_by_entry_family": _breakdown(ordered, field="entry_family"),
        "all_trades_by_exit_reason": _breakdown(ordered, field="exit_reason"),
        "all_trades_by_side": _breakdown(ordered, field="side"),
        "all_trades_by_year": _breakdown([
            {**row, "year": str(row["local_date"])[:4]}
            for row in ordered
        ], field="year"),
        "frozen_control_chronological_ledger": ledger,
    }


def audit(replay: dict[str, Any], adjudication: dict[str, Any]) -> dict[str, object]:
    if replay.get("schema") != "qore.vt31.nas100.owner_3y_replay.v1":
        raise ValueError("unexpected replay schema")
    if replay.get("base_id") != BASE_ID or adjudication.get("base_id") != BASE_ID:
        raise ValueError("wrong 3Y base")
    if replay.get("window", {}).get("start_at") != "2023-10-01T00:00:00+00:00":
        raise ValueError("wrong start of frozen window")
    if replay.get("window", {}).get("end_exclusive") != "2026-10-01T00:00:00+00:00":
        raise ValueError("wrong end of frozen window")
    governance = replay.get("governance", {})
    if governance.get("single_contiguous_3y_base") is not True:
        raise ValueError("non-contiguous 3Y base")
    if governance.get("legacy_r5_r6_r8_operating_folds_used") is not False:
        raise ValueError("forbidden historical fold replay")
    if governance.get("fresh_independent_holdout_claimed") is not False:
        raise ValueError("fresh holdout contamination")
    stack = replay["current_stack"]
    alias = stack["lab_control_alias"]
    if alias != adjudication["control_alias"]:
        raise ValueError("control alias disagreement")
    rows = stack["variants"][alias]["candidate_rows"]
    reported = adjudication["variants"][alias]
    result = analyze_rows(rows)
    if result["trade_count"] != reported["trade_count"]:
        raise AssertionError("adjudicated trade count drift")
    if abs(_d(result["max_drawdown_r"]) -
           _d(reported["drawdown_episode"]["max_drawdown_r"])) > TOLERANCE:
        raise AssertionError("frozen adjudicator drawdown drift")
    for key, expected in EXPECTED.items():
        current = result[key]
        if isinstance(expected, Decimal):
            if abs(_d(current) - expected) > TOLERANCE:
                raise AssertionError(f"frozen baseline {key} drift: {current}")
        elif current != expected:
            raise AssertionError(f"frozen baseline {key} drift: {current}")
    result["schema"] = SCHEMA
    result["base_id"] = BASE_ID
    result["control_alias"] = alias
    result["friction_r_per_trade"] = _s(FRICTION)
    result["existing_adjudicator_gates"] = reported["gates"]
    result["existing_control_certification_pass"] = reported[
        "certification_gate_pass"
    ]
    result["governance"] = {
        "consumed_3y_control_only": True,
        "read_only_outcome_attribution": True,
        "no_trade_or_policy_change": True,
        "no_runtime_use_of_terminal_outcome": True,
        "no_sizing_leverage_compounding": True,
        "fresh_holdout_opened": False,
        "candidate_certified": False,
        "live_authorized": False,
    }
    return result


def self_test() -> None:
    rows = [
        {"signal_at": f"2024-01-0{i}T10:00:00+00:00",
         "local_date": f"2024-01-0{i}", "entry_family": "breaker",
         "side": "long", "exit_reason": "test",
         "r_multiple": str(r)}
        for i, r in enumerate((1, -1, -1, 2), start=1)
    ]
    x = analyze_rows(rows)
    assert x["max_drawdown_r"] == "2.10"
    assert x["max_losing_streak"] == 2
    assert x["max_drawdown_episode"]["trades_after_peak_through_trough"] == 2
    assert x["max_drawdown_episode"]["gross_negative_mass_r"] == "2.10"
    assert x["total_r"] == "0.80"
    try:
        analyze_rows(rows + [rows[-1]])
    except ValueError:
        pass
    else:
        raise AssertionError("duplicate signal accepted")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--replay", type=Path)
    parser.add_argument("--adjudication", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        print(json.dumps({"self_test": "PASS", "schema": SCHEMA}))
        return
    if not args.replay or not args.adjudication or not args.output:
        parser.error("--replay, --adjudication, --output required")
    result = audit(
        json.loads(args.replay.read_text(encoding="utf-8")),
        json.loads(args.adjudication.read_text(encoding="utf-8")),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "schema": SCHEMA,
        "base_id": BASE_ID,
        "trade_count": result["trade_count"],
        "total_r": result["total_r"],
        "max_drawdown_r": result["max_drawdown_r"],
        "max_losing_streak": result["max_losing_streak"],
        "dd_cluster": result["max_drawdown_episode"],
        "existing_control_certification_pass": result[
            "existing_control_certification_pass"
        ],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
