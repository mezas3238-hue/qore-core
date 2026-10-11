"""A2 audit 13 H1 C2/C3: source-label event/POI provenance on native M1.

This checks QORE's original H1 detector mechanically, not equivalence to every
valid TTrades point of interest (notably the opposing-candle alternative).
A 45/60 partial H1 is NEVER silently called an exact completed source hour.
No trades or source admissions change.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import timedelta
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    iter_cibo_m1,
)
from qore.infrastructure.trader_lab.capitalizer_generic_scalp_census_v48 import (
    V48AggregatedBar,
    V48H1BiasEvent,
    _aggregate,
    _build_h1_bias_events,
    _poi_direction_compatible,
)
from qore.infrastructure.trader_lab.capitalizer_high_frequency_capacity_census_v49 import (
    DEV_WINDOW_END,
    DEV_WINDOW_START,
    V49Opportunity,
)
from qore.infrastructure.trader_lab.capitalizer_scalper_v49_v50_g_waterfall_v1 import (
    _jsonl,
    source_id,
)
from qore.infrastructure.trader_lab.capitalizer_source_observation_detectors_v2 import (
    CapitalizerSourceDirection,
    detect_candle2_reversal_closure,
    detect_candle3_confirmation,
)
from qore.infrastructure.trader_lab.capitalizer_source_poi_v2 import (
    CapitalizerSourcePOI,
    bar_interacts_with_poi,
    detect_external_liquidity_swing,
    detect_fair_value_gap,
)

IDENTITY="QORE_SCALPER_A2_THIRTEENTH_C2_POI_NATIVE_PROVENANCE_V1"


def choose_origin(
    events: tuple[V48H1BiasEvent,...], source: V49Opportunity,
) -> V48H1BiasEvent | None:
    inherited=source.h1_state_basis.startswith("SESSION_INHERITED:")
    key=source.h1_state_basis.removeprefix("SESSION_INHERITED:")
    direction=CapitalizerSourceDirection(source.h1_state_direction)
    from_at=source.h1_state_from
    if inherited:
        prior=[e for e in events if e.confirmed_at.isoformat()<from_at]
        candidate=prior[-1] if prior else None
    else:
        at=[
            e for e in events
            if e.confirmed_at.isoformat()==from_at
            and e.direction is direction
            and f"{e.closure_kind}:{e.poi_kind}"==key
        ]
        candidate=at[-1] if at else None
    if candidate is None:
        return None
    if (candidate.direction is not direction
            or f"{candidate.closure_kind}:{candidate.poi_kind}"!=key):
        return None
    return candidate


def make_pois(
    h1: tuple[V48AggregatedBar,...],
) -> tuple[tuple[int,CapitalizerSourcePOI],...]:
    """POI formed at the CLOSE of the third H1 bar, never earlier."""

    found: list[tuple[int,CapitalizerSourcePOI]]=[]
    for center in range(1,len(h1)-1):
        left,mid,right=h1[center-1:center+2]
        fvg=detect_fair_value_gap(
            candle1=left.source,candle2=mid.source,candle3=right.source
        )
        swing=detect_external_liquidity_swing(
            left=left.source,center=mid.source,right=right.source
        )
        if fvg is not None:
            found.append((center+1,fvg))
        if swing is not None:
            found.append((center+1,swing))
    return tuple(found)


def poi_witness(
    h1:tuple[V48AggregatedBar,...],
    pois:tuple[tuple[int,CapitalizerSourcePOI],...],
    origin:V48H1BiasEvent,
) -> dict[str,Any]:
    index=next((i for i,h in enumerate(h1)
                if h.closed_at==origin.confirmed_at),None)
    if index is None or index<2:
        return {"source_event_reconstructed":False}
    c2_event=origin.closure_kind=="CANDLE2_REVERSAL"
    event_bar=h1[index] if c2_event else h1[index-1]
    prior=h1[index-1] if c2_event else h1[index-2]
    cutoff=index-1 if c2_event else index-2
    compatible=[
        (formed,poi) for formed,poi in pois
        if formed<=cutoff
        and poi.kind.value==origin.poi_kind
        and _poi_direction_compatible(poi,origin.direction)
        and bar_interacts_with_poi(bar=event_bar.source,poi=poi)
    ]
    if c2_event:
        geometry=detect_candle2_reversal_closure(
            previous=prior.source,candle2=event_bar.source,
            point_of_interest_present=True,
        )
    else:
        geometry=detect_candle3_confirmation(
            candle2=h1[index-1].source,candle3=h1[index].source,
            point_of_interest_present=True,candle2_reversal_already_confirmed=False,
        )
    plausible=(geometry is not None
               and geometry.direction is origin.direction
               and geometry.source_rule_satisfied)
    exact_event=h1[index].minute_count==60
    exact_previous=h1[index-1].minute_count==60
    return {
        "source_event_reconstructed":True,
        "source_event_kind":origin.closure_kind,
        "poi_kind":origin.poi_kind,
        "poi_formed_prior_to_source_event":bool(compatible),
        "matched_poi_count":len(compatible),
        "poi_formed_at":h1[compatible[0][0]].closed_at.isoformat()
            if compatible else None,
        "poi_interaction_candle_closed_at":event_bar.closed_at.isoformat(),
        "poi_from_same_H1_timeframe_not_independently_HTF_proven":True,
        "closure_geometry_reconstructed":plausible,
        "event_h1_exact_60":exact_event,
        "prior_h1_exact_60":exact_previous,
        "closure_geometrical_60_60":exact_event and exact_previous,
        "source_QORE_allows_45_of_60_partial_H1":True,
        "independent_author_fidelity_not_claimed":True,
    }


def market(
    original_root:Path,native_root:Path,
) ->tuple[dict[str,Any],tuple[dict[str,Any],...]]:
    files=sorted(original_root.rglob(
        "capitalizer-*-v49-hf-capacity-opportunities.jsonl"
    ))
    if len(files)!=1:
        raise ValueError("one frozen V49 source ledger required")
    sources=tuple(V49Opportunity(**x) for x in _jsonl(files[0]))
    if not sources:
        raise ValueError("no original IDs")
    symbol=sources[0].symbol
    if any(x.symbol!=symbol for x in sources):
        raise ValueError("mixed native source market")
    native=tuple(
        b for b in iter_cibo_m1(native_root)
        if DEV_WINDOW_START-timedelta(days=15)<=b.opened_at<DEV_WINDOW_END
    )
    if not native or any(x.symbol!=symbol for x in native):
        raise ValueError("missing or contradictory native M1")
    h1=_aggregate(native,minutes=60)
    events=_build_h1_bias_events(h1)
    pois=make_pois(h1)
    cache:dict[tuple[str,str,str,str],dict[str,Any]]={}
    rows=[]
    seen:set[str]=set()
    for source in sources:
        sid=source_id(source)
        if sid in seen:
            raise ValueError("duplicate immutable V49 identity")
        seen.add(sid)
        identity=(
            source.h1_state_from,source.h1_state_basis,
            source.h1_state_direction,source.session,
        )
        if identity not in cache:
            found=choose_origin(events,source)
            witness=(
                poi_witness(h1,pois,found)
                if found is not None else {"source_event_reconstructed":False}
            )
            witness["origin_closed_at"]=(
                found.confirmed_at.isoformat() if found else None
            )
            cache[identity]=witness
        record=cache[identity]
        rows.append({
            "source_opportunity_id":sid,"symbol":symbol,
            "original_basis":source.h1_state_basis,
            "session_inherited":source.h1_state_basis.startswith("SESSION_INHERITED:"),
            "source_H1_from":source.h1_state_from,
            **record,
            "changes_original_trade":False,
        })
    counts=Counter()
    for x in rows:
        counts["SOURCE_MATCH" if x["source_event_reconstructed"]
               else "SOURCE_UNMATCHED"]+=1
        if x.get("poi_formed_prior_to_source_event"):
            counts["INTERNAL_POI_PRIOR_AND_INTERACTED"]+=1
        if x.get("closure_geometry_reconstructed"):
            counts["INTERNAL_CLOSURE_GEOMETRY"]+=1
        if x.get("closure_geometrical_60_60"):
            counts["EXACT_NATIVE_H1_60_60"]+=1
    return {
        "identity":IDENTITY,"symbol":symbol,"sources":len(rows),
        "counts":dict(sorted(counts.items())),
        "h1_aggregate_minimum_minutes_per_hour":45,
        "independent_author_POI_timeframe_attested":False,
        "changed_admissions":0,"live":False,
    },tuple(rows)


def aggregate(root:Path)->dict[str,Any]:
    reports=[json.loads(p.read_text(encoding="utf-8"))
             for p in sorted(root.rglob("scalper-audit13-h1poi-market.json"))]
    if len(reports)!=9 or len({x["symbol"] for x in reports})!=9:
        raise ValueError("requires all 9 markets")
    rows=[x for p in sorted(root.rglob("scalper-audit13-h1poi-ids.jsonl"))
          for x in _jsonl(p)]
    if len(rows)!=2876 or len({x["source_opportunity_id"] for x in rows})!=2876:
        raise ValueError("source population not conserved")
    counts=Counter()
    for x in rows:
        key="C3" if "CANDLE3" in x["original_basis"] else "C2"
        counts[key]+=1
        if x["source_event_reconstructed"]:
            counts[key+"_RECONSTRUCTED"]+=1
        if x.get("poi_formed_prior_to_source_event"):
            counts[key+"_POI_INTERACTED"]+=1
        if x.get("closure_geometry_reconstructed"):
            counts[key+"_CLOSURE_GEOMETRY"]+=1
        if x.get("closure_geometrical_60_60"):
            counts[key+"_FULL_H1"]+=1
        if x["session_inherited"]:
            counts["SESSION_INHERITED"]+=1
    if counts["C2"]!=2638 or counts["C3"]!=238:
        raise ValueError("frozen H1 source labels changed")
    return {
        "identity":IDENTITY,"markets":9,"sources":2876,
        "counts":dict(sorted(counts.items())),
        "source_internal_POI_not_external_author_certification":True,
        "partial_H1_can_be_event_witness":True,
        "no_admission_changes":True,"paper_pf":None,"paper_dd":None,
        "status":"UNRESOLVED_AUTHOR_H1_POI",
    }


def main()->None:
    p=argparse.ArgumentParser()
    sub=p.add_subparsers(dest="mode",required=True)
    m=sub.add_parser("market")
    m.add_argument("original",type=Path)
    m.add_argument("native",type=Path)
    m.add_argument("output",type=Path)
    a=sub.add_parser("matrix")
    a.add_argument("inputs",type=Path)
    a.add_argument("output",type=Path)
    args=p.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    if args.mode=="market":
        report,rows=market(args.original,args.native)
        (args.output/"scalper-audit13-h1poi-market.json").write_text(
            json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8"
        )
        with (args.output/"scalper-audit13-h1poi-ids.jsonl").open(
            "w",encoding="utf-8"
        ) as f:
            for x in rows:
                f.write(json.dumps(x,sort_keys=True)+"\n")
    else:
        report=aggregate(args.inputs)
        (args.output/"scalper-audit13-h1poi-nine-market.json").write_text(
            json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8"
        )
    print(json.dumps(report,sort_keys=True))


if __name__=="__main__":
    main()
