#!/usr/bin/env python3
"""VT31 M3 intermediate swing SOURCE GEOMETRY hierarchy; NOT authorial MSS.

TTrades describes intermediate swing as a short-term swing with short-term
swings of the same kind to its left and right. Strict relative extremum
and selecting M1 short-term are explicitly QORE conservative policies.
Never invent displacement, protected swing, causative stop or orders.
"""
from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import time
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from pathlib import Path

from qore.infrastructure.traders.vt31_ict_cleanroom.contracts import M1Bar, Side
from scripts.vt31_m3_mss_structural_close_v4_20261015 import (
    audit_day as audit_v4_day,
)
from scripts.vt31_m3_source_first_cisd_cognition_v3_20261015 import (
    TTradesAmSourceFirstCognitionV3,
)
from scripts.vt31_m4_m5_author_semantics_bridge_20261015 import short_term_swings
from scripts.vt31_ttrades_am_method_m1_census_20261014 import (
    M1_TOTAL,
    MARKET_SHA,
    collect_hours,
    hash_file,
    market_rows,
    run_census,
)

PREREG = "54f5985ce174d3bcf8614d15ac33bc5201c882c0"
SCHEMA = "VT31_M3_V5_INTERMEDIATE_SWING_SOURCE_GEOMETRY_QORE_TIEBREAK_NO_MSS"
SOURCE_STATES = {
    "MSS_ATTESTED_CONTEXT_ONLY": 128,
    "FIRST_RETURN_NO_QORE_MSS": 483,
    "SWEEP_NO_RETURN": 92,
    "NO_SWEEP": 65,
    "INCOMPLETE_M1_HOURS": 6,
    "REJECTED_SOURCE": 1,
}
V4_STATES = {
    "SINGLE_CONFIRMED_SWING_CLOSE_COMPONENT_ONLY": 96,
    "MULTIPLE_MSS_SWING_REFERENCE_UNKNOWN": 318,
    "NO_ATTESTED_STRUCTURAL_CLOSE_COMPONENT": 69,
}
_GROUPS: dict | None = None


@dataclass(frozen=True, slots=True)
class IntermediateSwingCognitiveEvidence:
    state: str
    as_of: datetime
    candidate_short_term_same_kind_count: int
    confirmed_intermediate_geometries: int
    freshly_crossed_intermediate_geometries: int
    single_candidate_confirmed_at: datetime | None = None
    displacement_author_certified: bool = False
    author_protected_swing_identity_certified: bool = False


def intermediate_swing_source_geometry(
    ten_prefix: tuple[M1Bar, ...],
    *,
    side: Side,
    first_return_at: datetime,
    as_of: datetime,
) -> IntermediateSwingCognitiveEvidence:
    """Check triple short-term swing geometry without retrospective pivots.

    A *right* short-term swing is itself confirmed one M1 after its pivot;
    its confirmed_at must be strictly BEFORE the current break's close.
    """
    if (
        as_of.tzinfo is None or as_of.utcoffset() is None
        or first_return_at.tzinfo is None
        or first_return_at.utcoffset() is None
    ):
        raise ValueError("INTERMEDIATE_MSS_REQUIRES_AWARE_TIME")
    if not ten_prefix or ten_prefix[-1].closed_at != as_of:
        raise ValueError("INTERMEDIATE_MSS_ASOF_NOT_CLOSED_M1")
    if any(
        x.closed_at-x.opened_at != timedelta(minutes=1)
        or x.opened_at.tzinfo is None
        or x.closed_at.tzinfo is None
        or x.opened_at.utcoffset() is None
        or x.closed_at.utcoffset() is None
        for x in ten_prefix
    ):
        raise ValueError("INTERMEDIATE_MSS_BAD_M1_SOURCE")
    if any(
        a.closed_at != b.opened_at
        for a,b in zip(ten_prefix,ten_prefix[1:],strict=False)
    ):
        raise ValueError("INTERMEDIATE_MSS_SOURCE_GAP")
    if len(ten_prefix) < 8 or first_return_at >= as_of:
        return IntermediateSwingCognitiveEvidence(
            "NO_INTERMEDIATE_CONFIRMED_AT_CAUSAL_ASOF",as_of,0,0,0,
        )
    previous,current=ten_prefix[-2:]
    kind="HIGH" if side is Side.LONG else "LOW"
    shorts=tuple(
        s for s in short_term_swings(ten_prefix)
        if s.kind==kind and s.confirmed_at < as_of
    )
    intermediates=[]
    for left,center,right in zip(shorts,shorts[1:],shorts[2:],strict=False):
        if (
            center.pivot_closed_at < first_return_at
            or not (left.confirmed_at < center.confirmed_at < right.confirmed_at)
        ):
            continue
        strict_extreme=(
            center.extremum > left.extremum
            and center.extremum > right.extremum
            if side is Side.LONG else
            center.extremum < left.extremum
            and center.extremum < right.extremum
        )
        if strict_extreme:
            intermediates.append((center,right))
    newly_crossed=[
        pair for pair in intermediates
        if (
            previous.close <= pair[0].extremum < current.close
            if side is Side.LONG else
            previous.close >= pair[0].extremum > current.close
        )
    ]
    if len(newly_crossed)==1:
        return IntermediateSwingCognitiveEvidence(
            "SINGLE_SOURCE_INTERMEDIATE_GEOMETRY_COMPONENT_ONLY",
            as_of,len(shorts),len(intermediates),1,
            newly_crossed[0][1].confirmed_at,
        )
    if len(newly_crossed)>1:
        return IntermediateSwingCognitiveEvidence(
            "MULTIPLE_INTERMEDIATE_PIVOTS_UNKNOWN",
            as_of,len(shorts),len(intermediates),len(newly_crossed),
        )
    return IntermediateSwingCognitiveEvidence(
        "NO_INTERMEDIATE_CONFIRMED_AT_CAUSAL_ASOF",
        as_of,len(shorts),len(intermediates),0,
    )


def audit_day(
    *,day:str,nine:tuple[M1Bar,...],ten:tuple[M1Bar,...],
    return_at:datetime,
) -> dict[str,object]:
    old=audit_v4_day(day=day,nine=nine,ten=ten,return_at=return_at)
    state=old["m3_component_classification"]
    result={
        "ny_day":day,
        "v4_original_source_class":state,
        "first_return_at":return_at.astimezone(UTC).isoformat(),
        "first_v4_ambiguous_at":old["first_ambiguous_multi_swing_at"],
        "v5_intermediate_source_geometry":"NOT_IN_318_AMBIGUOUS_SCOPE",
        "v5_right_short_term_source_confirmed_at":None,
        "v5_short_term_candidate_count":0,
        "v5_intermediate_geometry_count":0,
        "v5_fresh_intermediate_break_count":0,
        "method_certified":False,
        "cognition_certified":False,
        "trader_certified":False,
        "orders_sizing_fills":0,
    }
    if state!="MULTIPLE_MSS_SWING_REFERENCE_UNKNOWN":
        return result
    at_str=old["first_ambiguous_multi_swing_at"]
    if not at_str:
        raise AssertionError("AMBIGUOUS_SOURCE_CASE_MISSING_FIRST_ASOF")
    at=datetime.fromisoformat(at_str).astimezone(UTC)
    prefix=tuple(x for x in ten if x.closed_at<=at)
    if not prefix or prefix[-1].closed_at!=at:
        raise AssertionError("FUTURE_OR_GAPPED_INTERMEDIATE_SOURCE_CLOCK")
    # Ask the ACTUAL already-source-backed V3 for first raid/return and bias.
    source=TTradesAmSourceFirstCognitionV3()
    for bar in nine:
        source.observe_closed_m1(bar)
    for bar in prefix:
        source.observe_closed_m1(bar)
    snap=source.snapshot()
    if snap.bias not in ("LONG","SHORT") or snap.first_return_at!=return_at:
        raise AssertionError("COG_V3_SOURCE_SWING_IDENTITY_UNAVAILABLE")
    x=intermediate_swing_source_geometry(
        prefix,side=Side(snap.bias),first_return_at=return_at,as_of=at,
    )
    result.update({
        "v5_intermediate_source_geometry":x.state,
        "v5_right_short_term_source_confirmed_at":(
            x.single_candidate_confirmed_at.isoformat()
            if x.single_candidate_confirmed_at else None
        ),
        "v5_short_term_candidate_count":x.candidate_short_term_same_kind_count,
        "v5_intermediate_geometry_count":x.confirmed_intermediate_geometries,
        "v5_fresh_intermediate_break_count":x.freshly_crossed_intermediate_geometries,
    })
    return result


def _worker(items:list[tuple[str,datetime]]) -> list[dict[str,object]]:
    if _GROUPS is None:
        raise ValueError("INTERMEDIATE_SOURCE_NOT_PRELOADED_ULTRAFAST")
    return [
        audit_day(day=day,nine=_GROUPS[day][9],ten=_GROUPS[day][10],
                  return_at=at)
        for day,at in items
    ]


def _digest(records:list[dict[str,object]]) -> str:
    return sha256(json.dumps(
        records,sort_keys=True,separators=(",",":"),allow_nan=False,
    ).encode("utf-8")).hexdigest()


def audit_real_m1(market:Path,*,parity:bool=True) -> dict[str,object]:
    global _GROUPS  # noqa: PLW0603
    if hash_file(market)!=MARKET_SHA:
        raise ValueError("ORIGINAL_M1_SHA_NOT_VERIFIED")
    start=time.monotonic()
    groups,total=collect_hours(market_rows(market))
    if total!=M1_TOTAL:
        raise AssertionError("M1_COUNT_DIFFERS_FROM_FROZEN_DATA")
    census=run_census(groups)
    if census["observed_days_total"]!=775 or census["state_counts"]!=SOURCE_STATES:
        raise AssertionError("FROZEN_CENSUS_CHANGED")
    tasks=[
        (x["ny_day"],datetime.fromisoformat(x["as_of"]).astimezone(UTC))
        for x in census["source_classifications"]
        if x["classification"]=="FIRST_RETURN_NO_QORE_MSS"
    ]
    if len(tasks)!=483 or len({x[0] for x in tasks})!=483:
        raise AssertionError("FROZEN_SOURCE_483_CHANGED")
    _GROUPS=groups
    load_s=time.monotonic()-start
    reference=None
    scalar_s=None
    if parity:
        start=time.monotonic()
        reference=sorted(_worker(tasks),key=lambda x:x["ny_day"])
        scalar_s=time.monotonic()-start
    start=time.monotonic()
    with mp.get_context("fork").Pool(processes=2) as pool:
        parts=pool.map(_worker,[tasks[::2],tasks[1::2]])
    fast=sorted([x for part in parts for x in part],key=lambda x:x["ny_day"])
    batch_s=time.monotonic()-start
    if len(fast)!=483 or (parity and (reference is None or _digest(reference)!=_digest(fast))):
        raise AssertionError("SCALAR_ULTRAFAST_FULL_COG_CASEBOOK_CHANGED")
    originals=Counter(x["v4_original_source_class"] for x in fast)
    new=Counter(x["v5_intermediate_source_geometry"] for x in fast)
    if originals!=V4_STATES or sum(new.values())!=483:
        raise AssertionError("SOURCE_SHORT_TERM_V4_MUST_NOT_BE_RECLASSIFIED")
    if new["NOT_IN_318_AMBIGUOUS_SCOPE"]!=165:
        raise AssertionError("INTERMEDIATE_318_CASE_SCOPE_CHANGED")
    if any(x["method_certified"] or x["orders_sizing_fills"] for x in fast):
        raise AssertionError("INTERMEDIATE_GEOMETRY_CANNOT_AUTHORIZE_TRADING")
    samples={}
    for x in fast:
        samples.setdefault(x["v5_intermediate_source_geometry"],x["ny_day"])
    return {
        "schema":SCHEMA,
        "prereg_before_code_sha":PREREG,
        "NAS100_M1_sha256":MARKET_SHA,
        "NAS100_M1_bars":total,
        "frozen_days":775,
        "frozen_source_first_return_contexts":len(tasks),
        "unchanged_V4_short_term_categories":dict(sorted(originals.items())),
        "V5_intermediate_source_geometries_not_MSS":dict(sorted(new.items())),
        "first_real_source_day_per_class":samples,
        "all_483_source_cognitive_cases":fast,
        "full_casebook_sha256":_digest(fast),
        "scalar_ultrafast_full_casebook_parity":parity,
        "timings_wall_seconds_not_PnL":{
            "market_source_load_census":round(load_s,6),
            "scalar":round(scalar_s,6) if scalar_s is not None else None,
            "ultrafast_two_fork":round(batch_s,6),
        },
        "intermediate_strict_extremum_is_QORE_policy":True,
        "author_displacement_MSS_certified":False,
        "protected_swing_causation_certified":False,
        "M4_author_entries_certified":False,
        "M5_causative_stop_certified":False,
        "M6_dual_signers_verified":False,
        "methodology_certified":False,
        "cognition_certified":False,
        "trader_certified":False,
        "broker_fills_or_orders":0,
        "sizing_PnL_computed":False,
        "live_authorized":False,
    }


def main() -> None:
    p=argparse.ArgumentParser()
    p.add_argument("--market",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--parity",action="store_true")
    a=p.parse_args()
    report=audit_real_m1(a.market,parity=a.parity)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(report,sort_keys=True,indent=2)+"\n")
    print(json.dumps({
        "cases":report["frozen_source_first_return_contexts"],
        "V4_prior":report["unchanged_V4_short_term_categories"],
        "V5_hierarchy":report["V5_intermediate_source_geometries_not_MSS"],
        "parity":report["scalar_ultrafast_full_casebook_parity"],
        "full_sha":report["full_casebook_sha256"],
        "times":report["timings_wall_seconds_not_PnL"],
        "trader_certified":False,
    },sort_keys=True))


if __name__=="__main__":
    main()
