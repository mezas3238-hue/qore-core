"""VT31 NAS100 causal hybrid rearm admission scan V2.

Consumed-evidence tuning only.

Starting point: WAIT_1025_B060 + genuine structural rearm already showed PF>2
and DD<10R cross-fold, but all rearms overpopulate R5/R6. This scan changes
only rearm admission using the existing causal pre-entry quality score.

No terminal outcome, fold identity, target trade count, or future bar is used by
an admission rule. Trade count is an evaluation output, never an input.
"""
# ruff: noqa: B009
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_nas100_causal_hybrid_density_v2 as hybrid
import vt31_nas100_causal_hybrid_rearm_v1 as rearm
import vt31_nas100_high_density_structural_protection_v1 as protection
import vt31_nas100_specialist_r1_candidate as specialist
import vt31_nas100_structural_rearm_density_frontier_v1 as frontier
import vt31_nas100_structural_rearm_quality_frontier_v1 as quality

from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_5_multi_index_research import (
    _day,
    _metrics,
    _wall,
    load_market_evidence,
)
from qore.infrastructure.traders.vt31_nas100_position_intelligence import (
    structurally_rearmed,
)
from qore.infrastructure.traders.vt31_silver_bullet_r2_2 import (
    Vt31R22ExecutionPolicy,
)

SCHEMA="qore.vt31.nas100.causal_hybrid_rearm_admission.v2"
IDENTITY="VT31_NAS100_CAUSAL_HYBRID_REARM_ADMISSION_V2"
MARKET="NAS100"
FRICTION=Decimal("0.05")
BASE_VARIANT="WAIT_1025_B060"
WAIT_RELEASE_MINUTE=10*60+25
MONTHLY_ALT_BUDGET=Decimal("0.60")
RISK_MAP={
    "HIGH":Decimal("0.10"),
    "MID":Decimal("0.05"),
    "LOW":Decimal("0.02"),
}
ADMISSIONS={
    "ALL":lambda score: True,
    "GE_NEG1":lambda score: score>=-1,
    "GE_0":lambda score: score>=0,
    "GE_1":lambda score: score>=1,
    "GE_2":lambda score: score>=2,
    "EXCLUDE_1_2":lambda score: score not in {1,2},
    "LE_0_OR_GE_3":lambda score: score<=0 or score>=3,
    "GE_0_EXCEPT_1_2":lambda score: score==0 or score>=3,
}


def _risk_class(score: int) -> str:
    return "HIGH" if score>=5 else ("MID" if score>=3 else "LOW")


def _weighted(
    outcome: dict[str,object],
    *,
    score: int,
) -> dict[str,object]:
    cls=_risk_class(score)
    risk=RISK_MAP[cls]
    gross=Decimal(cast(str,outcome["r_multiple"]))
    net=risk*(gross-FRICTION)
    row=dict(outcome)
    row.update({
        "tier":"REARM",
        "requested_risk_r":format(risk,"f"),
        "capital_weighted_net_r":format(net,"f"),
        "rearm_quality_score":score,
        "rearm_risk_class":cls,
    })
    return row


def _capital_metrics(rows: list[dict[str,object]]) -> dict[str,object]:
    converted=[
        {**row,"r_multiple":row["capital_weighted_net_r"]}
        for row in rows
    ]
    return _metrics(converted,friction=Decimal(0))


def _mc(rows: list[dict[str,object]], *, variant: str) -> dict[str,object]:
    values=[
        Decimal(cast(str,row["capital_weighted_net_r"]))
        for row in rows
    ]
    n=len(values)
    if not n:
        return {
            "paths":10000,
            "positive_terminal_probability":"0",
            "p95_max_drawdown_r":"0",
            "p99_max_drawdown_r":"0",
        }
    terminals=[]
    dds=[]
    domain=IDENTITY.encode()+b":"+variant.encode()
    for path_index in range(10000):
        sampled=[]
        block_index=0
        while len(sampled)<n:
            digest=hashlib.sha256(
                domain+b":"+str(path_index).encode()+b":"+
                str(block_index).encode()
            ).digest()
            start=int.from_bytes(digest,"big")%n
            sampled.extend(values[(start+i)%n] for i in range(5))
            block_index+=1
        equity=Decimal(0)
        peak=Decimal(0)
        max_dd=Decimal(0)
        for value in sampled[:n]:
            equity+=value
            peak=max(peak,equity)
            max_dd=max(max_dd,peak-equity)
        terminals.append(equity)
        dds.append(max_dd)
    terminals.sort()
    dds.sort()
    return {
        "paths":10000,
        "block_length":5,
        "positive_terminal_probability":format(
            Decimal(sum(x>0 for x in terminals))/Decimal(10000),"f"
        ),
        "p05_terminal_r":format(terminals[(n-1)*5//100],"f"),
        "p50_terminal_r":format(terminals[(n-1)*50//100],"f"),
        "p95_max_drawdown_r":format(dds[(n-1)*95//100],"f"),
        "p99_max_drawdown_r":format(dds[(n-1)*99//100],"f"),
    }


def replay(evidence_path: Path, *, partition: str) -> dict[str,object]:
    series,account,evidence,checked,evidence_sha,provider=load_market_evidence(
        evidence_path
    )
    if not series or getattr(series[0],"instrument").symbol!=MARKET:
        raise ValueError("hybrid rearm admission requires NAS100")

    raw: dict[date,list[object]]=defaultdict(list)
    for bar in series:
        raw[_day(getattr(bar,"opened_at"))].append(bar)
    by_day={
        d:tuple(sorted(items,key=lambda item:getattr(item,"opened_at")))
        for d,items in raw.items()
    }
    context_by_day=specialist._context_map(by_day)
    first_report=hybrid._run_variant(
        by_day,
        context_by_day,
        evidence=evidence,
        wait_release_minute=WAIT_RELEASE_MINUTE,
        monthly_alt_budget=MONTHLY_ALT_BUDGET,
        variant=BASE_VARIANT,
    )
    first_rows=[
        dict(row)
        for row in cast(list[dict[str,object]],first_report["trades"])
    ]
    first_by_day={
        date.fromisoformat(cast(str,row["local_date"])):row
        for row in first_rows
    }

    policy=Vt31R22ExecutionPolicy()
    terminal_rearms: list[dict[str,object]]=[]
    statuses: Counter[str]=Counter()

    for local_day,first_row in sorted(first_by_day.items()):
        exit_at=datetime.fromisoformat(cast(str,first_row["exit_at"]))
        if _wall(exit_at)>=(11,0,0):
            statuses["first-exit-after-source-window"]+=1
            continue
        day_bars=by_day[local_day]
        reference=specialist._slice(day_bars,(9,0,0),(10,0,0))
        session=specialist._slice(day_bars,(10,0,0),(11,0,0))
        if len(reference)!=60 or len(session)!=60:
            statuses["incomplete-day"]+=1
            continue
        selected=frontier._next_executable_after(
            reference=reference,
            session=session,
            after_at=exit_at,
            evidence=evidence,
            policy=policy,
        )
        if selected is None:
            statuses["no-post-exit-source"]+=1
            continue
        source,setup=selected
        if not structurally_rearmed(
            protected_exit_at_epoch=int(exit_at.timestamp()),
            new_raid_at_epoch=int(source.structure.raid_at.timestamp()),
            new_confirmation_at_epoch=int(source.structure.confirmation_at.timestamp()),
            new_decision_at_epoch=int(setup.decision_at.timestamp()),
        ):
            statuses["rearm-invariant-failed"]+=1
            continue

        prev_range,prior_ref,prior_bars=context_by_day[local_day]
        observation_at=setup.decision_at
        prefix=tuple(
            bar for bar in session
            if cast(datetime,getattr(bar,"closed_at"))<=observation_at
        )
        state=specialist._state_snapshot(
            day_bars,prev_range,prior_ref,prior_bars,prefix,
            source,setup,observation_at
        )
        score,reasons=quality._quality_score(state,setup)
        outcome=protection._simulate_single_structural_trail(
            day_bars,
            setup,
            required_confirmations=(1 if score<5 else None),
        )
        statuses[f"rearm-{outcome['status']}"]+=1
        if outcome.get("status")!="terminal":
            continue
        row=dict(outcome)
        row.update({
            "local_date":local_day.isoformat(),
            "rearm_quality_score":score,
            "rearm_quality_reasons":list(reasons),
            "first_tier":first_row["tier"],
            "first_exit_reason":first_row.get("exit_reason"),
        })
        terminal_rearms.append(row)

    variants={}
    for name,predicate in ADMISSIONS.items():
        admitted=[
            row for row in terminal_rearms
            if predicate(int(cast(int,row["rearm_quality_score"])))
        ]
        weighted=[
            _weighted(row,score=int(cast(int,row["rearm_quality_score"])))
            for row in admitted
        ]
        combined=sorted(
            [*first_rows,*weighted],
            key=lambda row:cast(str,row["signal_at"])
        )
        metrics=_capital_metrics(combined)
        mc=_mc(combined,variant=name)
        count=len(combined)
        variants[name]={
            "trade_count":count,
            "base_trade_count":len(first_rows),
            "rearm_trade_count":len(weighted),
            "metrics":metrics,
            "monte_carlo":mc,
            "objectives":{
                "density_300_350":300<=count<=350,
                "pf_ge_2":(
                    metrics["profit_factor"] is not None
                    and Decimal(cast(str,metrics["profit_factor"]))>=Decimal("2")
                ),
                "dd_le_10":Decimal(cast(str,metrics["max_drawdown_r"]))<=Decimal("10"),
                "dd_le_5":Decimal(cast(str,metrics["max_drawdown_r"]))<=Decimal("5"),
                "mc_positive_ge_0_90":Decimal(
                    cast(str,mc["positive_terminal_probability"])
                )>=Decimal("0.90"),
                "mc_p95_dd_le_15":Decimal(
                    cast(str,mc["p95_max_drawdown_r"])
                )<=Decimal("15"),
            },
        }

    return {
        "schema":SCHEMA,
        "identity":IDENTITY,
        "market":MARKET,
        "partition":partition,
        "base_trade_count":len(first_rows),
        "terminal_rearm_pool":len(terminal_rearms),
        "variants":variants,
        "status_counts":dict(sorted(statuses.items())),
        "evidence":{
            "account_fingerprint":account,
            "evidence_fingerprint":evidence,
            "evidence_software_sha":evidence_sha,
            "checked_at":checked.astimezone(UTC).isoformat(),
            "provider_symbol_name":provider,
        },
        "governance":{
            "admission_uses_terminal_outcome":False,
            "admission_uses_fold_identity":False,
            "admission_uses_target_trade_count":False,
            "admission_uses_future_bars":False,
            "quality_score_is_pre_entry":True,
            "consumed_evidence_only":True,
            "policy_promoted":False,
            "opens_new_holdout":False,
            "live_authorized":False,
            "production_authorized":False,
        },
    }


def main() -> None:
    parser=argparse.ArgumentParser()
    parser.add_argument("evidence",type=Path)
    parser.add_argument("--partition",required=True)
    parser.add_argument("--output",required=True,type=Path)
    args=parser.parse_args()
    p=replay(args.evidence,partition=args.partition)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(p,sort_keys=True,indent=2)+"\n")
    print(json.dumps({
        "partition":p["partition"],
        "base_trade_count":p["base_trade_count"],
        "terminal_rearm_pool":p["terminal_rearm_pool"],
        "variants":p["variants"],
    },sort_keys=True))


if __name__=="__main__":
    main()
