"""W2 PADE reproducible posthoc only; reads signed first GROSS result JSON.

No OHLC, no PnL recomputation, no parameter or market selection.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from qore.research.alpha2_intermarket import MARKETS, sha256_file

FIRST_GROSS_RUN = 38283326547
FIRST_GROSS_HEAD = "3f81e41ba6af5c226402f68621db7f78980231fe"
FILE = "alpha2-w2-pade-33-first-gross-panel.json"


def summarize(source: Path) -> dict:
    ledger_lines = (source / "OUTPUT_SHA256SUMS.txt").read_text(encoding="utf-8").splitlines()
    expected = {}
    for line in ledger_lines:
        parts = line.split()
        if len(parts) != 2 or parts[1] in expected:
            raise ValueError("invalid original GROSS checksum scope")
        expected[parts[1]] = parts[0]
    if set(expected) != {FILE, "exact-code-head-sha.txt"}:
        raise ValueError("exact original GROSS SHA witness missing")
    for filename, value in expected.items():
        if sha256_file(source / filename) != value:
            raise ValueError("source original GROSS artifact tampering detected")
    if (source / "exact-code-head-sha.txt").read_text(encoding="utf-8").strip() != FIRST_GROSS_HEAD:
        raise ValueError("exact original gross code-head drift")
    original = json.loads((source / FILE).read_text(encoding="utf-8"))
    if (original.get("identity") != "QORE_ALPHA2_W2_PADE_33_FIRST_PAIRED_GROSS_ONLY_PANEL_V1"
            or original.get("status") != "UNDERPOWERED"
            or original.get("markets") != 33
            or original.get("original_signals") != 265
            or original.get("total_evaluable_paired") != 265
            or original.get("opposite_direction_cases") != 134
            or original.get("traders_certified") != 0
            or original.get("NET_PF_Sharpe_Sortino_DD_not_computed") is not True):
        raise ValueError("original W2 source economic status/count drift")
    markets = original["per_market_all33"]
    if set(markets) != set(MARKETS):
        raise ValueError("original W2 market roster incomplete")
    original_eras = original["eras"]
    if (original_eras["DEVELOPMENT"]["paired_evaluable"] != 220
            or original_eras["DIAGNOSTIC"]["paired_evaluable"] != 45
            or original_eras["DEVELOPMENT"]["minimum_sample_gate"] is not True
            or original_eras["DIAGNOSTIC"]["minimum_sample_gate"] is not False):
        raise ValueError("original 220/45 Gate status drift")
    screening = Counter()
    for symbol in sorted(MARKETS):
        screening.update(markets[symbol]["rule_exclusion_counts"])
    by_era = {}
    for era, row in original_eras.items():
        by_era[era] = {
            "signals": row["original_signals"],
            "paired": row["paired_evaluable"],
            "sample_gate": row["minimum_sample_gate"],
            "first_gross_bps": row["mean_gross_strategy_bps_proxy"],
            "first_paired_delta_bps": row["paired_delta_mean_bps_proxy"],
            "original_block_CI": {
                f"{n}wk": row["common_calendar_synchronized_bootstrap"][f"{n}wk"]
                for n in (1, 2, 4)
            },
            "by_year_descriptive": row["year_descriptive"],
            "by_broker_source_cohort": row["per_cohort_paired"],
            "censorship": row["censor_reason_counts"],
        }
    return {
        "identity": "QORE_ALPHA2_W2_FIRST33_POSTHOC_BLOCKER_CENSUS_ONLY",
        "source_run": FIRST_GROSS_RUN,
        "source_head": FIRST_GROSS_HEAD,
        "source_sha256": expected[FILE],
        "markets": 33,
        "original_signals": 265,
        "opposing_baseline_direction": 134,
        "markets_with_zero_signals": sum(v["signals"] == 0 for v in markets.values()),
        "market_count_by_family": original["by_family"],
        "rule_exclusion_counts_ALL_MARKETS_NOT_SELECTED":dict(screening.most_common()),
        "by_era":by_era,
        "replay_is_prior_consumed_exploratory":True,
        "no_new_OHLC_or_return_access":True,
        "no_posthoc_alpha_retuning":True,
        "no_real_bidask_or_macro_PIT":True,
        "UTC001_certified":False,
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("original_signed_w2", type=Path)
    p.add_argument("output", type=Path)
    args = p.parse_args()
    result = summarize(args.original_signed_w2)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "pade-w2-33-original-posthoc-census.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "markets": 33, "signals":265, "zero_signal_markets":result["markets_with_zero_signals"],
        "exclusion_top5":list(result["rule_exclusion_counts_ALL_MARKETS_NOT_SELECTED"].items())[:5],
        "families":result["market_count_by_family"],
        "era_bootstrap_4week": {
            e:row["original_block_CI"]["4wk"]
            for e,row in result["by_era"].items()
        },
        "no_net_claim":True,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
