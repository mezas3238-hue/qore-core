"""Freeze source-only four-market Phase-0 from exposed original E1 times.

No network, broker credentials, trading, PnL, execution or shard download.
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
from collections import Counter
from datetime import datetime
from pathlib import Path

ROOT=Path(os.environ.get("QORE_E1_REPORT_DIR","/mnt/data/qore_native_g1_all33_clock_audit"))
COHORT={
    "EURGBP":("EURGBP","FX_CROSS"),
    "SP500":("US500","INDEX_ALIAS_CONTRACT_UNHOMOLOGATED"),
    "USDJPY":("USDJPY","FX_MAJOR"),
    "XAGUSD":("XAGUSD","PRECIOUS_METAL"),
}
DATES={"2021-03-16","2023-03-21"}
PER_MARKET_EVENTS={"EURGBP":10,"SP500":12,"USDJPY":12,"XAGUSD":11}
PER_MARKET_SHARDS={"EURGBP":11,"SP500":12,"USDJPY":14,"XAGUSD":12}
MAX_SOURCE_WINDOWS=49
MAX_PROVIDER_SIDE_REQUESTS=98


def utc_date(text:str)->datetime:
    clock=datetime.fromisoformat(text)
    if clock.tzinfo is None or clock.utcoffset().total_seconds()!=0:
        raise ValueError("PHASE0_TIMEZONE_MUST_BE_UTC")
    return clock


def main()->None:
    base=json.loads((ROOT/"summary.json").read_text())
    exposed=json.loads((ROOT/"calendar_two_dates_pilot_summary.json").read_text())
    if (base.get("all_original_research_E1_event_count")!=373611
        or base.get("universe_markets_signed_source_verified")!=33
        or base.get("net_authorized") is not False
        or exposed.get("original_source_event_count")!=368
        or exposed.get("net_authorized") is not False):
        raise ValueError("PHASE0_PREVIOUS_E1_SOURCE_INTEGRITY_NOT_PASS")
    market_days={(x["canonical_symbol"],x["UTC_date"]):x
                 for x in exposed["per_market_day"]}
    rows=[]
    counts=Counter()
    input_path=ROOT/"calendar_two_dates_source_only_pilot_windows.csv"
    with input_path.open(newline="",encoding="utf-8") as f:
        for source in csv.DictReader(f):
            sym=source["market"]
            if sym not in COHORT:
                continue
            day=source["date"]
            if day not in DATES or (sym,day) not in market_days:
                raise ValueError("PHASE0_UNFROZEN_OR_UNREGISTERED_E1_SOURCE_DATE")
            start=utc_date(source["source_start_utc"])
            end=utc_date(source["source_end_exclusive_utc"])
            if (start.date().isoformat()!=day or start>=end
                or (end-start).total_seconds()>1800
                or source["source_only_no_pnl"]!="True"
                or source["side_requests_at_least"]!="2"):
                raise ValueError("PHASE0_MALFORMED_CLOCK_OR_NON_SOURCE_EVENT")
            broker_name,kind=COHORT[sym]
            rows.append({
                "canonical_symbol":sym,
                "current_provider_symbol_candidate":broker_name,
                "source_kind":kind,
                "research_date":day,
                "source_start_utc":start.isoformat(),
                "source_end_exclusive_utc":end.isoformat(),
                "side_requests_minimum":2,
                "contract_G0_G1_homologated":False,
                "broker_quote_download_authorized":False,
                "historical_NET_authorized":False,
            })
            counts[sym]+=1
    if len(rows)!=MAX_SOURCE_WINDOWS or dict(counts)!=PER_MARKET_SHARDS:
        raise ValueError("PHASE0_SOURCE_FOUR_ASSET_EXACT_SHARD_BUDGET_DRIFT")
    e1count=Counter()
    for (sym,_),market in market_days.items():
        if sym in COHORT:
            e1count[sym]+=market["original_E1_method_events"]
    if dict(e1count)!=PER_MARKET_EVENTS or sum(e1count.values())!=45:
        raise ValueError("PHASE0_E1_ORIGINAL_METHOD_EVENT_COUNT_DRIFT")
    rows.sort(key=lambda x:(
        x["canonical_symbol"],x["research_date"],x["source_start_utc"]
    ))
    dest=ROOT/"phase0_four_market_quote_windows.csv"
    with dest.open("w",newline="",encoding="utf-8") as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    summary={
        "identity":"QORE_NATIVE_G1_33X7_PHASE0_FOUR_MARKET_QUOTE_SOURCE_ONLY_REQUEST_PLAN_V1",
        "status":"SOURCE_SHARDS_BUDGETED_NOT_QUEUED_OR_DOWNLOADED",
        "original_E1_source_events":45,
        "current_provider_alias_G0_contract_equivalence_verified":False,
        "source_shards_by_market":dict(sorted(counts.items())),
        "source_E1_events_by_market":dict(sorted(e1count.items())),
        "source_bounded_shards":MAX_SOURCE_WINDOWS,
        "minimum_BIDASK_requests":MAX_PROVIDER_SIDE_REQUESTS,
        "hasMore_extra_requests_unbudgeted":True,
        "original_E1_exposed_dates":sorted(DATES),
        "source_only_calendar_already_researched_no_new_holdout":True,
        "source_raw_price_storage_license_and_private_vault_confirmed":False,
        "source_capture_workflow_enabled":False,
        "broker_api_credentials_used":False,
        "broker_api_calls_executed":0,
        "historical_NET_authorized":False,
        "certified_traders":0,
    }
    p=ROOT/"phase0_four_market_source_plan_NOT_NET.json"
    p.write_text(json.dumps(summary,indent=2,sort_keys=True)+"\n")
    (ROOT/"PHASE0_SHA256SUMS.txt").write_text(
        "".join(hashlib.sha256(f.read_bytes()).hexdigest()+"  "+f.name+"\n"
                for f in (dest,p))
    )
    print(json.dumps({
        "market_count":4,"original_E1_events":45,
        "bounded_source_shards":len(rows),
        "minimum_BIDASK_side_requests":98,
        "broker_calls_made":0,"NET":False,
    },sort_keys=True))


if __name__=="__main__":
    main()
