#!/usr/bin/env python3
"""VT31 COG V3: source-first CISD with persistent WAIT and causal revocation.

Compose original V2 real H1 09 source and independently derived TTrades
FIRST-OPPOSING-CANDLE OPEN, never latest-only QORE fake author confirmation.
NO CognitiveDecision, fills, stops, sizing or signal authority.
"""
from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import time
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from zoneinfo import ZoneInfo

from qore.infrastructure.traders.vt31_ict_cleanroom.contracts import (
    M1Bar,
    Side,
)
from scripts.vt31_m3_cisd_first_series_source_witness_20261015 import (
    ACTIVE,
    EXPECTED,
    FirstSeriesCisd,
    audit_real_day,
    first_series_cisd,
)
from scripts.vt31_m3_ttrades_cog_wait_v2_20261015 import (
    TTradesAmWaitCognitionV2,
)
from scripts.vt31_ttrades_am_method_m1_census_20261014 import (
    M1_TOTAL,
    MARKET_SHA,
    collect_hours,
    hash_file,
    market_rows,
    run_census,
)

NY = ZoneInfo("America/New_York")
PREREG = "3e9400c4e46abafc212cbdffe0ae9cc17c4633b7"
IDENTITY = "VT31_TTRADES_NY_AM_COG_V3_FIRST_SERIES_STATEFUL_RESEARCH"
_GROUPS: dict[str, dict[int, tuple[M1Bar, ...]]] | None = None


@dataclass(frozen=True, slots=True)
class SourceFirstCognitiveSnapshot:
    state: str
    as_of: datetime
    original_v2_state: str
    first_sweep_at: datetime | None
    first_return_at: datetime | None
    bias: str | None
    first_author_cisd_at: datetime | None
    first_author_series_length: int | None
    first_legacy_last_only_at: datetime | None
    first_legacy_last_only_series_length: int | None
    author_events_observed: int
    legacy_last_only_events_observed: int
    was_target_consumed: bool
    method_profile: str = "TTRADES_NY_AM_2025"
    author_first_open_component_not_full_mss_or_ob: bool = True
    cognitive_decision_emitted: bool = False
    author_entry_ready: bool = False
    stop_assigned: bool = False
    lot_sizing: bool = False
    trader_certified: bool = False


class TTradesAmSourceFirstCognitionV3:
    """One NY date, real source-state + first-open CISD event ledger."""

    def __init__(self) -> None:
        self._source = TTradesAmWaitCognitionV2()
        self._nine: list[M1Bar] = []
        self._ten: list[M1Bar] = []
        self._first: FirstSeriesCisd | None = None
        self._last_only: FirstSeriesCisd | None = None
        self._first_events = 0
        self._last_events = 0
        self._consumed = False
        self._uncertain_gap = False
        self._last_state = "WAIT_FOR_09H_CONTEXT"
        self._snapshot: SourceFirstCognitiveSnapshot | None = None
        self._origin: tuple[datetime, datetime, str] | None = None

    def observe_closed_m1(self, bar: M1Bar) -> SourceFirstCognitiveSnapshot:
        source = self._source.observe_closed_m1(bar)
        if source.as_of is None:
            raise AssertionError("ORIGINAL_V2_FAILED_TO_TRACK_CLOSED_M1")
        hour = bar.opened_at.astimezone(NY).hour
        if hour == 9:
            self._nine.append(bar)
            state = "WAIT_FOR_09H_CONTEXT"
        else:
            self._ten.append(bar)
            state = self._observe_ten(source)
        self._last_state = state
        self._snapshot = SourceFirstCognitiveSnapshot(
            state=state,
            as_of=source.as_of,
            original_v2_state=source.state,
            first_sweep_at=source.first_sweep_at,
            first_return_at=source.first_return_at,
            bias=source.bias,
            first_author_cisd_at=(
                self._first.confirmed_at if self._first else None
            ),
            first_author_series_length=(
                self._first.opposing_series_length if self._first else None
            ),
            first_legacy_last_only_at=(
                self._last_only.confirmed_at if self._last_only else None
            ),
            first_legacy_last_only_series_length=(
                self._last_only.opposing_series_length if self._last_only else None
            ),
            author_events_observed=self._first_events,
            legacy_last_only_events_observed=self._last_events,
            was_target_consumed=self._consumed,
        )
        return self._snapshot

    def _observe_ten(self, source) -> str:
        if source.state == "INVALIDATED_OPPOSITE_RAID":
            return "INVALIDATED_OPPOSITE_RAID"
        if source.as_of.astimezone(NY).hour == 11:
            return "EXPIRED_11_NY"
        if self._uncertain_gap:
            return "UNKNOWN_SOURCE_GAP"
        if source.bias not in ("LONG", "SHORT") or source.first_return_at is None:
            if source.state in ("WAIT_FOR_SWEEP", "AWAIT_SWEEP"):
                return "WAIT_FOR_SWEEP"
            if source.state in ("WAIT_FOR_RETURN", "AWAIT_RETURN"):
                return "WAIT_FOR_RETURN"
            return "WAIT_FOR_VALID_SOURCE_CONTEXT"
        if source.first_sweep_at is None:
            return "UNKNOWN_ORIGINAL_SOURCE_WITNESS"
        current_origin=(source.first_sweep_at,source.first_return_at,source.bias)
        if self._origin is None:
            self._origin=current_origin
        elif current_origin!=self._origin:
            raise AssertionError("SOURCE_FIRST_RAID_RETURN_BIAS_MUTATED")
        side=Side(source.bias)
        target=(
            max(x.high for x in self._nine)
            if side is Side.LONG else min(x.low for x in self._nine)
        )
        now=self._ten[-1]
        if (now.high >= target if side is Side.LONG else now.low <= target):
            self._consumed=True
        if self._consumed:
            return "TARGET_CONSUMED_NO_FRESH_INTENT"
        if source.state not in ACTIVE or source.as_of <= source.first_return_at:
            return (
                "AUTHOR_FIRST_OPEN_CISD_COMPONENT_MSS_UNVERIFIED"
                if self._first is not None else "WAIT_FOR_FIRST_OPEN_CISD"
            )
        try:
            found=first_series_cisd(
                tuple(self._ten),side=side,
                first_sweep_at=source.first_sweep_at,
                as_of=source.as_of,
            )
        except ValueError as exc:
            if str(exc) not in (
                "MISSING_M1_OR_OVERLAPPING_SOURCE",
                "CLOSED_ONE_MINUTE_AWARE_SOURCE_REQUIRED",
            ):
                raise
            self._uncertain_gap=True
            return "UNKNOWN_SOURCE_GAP"
        if found is not None:
            if found.first_candle_open_crossed:
                self._first_events+=1
                if self._first is None:
                    self._first=found
            if found.last_candle_open_crossed and not found.first_candle_open_crossed:
                self._last_events+=1
                if self._last_only is None:
                    self._last_only=found
        if self._first is not None:
            return "AUTHOR_FIRST_OPEN_CISD_COMPONENT_MSS_UNVERIFIED"
        if self._last_only is not None:
            return "QORE_LAST_OPEN_PREMATURE_WAIT"
        return "WAIT_FOR_FIRST_OPEN_CISD"

    def snapshot(self) -> SourceFirstCognitiveSnapshot:
        if self._snapshot is None:
            raise ValueError("NO_CLOSED_M1_OBSERVED")
        return self._snapshot


def audit_v3_day(
    *, day: str, nine: tuple[M1Bar, ...], ten: tuple[M1Bar, ...],
    first_return_at: datetime,
) -> dict[str, object]:
    v3=TTradesAmSourceFirstCognitionV3()
    for b in nine:
        v3.observe_closed_m1(b)
    for b in ten:
        v3.observe_closed_m1(b)
    end=v3.snapshot()
    oracle=audit_real_day(
        day=day,nine=nine,ten=ten,first_return_at=first_return_at,
    )
    author=(end.first_author_cisd_at.isoformat()
            if end.first_author_cisd_at else None)
    legacy=(end.first_legacy_last_only_at.isoformat()
            if end.first_legacy_last_only_at else None)
    if (
        author != oracle["author_first_series_close_at"]
        or legacy != oracle["first_last_only_false_promotion_at"]
        or end.author_events_observed != oracle["author_first_series_events"]
        or end.legacy_last_only_events_observed != oracle[
            "legacy_last_only_false_events"
        ]
    ):
        raise AssertionError("COGNITIVE_V3_VS_AUTHOR_FIRST_SERIES_ORACLE_DIVERGED")
    return {
        "ny_day":day,
        "first_return_at":first_return_at.astimezone(UTC).isoformat(),
        "oracle_state":oracle["first_series_cisd_component_state"],
        "v3_first_author_cisd_at":author,
        "v3_first_qore_last_only_at":legacy,
        "v3_first_author_cisd_series_length":end.first_author_series_length,
        "v3_final_state":end.state,
        "v3_original_source_end_state":end.original_v2_state,
        "v3_author_cisd_events":end.author_events_observed,
        "v3_last_only_false_events":end.legacy_last_only_events_observed,
        "v3_target_consumed":end.was_target_consumed,
        "v3_source_profile":end.method_profile,
        "v3_cognitive_decision_emitted":False,
        "v3_author_method_certified":False,
        "v3_cognitive_certified":False,
        "trader_certified":False,
        "orders_sizing_economics":0,
    }


def _batch(records: list[tuple[str, datetime]]) -> list[dict[str, object]]:
    if _GROUPS is None:
        raise ValueError("COG_V3_ULTRAFAST_SHARED_SOURCE_REQUIRED")
    return [
        audit_v3_day(
            day=day,nine=_GROUPS[day][9],ten=_GROUPS[day][10],
            first_return_at=at,
        )
        for day,at in records
    ]


def full_sha(data: list[dict[str, object]]) -> str:
    return sha256(json.dumps(
        data,sort_keys=True,separators=(",",":"),allow_nan=False,
    ).encode("utf-8")).hexdigest()


def run_real_m1(market: Path, *, parity: bool=True) -> dict[str, object]:
    global _GROUPS  # noqa: PLW0603
    if hash_file(market) != MARKET_SHA:
        raise ValueError("VT31_ORIGINAL_M1_MARKET_SHA_MISMATCH")
    start=time.monotonic()
    groups,n=collect_hours(market_rows(market))
    if n != M1_TOTAL:
        raise AssertionError("VT31_ORIGINAL_BAR_COUNT_DRIFT")
    census=run_census(groups)
    if census["observed_days_total"] != 775 or census["state_counts"] != EXPECTED:
        raise AssertionError("SOURCE_FROZEN_CENSUS_CHANGED")
    rows=[
        (x["ny_day"],datetime.fromisoformat(x["as_of"]).astimezone(UTC))
        for x in census["source_classifications"]
        if x["classification"]=="FIRST_RETURN_NO_QORE_MSS"
    ]
    if len(rows)!=483:
        raise AssertionError("FROZEN_FIRST_RETURN_DENOMINATOR_CHANGED")
    _GROUPS=groups
    load_s=time.monotonic()-start
    baseline=None
    scalar_s=None
    if parity:
        start=time.monotonic()
        baseline=sorted(_batch(rows),key=lambda x:x["ny_day"])
        scalar_s=time.monotonic()-start
    start=time.monotonic()
    with mp.get_context("fork").Pool(processes=2) as pool:
        runs=pool.map(_batch,[rows[::2],rows[1::2]])
    output=sorted([x for xs in runs for x in xs],key=lambda x:x["ny_day"])
    batch_s=time.monotonic()-start
    if len(output)!=483:
        raise AssertionError("COG_V3_MISSING_CASES")
    digest=full_sha(output)
    if parity and (baseline is None or full_sha(baseline)!=digest):
        raise AssertionError("ULTRAFAST_COG_V3_SCALAR_PARITY_BREAK")
    statuses=Counter(x["oracle_state"] for x in output)
    final=Counter(x["v3_final_state"] for x in output)
    if statuses!={"AUTHOR_FIRST_SERIES_CLOSE_COMPONENT":441,
                 "LEGACY_LAST_ONLY_FALSE_PROMOTION":22,
                 "NO_SOURCE_FIRST_SERIES_CLOSE_OBSERVED":20}:
        raise AssertionError("FIRST_CISD_AUTHOR_CASEBOOK_968_DRIFT")
    if any(x["v3_cognitive_decision_emitted"] or x["trader_certified"] for x in output):
        raise AssertionError("READ_ONLY_COG_RESEARCH_GENERATED_CERTIFICATION")
    return {
        "schema":IDENTITY,
        "prereg_commit":PREREG,
        "source_original_M1_sha256":MARKET_SHA,
        "source_original_M1_count":n,
        "frozen_contexts":len(rows),
        "frozen_days":775,
        "cognitive_v3_per_case_matches_first_series_oracle_968":True,
        "scalar_ultrafast_full_casebook_SHA_match":parity,
        "full_casebook_sha256":digest,
        "first_series_source_components":dict(sorted(statuses.items())),
        "end_of_session_cognitive_revocation_states":dict(sorted(final.items())),
        "all_483_original_source_cognitive_states":output,
        "timings_wall_seconds":{
            "load_once_census":round(load_s,6),
            "scalar":round(scalar_s,6) if scalar_s is not None else None,
            "ultrafast_two_workers":round(batch_s,6),
        },
        "source_data_development_NOT_OOS":True,
        "G3_original_not_mutated":True,
        "M3_author_full_method_certified":False,
        "M3_cognition_runtime_certified":False,
        "M4_author_full_entry_certified":False,
        "M5_causative_swing_certified":False,
        "M6_two_independent_signatures":False,
        "trader_certified":False,
        "orders_ack_fills":0,
        "vt31_sizing":False,
        "live_authorized":False,
    }


def main() -> None:
    p=argparse.ArgumentParser()
    p.add_argument("--market",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--parity",action="store_true")
    args=p.parse_args()
    summary=run_real_m1(args.market,parity=args.parity)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(summary,sort_keys=True,indent=2)+"\n")
    print(json.dumps({
        "cases":summary["frozen_contexts"],
        "components":summary["first_series_source_components"],
        "v3_final_states":summary["end_of_session_cognitive_revocation_states"],
        "full_sha":summary["full_casebook_sha256"],
        "scalar_ultrafast_parity":summary["scalar_ultrafast_full_casebook_SHA_match"],
        "timings":summary["timings_wall_seconds"],
        "trader_certified":False,
    },sort_keys=True))


if __name__=="__main__":
    main()
