"""Diagnostic path-consistency audit for certified VT31 target architecture.

Checks whether the pre-existing CORE partial-1.25R lifecycle can realize a
partial before the new EQ50 milestone. Such a case would make the post-hoc
mixture in Capacity Selective Target Ladder non-replicable by a single live
position without predeclared sub-leg semantics.

Diagnostic only. No policy changes.
"""
# ruff: noqa: B009\nfrom __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_nas100_alt_tier_bifurcation_forensics_v1 as alt
import vt31_nas100_target_decision_engine_frontier_v2 as target_v2

from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_5_multi_index_research import (
    _day,
    _wall,
    load_market_evidence,
)

SCHEMA = "qore.vt31.nas100.live_path_consistency_audit.v1"


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _touch(bar: object, side: str, level: Decimal) -> bool:
    if side == "long":
        return _d(getattr(bar, "high")) >= level
    return _d(getattr(bar, "low")) <= level


def replay(path: Path, *, partition: str) -> dict[str, object]:
    rows, evidence, diagnostics, stats = alt._current_rows(path)
    series, account, fingerprint, checked, evidence_sha, provider = (
        load_market_evidence(path)
    )
    raw: dict[date, list[object]] = defaultdict(list)
    for bar in series:
        raw[_day(getattr(bar, "opened_at"))].append(bar)
    by_day = {
        day: tuple(sorted(items, key=lambda bar: getattr(bar, "opened_at")))
        for day, items in raw.items()
    }

    counts: Counter[str] = Counter()
    conflicts: list[dict[str, object]] = []

    for row in rows:
        if str(row.get("tier")) != "CORE":
            continue
        if str(row.get("reference_volatility_state")) == "compressed":
            counts["core_compressed"] += 1
            continue
        entry_raw = row.get("entry")
        stop_raw = row.get("initial_stop")
        filled_raw = row.get("filled_at")
        exit_raw = row.get("exit_at")
        if None in {entry_raw, stop_raw, filled_raw, exit_raw}:
            counts["censored_missing_geometry"] += 1
            continue

        entry = _d(entry_raw)
        stop = _d(stop_raw)
        risk = abs(entry - stop)
        if risk <= 0:
            counts["censored_invalid_risk"] += 1
            continue
        side = str(row["side"])
        partial = (
            entry + risk * Decimal("1.25")
            if side == "long"
            else entry - risk * Decimal("1.25")
        )
        local_day = date.fromisoformat(cast(str, row["local_date"]))
        bars = by_day.get(local_day, ())
        reference = tuple(
            bar
            for bar in bars
            if (9, 0, 0) <= _wall(getattr(bar, "opened_at")) < (10, 0, 0)
        )
        if len(reference) != 60:
            counts["censored_reference"] += 1
            continue
        ref_high = max(_d(getattr(bar, "high")) for bar in reference)
        ref_low = min(_d(getattr(bar, "low")) for bar in reference)
        eq = (ref_high + ref_low) / Decimal(2)
        forward = eq > entry if side == "long" else eq < entry
        if not forward:
            counts["eq_not_forward"] += 1
            continue

        filled = datetime.fromisoformat(cast(str, filled_raw))
        terminal = datetime.fromisoformat(cast(str, exit_raw))
        partial_at = None
        eq_at = None
        for bar in bars:
            closed = cast(datetime, getattr(bar, "closed_at"))
            opened = cast(datetime, getattr(bar, "opened_at"))
            if closed < filled or closed >= terminal:
                continue
            if _wall(opened) >= (16, 0, 0):
                break
            if partial_at is None and _touch(bar, side, partial):
                partial_at = closed
            if eq_at is None and _touch(bar, side, eq):
                eq_at = closed

        if eq_at is None:
            counts["no_eq_before_terminal"] += 1
            continue
        counts["eq_before_terminal"] += 1
        if partial_at is None:
            counts["eq_before_any_1_25"] += 1
            continue
        if partial_at < eq_at:
            counts["CONFLICT_1_25_BEFORE_EQ"] += 1
            conflicts.append(
                {
                    "local_date": row["local_date"],
                    "signal_at": row["signal_at"],
                    "side": side,
                    "entry": str(entry),
                    "partial_1_25": str(partial),
                    "equilibrium": str(eq),
                    "partial_at": partial_at.isoformat(),
                    "equilibrium_at": eq_at.isoformat(),
                    "base_exit_reason": row.get("exit_reason"),
                    "destination_state": target_v2._destination_state(row)[0],
                }
            )
        elif partial_at == eq_at:
            counts["AMBIGUOUS_SAME_M1_1_25_EQ"] += 1
        else:
            counts["EQ_BEFORE_1_25"] += 1

    return {
        "schema": SCHEMA,
        "partition": partition,
        "counts": dict(sorted(counts.items())),
        "conflicts": conflicts,
        "path_consistent_for_single_position": (
            counts["CONFLICT_1_25_BEFORE_EQ"] == 0
            and counts["AMBIGUOUS_SAME_M1_1_25_EQ"] == 0
        ),
        "evidence": {
            "account_fingerprint": account,
            "evidence_fingerprint": fingerprint,
            "checked_at": checked.isoformat(),
            "software_sha": evidence_sha,
            "provider": provider,
        },
        "source_stats": stats,
        "diagnostics": diagnostics,
        "governance": {
            "diagnostic_only": True,
            "policy_changed": False,
            "certification_changed": False,
            "future_runtime_input": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path)
    parser.add_argument("--partition", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    payload = replay(args.evidence, partition=args.partition)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "partition": payload["partition"],
                "counts": payload["counts"],
                "path_consistent": payload[
                    "path_consistent_for_single_position"
                ],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
