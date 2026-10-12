"""E2 all 231 signed gross E1 cells, synchronized weekly bootstrap + Holm.

No direct OHLC reads; accepts precisely 33 signed original-source E1 witnesses
from ONE GitHub Actions code SHA. NOT execution fills, news PIT, or net edge.
"""
from __future__ import annotations

import argparse
import json
import math
from collections import Counter, defaultdict
from datetime import UTC, date, datetime
from pathlib import Path
from statistics import mean
from typing import Any

import numpy as np

from qore.infrastructure.trader_lab import qore_native_e1_33x7_seven_gross_per_market_v1 as e1
from qore.infrastructure.trader_lab import qore_native_33x7_method_market_registry_v1 as registry
from qore.infrastructure.trader_lab import qore_native_existing12_m5_g0_v1 as g0

IDENTITY = "QORE_NATIVE_E2_ALL231_HOLM_WEEK_BOOTSTRAP_GROSS_ONLY_V1"
B = 20000
SEED = 20261012
ALPHA_FWER = 0.05
MIN = {"development": (150, 52), "temporal_diagnostic": (50, 26)}
METHODS = tuple(x[0] for x in registry.METHODOLOGIES)
SYMBOLS = tuple(sorted(e1.source_g0.final33.FROZEN_UNIVERSE_33))
CELLS = tuple(f"{m}__{s}" for m in METHODS for s in SYMBOLS)
COSTS = list(e1.ROUNDTRIP_ASSUMPTIONS)


def load_signed_observations(root: Path) -> dict[str, list[dict[str, Any]]]:
    paths = sorted(root.rglob("qore-native-e1-seven-*.json"))
    if len(paths) != 33:
        raise ValueError("exactly 33 signed original-G0+seven-method witnesses required")
    found: dict[str, list[dict[str, Any]]] = {}
    code_sha: set[str] = set()
    for path in paths:
        witness = g0.digest_ledger(path.with_name(path.name + ".sha256"))
        g0.verified_file(path.parent, witness, path.name)
        head_path = path.with_name("exact-code-head-sha.txt")
        if not head_path.is_file():
            raise ValueError("per-symbol witness code SHA missing")
        head = head_path.read_text(encoding="utf-8").strip()
        if len(head) != 40 or any(ch not in "0123456789abcdef" for ch in head):
            raise ValueError("per-symbol code SHA malformed")
        code_sha.add(head)
        doc = json.loads(path.read_text(encoding="utf-8"))
        sym = doc.get("original_symbol")
        if (
            sym not in SYMBOLS or sym in found
            or doc.get("identity") != e1.IDENTITY
            or doc.get("frozen_prereg_commit") != e1.PREREG_SHA
            or doc.get("source33_sha") != e1.SOURCE_33_SHA
            or doc.get("status") != "E1_SEVEN_METHOD_GROSS_ONLY_PREVIOUSLY_EXPOSED_PERIODS"
            or doc.get("future_ohlc_not_read") is not True
            or doc.get("net_certified") is not False
            or doc.get("traders_certified") != 0
            or doc.get("production_untouched") is not True
            or not isinstance(doc.get("seven_methods"), list)
            or len(doc["seven_methods"]) != 7
            or doc.get("source_audit", {}).get("original_raw_11_year_sha_checked") is not True
        ):
            raise ValueError("tampered/missing original 33 source code/prereg/NoLIVE flags")
        ids = []
        for section in doc["seven_methods"]:
            method = section.get("method_id")
            ids.append(method)
            if (
                method not in METHODS
                or section.get("cell_id") != f"{method}__{sym}"
                or section.get("prior_pr") != registry.cell_prior(method, sym)["prior_pr"]
                or section.get("evidence_status") != registry.cell_prior(method, sym)["status"]
                or section.get("net_economics_authorized") is not False
                or section.get("news_asof_filtered") is not False
                or section.get("bidask_measured") is not False
                or not isinstance(section.get("paired_events"), list)
            ):
                raise ValueError("E1 source/cell prior and news/bidask guarantees drift")
            seen: set[str] = set()
            for row in section["paired_events"]:
                utc = datetime.fromisoformat(row["reference_entry_utc"])
                d = date.fromisoformat(row["utc_date"])
                iso = d.isocalendar()
                if (
                    utc.tzinfo is None or utc.utcoffset() is None
                    or not e1.START_UTC <= utc.astimezone(UTC) < e1.EMBARGO
                    or row["utc_date"] in seen
                    or row.get("method_id") != method
                    or utc.astimezone(UTC).date() != d
                    or d.weekday() >= 5
                    or row.get("iso_week") != f"{iso.year}-W{iso.week:02d}"
                    or row.get("strategy_signal") not in (-1, 1)
                    or row.get("baseline_signal") not in (-1, 1)
                    or row.get("broker_executable_fill") is not False
                    or row.get("macro_news_asof_filtered") is not False
                    or any(not isinstance(row.get(k), (float, int))
                           or not math.isfinite(row[k]) for k in (
                        "strategy_gross_bps", "baseline_gross_bps", "paired_delta_bps"
                    ))
                    or abs(row["strategy_gross_bps"] - row["baseline_gross_bps"]
                           - row["paired_delta_bps"]) > 1e-7
                ):
                    raise ValueError("outcome temporal/causal signal or paired metric drift")
                seen.add(row["utc_date"])
        if set(ids) != set(METHODS) or len(set(ids)) != 7:
            raise ValueError("some of seven methods missing or duplicated")
        found[sym] = doc["seven_methods"]
    if set(found) != set(SYMBOLS) or len(code_sha) != 1:
        raise ValueError("incomplete universe or mixed source code across jobs")
    return found


def holm_adjusted(raw: list[float]) -> list[float]:
    """Holm FWER valid under dependence if input marginal p values are valid."""
    size = len(raw)
    order = sorted(range(size), key=lambda i: (raw[i], i))
    adjusted = [1.0] * size
    floor = 0.0
    for rank, idx in enumerate(order):
        floor = max(floor, min(1.0, raw[idx] * (size - rank)))
        adjusted[idx] = floor
    return adjusted


def analyze_period(
    entries: dict[str, list[dict[str, Any]]],
    period: str,
) -> dict[str, Any]:
    """All weeks resampled ONCE jointly across methods/assets; no independence fiction."""
    if period not in MIN:
        raise ValueError("unregistered period")
    n_floor, week_floor = MIN[period]
    groups: dict[str, list[dict[str, Any]]] = {}
    weeks_all: set[str] = set()
    for method in METHODS:
        for symbol in SYMBOLS:
            key = f"{method}__{symbol}"
            collection = next(p["paired_events"] for p in entries[symbol]
                              if p["method_id"] == method)
            chosen = [x for x in collection if (
                datetime.fromisoformat(x["reference_entry_utc"]).astimezone(UTC)
                < e1.DEV_CUTOFF
            ) == (period == "development")]
            groups[key] = chosen
            weeks_all.update(x["iso_week"] for x in chosen)
    weeks = sorted(weeks_all)
    n_week = len(weeks)
    w_index = {s:i for i,s in enumerate(weeks)}
    num = len(CELLS)
    sumdelta = np.zeros((n_week, num), dtype=np.float64)
    sumgross = np.zeros((n_week, num), dtype=np.float64)
    sumbaseline = np.zeros((n_week, num), dtype=np.float64)
    count = np.zeros((n_week, num), dtype=np.float64)
    for j, key in enumerate(CELLS):
        for row in groups[key]:
            i = w_index[row["iso_week"]]
            sumdelta[i, j] += row["paired_delta_bps"]
            sumgross[i, j] += row["strategy_gross_bps"]
            sumbaseline[i, j] += row["baseline_gross_bps"]
            count[i, j] += 1
    totals = count.sum(axis=0)
    observed = np.divide(sumdelta.sum(axis=0), totals, out=np.zeros(num), where=totals>0)
    gross = np.divide(sumgross.sum(axis=0), totals, out=np.zeros(num), where=totals>0)
    ctrl = np.divide(sumbaseline.sum(axis=0), totals, out=np.zeros(num), where=totals>0)
    eligible = np.array([
        totals[j] >= n_floor and sum(count[:, j] > 0) >= week_floor
        for j in range(num)
    ], dtype=bool)
    # One shared draw-of-weeks count matrix across all 231 cells preserves
    # cross-market and cross-method contemporaneous shocks by construction.
    if n_week:
        rng = np.random.default_rng(SEED if period == "development" else SEED+1)
        draws = rng.multinomial(n_week, [1/n_week]*n_week, size=B)
        boot_den = draws @ count
        boot_sum = draws @ sumdelta
        boot_mean = np.divide(
            boot_sum, boot_den, out=np.full_like(boot_sum, np.nan),
            where=boot_den>0,
        )
    else:
        boot_den = np.zeros((B, num))
        boot_mean = np.full((B, num), np.nan)
    results = []
    pvalues = []
    for j, key in enumerate(CELLS):
        method, symbol = key.split("__", 1)
        event_rows = groups[key]
        valid = np.isfinite(boot_mean[:, j])
        invalid_n = int(B - int(valid.sum()))
        enough = bool(eligible[j] and invalid_n == 0)
        if enough:
            samples = boot_mean[:, j]
            ci = [float(np.quantile(samples, 0.025)),
                  float(np.quantile(samples, 0.975))]
            # Null-centered paired-delta bootstrap two-sided p; p finite draw floor.
            centered = samples - observed[j]
            extreme = int(np.count_nonzero(abs(centered) >= abs(observed[j])))
            p = (extreme+1)/(B+1)
        else:
            ci, p = None, 1.0
        pvalues.append(p)
        base = {
            "cell_id":key, "method_id":method, "symbol":symbol,
            "family":registry.family_for(symbol),
            "source_cohort":("original12" if symbol in e1.source_g0.new_source.EXISTING
                             else "new21_icmarkets"),
            "preexisting_result":registry.cell_prior(method, symbol)["status"],
            "n_paired_days":len(event_rows),
            "n_iso_weeks":len({x["iso_week"] for x in event_rows}),
            "gross_mean_bps":float(gross[j]) if totals[j] else None,
            "control_gross_mean_bps":float(ctrl[j]) if totals[j] else None,
            "paired_delta_mean_bps":float(observed[j]) if totals[j] else None,
            "gross_positive_fraction":(
                sum(x["strategy_gross_bps"] > 0 for x in event_rows)/len(event_rows)
                if event_rows else None
            ),
            "delta_bootstrap_ci95_unadjusted_bps":ci,
            "delta_bootstrap_p_two_sided_exploratory":float(p),
            "bootstrap_zero_denominator_draws":invalid_n,
            "sample_gate":enough,
            "hypothetical_gross_minus_cost_RT_bps_NOT_NET": {
                str(c):float(gross[j]-c) if totals[j] else None for c in COSTS
            },
            "net_broker_certification":False,
        }
        results.append(base)
    adjusted = holm_adjusted(pvalues)
    if len(results) != 231:
        raise ValueError("all fixed 231 cells mandatory")
    for i, item in enumerate(results):
        item["p_Holm_FWER_231_exploratory"] = adjusted[i]
        item["holm_alpha05_screen_positive_not_certified"] = bool(
            item["sample_gate"] and adjusted[i] <= ALPHA_FWER
            and item["paired_delta_mean_bps"] is not None
            and item["paired_delta_mean_bps"] > 0
            and item["gross_mean_bps"] is not None
            and item["gross_mean_bps"] > 0
        )
    family = {}
    for method in METHODS:
        rr = [x for x in results if x["method_id"] == method]
        deltas = [x["paired_delta_mean_bps"] for x in rr
                  if x["paired_delta_mean_bps"] is not None]
        family[method] = {
            "markets":len(rr),
            "total_events":sum(x["n_paired_days"] for x in rr),
            "market_equal_weight_delta_descriptive_bps":mean(deltas) if deltas else None,
            "markets_with_sufficient_sample":sum(x["sample_gate"] for x in rr),
            "Holm_screen_pos":sum(x["holm_alpha05_screen_positive_not_certified"] for x in rr),
        }
    return {
        "period":period,
        "methods":family,
        "one_shared_synced_week_calendar":True,
        "calendar_week_clusters":n_week,
        "bootstrap_draws":B,
        "bootstrap_seed":SEED if period=="development" else SEED+1,
        "comparison_count_Holm":len(CELLS),
        "cells":results,
        "n_sample_gate_pass":sum(x["sample_gate"] for x in results),
        "n_no_event":sum(x["n_paired_days"] == 0 for x in results),
        "n_Holm_positive_screen":sum(x["holm_alpha05_screen_positive_not_certified"] for x in results),
        "net_certified":False,
    }


def analyze(root: Path) -> dict[str, Any]:
    evidence = load_signed_observations(root)
    development = analyze_period(evidence, "development")
    diagnostic = analyze_period(evidence, "temporal_diagnostic")
    if len(development["cells"]) != 231 or len(diagnostic["cells"]) != 231:
        raise ValueError("231 exact cross-market rule tests missing")
    jointly_screening = [
        d["cell_id"] for d,t in zip(development["cells"], diagnostic["cells"], strict=True)
        if d["cell_id"]==t["cell_id"]
        and d["holm_alpha05_screen_positive_not_certified"]
        and t["holm_alpha05_screen_positive_not_certified"]
    ]
    return {
        "identity":IDENTITY,
        "status":"E2_231_GROSS_RESEARCH_ONLY_NOT_NET_NOT_OOS_VIRGIN",
        "original_g0_source_sha256":e1.SOURCE_33_SHA,
        "pre_outcome_D1_sha":e1.PREREG_SHA,
        "markets":33, "methods":7, "all_fixed_cells":231,
        "development":development, "temporal_diagnostic":diagnostic,
        "holm_screen_both_periods_NOT_EDGE_CERTIFIED":jointly_screening,
        "old_33_sweep_results_not_independent_confirmation":True,
        "g1_historical_bidask_not_measured":True,
        "macro_news_known_asof_not_filtered":True,
        "2024_09_17_onward_prices_embargoed":True,
        "week_clusters_not_independent_daily_events":True,
        "future_2_to_4_week_block_bootstrap_sensitivity_pending":True,
        "net_PF_sharpe_sortino_DD_not_certified":True,
        "traders_certified":0, "production_untouched":True,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("signed_e1_33", type=Path)
    parser.add_argument("dest", type=Path)
    args = parser.parse_args()
    result = analyze(args.signed_e1_33)
    args.dest.mkdir(parents=True, exist_ok=True)
    file = args.dest / "qore-native-e2-33x7-full-gross-results.json"
    file.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    file.with_name(file.name + ".sha256").write_text(
        g0.sha256(file) + f"  {file.name}\n", encoding="utf-8"
    )
    print(json.dumps({
        "status":result["status"], "cells":231,
        "dev_sample_gate":result["development"]["n_sample_gate_pass"],
        "diagnostic_sample_gate":result["temporal_diagnostic"]["n_sample_gate_pass"],
        "dev_Holm_screen":result["development"]["n_Holm_positive_screen"],
        "diag_Holm_screen":result["temporal_diagnostic"]["n_Holm_positive_screen"],
        "net_certified":False,
    },sort_keys=True))


if __name__ == "__main__":
    main()
