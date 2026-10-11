"""Audit14 source-ID winner preservation over genuine economic closed trades.

Compares original chronological MAX3 versus source-anchored causal-first MAX3.
Original winners and their original positive R are frozen at baseline, never
used to choose which source candidate to execute. All metrics are GROSS only.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.capitalizer_scalper_v49_v50_g_waterfall_v1 import (
    _jsonl,
)
from qore.infrastructure.trader_lab.capitalizer_v49_development_economics import (
    V49EconomicTrade,
    _metrics,
    _portfolio_select,
)

IDENTITY = "QORE_SCALPER_A2_FOURTEENTH_CAUSAL_FIRST_WINNER_IDENTITY_CHECK_V1"


def original_key(t:V49EconomicTrade)->tuple[str,...]:
    return t.symbol,t.session,t.operating_date,t.entry_at,t.trigger_family


def source_key(row:dict[str,Any])->tuple[str,...]:
    return (
        row["symbol"],row["session"],row["operating_date"],
        row["v49_entry_at"],row["source_family"],
    )


def candidate_key(row:dict[str,Any])->tuple[str,...]:
    return (
        row["symbol"],row["session"],row["operating_date"],
        row["online_entry_at"],row["online_family"],
    )


def reconcile(root:Path)->dict[str,Any]:
    rows=[x for p in sorted(root.rglob("scalper-audit14-ids.jsonl"))
          for x in _jsonl(p)]
    original=tuple(
        V49EconomicTrade(**x)
        for p in sorted(root.rglob("capitalizer-*-v49-development-economics-trades.jsonl"))
        for x in _jsonl(p)
    )
    alt=tuple(
        V49EconomicTrade(**x)
        for p in sorted(root.rglob("scalper-audit14-candidates.jsonl"))
        for x in _jsonl(p)
    )
    if (len(rows)!=2876 or len(original)!=2876
            or len({x["source_opportunity_id"] for x in rows})!=2876):
        raise ValueError("original 2876 IDs and economic reference not conserved")
    by_original={source_key(x):x for x in rows}
    by_alt={candidate_key(x):x for x in rows if x["status"]=="ELIGIBLE"}
    if len(by_original)!=len(rows) or len(by_alt)!=len(alt):
        raise ValueError("source key collisions prevent winner identity certification")
    for t in original:
        if original_key(t) not in by_original:
            raise ValueError("original economic trade lacks source-ID mapping")
    for t in alt:
        if original_key(t) not in by_alt:
            raise ValueError("alt economic trade lacks same-anchor source-ID mapping")
    baseline=tuple(t for _,t in _portfolio_select(original))
    new=tuple(t for _,t in _portfolio_select(alt))
    if len(baseline)!=2020:
        raise ValueError("original 2020 MAX3 portfolio modified")
    baseline_by_id={
        by_original[original_key(t)]["source_opportunity_id"]:t
        for t in baseline
    }
    alternative_by_id={
        by_alt[original_key(t)]["source_opportunity_id"]:t
        for t in new
    }
    if len(baseline_by_id)!=len(baseline) or len(alternative_by_id)!=len(new):
        raise ValueError("MAX3 selected IDs not unique")
    original_winners={
        id:Decimal(t.realized_gross_r)
        for id,t in baseline_by_id.items()
        if Decimal(t.realized_gross_r)>0
    }
    if len(original_winners)!=1167:
        raise ValueError("V49 frozen 1167 winners not preserved")
    retained={
        id:amount for id,amount in original_winners.items()
        if id in alternative_by_id
    }
    mass=sum(original_winners.values(),Decimal(0))
    preserved_mass=sum(retained.values(),Decimal(0))
    original_ids=set(baseline_by_id)
    candidate_ids=set(alternative_by_id)
    winner_ids=set(original_winners)
    result={
        "identity":IDENTITY,"sources":2876,
        "baseline_max3":len(baseline),"candidate_max3":len(new),
        "baseline_winners":len(winner_ids),
        "original_winner_gross_mass_R":str(mass),
        "retained_original_winner_id_count":len(retained),
        "retained_original_winner_mass_R":str(preserved_mass),
        "retained_original_winner_mass_share":str(preserved_mass/mass),
        "original_max3_ids_retained":len(original_ids & candidate_ids),
        "original_max3_ids_lost":len(original_ids-candidate_ids),
        "new_max3_ids":len(candidate_ids-original_ids),
        "retained_original_winner_ids_that_win_alt":sum(
            Decimal(alternative_by_id[id].realized_gross_r)>0
            for id in retained
        ),
        "retained_original_winner_ids_that_lose_alt":sum(
            Decimal(alternative_by_id[id].realized_gross_r)<0
            for id in retained
        ),
        "original_max3_gross_metrics":asdict(_metrics(baseline)),
        "candidate_max3_gross_metrics":asdict(_metrics(new)),
        "owner_original_winner_count_gate_934_met":len(retained)>=934,
        "owner_original_winner_mass_gate_415_74848565R_met":
            preserved_mass>=Decimal("415.74848565"),
        "owner_gates_not_TTrades_source_rules":True,
        "gross_only_no_physical_bid_ask":True,
        "author_fidelity_certified":False,
    }
    if result["candidate_max3"]>2020:
        raise ValueError("MAX3 can never exceed original frozen ceiling")
    return result


def main()->None:
    parser=argparse.ArgumentParser()
    parser.add_argument("inputs",type=Path)
    parser.add_argument("output",type=Path)
    args=parser.parse_args()
    report=reconcile(args.inputs)
    args.output.mkdir(parents=True,exist_ok=True)
    (args.output/"scalper-audit14-winner-preservation-nine-market.json").write_text(
        json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8"
    )
    print(json.dumps(report,sort_keys=True))


if __name__=="__main__":
    main()
