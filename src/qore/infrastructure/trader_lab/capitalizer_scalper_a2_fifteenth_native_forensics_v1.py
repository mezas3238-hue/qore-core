"""Audit15: rerun M1 MFE/MAE, same-state H1 random null, and CISD stage chain.

All nine-market observations are strictly anchored to Audit14 GROSS economic
source-ID MAX3 (1997), and V49 control MAX3 (2020). Future bar highs,
lows and forward direction are diagnostic labels only, never admissions.
"""

from __future__ import annotations

import argparse
import bisect
import json
import random
from collections import Counter, defaultdict
from dataclasses import asdict, replace
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    iter_cibo_m1,
)
from qore.infrastructure.trader_lab.capitalizer_contract import CapitalizerSession
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
from qore.infrastructure.trader_lab.capitalizer_scalper_a2_fourteenth_winner_reconciliation_v1 import (
    candidate_key,
    original_key,
    source_key,
)
from qore.infrastructure.trader_lab.capitalizer_scalper_h1_direction_random_baseline_v1 import (
    DRAWS,
    MODES,
    _future_label,
    _runs,
    _seed,
    _third,
    eligible_h1_state_times,
)
from qore.infrastructure.trader_lab.capitalizer_scalper_m1_stage_chain_forensic_v1 import (
    reconstruct_source_chain,
)
from qore.infrastructure.trader_lab.capitalizer_scalper_mfe_mae_v1 import (
    ExcursionRow,
    _summary as excursion_summary,
    observe_market_excursions,
)
from qore.infrastructure.trader_lab.capitalizer_scalper_v49_v50_g_waterfall_v1 import (
    _jsonl,
    source_id,
)
from qore.infrastructure.trader_lab.capitalizer_session_clock import (
    _operating_date,
    capitalizer_session_at,
)
from qore.infrastructure.trader_lab.capitalizer_v49_development_economics import (
    V49EconomicTrade,
)

IDENTITY="QORE_SCALPER_A2_FIFTEENTH_SELECTED_MAX3_NATIVE_M1_FORENSICS_V1"
HORIZONS=(15,30,60)


def market(
    selection_root:Path,source_root:Path,economic_root:Path,native_root:Path,
)->tuple[dict[str,Any],tuple[dict[str,Any],...]]:
    selections=tuple(selection_root.rglob(
        "scalper-a2-audit15-residual-anatomy-nine-market.json"
    ))
    sources_files=tuple(source_root.rglob(
        "capitalizer-*-v49-hf-capacity-opportunities.jsonl"
    ))
    origin_files=tuple(source_root.rglob(
        "capitalizer-*-v49-development-economics-trades.jsonl"
    ))
    alt_files=tuple(economic_root.rglob("scalper-audit14-candidates.jsonl"))
    id_files=tuple(economic_root.rglob("scalper-audit14-ids.jsonl"))
    if any(len(files)!=1 for files in (
        selections,sources_files,origin_files,alt_files,id_files
    )):
        raise ValueError("requires exactly one frozen market and nine-market selection")
    selections_json=json.loads(selections[0].read_text(encoding="utf-8"))
    original_ids=set(selections_json["baseline_max3_source_ids"])
    alternative_ids=set(selections_json["online_max3_source_ids"])
    if len(original_ids)!=2020 or len(alternative_ids)!=1997:
        raise ValueError("selection source IDs not source-audited MAX3")
    sources=tuple(V49Opportunity(**x) for x in _jsonl(sources_files[0]))
    originals=tuple(V49EconomicTrade(**x) for x in _jsonl(origin_files[0]))
    alts=tuple(V49EconomicTrade(**x) for x in _jsonl(alt_files[0]))
    ids=tuple(_jsonl(id_files[0]))
    if not sources or len(sources)!=len(originals) or len(ids)!=len(sources):
        raise ValueError("original market population not reproduced")
    symbol=sources[0].symbol
    if any(x.symbol!=symbol for x in sources):
        raise ValueError("mixed market source")
    source_by_id={source_id(x):x for x in sources}
    row_by_old={source_key(x):x for x in ids}
    row_by_alt={candidate_key(x):x for x in ids if x["status"]=="ELIGIBLE"}
    if len(source_by_id)!=len(sources) or len(row_by_old)!=len(sources):
        raise ValueError("source IDs / reference economic source not unique")
    old_selected=[
        (row_by_old[original_key(t)]["source_opportunity_id"],t)
        for t in originals
        if row_by_old[original_key(t)]["source_opportunity_id"] in original_ids
    ]
    alt_selected=[
        (row_by_alt[original_key(t)]["source_opportunity_id"],t)
        for t in alts
        if row_by_alt[original_key(t)]["source_opportunity_id"] in alternative_ids
    ]
    if (len({id for id,_ in old_selected})!=len(old_selected)
            or len({id for id,_ in alt_selected})!=len(alt_selected)):
        raise ValueError("selected source ID duplicates")
    native=tuple(x for x in iter_cibo_m1(native_root)
                 if DEV_WINDOW_START-DEFAULT_LOOKBACK<=x.opened_at<DEV_WINDOW_END)
    if not native or any(x.symbol!=symbol for x in native):
        raise ValueError("provider M1 provenance not consistent with source")
    bars=tuple(x for x in native if x.opened_at>=DEV_WINDOW_START)
    opened=tuple(x.opened_at for x in bars)
    consecutive=_runs(bars)
    source_h1=_build_h1_bias_events(_aggregate(native,minutes=60))
    opposite={
        "BULLISH":tuple(x.confirmed_at for x in source_h1
                        if x.direction.value=="BEARISH"),
        "BEARISH":tuple(x.confirmed_at for x in source_h1
                        if x.direction.value=="BULLISH"),
    }
    original_mfe=observe_market_excursions(
        tuple(t for _,t in old_selected),bars
    ) if old_selected else ()
    alternative_mfe=observe_market_excursions(
        tuple(t for _,t in alt_selected),bars
    ) if alt_selected else ()
    old_mfe_by_key={original_key(t):t for t in original_mfe}
    alt_mfe_by_key={original_key(t):t for t in alternative_mfe}
    # ExcursionRow and economic trade share source keys except exit metadata.
    if len(old_mfe_by_key)!=len(old_selected) or len(alt_mfe_by_key)!=len(alt_selected):
        raise ValueError("MFE/MAE lifecycle did not reconcile")
    group:dict[tuple[str,str],list[Any]]=defaultdict(list)
    session=CapitalizerSession(sources[0].session)
    for bar in bars:
        if capitalizer_session_at(bar.opened_at) is session:
            group[(session.value,_operating_date(bar.opened_at,session))].append(bar)
    outputs:list[dict[str,Any]]=[]
    stage_problems:Counter[str]=Counter()
    for sid,trade in old_selected:
        excursion=old_mfe_by_key[original_key(trade)]
        outputs.append({
            "which":"V49","source_opportunity_id":sid,"symbol":symbol,
            "excursion":asdict(excursion),
        })
    for sid,trade in alt_selected:
        excursion=alt_mfe_by_key[original_key(trade)]
        source=source_by_id[sid]
        at=datetime.fromisoformat(trade.entry_at)
        side=1 if trade.direction=="LONG" else -1
        ix=bisect.bisect_left(opened,at)
        if ix==0 or ix==len(bars) or bars[ix-1].closed_at!=at:
            raise ValueError("first-online M1 close absent")
        if bars[ix-1].close!=Decimal(trade.entry_price):
            raise ValueError("first-online replay did not use provider close")
        actual=_future_label(
            bars,opened,consecutive,at,Decimal(trade.entry_price),
            side,trade.session,
        )
        eligible=tuple(b for b in eligible_h1_state_times(
            source,tuple(group.get((trade.session,trade.operating_date),())),
            opposite[source.h1_state_direction],
        ) if b.closed_at!=at)
        matched=tuple(b for b in eligible if _third(b.closed_at)==_third(at))
        random_modes:dict[str,dict[str,dict[str,int]]]={}
        for mode,candidates in zip(MODES,(eligible,matched),strict=True):
            draw=random.Random(_seed(sid,mode))
            chosen=tuple(candidates[draw.randrange(len(candidates))]
                         for _ in range(DRAWS)) if candidates else ()
            count={str(h):{"covered":0,"positive":0,"negative":0,"flat":0}
                   for h in HORIZONS}
            for sampled in chosen:
                y=_future_label(
                    bars,opened,consecutive,sampled.closed_at,sampled.close,
                    side,trade.session,
                )
                for h,v in zip(HORIZONS,y,strict=True):
                    if v is None:
                        continue
                    bucket=count[str(h)]
                    bucket["covered"]+=1
                    bucket["positive" if v>0 else "negative" if v<0 else "flat"]+=1
            random_modes[mode]=count
        try:
            altered=replace(
                source,m1_trigger_confirmed_at=trade.entry_at,
                m1_trigger_family=trade.trigger_family,
                decision_reference_price=trade.entry_price,
                structural_target_witness_price=trade.target_price,
            )
            chain=reconstruct_source_chain(
                altered,trade,bars,opened,consecutive,
            )
            stages={o.kind:asdict(o) for o in chain.stages}
            stage_error=None
        except ValueError as exc:
            # An independent stage observer can fail to reconstruct routes:
            # annotate the missing receipt, NEVER silently substitute original.
            stage_error=str(exc)
            stage_problems[stage_error]+=1
            stages=None
        outputs.append({
            "which":"ONLINE","source_opportunity_id":sid,
            "symbol":symbol,"session":trade.session,"operating_date":trade.operating_date,
            "online_family":trade.trigger_family,
            "m15_confirmed_at":source.m15_setup_confirmed_at,
            "h1_state_from":source.h1_state_from,
            "excursion":asdict(excursion),
            "h1_random_null":random_modes,
            "same_state_null_no_h1_until":True,
            "actual_favorable_by_horizon":{
                str(h):None if v is None else v>0
                for h,v in zip(HORIZONS,actual,strict=True)
            },
            "stage_reconstructed":stage_error is None,
            "stage_error":stage_error,
            "stages":stages,
            "outcome_used_for_admission":False,
        })
    return ({
        "identity":IDENTITY,"symbol":symbol,
        "baseline_selected":len(old_selected),"online_selected":len(alt_selected),
        "stage_reconstruction_failures":dict(sorted(stage_problems.items())),
        "provider_native_M1":True,"uses_future_outcomes_to_select":False,
        "physical_bid_ask_available":False,
    },tuple(outputs))


def summarize(root:Path)->dict[str,Any]:
    files=sorted(root.rglob("audit15-native-market.json"))
    if len(files)!=9:
        raise ValueError("all 9 source markets required")
    by_market=[json.loads(x.read_text(encoding="utf-8")) for x in files]
    if len({x["symbol"] for x in by_market})!=9:
        raise ValueError("native market symbols duplicated")
    raw=[x for p in sorted(root.rglob("audit15-native-receipts.jsonl"))
         for x in _jsonl(p)]
    old=[x for x in raw if x["which"]=="V49"]
    online=[x for x in raw if x["which"]=="ONLINE"]
    if (len(old)!=2020 or len(online)!=1997
            or len({x["source_opportunity_id"] for x in old})!=2020
            or len({x["source_opportunity_id"] for x in online})!=1997):
        raise ValueError("MAX3 population or source identity changed")
    groups={}
    for label,rows in (("V49",old),("ONLINE",online)):
        groups[label]=excursion_summary(tuple(
            ExcursionRow(**x["excursion"]) for x in rows
        ))
    rand={}
    for h in HORIZONS:
        n=sum(x["actual_favorable_by_horizon"][str(h)] is not None
              for x in online)
        positives=sum(x["actual_favorable_by_horizon"][str(h)] is True
                      for x in online)
        null={}
        for mode in MODES:
            total=sum(x["h1_random_null"][mode][str(h)]["covered"] for x in online)
            good=sum(x["h1_random_null"][mode][str(h)]["positive"] for x in online)
            null[mode]={
                "draw_covered":total,"draw_positive":good,
                "positive_fraction":str(Decimal(good)/Decimal(total)) if total else None,
            }
        rand[str(h)]={
            "online_covered":n,"online_favorable":positives,
            "online_positive_fraction":str(Decimal(positives)/Decimal(n)) if n else None,
            "state_matched_null":null,
            "random_state_control_is_not_executable_trades":True,
        }
    stage={}
    reconstructed=[x for x in online if x["stage_reconstructed"]]
    for family in sorted({x["online_family"] for x in online}):
        subset=[x for x in reconstructed if x["online_family"]==family]
        anchor=(
            "M1_SWEEP_CONFIRMED_BAR" if family=="LIQUIDITY_SWEEP_CISD"
            else "M1_FVG_FORMATION_CONFIRMED"
        )
        windows={}
        for h in HORIZONS:
            field=f"forward_signed_price_{h}"
            pairs=[]
            for x in subset:
                p=x["stages"]
                if p is None:
                    continue
                early=p[anchor][field]
                late=p["M1_CISD_CONFIRMED"][field]
                if early is not None and late is not None:
                    pairs.append((Decimal(early),Decimal(late)))
            early_count=sum(a>0 for a,z in pairs)
            late_count=sum(z>0 for a,z in pairs)
            windows[str(h)]={
                "paired_n":len(pairs),"early_favorable":early_count,
                "cisd_favorable":late_count,
                "late_minus_early_pp":
                    str(Decimal(100)*(late_count-early_count)/Decimal(len(pairs)))
                    if pairs else None,
            }
        stage[family]={
            "online_selected":sum(x["online_family"]==family for x in online),
            "stage_reconstructed":len(subset),
            "stage_missing":sum(x["online_family"]==family
                                and not x["stage_reconstructed"] for x in online),
            "paired_sweep_or_fvg_to_cisd":windows,
        }
    return {
        "identity":IDENTITY,"markets":9,"V49_MAX3":len(old),"ONLINE_MAX3":len(online),
        "native_m1_mfe_mae":groups,
        "h1_random_same_state_competitor":rand,
        "sweep_fvg_to_cisd":stage,
        "stage_reconstructed":len(reconstructed),
        "stage_missing":len(online)-len(reconstructed),
        "no_fitted_rules_or_filters":True,
        "outcome_labels_hindsight_only":True,
        "physical_execution_costs_present":False,
        "universe_H1_M15_regenerated":False,
        "certification":"BLOCKED",
    }


def main()->None:
    parser=argparse.ArgumentParser()
    sub=parser.add_subparsers(dest="mode",required=True)
    m=sub.add_parser("market")
    m.add_argument("selection",type=Path)
    m.add_argument("source",type=Path)
    m.add_argument("economic",type=Path)
    m.add_argument("native",type=Path)
    m.add_argument("output",type=Path)
    a=sub.add_parser("matrix")
    a.add_argument("inputs",type=Path)
    a.add_argument("output",type=Path)
    args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    if args.mode=="market":
        status,rows=market(
            args.selection,args.source,args.economic,args.native,
        )
        (args.output/"audit15-native-market.json").write_text(
            json.dumps(status,indent=2,sort_keys=True)+"\n",encoding="utf-8"
        )
        with (args.output/"audit15-native-receipts.jsonl").open(
            "w",encoding="utf-8"
        ) as file:
            for x in rows:
                file.write(json.dumps(x,sort_keys=True)+"\n")
        print(json.dumps(status,sort_keys=True))
    else:
        report=summarize(args.inputs)
        (args.output/"audit15-native-nine-market.json").write_text(
            json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8"
        )
        print(json.dumps(report,sort_keys=True))


if __name__=="__main__":
    main()
