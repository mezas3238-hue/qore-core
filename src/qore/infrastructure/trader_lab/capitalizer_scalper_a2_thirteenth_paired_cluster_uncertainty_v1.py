"""Audit13 cross-ledger H1/online strata and day-cluster uncertainty.

Bootstrap estimates only P(positive signed close) difference at +15/30/60.
This cannot establish fill-based trade profitability or author fidelity.
All identity joins are strict, frozen and post-decision outcome-free.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from random import Random
from typing import Any

from qore.infrastructure.trader_lab.capitalizer_scalper_v49_v50_g_waterfall_v1 import (
    _jsonl,
)

IDENTITY="QORE_SCALPER_A2_AUDIT13_CLUSTERED_PAIRED_SOURCE_STRATA_V1"
HORIZONS=(15,30,60)
DRAWS=1000
SEED=20261010


def bootstrap_pp(
    cohort:list[dict[str,Any]],horizon:int,
) ->dict[str,Any]:
    """Draw complete operating-date clusters, retaining cross-market dependence."""

    clusters:dict[str,list[int]]=defaultdict(list)
    for row in cohort:
        comparison=row["paired"][str(horizon)]
        v49,online=comparison["v49"],comparison["online"]
        if not v49["covered"] or not online["covered"]:
            continue
        clusters[row["operating_date"]].append(
            int(online["positive"])-int(v49["positive"])
        )
    n=sum(len(v) for v in clusters.values())
    if not n:
        return {
            "paired_covered":0,"operating_day_clusters":0,
            "favorable_online_minus_v49_pp":None,
            "day_cluster_95ci_pp":None,
            "exploratory_5pp_label":"INSUFFICIENT_COVERAGE",
        }
    delta=sum(sum(v) for v in clusters.values())
    estimates=[]
    days=sorted(clusters)
    rng=Random(SEED+int(horizon)+len(cohort)*97)
    for _ in range(DRAWS):
        sample=(clusters[days[rng.randrange(len(days))]] for _ in days)
        picked=list(sample)
        total=sum(len(v) for v in picked)
        diff=sum(sum(v) for v in picked)
        estimates.append(100*diff/total)
    estimates.sort()
    low=round(estimates[24],4)
    high=round(estimates[975],4)
    if low>=-5 and high<=5:
        label="DIAGNOSTIC_5PP_BAND_WITHIN_CI"
    elif low>5:
        label="DIAGNOSTIC_ONLINE_ADVANTAGE_ABOVE_5PP"
    elif high < -5:
        label="DIAGNOSTIC_V49_ADVANTAGE_ABOVE_5PP"
    else:
        label="INCONCLUSIVE_CI_CROSSES_5PP"
    return {
        "paired_covered":n,"operating_day_clusters":len(days),
        "favorable_online_minus_v49_pp":round(100*delta/n,4),
        "day_cluster_95ci_pp":[low,high],
        "exploratory_5pp_label":label,
        "uncertainty_is_not_an_execution_cost_or_trade_CI":True,
    }


def audit(stream_root:Path,h1_root:Path)->dict[str,Any]:
    streams=[
        x for p in sorted(stream_root.rglob("scalper-thirteenth-stream-ids.jsonl"))
        for x in _jsonl(p)
    ]
    h1=[
        x for p in sorted(h1_root.rglob("scalper-audit13-h1poi-ids.jsonl"))
        for x in _jsonl(p)
    ]
    if len(streams)!=2876 or len(h1)!=2876:
        raise ValueError("both immutable nine-market ID ledgers required")
    mapping={x["source_opportunity_id"]:x for x in h1}
    if (len(mapping)!=2876
            or len({x["source_opportunity_id"] for x in streams})!=2876
            or {x["source_opportunity_id"] for x in streams}!=set(mapping)):
        raise ValueError("unmatched or duplicated H1/CISD source IDs")
    joined: list[dict[str,Any]]=[]
    for x in streams:
        witness=mapping[x["source_opportunity_id"]]
        if x["symbol"]!=witness["symbol"]:
            raise ValueError("symbol mismatch on source join")
        joined.append({
            **x,
            "original_basis":witness["original_basis"],
            "h1_event_reconstructed":witness["source_event_reconstructed"],
            "h1_exact_60_60":bool(witness.get("closure_geometrical_60_60",False)),
            "h1_event_close_is_clock_hour":(
                witness["origin_closed_at"][14:16]=="00"
                if witness.get("origin_closed_at") else None
            ),
        })
    frozen381=[x for x in joined if x["frozen_full_prefix_disagreement"]]
    early=[x for x in frozen381
           if x["frozen_prefix_sensor_at"]<x["v49_entry_at"]]
    same=[x for x in frozen381
          if x["frozen_prefix_sensor_at"]==x["v49_entry_at"]]
    if len(frozen381)!=381 or len(early)!=247 or len(same)!=134:
        raise ValueError("frozen 247 earlier and 134 same-close labels diverged")
    different=[x for x in joined if x["family_changed"] or x["close_changed"]]
    matched=[x for x in joined if not (x["family_changed"] or x["close_changed"])]
    exact=[x for x in joined if x["h1_exact_60_60"]]
    unmatched=[x for x in joined if not x["h1_event_reconstructed"]]
    groupings={
        "FROZEN_381":frozen381,
        "FROZEN_381_SENSOR_EARLIER_247":early,
        "FROZEN_381_SENSOR_SAME_CLOSE_134":same,
        "FIRST_INCREMENTAL_DIFFERENT":different,
        "FIRST_INCREMENTAL_SAME":matched,
        "H1_QORE_EVENT_UNRECONSTRUCTED":unmatched,
        "H1_NATIVE_EXACT_60_60":exact,
        "ALL_SOURCE_OPPORTUNITIES":joined,
    }
    strata={}
    for name,cohort in groupings.items():
        strata[name]={
            "source_opportunities":len(cohort),
            "horizons":{
                str(h):bootstrap_pp(cohort,h) for h in HORIZONS
            },
        }
    source_counts:Counter[str]=Counter()
    for x in joined:
        if x["h1_event_reconstructed"]:
            source_counts["SOURCE_EVENT_RECONSTRUCTED"]+=1
            if x["h1_event_close_is_clock_hour"]:
                source_counts["RECONSTRUCTED_H1_EVENT_AT_CLOCK_HOUR"]+=1
            else:
                source_counts["RECONSTRUCTED_H1_EVENT_NOT_AT_CLOCK_HOUR"]+=1
        else:
            source_counts["SOURCE_EVENT_UNRECONSTRUCTED"]+=1
            if x["original_basis"].startswith("SESSION_INHERITED:"):
                source_counts["UNRECONSTRUCTED_INHERITED"]+=1
            else:
                source_counts["UNRECONSTRUCTED_DIRECT"]+=1
        if x["h1_exact_60_60"]:
            source_counts["H1_EXACT_60_60"]+=1
        if x["frozen_full_prefix_disagreement"]:
            source_counts["FROZEN_CISD_381"]+=1
    return {
        "identity":IDENTITY,"sources":2876,"markets":9,
        "counts":dict(sorted(source_counts.items())),"strata":strata,
        "bootstrap_resamples":DRAWS,"fixed_seed":SEED,
        "paired_label_not_real_fill_economics":True,
        "no_veto_or_trade_admission_changes":True,
        "source_author_fidelity_not_certified":True,
        "paper_pf":None,"paper_dd":None,
    }


def main()->None:
    p=argparse.ArgumentParser()
    p.add_argument("stream",type=Path)
    p.add_argument("h1",type=Path)
    p.add_argument("output",type=Path)
    args=p.parse_args()
    result=audit(args.stream,args.h1)
    args.output.mkdir(parents=True,exist_ok=True)
    (args.output/"scalper-audit13-cluster-nine-market.json").write_text(
        json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8"
    )
    print(json.dumps(result,sort_keys=True))


if __name__=="__main__":
    main()
