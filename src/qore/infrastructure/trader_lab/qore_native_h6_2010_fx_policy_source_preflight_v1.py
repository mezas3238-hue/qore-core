"""Single source-only GO/NO-GO preflight for new H6 2010-2015 independent backcast.

Never looks up H5 economic outcomes or 2024-09-17+ original M5.
BIS 8 policy month-end (2010-May..2015-Dec) and Dukascopy 28 FX 2 hours
ONLY (2010-06-15 and 2015-06-16). No raw quotes/ticks/rates exported.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import lzma
import math
import struct
import time
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path
from urllib.error import HTTPError,URLError
from urllib.request import Request,urlopen
from urllib.parse import urlencode

from qore.infrastructure.trader_lab.qore_native_h5_bis_policy_fx28_one_test_v1 import (
    CURRENCY_BIS, FX28, xml_local
)

IDENTITY="QORE_NATIVE_H6_EXTENDED_SOURCE_BIS8_DUKA28_SINGLE_GO_NOGO_NO_OUTCOMES"
BIS_START=date(2010,5,1)  # July decisions with rate month -2.
BIS_END=date(2015,12,1)
DUKA_DATES=(date(2010,6,15),date(2015,6,16))
DUKA_UTC_HOUR=12
MAX_BIS_RESPONSE=5_000_000
MAX_TICK_HOUR=4_000_000


def months(begin:date,end:date):
    a=[]
    t=begin
    while t<=end:
        a.append(t)
        t=date(t.year+1,1,1) if t.month==12 else date(t.year,t.month+1,1)
    return a


def validate_contract()->None:
    assert len(FX28)==28 and len(CURRENCY_BIS)==8
    assert BIS_START==date(2010,5,1) and BIS_END==date(2015,12,1)
    assert all(x<date(2016,1,1) for x in DUKA_DATES)


def bis_url(ccy:str):
    if ccy not in CURRENCY_BIS:
        raise ValueError("H6_INVALID_POLICY_CURRENCY")
    return "https://stats.bis.org/api/v1/data/WS_CBPOL/M."+CURRENCY_BIS[ccy]+"?"+urlencode({
        "startPeriod":"2010-05","endPeriod":"2015-12"})


def parse_bis_source(raw:bytes,ccy:str):
    if not raw or len(raw)>MAX_BIS_RESPONSE:
        raise ValueError("H6_BIS_OVERSIZE_OR_EMPTY")
    try:root=ET.fromstring(raw)
    except ET.ParseError as e:
        raise ValueError("H6_BIS_NOT_XML") from e
    if xml_local(root.tag) not in ("StructureSpecificData","GenericData","CompactData"):
        raise ValueError("H6_BIS_BAD_XML_ROOT")
    observed={}
    series_count=0
    expected_country=CURRENCY_BIS[ccy]
    for item in root.iter():
        if xml_local(item.tag)!="Series":continue
        attrs={xml_local(k):v for k,v in item.attrib.items()}
        for child in item:
            if xml_local(child.tag)=="SeriesKey":
                for v in child:
                    if xml_local(v.tag)=="Value":
                        attrs[v.attrib.get("id","")]=v.attrib.get("value")
        if attrs.get("REF_AREA") not in (None,expected_country) or attrs.get("FREQ") not in (None,"M"):
            raise ValueError("H6_BIS_MISMATCH_ID_COUNTRY_FREQ")
        series_count+=1
        for row in item:
            if xml_local(row.tag)!="Obs":continue
            props={xml_local(k):v for k,v in row.attrib.items()}
            for ch in row:
                if xml_local(ch.tag) in ("ObsValue","ObsDimension"):
                    key="OBS_VALUE" if xml_local(ch.tag)=="ObsValue" else "TIME_PERIOD"
                    props[key]=ch.attrib.get("value")
            stamp=props.get("TIME_PERIOD")
            if not stamp or len(stamp)!=7:
                raise ValueError("H6_BIS_BAD_MONTH")
            d=date.fromisoformat(stamp+"-01")
            if not BIS_START<=d<=BIS_END:
                raise ValueError("H6_BIS_OUT_OF_PRE_2016_SCOPE")
            if d in observed:
                raise ValueError("H6_BIS_DUPLICATE_MONTH")
            val=props.get("OBS_VALUE")
            if val in (None,"","."):
                continue
            number=float(val)
            if not math.isfinite(number) or number<=-20 or number>=100:
                raise ValueError("H6_BIS_INVALID_POLICY_VALUE")
            observed[d]=number
    if series_count>1:
        raise ValueError("H6_BIS_MORE_THAN_ONE_SERIES")
    expected=months(BIS_START,BIS_END)
    missing=[x for x in expected if x not in observed]
    return {
        "country":ccy,
        "series_id":"WS_CBPOL/M."+expected_country,
        "source_byte_hash_sha256":hashlib.sha256(raw).hexdigest(),
        "observed_months":len(observed),
        "expected_months":len(expected),
        "missing_months":len(missing),
        "missing_first_5_month_stamps":[d.isoformat() for d in missing[:5]],
        "first_month":min(observed).isoformat() if observed else None,
        "last_month":max(observed).isoformat() if observed else None,
        "series_count":series_count,
        "PIT_2010_2015_unrevised_evidence":False,
        "rates_exported":False,
    }


def request_bytes(url:str,expected_prefix:str,max_size:int):
    last=None
    for attempt in range(2):
        try:
            req=Request(url,headers={
                "User-Agent":"QORE-Native-H6-Source-Preflight/1.0",
                "Accept":"application/vnd.sdmx.structurespecificdata+xml;version=2.1,application/xml;q=0.8,*/*;q=0.2",
            })
            with urlopen(req,timeout=25) as res:
                if res.status!=200 or not res.geturl().startswith(expected_prefix):
                    raise ValueError("H6_WRONG_RESPONSE_OR_URL")
                return res.read(max_size+1)
        except (HTTPError,URLError,TimeoutError) as e:
            last=e
            if attempt==0:time.sleep(.3)
    raise ValueError("H6_REMOTE_SOURCE_NOT_AVAILABLE_"+type(last).__name__)


def duka_url(pair:str,day:date):
    if pair not in FX28 or day not in DUKA_DATES:
        raise ValueError("H6_DUKA_NOT_PREREG_SOURCE")
    return (f"https://datafeed.dukascopy.com/datafeed/{pair}/"
            f"{day.year}/{day.month-1:02d}/{day.day:02d}/"
            f"{DUKA_UTC_HOUR:02d}h_ticks.bi5")


def inspect_duka(raw:bytes,pair:str,day:date):
    if not raw or len(raw)>MAX_TICK_HOUR:
        raise ValueError("H6_DUKA_EMPTY_OVERSIZE")
    try:
        values=lzma.decompress(raw,format=lzma.FORMAT_AUTO)
    except lzma.LZMAError as e:
        raise ValueError("H6_DUKA_NOT_A_BI5_LZMA_ARCHIVE") from e
    if not values or len(values)%20 or len(values)>25_000_000:
        raise ValueError("H6_DUKA_TICKS_NOT_20_BYTES_EACH")
    if len(values)<20:
        raise ValueError("H6_DUKA_EMPTY_TICK_HOUR")
    # Tick binary checked for shape only, not exporting any price or tick.
    ts,bid,ask,bv,av=struct.unpack_from(">3I2f",values,0)
    if ts>=3600000 or not math.isfinite(bv+av):
        raise ValueError("H6_DUKA_MALFORMED_TICK_FORMAT")
    return {
        "symbol":pair,"sample_utc":f"{day}T{DUKA_UTC_HOUR:02d}:00:00Z",
        "status":"SAMPLE_BI5_20B_RECORD_VALID",
        "bytes":len(raw),
        "ticks_count":len(values)//20,
        "sha256_original":hashlib.sha256(raw).hexdigest(),
        "source_url":duka_url(pair,day),
        "not_a_2010_2015_full_coverage_witness":True,
        "underlying_tick_prices_exported":False,
    }


def source_audit(bis_downloader=None,duka_downloader=None):
    validate_contract()
    if bis_downloader is None:
        bis_downloader=lambda ccy:request_bytes(
            bis_url(ccy),"https://stats.bis.org/",MAX_BIS_RESPONSE)
    if duka_downloader is None:
        duka_downloader=lambda s,d:request_bytes(
            duka_url(s,d),"https://datafeed.dukascopy.com/",MAX_TICK_HOUR)
    policies={}
    for ccy in sorted(CURRENCY_BIS):
        try:
            policies[ccy]=parse_bis_source(bis_downloader(ccy),ccy)
            print("H6_BIS_2010_2015_SOURCE_PROBE",ccy,
                  policies[ccy]["observed_months"],
                  "missing",policies[ccy]["missing_months"],flush=True)
        except Exception as e:
            if isinstance(e,(KeyboardInterrupt,SystemExit)):raise
            policies[ccy]={
                "country":ccy,"status":"SOURCE_UNAVAILABLE",
                "cause":type(e).__name__,
                "observed_months":0,"expected_months":len(months(BIS_START,BIS_END)),
                "missing_months":len(months(BIS_START,BIS_END)),
            }
            print("H6_BIS_2010_2015_SOURCE_UNAVAILABLE",ccy,type(e).__name__,flush=True)
    ticks=[]
    tasks=[(s,d) for s in FX28 for d in DUKA_DATES]
    def one(task):
        s,d=task
        try:
            r=inspect_duka(duka_downloader(s,d),s,d)
            return r
        except Exception as e:
            if isinstance(e,(KeyboardInterrupt,SystemExit)):raise
            return {"symbol":s,"sample_utc":f"{d}T{DUKA_UTC_HOUR:02d}:00:00Z",
                    "status":"SAMPLE_UNAVAILABLE","cause":type(e).__name__,
                    "underlying_tick_prices_exported":False}
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        for r in pool.map(one,tasks):
            ticks.append(r)
    for d in DUKA_DATES:
        ok=sum(t["status"]=="SAMPLE_BI5_20B_RECORD_VALID" and t["sample_utc"].startswith(d.isoformat()) for t in ticks)
        print("H6_DUKA_28_ONE_HOUR_PROBE",d.isoformat(),ok,"of28",flush=True)
    complete_policy=all(p.get("missing_months") == 0 for p in policies.values())
    duka_ok=all(t["status"]=="SAMPLE_BI5_20B_RECORD_VALID" for t in ticks)
    status=("TWO_HOUR_SAMPLES_GO_FOR_EXPANDED_DATA_ACQUISITION_ONLY" if complete_policy and duka_ok
            else "H6_DATA_CONDITION_NOT_MET")
    return {
        "identity":IDENTITY,"status":status,
        "sample_only":True,
        "BIS_months_required_per_currency":len(months(BIS_START,BIS_END)),
        "BIS_full_8_policy_2010_2015":complete_policy,
        "Dukascopy_all_56_one_hour_samples_valid":duka_ok,
        "Dukascopy_valid_samples":sum(t["status"]=="SAMPLE_BI5_20B_RECORD_VALID" for t in ticks),
        "Dukascopy_sample_count":len(ticks),
        "BIS_source_reports":policies,
        "Dukascopy_sample_reports":ticks,
        "G0_2010_2015_original_28_FX_source_available":False,
        "full_history_2010_2015_28_FX_data_retrieved":False,
        "source_homologation_to_IC_Markets_certified":False,
        "FX_H6_vol20_Sortino_economic_returns_calculated":False,
        "no_bidask_or_rate_values_exported":True,
        "holdout_from_2024_09_17_read":False,
        "broker_NET_certified":False,
        "certified_traders":0,
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("output",type=Path)
    x=p.parse_args()
    r=source_audit()
    x.output.parent.mkdir(parents=True,exist_ok=True)
    x.output.write_text(json.dumps(r,sort_keys=True,indent=2,allow_nan=False)+"\n")
    print("H6_EXTENDED_CARRY_PRETEST_28FX_8POLICY_GO_NOGO",
          json.dumps({
            "status":r["status"],
            "BIS8":r["BIS_full_8_policy_2010_2015"],
            "Dukascopy_valid_samples":r["Dukascopy_valid_samples"],
            "Sharpe_Sortino_PnL":None,
            "broker_NET":False,"certified":0,
        },sort_keys=True),flush=True)


if __name__=="__main__":
    main()
