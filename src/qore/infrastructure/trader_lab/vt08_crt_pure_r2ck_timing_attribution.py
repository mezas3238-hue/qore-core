"""R2-CK six frozen rolling-H4 timing starts attribution (NON-PROMOTABLE).

Freeze: docs/research/VT08-CRT-PURE-R2CK-SIX-START-TIMING-ATTRIBUTION-FREEZE-001.md
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import vt08_crt_pure_r2cj_rolling_cost_margin as r2cj

IDENTITY = "VT08_CRT_PURE_R2CK_SIX_START_TIMING_ATTRIBUTION_001"
SIX_STARTS = tuple(f"ROLLING_H4:{idx}" for idx in range(1, 7))
START_HOUR_NY = {"ROLLING_H4:1": 1, "ROLLING_H4:2": 5, "ROLLING_H4:3": 9,
                 "ROLLING_H4:4": 13, "ROLLING_H4:5": 17, "ROLLING_H4:6": 21}
STRESS_COST_R = 0.02


def _bucket(
    records: tuple[dict[str, Any], ...],
    *,
    years: int,
    from_year: int,
) -> dict[str, Any]:
    if years <= 0:
        raise ValueError("Zero-year window is invalid")
    chron = tuple(sorted(records, key=lambda row: r2cj._time(row["entry_opened_at"])))
    raw = tuple(float(x["r_multiple"]) for x in chron)
    baseline = r2cj._stats(raw)
    friction = r2cj._stats(tuple(r - STRESS_COST_R for r in raw))
    positive_gross = 0
    positive_net = 0
    for year in range(from_year, from_year + years):
        left, right = (
            datetime(yr, 9, 21, tzinfo=UTC) for yr in (year, year + 1)
        )
        yearly = tuple(
            float(x["r_multiple"]) for x in chron
            if left <= r2cj._time(x["entry_opened_at"]) < right
        )
        positive_gross += sum(yearly) > 0
        positive_net += sum(yearly) - len(yearly) * STRESS_COST_R > 0
    return {
        "count": len(raw),
        "trades_per_year": round(len(raw) / years, 8),
        "gross": baseline,
        "cost_0.02R": friction,
        "gross_positive_annual_windows": positive_gross,
        "net_0.02R_positive_annual_windows": positive_net,
        "years": years,
    }


def _by_lattice(
    records: tuple[dict[str, Any], ...], *, years: int, start_year: int,
) -> dict[str, Any]:
    counts = Counter(str(row.get("timing_triplet")) for row in records)
    unexpected = set(counts) - set(SIX_STARTS)
    if unexpected:
        raise ValueError(f"Unexpected rolling-H4 timing labels {sorted(unexpected)}")
    categorized: dict[str, Any] = {}
    for label in SIX_STARTS:
        subset = tuple(
            row for row in records if row["timing_triplet"] == label
        )
        categorized[label] = {
            "h4_start_hour_america_new_york": START_HOUR_NY[label],
            **_bucket(subset, years=years, from_year=start_year),
        }
    if sum(v["count"] for v in categorized.values()) != len(records):
        raise ValueError("Six start counts not reconciled")
    if abs(
        sum(float(v["gross"]["total_r"]) for v in categorized.values())
        - sum(float(row["r_multiple"]) for row in records)
    ) > 0.000001:
        raise ValueError("Six start original R not reconciled")
    return {
        "all_starts": _bucket(records, years=years, from_year=start_year),
        "six_frozen_starts": categorized,
        "all_six_labels_present": len(counts) == 6,
        "reconciled": True,
    }


def run_market(
    market: str, *, older_trades: Path, older_report: Path,
    recent_trades: Path, recent_report: Path,
) -> dict[str, Any]:
    if market not in r2cj.MARKETS:
        raise ValueError("BTCUSD frozen; unsupported market")
    older = r2cj._lines(older_trades)
    recent = r2cj._lines(recent_trades)
    older_json = json.loads(older_report.read_text(encoding="utf-8"))
    recent_json = json.loads(recent_report.read_text(encoding="utf-8"))
    r2cj._check_frozen(market, "AQ", older, older_json)
    r2cj._check_frozen(market, "AO", recent, recent_json)
    fixed_recent = tuple(row for row in recent if row.get("target_arm") == r2cj.ARM)
    older_start = r2cj.EARLIEST[market].year
    older_years = r2cj.BOUNDARY.year - older_start
    by_period = {
        "OLDER_R2AQ": _by_lattice(
            older, years=older_years, start_year=older_start
        ),
        "RECENT_R2AO": _by_lattice(
            fixed_recent, years=6, start_year=2020
        ),
        "COMBINED": _by_lattice(
            older + fixed_recent, years=older_years + 6, start_year=older_start
        ),
    }
    for label in SIX_STARTS:
        old = by_period["OLDER_R2AQ"]["six_frozen_starts"][label]
        new = by_period["RECENT_R2AO"]["six_frozen_starts"][label]
        combined = by_period["COMBINED"]["six_frozen_starts"][label]
        if combined["count"] != old["count"] + new["count"]:
            raise ValueError("Timing label pooled trade count failed reconciliation")
        r2cj._check_number(
            combined["gross"]["total_r"],
            float(old["gross"]["total_r"]) + float(new["gross"]["total_r"]),
            f"{market}:{label}:gross pooled source",
        )

    source_stress = r2cj._stress(market, older + fixed_recent)
    pooled = by_period["COMBINED"]["all_starts"]
    r2cj._check_number(
        source_stress["gross_and_cost_stress"]["COST_0R"]["total_r"],
        pooled["gross"]["total_r"], "R2-CJ gross pooled check",
    )
    r2cj._check_number(
        source_stress["gross_and_cost_stress"]["COST_0.02R"]["total_r"],
        pooled["cost_0.02R"]["total_r"], "R2-CJ modeled cost pooled check",
    )
    return {
        "identity": IDENTITY,
        "market": market,
        "fixed_start_labels": list(SIX_STARTS),
        "reconciled_with_unchanged_original_AQ_AO": True,
        "reconciled_with_R2CJ_pooled_economics": True,
        "results": by_period,
        "historical_timing_win_selection_authorized": False,
        "multiplicity_is_descriptive_only": True,
        "strict_promotion_requires_fresh_holdout": True,
        "research_only": True,
        "sizing_volume_capital_leverage_forbidden": True,
        "no_merge_or_trading": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    parser.add_argument("--market", choices=r2cj.MARKETS, required=True)
    for item in ("older-trades", "older-report", "recent-trades", "recent-report"):
        parser.add_argument(f"--{item}", type=Path, required=True)
    args = parser.parse_args()
    result = run_market(
        args.market, older_trades=args.older_trades, older_report=args.older_report,
        recent_trades=args.recent_trades, recent_report=args.recent_report,
    )
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "report.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    summarized: dict[str, Any] = {}
    for period, panel in result["results"].items():
        summarized[period] = {
            label: {
                "count": item["count"],
                "gross_r": item["gross"]["total_r"],
                "gross_pf": item["gross"]["profit_factor"],
                "cost_0.02R_total_r": item["cost_0.02R"]["total_r"],
                "gross_positive_annual_windows": item["gross_positive_annual_windows"],
                "cost_0.02R_positive_annual_windows": item[
                    "net_0.02R_positive_annual_windows"
                ],
            }
            for label, item in panel["six_frozen_starts"].items()
        }
    print("VT08_R2CK_SIX_START=" + json.dumps({
        "market": args.market, "periods": summarized,
        "all_sources_reproduced": True,
        "no_rule_promotion": True,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
