"""Independent regression: 373611 E1 clocks, 412012 source shards, never NET."""
from __future__ import annotations

import csv
import gzip
import hashlib
import json
import os
from pathlib import Path

FOLDER=Path(os.environ.get("QORE_E1_REPORT_DIR","/mnt/data/qore_native_g1_all33_clock_audit"))


def sha(value:bytes)->str:
    return hashlib.sha256(value).hexdigest()


def main()->None:
    original=json.loads((FOLDER/"summary.json").read_bytes())
    exposed=json.loads((FOLDER/"calendar_two_dates_pilot_summary.json").read_bytes())
    if (original["universe_markets_signed_source_verified"]!=33
        or original["frozen_method_count"]!=7
        or original["all_original_research_E1_event_count"]!=373611
        or original["source_clock_windows_before_dedup"]!=747222
        or original["deduplicated_native_quote_history_shards_max_30min"]!=412012
        or original["minimum_original_BIDASK_side_history_requests"]!=824024
        or original["original_E1_events_by_source_period"]!={"DEV":278983,"DIAG":94628}
        or original["original_E1_231_Holm_FDR_E3_positive_replicated_edges"]!=0
        or original["actual_BIDASK_requested_in_this_audit"] is not False
        or original["source_G0_vs_G1_broker_contract_homologated"] is not False
        or original["raw_tick_storage_license_and_private_vault_confirmed"] is not False
        or original["original_E1_signs_gross_returns_PnL_not_exported"] is not True
        or original["net_authorized"] is not False
        or original["certified_traders"]!=0):
        raise ValueError("G1_E1_ALL33_ORIGINAL_SOURCE_SUMMARY_CONTRACT_DRIFT")
    if (exposed["original_source_event_count"]!=368
        or exposed["market_day_combinations"]!=66
        or exposed["dedup_quote_shards"]!=403
        or exposed["minimum_read_only_side_requests"]!=806
        or exposed["long_term_private_archival_license_confirmed"] is not False):
        raise ValueError("G1_EXPOSED_TWO_DATE_SOURCE_BUDGET_DRIFT")
    if sum(original["original_E1_events_by_method"].values())!=373611:
        raise ValueError("G1_SEVEN_METHOD_EVENT_SUM_MISMATCH")
    if sum(x["original_E1_method_events"] for x in exposed["per_market_day"]
           if x["canonical_symbol"] in {"EURUSD","GBPUSD","USDJPY","XAGUSD","SP500"})!=56:
        raise ValueError("G1_ORIGINAL_FIVE_MARKET_56_CLOCK_NOT_REPRODUCED")
    per_symbol=list(csv.DictReader((FOLDER/"source_coverage_budget_by_symbol.csv").open()))
    if len(per_symbol)!=33 or sum(int(x["method_opportunities"]) for x in per_symbol)!=373611:
        raise ValueError("G1_MARKET_SOURCE_CONTRACT_MISMATCH")
    with (FOLDER/"deduplicated_original_E1_native_quote_request_shards.csv").open() as file:
        shards=sum(1 for _ in csv.DictReader(file))
    if shards!=412012:
        raise ValueError("G1_ORIGINAL_QUOTE_SHARD_COUNT_MISMATCH")
    signed=json.loads((FOLDER/"signed_E1_33_GitHub_artifact_custody.json").read_bytes())
    if len(signed)!=33 or any(len(x["github_zip_sha256_verified"])!=64 for x in signed.values()):
        raise ValueError("G1_ORIGINAL_33_SOURCE_CUSTODY_MISSING")
    six=set()
    n=0
    with gzip.open(FOLDER/"original_E1_event_clocks_only.jsonl.gz","rt",encoding="utf-8") as file:
        for line in file:
            e=json.loads(line)
            n+=1
            if (e["real_broker_fill"] is not False or e["outcome_exported"] is not False
                or e["entry_research_utc"]>="2024-09-17T00:00:00+00:00"
                or {"strategy_gross_bps","baseline_gross_bps","strategy_signal",
                    "baseline_signal","paired_delta_bps","pnl","profit"}.intersection(e)):
                raise ValueError("G1_E1_FUTURE_OUTCOME_OR_EMBARGO_LEAK")
            if (e["method_id"] in {"SWEEP_RECLAIM","RANGE_BREAK_CONT"}
                and e["entry_research_utc"] in {"2021-03-16T13:00:00+00:00","2023-03-21T13:00:00+00:00"}
                and e["symbol"] in {"SP500","GBPUSD","USDJPY","XAGUSD"}):
                six.add((e["symbol"],e["method_id"],e["entry_research_utc"]))
    if n!=373611 or len(six)!=6:
        raise ValueError("G1_E1_6_SIGNED_ORIGINAL_METHOD_CLOCK_IDENTITIES_DRIFT")
    checks=FOLDER/"SHA256SUMS.txt"
    files=sorted(p for p in FOLDER.iterdir() if p.is_file() and p.name!="SHA256SUMS.txt")
    checks.write_text("".join(sha(p.read_bytes())+"  "+p.name+"\n" for p in files))
    print("VERIFIED_ALL33_E1_SIGNED_373611_CLOCKS_412012_DEDUP_SHARDS_NO_NET")


if __name__=="__main__":
    main()
