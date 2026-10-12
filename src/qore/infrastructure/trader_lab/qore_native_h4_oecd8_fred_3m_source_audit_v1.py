"""H4 rate-source audit: exact OECD/FRED monthly 3M interbank series, 8 currencies.

SOURCE DISCOVERY ONLY. No NAV, Sharpe, economic backtest, or synthetic
forward prices. FRED/OECD monthly observations as downloaded in 2026 are
NOT proof of publication vintage known in 2016-2024. Downloader stores
raw bytes ONLY in temporary CI memory, emits aggregate coverage and SHA
metadata; no quote values or PnL are put in public GitHub artifacts.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import re
import time
from datetime import date
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

SERIES = {
    "AUD":"IR3TIB01AUM156N",
    "CAD":"IR3TIB01CAM156N",
    "CHF":"IR3TIB01CHM156N",
    "EUR":"IR3TIB01EZM156N",
    "GBP":"IR3TIB01GBM156N",
    "JPY":"IR3TIB01JPM156N",
    "NZD":"IR3TIB01NZM156N",
    "USD":"IR3TIB01USM156N",
}
START = date(2016, 1, 1)
END = date(2024, 8, 1)  # embargo from 2024-09-17 remains closed.
MONTH_COUNT = (END.year-START.year)*12 + END.month-START.month + 1
BASE = "https://fred.stlouisfed.org/graph/fredgraph.csv"
CITED_PROVENANCE = "OECD Main Economic Indicators, via FRED, percent p.a., monthly 3M or 90D interbank rate"
IDENTITY = "QORE_NATIVE_H4_EIGHT_CURRENCY_OECD_3M_SOURCE_COVERAGE_AUDIT_V1"


def validate_source_roster() -> None:
    if (len(SERIES)!=8 or len(set(SERIES.values()))!=8
        or sorted(SERIES)!=[
            "AUD","CAD","CHF","EUR","GBP","JPY","NZD","USD"
        ] or MONTH_COUNT != 104):
        raise ValueError("H4_OECD_EIGHT_RATE_SERIES_ROSTER_DRIFT")


def source_url(series: str) -> str:
    if series not in SERIES.values():
        raise ValueError("H4_OECD_UNAPPROVED_FRED_SERIES")
    return BASE+"?"+urlencode({
        "id":series, "cosd":START.isoformat(), "coed":END.isoformat()
    })


def parse_fred_csv(raw: bytes, currency:str) -> dict:
    validate_source_roster()
    if currency not in SERIES:
        raise ValueError("H4_OECD_UNKNOWN_CURRENCY")
    if len(raw)>2_000_000 or not raw:
        raise ValueError("H4_OECD_EMPTY_OR_OVERSIZED_CSV")
    try: doc=raw.decode("utf-8-sig")
    except UnicodeDecodeError as e:
        raise ValueError("H4_OECD_NON_UTF8_SOURCE") from e
    records=list(csv.reader(io.StringIO(doc)))
    if not records or records[0] not in (
        ["DATE",SERIES[currency]],
        ["observation_date",SERIES[currency]],
    ):
        raise ValueError("H4_OECD_NOT_EXPECTED_CSV_SERIES_OR_HTML_RESPONSE")
    by_date={}
    out_of_window=0
    count_missing=0
    prev=None
    for rec in records[1:]:
        if len(rec)!=2:
            raise ValueError("H4_OECD_NON_TWO_COLUMN_OBSERVATION")
        stamp,value=rec
        try: d=date.fromisoformat(stamp)
        except ValueError as e:
            raise ValueError("H4_OECD_MALFORMED_DATE") from e
        if d.day!=1 or (prev is not None and d<=prev):
            raise ValueError("H4_OECD_NOT_SORTED_MONTH_STARTS_OR_DUPLICATE")
        prev=d
        if not START<=d<=END:
            out_of_window+=1
            continue
        if value.strip() in (".",""):
            count_missing+=1
            continue
        try: rate=float(value)
        except ValueError as e:
            raise ValueError("H4_OECD_RATE_NONNUMERIC") from e
        if not math.isfinite(rate) or not -15 <= rate <= 100:
            raise ValueError("H4_OECD_IMPLAUSIBLE_RATE")
        by_date[d]=rate
    expected=set()
    d=START
    while d<=END:
        expected.add(d)
        d=date(d.year+1,1,1) if d.month==12 else date(d.year,d.month+1,1)
    seen=set(by_date)
    absent=expected-seen
    # Never serialize actual numeric rates: OECD/FRED may require
    # downstream permission for data reuse and vintage audits.
    return {
        "currency":currency,
        "series_id":SERIES[currency],
        "url":source_url(SERIES[currency]),
        "source_bytes_sha256":hashlib.sha256(raw).hexdigest(),
        "expected_months_2016_01_through_2024_08":MONTH_COUNT,
        "present_valid_months":len(seen),
        "missing_months_including_na":len(absent),
        "missing_first_5_month_stamps":[x.isoformat() for x in sorted(absent)[:5]],
        "first_present_month":min(seen).isoformat() if seen else None,
        "last_present_month":max(seen).isoformat() if seen else None,
        "out_of_requested_period_month_records":out_of_window,
        "explicit_no_numeric_rates_published":True,
        "monthly_values_may_have_been_revised_after_asof":True,
        "proves_1_month_forward_quotes":False,
        "proves_real_time_2016_2024_vintage":False,
    }


def fetch(series:str) -> bytes:
    url=source_url(series)
    request=Request(url, headers={
        "User-Agent":"QORE-Native-Research-RateCoverageAudit/1.0 (+source-only)",
        "Accept":"text/csv,text/plain,*/*",
    })
    last=None
    for retry in range(3):
        try:
            with urlopen(request,timeout=35) as resp:
                if resp.status!=200:
                    raise ValueError("H4_OECD_NON_200_RESPONSE")
                if not resp.geturl().startswith("https://fred.stlouisfed.org/"):
                    raise ValueError("H4_OECD_UNTRUSTED_REDIRECT")
                return resp.read(2_000_001)
        except (HTTPError,URLError,TimeoutError) as e:
            last=e
            if retry<2:time.sleep(2*(retry+1))
    raise RuntimeError(f"H4_OECD_SOURCE_NETWORK_ERROR_{series}: {type(last).__name__}") from last


def source_audit(downloader=fetch) -> dict:
    validate_source_roster()
    reports={}
    for currency,series in SERIES.items():
        raw=downloader(series)
        report=parse_fred_csv(raw,currency)
        reports[currency]=report
        print("H4_OECD_3M_8RATE_SOURCE_PASS",
              currency,report["present_valid_months"],
              report["missing_months_including_na"],
              "missing_months=", ",".join(report["missing_first_5_month_stamps"]),flush=True)
    if len(reports)!=8:raise ValueError("H4_OECD_NOT_ALL_8")
    full=all(x["missing_months_including_na"]==0 for x in reports.values())
    return {
        "identity":IDENTITY,
        "status":("8_OF_8_HISTORICAL_MONTHLY_3M_REVISED_SERIES_COVERED_PIT_UNPROVEN"
                  if full else "PARTIAL_MONTHLY_3M_COVERAGE_PIT_UNPROVEN"),
        "oecd_fred_provenance":CITED_PROVENANCE,
        "currency_count":8,
        "monthly_spot_periods_in_audit":MONTH_COUNT,
        "historical_complete_currency_count":sum(
            x["missing_months_including_na"]==0 for x in reports.values()),
        "series":reports,
        "not_one_month_tenor":True,
        "not_forward_quotes":True,
        "not_verified_2016_2024_asof_vintages":True,
        "not_broker_swaps_or_costs":True,
        "no_historical_rates_republished":True,
        "no_historical_prices_or_returns_evaluated":True,
        "monthly_carry_backtest_executed":False,
        "historical_holdout_2024_09_17_onward_economics_read":False,
        "sharpe_or_CAGR":None,
        "FX_carry_edge_certified":False,
        "certified_traders":0,
        "production_untouched":True,
    }


def main() -> None:
    p=argparse.ArgumentParser()
    p.add_argument("output",type=Path)
    a=p.parse_args()
    audit=source_audit()
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(audit,indent=2,sort_keys=True,allow_nan=False)+"\n")
    print("H4_OECD_RATE_SERIES_AUDIT_COMPLETE",
          json.dumps({
              "status":audit["status"],
              "currency_count":audit["currency_count"],
              "complete":audit["historical_complete_currency_count"],
              "PIT":False,"forward":False,"broker_net":False,
              "Sharpe":None,"certified":0
          },sort_keys=True),flush=True)


if __name__=="__main__":
    main()
