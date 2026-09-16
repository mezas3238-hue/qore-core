"""Freeze the four consumed gap05 VT-31 later same-M1 stop/target ambiguities.

These rows were already identified by immutable fill-attrition forensics but were
outside both the 437 fill-bar ambiguity manifest and the 339 resolved parity
controls. The reconstruction preserves the same setup selection and protected
swing mechanics, records the exact ambiguous bar and stop in force before that
bar, and opens no fresh evidence.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from datetime import UTC, date
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

import vt31_r5_candidate as r5
import vt31_r8_fill_attrition_forensics as attr
import vt31_r8_sparse_reference_forensics as sparse
from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_5_multi_index_research import _day, _wall, load_market_evidence

MARKETS=("NAS100","SP500","US30")
PARTITIONS=("r5","r6","r8_fresh")
EXPECTED={"r5":{"NAS100":0,"SP500":1,"US30":0},"r6":{"NAS100":1,"SP500":0,"US30":1},"r8_fresh":{"NAS100":0,"SP500":1,"US30":0}}
POLICY="gap05"


def _d(value: float) -> Decimal:
    return Decimal(str(value))


def _ms(value: object) -> int:
    return int(getattr(value,"astimezone")(UTC).timestamp()*1000)


def _locate(day_bars: tuple[object,...], signal_index: int, setup: object) -> tuple[int,Decimal,Decimal,Decimal]:
    side=getattr(setup,"side").value
    entry=cast(Decimal,getattr(setup,"entry"))
    initial_stop=cast(Decimal,getattr(setup,"stop"))
    risk=abs(entry-initial_stop)
    if risk<=0:
        raise ValueError("invalid frozen risk")
    target=entry+r5.TARGET_R*risk if side=="long" else entry-r5.TARGET_R*risk
    fill_index=None
    for index in range(signal_index+1,len(day_bars)):
        bar=day_bars[index]
        if _wall(getattr(bar,"opened_at")) >= (11,0,0):
            break
        if index>signal_index+1 and getattr(bar,"opened_at")!=getattr(day_bars[index-1],"closed_at"):
            raise ValueError("unexpected pending data gap in later-ambiguity source")
        if r5._touch(bar,entry):
            fill_index=index
            break
    if fill_index is None:
        raise ValueError("later ambiguity must have a fill")
    first=day_bars[fill_index]
    first_stop=_d(cast(float,getattr(first,"low")))<=initial_stop if side=="long" else _d(cast(float,getattr(first,"high")))>=initial_stop
    first_target=_d(cast(float,getattr(first,"high")))>=target if side=="long" else _d(cast(float,getattr(first,"low")))<=target
    if first_stop or first_target:
        raise ValueError("later ambiguity cannot be a fill-bar ambiguity")
    current_stop=initial_stop
    previous=first
    for index in range(fill_index+1,len(day_bars)):
        bar=day_bars[index]
        local=getattr(bar,"opened_at").astimezone(r5.NY)
        if local.hour*60+local.minute>=16*60:
            break
        if getattr(bar,"opened_at")!=getattr(previous,"closed_at"):
            raise ValueError("unexpected post-fill data gap")
        previous=bar
        low=_d(cast(float,getattr(bar,"low")))
        high=_d(cast(float,getattr(bar,"high")))
        hit_stop=low<=current_stop if side=="long" else high>=current_stop
        hit_target=high>=target if side=="long" else low<=target
        if hit_stop and hit_target:
            return index,current_stop,target,risk
        if hit_stop or hit_target:
            raise ValueError("terminal event occurred before claimed later ambiguity")
        current_stop=r5._new_protected_stop(day_bars,index,side,current_stop,_d(cast(float,getattr(bar,"close"))))
    raise ValueError("failed to locate later same-bar ambiguity")


def _run_market(path: Path, partition: str, market: str) -> list[dict[str,Any]]:
    series,_,_,_,_,provider=load_market_evidence(path)
    by_day:dict[date,list[object]]=defaultdict(list)
    for bar in series:
        by_day[_day(bar.opened_at)].append(bar)
    rows=[]
    for local_day in sorted(by_day):
        day_bars=tuple(by_day[local_day])
        reference=sparse._reference_bars(day_bars)
        indexed_session=tuple((index,bar) for index,bar in enumerate(day_bars) if (10,0,0)<=_wall(getattr(bar,"opened_at"))<(11,0,0))
        if len(indexed_session)!=60 or not reference or not sparse._policy_accepts(reference,POLICY):
            continue
        ref_high=max(_d(cast(float,getattr(item,"high"))) for item in reference)
        ref_low=min(_d(cast(float,getattr(item,"low"))) for item in reference)
        ref_width=ref_high-ref_low
        if ref_width<=0:
            continue
        prefix=list(reference)
        selected=None
        selected_index=None
        for global_index,bar in indexed_session:
            prefix.append(bar)
            candidate,_=sparse._evaluate_sparse(instrument=getattr(bar,"instrument"),as_of=getattr(bar,"closed_at"),bars=tuple(prefix),variant=r5.BASE_VARIANT)
            if candidate is None:
                continue
            if not sparse._quality_sparse(tuple(prefix),candidate,ref_width):
                break
            selected=candidate
            selected_index=global_index
            break
        if selected is None or selected_index is None:
            continue
        _,reason=attr._diagnose_simulation(day_bars,selected_index,selected)
        if reason!="later-same-bar-stop-target-ambiguous":
            continue
        ambiguous_index,current_stop,target,risk=_locate(day_bars,selected_index,selected)
        side=getattr(selected,"side").value
        entry=cast(Decimal,getattr(selected,"entry"))
        initial_stop=cast(Decimal,getattr(selected,"stop"))
        signal=day_bars[selected_index]
        ambiguous=day_bars[ambiguous_index]
        root_material={
            "partition":partition,"market":market,"ny_date":local_day.isoformat(),"side":side,
            "signal_opened_at":getattr(signal,"opened_at").astimezone(UTC).isoformat(),
            "entry":format(entry,"f"),"initial_stop":format(initial_stop,"f"),"fixed_2r_target":format(target,"f"),
        }
        root_id=hashlib.sha256(json.dumps(root_material,sort_keys=True,separators=(",",":")).encode()).hexdigest()[:24]
        row={
            "root_id":root_id,
            "partition":partition,"market":market,"provider":provider,"ny_date":local_day.isoformat(),"side":side,
            "signal_opened_at":root_material["signal_opened_at"],
            "entry":format(entry,"f"),"initial_stop":format(initial_stop,"f"),"current_protected_stop":format(current_stop,"f"),
            "fixed_2r_target":format(target,"f"),"initial_risk":format(risk,"f"),
            "tick_window_open_ms":_ms(getattr(ambiguous,"opened_at")),"tick_window_close_ms":_ms(getattr(ambiguous,"closed_at"))-1,
            "m1_low":format(_d(cast(float,getattr(ambiguous,"low"))),"f"),"m1_high":format(_d(cast(float,getattr(ambiguous,"high"))),"f"),
            "classification":"later-same-bar-stop-target-ambiguous",
        }
        material=json.dumps(row,sort_keys=True,separators=(",",":"))
        row["window_id"]=hashlib.sha256(material.encode()).hexdigest()[:24]
        rows.append(row)
    return rows


def main() -> None:
    parser=argparse.ArgumentParser()
    for partition in PARTITIONS:
        for market in MARKETS:
            parser.add_argument(f"--{partition.replace('_','-')}-{market.lower()}",required=True,type=Path)
    parser.add_argument("--output",required=True,type=Path)
    args=parser.parse_args()
    rows=[]
    counts={}
    for partition in PARTITIONS:
        block={}
        for market in MARKETS:
            path=getattr(args,f"{partition}_{market.lower()}")
            market_rows=_run_market(path,partition,market)
            observed=len(market_rows)
            if observed!=EXPECTED[partition][market]:
                raise AssertionError(f"{partition}/{market} later ambiguity changed: {observed} != {EXPECTED[partition][market]}")
            block[market]=observed
            rows.extend(market_rows)
        counts[partition]={"total":sum(block.values()),**block}
    if len(rows)!=4 or len({row['root_id'] for row in rows})!=4 or len({row['window_id'] for row in rows})!=4:
        raise AssertionError("expected four unique original later ambiguities")
    rows.sort(key=lambda row:(row['partition'],row['tick_window_open_ms'],row['market']))
    payload={"schema":"qore.vt31.consumed_original_later_same_bar_tick_manifest.v1","research_only":True,"opens_new_holdout":False,"candidate_status":"NO_R9_NOT_CERTIFIED","reference_policy":POLICY,"counts":counts,"windows":rows}
    canonical=json.dumps(payload,sort_keys=True,separators=(",",":"))
    payload["sha256"]=hashlib.sha256(canonical.encode()).hexdigest()
    args.output.write_text(json.dumps(payload,sort_keys=True,indent=2)+"\n")
    print(json.dumps({"count":len(rows),"counts":counts},sort_keys=True))


if __name__=="__main__":
    main()
