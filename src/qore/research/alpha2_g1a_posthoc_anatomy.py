"""Post-outcome Alpha2 G1A diagnostics; NO new prices, hypotheses or retuning."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from qore.research.alpha2_intermarket import sha256_file

ORIGINAL_RUN = 38270999595
ORIGINAL_HEAD = "b406be34e16e61b7b4c042f31f95cf38a45f4e07"
ORIGINAL_FILE = "alpha2-g1a-paired-33-first-gross-panel.json"


def read_signed(root: Path) -> tuple[dict, str]:
    ledger = root / "OUTPUT_SHA256SUMS.txt"
    rows = [v.split() for v in ledger.read_text(encoding="utf-8").splitlines()]
    digest = {row[1]: row[0] for row in rows if len(row) == 2}
    if set(digest) != {ORIGINAL_FILE, "exact-code-head-sha.txt"}:
        raise ValueError("G1A original artifact checksum scope invalid")
    for name, expected in digest.items():
        if sha256_file(root / name) != expected:
            raise ValueError("G1A exact original SHA mismatch")
    if (root / "exact-code-head-sha.txt").read_text(encoding="utf-8").strip() != ORIGINAL_HEAD:
        raise ValueError("G1A original code identity drift")
    raw = json.loads((root / ORIGINAL_FILE).read_text(encoding="utf-8"))
    if (raw.get("identity") != "QORE_ALPHA2_G1A_PAIRED_GROSS_PANEL_FIRST_OUTCOME_V1"
            or raw.get("source_head") != ORIGINAL_HEAD
            or raw.get("research_verdict") != "UNDERPOWERED"
            or raw.get("markets") != 33
            or raw.get("original_signals") != 224
            or raw.get("total_paired_gross_events") != 176
            or raw.get("net_pf_sharpe_sortino_dd_not_computed") is not True):
        raise ValueError("G1A report evidence status unexpected")
    return raw, digest[ORIGINAL_FILE]


def diagnose(root: Path) -> dict:
    data, digest = read_signed(root)
    by_era: dict[str, dict] = {}
    total_censored = 0
    for era, x in data["eras"].items():
        signals = x["original_signals"]
        paired = x["evaluable_paired_events"]
        if paired > signals:
            raise ValueError("evaluable gross count exceeds source signals")
        status = x["reason_count"]
        if sum(status.values()) != signals - paired:
            raise ValueError("censor reason counts do not reconcile")
        total_censored += signals - paired
        by_era[era] = {
            "original_signals": signals, "evaluable_paired": paired,
            "censored_unpaired": signals-paired, "status_counts": status,
            "source_sample_gate": x["sample_gate_predeclared"],
            "week_clusters": x["weeks_with_evaluable_events"],
            "gross_mean_bps_already_observed": x["gross_mean_bps_proxy"],
            "delta_mean_bps_already_observed": x["paired_delta_mean_bps_proxy"],
            "bootstrap_1_2_4_week_as_already_observed": x[
                "bootstrap_calendar_synced_all_markets"],
            "yearly_original_descriptive": x["year_descriptive"],
        }
    if total_censored != 48:
        raise ValueError("G1A censored population not 48")
    market = data["by_symbol"]
    if len(market) != 33 or sum(x["signals"] for x in market.values()) != 224:
        raise ValueError("33-market census/signals mismatch")
    return {
        "identity": "QORE_ALPHA2_G1A_POSTHOC_SOURCE_ONLY_FAILURE_ANATOMY_V1",
        "original_run": ORIGINAL_RUN, "original_head": ORIGINAL_HEAD,
        "original_gross_json_sha256": digest,
        "scope": "DESCRIPTIVE_POSTHOC_NO_NEW_OHLC_NO_NEW_HYPOTHESIS",
        "original_signals": 224, "observed_paired": 176,
        "censored": total_censored,
        "by_era": by_era,
        "markets_with_zero_events": sum(x["signals"] == 0 for x in market.values()),
        "top_10_markets_by_number_of_signals_DESCRIPTIVE_ONLY": sorted(
            [{"symbol": sym, "signals": m["signals"], "paired": m["paired"]}
             for sym, m in market.items()],
            key=lambda m: (-m["signals"], m["symbol"]))[:10],
        "no_retuning_authorized": True,
        "no_new_statistical_discovery": True,
        "news_PIT_and_real_broker_costs_missing": True,
        "utc001_certified": False,
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("original_artifact", type=Path)
    p.add_argument("output", type=Path)
    args = p.parse_args()
    result = diagnose(args.original_artifact)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "alpha2-g1a-posthoc-anatomy.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps({
        "censored": result["censored"],
        "eras": {
            era: {"reasons": row["status_counts"],
                  "paired": row["evaluable_paired"],
                  "weeks": row["week_clusters"],
                  "bootstrap_4wk": row["bootstrap_1_2_4_week_as_already_observed"]["4wk"]}
            for era,row in result["by_era"].items()
        },
        "markets_with_zero_events": result["markets_with_zero_events"],
        "top_market_counts": result[
            "top_10_markets_by_number_of_signals_DESCRIPTIVE_ONLY"],
        "scope": result["scope"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
