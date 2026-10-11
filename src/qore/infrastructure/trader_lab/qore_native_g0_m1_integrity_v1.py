"""QORE Native G0: observation-only market data integrity, never economic outcomes.

This deliberately imports only the neutral native M1 reader. Unlike a trading
strategy it does not compute entries, forward returns, labels or P&L.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from collections.abc import Iterable
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from statistics import median
from typing import Any

from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar, iter_cibo_m1,
)

IDENTITY = "QORE_NATIVE_G0_NINE_MARKET_M1_SOURCE_AUDIT_V1"
SOURCE_SHA = "18c338aedd5013ce65a6cb6408ffbc2e904a6217"
SOURCE_RUN = 35548099334
WINDOW_START = datetime(2025, 9, 17, tzinfo=UTC)
WINDOW_END = datetime(2026, 9, 17, tzinfo=UTC)
UNIVERSE = ("EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "AUDJPY",
            "GBPJPY", "XAUUSD", "USDCAD", "NAS100")
PAIRS = (("EURUSD", "GBPUSD"), ("AUDUSD", "GBPUSD"), ("AUDJPY", "GBPJPY"))
BINS = ("2-4m", "5-14m", "15-59m", ">=60m")


def interval_bin(minutes: int) -> str:
    if minutes < 2:
        raise ValueError("only genuine gaps of >=2m qualify")
    if minutes <= 4:
        return BINS[0]
    if minutes <= 14:
        return BINS[1]
    if minutes <= 59:
        return BINS[2]
    return BINS[3]


def sha256_file(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as stream:
        for buf in iter(lambda: stream.read(1024*1024), b""):
            h.update(buf)
    return h.hexdigest()


def source_evidence(root:Path, symbol:str)->dict[str, Any]:
    if symbol not in UNIVERSE:
        raise ValueError("symbol not frozen in G0 preregistration")
    p=root/"m1-clone-manifest.json"
    if not p.is_file():
        raise ValueError("native source manifest missing")
    manifest=json.loads(p.read_text(encoding="utf-8"))
    expected={
        "canonical_symbol":symbol,
        "provider_native_m1":True,
        "synthetic_m1":False,
        "interpolated_m1":False,
        "contradictory_m1":0,
        "read_only":True,
    }
    for k,v in expected.items():
        if type(manifest.get(k)) is not type(v) or manifest.get(k)!=v:
            raise ValueError(f"native manifest not verified {symbol}.{k}: {manifest.get(k)!r}")
    parts=sorted((root/"RAW_M1_LEDGER").glob("*.jsonl"))
    if not parts:
        raise ValueError("source has no native RAW_M1_LEDGER")
    combined=hashlib.sha256()
    raw_size=0
    for f in parts:
        digest=sha256_file(f)
        combined.update(f.relative_to(root).as_posix().encode("utf-8"))
        combined.update(bytes.fromhex(digest))
        raw_size+=f.stat().st_size
    return {
        "source_artifact_run":SOURCE_RUN, "source_artifact_sha":SOURCE_SHA,
        "source_artifact_name":f"qore-capitalizer-cibo-10y-native-m1-{symbol}-{SOURCE_SHA}",
        "manifest_sha256":sha256_file(p),
        "raw_partition_count":len(parts),
        "raw_bytes":raw_size, "partition_ordered_combined_sha256":combined.hexdigest(),
        "manifest":manifest,
        "source_not_new_OOS":True,
    }


def audit_stream(bars:Iterable[CapitalizerM1Bar], symbol:str)->tuple[dict[str,Any],dict[str,Any]]:
    if symbol not in UNIVERSE:
        raise ValueError("symbol out of frozen nine-market scope")
    masks:dict[str,int]=defaultdict(int)
    m15:Counter[datetime]=Counter()
    h1:Counter[datetime]=Counter()
    hour_weekday:Counter[int]=Counter()
    hour_weekend:Counter[int]=Counter()
    missing_bin:Counter[str]=Counter()
    prior:datetime|None=None
    n_full=0
    n_window=0
    first:datetime|None=None
    last:datetime|None=None
    digits:Counter[int]=Counter()
    max_gap=0
    for bar in bars:
        n_full+=1
        if bar.symbol!=symbol:
            raise ValueError("wrong symbol in native M1 source")
        t=bar.opened_at.astimezone(UTC)
        if t != bar.opened_at or bar.closed_at != t+timedelta(minutes=1):
            raise ValueError("native M1 must be exact UTC 1-minute candle")
        if prior is not None and t<=prior:
            raise ValueError("nonmonotone or duplicate M1 in G0")
        prior=t
        if not WINDOW_START<=t<WINDOW_END:
            continue
        n_window+=1
        first=first or t
        last=t
        digits[bar.digits]+=1
        day=t.date().isoformat()
        minute=t.hour*60+t.minute
        key=1<<minute
        if masks[day]&key:
            raise ValueError("duplicate exact UTC minute")
        masks[day]|=key
        m15[t.replace(minute=(t.minute//15)*15,second=0,microsecond=0)]+=1
        h1[t.replace(minute=0,second=0,microsecond=0)]+=1
        if t.weekday()<5:
            hour_weekday[t.hour]+=1
        else:
            hour_weekend[t.hour]+=1
    # Gap count calculated from day mask, explicitly excluding overnight and
    # weekend crossings to avoid labeling normal market closure corruption.
    daily_minutes:dict[str,int]={}
    for day,mask in masks.items():
        daily_minutes[day]=mask.bit_count()
        present=[i for i in range(1440) if (mask>>i)&1]
        if len(present)<=1:
            continue
        for a,b in zip(present,present[1:]):
            diff=b-a
            if diff>1:
                missing_bin[interval_bin(diff)]+=1
                max_gap=max(max_gap,diff-1)
    weekdays={d:c for d,c in daily_minutes.items() if date.fromisoformat(d).weekday()<5}
    weekend={d:c for d,c in daily_minutes.items() if date.fromisoformat(d).weekday()>=5}
    by_m15=Counter(m15.values())
    by_h1=Counter(h1.values())
    if n_window==0 or not first or not last:
        raise ValueError("no actual M1 in G0 historical window")
    if any(c>15 for c in by_m15) or any(c>60 for c in by_h1):
        raise ValueError("bucket M1 count exceeds valid nominal capacity")
    status="SOURCE_INTEGRITY_PASS"
    report={
        "identity":IDENTITY, "symbol":symbol,
        "integrity_gate":status,
        "coverage": "COVERAGE_PARTIAL" if (sum(v for k,v in by_m15.items() if k<15)>0 or missing_bin) else "ACTIVE_BUCKETS_COMPLETE",
        "source_native_m1_full_artifact_rows":n_full,
        "source_native_m1_rows_in_year":n_window,
        "window_start":WINDOW_START.isoformat(),
        "window_end_exclusive":WINDOW_END.isoformat(),
        "first_m1_in_window":first.isoformat(),
        "last_m1_in_window":last.isoformat(),
        "digits_counts":dict(digits),
        "active_UTC_days":len(daily_minutes),
        "weekday_active_days":len(weekdays),
        "weekend_active_days":len(weekend),
        "weekday_minutes_per_active_day_median":median(weekdays.values()) if weekdays else None,
        "weekend_minutes_per_active_day_median":median(weekend.values()) if weekend else None,
        "total_weekday_m1":sum(weekdays.values()),
        "total_weekend_m1":sum(weekend.values()),
        "weekday_hour_UTC_observed":{str(i):hour_weekday[i] for i in range(24)},
        "weekend_hour_UTC_observed":{str(i):hour_weekend[i] for i in range(24)},
        "intra_UTC_day_gap_count_by_duration":{bin:missing_bin[bin] for bin in BINS},
        "maximum_intra_day_missing_minutes":max_gap,
        "active_m15_buckets":sum(by_m15.values()),
        "m15_complete_15of15":by_m15[15],
        "m15_incomplete_1to14":sum(n for c,n in by_m15.items() if c<15),
        "active_h1_buckets":sum(by_h1.values()),
        "h1_complete_60of60":by_h1[60],
        "h1_incomplete_1to59":sum(n for c,n in by_h1.items() if c<60),
        "execution_costs_known":False,
        "physical_trade_replay_authorized":False,
        "trading_strategy_edge_evaluated":False,
        "unseen_holdout":False,
        "schedule_certified":False,
    }
    return report,{
        "identity":IDENTITY, "symbol":symbol,
        "days":{k:format(v,"0360x") for k,v in masks.items()},
        "minutes_by_day":daily_minutes,
    }


def audit_market(native:Path, symbol:str, out:Path)->dict[str,Any]:
    evidence=source_evidence(native,symbol)
    report,clock=audit_stream(iter_cibo_m1(native),symbol)
    report["source_evidence"]=evidence
    out.mkdir(parents=True,exist_ok=True)
    (out/f"qore-native-G0-{symbol}-source-integrity.json").write_text(
        json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    (out/f"qore-native-G0-{symbol}-minute-bitmaps.json").write_text(
        json.dumps(clock,sort_keys=True)+"\n",encoding="utf-8")
    return report


def audit_aggregate(root:Path, out:Path)->dict[str,Any]:
    report_files=sorted(root.rglob("qore-native-G0-*-source-integrity.json"))
    clock_files=sorted(root.rglob("qore-native-G0-*-minute-bitmaps.json"))
    if len(report_files)!=len(UNIVERSE) or len(clock_files)!=len(UNIVERSE):
        raise ValueError(f"missing one or more market source artifacts: {len(report_files)}/{len(clock_files)}")
    reports={x["symbol"]:x for p in report_files for x in [json.loads(p.read_text())]}
    clocks={x["symbol"]:x for p in clock_files for x in [json.loads(p.read_text())]}
    if set(reports)!=set(UNIVERSE) or set(clocks)!=set(UNIVERSE):
        raise ValueError("one symbol missing, duplicate, or unexpected")
    if any(v["integrity_gate"]!="SOURCE_INTEGRITY_PASS" for v in reports.values()):
        raise ValueError("native source failed G0")
    relative={}
    for a,b in PAIRS:
        days=sorted(set(clocks[a]["days"])|set(clocks[b]["days"]))
        together=only_a=only_b=0
        common_dates=0
        for d in days:
            av=int(clocks[a]["days"].get(d,"0"),16)
            bv=int(clocks[b]["days"].get(d,"0"),16)
            overlap=(av&bv).bit_count()
            together+=overlap
            only_a+=(av&~bv).bit_count()
            only_b+=(bv&~av).bit_count()
            if overlap:
                common_dates+=1
        total=together+only_a+only_b
        relative[f"{a}|{b}"]={
            "shared_UTC_days_with_any_common_minute":common_dates,
            "paired_minutes_both_native":together,
            "A_only_minutes":only_a,"B_only_minutes":only_b,
            "minute_jaccard":together/total if total else None,
            "pair_clock_historical_not_OOS":True,
            "cointegration_or_profitability_not_tested":True,
        }
    result={
        "identity":IDENTITY,
        "source_run":SOURCE_RUN,"source_sha":SOURCE_SHA,
        "symbol_count":len(reports),
        "all_source_integrity_pass":True,
        "all_markets":[] if not reports else [
            {k:v for k,v in reports[s].items() if k!="source_evidence"}
            for s in UNIVERSE
        ],
        "pair_minute_alignment":relative,
        "candidate_data_inventory":{
            "DRIVE":["NAS100","XAUUSD","EURUSD","GBPUSD"],
            "RESET":["EURUSD","GBPUSD","USDJPY"],
            "RELATIVE":[list(p) for p in PAIRS],
        },
        "data_provider_native_not_broker_cost_verified":True,
        "development_history_already_seen":True,
        "fresh_unseen_OOS_accredited":False,
        "G1_economics_and_signal_unopened":True,
        "G0_status":"SOURCE_INTEGRITY_PASS_G1_REQUIRES_MARKET_SCHEDULE_AND_PREREG",
        "live_and_production_untouched":True,
    }
    out.mkdir(parents=True,exist_ok=True)
    (out/"qore-native-G0-nine-market-integrity-and-pair-synchrony.json").write_text(
        json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print("QORE_NATIVE_G0_AGGREGATE",json.dumps({
        "identity":IDENTITY,"status":result["G0_status"],
        "markets":[{k:m[k] for k in (
            "symbol","source_native_m1_rows_in_year","weekday_active_days",
            "m15_complete_15of15","m15_incomplete_1to14","active_h1_buckets",
            "h1_complete_60of60","coverage"
        )} for m in result["all_markets"]],
        "synchrony":relative,
        "fresh_unseen_OOS_accredited":False,
        "all_source_integrity_pass":True,
    },sort_keys=True))
    return result


def main()->None:
    p=argparse.ArgumentParser()
    subs=p.add_subparsers(dest="mode",required=True)
    m=subs.add_parser("market")
    m.add_argument("native",type=Path)
    m.add_argument("symbol",choices=UNIVERSE)
    m.add_argument("out",type=Path)
    a=subs.add_parser("aggregate")
    a.add_argument("markets",type=Path)
    a.add_argument("out",type=Path)
    args=p.parse_args()
    if args.mode=="market":
        x=audit_market(args.native,args.symbol,args.out)
        print("QORE_NATIVE_G0_MARKET",json.dumps({
            "symbol":args.symbol,
            "source_rows":x["source_native_m1_rows_in_year"],
            "active_weekdays":x["weekday_active_days"],
            "complete_M15":x["m15_complete_15of15"],
            "incomplete_M15":x["m15_incomplete_1to14"],
            "status":x["integrity_gate"],
        },sort_keys=True))
    else:
        audit_aggregate(args.markets,args.out)


if __name__=="__main__":
    main()
