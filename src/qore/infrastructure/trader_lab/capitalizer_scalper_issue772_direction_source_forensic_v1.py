"""Issue772 causal source witnesses: NO economic outcomes, NO signals authorized.

H1 event-recovery calls the ORIGINAL V48 POI observer for provenance comparison.
It MUST NOT be presented as an independent first-online reimplementation.
Trend-4 is separately calculated only from completed native M1-based H1 bars.
"""
from __future__ import annotations

import argparse
import bisect
import hashlib
import json
from collections import Counter
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
    iter_cibo_m1,
)
from qore.infrastructure.trader_lab.capitalizer_generic_scalp_census_v48 import (
    _aggregate,
    _build_h1_bias_events,
)
from qore.infrastructure.trader_lab.capitalizer_high_frequency_capacity_census_v49 import (
    DEFAULT_LOOKBACK,
    DEV_WINDOW_END,
    DEV_WINDOW_START,
    V49Opportunity,
)
from qore.infrastructure.trader_lab.capitalizer_scalper_v49_v50_g_waterfall_v1 import (
    source_id,
)

IDENTITY="QORE_SCALPER_ISSUE772_P0_DIRECTION_CAUSAL_SOURCE_FORENSICS_V1"
SAMPLE_PREFIX="QORE_SCALPER_H1_M15_M1_AUDIT_20261011|"


def load_sources(root:Path)->tuple[V49Opportunity,...]:
    found=tuple(root.rglob("capitalizer-*-v49-hf-capacity-opportunities.jsonl"))
    if len(found)!=1:
        raise ValueError("exactly one frozen V49 source opportunity file required")
    events=tuple(
        V49Opportunity(**json.loads(x))
        for x in found[0].read_text(encoding="utf-8").splitlines()
        if x.strip()
    )
    if not events:
        raise ValueError("no frozen source opportunity events")
    return events


def _date(value:str)->datetime:
    t=datetime.fromisoformat(value)
    if t.utcoffset() is None:
        raise ValueError("timezone missing from causal timestamp")
    return t


def sample_hash(sid:str)->str:
    return hashlib.sha256((SAMPLE_PREFIX+sid).encode("utf-8")).hexdigest()


def price_direction(close_delta:Decimal)->str:
    return "UP" if close_delta>0 else "DOWN" if close_delta<0 else "FLAT"


def _candle(bar:CapitalizerM1Bar)->dict[str,Any]:
    return {
        "opened_at":bar.opened_at.isoformat(),
        "closed_at":bar.closed_at.isoformat(),
        "open":str(bar.open),"high":str(bar.high),
        "low":str(bar.low),"close":str(bar.close),
    }


def source_witness(
    item:V49Opportunity,
    bars:tuple[CapitalizerM1Bar,...],
    m1_times:tuple[datetime,...],
    h1:tuple[Any,...],
    h1_times:tuple[datetime,...],
    m15:tuple[Any,...],
    m15_times:tuple[datetime,...],
    bias_events:tuple[Any,...],
    event_times:tuple[datetime,...],
    native_feed_digest:str,
)->dict[str,Any]:
    entry=_date(item.m1_trigger_confirmed_at)
    setup=_date(item.m15_setup_confirmed_at)
    state=_date(item.h1_state_from)
    inherited=item.h1_state_basis.startswith("SESSION_INHERITED:")
    sid=source_id(item)
    # Future active_until is only a historical label; NEVER a predecision
    # input to this witness or an independent first-online classifier.
    violations=[]
    if not state<=setup<=entry:
        violations.append("FUTURE_SOURCE_H1_OR_M15_TIMESTAMP")
    i=bisect.bisect_right(m1_times,entry)-1
    if i<0 or bars[i].closed_at!=entry:
        violations.append("M1_ENTRY_CLOSED_PRICE_NOT_WITNESSED")
        reference_ok=False
    else:
        reference_ok=bars[i].close==Decimal(item.decision_reference_price)
        if not reference_ok:
            violations.append("ENTRY_PRICE_DIFFERS_NATIVE_M1_CLOSE")
    h=bisect.bisect_right(h1_times,entry)
    current_h1=tuple(h1[max(0,h-5):h])
    if h>=5:
        trend4=price_direction(current_h1[-1].source.close-current_h1[0].source.close)
    else:
        trend4="UNKNOWN"
    expected="UP" if item.h1_state_direction=="BULLISH" else "DOWN"
    agreement=(
        "UNKNOWN" if trend4=="UNKNOWN"
        else "FLAT" if trend4=="FLAT"
        else "MATCH" if trend4==expected else "OPPOSE"
    )
    # For inherited states the ORIGINAL state_from is reset to session start.
    # Recover the true source event BEFORE that date (no event after entry).
    desired_basis=item.h1_state_basis.split("SESSION_INHERITED:",1)[-1]
    j=bisect.bisect_right(event_times,state if inherited else entry)
    if inherited:
        eligible=bias_events[:j]
        source_matches=[
            ev for ev in eligible
            if f"{ev.closure_kind}:{ev.poi_kind}"==desired_basis
            and ev.direction.value==item.h1_state_direction
            and ev.confirmed_at<state
        ]
    else:
        source_matches=[
            ev for ev in bias_events[:j]
            if ev.confirmed_at==state
            and f"{ev.closure_kind}:{ev.poi_kind}"==desired_basis
            and ev.direction.value==item.h1_state_direction
        ]
    origin=source_matches[-1] if source_matches else None
    origin_at=origin.confirmed_at if origin is not None else None
    if origin_at is None:
        origin_status="ORIGINAL_V48_BIAS_EVENT_UNRESOLVED"
    else:
        origin_status="ORIGINAL_V48_BIAS_EVENT_MATCH"
        if origin_at>entry:
            violations.append("SOURCE_H1_EVENT_CONFIRMED_AFTER_ENTRY")
    k=bisect.bisect_right(m15_times,entry)
    last_m15=m15[k-1] if k else None
    m15_confirmed_in_closed=(
        any(z.closed_at==setup for z in m15[:k]) if k else False
    )
    if not m15_confirmed_in_closed:
        violations.append("STORED_M15_SETUP_TIMESTAMP_NOT_NATIVE_CLOSE")
    if last_m15 is not None and last_m15.closed_at>entry:
        violations.append("OPEN_M15_USED_AS_CLOSED")
    entry_abs=Decimal(item.decision_reference_price)
    stop=Decimal(item.m15_protected_swing_price)
    risk=abs(entry_abs-stop)
    if risk<=0:
        violations.append("ZERO_RISK_SOURCE")
    valid_geometry=(
        stop<entry_abs if item.h1_state_direction=="BULLISH"
        else stop>entry_abs
    )
    if not valid_geometry:
        violations.append("DIRECTION_STOP_SWING_GEOMETRY_INVALID")
    idx=bisect.bisect_right(m1_times,entry)
    prior_m1=tuple(bars[max(0,idx-10):idx])
    # A valid timestamp chain is not independently verified CISD semantics.
    # M15 price, pivot-right, source POI, full first-online trigger remain
    # NOT_EVALUATED until corroborated by independent reconstruction.
    displacement=(
        (entry_abs-stop)/risk if item.h1_state_direction=="BULLISH"
        else (stop-entry_abs)/risk
    ) if risk>0 else None
    return {
        "source_opportunity_id":sid,"selection_rank_sha256":sample_hash(sid),
        "symbol":item.symbol,"session":item.session,
        "operating_date":item.operating_date,
        "trigger_family":item.m1_trigger_family,
        "h1_state_basis":item.h1_state_basis,
        "h1_state_inherited":inherited,
        "h1_direction":item.h1_state_direction,
        "m1_direction":"LONG" if expected=="UP" else "SHORT",
        "decision_at":item.m1_trigger_confirmed_at,
        "original_state_from":item.h1_state_from,
        "original_state_until_RETROSPECTIVE_NOT_ASOF":item.h1_state_until,
        "original_source_origin_at":origin_at.isoformat() if origin_at else None,
        "original_source_origin_status":origin_status,
        "h1_source_age_minutes":(
            (entry-origin_at).total_seconds()/60 if origin_at else None
        ),
        "original_h1_basis":(
            f"{origin.closure_kind}:{origin.poi_kind}" if origin else None
        ),
        "h1_trend4_completed_native":trend4,
        "h1_trend4_agreement":agreement,
        "h1_last_closed_at":current_h1[-1].closed_at.isoformat()
            if current_h1 else None,
        "h1_last_5_closed_candles":[{
            "opened_at":x.opened_at.isoformat(),
            "closed_at":x.closed_at.isoformat(),
            "open":str(x.source.open),"high":str(x.source.high),
            "low":str(x.source.low),"close":str(x.source.close),
            "native_minutes_aggregated":x.minute_count,
        } for x in current_h1],
        "m15_setup_confirmed_at":item.m15_setup_confirmed_at,
        "m15_confirmed_in_closed_native":m15_confirmed_in_closed,
        "m15_setup_to_entry_minutes":(entry-setup).total_seconds()/60,
        "m15_last_closed_at":last_m15.closed_at.isoformat() if last_m15 else None,
        "m15_recent_candles":[{
            "opened_at":x.opened_at.isoformat(),
            "closed_at":x.closed_at.isoformat(),
            "open":str(x.source.open),"high":str(x.source.high),
            "low":str(x.source.low),"close":str(x.source.close),
            "native_minutes_aggregated":x.minute_count,
        } for x in m15[max(0,k-5):k]],
        "m1_recent_closed_candles":[_candle(x) for x in prior_m1],
        "entry_price":str(entry_abs),
        "m15_swing_stop_price":str(stop),
        "structural_h1_target_price":item.structural_target_witness_price,
        "entry_matches_native_m1_close":reference_ok,
        "stop_geometry_valid":valid_geometry,
        "entry_distance_from_stored_swing_R":str(displacement) if displacement is not None else None,
        "causal_timestamp_failures":violations,
        "causal_timestamp_pass":not violations,
        "swing_right_candle_and_earliest_availability":"NOT_IN_SOURCE_NEEDS_INDEPENDENT_RECONSTRUCTION",
        "m1_sweep_series_CISD_first_online":"NOT_IN_SOURCE_NEEDS_INDEPENDENT_RECONSTRUCTION",
        "h1_original_events_used_as_independent_oracle":False,
        "feed_sha256_native_research_slice":native_feed_digest,
        "outcomes_accessed":False,
        "author_semantics_certified":False,
        "first_online_independently_complete":False,
    }


def market(frozen_root:Path,native_root:Path,output:Path)->dict[str,Any]:
    sources=load_sources(frozen_root)
    symbol=sources[0].symbol
    if any(x.symbol!=symbol for x in sources):
        raise ValueError("multiple markets in one source ledger")
    # 15d lookback = enough to recover most events, but NOT guaranteed
    # origin for inherited signals beyond source lookback.
    bars=tuple(
        b for b in iter_cibo_m1(native_root)
        if DEV_WINDOW_START-DEFAULT_LOOKBACK<=b.opened_at<DEV_WINDOW_END
    )
    if not bars or any(b.symbol!=symbol for b in bars):
        raise ValueError("missing native M1 provider research observations")
    m1_times=tuple(x.closed_at for x in bars)
    if any(m1_times[i]>=m1_times[i+1] for i in range(len(bars)-1)):
        raise ValueError("native M1 out of order")
    native_feed_digest=hashlib.sha256(
        "".join(
            f"{b.opened_at.isoformat()}|{b.open}|{b.high}|{b.low}|{b.close}\n"
            for b in bars
        ).encode()
    ).hexdigest()
    h1=_aggregate(bars,minutes=60)
    m15=_aggregate(bars,minutes=15)
    h1_times=tuple(x.closed_at for x in h1)
    m15_times=tuple(x.closed_at for x in m15)
    events=_build_h1_bias_events(h1)
    event_times=tuple(x.confirmed_at for x in events)
    traces=tuple(source_witness(
        x,bars,m1_times,h1,h1_times,m15,m15_times,
        events,event_times,native_feed_digest
    ) for x in sources)
    if len({x["source_opportunity_id"] for x in traces})!=len(sources):
        raise ValueError("duplicate source ID on market")
    output.mkdir(parents=True,exist_ok=True)
    (output/"scalper-issue772-all-source-causal-witnesses.jsonl").write_text(
        "".join(json.dumps(x,sort_keys=True)+"\n" for x in traces),
        encoding="utf-8",
    )
    counts=Counter()
    for x in traces:
        counts["INHERITED" if x["h1_state_inherited"] else "FRESH"]+=1
        counts["ORIGIN_MATCH" if x["original_source_origin_at"] else
               "ORIGIN_UNKNOWN"]+=1
        counts["DIRECTION_"+x["h1_trend4_agreement"]]+=1
        counts["TIMESTAMP_PASS" if x["causal_timestamp_pass"] else
               "TIMESTAMP_FAIL"]+=1
        counts["TRIGGER_"+x["trigger_family"]]+=1
        for reason in x["causal_timestamp_failures"]:
            counts["TIMESTAMP_FAILURE_"+reason]+=1
    report={
        "identity":IDENTITY,"symbol":symbol,"original_source_n":len(sources),
        "counts":dict(sorted(counts.items())),
        "native_research_slice_m1_bars":len(bars),
        "native_feed_sha256":native_feed_digest,
        "outcomes_not_loaded":True,
        "original_bias_detector_only_as_comparator":True,
        "independent_first_online_full_route_complete":False,
        "v49_or_production_changed":False,
    }
    (output/"scalper-issue772-market-causal-census.json").write_text(
        json.dumps(report,sort_keys=True,indent=2)+"\n",encoding="utf-8",
    )
    return report


def main()->None:
    p=argparse.ArgumentParser()
    p.add_argument("frozen",type=Path)
    p.add_argument("native",type=Path)
    p.add_argument("output",type=Path)
    x=p.parse_args()
    print("ISSUE772_MARKET",json.dumps(market(x.frozen,x.native,x.output),sort_keys=True))


if __name__=="__main__":
    main()
