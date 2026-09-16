"""Root-by-root consumed-only causal attribution for CIBO Atlas / VT-31.

This module joins the definitive tick-corrected terminal ledger features with the
independent gap05 CIBO market-day Atlas. It separates demonstrated path facts
from causal hypotheses. It never changes trader parameters, selects a market,
or opens fresh evidence.
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

MARKETS = ("NAS100", "SP500", "US30")
SCHEMA = "qore.cibo_atlas.vt31.root_cause_attribution.v1"


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


def truth(value: object) -> bool:
    return str(value).lower() == "true"


def terminal_family(status: object) -> str:
    text = str(status).lower()
    if "initial-stop" in text:
        return "initial_stop"
    if "protected-stop" in text:
        return "protected_stop"
    if "target" in text:
        return "target"
    return "other"


def load_forensics(path: Path) -> dict[str, Any]:
    payload = cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))
    if payload.get("schema") != "qore.vt31.tick_corrected.deep_forensics.v1":
        raise ValueError("requires definitive deep forensics v1")
    if payload.get("research_only") is not True or payload.get("selection_prohibited") is not True:
        raise ValueError("forensics governance guard")
    rows = payload.get("rows")
    if not isinstance(rows, list) or len(rows) != 618:
        raise ValueError("requires all 618 terminal feature rows")
    return payload


def load_atlas(scanner_path: Path, matrix_path: Path) -> tuple[dict[str, Any], list[dict[str, str]]]:
    scanner = cast(dict[str, Any], json.loads(scanner_path.read_text(encoding="utf-8")))
    if scanner.get("schema") != "qore.cibo_atlas.vt31.historical_market_scanner.gap05.v1":
        raise ValueError("requires gap05 historical Atlas v1")
    if scanner.get("ledger_root_overlay_count") != 780:
        raise ValueError("Atlas must cover all 780 roots")
    if scanner.get("research_only") is not True or scanner.get("selection_prohibited") is not True:
        raise ValueError("Atlas governance guard")
    with matrix_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != int(scanner["independent_market_day_count"]):
        raise ValueError("Atlas matrix cardinality mismatch")
    return scanner, rows


def cross_index_state(by_day: dict[str, dict[str, dict[str, str]]], ny_date: str) -> str:
    markets = by_day.get(ny_date, {})
    if set(markets) != set(MARKETS):
        return "not-three-market-complete"
    directions = [markets[market]["first_breach"] for market in MARKETS]
    directional = [value for value in directions if value in {"high", "low"}]
    if len(directional) == 3 and len(set(directional)) == 1:
        return f"unanimous-{directional[0]}"
    if len(directional) == 3:
        return "three-directional-conflict"
    return "mixed-or-incomplete"


def pre_entry_bundle(rows: list[dict[str, Any]]) -> dict[str, Any]:
    numeric = (
        "risk_to_reference",
        "entry_location_to_reference",
        "raid_body_fraction",
        "raid_depth_to_reference",
        "confirmation_body_fraction",
        "confirmation_range_to_reference",
        "displacement_beyond_anchor_to_reference",
        "raid_to_confirmation_latency_m1",
        "raid_to_final_extreme_latency_m1",
        "opposing_liquidity_r",
        "signal_minute",
    )
    result: dict[str, Any] = {
        "n": len(rows),
        "markets": dict(sorted(Counter(str(row["market"]) for row in rows).items())),
        "sides": dict(sorted(Counter(str(row["side"]) for row in rows).items())),
        "entry_families": dict(sorted(Counter(str(row["entry_family"]) for row in rows).items())),
        "cross_index_states": dict(sorted(Counter(str(row["cross_index_state"]) for row in rows).items())),
    }
    for field in numeric:
        values = [dec(row[field]) for row in rows if row.get(field) is not None]
        result[field] = {
            "n": len(values),
            "p10": fmt(quantile(values, Decimal("0.10"))),
            "p50": fmt(quantile(values, Decimal("0.50"))),
            "p90": fmt(quantile(values, Decimal("0.90"))),
        }
    return result


def classify(row: dict[str, Any], atlas: dict[str, str]) -> tuple[str, str]:
    family = terminal_family(row["terminal_status"])
    opposite = truth(atlas["opposite_boundary_hit_by_16"])
    objective_r = dec(row["opposing_liquidity_r"])
    if objective_r <= Decimal(2):
        raise AssertionError("source objective must remain beyond frozen 2R target")
    if family == "initial_stop" and opposite:
        return (
            "demonstrated_exit_before_eventual_source_objective",
            "initial-invalidation-path-mismatch",
        )
    if family == "protected_stop" and opposite:
        return (
            "demonstrated_exit_before_eventual_source_objective",
            "protected-management-path-mismatch",
        )
    if family in {"initial_stop", "protected_stop"}:
        return (
            "stop_without_eventual_source_objective_by_16",
            "direction-or-setup-quality-investigation",
        )
    if family == "target" and opposite:
        return (
            "fixed_2r_exit_before_or_at_eventual_source_objective",
            "target-lifecycle-source-mismatch-investigation",
        )
    if family == "target":
        return (
            "fixed_2r_target_without_source_objective_by_16",
            "target-lifecycle-source-mismatch-investigation",
        )
    return "unclassified", "unclassified"


def build(forensics_path: Path, scanner_path: Path, matrix_path: Path, output_dir: Path) -> dict[str, Any]:
    forensics = load_forensics(forensics_path)
    scanner, atlas_rows = load_atlas(scanner_path, matrix_path)
    atlas_by_key = {(row["market"], row["ny_date"]): row for row in atlas_rows}
    if len(atlas_by_key) != len(atlas_rows):
        raise ValueError("duplicate market/date Atlas row")
    by_day: dict[str, dict[str, dict[str, str]]] = defaultdict(dict)
    for row in atlas_rows:
        by_day[row["ny_date"]][row["market"]] = row

    joined: list[dict[str, Any]] = []
    for raw in cast(list[object], forensics["rows"]):
        if not isinstance(raw, dict):
            raise ValueError("malformed forensics row")
        row = cast(dict[str, Any], raw)
        key = (str(row["market"]), str(row["ny_date"]))
        atlas = atlas_by_key.get(key)
        if atlas is None:
            raise ValueError(f"terminal row missing Atlas day {key}")
        expected_breach = "low" if row["side"] == "long" else "high"
        if atlas["first_breach"] != expected_breach:
            raise ValueError(
                f"source/trader raid-side mismatch for {row['root_id']}: "
                f"expected {expected_breach}, Atlas {atlas['first_breach']}"
            )
        fact, hypothesis = classify(row, atlas)
        enriched = dict(row)
        enriched.update(
            {
                "terminal_family": terminal_family(row["terminal_status"]),
                "atlas_first_breach": atlas["first_breach"],
                "atlas_first_breach_minute": atlas["first_breach_minute"],
                "atlas_both_sides_by_11": truth(atlas["both_sides_by_11"]),
                "atlas_close_reentry_latency_m1": atlas["close_reentry_latency_m1"],
                "atlas_opposite_boundary_hit_by_11": truth(atlas["opposite_boundary_hit_by_11"]),
                "atlas_opposite_boundary_hit_by_16": truth(atlas["opposite_boundary_hit_by_16"]),
                "atlas_max_continuation_depth_ref": atlas["max_continuation_depth_ref"],
                "atlas_max_reversal_excursion_ref_by_16": atlas["max_reversal_excursion_ref_by_16"],
                "cross_index_state": cross_index_state(by_day, str(row["ny_date"])),
                "demonstrated_path_fact": fact,
                "causal_hypothesis_family": hypothesis,
            }
        )
        joined.append(enriched)

    if len(joined) != 618 or len({str(row["root_id"]) for row in joined}) != 618:
        raise AssertionError("terminal root conservation failed")

    demonstrated = [
        row
        for row in joined
        if row["demonstrated_path_fact"] == "demonstrated_exit_before_eventual_source_objective"
    ]
    stop_rows = [row for row in joined if row["terminal_family"] in {"initial_stop", "protected_stop"}]
    by_market: dict[str, Any] = {}
    for market in MARKETS:
        market_rows = [row for row in joined if row["market"] == market]
        market_stops = [row for row in market_rows if row["terminal_family"] in {"initial_stop", "protected_stop"}]
        market_demonstrated = [
            row
            for row in market_rows
            if row["demonstrated_path_fact"] == "demonstrated_exit_before_eventual_source_objective"
        ]
        initial = [row for row in market_rows if row["terminal_family"] == "initial_stop"]
        protected = [row for row in market_rows if row["terminal_family"] == "protected_stop"]
        by_market[market] = {
            "terminal_count": len(market_rows),
            "stop_count": len(market_stops),
            "demonstrated_exit_before_eventual_source_objective_count": len(market_demonstrated),
            "demonstrated_rate_of_stops": fraction(len(market_demonstrated), len(market_stops)),
            "initial_stop_count": len(initial),
            "initial_stop_then_source_objective_count": sum(
                row["demonstrated_path_fact"] == "demonstrated_exit_before_eventual_source_objective"
                for row in initial
            ),
            "initial_stop_then_source_objective_rate": fraction(
                sum(
                    row["demonstrated_path_fact"] == "demonstrated_exit_before_eventual_source_objective"
                    for row in initial
                ),
                len(initial),
            ),
            "protected_stop_count": len(protected),
            "protected_stop_then_source_objective_count": sum(
                row["demonstrated_path_fact"] == "demonstrated_exit_before_eventual_source_objective"
                for row in protected
            ),
            "protected_stop_then_source_objective_rate": fraction(
                sum(
                    row["demonstrated_path_fact"] == "demonstrated_exit_before_eventual_source_objective"
                    for row in protected
                ),
                len(protected),
            ),
            "demonstrated_pre_entry_profile": pre_entry_bundle(market_demonstrated),
            "other_stop_pre_entry_profile": pre_entry_bundle(
                [row for row in market_stops if row not in market_demonstrated]
            ),
        }

    hypothesis_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in joined:
        hypothesis_groups[str(row["causal_hypothesis_family"])].append(row)

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "research_only": True,
        "selection_prohibited": True,
        "opens_new_holdout": False,
        "candidate_status": "NO_R9_NOT_CERTIFIED",
        "live_authorized": False,
        "production_authorized": False,
        "source_forensics_schema": forensics["schema"],
        "source_atlas_schema": scanner["schema"],
        "terminal_root_count": len(joined),
        "stop_root_count": len(stop_rows),
        "demonstrated_exit_before_eventual_source_objective_count": len(demonstrated),
        "demonstrated_rate_of_all_stops": fraction(len(demonstrated), len(stop_rows)),
        "proof_contract": {
            "source_objective_beyond_2r_for_all_terminal_rows": all(
                dec(row["opposing_liquidity_r"]) > Decimal(2) for row in joined
            ),
            "logic": (
                "For a terminal stop, if the opposite 09:00 boundary is later observed by 16:00, "
                "the frozen 2R target could not have been reached first while the position remained open; "
                "therefore the source objective occurred only after the trader had already exited."
            ),
            "does_not_prove_stop_should_be_widened": True,
            "requires_post_stop_structure_validation": True,
        },
        "by_market": by_market,
        "causal_hypothesis_profiles": {
            name: pre_entry_bundle(rows) for name, rows in sorted(hypothesis_groups.items())
        },
        "demonstrated_cross_index_states": dict(
            sorted(Counter(str(row["cross_index_state"]) for row in demonstrated).items())
        ),
        "next_required_tests": [
            "reconstruct post-exit M1 path and source-defined structure validity for demonstrated cases",
            "measure whether displacement/CISD remained valid after QORE exit",
            "measure MFE/MAE from executable fill with tick evidence where available",
            "compare demonstrated path-mismatch cases against stop-without-objective controls within each market",
            "form finite market-specific repair hypotheses only after those causal tests",
        ],
        "rows": joined,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "cibo-atlas-vt31-root-cause-attribution.json").write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    compact = {
        "terminal_roots": payload["terminal_root_count"],
        "stops": payload["stop_root_count"],
        "demonstrated": payload["demonstrated_exit_before_eventual_source_objective_count"],
        "rate": payload["demonstrated_rate_of_all_stops"],
        "by_market": {
            market: {
                "stops": by_market[market]["stop_count"],
                "demonstrated": by_market[market]["demonstrated_exit_before_eventual_source_objective_count"],
                "rate": by_market[market]["demonstrated_rate_of_stops"],
            }
            for market in MARKETS
        },
    }
    (output_dir / "cibo-atlas-vt31-root-cause-summary.json").write_text(
        json.dumps(compact, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    return payload


def self_test() -> None:
    assert terminal_family("initial-stop-after-fill") == "initial_stop"
    assert terminal_family("terminal-protected-stop") == "protected_stop"
    assert terminal_family("fixed-2r-target") == "target"
    assert fraction(1, 4) == "0.25"
    print("CIBO Atlas VT31 root-cause attribution self-test PASS")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--forensics", type=Path)
    parser.add_argument("--scanner", type=Path)
    parser.add_argument("--matrix", type=Path)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return
    if args.forensics is None or args.scanner is None or args.matrix is None or args.output_dir is None:
        parser.error("forensics, scanner, matrix and output-dir are required")
    payload = build(args.forensics, args.scanner, args.matrix, args.output_dir)
    print(
        json.dumps(
            {
                "stops": payload["stop_root_count"],
                "demonstrated": payload["demonstrated_exit_before_eventual_source_objective_count"],
                "rate": payload["demonstrated_rate_of_all_stops"],
                "by_market": payload["by_market"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
