"""Two pre-exposed dates: E1 source-only 33 market clocks and read-only budget.

No market price requests, no outcomes, no new OOS test.
"""
from __future__ import annotations

import csv
import gzip
import json
import os
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path

ROOT=Path(os.environ.get("QORE_E1_REPORT_DIR", "/mnt/data/qore_native_g1_all33_clock_audit"))
DATES=frozenset(("2021-03-16","2023-03-21"))


def union(windows: list[tuple[int,int]]) -> list[tuple[int,int]]:
    if not windows:
        return []
    ranges=[]
    for a,b in sorted(windows):
        if ranges and a <= ranges[-1][1]:
            ranges[-1]=(ranges[-1][0],max(b,ranges[-1][1]))
        else:
            ranges.append((a,b))
    return ranges


def main()->None:
    windows=defaultdict(list)
    events=Counter()
    methods=Counter()
    with gzip.open(ROOT/"original_E1_event_clocks_only.jsonl.gz","rt",encoding="utf-8") as data:
        for line in data:
            row=json.loads(line)
            date=row["entry_research_utc"][:10]
            if date not in DATES:
                continue
            sym=row["symbol"]
            events[(sym,date)]+=1
            methods[row["method_id"]]+=1
            for name in ("entry_research_utc","theoretical_M5_target_close_utc"):
                seconds=int(datetime.fromisoformat(row[name]).timestamp())
                windows[(sym,date)].append((seconds-300,seconds+300))
    totals=Counter()
    rows=[]
    path=ROOT/"calendar_two_dates_source_only_pilot_windows.csv"
    with path.open("w",newline="",encoding="utf-8") as f:
        writer=csv.DictWriter(f,fieldnames=(
            "market","date","source_start_utc","source_end_exclusive_utc",
            "side_requests_at_least","source_only_no_pnl",
        ))
        writer.writeheader()
        for sym,date in sorted(windows):
            coverage=union(windows[(sym,date)])
            for first,last in coverage:
                if not 0<last-first<=1800:
                    raise ValueError("G1_TWO_DATE_SOURCE_MAX_30MIN_EXCEEDED")
                writer.writerow({
                    "market":sym,"date":date,
                    "source_start_utc":datetime.fromtimestamp(first,tz=UTC).isoformat(),
                    "source_end_exclusive_utc":datetime.fromtimestamp(last,tz=UTC).isoformat(),
                    "side_requests_at_least":2,"source_only_no_pnl":True,
                })
            rows.append({
                "canonical_symbol":sym,"UTC_date":date,
                "original_E1_method_events":events[(sym,date)],
                "raw_BIDASK_clock_windows":2*events[(sym,date)],
                "deduplicated_quote_shards":len(coverage),
                "minimum_read_only_side_requests":2*len(coverage),
                "HISTORICAL_NET_BLOCKED":True,
            })
            totals["events"]+=events[(sym,date)]
            totals["shards"]+=len(coverage)
            totals["market_days"]+=1
    report={
        "dates_UTC":sorted(DATES),
        "original_source_event_count":totals["events"],
        "market_day_combinations":totals["market_days"],
        "expected":66,
        "dedup_quote_shards":totals["shards"],
        "minimum_read_only_side_requests":2*totals["shards"],
        "source_only_no_broker_calls_executed":True,
        "historical_broker_contracts_homologated":False,
        "long_term_private_archival_license_confirmed":False,
        "net_authorized":False,
        "previously_exposed_data_not_new_holdout":True,
        "per_market_day":rows,"methods":dict(methods),
    }
    (ROOT/"calendar_two_dates_pilot_summary.json").write_text(
        json.dumps(report,indent=2,sort_keys=True)+"\n"
    )
    if (totals["events"],totals["market_days"],totals["shards"])!=(368,66,403):
        raise ValueError("G1_ORIGINAL_EXPOSED_TWO_DATE_SOURCE_COUNT_DRIFT")
    print(json.dumps({
        "frozen_dates":sorted(DATES),"market_days":totals["market_days"],
        "events":totals["events"],"shards":totals["shards"],
        "min_side_requests":totals["shards"]*2,"NET":False,
    },sort_keys=True))


if __name__=="__main__":
    main()
