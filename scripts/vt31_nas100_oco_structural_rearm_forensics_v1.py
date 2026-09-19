"""VT31 NAS100 OCO structural-rearm forensics V1.

Consumed-evidence research only.

The high-density OCO universe already reaches roughly 328/299/257 terminal
trades on R5/R6/R8. This lab asks whether a genuine second source event after
the first OCO trade closes can recover the remaining density, especially in the
adversarial fold, without reusing the first source.

Groups are defined only with information available by the second decision:
- second-event decision-time market state;
- second-event entry family / side;
- previous trade exit reason and realized R (already known after its exit);
- side flip and elapsed minutes since previous exit.

The second-event terminal outcome is attached only after group formation and
is never a runtime input.
"""
# ruff: noqa: B009
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_nas100_entry_intelligence_oco_lab_v1 as oco
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

SCHEMA="qore.vt31.nas100.oco_structural_rearm_forensics.v1"
MARKET="NAS100"
FRICTION=Decimal("0.05")


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _bucket_minutes(minutes: int) -> str:
    if minutes <= 5:
        return "0-5m"
    if minutes <= 10:
        return "6-10m"
    if minutes <= 20:
        return "11-20m"
    return "21m-plus"


def _previous_result_bucket(value: object) -> str:
    r=_d(value)-FRICTION
    if r < Decimal("-0.50"):
        return "LOSS"
    if r <= Decimal("0.25"):
        return "FLAT_OR_SMALL"
    if r < Decimal("1.50"):
        return "WIN_LT_1_5R"
    return "WIN_GE_1_5R"


def _summary(rows: list[dict[str, object]]) -> dict[str, object]:
    return _metrics(rows, friction=FRICTION)


def replay(evidence_path: Path, *, partition: str) -> dict[str, object]:
    series,account,evidence,checked,evidence_sha,provider=load_market_evidence(
        evidence_path
    )
    if not series or getattr(series[0],"instrument").symbol != MARKET:
        raise ValueError("OCO rearm forensics requires NAS100 evidence")

    raw: dict[date,list[object]]=defaultdict(list)
    for bar in series:
        raw[_day(getattr(bar,"opened_at"))].append(bar)
    by_day={
        local_day:tuple(sorted(items,key=lambda item:getattr(item,"opened_at")))
        for local_day,items in raw.items()
    }
    context_by_day=specialist._context_map(by_day)
    policy=Vt31R22ExecutionPolicy()
    status: Counter[str]=Counter()
    first_rows: list[dict[str,object]]=[]
    second_rows: list[dict[str,object]]=[]

    for local_day in sorted(by_day):
        day_bars=by_day[local_day]
        reference=specialist._slice(day_bars,(9,0,0),(10,0,0))
        session=specialist._slice(day_bars,(10,0,0),(11,0,0))
        if len(reference)!=60 or len(session)!=60:
            status["incomplete-day"]+=1
            continue

        timeline=oco._timeline(day_bars,evidence_fingerprint=evidence)
        if timeline is None:
            status["no-oco-source"]+=1
            continue
        first_setup,selection_status=oco._select_oco(
            day_bars,timeline,policy
        )
        status[f"oco-{selection_status}"]+=1
        if first_setup is None:
            continue
        first_outcome=specialist.baseline._simulate(day_bars,first_setup)
        status[f"first-{first_outcome['status']}"]+=1
        if first_outcome.get("status")!="terminal":
            continue

        first_row=dict(first_outcome)
        first_row.update({
            "partition":partition,
            "local_date":local_day.isoformat(),
            "entry_family":first_setup.selected_family.value,
            "side":first_setup.side.value,
        })
        first_rows.append(first_row)

        first_exit=datetime.fromisoformat(cast(str,first_outcome["exit_at"]))
        if _wall(first_exit)>=(11,0,0):
            status["first-exit-after-source-window"]+=1
            continue

        second_selected=frontier._next_executable_after(
            reference=reference,
            session=session,
            after_at=first_exit,
            evidence=evidence,
            policy=policy,
        )
        if second_selected is None:
            status["no-second-event"]+=1
            continue
        second_source,second_setup=second_selected
        if not structurally_rearmed(
            protected_exit_at_epoch=int(first_exit.timestamp()),
            new_raid_at_epoch=int(second_source.structure.raid_at.timestamp()),
            new_confirmation_at_epoch=int(
                second_source.structure.confirmation_at.timestamp()
            ),
            new_decision_at_epoch=int(second_setup.decision_at.timestamp()),
        ):
            status["rearm-invariant-failed"]+=1
            continue

        (
            previous_path_range,
            prior_ref_median,
            prior_admitted_day_bars,
        )=context_by_day[local_day]
        observation_at=second_setup.decision_at
        session_prefix=tuple(
            bar for bar in session
            if cast(datetime,getattr(bar,"closed_at"))<=observation_at
        )
        state=specialist._state_snapshot(
            day_bars,
            previous_path_range,
            prior_ref_median,
            prior_admitted_day_bars,
            session_prefix,
            second_source,
            second_setup,
            observation_at,
        )
        score,reasons=quality._quality_score(state,second_setup)

        second_outcome=specialist.baseline._simulate(day_bars,second_setup)
        status[f"second-{second_outcome['status']}"]+=1
        if second_outcome.get("status")!="terminal":
            continue

        elapsed=int(
            (second_setup.decision_at-first_exit).total_seconds()//60
        )
        previous_bucket=_previous_result_bucket(first_outcome["r_multiple"])
        row=dict(second_outcome)
        row.update({
            "partition":partition,
            "local_date":local_day.isoformat(),
            "quality_score":score,
            "quality_reasons":list(reasons),
            "reference_volatility_state":state[
                "reference_volatility_state"
            ],
            "current_path_vs_previous":state["current_path_vs_previous"],
            "h1_state":state["h1_state"],
            "h4_state":state["h4_state"],
            "prior_day_state":state["prior_day_state"],
            "premarket_state":state["premarket_state"],
            "cash_open_state":state["cash_open_state"],
            "last_structure_event_family":state[
                "last_structure_event_family"
            ],
            "reference_reclaim_age_minutes":state[
                "reference_reclaim_age_minutes"
            ],
            "confirmation_latency_minutes":state[
                "confirmation_latency_minutes"
            ],
            "risk_ref":state["risk_ref"],
            "entry_family":second_setup.selected_family.value,
            "side":second_setup.side.value,
            "previous_entry_family":first_setup.selected_family.value,
            "previous_side":first_setup.side.value,
            "previous_exit_reason":first_outcome.get("exit_reason"),
            "previous_r_multiple":first_outcome["r_multiple"],
            "previous_result_bucket":previous_bucket,
            "side_flip":first_setup.side.value!=second_setup.side.value,
            "minutes_after_previous_exit":elapsed,
            "minutes_after_previous_exit_bucket":_bucket_minutes(elapsed),
            "used_for_runtime_decision":False,
        })
        second_rows.append(row)

    first_rows.sort(key=lambda row:cast(str,row["signal_at"]))
    second_rows.sort(key=lambda row:cast(str,row["signal_at"]))

    dimensions=(
        "quality_score",
        "entry_family",
        "side",
        "previous_result_bucket",
        "previous_exit_reason",
        "side_flip",
        "minutes_after_previous_exit_bucket",
        "reference_volatility_state",
        "h1_state",
        "h4_state",
        "cash_open_state",
        "last_structure_event_family",
    )
    by_dimension: dict[str,dict[str,object]]={}
    for dim in dimensions:
        groups: dict[str,list[dict[str,object]]]=defaultdict(list)
        for row in second_rows:
            groups[str(row.get(dim))].append(row)
        by_dimension[dim]={
            key:_summary(values) for key,values in sorted(groups.items())
        }

    interactions={
        "prev_result_x_side_flip":(
            "previous_result_bucket","side_flip"
        ),
        "prev_result_x_family":(
            "previous_result_bucket","entry_family"
        ),
        "prev_exit_x_quality":(
            "previous_exit_reason","quality_score"
        ),
        "volatility_x_family":(
            "reference_volatility_state","entry_family"
        ),
        "structure_x_family":(
            "last_structure_event_family","entry_family"
        ),
        "timing_x_quality":(
            "minutes_after_previous_exit_bucket","quality_score"
        ),
        "h1_x_family":("h1_state","entry_family"),
    }
    by_interaction: dict[str,dict[str,object]]={}
    for name,fields in interactions.items():
        groups=defaultdict(list)
        for row in second_rows:
            key="|".join(f"{field}={row.get(field)}" for field in fields)
            groups[key].append(row)
        by_interaction[name]={
            key:_summary(values) for key,values in sorted(groups.items())
        }

    return {
        "schema":SCHEMA,
        "market":MARKET,
        "partition":partition,
        "evidence":{
            "account_fingerprint":account,
            "evidence_fingerprint":evidence,
            "evidence_software_sha":evidence_sha,
            "checked_at":checked.astimezone(UTC).isoformat(),
            "provider_symbol_name":provider,
        },
        "first_oco_terminal_count":len(first_rows),
        "second_rearm_terminal_count":len(second_rows),
        "combined_capacity_count":len(first_rows)+len(second_rows),
        "first_oco_metrics":_summary(first_rows),
        "second_rearm_metrics":_summary(second_rows),
        "by_dimension":by_dimension,
        "by_interaction":by_interaction,
        "second_rows":second_rows,
        "status_counts":dict(sorted(status.items())),
        "governance":{
            "consumed_evidence_only":True,
            "groups_defined_before_second_terminal_outcome":True,
            "previous_trade_result_is_known_before_rearm_decision":True,
            "second_terminal_pnl_used_at_runtime":False,
            "future_bars_used_to_authorize_rearm":False,
            "fold_identity_used_by_runtime_rule":False,
            "one_trade_max_per_source_event":True,
            "new_raid_confirmation_decision_required":True,
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
        "first_oco_terminal_count":payload["first_oco_terminal_count"],
        "second_rearm_terminal_count":payload["second_rearm_terminal_count"],
        "combined_capacity_count":payload["combined_capacity_count"],
        "first_oco_metrics":payload["first_oco_metrics"],
        "second_rearm_metrics":payload["second_rearm_metrics"],
        "status_counts":payload["status_counts"],
    },sort_keys=True))


if __name__=="__main__":
    main()
