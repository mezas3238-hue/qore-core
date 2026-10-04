#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from decimal import Decimal
from pathlib import Path


def dec(value: object) -> Decimal:
    return Decimal(str(value))


def gaps(payload: dict) -> list[tuple[str, Decimal, int]]:
    ee = payload["economic_efficiency"]
    ab = payload["block_ablations"]
    cov = payload["position_lifecycle_coverage"]
    att = payload["function_attribution_summary"]
    cog = payload["cognitive_economic_actuation"]
    out: list[tuple[str, Decimal, int]] = []

    lifecycle = dec(ab["position_lifecycle_value_usd"])
    if lifecycle < 0:
        out.append(("LIFECYCLE_DESTRUCTIVE", -lifecycle, cov["candidate_count"]))

    portfolio = dec(ab["portfolio_competition_value_usd"])
    if portfolio <= Decimal("0.000001"):
        out.append(("PORTFOLIO_NO_VALUE", abs(portfolio), 1))

    leverage = dec(ab["adaptive_leverage_value_vs_1x_usd"])
    if leverage < 0:
        out.append(("LEVERAGE_DESTRUCTIVE", -leverage, 1))

    compound = dec(ab["capital_compound_value_usd"])
    if compound < 0:
        out.append(("COMPOUND_DESTRUCTIVE", -compound, 1))

    missed = ee["opportunity_capture"]
    if int(missed["positive_expectancy_missed_count"]):
        out.append((
            "MISSED_POSITIVE_OPPORTUNITY",
            dec(missed["positive_expectancy_missed_expected_value_usd"]),
            int(missed["positive_expectancy_missed_count"]),
        ))

    velocity = ee["capital_velocity"]
    out.append((
        "SLOW_REDEPLOYMENT",
        dec(velocity["release_to_next_deploy_median_minutes"]),
        int(velocity["release_to_next_deploy_observations"]),
    ))

    idle = ee["idle_deployable_capital"]
    out.append((
        "IDLE_RISK_REQUIRES_CLASSIFICATION",
        dec(idle["risk_headroom_idle_pct_time_weighted"]),
        int(idle["epoch_count"]),
    ))

    fallback = int(cov["fallback_original_settlement_count"])
    if fallback:
        pct = Decimal(fallback) / Decimal(cov["candidate_count"]) * 100
        out.append(("POSITION_PATH_DATA_GAP", pct, fallback))

    unresolved = 53 - int(att["unique_function_values_identified"])
    if unresolved:
        out.append(("FUNCTION_ATTRIBUTION_UNRESOLVED", Decimal(unresolved), 53))

    direct = len(cog["consumed_control_functions"])
    if direct < 19:
        out.append(("COGNITIVE_ACTUATION_GAP", Decimal(19 - direct), 19))

    t14 = ee["t14_pre_settlement_release"]
    released = dec(t14["released_stop_risk_usd"])
    if released > 0:
        out.append(("T14_REDEPLOYMENT_UNPROVEN", released, int(t14["changed_count"])))

    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--frontier", action="append", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    grouped: dict[str, list[tuple[str, Decimal, int]]] = defaultdict(list)
    for path in args.frontier:
        payload = json.loads(path.read_text(encoding="utf-8"))
        group = str(payload["research_group_id"])
        for kind, magnitude, count in gaps(payload):
            grouped[kind].append((group, magnitude, count))

    queue = []
    for kind, rows in grouped.items():
        queue.append({
            "kind": kind,
            "group_recurrence": len(rows),
            "groups": [row[0] for row in rows],
            "max_magnitude": format(max(row[1] for row in rows), "f"),
            "total_magnitude": format(sum((row[1] for row in rows), Decimal(0)), "f"),
            "evidence_count": sum(row[2] for row in rows),
        })
    queue.sort(key=lambda row: (
        -row["group_recurrence"],
        -dec(row["max_magnitude"]),
        row["kind"],
    ))

    report = {
        "schema": "qore.cibo.maximum-capability-diagnostic.v1",
        "group_count": len(args.frontier),
        "target_efficiency": "0.9999",
        "certification_claimed": False,
        "priority_queue": queue,
    }
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
