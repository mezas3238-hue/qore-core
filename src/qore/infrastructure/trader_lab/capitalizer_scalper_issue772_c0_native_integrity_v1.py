"""Issue772 Gate C0: exact native-minute integrity of V49 H1/M15 witnesses.

READ ONLY. _build_h1_bias_events and _all_m15_setups are ORIGINAL
comparators, NOT independent first-online/author-adjudicated detectors.
"""
from __future__ import annotations

import argparse
import bisect
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
    iter_cibo_m1,
)
from qore.infrastructure.trader_lab.capitalizer_contract import CapitalizerSession
from qore.infrastructure.trader_lab.capitalizer_generic_scalp_census_v48 import (
    V48AggregatedBar,
    _aggregate,
    _build_h1_bias_events,
)
from qore.infrastructure.trader_lab.capitalizer_h1_context_state_v49 import (
    IDENTITY as STATE_ID,
    V49H1ContextState,
    V49H1StateEndReason,
)
from qore.infrastructure.trader_lab.capitalizer_high_frequency_capacity_census_v49 import (
    DEFAULT_LOOKBACK,
    DEV_WINDOW_END,
    DEV_WINDOW_START,
    V49Opportunity,
    _all_m15_setups,
    _slice,
)
from qore.infrastructure.trader_lab.capitalizer_scalper_issue772_direction_source_forensic_v1 import (  # noqa: E501
    load_sources,
)
from qore.infrastructure.trader_lab.capitalizer_scalper_v49_v50_g_waterfall_v1 import source_id
from qore.infrastructure.trader_lab.capitalizer_source_observation_detectors_v2 import (
    CapitalizerSourceBar,
    CapitalizerSourceDirection,
)
from qore.infrastructure.trader_lab.capitalizer_ttrades_structural_cisd_v48 import (
    V48TimedSourceBar,
)

ID="QORE_SCALPER_ISSUE772_GATE_C0_CANDLE_INTEGRITY_V1"


@dataclass(frozen=True,slots=True)
class Bucket:
    start:datetime
    end:datetime
    minutes:int
    observed:int
    missing:int
    eligible_legacy:bool
    strict_complete:bool
    leading:bool
    trailing:bool
    internal_gap:bool
    duplicate:bool
    premature_close:bool
    actual_first_open:datetime
    actual_last_close:datetime
    strict_bar:V48AggregatedBar|None

    def detail(self)->dict[str,Any]:
        return {
            "nominal_start":self.start.isoformat(),
            "nominal_end":self.end.isoformat(),
            "observed_minutes":self.observed,
            "expected_minutes":self.minutes,
            "missing_distinct_minutes":self.missing,
            "legacy_accepted":self.eligible_legacy,
            "strict_complete":self.strict_complete,
            "partial_leading":self.leading,"partial_trailing":self.trailing,
            "internal_gap":self.internal_gap,"duplicate_m1":self.duplicate,
            "premature_last_m1_close":self.premature_close,
            "actual_first_open":self.actual_first_open.isoformat(),
            "actual_last_close":self.actual_last_close.isoformat(),
            "complete_at":self.end.isoformat() if self.strict_complete else "UNAVAILABLE",
            "cause_market_closed_or_feed_gap":"UNKNOWN_NO_EXTERNAL_EXCHANGE_CALENDAR",
        }


def bucketize(
    bars:tuple[CapitalizerM1Bar,...],minutes:int,
)->tuple[dict[datetime,Bucket],tuple[V48AggregatedBar,...],Counter[str]]:
    if minutes not in (15,60):
        raise ValueError("only H1 M15")
    by_bucket:dict[int,list[CapitalizerM1Bar]]=defaultdict(list)
    for bar in bars:
        by_bucket[int(bar.opened_at.timestamp())//(60*minutes)].append(bar)
    info:dict[datetime,Bucket]={}
    strict:list[V48AggregatedBar]=[]
    tally:Counter[str]=Counter()
    for key,raw in sorted(by_bucket.items()):
        chunk=sorted(raw,key=lambda b:b.opened_at)
        start=datetime.fromtimestamp(key*minutes*60,tz=UTC)
        end=start+timedelta(minutes=minutes)
        actual={x.opened_at for x in chunk}
        # Set membership protects against duplicates and off-grid seconds.
        expected={start+timedelta(minutes=k) for k in range(minutes)}
        absent=expected-actual
        duplicates=len(chunk)!=len(actual)
        leading=start not in actual
        trailing=end-timedelta(minutes=1) not in actual
        between=[
            start+timedelta(minutes=k) for k in range(minutes)
            if start+timedelta(minutes=k) not in actual
        ]
        internal=any(not leading and not trailing
                     or (start<dt<end-timedelta(minutes=1))
                     for dt in between)
        wrong_clock=any(
            x.closed_at!=x.opened_at+timedelta(minutes=1)
            or x.opened_at.second!=0 or x.opened_at.microsecond!=0
            for x in chunk
        )
        complete=(len(chunk)==minutes and not absent and not duplicates
                  and not wrong_clock)
        allowed=len(chunk)>=minutes*3//4
        premature=chunk[-1].closed_at<end
        if complete:
            z=V48AggregatedBar(
                opened_at=start,closed_at=end,
                source=CapitalizerSourceBar(
                    open=chunk[0].open,
                    high=max(x.high for x in chunk),
                    low=min(x.low for x in chunk),
                    close=chunk[-1].close,
                ),
                minute_count=minutes,
            )
            strict.append(z)
        else:
            z=None
        obj=Bucket(
            start=start,end=end,minutes=minutes,observed=len(chunk),
            missing=len(absent),eligible_legacy=allowed,
            strict_complete=complete,leading=leading,trailing=trailing,
            internal_gap=internal,duplicate=duplicates,
            premature_close=premature,actual_first_open=chunk[0].opened_at,
            actual_last_close=chunk[-1].closed_at,strict_bar=z,
        )
        info[start]=obj
        tally["BUCKET_NATIVE_OBSERVED"]+=1
        tally["LEGACY_ACCEPTED" if allowed else "LEGACY_REJECTED"]+=1
        tally["STRICT_COMPLETE" if complete else "STRICT_INVALID"]+=1
        if allowed and not complete:
            tally["LEGACY_ACCEPTED_NONSTRICT"]+=1
        if allowed and premature:
            tally["LEGACY_ACCEPTED_EARLY_CLOSE"]+=1
        for name,flag in (
            ("MISSING_MINUTES",bool(absent)),
            ("LEADING_GAP",leading),("TRAILING_GAP",trailing),
            ("INTERNAL_GAP",internal),("DUPLICATE",duplicates),
            ("PREMATURE_CLOSE",premature),("WRONG_M1_CLOCK",wrong_clock),
        ):
            if flag:
                tally[name]+=1
    return info,tuple(strict),tally


def bucket_key(at:datetime,minutes:int)->datetime:
    key=int(at.timestamp())//(minutes*60)
    return datetime.fromtimestamp(key*minutes*60,tz=UTC)


def diagnose(
    *,
    frozen_root:Path,native_root:Path,output:Path,
)->dict[str,Any]:
    sources=load_sources(frozen_root)
    symbol=sources[0].symbol
    if any(x.symbol!=symbol for x in sources):
        raise ValueError("one symbol only")
    m1=tuple(x for x in iter_cibo_m1(native_root)
             if DEV_WINDOW_START-DEFAULT_LOOKBACK<=x.opened_at<DEV_WINDOW_END)
    if not m1 or any(x.symbol!=symbol for x in m1):
        raise ValueError("provider native M1 missing or multiple symbols")
    for prev,new in zip(m1,m1[1:]):
        if prev.opened_at>=new.opened_at:
            raise ValueError("M1 native chronology duplicate or unordered")
    h_buckets,strict_h,h_count=bucketize(m1,60)
    q_buckets,strict_q,q_count=bucketize(m1,15)
    old_h=_aggregate(m1,minutes=60)
    old_q=_aggregate(m1,minutes=15)
    if len(old_h)!=h_count["LEGACY_ACCEPTED"] or len(old_q)!=q_count["LEGACY_ACCEPTED"]:
        raise ValueError("legacy aggregate source acceptance not reproduced")
    for frequency,old,buckets in (
        (60,old_h,h_buckets),(15,old_q,q_buckets)
    ):
        for bar in old:
            chk=buckets[bucket_key(bar.opened_at,frequency)]
            if (bar.opened_at!=chk.actual_first_open or
                bar.closed_at!=chk.actual_last_close or
                bar.minute_count!=chk.observed):
                raise ValueError("original V48 aggregate witness changed")
    original_events=_build_h1_bias_events(old_h)
    strict_events=_build_h1_bias_events(strict_h)
    strict_event_keys={
        (x.confirmed_at.isoformat(),x.direction.value,
         f"{x.closure_kind}:{x.poi_kind}")
        for x in strict_events
    }
    old_end=tuple(x.closed_at for x in old_h)
    strict_times=tuple(x.closed_at for x in strict_h)
    old_q_timed=tuple(
        V48TimedSourceBar(x.opened_at,x.closed_at,x.source) for x in old_q
    )
    strict_q_timed=tuple(
        V48TimedSourceBar(x.opened_at,x.closed_at,x.source) for x in strict_q
    )
    old_q_open=tuple(x.opened_at for x in old_q_timed)
    strict_q_open=tuple(x.opened_at for x in strict_q_timed)
    all_groups:dict[tuple[str,str,str,str,str],list[V49Opportunity]]=defaultdict(list)
    for row in sources:
        g=(row.session,row.operating_date,row.h1_state_from,
           row.h1_state_until,row.h1_state_direction)
        all_groups[g].append(row)
    state_observations:dict[tuple[str,str,str,str,str],dict[str,Any]]={}
    for key,rows in all_groups.items():
        ses,_,fr,until,direction=key
        begin=datetime.fromisoformat(fr)
        finish=datetime.fromisoformat(until)
        state=V49H1ContextState(
            identity=STATE_ID,session=CapitalizerSession(ses),
            direction=CapitalizerSourceDirection(direction),
            active_from=begin,active_until=finish,
            established_by=rows[0].h1_state_basis,
            end_reason=V49H1StateEndReason.SESSION_END,
        )
        old_window=_slice(
            old_q_timed,old_q_open,start=begin,end=finish
        )
        strict_window=_slice(
            strict_q_timed,strict_q_open,start=begin,end=finish
        )
        source_setups=_all_m15_setups(old_window,state=state)
        strict_setups=_all_m15_setups(strict_window,state=state)
        old_lookup={
            (x.confirmed_at.isoformat(),str(x.swing_price)):x
            for x in source_setups if x.confirmed_at and x.swing_price is not None
        }
        strict_keys={
            (x.confirmed_at.isoformat(),str(x.swing_price))
            for x in strict_setups if x.confirmed_at and x.swing_price is not None
        }
        state_observations[key]={
            "lookup":old_lookup,"strict":strict_keys,
            "old_window":old_window,
        }
    rows_out=[]
    c=Counter()
    for row in sources:
        sid=source_id(row)
        dec=datetime.fromisoformat(row.m1_trigger_confirmed_at)
        frm=datetime.fromisoformat(row.h1_state_from)
        inherited=row.h1_state_basis.startswith("SESSION_INHERITED:")
        expected_basis=row.h1_state_basis.removeprefix("SESSION_INHERITED:")
        target_events=(
            [ev for ev in original_events
             if ev.confirmed_at<frm and ev.direction.value==row.h1_state_direction
             and f"{ev.closure_kind}:{ev.poi_kind}"==expected_basis]
            if inherited else
            [ev for ev in original_events
             if ev.confirmed_at==frm and ev.direction.value==row.h1_state_direction
             and f"{ev.closure_kind}:{ev.poi_kind}"==expected_basis]
        )
        ev=target_events[-1] if target_events else None
        h_direct=[]
        h_missing=False
        h_origin=None
        event_strict=False
        if ev is not None:
            h_origin=ev.confirmed_at.isoformat()
            ix=bisect.bisect_left(old_end,ev.confirmed_at)
            if ix>=len(old_h) or old_h[ix].closed_at!=ev.confirmed_at:
                h_missing=True
            else:
                n=3 if "CANDLE3" in ev.closure_kind.upper() else 2
                for h in old_h[max(0,ix-n+1):ix+1]:
                    chk=h_buckets[bucket_key(h.opened_at,60)]
                    h_direct.append(chk)
                if len(h_direct)!=n:
                    h_missing=True
            event_strict=(
                (h_origin,ev.direction.value,
                 f"{ev.closure_kind}:{ev.poi_kind}") in strict_event_keys
            )
        k=(row.session,row.operating_date,row.h1_state_from,
           row.h1_state_until,row.h1_state_direction)
        group=state_observations[k]
        setup_at=row.m15_setup_confirmed_at
        swing=row.m15_protected_swing_price
        original_setup=group["lookup"].get((setup_at,swing))
        m_direct=[]
        m_gap=False
        m_missing=original_setup is None
        original_observation=None
        if original_setup is not None:
            local=group["old_window"]
            center=next(
                (i for i,x in enumerate(local)
                 if x.opened_at==original_setup.swing_occurred_at),None
            )
            if center is None or center==0 or center>=len(local)-1:
                m_missing=True
            else:
                relevant={center-1,center,center+1}
                for i,x in enumerate(local):
                    if (original_setup.causal_series_started_at is not None
                        and original_setup.causal_series_ended_at is not None
                        and x.opened_at>=original_setup.causal_series_started_at
                        and x.closed_at<=original_setup.causal_series_ended_at):
                        relevant.add(i)
                    if x.closed_at==original_setup.confirmed_at:
                        relevant.add(i)
                if not any(local[i].closed_at==original_setup.confirmed_at
                           for i in relevant):
                    m_missing=True
                else:
                    m_direct=[
                        q_buckets[bucket_key(local[i].opened_at,15)]
                        for i in sorted(relevant)
                    ]
                    left=min(relevant)
                    right=max(relevant)
                    m_gap=any(
                        local[i-1].closed_at!=local[i].opened_at
                        for i in range(left+1,right+1)
                    )
                    original_observation={
                        "swing_at":original_setup.swing_occurred_at.isoformat(),
                        "swing_price":str(original_setup.swing_price),
                        "series_from":original_setup.causal_series_started_at.isoformat(),
                        "series_until":original_setup.causal_series_ended_at.isoformat(),
                        "cisd_at":original_setup.confirmed_at.isoformat(),
                        "right_bar_available_at":local[center+1].closed_at.isoformat(),
                    }
        h_partial=any(not x.strict_complete for x in h_direct)
        m_partial=any(not x.strict_complete for x in m_direct)
        h_early=any(x.premature_close for x in h_direct)
        m_early=any(x.premature_close for x in m_direct)
        m_internal=any(x.internal_gap for x in m_direct)
        # Exact original H1 context state is frozen; this strict-H1 test
        # never regenerates states/sessions/M1. It is a sensitivity only.
        n_events=5
        zz=bisect.bisect_right(strict_times,dec)
        last5=strict_h[max(0,zz-n_events):zz]
        continuous5=(
            len(last5)==5 and all(
                (b.closed_at-a.closed_at)==timedelta(hours=1)
                for a,b in zip(last5,last5[1:])
            )
        )
        benchmark_available=len(last5)==5
        h_status=(
            "UNKNOWN_ORIGIN" if ev is None or h_missing
            else "PARTIAL_SOURCE" if h_partial
            else "COMPLETE_AND_CLOSED"
        )
        m_status=(
            "UNKNOWN_ORIGIN" if m_missing
            else "PARTIAL_SOURCE" if m_partial
            else "GAP_IN_CHAIN" if m_gap
            else "COMPLETE_AND_CLOSED"
        )
        if m_gap and m_partial:
            m_status="PARTIAL_SOURCE_AND_GAP_IN_CHAIN"
        record={
            "source_opportunity_id":sid,"symbol":row.symbol,
            "session":row.session,"operating_date":row.operating_date,
            "h1_inherited":inherited,
            "trigger_family":row.m1_trigger_family,
            "entry_at":row.m1_trigger_confirmed_at,
            "h1_event_origin_at":h_origin,
            "h1_event_origin_recovered_original_V48":ev is not None,
            "h1_direct_closure_status":h_status,
            "h1_direct_input_buckets":[x.detail() for x in h_direct],
            "h1_local_closure_has_non_strict_bucket":h_partial,
            "h1_local_closure_premature_bucket":h_early,
            "h1_strict_full_H1_same_original_event":event_strict,
            "h1_POI_complete_upstream":"UNKNOWN_ORIGIN_NO_POI_ID",
            "m15_original_structural_setup_witness":original_observation,
            "m15_original_setup_reconstructed":not m_missing,
            "m15_direct_component_status":m_status,
            "m15_direct_component_buckets":[x.detail() for x in m_direct],
            "m15_direct_components_non_strict":m_partial,
            "m15_direct_components_early_close":m_early,
            "m15_direct_components_internal_gap":m_internal,
            "m15_structural_span_timestamp_gap":m_gap,
            "m15_conditional_strict_exact_setup_match":(
                (setup_at,swing) in group["strict"]
            ),
            "M1_CISD_first_online_independent":"UNRESOLVED_GATE_C",
            "h1_last5_available_full":benchmark_available,
            "h1_last5_full_nominal_hours_consecutive":continuous5,
            "five_H1_benchmark_correct_label":"LAST_FIVE_AVAILABLE_COMPLETE_H1",
            "original_H1_M15_state_extracted_asof":False,
            "original_m15_state_until_used_retrospectively_only":True,
            "outcome_or_PnL_loaded":False,
            "gate_C_full_independent_first_online":False,
        }
        rows_out.append(record)
        c["N"]+=1
        c["H1_"+h_status]+=1
        c["M15_"+m_status]+=1
        if h_partial:
            c["H1_DIRECT_PARTIAL_SOURCE"]+=1
        if m_partial:
            c["M15_DIRECT_PARTIAL_SOURCE"]+=1
        if h_early:
            c["H1_DIRECT_PREMATURE_CLOSE"]+=1
        if m_early:
            c["M15_DIRECT_PREMATURE_CLOSE"]+=1
        if m_gap:
            c["M15_SPAN_GAP"]+=1
        if m_missing:
            c["M15_PROVENANCE_UNKNOWN"]+=1
        if ev is None or h_missing:
            c["H1_PROVENANCE_UNKNOWN"]+=1
        if event_strict:
            c["H1_EVENT_STRICT_SAME_SIGNATURE"]+=1
        if (setup_at,swing) in group["strict"]:
            c["M15_SETUP_STRICT_SAME_SIGNATURE"]+=1
        if benchmark_available:
            c["H1_BENCHMARK_5_AVAILABLE"]+=1
        if continuous5:
            c["H1_BENCHMARK_5_CONSECUTIVE"]+=1
    output.mkdir(parents=True,exist_ok=True)
    ledger=output/"scalper-issue772-c0-source-aggregate-exposure.jsonl"
    ledger.write_text(
        "".join(json.dumps(x,sort_keys=True)+"\n" for x in rows_out),
        encoding="utf-8",
    )
    for period,buckets in (("H1",h_buckets),("M15",q_buckets)):
        out=output/f"scalper-issue772-c0-{period.lower()}-deficient-buckets.jsonl"
        out.write_text(
            "".join(json.dumps(b.detail(),sort_keys=True)+"\n"
                    for b in buckets.values() if not b.strict_complete),
            encoding="utf-8",
        )
    report={
        "identity":ID,"symbol":symbol,
        "source_ids":len(rows_out),"counters":dict(sorted(c.items())),
        "bucket_census":{
            "H1":dict(sorted(h_count.items())),
            "M15":dict(sorted(q_count.items())),
        },
        "strict_shadow_H1_n":len(strict_h),
        "strict_shadow_M15_n":len(strict_q),
        "original_H1_events_n":len(original_events),
        "strict_H1_original_detector_events_n":len(strict_events),
        "legacy_original_detectors_only_for_conditional_comparisons":True,
        "POI_upstream_fully_independent":False,
        "M1_first_online_independent":False,
        "outcome_used":False,"certified":False,"production_changed":False,
    }
    (output/"scalper-issue772-c0-market-report.json").write_text(
        json.dumps(report,sort_keys=True,indent=2)+"\n",encoding="utf-8"
    )
    print("ISSUE772_C0_MARKET",json.dumps(report,sort_keys=True))
    return report


def main()->None:
    parser=argparse.ArgumentParser()
    parser.add_argument("frozen",type=Path)
    parser.add_argument("native",type=Path)
    parser.add_argument("output",type=Path)
    args=parser.parse_args()
    diagnose(frozen_root=args.frozen,native_root=args.native,output=args.output)


if __name__=="__main__":
    main()
