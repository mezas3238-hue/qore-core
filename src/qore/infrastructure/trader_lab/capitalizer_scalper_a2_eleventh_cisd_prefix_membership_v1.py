"""A2 P0: distinguish V49 first-online selection from event candidate availability.

The 381 full-vs-prefix contradictions prove non-prefix-invariance of the
FIRST-EVENT decision. A differing first candidate does not logically prove
that the V49 event was absent from *all* alternative candidates at the close.
This module makes that distinction explicit by source ID; no admission changes.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.capitalizer_scalper_v49_v50_g_waterfall_v1 import (
    _jsonl,
)

IDENTITY = "QORE_SCALPER_A2_ELEVENTH_PREFIX_MEMBERSHIP_FORENSIC_V1"
FAMILIES = ("FVG_RETRACE_CISD", "LIQUIDITY_SWEEP_CISD")


def route_first_at(witness: dict[str, Any], family: str) -> str | None:
    if family == "FVG_RETRACE_CISD":
        value = witness["fvg_cisd_confirmed_at"]
    elif family == "LIQUIDITY_SWEEP_CISD":
        value = witness["sweep_confirmed_at"]
    else:
        raise ValueError("unknown V49 CISD route")
    if value is not None and not isinstance(value, str):
        raise ValueError("source route witness must be an ISO time or null")
    return value if isinstance(value, str) else None


def classify_row(row: dict[str, Any]) -> dict[str, Any]:
    if row.get("classification") == "M15_PARENT_NOT_RECONSTRUCTED":
        return {
            "source_opportunity_id": row["source_opportunity_id"],
            "status": "NO_M15_PARENT_WITNESS",
            "original_route_first_at_source_close": None,
            "original_is_first_online_candidate": None,
            "original_absent_from_all_asof_candidates": None,
            "future_dependent_offline_first_selection": None,
            "changes_admission": False,
        }
    for key in (
        "source_opportunity_id", "source_entry_at", "source_family",
        "full_window_witness", "closed_prefix_witness", "full_matches_original",
        "prefix_matches_sensor", "source_sensor_disagree",
    ):
        if key not in row:
            raise ValueError(f"missing forensic field: {key}")
    if not row["full_matches_original"] or not row["prefix_matches_sensor"]:
        raise ValueError("underlying frozen full-prefix reconstruction must match")
    family = row["source_family"]
    if family not in FAMILIES:
        raise ValueError("unsupported frozen source route")
    prefix = row["closed_prefix_witness"]
    full = row["full_window_witness"]
    at = row["source_entry_at"]
    if full["first_family"] != family or full["first_at"] != at:
        raise ValueError("full-window selected family/time diverged from source")
    route_at = route_first_at(prefix, family)
    route_exact = route_at == at
    selected_exact = prefix["first_at"] == at and prefix["first_family"] == family
    disagreement = bool(row["source_sensor_disagree"])
    if selected_exact == disagreement:
        raise ValueError("source/sensor mismatch inconsistent with online first event")
    if route_at is not None and route_at > at:
        raise ValueError("as-of prefix cannot witness a route after original decision")
    return {
        "source_opportunity_id": row["source_opportunity_id"],
        "symbol": row["symbol"],
        "source_entry_at": at,
        "source_family": family,
        "sensor_first_at": row["sensor_first_at"],
        "sensor_family": row["sensor_family"],
        "original_route_first_at_source_close": route_exact,
        "original_route_prefix_first_at": route_at,
        "original_is_first_online_candidate": selected_exact,
        "future_dependent_offline_first_selection": disagreement,
        "original_absent_from_all_asof_candidates": (
            None  # Requires enumerating ALL candidate events, not merely the first.
        ),
        "not_first_route_is_not_lookahead_event_proof": True,
        "changes_admission": False,
    }


def market(source_root: Path) -> tuple[dict[str, Any], tuple[dict[str, Any], ...]]:
    files = sorted(source_root.rglob("scalper-cisd-prefix-rows.jsonl"))
    if len(files) != 1:
        raise ValueError("one exact frozen CISD full-prefix per-market rows file")
    original = tuple(_jsonl(files[0]))
    if not original:
        raise ValueError("no CISD source rows")
    rows = tuple(classify_row(x) for x in original)
    if len({r["source_opportunity_id"] for r in rows}) != len(rows):
        raise ValueError("duplicate source identity")
    symbol = original[0]["symbol"]
    if any(x["symbol"] != symbol for x in original):
        raise ValueError("mixed market")
    counts: Counter[str] = Counter()
    for r in rows:
        if r["original_is_first_online_candidate"] is None:
            counts["UNATTESTED_M15"] += 1
        elif r["original_is_first_online_candidate"]:
            counts["ONLINE_FIRST_MATCH"] += 1
        else:
            counts["OFFLINE_FIRST_NOT_PREFIX_INVARIANT"] += 1
        if r["original_route_first_at_source_close"] is True:
            counts["ORIGINAL_ROUTE_FIRST_MATCH"] += 1
        if r["original_route_first_at_source_close"] is False:
            counts["ORIGINAL_ROUTE_NOT_FIRST_MATCH"] += 1
    return {
        "identity": IDENTITY, "symbol": symbol, "sources": len(rows),
        "class_counts": dict(sorted(counts.items())),
        "unresolved_all_candidate_membership": sum(
            r["original_absent_from_all_asof_candidates"] is None for r in rows
        ),
        "trades_reexecuted": 0, "changes_admission": 0,
        "author_certified": False,
    }, rows


def aggregate(root: Path) -> dict[str, Any]:
    summaries = [
        json.loads(f.read_text(encoding="utf-8"))
        for f in sorted(root.rglob("scalper-eleventh-cisd-membership-market.json"))
    ]
    if len(summaries) != 9 or len({r["symbol"] for r in summaries}) != 9:
        raise ValueError("require nine different markets")
    rows = [
        row for f in sorted(root.rglob("scalper-eleventh-cisd-membership-ids.jsonl"))
        for row in _jsonl(f)
    ]
    if len(rows) != 2876 or len({r["source_opportunity_id"] for r in rows}) != 2876:
        raise ValueError("missing original source identities")
    counts: Counter[str] = Counter()
    for row in rows:
        if row["original_is_first_online_candidate"] is True:
            counts["ONLINE_FIRST_MATCH"] += 1
        elif row["original_is_first_online_candidate"] is False:
            counts["OFFLINE_FIRST_NOT_PREFIX_INVARIANT"] += 1
        else:
            counts["UNATTESTED_M15"] += 1
        if row["original_route_first_at_source_close"] is True:
            counts["ORIGINAL_ROUTE_FIRST_MATCH"] += 1
        if row["original_route_first_at_source_close"] is False:
            counts["ORIGINAL_ROUTE_NOT_FIRST_MATCH"] += 1
    if counts["ONLINE_FIRST_MATCH"] != 2495 or counts[
        "OFFLINE_FIRST_NOT_PREFIX_INVARIANT"
    ] != 381:
        raise ValueError("eleventh audit population changed unexpectedly")
    return {
        "identity": IDENTITY, "sources": 2876, "markets": 9,
        "counts": dict(sorted(counts.items())),
        "original_event_absent_from_every_asof_candidate_not_yet_proven": True,
        "future_dependent_offline_first_selection": 381,
        "changed_admissions": 0, "paper_pf": None, "paper_dd_r": None,
        "author_fidelity_certified": False,
    }


def main() -> None:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="mode", required=True)
    m = sub.add_parser("market")
    m.add_argument("inputs", type=Path)
    m.add_argument("output", type=Path)
    a = sub.add_parser("matrix")
    a.add_argument("inputs", type=Path)
    a.add_argument("output", type=Path)
    args = p.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    if args.mode == "market":
        report, rows = market(args.inputs)
        (args.output/"scalper-eleventh-cisd-membership-market.json").write_text(
            json.dumps(report, indent=2, sort_keys=True)+"\n", encoding="utf-8"
        )
        with (args.output/"scalper-eleventh-cisd-membership-ids.jsonl").open(
            "w", encoding="utf-8"
        ) as file:
            for row in rows:
                file.write(json.dumps(row, sort_keys=True)+"\n")
    else:
        report = aggregate(args.inputs)
        (args.output/"scalper-eleventh-cisd-membership-nine-market.json").write_text(
            json.dumps(report, indent=2, sort_keys=True)+"\n", encoding="utf-8"
        )
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
