"""Consumed-only concentration map for demonstrated VT-31 path mismatches.

Reads the immutable root-cause attribution artifact and reports every observed
cohort without promoting filters or thresholds. Outcome-derived rates are
research labels only and cannot become trader rules without a separate causal
hypothesis and leakage-free walk-forward.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

SCHEMA = "qore.cibo_atlas.vt31.error_concentration_map.v1"
DIMENSIONS: tuple[tuple[str, ...], ...] = (
    ("market", "terminal_family"),
    ("market", "entry_family"),
    ("market", "side"),
    ("market", "cross_index_state"),
    ("market", "protected_swing_like_at_signal"),
    ("market", "side", "entry_family"),
)


def dec(value: object) -> Decimal:
    return Decimal(str(value))


def fmt(value: Decimal | None) -> str | None:
    return None if value is None else format(value, "f")


def fraction(numerator: int, denominator: int) -> str | None:
    return None if denominator == 0 else fmt(Decimal(numerator) / Decimal(denominator))


def quantile(values: list[Decimal], p: Decimal) -> Decimal | None:
    if not values:
        return None
    xs = sorted(values)
    if len(xs) == 1:
        return xs[0]
    pos = p * Decimal(len(xs) - 1)
    lo = int(pos)
    hi = min(lo + 1, len(xs) - 1)
    weight = pos - Decimal(lo)
    return xs[lo] * (Decimal(1) - weight) + xs[hi] * weight


def load_source(path: Path) -> dict[str, Any]:
    payload = cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))
    if payload.get("schema") != "qore.cibo_atlas.vt31.root_cause_attribution.v1":
        raise ValueError("requires root-cause attribution v1")
    if payload.get("research_only") is not True or payload.get("selection_prohibited") is not True:
        raise ValueError("source governance guard")
    rows = payload.get("rows")
    if not isinstance(rows, list) or len(rows) != 618:
        raise ValueError("requires 618 terminal rows")
    return payload


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    stops = [row for row in rows if row["terminal_family"] in {"initial_stop", "protected_stop"}]
    demonstrated = [
        row
        for row in stops
        if row["demonstrated_path_fact"] == "demonstrated_exit_before_eventual_source_objective"
    ]
    initial = [row for row in stops if row["terminal_family"] == "initial_stop"]
    protected = [row for row in stops if row["terminal_family"] == "protected_stop"]
    numeric_fields = (
        "risk_to_reference",
        "entry_location_to_reference",
        "confirmation_body_fraction",
        "displacement_beyond_anchor_to_reference",
        "raid_body_fraction",
        "raid_depth_to_reference",
        "raid_to_confirmation_latency_m1",
        "signal_minute",
    )
    profile: dict[str, Any] = {}
    for field in numeric_fields:
        values = [dec(row[field]) for row in demonstrated if row.get(field) is not None]
        profile[field] = {
            "n": len(values),
            "p50": fmt(quantile(values, Decimal("0.5"))),
        }
    return {
        "terminal_count": len(rows),
        "stop_count": len(stops),
        "demonstrated_count": len(demonstrated),
        "demonstrated_rate_of_stops": fraction(len(demonstrated), len(stops)),
        "initial_stop_count": len(initial),
        "initial_demonstrated_count": sum(
            row["demonstrated_path_fact"] == "demonstrated_exit_before_eventual_source_objective"
            for row in initial
        ),
        "protected_stop_count": len(protected),
        "protected_demonstrated_count": sum(
            row["demonstrated_path_fact"] == "demonstrated_exit_before_eventual_source_objective"
            for row in protected
        ),
        "demonstrated_pre_entry_medians": profile,
    }


def build(source_path: Path, output_dir: Path) -> dict[str, Any]:
    source = load_source(source_path)
    rows = [cast(dict[str, Any], row) for row in cast(list[object], source["rows"])]
    dimensions: dict[str, Any] = {}
    for fields in DIMENSIONS:
        groups: dict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            key = tuple(str(row[field]) for field in fields)
            groups[key].append(row)
        dimensions[" x ".join(fields)] = [
            {
                "cohort": {field: value for field, value in zip(fields, key, strict=True)},
                **summarize(group),
            }
            for key, group in sorted(groups.items())
        ]
    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "research_only": True,
        "selection_prohibited": True,
        "opens_new_holdout": False,
        "candidate_status": "NO_R9_NOT_CERTIFIED",
        "live_authorized": False,
        "production_authorized": False,
        "source_root_cause_schema": source["schema"],
        "terminal_root_count": len(rows),
        "demonstrated_total": source["demonstrated_exit_before_eventual_source_objective_count"],
        "dimensions": dimensions,
        "interpretation_guard": [
            "rates describe consumed evidence only",
            "no cohort is an admissibility rule",
            "small cohorts are not promoted or discarded",
            "market-specific repair requires post-exit structure validation",
            "any repair must pass leakage-free walk-forward before fresh evidence",
        ],
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "cibo-atlas-vt31-error-concentration-map.json").write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    return payload


def self_test() -> None:
    assert fraction(2, 5) == "0.4"
    assert quantile([Decimal(1), Decimal(3)], Decimal("0.5")) == Decimal(2)
    print("CIBO Atlas VT31 error concentration map self-test PASS")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--source", type=Path)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return
    if args.source is None or args.output_dir is None:
        parser.error("source and output-dir are required")
    payload = build(args.source, args.output_dir)
    print(json.dumps({"demonstrated_total": payload["demonstrated_total"], "dimensions": payload["dimensions"]}, sort_keys=True))


if __name__ == "__main__":
    main()
