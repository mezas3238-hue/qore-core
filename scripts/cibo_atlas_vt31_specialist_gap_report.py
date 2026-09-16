"""Render research-only market-vs-trader gap diagnostics for VT-31 specialists.

Inputs come from the independent CIBO Atlas Historical Market Scanner. Trader
outcomes are labels only. This script does not select markets, thresholds, or
candidate rules and does not open a holdout.
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
SCHEMA = "qore.cibo_atlas.vt31.specialist_gap_report.v1"


def D(value: object) -> Decimal:
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
    frac = pos - Decimal(lo)
    return xs[lo] * (Decimal(1) - frac) + xs[hi] * frac


def truth(value: object) -> bool:
    return str(value).lower() == "true"


def optional_decimal(value: object) -> Decimal | None:
    text = str(value)
    return None if text in {"", "None", "null"} else D(text)


def load_inputs(scanner_path: Path, matrix_path: Path) -> tuple[dict[str, Any], list[dict[str, str]]]:
    scanner = cast(dict[str, Any], json.loads(scanner_path.read_text(encoding="utf-8")))
    if scanner.get("schema") != "qore.cibo_atlas.vt31.historical_market_scanner.v1":
        raise ValueError("gap report requires CIBO Atlas historical scanner v1")
    if scanner.get("research_only") is not True or scanner.get("selection_prohibited") is not True:
        raise ValueError("scanner governance guard")
    if scanner.get("opens_new_holdout") is not False:
        raise ValueError("scanner cannot open fresh evidence")
    with matrix_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != int(scanner["independent_market_day_count"]):
        raise ValueError("scanner/matrix cardinality mismatch")
    return scanner, rows


def metric_bundle(rows: list[dict[str, str]]) -> dict[str, Any]:
    directional = [row for row in rows if row["first_breach"] in {"high", "low"}]
    reverse16 = [
        value
        for row in directional
        if (value := optional_decimal(row["max_reversal_excursion_ref_by_16"])) is not None
    ]
    return {
        "day_count": len(rows),
        "directional_breach_rate": fraction(len(directional), len(rows)),
        "both_sides_by_11_rate": fraction(sum(truth(row["both_sides_by_11"]) for row in rows), len(rows)),
        "opposite_boundary_hit_by_11_rate": fraction(
            sum(truth(row["opposite_boundary_hit_by_11"]) for row in directional), len(directional)
        ),
        "opposite_boundary_hit_by_16_rate": fraction(
            sum(truth(row["opposite_boundary_hit_by_16"]) for row in directional), len(directional)
        ),
        "post_breach_reversal_excursion_ref_by_16_p50": fmt(quantile(reverse16, Decimal("0.5"))),
    }


def outcome_rows(rows: list[dict[str, str]], field: str) -> list[dict[str, str]]:
    return [row for row in rows if int(row[field]) > 0]


def specialist_report(market: str, rows: list[dict[str, str]]) -> dict[str, Any]:
    terminal = sum(int(row["trader_terminal_count"]) for row in rows)
    initial_stop = sum(int(row["trader_initial_stop_count"]) for row in rows)
    protected_stop = sum(int(row["trader_protected_stop_count"]) for row in rows)
    target = sum(int(row["trader_target_count"]) for row in rows)
    roots = sum(int(row["trader_root_count"]) for row in rows)
    initial_days = outcome_rows(rows, "trader_initial_stop_count")
    protected_days = outcome_rows(rows, "trader_protected_stop_count")
    target_days = outcome_rows(rows, "trader_target_count")
    initial_then_opposite = [
        row for row in initial_days if truth(row["opposite_boundary_hit_by_16"])
    ]
    protected_then_opposite = [
        row for row in protected_days if truth(row["opposite_boundary_hit_by_16"])
    ]
    return {
        "market": market,
        "market_baseline": metric_bundle(rows),
        "trader": {
            "market_day_count": len(rows),
            "root_count": roots,
            "root_day_coverage_rate": fraction(sum(int(row["trader_root_count"]) > 0 for row in rows), len(rows)),
            "terminal_count": terminal,
            "initial_stop_count": initial_stop,
            "protected_stop_count": protected_stop,
            "target_count": target,
            "initial_stop_rate_terminal": fraction(initial_stop, terminal),
            "protected_stop_rate_terminal": fraction(protected_stop, terminal),
            "target_rate_terminal": fraction(target, terminal),
        },
        "outcome_context": {
            "initial_stop_days": metric_bundle(initial_days),
            "protected_stop_days": metric_bundle(protected_days),
            "target_days": metric_bundle(target_days),
            "initial_stop_then_opposite_09_boundary_by_16_count": len(initial_then_opposite),
            "initial_stop_then_opposite_09_boundary_by_16_rate": fraction(
                len(initial_then_opposite), len(initial_days)
            ),
            "protected_stop_then_opposite_09_boundary_by_16_count": len(protected_then_opposite),
            "protected_stop_then_opposite_09_boundary_by_16_rate": fraction(
                len(protected_then_opposite), len(protected_days)
            ),
        },
        "research_questions": [
            "Are initial-stop days directionally wrong, or is invalidation too close to the market's normal raid path?",
            "On stop-then-opposite-boundary days, did the methodological displacement remain valid after QORE invalidation?",
            "Does the specialist enter before the market's typical close-reentry/displacement latency for this index?",
            "Are double-sweep days disproportionately represented in specialist losses?",
            "Does cross-index unanimity identify crowding rather than confirmation for this market?",
        ],
    }


def cross_index_diagnostics(rows: list[dict[str, str]]) -> dict[str, Any]:
    by_day: dict[str, dict[str, dict[str, str]]] = defaultdict(dict)
    for row in rows:
        by_day[row["ny_date"]][row["market"]] = row
    buckets: dict[str, list[dict[str, dict[str, str]]]] = defaultdict(list)
    for markets in by_day.values():
        if set(markets) != set(MARKETS):
            continue
        directions = [markets[market]["first_breach"] for market in MARKETS]
        directional = [side for side in directions if side in {"high", "low"}]
        if len(directional) == 3 and len(set(directional)) == 1:
            state = "unanimous"
        elif len(directional) == 3:
            state = "conflict"
        else:
            state = "incomplete"
        buckets[state].append(markets)
    result: dict[str, Any] = {}
    for state, days in sorted(buckets.items()):
        initial = sum(
            int(markets[market]["trader_initial_stop_count"])
            for markets in days
            for market in MARKETS
        )
        targets = sum(
            int(markets[market]["trader_target_count"])
            for markets in days
            for market in MARKETS
        )
        terminals = sum(
            int(markets[market]["trader_terminal_count"])
            for markets in days
            for market in MARKETS
        )
        result[state] = {
            "day_count": len(days),
            "terminal_trade_count": terminals,
            "initial_stop_count": initial,
            "target_count": targets,
            "initial_stop_rate_terminal": fraction(initial, terminals),
            "target_rate_terminal": fraction(targets, terminals),
        }
    return result


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# CIBO Atlas — VT-31 Specialist Gap Report",
        "",
        "Research-only consumed evidence. No market selection, candidate promotion, fresh holdout, or live authority.",
        "",
    ]
    specialists = cast(dict[str, dict[str, Any]], payload["specialists"])
    for market in MARKETS:
        report = specialists[market]
        trader = cast(dict[str, Any], report["trader"])
        context = cast(dict[str, Any], report["outcome_context"])
        lines.extend(
            [
                f"## {market}",
                "",
                f"- terminal trades: {trader['terminal_count']}",
                f"- initial-stop rate: {trader['initial_stop_rate_terminal']}",
                f"- protected-stop rate: {trader['protected_stop_rate_terminal']}",
                f"- target rate: {trader['target_rate_terminal']}",
                f"- initial-stop days that later hit opposite 09:00 boundary by 16:00: {context['initial_stop_then_opposite_09_boundary_by_16_rate']}",
                f"- protected-stop days that later hit opposite 09:00 boundary by 16:00: {context['protected_stop_then_opposite_09_boundary_by_16_rate']}",
                "",
            ]
        )
    lines.extend(
        [
            "## Governance",
            "",
            "These are diagnostic gaps, not trading rules. A stop-then-target-like path is evidence for investigation, not proof that the stop should be widened. Any repair must preserve source methodology and pass leakage-free walk-forward before a fresh holdout.",
            "",
        ]
    )
    return "\n".join(lines)


def build(scanner_path: Path, matrix_path: Path, output_dir: Path) -> dict[str, Any]:
    scanner, rows = load_inputs(scanner_path, matrix_path)
    by_market = {market: [row for row in rows if row["market"] == market] for market in MARKETS}
    if any(not by_market[market] for market in MARKETS):
        raise ValueError("all three specialist markets require Atlas rows")
    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "research_only": True,
        "selection_prohibited": True,
        "opens_new_holdout": False,
        "candidate_status": "NO_R9_NOT_CERTIFIED",
        "live_authorized": False,
        "production_authorized": False,
        "source_scanner_schema": scanner["schema"],
        "specialists": {
            market: specialist_report(market, by_market[market]) for market in MARKETS
        },
        "cross_index_diagnostics": cross_index_diagnostics(rows),
        "hypothesis_policy": {
            "outcomes_are_labels_only": True,
            "automatic_parameter_change": False,
            "automatic_market_drop": False,
            "requires_causal_methodology_review": True,
            "requires_leakage_free_walk_forward": True,
        },
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "cibo-atlas-vt31-specialist-gap-report.json").write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    (output_dir / "cibo-atlas-vt31-specialist-gap-report.md").write_text(
        render_markdown(payload), encoding="utf-8"
    )
    return payload


def self_test() -> None:
    assert fraction(1, 2) == "0.5"
    assert quantile([Decimal(0), Decimal(2)], Decimal("0.5")) == Decimal(1)
    assert truth("true")
    assert not truth("false")
    print("CIBO Atlas specialist gap report self-test PASS")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--scanner", type=Path)
    parser.add_argument("--matrix", type=Path)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return
    if args.scanner is None or args.matrix is None or args.output_dir is None:
        parser.error("scanner, matrix, and output-dir are required")
    payload = build(args.scanner, args.matrix, args.output_dir)
    print(json.dumps(payload["specialists"], sort_keys=True))


if __name__ == "__main__":
    main()
