"""Cross-fold causal CORE drawdown forensics for WAIT_1025_B060.

Consumed-evidence research only.

The goal is to explain concentration of 1R CORE drawdown without removing the
high-density SECONDARY/SCOUT opportunity layer. Structural groups are defined
from the decision-time situation model. Terminal outcomes are attached only
after the groups exist and are never runtime inputs.
"""
# ruff: noqa: B009
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

import vt31_nas100_causal_hybrid_replay_v1 as v1
import vt31_nas100_caution_context_decomposition_v1 as caution
import vt31_nas100_specialist_r1_candidate as specialist

from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_5_multi_index_research import (
    _day,
    _metrics,
    _wall,
    load_market_evidence,
)
from qore.infrastructure.traders.vt31_silver_bullet_r2_2 import (
    Vt31R22ExecutionPolicy,
    evaluate_vt31_r2_2_source,
    make_executable_setup,
)

SCHEMA="qore.vt31.nas100.core_drawdown_forensics.v1"
MARKET="NAS100"
WAIT_RELEASE_MINUTE=10*60+25
VARIANT="WAIT_1025_B060"
FRICTION=Decimal("0.05")


def _summary(rows: list[dict[str, object]]) -> dict[str, object]:
    metrics=_metrics(rows, friction=FRICTION)
    losses=sum(
        Decimal(cast(str,row["r_multiple"]))-FRICTION < 0
        for row in rows
    )
    return {
        "metrics":metrics,
        "loss_rate":(
            format(Decimal(losses)/Decimal(len(rows)),"f")
            if rows else None
        ),
    }


def _loss_clusters(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    result: list[dict[str, object]]=[]
    current: list[dict[str, object]]=[]
    for row in rows:
        net=Decimal(cast(str,row["r_multiple"]))-FRICTION
        if net < 0:
            current.append(row)
            continue
        if len(current)>=2:
            result.append(_cluster(current,len(result)+1))
        current=[]
    if len(current)>=2:
        result.append(_cluster(current,len(result)+1))
    return result


def _cluster(
    rows: list[dict[str, object]],
    cluster_id: int,
) -> dict[str, object]:
    nets=[
        Decimal(cast(str,row["r_multiple"]))-FRICTION
        for row in rows
    ]
    return {
        "cluster_id":cluster_id,
        "length":len(rows),
        "start_signal_at":rows[0]["signal_at"],
        "end_signal_at":rows[-1]["signal_at"],
        "net_r":format(sum(nets,Decimal(0)),"f"),
        "side":dict(
            Counter(str(row["side"]) for row in rows).most_common()
        ),
        "entry_family":dict(
            Counter(str(row["entry_family"]) for row in rows).most_common()
        ),
        "reference_volatility_state":dict(
            Counter(
                str(row["reference_volatility_state"])
                for row in rows
            ).most_common()
        ),
        "last_structure_event_family":dict(
            Counter(
                str(row["last_structure_event_family"])
                for row in rows
            ).most_common()
        ),
        "runtime_rule_authorized":False,
    }


def replay(
    evidence_path: Path,
    *,
    partition: str,
) -> dict[str, object]:
    series, account, evidence, checked, evidence_sha, provider=(
        load_market_evidence(evidence_path)
    )
    if not series or getattr(series[0],"instrument").symbol != MARKET:
        raise ValueError("CORE forensics requires NAS100 evidence")

    raw: dict[date,list[object]]=defaultdict(list)
    for bar in series:
        raw[_day(getattr(bar,"opened_at"))].append(bar)
    by_day={
        local_day:tuple(
            sorted(items,key=lambda item:getattr(item,"opened_at"))
        )
        for local_day,items in raw.items()
    }
    context_by_day=specialist._context_map(by_day)
    policy=Vt31R22ExecutionPolicy()
    status: Counter[str]=Counter()
    rows: list[dict[str,object]]=[]

    for local_day in sorted(by_day):
        day_bars=by_day[local_day]
        reference=specialist._slice(day_bars,(9,0,0),(10,0,0))
        session=specialist._slice(day_bars,(10,0,0),(11,0,0))
        if len(reference)!=60 or len(session)!=60:
            status["incomplete-day"]+=1
            continue

        prefix=list(reference)
        (
            previous_path_range,
            prior_ref_median,
            prior_admitted_day_bars,
        )=context_by_day[local_day]
        selected=None
        selected_state: dict[str,object] | None=None
        saw_wait=False

        for bar in session:
            prefix.append(bar)
            closed_at=cast(datetime,getattr(bar,"closed_at"))
            evaluation=evaluate_vt31_r2_2_source(
                instrument=getattr(bar,"instrument"),
                as_of=closed_at,
                m1_candles=cast(Any,tuple(prefix)),
                evidence_fingerprint=evidence,
            )
            if evaluation.setup is None:
                if saw_wait and evaluation.both_sides_swept:
                    status["invalidated-after-wait"]+=1
                    break
                continue
            executable,_=make_executable_setup(evaluation.setup,policy)
            if executable is None:
                status["source-router-secondary"]+=1
                break

            session_prefix=tuple(
                item
                for item in prefix
                if (10,0,0)
                <= _wall(getattr(item,"opened_at"))
                < (11,0,0)
            )
            state=specialist._state_snapshot(
                day_bars,
                previous_path_range,
                prior_ref_median,
                prior_admitted_day_bars,
                session_prefix,
                evaluation.setup,
                executable,
                closed_at,
            )
            action=cast(str,state["action"])
            if action=="WAIT":
                saw_wait=True
                if specialist.baseline._local_minute(bar)>=WAIT_RELEASE_MINUTE:
                    status["released-to-scout"]+=1
                    break
                continue
            if action=="ABSTAIN":
                status["released-to-secondary"]+=1
                break
            if action!="EXECUTE":
                raise ValueError(action)
            selected=v1._activation_setup(executable,closed_at)
            selected_state=state
            break

        if selected is None or selected_state is None:
            continue
        outcome=specialist._simulate_selected_plan(
            day_bars,
            selected,
            selected_state,
        )
        status[f"core-{outcome['status']}"]+=1
        if outcome.get("status")!="terminal":
            continue

        profile=caution._profile(
            selected_state,
            side=selected.side.value,
            entry_family=selected.selected_family.value,
        )
        rows.append({
            **outcome,
            **profile,
            "partition":partition,
            "variant":VARIANT,
            "decision_at":selected.decision_at.astimezone(UTC).isoformat(),
            "target_plan":selected_state["target_plan"],
            "used_for_runtime_decision":False,
        })

    rows.sort(key=lambda row:cast(str,row["signal_at"]))
    by_dimension: dict[str,dict[str,object]]={}
    for dimension in caution.DIMENSIONS:
        grouped: dict[str,list[dict[str,object]]]=defaultdict(list)
        for row in rows:
            grouped[str(row[dimension])].append(row)
        by_dimension[dimension]={
            key:_summary(values)
            for key,values in sorted(grouped.items())
        }

    by_interaction: dict[str,dict[str,object]]={}
    for name,fields in caution.INTERACTIONS.items():
        grouped=defaultdict(list)
        for row in rows:
            key="|".join(f"{field}={row[field]}" for field in fields)
            grouped[key].append(row)
        by_interaction[name]={
            key:_summary(values)
            for key,values in sorted(grouped.items())
        }

    return {
        "schema":SCHEMA,
        "market":MARKET,
        "partition":partition,
        "variant":VARIANT,
        "evidence":{
            "account_fingerprint":account,
            "evidence_fingerprint":evidence,
            "evidence_software_sha":evidence_sha,
            "checked_at":checked.astimezone(UTC).isoformat(),
            "provider_symbol_name":provider,
        },
        "core_terminal_count":len(rows),
        "core_summary":_summary(rows),
        "by_dimension":by_dimension,
        "by_interaction":by_interaction,
        "loss_clusters_min_2":_loss_clusters(rows),
        "status_counts":dict(sorted(status.items())),
        "rows":rows,
        "governance":{
            "groups_defined_without_terminal_pnl":True,
            "future_bars_used_for_grouping":False,
            "terminal_outcomes_evaluation_only":True,
            "loss_clusters_forensics_only":True,
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
    payload=replay(args.evidence,partition=args.partition)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(
        json.dumps(payload,sort_keys=True,indent=2)+"\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "partition":payload["partition"],
        "core_terminal_count":payload["core_terminal_count"],
        "core_summary":payload["core_summary"],
        "loss_cluster_count":len(
            cast(list[object],payload["loss_clusters_min_2"])
        ),
    },sort_keys=True))


if __name__=="__main__":
    main()
