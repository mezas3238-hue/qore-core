"""Deep consumed-only VT-31 forensics over the tick-corrected ledger.

This module never selects a candidate. It reconstructs the frozen R8/gap05
pre-entry state and joins terminal outcomes only as labels. Post-entry outcomes
must not be used as entry features. No new holdout is opened.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import UTC
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

import vt31_r5_candidate as r5
import vt31_r8_candidate as r8
import vt31_r8_sparse_reference_forensics as sparse

from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_5_multi_index_research import (
    _day,
    _entry,
    _wall,
    load_market_evidence,
)
from qore.infrastructure.traders.vt31_silver_bullet_r2_2 import (
    _detect_raid,
    _entry_evidence,
    _session_bars,
    _structure,
)

EXPECTED_QUALITY={"r5":367,"r6":366,"r8_fresh":286}
FRICTION=Decimal("0.10")


def D(value: object) -> Decimal:
    return Decimal(str(value))


def fmt(value: Decimal | None) -> str | None:
    return None if value is None else format(value,"f")


def _selected_family(session: tuple[object,...], raid: object, confirmation_index: int, extreme_index: int, setup: object) -> tuple[str, Decimal | None, Decimal | None]:
    candidates=_entry_evidence(cast(Any,session),cast(Any,raid),confirmation_index,extreme_index)
    side=getattr(setup,"side")
    entry=cast(Decimal,getattr(setup,"entry"))
    confirmation_close=D(getattr(session[confirmation_index],"close"))
    extreme=cast(Decimal,getattr(setup,"stop"))
    target=cast(Decimal,getattr(setup,"target"))
    matches=[]
    for candidate in candidates:
        price=_entry(candidate,side,r5.BASE_VARIANT.location)
        geometry=(target < price < extreme) if side.value=="short" else (extreme < price < target)
        retracement=(price > confirmation_close) if side.value=="short" else (price < confirmation_close)
        if geometry and retracement and price==entry:
            matches.append(candidate)
    if not matches:
        return "unresolved",None,None
    families=sorted({item.family.value for item in matches})
    widths=[cast(Decimal,item.zone_upper)-cast(Decimal,item.zone_lower) for item in matches]
    width=min(widths) if widths else None
    midpoint_offset=None
    if width is not None and width>0:
        first=matches[0]
        midpoint=(cast(Decimal,first.zone_lower)+cast(Decimal,first.zone_upper))/Decimal(2)
        midpoint_offset=abs(entry-midpoint)/width
    return "+".join(families),width,midpoint_offset


def _protected_swing_like(session: tuple[object,...], confirmation_index: int, side: str) -> tuple[bool,int]:
    if confirmation_index<2:
        return False,0
    start=confirmation_index-1
    if not r5._opposing(session[start],side):
        return False,0
    while start>0 and r5._opposing(session[start-1],side):
        start-=1
    if start==0:
        return False,confirmation_index-start
    series=session[start:confirmation_index]
    swept=(
        min(D(getattr(item,"low")) for item in series)<D(getattr(session[start-1],"low"))
        if side=="long" else
        max(D(getattr(item,"high")) for item in series)>D(getattr(session[start-1],"high"))
    )
    crossed=(
        D(getattr(session[confirmation_index],"close"))>D(getattr(series[0],"open"))
        if side=="long" else
        D(getattr(session[confirmation_index],"close"))<D(getattr(series[0],"open"))
    )
    return bool(swept and crossed),len(series)


def _feature_row(day_bars: tuple[object,...], setup: object, prefix: tuple[object,...], reference: tuple[object,...], signal_index: int, prior_day: tuple[object,...] | None) -> dict[str,Any]:
    signal_at=getattr(setup,"signal_at")
    ref_high=max(D(getattr(x,"high")) for x in reference)
    ref_low=min(D(getattr(x,"low")) for x in reference)
    ref_width=ref_high-ref_low
    session=_session_bars(signal_at,cast(Any,prefix))
    raid=_detect_raid(cast(Any,session),cast(Any,sparse._sparse_reference(instrument=getattr(prefix[0],"instrument"),as_of=signal_at,bars=prefix)))
    if raid is None or getattr(raid,"high_taken") and getattr(raid,"low_taken"):
        raise AssertionError("selected setup lost raid")
    structure=_structure(cast(Any,session),cast(Any,raid))
    if structure is None:
        raise AssertionError("selected setup lost structure")
    confirmation_index,extreme_index,extreme,anchor=structure
    confirmation=session[confirmation_index]
    raid_bar=session[raid.index]
    side=getattr(setup,"side").value
    entry=cast(Decimal,getattr(setup,"entry"))
    risk=cast(Decimal,getattr(setup,"risk"))
    source_target=cast(Decimal,getattr(setup,"target"))
    raid_high=D(getattr(raid_bar,"high")); raid_low=D(getattr(raid_bar,"low")); raid_open=D(getattr(raid_bar,"open")); raid_close=D(getattr(raid_bar,"close"))
    raid_span=raid_high-raid_low
    c_open=D(getattr(confirmation,"open")); c_close=D(getattr(confirmation,"close")); c_high=D(getattr(confirmation,"high")); c_low=D(getattr(confirmation,"low")); c_span=c_high-c_low
    if ref_width<=0 or raid_span<=0 or c_span<=0 or risk<=0:
        raise AssertionError("non-positive geometry")
    if side=="long":
        raid_depth=max(Decimal(0),ref_low-raid_low)/ref_width
        final_depth=max(Decimal(0),ref_low-D(extreme))/ref_width
        entry_loc=(entry-ref_low)/ref_width
    else:
        raid_depth=max(Decimal(0),raid_high-ref_high)/ref_width
        final_depth=max(Decimal(0),D(extreme)-ref_high)/ref_width
        entry_loc=(ref_high-entry)/ref_width
    family,zone_width,zone_mid_offset=_selected_family(session,raid,confirmation_index,extreme_index,setup)
    ps_like,ps_series_len=_protected_swing_like(session,confirmation_index,side)
    local=signal_at.astimezone(r5.NY)
    signal_minute=local.hour*60+local.minute-10*60
    target_distance=abs(source_target-entry)
    source_target_r=target_distance/risk
    displacement_beyond_anchor=abs(c_close-D(anchor))/ref_width
    previous={
        "prior_day_bar_count":0,"prior_day_direction":"unavailable","prior_day_range":None,"prior_day_close_vs_open":None,"side_aligned_with_prior_day":None
    }
    if prior_day:
        po=D(getattr(prior_day[0],"open")); pc=D(getattr(prior_day[-1],"close")); ph=max(D(getattr(x,"high")) for x in prior_day); pl=min(D(getattr(x,"low")) for x in prior_day)
        direction="bullish" if pc>po else "bearish" if pc<po else "flat"
        previous={
            "prior_day_bar_count":len(prior_day),"prior_day_direction":direction,"prior_day_range":fmt(ph-pl),"prior_day_close_vs_open":fmt(pc-po),
            "side_aligned_with_prior_day": (direction=="bullish" and side=="long") or (direction=="bearish" and side=="short") if direction!="flat" else None,
        }
    row={
        "signal_at":signal_at.astimezone(UTC).isoformat(),"signal_minute":signal_minute,"side":side,
        "entry_family":family,"reference_range":fmt(ref_width),"raid_side":side,
        "raid_body_fraction":fmt(abs(raid_close-raid_open)/raid_span),"raid_wick_fraction":fmt(Decimal(1)-abs(raid_close-raid_open)/raid_span),
        "raid_depth_to_reference":fmt(raid_depth),"final_extreme_depth_to_reference":fmt(final_depth),
        "raid_to_final_extreme_latency_m1":extreme_index-raid.index,"raid_to_confirmation_latency_m1":confirmation_index-raid.index,
        "confirmation_body_fraction":fmt(abs(c_close-c_open)/c_span),"confirmation_range_to_reference":fmt(c_span/ref_width),
        "displacement_beyond_anchor_to_reference":fmt(displacement_beyond_anchor),"risk_to_reference":fmt(risk/ref_width),
        "entry_to_stop":fmt(risk),"entry_to_opposing_liquidity":fmt(target_distance),"opposing_liquidity_r":fmt(source_target_r),
        "entry_location_to_reference":fmt(entry_loc),"selected_zone_width":fmt(zone_width),"entry_offset_from_zone_mid_widths":fmt(zone_mid_offset),
        "protected_swing_like_at_signal":ps_like,"protected_swing_opposing_series_length":ps_series_len,
        "qore_initial_stop_anchor":"raid-final-extreme","source_objective":"opposite-09-range-boundary",
        "signal_global_index":signal_index,
    }
    row.update(previous)
    return row


def reconstruct(partition: str, market: str, path: Path) -> list[dict[str,Any]]:
    series,_,_,_,_,provider=load_market_evidence(path)
    by_day:dict[object,list[object]]=defaultdict(list)
    for bar in series:
        by_day[_day(bar.opened_at)].append(bar)
    days=sorted(by_day)
    previous_by_day={day:(tuple(by_day[days[i-1]]) if i>0 else None) for i,day in enumerate(days)}
    rows=[]
    for local_day in days:
        day_bars=tuple(by_day[local_day]); reference=sparse._reference_bars(day_bars)
        indexed_session=tuple((i,b) for i,b in enumerate(day_bars) if (10,0,0)<=_wall(getattr(b,"opened_at"))<(11,0,0))
        if len(indexed_session)!=60 or not reference or not sparse._policy_accepts(reference,"gap05"):
            continue
        ref_high=max(D(getattr(x,"high")) for x in reference); ref_low=min(D(getattr(x,"low")) for x in reference); ref_width=ref_high-ref_low
        if ref_width<=0: continue
        prefix=list(reference); selected=None; selected_index=None
        for global_index,bar in indexed_session:
            prefix.append(bar)
            candidate,_=sparse._evaluate_sparse(instrument=getattr(bar,"instrument"),as_of=getattr(bar,"closed_at"),bars=tuple(prefix),variant=r5.BASE_VARIANT)
            if candidate is None: continue
            if not sparse._quality_sparse(tuple(prefix),candidate,ref_width):
                break
            selected=candidate; selected_index=global_index; break
        if selected is None or selected_index is None: continue
        row=_feature_row(day_bars,selected,tuple(prefix),reference,selected_index,previous_by_day[local_day])
        row.update({"partition":partition,"market":market,"ny_date":str(local_day),"provider":provider})
        rows.append(row)
    return rows


def _metrics(rows:list[dict[str,Any]]) -> dict[str,Any]:
    vals=[D(r["terminal_r"])-FRICTION for r in rows]
    wins=[v for v in vals if v>0]; losses=[v for v in vals if v<0]
    total=sum(vals,Decimal(0)); n=len(vals)
    pf=sum(wins,Decimal(0))/abs(sum(losses,Decimal(0))) if losses else None
    return {"n":n,"total_stressed_r":fmt(total),"mean_stressed_r":fmt(total/Decimal(n) if n else None),"profit_factor_stressed":fmt(pf),"wins":len(wins),"losses":len(losses)}


def _bucket(value: Decimal, edges: tuple[Decimal,...]) -> str:
    prev=None
    for edge in edges:
        if value<=edge:
            return f"<= {edge}" if prev is None else f"({prev}, {edge}]"
        prev=edge
    return f"> {edges[-1]}"


def _diagnostic_groups(rows:list[dict[str,Any]]) -> dict[str,Any]:
    specs={
        "entry_family":lambda r:str(r["entry_family"]),
        "market":lambda r:str(r["market"]),"side":lambda r:str(r["side"]),
        "protected_swing_like_at_signal":lambda r:str(r["protected_swing_like_at_signal"]),
        "signal_minute_bucket":lambda r:_bucket(D(r["signal_minute"]),(Decimal(5),Decimal(10),Decimal(15),Decimal(20))),
        "risk_to_reference_bucket":lambda r:_bucket(D(r["risk_to_reference"]),(Decimal("0.10"),Decimal("0.125"),Decimal("0.15"),Decimal("0.175"))),
        "raid_body_bucket":lambda r:_bucket(D(r["raid_body_fraction"]),(Decimal("0.45"),Decimal("0.55"),Decimal("0.70"))),
        "confirmation_body_bucket":lambda r:_bucket(D(r["confirmation_body_fraction"]),(Decimal("0.60"),Decimal("0.70"),Decimal("0.85"))),
        "raid_to_extreme_latency":lambda r:str(r["raid_to_final_extreme_latency_m1"]),
        "opposing_liquidity_r_bucket":lambda r:_bucket(D(r["opposing_liquidity_r"]),(Decimal("1"),Decimal("1.5"),Decimal("2"),Decimal("3"))),
        "prior_day_alignment":lambda r:str(r["side_aligned_with_prior_day"]),
    }
    out={}
    for name,keyfn in specs.items():
        groups:dict[str,list[dict[str,Any]]]=defaultdict(list)
        for row in rows: groups[keyfn(row)].append(row)
        out[name]={k:_metrics(v) for k,v in sorted(groups.items())}
    return out


def _streaks(rows:list[dict[str,Any]]) -> list[dict[str,Any]]:
    ordered=sorted(rows,key=lambda r:(r["signal_at"],r["market"],r["root_id"]))
    streaks=[]; current=[]
    def flush() -> None:
        nonlocal current
        if current:
            streaks.append({
                "length":len(current),"start":current[0]["signal_at"],"end":current[-1]["signal_at"],
                "markets":dict(Counter(str(r["market"]) for r in current)),"sides":dict(Counter(str(r["side"]) for r in current)),
                "entry_families":dict(Counter(str(r["entry_family"]) for r in current)),
                "protected_swing_like":dict(Counter(str(r["protected_swing_like_at_signal"]) for r in current)),
                "mean_risk_to_reference":fmt(sum((D(r["risk_to_reference"]) for r in current),Decimal(0))/Decimal(len(current))),
                "mean_confirmation_body_fraction":fmt(sum((D(r["confirmation_body_fraction"]) for r in current),Decimal(0))/Decimal(len(current))),
                "mean_raid_body_fraction":fmt(sum((D(r["raid_body_fraction"]) for r in current),Decimal(0))/Decimal(len(current))),
                "mean_opposing_liquidity_r":fmt(sum((D(r["opposing_liquidity_r"]) for r in current),Decimal(0))/Decimal(len(current))),
                "rows":[r["root_id"] for r in current],
            }); current=[]
    for row in ordered:
        if D(row["terminal_r"])<0: current.append(row)
        else: flush()
    flush(); streaks.sort(key=lambda s:(-int(s["length"]),str(s["start"])))
    return streaks


def main() -> None:
    ap=argparse.ArgumentParser(); ap.add_argument("--ledger",required=True,type=Path); ap.add_argument("--output",required=True,type=Path)
    for p in ("r5","r6","r8_fresh"):
        for m in ("nas100","sp500","us30"): ap.add_argument(f"--{p.replace('_','-')}-{m}",required=True,type=Path)
    a=ap.parse_args(); ledger=json.loads(a.ledger.read_text())
    if ledger.get("research_only") is not True or ledger.get("opens_new_holdout") is not False: raise ValueError("ledger governance guard failed")
    all_features=[]
    for p in ("r5","r6","r8_fresh"):
        part=[]
        for m in ("NAS100","SP500","US30"):
            path=getattr(a,f"{p}_{m.lower()}")
            part.extend(reconstruct(p,m,path))
        if len(part)!=EXPECTED_QUALITY[p]: raise AssertionError(f"{p} quality reconstruction {len(part)} != {EXPECTED_QUALITY[p]}")
        all_features.extend(part)
    feature_by_key={}
    for r in all_features:
        key=(r["partition"],r["market"],r["ny_date"],r["side"])
        if key in feature_by_key: raise AssertionError(f"duplicate setup key {key}")
        feature_by_key[key]=r
    terminal=[]
    for trade in ledger["trades"]:
        key=(trade["partition"],trade["market"],trade["ny_date"],trade["side"])
        f=feature_by_key.get(key)
        if f is None: raise AssertionError(f"terminal trade missing features {key}")
        row=dict(f); row.update({"root_id":trade["root_id"],"terminal_r":str(trade["terminal_r"]),"terminal_status":trade["terminal_status"],"resolution_source":trade["resolution_source"]})
        terminal.append(row)
    terminal.sort(key=lambda r:(r["signal_at"],r["market"],r["root_id"]))
    streaks=_streaks(terminal)
    source_target={
        "below_2r":sum(D(r["opposing_liquidity_r"])<Decimal(2) for r in terminal),
        "at_2r":sum(D(r["opposing_liquidity_r"])==Decimal(2) for r in terminal),
        "above_2r":sum(D(r["opposing_liquidity_r"])>Decimal(2) for r in terminal),
        "median_opposing_liquidity_r":fmt(sorted(D(r["opposing_liquidity_r"]) for r in terminal)[len(terminal)//2]) if terminal else None,
    }
    payload={
        "schema":"qore.vt31.tick_corrected.deep_forensics.v1","research_only":True,"opens_new_holdout":False,"candidate_status":"NO_R9_NOT_CERTIFIED",
        "selection_prohibited":True,"feature_timing":"pre-entry-only","label_policy":"terminal_r is diagnostic label only",
        "reconstructed_quality_pass_count":len(all_features),"terminal_count":len(terminal),"aggregate":_metrics(terminal),
        "source_target_structure":source_target,"diagnostic_groups":_diagnostic_groups(terminal),"losing_streaks":streaks,
        "max_losing_streak":max((int(s["length"]) for s in streaks),default=0),"top_losing_streaks":streaks[:20],"rows":terminal,
    }
    a.output.write_text(json.dumps(payload,sort_keys=True,indent=2)+"\n")
    print(json.dumps({"terminal_count":len(terminal),"max_losing_streak":payload["max_losing_streak"],"source_target_structure":source_target},sort_keys=True))

if __name__=="__main__": main()
