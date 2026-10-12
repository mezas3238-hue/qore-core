"""ALFRED public graph vintage check — 8 currencies, two frozen historical dates.

PIT VINTAGE DATA DISCOVERY ONLY; produces no returns or raw rate exports.
If the API returns current values masked as historical, reject via header.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import time
from datetime import date
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from qore.infrastructure.trader_lab.qore_native_h4_oecd8_fred_3m_source_audit_v1 import SERIES,validate_source_roster

IDENTITY="QORE_NATIVE_H4_ALFRED_TWO_HISTORIC_VINTAGES_8_CURRENCIES_PREFLIGHT_V1"
VINTAGES=(date(2019,12,31),date(2023,12,29))
BASE="https://alfred.stlouisfed.org/graph/alfredgraph.csv"


def vintage_url(series:str)->str:
    if series not in SERIES.values():
        raise ValueError("H4_ALFRED_UNAPPROVED_SERIES")
    return BASE+"?"+urlencode({
        "id":",".join([series]*len(VINTAGES)),
        "vintage_date":",".join(d.isoformat() for d in VINTAGES),
    })


def validate_vintage_csv(data:bytes,currency:str)->dict:
    validate_source_roster()
    if currency not in SERIES or not data or len(data)>3_000_000:
        raise ValueError("H4_ALFRED_MISSING_OR_OVERSIZED_OR_BAD_CURRENCY")
    try: text=data.decode("utf-8-sig")
    except UnicodeDecodeError as e:raise ValueError("H4_ALFRED_BINARY_RESPONSE") from e
    reader=csv.reader(io.StringIO(text))
    header=next(reader,None)
    series=SERIES[currency]
    expected=("observation_date",*[series+"_"+d.strftime("%Y%m%d") for d in VINTAGES])
    if tuple(header or ())!=expected:
        raise ValueError("H4_ALFRED_VINTAGE_HEADERS_MISMATCH_NO_FALLBACK_TO_CURRENT")
    counts={d.isoformat():0 for d in VINTAGES}
    last_seen={d.isoformat():None for d in VINTAGES}
    prev=None
    for row in reader:
        if len(row)!=len(expected):
            raise ValueError("H4_ALFRED_COLUMN_DRIFT")
        d=date.fromisoformat(row[0])
        if prev is not None and d<=prev:
            raise ValueError("H4_ALFRED_MONTH_DUPLICATE_OR_UNSORTED")
        prev=d
        for i,v in enumerate(VINTAGES,1):
            if row[i] in ("", "."):continue
            if d > v:
                raise ValueError("H4_ALFRED_VALUE_FROM_FUTURE_MONTH_PRESENT_AT_VINTAGE")
            try: value=float(row[i])
            except ValueError as e:
                raise ValueError("H4_ALFRED_NON_NUMERIC_VINTAGE") from e
            if not math.isfinite(value) or not -15<=value<=100:
                raise ValueError("H4_ALFRED_IMPLAUSIBLE_VINTAGE")
            counts[v.isoformat()]+=1
            last_seen[v.isoformat()]=d.isoformat()
    return {
        "series_id":series,
        "currency":currency,
        "official_alfred_source":vintage_url(series),
        "source_bytes_sha256":hashlib.sha256(data).hexdigest(),
        "historical_vintage_expected_headers":list(expected),
        "non_missing_monthly_values_by_vintage":counts,
        "last_observation_available_as_of_vintage":last_seen,
        "ALFRED_vintage_headers_authenticated_not_source_initial_release_certification":True,
        "no_numeric_rates_exported":True,
        "forward_one_month_quotes_found":False,
    }


def fetch(currency:str)->bytes:
    u=vintage_url(SERIES[currency])
    request=Request(u,headers={
        "User-Agent":"QORE-Native-Research-PIT-Prefight/1.0",
        "Accept":"text/csv,text/plain,*/*",
    })
    last=None
    for retry in range(3):
        try:
            with urlopen(request,timeout=40) as response:
                if response.status!=200 or not response.geturl().startswith("https://alfred.stlouisfed.org/"):
                    raise ValueError("H4_ALFRED_WRONG_HTTP_SOURCE")
                return response.read(3_000_001)
        except (HTTPError,URLError,TimeoutError) as e:
            last=e
            if retry<2:time.sleep(2*(retry+1))
    raise RuntimeError("H4_ALFRED_CANNOT_FETCH_VINTAGE_"+currency+"_"+type(last).__name__) from last


def audit(downloader=fetch)->dict:
    validate_source_roster()
    observations={}
    for currency in sorted(SERIES):
        raw=downloader(currency)
        observations[currency]=validate_vintage_csv(raw,currency)
        print("H4_ALFRED_VINTAGE_HEADER_PASS",currency,
              json.dumps(observations[currency]["last_observation_available_as_of_vintage"],
                         sort_keys=True),flush=True)
    return {
        "identity":IDENTITY,
        "status":"HISTORICAL_ALFRED_2_VINTAGES_8_OF_8_SOURCE_OBSERVED_NOT_1M_FORWARD",
        "historical_vintage_asof_dates":[x.isoformat() for x in VINTAGES],
        "currency_count":len(observations),
        "series":observations,
        "not_1month_forward_quotes":True,
        "not_pit_monthly_all_2016_2024_yet":True,
        "no_historical_interest_rate_values_published":True,
        "spot_M5_not_accessed":True,
        "holdout_2024_09_17_onward_not_accessed":True,
        "broker_NET_backtest_performed":False,
        "FX_carry_backtest_performed":False,
        "claimed_Sharpe":None,
        "certified_traders":0,
    }


def main()->None:
    p=argparse.ArgumentParser()
    p.add_argument("output",type=Path)
    a=p.parse_args()
    result=audit()
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+"\n")
    print("H4_ALFRED_8_TWO_VINTAGE_AUDIT",
          json.dumps({"status":result["status"],"currencies":result["currency_count"],
                      "Sharpe":None,"certified_traders":0}),flush=True)


if __name__=="__main__":main()
