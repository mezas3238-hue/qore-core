"""Read-only 33-market original E1 UTC research clock and bounded quote-source plan.

This script ingests E1 gross-labelled source archives but never exports or
computes a gross return, sign, financial trade or executable broker quote.
"""
from __future__ import annotations

import csv
import gzip
import hashlib
import json
import os
import zipfile
from collections import Counter
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(os.environ.get("QORE_E1_DATA_ROOT", "/mnt/data"))
OUT = Path(os.environ.get("QORE_E1_REPORT_DIR", str(ROOT / "qore_native_g1_all33_clock_audit")))
E1_SHA = "dfe78f115957a40f4188c30e78bd7f88c2ce6c42"
G0_SHA = "1291d5c2efb4e51c2698ea25ad420a01a213dc405b5070c37efbce4131606b85"
REG_SHA = "67022daf7e2c3335eda991fd217df83fc1a34bc4"
METHODS = {
    "REVERSAL_12H":240, "POST_OPEN_CONT":120, "PERSISTENCE_12H":240,
    "OPEN_INITIAL_REACTION":15, "SWEEP_RECLAIM":120, "TREND_MULTI_DAY":240,
    "RANGE_BREAK_CONT":120,
}
ORIGINAL12 = frozenset(("AUDJPY","AUDUSD","EURUSD","GBPJPY","GBPUSD",
    "USDCAD","USDJPY","NAS100","SP500","US30","XAUUSD","XAGUSD"))
INDICES = frozenset(("NAS100","SP500","US30"))
METALS = frozenset(("XAUUSD","XAGUSD"))
LOWER = datetime(2016,9,17,tzinfo=UTC)
EMBARGO = datetime(2024,9,17,tzinfo=UTC)


def sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def expected_clock(symbol: str, method: str, day: date) -> datetime:
    if method in ("REVERSAL_12H","PERSISTENCE_12H","TREND_MULTI_DAY"):
        return datetime(day.year,day.month,day.day,16,tzinfo=UTC)
    if method in ("SWEEP_RECLAIM","RANGE_BREAK_CONT"):
        return datetime(day.year,day.month,day.day,13,tzinfo=UTC)
    if symbol in INDICES:
        timezone,hour,minute = "America/New_York",9,30
    elif symbol in METALS:
        timezone,hour,minute = "America/New_York",8,0
    else:
        timezone,hour,minute = "Europe/London",8,0
    local = datetime(day.year,day.month,day.day,hour,minute,tzinfo=ZoneInfo(timezone))
    extra = 15 if method=="OPEN_INITIAL_REACTION" else 30
    return (local+timedelta(minutes=extra)).astimezone(UTC)


def group_windows(windows: list[tuple[int,int]]) -> list[tuple[int,int]]:
    """Union overlapping and adjacent source intervals, cap at 30m."""
    if not windows:
        return []
    pairs=sorted(windows)
    unions=[]
    left,right=pairs[0]
    for a,b in pairs[1:]:
        if a<=right:
            right=max(b,right)
        else:
            unions.append((left,right))
            left,right=a,b
    unions.append((left,right))
    out=[]
    for left,right in unions:
        while left<right:
            nxt=min(right,left+1800)
            out.append((left,nxt))
            left=nxt
    return out


def load_register() -> dict[str,tuple[int,str]]:
    path=OUT/"artifact_register.txt"
    records={}
    for line in path.read_text(encoding="utf-8").splitlines():
        symbol,num,checksum=line.split()
        if symbol in records or len(checksum)!=64 or not num.isdecimal():
            raise ValueError("E1_REGISTER_DUPLICATE_OR_UNSAFE")
        records[symbol]=(int(num),checksum)
    if len(records)!=33:
        raise ValueError("E1_SOURCE_MARKET_COUNT_NOT_33")
    return records


def archive_path(symbol:str)->Path:
    prefix=(f"qore-native-E1-seven-{symbol}-frozen-witness.zip"
            if symbol in ("EURUSD","GBPUSD","USDJPY","XAGUSD","SP500")
            else f"qore-E1-{symbol}.zip")
    return ROOT/prefix


def source_record(symbol:str,expected_zip_sha:str)->tuple[dict,str]:
    file=archive_path(symbol)
    if sha(file.read_bytes())!=expected_zip_sha:
        raise ValueError("E1_ORIGINAL_SIGNED_ZIP_SHA_MISMATCH_"+symbol)
    with zipfile.ZipFile(file) as z:
        name=f"qore-native-e1-seven-{symbol}.json"
        if set(z.namelist())!={name,name+".sha256","exact-code-head-sha.txt"}:
            raise ValueError("E1_ORIGINAL_ZIP_FILE_SET_MISMATCH")
        if z.read("exact-code-head-sha.txt").decode().strip()!=E1_SHA:
            raise ValueError("E1_ORIGINAL_HEAD_SHA_MISMATCH")
        data=z.read(name)
        internal=sha(data)
        if z.read(name+".sha256").decode().strip()!=internal+"  "+name:
            raise ValueError("E1_ORIGINAL_INNER_JSON_SHA_MISMATCH")
        doc=json.loads(data)
    if (doc.get("identity")!="QORE_NATIVE_33X7_E1_FROZEN_GROSS_ONLY_V1"
        or doc.get("status")!="E1_SEVEN_METHOD_GROSS_ONLY_PREVIOUSLY_EXPOSED_PERIODS"
        or doc.get("original_symbol")!=symbol
        or doc.get("source33_sha")!=G0_SHA
        or doc.get("frozen_prereg_commit")!=REG_SHA
        or doc.get("future_ohlc_not_read") is not True
        or doc.get("net_certified") is not False
        or doc.get("traders_certified")!=0
        or doc.get("production_untouched") is not True
        or doc.get("source_audit",{}).get("original_raw_11_year_sha_checked") is not True):
        raise ValueError("E1_ORIGINAL_PREREG_OR_NO_NET_STATE_DRIFT")
    return doc,internal


def main()->None:
    OUT.mkdir(parents=True,exist_ok=True)
    register=load_register()
    totals=Counter()
    by_method=Counter()
    by_year=Counter()
    by_period=Counter()
    by_family=Counter()
    by_symbol_year=Counter()
    summary_symbols=[]
    custody={}
    clockfile=OUT/"original_E1_event_clocks_only.jsonl.gz"
    shardfile=OUT/"deduplicated_original_E1_native_quote_request_shards.csv"
    shardcols=("canonical_symbol","g0_provenance","provider_identity_status",
               "source_window_start_utc","source_window_end_exclusive_utc",
               "source_duration_minutes","historical_broker_homologated","NET_authorized")
    with gzip.open(clockfile,"wt",encoding="utf-8",compresslevel=6) as ledger, shardfile.open("w",newline="",encoding="utf-8") as shard_io:
        writer=csv.DictWriter(shard_io,fieldnames=shardcols)
        writer.writeheader()
        for symbol,(artifact,zip_sha) in sorted(register.items()):
            doc,inner_sha=source_record(symbol,zip_sha)
            blocks=doc.get("seven_methods")
            if not isinstance(blocks,list) or len(blocks)!=7 or {b.get("method_id") for b in blocks}!=set(METHODS):
                raise ValueError("E1_ORIGINAL_SEVEN_METHOD_ROSTER_DRIFT")
            family=("index" if symbol in INDICES else "metal" if symbol in METALS else "forex")
            cohort=("ORIGINAL12_G0_CONTRACT_UNHOMOLOGATED" if symbol in ORIGINAL12
                    else "NEW21_ICMARKETS_G0_CONTRACT_NOT_G1_PROVEN")
            provenance=("USTEC_ALIAS_UNHOMOLOGATED" if symbol=="NAS100" else
                "US500_ALIAS_CONTRACT_UNHOMOLOGATED" if symbol=="SP500" else
                "UNHOMOLOGATED_TO_G0_ORIGINAL" if symbol in ORIGINAL12 else
                "CURRENT_PROVIDER_G1_CONTRACT_NOT_ATTESTED")
            intervals=[]
            number=0
            for block in blocks:
                method=block["method_id"]
                if (block.get("cell_id")!=f"{method}__{symbol}"
                    or block.get("net_economics_authorized") is not False
                    or block.get("news_asof_filtered") is not False
                    or block.get("bidask_measured") is not False):
                    raise ValueError("E1_METHOD_NO_NET_OR_CAUSAL_CONTRACT_FAILED")
                seen=set()
                for row in block.get("paired_events",[]):
                    daystr=row.get("utc_date")
                    if not isinstance(daystr,str) or daystr in seen:
                        raise ValueError("E1_DUPLICATE_RESEARCH_METHOD_DATE")
                    seen.add(daystr)
                    day=date.fromisoformat(daystr)
                    iso=day.isocalendar()
                    if (row.get("iso_week")!=f"{iso.year}-W{iso.week:02d}"
                        or row.get("method_id")!=method
                        or row.get("broker_executable_fill") is not False
                        or row.get("macro_news_asof_filtered") is not False
                        or row.get("strategy_signal") not in (-1,1)
                        or row.get("baseline_signal") not in (-1,1)):
                        raise ValueError("E1_RESEARCH_EVENT_CAUSAL_METADATA_INVALID")
                    start=datetime.fromisoformat(row["reference_entry_utc"])
                    if start.tzinfo is None:
                        raise ValueError("E1_NAIVE_EVENT_TIMESTAMP")
                    start=start.astimezone(UTC)
                    target=start+timedelta(minutes=METHODS[method])
                    if (not LOWER<=start<EMBARGO or target>EMBARGO
                        or start.date()!=day
                        or start!=expected_clock(symbol,method,day)):
                        raise ValueError("E1_FROZEN_ORIGINAL_RESEARCH_CLOCK_OR_EMBARGO_DRIFT")
                    event_id=sha(f"{E1_SHA}|{method}|{symbol}|{start.isoformat()}".encode())
                    ledger.write(json.dumps({
                        "opportunity_sha256":event_id,"method_id":method,"symbol":symbol,
                        "entry_research_utc":start.isoformat(),
                        "theoretical_M5_target_close_utc":target.isoformat(),
                        "duration_minutes":METHODS[method],"broker_provenance":cohort,
                        "news_asof_filtered":False,"real_broker_fill":False,
                        "outcome_exported":False},sort_keys=True)+"\n")
                    totals["event_rows"]+=1
                    number+=1
                    by_method[method]+=1
                    by_year[start.year]+=1
                    by_family[family]+=1
                    by_period["DEV" if start<datetime(2022,9,17,tzinfo=UTC) else "DIAG"]+=1
                    for at in (start,target):
                        sec=int(at.timestamp())
                        intervals.append((sec-300,sec+300))
                        totals["raw_windows"]+=1
            shards=group_windows(intervals)
            if len(intervals)!=number*2 or any(not 0<b-a<=1800 for a,b in shards):
                raise ValueError("E1_SHARD_SOURCE_UNION_UNBOUNDED")
            totals["shards"]+=len(shards)
            totals["source_seconds"]+=sum(b-a for a,b in shards)
            for a,b in shards:
                utc=datetime.fromtimestamp(a,tz=UTC)
                by_symbol_year[(symbol,utc.year)]+=1
                writer.writerow({
                    "canonical_symbol":symbol,"g0_provenance":cohort,
                    "provider_identity_status":provenance,
                    "source_window_start_utc":utc.isoformat(),
                    "source_window_end_exclusive_utc":datetime.fromtimestamp(b,tz=UTC).isoformat(),
                    "source_duration_minutes":round((b-a)/60,3),
                    "historical_broker_homologated":False,"NET_authorized":False,
                })
            custody[symbol]={
                "github_source_artifact_id":artifact,
                "github_zip_sha256_verified":zip_sha,
                "internal_json_sha256_verified":inner_sha,
            }
            summary_symbols.append({
                "canonical_symbol":symbol,"source_E1_artifact_id":artifact,
                "zip_sha256":zip_sha,"internal_signed_json_sha256":inner_sha,
                "g0_source_cohort":cohort,"method_opportunities":number,
                "raw_entry_target_clock_windows":len(intervals),
                "deduplicated_bounded_source_shards":len(shards),
                "minimum_BIDASK_history_requests":len(shards)*2,
                "min_valid_quote_age_ms":5000,
                "verified_against_signed_E1":True,
                "g0_g1_contract_homologated":False,
                "net_authorized":False,
            })
            print(f"E1_SOURCE_SHA_PASS {symbol} {number} {len(shards)}",flush=True)
    if len(summary_symbols)!=33 or totals["event_rows"]!=373611:
        raise ValueError("E1_ALL33_EVENT_COUNT_MISMATCH")
    by_symbol_fields=list(summary_symbols[0])
    with (OUT/"source_coverage_budget_by_symbol.csv").open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=by_symbol_fields);w.writeheader();w.writerows(summary_symbols)
    with (OUT/"shards_by_symbol_year.csv").open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=("symbol","utc_year","max_30m_source_shards","minimum_BIDASK_requests"))
        w.writeheader()
        for (sym,year),n in sorted(by_symbol_year.items()):
            w.writerow({"symbol":sym,"utc_year":year,
                        "max_30m_source_shards":n,"minimum_BIDASK_requests":n*2})
    out={
        "identity":"QORE_NATIVE_G1_E1_ALL33_SIGNED_CLOCKS_AND_HISTORICAL_SOURCE_SHARD_BUDGET_V1",
        "status":"ORIGINAL_SIGNED_33X7_E1_ALL_EVENT_CLOCKS_SHA_VERIFIED_SOURCE_BUDGET_NOT_NET",
        "original_E1_GitHub_Actions_run":38257207836,
        "original_E1_source_code_SHA":E1_SHA,"original_E1_prereg_SHA":REG_SHA,
        "original_G0_SHA":G0_SHA,
        "universe_markets_signed_source_verified":33,"frozen_method_count":7,
        "all_original_research_E1_event_count":totals["event_rows"],
        "original_E1_events_by_method":dict(sorted(by_method.items())),
        "original_E1_events_by_year":dict(sorted(by_year.items())),
        "original_E1_events_by_source_period":dict(sorted(by_period.items())),
        "original_E1_events_by_class":dict(sorted(by_family.items())),
        "source_clock_windows_before_dedup":totals["raw_windows"],
        "deduplicated_native_quote_history_shards_max_30min":totals["shards"],
        "minimum_original_BIDASK_side_history_requests":2*totals["shards"],
        "hours_of_sampled_source_quote_time_nonoverlapping":round(totals["source_seconds"]/3600,4),
        "reduced_requests_vs_naive_event_entry_exit":round(1-totals["shards"]/totals["raw_windows"],6),
        "frozen_native_source_warmup_before_each_clock_seconds":300,
        "frozen_native_source_tail_after_each_clock_seconds":300,
        "actual_BIDASK_requested_in_this_audit":False,
        "source_not_yet_available_across_required_intervals":True,
        "source_G0_vs_G1_broker_contract_homologated":False,
        "raw_tick_storage_license_and_private_vault_confirmed":False,
        "historical_quote_origin_and_fills_at_original_E1_exit_verified":False,
        "selection_after_previous_E1_gross_exposure_nonvirgin":True,
        "original_E1_signs_gross_returns_PnL_not_exported":True,
        "post_2024_09_17_price_embargo_respected":True,
        "original_E1_231_Holm_FDR_E3_positive_replicated_edges":0,
        "net_authorized":False,"certified_traders":0,
        "never_touch":["VPS","MT5","LIVE","CIBO","Shared","QDLE"],
        "per_market":summary_symbols,
    }
    (OUT/"summary.json").write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    (OUT/"signed_E1_33_GitHub_artifact_custody.json").write_text(
        json.dumps(custody,indent=2,sort_keys=True)+"\n")
    print(json.dumps({
        "markets":33,"methods":7,"events":totals["event_rows"],
        "bounded_shards":totals["shards"],"side_requests_minimum":2*totals["shards"],
        "NET":False,"certified":0,
    },sort_keys=True))


if __name__=="__main__":
    main()
