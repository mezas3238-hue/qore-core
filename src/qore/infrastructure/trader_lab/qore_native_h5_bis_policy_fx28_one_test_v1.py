"""BIS policy-rate H5 one-shot FX28 monthly differential test, research-only.

H5 prereg: BIS central bank policy monthly, two completed calendar months
release/observation lag, long top six / short bottom six of 28 FX pairs,
1/12 equal abs weights and 2bp/side notional turnover.
Reports separately SPOT_ONLY_ASSUMED_COST and IDEAL_POLICY_ACCRUAL_NOT_BROKER_NET.
No transaction orders, no 2024-09-17+ returns, no production changes.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import statistics
import subprocess
import time
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from qore.infrastructure.trader_lab import qore_native_d1_tsmom20_single_edge_v1 as src
from qore.infrastructure.trader_lab.qore_native_d1_xsrev5_33_h3_one_test_v1 import FAMILIES

IDENTITY="QORE_NATIVE_H5_8_POLICY_RATES_FX28_MONTHLY_2BP_COST_ONE_HYPOTHESIS_V1"
CURRENCY_BIS={"AUD":"AU","CAD":"CA","CHF":"CH","EUR":"XM",
              "GBP":"GB","JPY":"JP","NZD":"NZ","USD":"US"}
FX28=tuple(sorted(FAMILIES["FX_28"]))
SIDE_COST=0.0002
ABS_WEIGHT=1/12
LONGS=SHORTS=6
LAG_MONTHS=2
START_RATE_MONTH=date(2016,1,1)
LAST_RATE_MONTH=date(2024,8,1)
SOURCE_ENDPOINT="https://stats.bis.org/api/v1/data/WS_CBPOL/"
RATE_BASE="/policy_rate_annual_percent"
MAX_PRICE_DAILY_CHANGE=.45


def month_minus(d:date,n:int)->date:
    z=d.year*12+(d.month-1)-n
    return date(z//12,z%12+1,1)


def check_universe():
    if len(FX28)!=28 or len(set(FX28))!=28 or set(FX28)!=FAMILIES["FX_28"]:
        raise ValueError("H5_FX28_UNIVERSE_DRIFT")
    if set(CURRENCY_BIS)!={x for s in FX28 for x in (s[:3],s[3:])}:
        raise ValueError("H5_BIS_EIGHT_POLICY_CURRENCY_DRIFT")
    if src.EMBARGO!=date(2024,9,17) or SIDE_COST!=.0002:
        raise ValueError("H5_EMBARGO_OR_COST_DRIFT")


def bis_url(ccy:str)->str:
    if ccy not in CURRENCY_BIS:
        raise ValueError("H5_BIS_UNRECOGNIZED_CURRENCY")
    return SOURCE_ENDPOINT+"M."+CURRENCY_BIS[ccy]+"?"+urlencode({
        "startPeriod":"2016-01","endPeriod":"2024-08",
    })


def xml_local(tag:str)->str:
    return tag.rsplit("}",1)[-1]


def parse_policy_rates(raw:bytes,ccy:str)->dict[date,float]:
    """Strict SDMX 2.1 XML structure-specific/generic monthly observations.

    Reject provenance mismatches or missing months. No accidental use of
    updated 2026 values as proof of historical vintage is asserted.
    """
    if ccy not in CURRENCY_BIS or len(raw)>5_000_000 or not raw:
        raise ValueError("H5_BIS_UNEXPECTED_SOURCE_OR_OVERSIZED")
    try: root=ET.fromstring(raw)
    except ET.ParseError as e:
        raise ValueError("H5_BIS_NOT_XML_SDMX_SERIES") from e
    if xml_local(root.tag) not in ("StructureSpecificData","GenericData","CompactData"):
        raise ValueError("H5_BIS_WRONG_SDMX_ROOT_"+xml_local(root.tag))
    country=CURRENCY_BIS[ccy]
    found={}
    matching_series=0
    for series in root.iter():
        if xml_local(series.tag)!="Series":
            continue
        attrib={xml_local(k):v for k,v in series.attrib.items()}
        for child in series:
            if xml_local(child.tag)=="SeriesKey":
                for val in child:
                    if xml_local(val.tag)=="Value":
                        attrib[val.attrib.get("id","")]=val.attrib.get("value")
        if (attrib.get("REF_AREA") not in (None,country)
            or attrib.get("FREQ") not in (None,"M")):
            raise ValueError("H5_BIS_WRONG_COUNTRY_OR_FREQ")
        matching_series+=1
        for obs in series:
            if xml_local(obs.tag)!="Obs":
                continue
            props={xml_local(k):v for k,v in obs.attrib.items()}
            for child in obs:
                local=xml_local(child.tag)
                if local in ("ObsDimension","ObsValue"):
                    key="TIME_PERIOD" if local=="ObsDimension" else "OBS_VALUE"
                    props[key]=child.attrib.get("value")
            period=props.get("TIME_PERIOD")
            value=props.get("OBS_VALUE")
            if not period or len(period)!=7:
                raise ValueError("H5_BIS_BAD_MONTHLY_PERIOD")
            try: d=date.fromisoformat(period+"-01")
            except ValueError as e:
                raise ValueError("H5_BIS_BAD_PERIOD") from e
            if not START_RATE_MONTH<=d<=LAST_RATE_MONTH:
                raise ValueError("H5_BIS_RATE_AFTER_FROZEN_BOUNDS")
            if d in found:
                raise ValueError("H5_BIS_DUPLICATE_MONTH_OR_SERIES")
            if value in (None,"","."):
                continue
            try: number=float(value)
            except ValueError as e:
                raise ValueError("H5_BIS_NON_NUMERIC_POLICY_RATE") from e
            if not math.isfinite(number) or not -20<number<100:
                raise ValueError("H5_BIS_POLICY_RATE_RANGE_INVALID")
            found[d]=number
    if matching_series!=1 or len(found)<98:
        raise ValueError(
            f"H5_BIS_INCOMPLETE_{ccy}_series={matching_series}_count={len(found)}"
            f"_first={min(found).isoformat() if found else 'NONE'}"
            f"_last={max(found).isoformat() if found else 'NONE'}"
        )
    return found


def fetch_policy(ccy:str)->tuple[bytes,dict]:
    u=bis_url(ccy)
    headers={
        "User-Agent":"QORE-Native-Research-PolicyRateProxy/1.0",
        "Accept":"application/vnd.sdmx.structurespecificdata+xml;version=2.1,application/xml;q=0.9,*/*;q=0.1",
    }
    last=None
    for attempt in range(3):
        try:
            with urlopen(Request(u,headers=headers),timeout=40) as r:
                if r.status!=200 or not r.geturl().startswith("https://stats.bis.org/"):
                    raise ValueError("H5_BIS_WRONG_ORIGIN")
                raw=r.read(5_000_001)
                # source identity hashed, no raw rates exported
                rates=parse_policy_rates(raw,ccy)
                return raw,{
                    "currency":ccy,"BIS_ref_area":CURRENCY_BIS[ccy],
                    "monthly_observation_count":len(rates),
                    "first_month":min(rates).isoformat(),
                    "last_month":max(rates).isoformat(),
                    "source_URL":u,
                    "sha256":src.sha256_bytes(raw),
                    "historical_vintage_revisions_proven_absent":False,
                    "broker_policy_funding_equivalent":False,
                }
        except (HTTPError,URLError,TimeoutError) as e:
            last=e
            if attempt<2:time.sleep(attempt+1)
    raise RuntimeError("H5_BIS_SOURCE_UNAVAILABLE_"+ccy+"_"+type(last).__name__) from last


def policy_basket(rates:dict[str,dict[date,float]],day:date)->tuple[dict[str,float],dict[str,float]]:
    """Uses BIS month m-2 only, sign BASE minus QUOTE."""
    m=month_minus(day,LAG_MONTHS)
    if m not in {x for rs in rates.values() for x in rs}:
        raise ValueError("H5_POLICY_MONTH_NOT_PRESENT")
    for ccy in CURRENCY_BIS:
        if m not in rates.get(ccy,{}):
            raise ValueError("H5_RATE_MISSING_FAIL_CLOSED_"+ccy+"_"+m.isoformat())
    diff={s:(rates[s[:3]][m]-rates[s[3:]][m]) for s in FX28}
    ranked=sorted(FX28,key=lambda s:(-diff[s],s))
    pos={s:0. for s in FX28}
    for s in ranked[:LONGS]:pos[s]=ABS_WEIGHT
    for s in ranked[-SHORTS:]:pos[s]=-ABS_WEIGHT
    if (len({s for s in ranked[:LONGS]+ranked[-SHORTS:]})!=12 or
        abs(sum(pos.values()))>1e-12 or
        abs(sum(abs(p) for p in pos.values())-1.)>1e-12):
        raise ValueError("H5_BASKET_NOT_6_BY_6_NEUTRAL")
    return pos,diff


def calendar_and_maps(dailies:dict)->tuple[list[date],dict,dict]:
    check_universe()
    if set(dailies)!=set(FX28):
        raise ValueError("H5_EXACT_FX28_SOURCE_REQUIRED")
    maps={}
    common=None
    union=set()
    for s in FX28:
        rows=dailies[s]
        indexed={x["date"]:x for x in rows}
        if not indexed or len(indexed)!=len(rows):
            raise ValueError("H5_BAD_DAILY_SERIES_DUPLICATE_"+s)
        for d,x in indexed.items():
            if not src.LOWER<=d<src.EMBARGO:
                raise ValueError("H5_HOLDOUT_FORBIDDEN")
            if (x["entry_ts"].date()!=d or
                x["entry_ts"].hour*60+x["entry_ts"].minute<src.FIRST_EXEC_MINUTE_UTC):
                raise ValueError("H5_OPEN_TOO_EARLY")
        maps[s]=indexed
        dates=set(indexed)
        union|=dates
        common=dates if common is None else common & dates
    days=sorted(common or ())
    if len(days)<1500:
        raise ValueError("H5_INSUFFICIENT_OVERLAP_DATES")
    for a,b in zip(days,days[1:]):
        if (b-a).days>src.MAX_GAP_DAYS:
            raise ValueError("H5_UNPRICED_MARK_GAP")
    return days,maps,{
        "fx_count":28,"common_dates":len(days),
        "union_dates":len(union),
        "union_days_missing_at_least_one_fx":len(union)-len(days),
        "earliest_utc":days[0].isoformat(),
        "latest_utc":days[-1].isoformat(),
    }


def score(dailies:dict,rates:dict[str,dict[date,float]])->dict:
    common,maps,coverage=calendar_and_maps(dailies)
    result={}
    for era,begin,end in (("DEV",src.DEV_START,src.VALIDATION_START),
                          ("DIAG",src.VALIDATION_START,src.EMBARGO)):
        dates=[d for d in common if begin<=d<end]
        if len(dates)<100:raise ValueError("H5_TOO_FEW_SESSIONS_"+era)
        pos={s:0. for s in FX28}
        active_spreads={s:0. for s in FX28}
        old=None
        last_month=None
        spot_stream={}
        theory_stream={}
        benchmark={}
        turnover=0.
        fee_total=0.
        rebalances=0
        changed_orders=0
        currency_abs_exposures=Counter()
        max_abs_currency_exposure=0.
        basket_records=[]
        for d in dates:
            gross=0.
            ideal_yield=0.
            if old is not None:
                if (d-old).days>src.MAX_GAP_DAYS:
                    raise ValueError("H5_CANNOT_MARK_GAP")
                delta=(d-old).days
                for s,p in pos.items():
                    move=maps[s][d]["entry_open"]/maps[s][old]["entry_open"]-1.
                    if not math.isfinite(move) or abs(move)>.45:
                        raise ValueError("H5_BAD_DAILY_RETURN")
                    gross+=p*move
                    # PERCENT policy rate annualized -> decimal annual -> calendar day accrual.
                    ideal_yield+=p*(active_spreads[s]/100.)*delta/365.
            old=d
            requested=(d.year,d.month)
            fee=0.
            if requested!=last_month:
                last_month=requested
                target,spreads=policy_basket(rates,d)
                # Rates m-2, no OHLC information from decision day.
                for s in FX28:
                    # Historical last bar metadata from prior day never feeds rate signal;
                    # ensures source session at open is not accidentally stale.
                    if not math.isfinite(spreads[s]):raise ValueError("H5_BAD_SPREAD")
                changes=sum(abs(target[s]-pos[s]) for s in FX28)
                changed_orders+=sum(target[s]!=pos[s] for s in FX28)
                turnover+=changes
                fee+=changes*SIDE_COST
                pos=target
                active_spreads=spreads
                rebalances+=1
                exposures=defaultdict(float)
                for s,p in pos.items():
                    exposures[s[:3]]+=p
                    exposures[s[3:]]-=p
                max_abs_currency_exposure=max(max_abs_currency_exposure,
                                               max(abs(v) for v in exposures.values()))
                for ccy,exp in exposures.items():
                    currency_abs_exposures[ccy]+=abs(exp)
                if len(basket_records)<3:
                    basket_records.append({
                        "decision_utc":d.isoformat(),
                        "rate_month_m_minus_2":month_minus(d,2).isoformat(),
                        "longs":[s for s in FX28 if pos[s]>0],
                        "shorts":[s for s in FX28 if pos[s]<0],
                    })
            if d==dates[-1]:
                close_side=sum(abs(p) for p in pos.values())
                turnover+=close_side
                changed_orders+=sum(p!=0 for p in pos.values())
                fee+=SIDE_COST*close_side
                pos={s:0. for s in FX28}
            fee_total+=fee
            spot_stream[d]=gross-fee
            theory_stream[d]=gross+ideal_yield-fee
        calendar=[]
        date_cursor=begin
        while date_cursor<end:
            if date_cursor.weekday()<5:calendar.append(date_cursor)
            date_cursor+=timedelta(days=1)
        a=[spot_stream.get(x,0.) for x in calendar]
        b=[theory_stream.get(x,0.) for x in calendar]
        result[era]={
            "SPOT_ONLY_AFTER_2BP_ASSUMED_COST":src.performance(a),
            "SPOT_PLUS_IDEALIZED_POLICY_ACCRUAL_NOT_BROKER_NET":src.performance(b),
            "daily_calendar_sessions":len(calendar),
            "market_common_calendar_mark_days":len(dates),
            "rebalance_decisions":rebalances,
            "symbol_change_orders_including_liquidation":changed_orders,
            "turnover_abs_weight_sides":turnover,
            "assumed_2bp_cost_bp_capital_sum_not_compounded":fee_total*10000.,
            "currency_max_abs_net_exposure_nominal":max_abs_currency_exposure,
            "currency_abs_exposure_sum_across_rebalances":dict(currency_abs_exposures),
            "first_three_month_decisions_not_strategy_selection":basket_records,
        }
    sp=result["DIAG"]["SPOT_ONLY_AFTER_2BP_ASSUMED_COST"]["annualized_sharpe_252_rf0"]
    verdict=("NO_POSITIVE_SPOT_SUPPORT" if sp is None or sp<=0
             else "WEAK_SPOT_ONLY" if sp<=.5
             else "PROMISING_SPOT_ONLY_NOT_CERTIFIED")
    return {
        "identity":IDENTITY,
        "preregistered_SPOT_ONLY_verdict":verdict,
        "rate_tenor":"BIS_POLICY_RATE_MONTHLY_EOP_NOT_3M_INTERBANK_NOT_FORWARD",
        "policy_rate_decision_lag_full_months":LAG_MONTHS,
        "num_fx_pairs":28,"num_base_currencies":8,
        "long_top_pairs":6,"short_bottom_pairs":6,
        "cost_bps_per_notional_side":2,
        "gross_exposure":1.,"nominal_net_exposure":0.,
        "calendar_28_source":coverage,"performance":result,
        "has_no_verified_real_contract_swap":True,
        "B_component_is_idealized_yield_not_executable":True,
        "source_rates_2026_revision_vintage_not_proven":True,
        "retrospective_common_calendar_has_possible_availability_bias":True,
        "DIAG_adaptively_exposed_by_prior_H1_H2_H3":True,
        "economic_holdout_2024_09_17_onward_read":False,
        "broker_NET_certified":False,"certified_traders":0,
        "production_untouched":True,
    }


def run(source_tmp:Path,output:Path)->dict:
    repo=os.getenv("GITHUB_REPOSITORY","mezas3238-hue/qore-core")
    token=os.getenv("GH_TOKEN")
    if not token:raise ValueError("H5_READONLY_TOKEN_MISSING")
    # Source-only preflight FIRST, before costlier 28 ZIP archive retrieval.
    # Does not inspect any FX return or tune an economic parameter.
    rates={}
    rate_evidence=[]
    for ccy in sorted(CURRENCY_BIS):
        raw,meta=fetch_policy(ccy)
        values=parse_policy_rates(raw,ccy)
        rates[ccy]=values
        rate_evidence.append(meta)
        print("H5_REAL_BIS_POLICY_SOURCE_PASS",ccy,len(values),flush=True)
    source_tmp.mkdir(parents=True,exist_ok=True)
    reg=src.get_artifact_register(repo,token)
    data={}
    source_reports=[]
    for s in FX28:
        item=reg[s]
        archive=source_tmp/(s+".zip")
        try:
            subprocess.run([
                "curl","--fail","--silent","--show-error","--location",
                "--retry","2","-H",f"Authorization: Bearer {token}",
                "-H","Accept: application/vnd.github+json",
                f"https://api.github.com/repos/{repo}/actions/artifacts/{item['artifact_id']}/zip",
                "--output",str(archive)],check=True)
            bars,witness=src.daily_from_zip(archive,s)
            data[s]=bars
            witness.update({"original_run":item["original_run"]})
            source_reports.append(witness)
            print("H5_G0_SHA28_PASS",s,len(bars),flush=True)
        finally:
            archive.unlink(missing_ok=True)
    if len(source_reports)!=28 or len(rate_evidence)!=8:
        raise ValueError("H5_G0_28_AND_BIS_8_NOT_ATTESTED")
    if any(x.get("source_sha_verified_11_annual_partitions") is not True
           for x in source_reports):
        raise ValueError("H5_ORIGINAL_G0_SOURCE_HASH_FAILED")
    result=score(data,rates)
    result["source_G0_hash_reports"]=source_reports
    result["policy_rate_evidence"]=rate_evidence
    output.mkdir(parents=True,exist_ok=True)
    p=output/"H5_FX_POLICY_CARRY28_MONTHLY_BIS8_2BP_ASSUMED_ONLY.json"
    p.write_text(json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+"\n")
    (output/"SHA256SUMS.txt").write_text(
        src.sha256_bytes(p.read_bytes())+"  "+p.name+"\n")
    print("H5_FX_CARRY_POLICY8_28_ONE_TEST_RESULT",
        json.dumps({
            "verdict":result["preregistered_SPOT_ONLY_verdict"],
            "DEV":result["performance"]["DEV"],
            "DIAG":result["performance"]["DIAG"],
            "source8":len(rate_evidence),"originalFX":len(source_reports),
            "holdout_open":False,"broker_NET":False,"certified":0
        },sort_keys=True),flush=True)
    return result


def main():
    p=argparse.ArgumentParser()
    p.add_argument("workdir",type=Path)
    p.add_argument("outputdir",type=Path)
    args=p.parse_args()
    run(args.workdir,args.outputdir)


if __name__=="__main__":
    main()
