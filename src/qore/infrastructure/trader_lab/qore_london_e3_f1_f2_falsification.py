"""F1/F2 preregistered falsification of already-frozen EUR/GBP London E3 paths.

Date-shared circular moving-block bootstrap (5 NY dates); never recomputes
signal states, price outcomes or M1. No trading or production modifications.
"""
from __future__ import annotations

import argparse
import json
import random
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ID = "QORE_LONDON_E3_F1_F2_RECLAIM_INTERACTION_FALSIFICATION_V1"
SYMBOLS = ("EURUSD", "GBPUSD")
STATES = ("RECLAIM_INSIDE", "ACCEPTED_ATR_0P5")
SCENARIOS = ("FULL", "H4_KNOWN", "H4_UNKNOWN")
K = 5
SEED = 77520261014
FULL_REPS = 2000
LOBO_REPS = 1000
EXPECTED = {
    ("EURUSD", "RECLAIM_INSIDE"): (94, 38),
    ("EURUSD", "ACCEPTED_ATR_0P5"): (88, 35),
    ("GBPUSD", "RECLAIM_INSIDE"): (92, 22),
    ("GBPUSD", "ACCEPTED_ATR_0P5"): (98, 42),
}
H4_VALID = ("H4_ALIGNED_WITH_RAID", "H4_OPPOSED_TO_RAID")
CELLS = tuple((sym, state) for sym in SYMBOLS for state in STATES)
VECTOR_LENGTH = len(CELLS)*2


def freeze_rows(directory: Path) -> tuple[list[dict[str, Any]], list[str]]:
    files = sorted(directory.rglob("qore-london-E3-*-joined-states.jsonl"))
    if len(files) != 2:
        raise ValueError(f"must find exactly 2 E3 original ledgers: {len(files)}")
    rows = [
        json.loads(line)
        for file in files for line in file.read_text().splitlines()
        if line.strip()
    ]
    if len(rows) != 522:
        raise ValueError("E3 source must have exactly 522 NY-day rows")
    identities = [(x["symbol"], x["ny_day"]) for x in rows]
    if len(set(identities)) != 522:
        raise ValueError("duplicate E3 identity")
    dates = sorted({x["ny_day"] for x in rows})
    if len(dates) != 261:
        raise ValueError(f"expected 261 shared NY dates: {len(dates)}")
    if any(len([x for x in rows if x["ny_day"] == d]) != 2 for d in dates):
        raise ValueError("missing paired EUR/GBP NY day")
    if {x["symbol"] for x in rows} != set(SYMBOLS):
        raise ValueError("unexpected E3 symbol")
    valid = [x for x in rows if x["status"] == "CHECKPOINT_VALID"]
    if len(valid) != 458 or Counter(x["symbol"] for x in valid) != {"EURUSD": 227, "GBPUSD":231}:
        raise ValueError("original checkpoints modified")
    for cell, expected in EXPECTED.items():
        eligible = [x for x in valid if (x["symbol"],x["E3_state"]) == cell]
        actual = (len(eligible), sum(x["terminal_60"] == "REVERSAL" for x in eligible))
        if actual != expected:
            raise ValueError(f"frozen original rate changed: {cell} {actual}!={expected}")
    if any(x["terminal_60"] not in ("REVERSAL", "CONTINUATION", "NEUTRAL") for x in valid):
        raise ValueError("all 458 terminal60 outcomes must be known")
    if any(x["H4_E2_status"] is None for x in valid):
        raise ValueError("missing E2 H4 classification")
    return rows, dates


def scenario_qualifies(row: dict[str, Any], scenario: str) -> bool:
    if scenario == "FULL":
        return True
    if scenario == "H4_KNOWN":
        return row["H4_E2_status"] in H4_VALID
    if scenario == "H4_UNKNOWN":
        return row["H4_E2_status"] not in H4_VALID
    raise ValueError("unknown scenario")


def build_date_vectors(
    rows: list[dict[str, Any]], dates: list[str], scenario: str
) -> list[tuple[int, ...]]:
    indexes = {cell:i for i,cell in enumerate(CELLS)}
    day_idx = {day:i for i,day in enumerate(dates)}
    vectors = [[0]*VECTOR_LENGTH for _ in dates]
    for row in rows:
        if row["status"] != "CHECKPOINT_VALID" or not scenario_qualifies(row, scenario):
            continue
        key = (row["symbol"], row["E3_state"])
        if key not in indexes:
            continue
        i = indexes[key]*2
        d = vectors[day_idx[row["ny_day"]]]
        d[i] += 1
        if row["terminal_60"] == "REVERSAL":
            d[i+1] += 1
    return [tuple(v) for v in vectors]


def combine(vectors: list[tuple[int, ...]]) -> tuple[int, ...]:
    arr = [0]*VECTOR_LENGTH
    for v in vectors:
        for i,n in enumerate(v):
            arr[i] += n
    return tuple(arr)


def interaction(vector: tuple[int, ...]) -> float | None:
    if len(vector) != VECTOR_LENGTH or any(vector[j] == 0 for j in (0,2,4,6)):
        return None
    eur = vector[1]/vector[0] - vector[3]/vector[2]
    gbp = vector[5]/vector[4] - vector[7]/vector[6]
    return eur-gbp


def cell_counts(vector: tuple[int, ...]) -> dict[str, Any]:
    return {
        f"{cell[0]}|{cell[1]}": {
            "N":vector[i*2], "reversal":vector[i*2+1],
            "p_reversal":vector[i*2+1]/vector[i*2] if vector[i*2] else None,
        }
        for i,cell in enumerate(CELLS)
    }


def moving_block_bootstrap(
    vectors: list[tuple[int, ...]], seed: int, n_reps: int
) -> dict[str, Any]:
    """Circular block start drawn from common date-index, pairs remain paired.

    Bootstrap input is ordered days, not trade rows. Every resample
    draws ceil(N/5) contiguous date blocks, truncating to N exactly.
    """
    n = len(vectors)
    if n < 5:
        raise ValueError("insufficient date blocks")
    block_vectors = [
        combine([vectors[(start+j)%n] for j in range(K)])
        for start in range(n)
    ]
    remainder = n % K
    rng = random.Random(seed)
    vals = []
    for _ in range(n_reps):
        accum = [0]*VECTOR_LENGTH
        for _ in range(n//K):
            block=block_vectors[rng.randrange(n)]
            for j in range(VECTOR_LENGTH):
                accum[j]+=block[j]
        if remainder:
            start=rng.randrange(n)
            for k in range(remainder):
                day=vectors[(start+k)%n]
                for j in range(VECTOR_LENGTH):
                    accum[j]+=day[j]
        v=interaction(tuple(accum))
        if v is not None:
            vals.append(v)
    vals.sort()
    def quantile(p: float) -> float | None:
        if not vals:
            return None
        z=(len(vals)-1)*p
        left=int(z)
        return vals[left]*(1-(z-left))+vals[min(left+1,len(vals)-1)]*(z-left)
    return {
        "valid":len(vals), "requested":n_reps,
        "confidence_interval_95":[quantile(.025),quantile(.975)],
        "bootstrap_nonpositive_share":sum(z<=0 for z in vals)/len(vals) if vals else None,
        "low_support":len(vals)<.95*n_reps,
        "paired_date_blocks":5,
    }


def any_zero_ci(boot:dict[str,Any])->bool:
    a,b=boot["confidence_interval_95"]
    return a is None or b is None or a <= 0 <= b


def decide_f1(full:float,known:float|None,boot:dict[str,Any])->dict[str,Any]:
    if known is None or boot["low_support"]:
        return {"status":"F1_FAIL_PROMOTION_UNESTIMABLE","positive_ci_excludes_zero":False}
    collapse = known <=0 or abs(known) < .5*abs(full)
    crossed = any_zero_ci(boot)
    return {
        "status":"F1_COLLAPSE" if collapse else (
            "F1_FAIL_PROMOTION_CI_CROSSES_ZERO" if crossed else "F1_SURVIVES_HISTORICAL"
        ),
        "point_collapse":collapse, "ci_crosses_zero":crossed,
        "positive_ci_excludes_zero":not crossed and boot["confidence_interval_95"][0]>0,
    }


def runner(rows:list[dict[str,Any]], dates:list[str])->dict[str,Any]:
    vectors={s:build_date_vectors(rows,dates,s) for s in SCENARIOS}
    full={s:combine(v) for s,v in vectors.items()}
    effects={s:interaction(v) for s,v in full.items()}
    if effects["FULL"] is None or abs(effects["FULL"]-.19596904021048328)>1e-12:
        raise ValueError("expected frozen E3 interaction must reproduce exactly")
    baseline={
        s:{
            "effect":effects[s],
            "cells":cell_counts(full[s]),
            "bootstrap":moving_block_bootstrap(vectors[s],SEED+index*1_001,FULL_REPS),
        }
        for index,s in enumerate(SCENARIOS)
    }
    baseline["H4_KNOWN"]["f1_adjudication"]=decide_f1(
        effects["FULL"],effects["H4_KNOWN"],baseline["H4_KNOWN"]["bootstrap"]
    )
    partitions=[tuple(dates[i:i+K]) for i in range(0,len(dates),K)]
    if len(partitions)!=53 or len(partitions[-1])!=1:
        raise ValueError("expected 52 complete 5-NY-date blocks plus 1 last date")
    per_block=[]
    for idx,dropped in enumerate(partitions):
        exclude=set(dropped)
        remaining=[i for i,d in enumerate(dates) if d not in exclude]
        tests={}
        for s in ("FULL","H4_KNOWN"):
            sample=[vectors[s][i] for i in remaining]
            estimated=interaction(combine(sample))
            stats=moving_block_bootstrap(sample,SEED+(idx+1)*101+(0 if s=="FULL" else 53),LOBO_REPS)
            ref=effects[s]
            collapse=(estimated is None or estimated<=0 or
                      (abs(estimated)<.5*abs(ref) and any_zero_ci(stats)))
            tests[s]={
                "effect":estimated, "delta_vs_same_scenario_baseline":estimated-ref if estimated is not None and ref is not None else None,
                "cells":cell_counts(combine(sample)),
                "bootstrap":stats,
                "single_block_point_collapse":collapse,
                "CI_crosses_zero":any_zero_ci(stats),
            }
        per_block.append({
            "block_index_1based":idx+1,
            "dates_NY_removed":list(dropped),
            "days_in_block":len(dropped),
            "remaining_days":len(remaining),
            "tests":tests,
        })
    top2=sorted(
        per_block,
        key=lambda b:(
            b["tests"]["FULL"]["effect"] if b["tests"]["FULL"]["effect"] is not None else -999,
            b["block_index_1based"]
        )
    )[:2]
    excluded={d for b in top2 for d in b["dates_NY_removed"]}
    together={}
    for idx,s in enumerate(("FULL","H4_KNOWN")):
        sample=[v for d,v in zip(dates,vectors[s],strict=True) if d not in excluded]
        estimate=interaction(combine(sample))
        stats=moving_block_bootstrap(sample,SEED+9_000+idx,2_000)
        together[s]={
            "effect":estimate, "cells":cell_counts(combine(sample)),
            "bootstrap":stats,
            "CI_crosses_zero":any_zero_ci(stats),
            "point_collapse":estimate is None or estimate<=0 or
                (estimate is not None and abs(estimate)<.5*abs(effects[s]) and any_zero_ci(stats)),
        }
    summary={}
    for s in ("FULL","H4_KNOWN"):
        sub=[x["tests"][s] for x in per_block]
        vals=[x["effect"] for x in sub if x["effect"] is not None]
        summary[s]={
            "effect_original":effects[s],
            "min_leave_one_effect":min(vals) if vals else None,
            "max_leave_one_effect":max(vals) if vals else None,
            "CI_crosses_zero_block_count":sum(x["CI_crosses_zero"] for x in sub),
            "point_collapse_block_count":sum(x["single_block_point_collapse"] for x in sub),
            "bootstrap_low_support_block_count":sum(x["bootstrap"]["low_support"] for x in sub),
            "strict_survives_all_53":all(
                x["effect"] is not None and x["effect"]>0
                and not x["CI_crosses_zero"] and not x["bootstrap"]["low_support"]
                for x in sub
            ),
        }
    f2_strict=all(x["strict_survives_all_53"] for x in summary.values())
    f1=baseline["H4_KNOWN"]["f1_adjudication"]
    result={
        "identity":ID,"original_dates":len(dates),
        "frozen_source_checkpoints":458,
        "frozen_e3_eligible_R_or_accept":sum(full["FULL"][::2]),
        "date_bootstrap_method":"circular blocks of 5 shared NY dates; 2000 F1, 1000 each F2",
        "E3_FULL_KNOWN_UNKNOWN":baseline,
        "F2_53_fixed_chronological_blocks":per_block,
        "F2_leave_one_block_summary":summary,
        "F2_two_most_effect_reducing_full_blocks": {
            "selection":"two lowest individual FULL leave-one-block-out point effects (deterministic)",
            "selected_indices":[x["block_index_1based"] for x in top2],
            "removed_dates_NY":sorted(excluded),
            "tests":together,
        },
        "falsification_gates":{
            "F1":f1["status"],
            "F2":"F2_SURVIVES_STRICT" if f2_strict else "F2_FAIL_STRICT_PROMOTION",
            "RECLAIM_ACCEPTED_PROMOTION":"HISTORICAL_ROBUST_ONLY" if (
                f1["status"]=="F1_SURVIVES_HISTORICAL" and f2_strict
            ) else "STOP_NO_PROMOTION",
        },
        "already_inspected_history":True,"SMT_not_tested":True,
        "no_trader_or_production":True,
    }
    return result


def main()->None:
    ap=argparse.ArgumentParser()
    ap.add_argument("frozen_e3_dir",type=Path)
    ap.add_argument("output",type=Path)
    args=ap.parse_args()
    rows,dates=freeze_rows(args.frozen_e3_dir)
    out=runner(rows,dates)
    args.output.mkdir(parents=True,exist_ok=True)
    (args.output/"qore-london-E3-F1-F2-falsification-results.json").write_text(
        json.dumps(out,ensure_ascii=False,indent=2,sort_keys=True)+"\n",
        encoding="utf-8",
    )
    print("QORE_E3_F1_F2_RESULT",json.dumps({
        "f1":out["E3_FULL_KNOWN_UNKNOWN"],
        "f2":out["F2_leave_one_block_summary"],
        "f2_adversarial_pair":out["F2_two_most_effect_reducing_full_blocks"],
        "gates":out["falsification_gates"],
        "n_dates":out["original_dates"],
    },ensure_ascii=False,sort_keys=True))


if __name__=="__main__":
    main()
