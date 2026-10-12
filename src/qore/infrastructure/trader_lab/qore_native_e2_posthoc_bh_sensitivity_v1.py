"""POST HOC FDR sensitivity for the already executed 33x7 E2 gross study.

No price data, no additional return estimates, no parameter retuning.
The exact 231×2 signed p-values are reused. Not prospective confirmation.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import qore_native_existing12_m5_g0_v1 as g0
from qore.infrastructure.trader_lab import qore_native_e2_33x7_holm_synchronized_weeks_v1 as e2

IDENTITY = "QORE_NATIVE_33X7_E2_POSTHOC_FDR_SENSITIVITY_V1"
PARENT_RUN = 38257207836
PARENT_CODE_SHA = "dfe78f115957a40f4188c30e78bd7f88c2ce6c42"
PARENT_JSON_SHA256 = "5161dbdf157805af3e37957ec25acad3657962a50c99d214883005cb03945f80"
PARENT_NAME = "qore-native-e2-33x7-full-gross-results.json"
RATES = (0.05, 0.10)
NOMINAL_RATES = (0.05, 0.10)
PERIODS = ("development", "temporal_diagnostic")


def bh(pvalues: list[float]) -> list[float]:
    """Benjamini-Hochberg step-up q-values, exploratory under unknown dependence."""
    if not pvalues or any(not isinstance(p, (float, int)) or not math.isfinite(p)
                          or not 0 <= p <= 1 for p in pvalues):
        raise ValueError("nonempty valid probability vector expected")
    n = len(pvalues)
    order = sorted(range(n), key=lambda i: (pvalues[i], i))
    out = [1.0] * n
    running = 1.0
    for rank in reversed(range(n)):
        index = order[rank]
        running = min(running, float(pvalues[index]) * n / (rank+1))
        out[index] = running
    return out


def load_signed(root: Path) -> dict[str, Any]:
    # Immutable GH artifact #11749739981 from Actions #38257207836.
    ledger = g0.digest_ledger(root / "OUTPUT_SHA256SUMS.txt")
    side = g0.digest_ledger(root / (PARENT_NAME + ".sha256"))
    file = g0.verified_file(root, ledger, PARENT_NAME)
    if (ledger.get(PARENT_NAME) != PARENT_JSON_SHA256
            or side.get(PARENT_NAME) != PARENT_JSON_SHA256):
        raise ValueError("E2 immutable market-result SHA drift")
    g0.verified_file(root, side, PARENT_NAME)
    head = g0.verified_file(root, ledger, "exact-code-head-sha.txt")
    if head.read_text(encoding="utf-8").strip() != PARENT_CODE_SHA:
        raise ValueError("E2 tested HEAD SHA drift")
    return json.loads(file.read_text(encoding="utf-8"))


def analyze(result: dict[str, Any]) -> dict[str, Any]:
    if (
        result.get("identity") != e2.IDENTITY
        or result.get("status") != "E2_231_GROSS_RESEARCH_ONLY_NOT_NET_NOT_OOS_VIRGIN"
        or result.get("original_g0_source_sha256") != e2.e1.SOURCE_33_SHA
        or result.get("markets") != 33
        or result.get("methods") != 7
        or result.get("all_fixed_cells") != 231
        or result.get("2024_09_17_onward_prices_embargoed") is not True
        or result.get("traders_certified") != 0
        or result.get("g1_historical_bidask_not_measured") is not True
        or result.get("macro_news_known_asof_not_filtered") is not True
        or result.get("production_untouched") is not True
    ):
        raise ValueError("parent E2 signed-study identity or live guard drift")
    reports: dict[str, Any] = {}
    byperiod: dict[str, list[dict[str, Any]]] = {}
    for period in PERIODS:
        row = result.get(period)
        entries = row.get("cells") if isinstance(row, dict) else None
        if not isinstance(entries, list) or len(entries) != 231:
            raise ValueError("E2 must include all 231 cells, even underpowered")
        if (row.get("comparison_count_Holm") != 231
                or row.get("one_shared_synced_week_calendar") is not True
                or row.get("bootstrap_draws") != 20000
                or row.get("net_certified") is not False):
            raise ValueError("E2 week/bootstrap/Net integrity drift")
        ids = [x.get("cell_id") for x in entries]
        if ids != list(e2.CELLS):
            raise ValueError("E2 231 frozen cell order/id changed")
        p: list[float] = []
        for x in entries:
            p_value = x.get("delta_bootstrap_p_two_sided_exploratory")
            if (not isinstance(p_value, (float, int))
                    or not math.isfinite(p_value)
                    or not 0 <= p_value <= 1
                    or x.get("net_broker_certification") is not False
                    or x.get("preexisting_result") != e2.registry.cell_prior(
                        x["method_id"], x["symbol"]
                    )["status"]):
                raise ValueError("E2 marginal p, net or prior null drift")
            p.append(float(p_value))
        if any(abs(raw - observed) > 1e-10 for raw, observed in zip(
            e2.holm_adjusted(p),
            (x["p_Holm_FWER_231_exploratory"] for x in entries), strict=True
        )):
            raise ValueError("unreconciled original Holm inference")
        q = bh(p)
        enriched = []
        for i, x in enumerate(entries):
            enriched.append({
                "cell_id": x["cell_id"],
                "method_id": x["method_id"],
                "symbol": x["symbol"],
                "prior_exposure": x["preexisting_result"],
                "n": x["n_paired_days"],
                "n_iso_weeks": x["n_iso_weeks"],
                "sample_gate": x["sample_gate"],
                "gross_mean_bps": x["gross_mean_bps"],
                "paired_delta_bps": x["paired_delta_mean_bps"],
                "nominal_p_two_sided": p[i],
                "Holm_adjusted_p": x["p_Holm_FWER_231_exploratory"],
                "BH_FDR_q_posthoc": q[i],
                "is_positive_delta_and_gross": (
                    x["sample_gate"] is True
                    and x["paired_delta_mean_bps"] is not None
                    and x["paired_delta_mean_bps"] > 0
                    and x["gross_mean_bps"] is not None
                    and x["gross_mean_bps"] > 0
                ),
            })
        byperiod[period] = enriched
        bymethod: dict[str, dict[str, int]] = {}
        for method in e2.METHODS:
            z = [x for x in enriched if x["method_id"] == method]
            bymethod[method] = {
                "n_markets": len(z),
                "positive_nominal_5pct": sum(
                    x["is_positive_delta_and_gross"] and x["nominal_p_two_sided"] <= .05
                    for x in z
                ),
                "positive_BH_10pct": sum(
                    x["is_positive_delta_and_gross"] and x["BH_FDR_q_posthoc"] <= .10
                    for x in z
                ),
            }
        reports[period] = {
            "n_all_cells": 231,
            "n_sample_gate": sum(x["sample_gate"] for x in enriched),
            "n_positive_delta_gross_nominal_5pct": sum(
                x["is_positive_delta_and_gross"] and x["nominal_p_two_sided"] <= .05
                for x in enriched
            ),
            "n_positive_delta_gross_nominal_10pct": sum(
                x["is_positive_delta_and_gross"] and x["nominal_p_two_sided"] <= .10
                for x in enriched
            ),
            "n_nominal_5pct_any_sign": sum(x["nominal_p_two_sided"] <= .05 for x in enriched),
            "n_Holm_5pct_any_sign": sum(x["Holm_adjusted_p"] <= .05 for x in enriched),
            "BH_FDR_thresholds": {
                str(rate): {
                    "n_any_sign": sum(x["BH_FDR_q_posthoc"] <= rate for x in enriched),
                    "n_positive_delta_gross": sum(
                        x["is_positive_delta_and_gross"] and x["BH_FDR_q_posthoc"] <= rate
                        for x in enriched
                    ),
                    "cell_ids": [x["cell_id"] for x in enriched
                                 if x["BH_FDR_q_posthoc"] <= rate],
                } for rate in RATES
            },
            "per_method_descriptive_only": bymethod,
            "all_cells_qvalues_including_nulls": enriched,
        }
    both_positive = {}
    for label, cutoff in (
        ("nominal_two_sided_5pct", .05),
        ("nominal_two_sided_10pct", .10),
    ):
        both_positive[label] = [
            d["cell_id"]
            for d,t in zip(byperiod["development"],
                           byperiod["temporal_diagnostic"], strict=True)
            if d["is_positive_delta_and_gross"]
            and t["is_positive_delta_and_gross"]
            and d["nominal_p_two_sided"] <= cutoff
            and t["nominal_p_two_sided"] <= cutoff
        ]
    both_positive["FDR_BH_10pct"] = [
        d["cell_id"]
        for d,t in zip(byperiod["development"],
                       byperiod["temporal_diagnostic"], strict=True)
        if d["is_positive_delta_and_gross"]
        and t["is_positive_delta_and_gross"]
        and d["BH_FDR_q_posthoc"] <= .10
        and t["BH_FDR_q_posthoc"] <= .10
    ]
    return {
        "identity": IDENTITY,
        "status": "POSTHOC_EXPLORATORY_SENSITIVITY_NOT_PREREG_CONFIRMED",
        "parent_run": PARENT_RUN,
        "parent_code_sha": PARENT_CODE_SHA,
        "parent_signed_json_sha256": PARENT_JSON_SHA256,
        "reuses_original_231_p_values_no_price_data": True,
        "posthoc_after_Holm_result_known": True,
        "BH_guarantee_under_arbitrary_signed_market_dependence": False,
        "no_fresh_OOS_or_2024_plus_prices": True,
        "actual_bidask_costs_unknown": True,
        "outcomes_by_period": reports,
        "positive_both_periods": both_positive,
        "not_certified_regardless_of_q": True,
        "traders_certified": 0,
        "production_untouched": True,
        "next_action": "POSTHOC_SCREEN_ONLY_PREFER_INDEPENDENT_FUTURE_VALIDATION_AND_MEASURED_EXECUTION_COSTS",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("original_parent_artifact", type=Path)
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()
    report = analyze(load_signed(args.original_parent_artifact))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    path = args.output_dir / "qore-native-e2-33x7-posthoc-bh-fdr-audit.json"
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8")
    path.with_name(path.name + ".sha256").write_text(
        g0.sha256(path) + f"  {path.name}\n", encoding="utf-8"
    )
    print(json.dumps({
        "phase": "POSTHOC_NO_NEW_RETURNS",
        "source_sha256": report["parent_signed_json_sha256"],
        "dev": {k:report["outcomes_by_period"]["development"][k]
                for k in ("n_nominal_5pct_any_sign", "n_positive_delta_gross_nominal_5pct", "n_Holm_5pct_any_sign")},
        "diag": {k:report["outcomes_by_period"]["temporal_diagnostic"][k]
                for k in ("n_nominal_5pct_any_sign", "n_positive_delta_gross_nominal_5pct", "n_Holm_5pct_any_sign")},
        "both_positive_nominal5": len(report["positive_both_periods"]["nominal_two_sided_5pct"]),
        "both_positive_BH10": len(report["positive_both_periods"]["FDR_BH_10pct"]),
    },sort_keys=True))


if __name__ == "__main__":
    main()
