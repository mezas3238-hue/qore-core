"""W2 PADE signed GROSS research-only 33-market synchronized-week inference.

Never relabel as net profitability, Sharpe, certified DD or broker execution.
All 33 sources, zero-signal markets and censored events remain in denominator.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from statistics import mean

from qore.infrastructure.trader_lab.qore_native_market33_source_census_v1 import FAMILIES
from qore.research.alpha2_g1a_panel_stats import (
    ERAS,
    _gross_pf,
    block_bootstrap,
)
from qore.research.alpha2_intermarket import MARKETS, sha256_file
from qore.research.alpha2_w2_pade_native_m5 import ORIGINAL33_SHA, SOURCE_ONLY_ID

IDENTITY = "QORE_ALPHA2_W2_PADE_33_FIRST_PAIRED_GROSS_ONLY_PANEL_V1"
COST_BPS = (0, 1, 3, 5, 10, 20)
FAMILY = {s: f for f, members in FAMILIES.items() for s in members}


def _avg(v: list[float]) -> float | None:
    return float(mean(v)) if v else None


def source_load(root: Path, exact_head: str) -> dict[str, dict]:
    paths = sorted(root.rglob("alpha2-w2-pade-gross-*.json"))
    if len(paths) != 33:
        raise ValueError("full33 SHA-audited original-market results mandatory")
    observed: dict[str, dict] = {}
    for path in paths:
        label = path.name
        digest = path.with_name(label + ".sha256").read_text(encoding="utf-8").strip()
        if digest != f"{sha256_file(path)}  {label}":
            raise ValueError("market GROSS JSON independent SHA mismatch")
        worker_sha = (path.parent / "exact-code-head-sha.txt").read_text(encoding="utf-8").strip()
        if worker_sha != exact_head:
            raise ValueError("non-identical W2 economic replay worker HEAD")
        x = json.loads(path.read_text(encoding="utf-8"))
        symbol = x.get("symbol")
        if (symbol not in MARKETS or symbol in observed
                or x.get("identity") != SOURCE_ONLY_ID
                or x.get("source_33_manifest_sha256") != ORIGINAL33_SHA
                or x.get("full_native_source_SHA_verified_before_OHLC") is not True
                or x.get("after_2024_09_17_price_unread") is not True
                or x.get("UTC001_certified") is not False
                or x.get("broker_costs_verified") is not False
                or x.get("news_known_asof_verified") is not False
                or x.get("original_signal_count") != len(x.get("opportunities", []))):
            raise ValueError("W2 original source/research-only constraints violated")
        if len({e["utc_day"] for e in x["opportunities"]}) != len(x["opportunities"]):
            raise ValueError("more than one PADE event/day leaked")
        observed[symbol] = x
    if set(observed) != set(MARKETS) or len(FAMILY) != len(MARKETS):
        raise ValueError("not entire 33 frozen market/family universe")
    return observed


def infer(root: Path, exact_head: str) -> dict:
    source = source_load(root, exact_head)
    by_symbol = {}
    events = []
    by_family: dict[str, dict] = {}
    for symbol in sorted(MARKETS):
        src = source[symbol]
        ee = src["opportunities"]
        paired = [e for e in ee if e["paired"]]
        opposite = sum(
            e["plan"]["direction"] != e["plan"]["control_direction"] for e in paired
        )
        row = {
            "family": FAMILY[symbol],
            "source_cohort": src["source_proof"]["source_cohort"],
            "signals": len(ee), "paired": len(paired),
            "unpaired": len(ee) - len(paired),
            "opposing_control_direction_cases": opposite,
            "gross_strat_mean_bps_proxy": _avg(
                [e["strategy"]["gross_bps"] for e in paired]),
            "paired_delta_mean_bps_proxy": _avg(
                [e["delta_gross_bps"] for e in paired]),
            "rule_exclusion_counts": src["predeclared_rule_exclusion_counts"],
        }
        by_symbol[symbol] = row
        events.extend(ee)
    n_opposed = sum(x["opposing_control_direction_cases"] for x in by_symbol.values())
    for family in FAMILIES:
        rows = [by_symbol[s] for s in sorted(FAMILIES[family])]
        by_family[family] = {
            "markets": len(rows),
            "signals": sum(x["signals"] for x in rows),
            "paired": sum(x["paired"] for x in rows),
            "opposing_control_cases": sum(
                x["opposing_control_direction_cases"] for x in rows),
            "source_selection_by_outcome": False,
        }
    eras: dict[str, dict] = {}
    for era, (start, end, min_n, min_weeks) in ERAS.items():
        whole = [e for e in events if e["era"] == era]
        paired = [e for e in whole if e["paired"]]
        n_week = len({e["iso_week"] for e in paired})
        gross = [float(e["strategy"]["gross_bps"]) for e in paired]
        baseline = [float(e["control"]["gross_bps"]) for e in paired]
        delta = [float(e["delta_gross_bps"]) for e in paired]
        r = [float(e["strategy"]["gross_R"]) for e in paired]
        delta_event = [{
            "iso_week": e["iso_week"],
            "paired_observed": e["paired"],
            "paired_delta_gross_bps": e["delta_gross_bps"],
        } for e in whole]
        boots = {f"{size}wk": block_bootstrap(delta_event, era=era, length=size)
                 for size in (1, 2, 4)}
        by_orig = {
            origin: sum(
                e["paired"] and by_symbol[e["symbol"]]["source_cohort"] == origin
                for e in whole
            )
            for origin in ("ORIGINAL12_CIBO_ATLAS", "NEW21_ICMARKETS_DEMO")
        }
        min_cohorts = all(v >= 20 for v in by_orig.values())
        sample = len(paired) >= min_n and n_week >= min_weeks and min_cohorts
        year_rows = {}
        for y in range(start.year, end.year + 1):
            yy = [e for e in paired if datetime.fromisoformat(
                e["plan"]["decision_utc"]).year == y]
            year_rows[str(y)] = {
                "n_paired":len(yy),
                "gross_mean_bps_proxy":_avg([e["strategy"]["gross_bps"] for e in yy]),
                "delta_mean_bps_proxy":_avg([e["delta_gross_bps"] for e in yy]),
                "gross_pf_proxy_not_utc001":_gross_pf(
                    [e["strategy"]["gross_R"] for e in yy]),
            }
        by_era_opposed = sum(
            e["plan"]["direction"] != e["plan"]["control_direction"] for e in paired
        )
        eras[era] = {
            "original_signals": len(whole),
            "paired_evaluable":len(paired),
            "censored_or_unpaired":len(whole)-len(paired),
            "censor_reason_counts":dict(sorted(Counter(
                e["strategy"]["status"]+"|"+e["control"]["status"]
                for e in whole if not e["paired"]
            ).items())),
            "opposing_control_direction_cases": by_era_opposed,
            "weeks_with_events": n_week,
            "minimum_sample_gate": sample,
            "predeclared_min_trades": min_n,
            "predeclared_min_weeks": min_weeks,
            "per_cohort_paired": by_orig,
            "mean_gross_strategy_bps_proxy": _avg(gross),
            "mean_gross_control_bps_proxy": _avg(baseline),
            "paired_delta_mean_bps_proxy": _avg(delta),
            "gross_pf_proxy_not_utc001": _gross_pf(r),
            "gross_expectancy_R_proxy_not_utc001":_avg(r),
            "cost_hypothesis_bps_RT_NOT_NET":{
                str(k): (_avg(gross)-k if gross else None) for k in COST_BPS
            },
            "common_calendar_synchronized_bootstrap": boots,
            "year_descriptive": year_rows,
        }
    valid_comparator = all(
        eras[era]["opposing_control_direction_cases"] > 0 for era in ERAS
    )
    sample = all(x["minimum_sample_gate"] for x in eras.values())
    positivity = all(
        x["mean_gross_strategy_bps_proxy"] is not None
        and x["mean_gross_strategy_bps_proxy"] > 0
        and x["paired_delta_mean_bps_proxy"] is not None
        and x["paired_delta_mean_bps_proxy"] > 0
        for x in eras.values()
    )
    confidence = all(
        all(
            x["common_calendar_synchronized_bootstrap"][f"{size}wk"]["ci95_bps"] is not None
            and x["common_calendar_synchronized_bootstrap"][f"{size}wk"]["ci95_bps"][0] > 0
            for size in (1, 2, 4)
        ) for x in eras.values()
    )
    status = ("COMPARATOR_NONDISCRIMINATIVE" if not valid_comparator
              else "UNDERPOWERED" if not sample
              else "GROSS_RESEARCH_CANDIDATE_NOT_NET" if positivity and confidence
              else "NO_SUPPORT_PREDECLARED_GROSS")
    return {
        "identity": IDENTITY, "status": status, "markets": 33,
        "source33_sha256": ORIGINAL33_SHA,
        "exact_worker_code_head": exact_head,
        "original_signals":len(events),
        "total_evaluable_paired":sum(x["paired_evaluable"] for x in eras.values()),
        "opposite_direction_cases":n_opposed,
        "independent_direction_comparator_non_tautological":valid_comparator,
        "eras":eras, "per_market_all33":by_symbol, "by_family":by_family,
        "no_pnl_winner_market_selection": True,
        "provider_volume_semantics_unverified":True,
        "broker_bidask_historical_unverified":True,
        "macro_news_PIT_unverified":True,
        "gross_from_native_M5_open_not_executable":True,
        "NET_PF_Sharpe_Sortino_DD_not_computed":True,
        "UTC001_certified":False,
        "traders_certified":0,
        "production_untouched":True,
        "after_2024_09_17_ohlc_unread":True,
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("workers33", type=Path)
    p.add_argument("out", type=Path)
    p.add_argument("--head", required=True)
    args = p.parse_args()
    result = infer(args.workers33, args.head)
    args.out.mkdir(parents=True, exist_ok=True)
    file = args.out / "alpha2-w2-pade-33-first-gross-panel.json"
    file.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8")
    print(json.dumps({
        "status": result["status"],
        "markets": result["markets"],
        "original_signals": result["original_signals"],
        "paired": result["total_evaluable_paired"],
        "opposite_control_cases": result["opposite_direction_cases"],
        "eras": {
            key: {"paired": row["paired_evaluable"],
                  "gross_bps": row["mean_gross_strategy_bps_proxy"],
                  "delta_bps": row["paired_delta_mean_bps_proxy"],
                  "sample_gate":row["minimum_sample_gate"]}
            for key,row in result["eras"].items()
        },
        "NO_NET_CERTIFICATION":True,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
