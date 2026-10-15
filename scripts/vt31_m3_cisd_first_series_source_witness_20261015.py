#!/usr/bin/env python3
"""TTrades FIRST opposing-series OPEN CISD source component, 483 real days.

Read-only author semantic witness. Unlike the older QORE latest-opposing-
candle proxy, a multiple-candle CISD requires a close through the FIRST
opposing candle's opening price (TTrades, June 29 2025). CISD != MSS.
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
from typing import Any
from zoneinfo import ZoneInfo

from qore.infrastructure.traders.vt31_ict_cleanroom.contracts import M1Bar, Side
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
PREREG = "a7395df49187aa67a29a98982b72b122fda8ceee"
ACTIVE = frozenset({
    "WAIT_FOR_CONFIRMATION",
    "QORE_PROXY_OBSERVED_AUTHOR_DISPLACEMENT_UNVERIFIED",
})
EXPECTED = {
    "MSS_ATTESTED_CONTEXT_ONLY": 128,
    "FIRST_RETURN_NO_QORE_MSS": 483,
    "SWEEP_NO_RETURN": 92,
    "NO_SWEEP": 65,
    "INCOMPLETE_M1_HOURS": 6,
    "REJECTED_SOURCE": 1,
}
_GROUPS: dict[str, dict[int, tuple[M1Bar, ...]]] | None = None


@dataclass(frozen=True)
class FirstSeriesCisd:
    confirmed_at: datetime
    opposing_series_length: int
    first_candle_open_crossed: bool
    last_candle_open_crossed: bool
    author_component_not_full_ob_or_mss: bool = True


def first_series_cisd(
    closed_m1: tuple[M1Bar, ...],
    *,
    side: Side,
    first_sweep_at: datetime,
    as_of: datetime,
) -> FirstSeriesCisd | None:
    """Evaluate ONLY the most recent contiguous opposing run, as of M1 close.

    The immediate-after-run constraint is conservative QORE operational
    formalization, NOT a claim that every author CISD must confirm one bar
    after a run. Missing it is UNKNOWN, never proof of absence of CISD.
    """
    if (
        first_sweep_at.tzinfo is None or first_sweep_at.utcoffset() is None
        or as_of.tzinfo is None or as_of.utcoffset() is None
    ):
        raise ValueError("AWARE_CLOCK_REQUIRED")
    if not closed_m1:
        return None
    current = closed_m1[-1]
    if current.closed_at != as_of or current.opened_at >= current.closed_at:
        raise ValueError("CLOSED_M1_ASOF_REQUIRED")
    if any(
        bar.opened_at.tzinfo is None or bar.closed_at.tzinfo is None
        or bar.opened_at.utcoffset() is None
        or bar.closed_at.utcoffset() is None
        or bar.closed_at-bar.opened_at != current.closed_at-current.opened_at
        or bar.closed_at-bar.opened_at != timedelta(minutes=1)
        for bar in closed_m1
    ):
        raise ValueError("CLOSED_ONE_MINUTE_AWARE_SOURCE_REQUIRED")
    if any(
        a.closed_at != b.opened_at
        for a,b in zip(closed_m1,closed_m1[1:],strict=False)
    ):
        raise ValueError("MISSING_M1_OR_OVERLAPPING_SOURCE")
    if len(closed_m1) < 2 or first_sweep_at >= current.closed_at:
        return None
    # Current candle must express delivery in the intended direction,
    # not merely have a wick through a possible OB open.
    if side is Side.LONG and not current.close > current.open:
        return None
    if side is Side.SHORT and not current.close < current.open:
        return None
    prior = closed_m1[-2]
    def is_opposite(x: M1Bar) -> bool:
        return x.close < x.open if side is Side.LONG else x.close > x.open
    if not is_opposite(prior) or prior.closed_at < first_sweep_at:
        return None
    j = len(closed_m1)-2
    while j >= 0 and is_opposite(closed_m1[j]):
        if closed_m1[j].closed_at < first_sweep_at:
            break
        j -= 1
    first = closed_m1[j+1]
    last = prior
    if first.opened_at > prior.opened_at:
        raise AssertionError("OPPOSING_SOURCE_SERIES_REVERSED")
    first_cross = (
        current.close > first.open if side is Side.LONG
        else current.close < first.open
    )
    last_cross = (
        current.close > last.open if side is Side.LONG
        else current.close < last.open
    )
    if not first_cross and not last_cross:
        return None
    return FirstSeriesCisd(
        confirmed_at=current.closed_at,
        opposing_series_length=len(closed_m1)-1-(j+1),
        first_candle_open_crossed=first_cross,
        last_candle_open_crossed=last_cross,
    )


def audit_real_day(
    *, day: str, nine: tuple[M1Bar, ...],
    ten: tuple[M1Bar, ...],
    first_return_at: datetime,
) -> dict[str, object]:
    if len(nine) != 60 or len(ten) != 60:
        raise ValueError("FROZEN_FULL_SOURCE_HOURS_REQUIRED")
    engine = TTradesAmWaitCognitionV2()
    for b in nine:
        engine.observe_closed_m1(b)
    first_author: FirstSeriesCisd | None = None
    first_false: FirstSeriesCisd | None = None
    author_events = 0
    false_events = 0
    target_consumed = False
    seen: list[M1Bar] = []
    for b in ten:
        snap = engine.observe_closed_m1(b)
        seen.append(b)
        if snap.first_return_at is None or snap.first_return_at != first_return_at:
            continue
        if snap.bias not in ("LONG", "SHORT"):
            continue
        side = Side(snap.bias)
        target = max(x.high for x in nine) if side is Side.LONG else min(
            x.low for x in nine
        )
        if b.high >= target if side is Side.LONG else b.low <= target:
            target_consumed = True
        if (
            target_consumed or snap.state not in ACTIVE
            or snap.first_sweep_at is None or snap.as_of is None
            or snap.as_of <= first_return_at
            or snap.as_of.astimezone(NY).hour != 10
        ):
            continue
        witness = first_series_cisd(
            tuple(seen), side=side,
            first_sweep_at=snap.first_sweep_at,
            as_of=snap.as_of,
        )
        if witness is None:
            continue
        if witness.first_candle_open_crossed:
            author_events += 1
            if first_author is None:
                first_author = witness
        if witness.last_candle_open_crossed and not witness.first_candle_open_crossed:
            false_events += 1
            if first_false is None:
                first_false = witness
    label = (
        "AUTHOR_FIRST_SERIES_CLOSE_COMPONENT"
        if first_author is not None else
        "LEGACY_LAST_ONLY_FALSE_PROMOTION"
        if first_false is not None else
        "NO_SOURCE_FIRST_SERIES_CLOSE_OBSERVED"
    )
    return {
        "ny_day": day,
        "first_return_at": first_return_at.astimezone(UTC).isoformat(),
        "first_series_cisd_component_state": label,
        "author_first_series_close_at": (
            first_author.confirmed_at.isoformat() if first_author else None
        ),
        "first_series_length": (
            first_author.opposing_series_length if first_author else None
        ),
        "first_last_only_false_promotion_at": (
            first_false.confirmed_at.isoformat() if first_false else None
        ),
        "first_last_only_series_length": (
            first_false.opposing_series_length if first_false else None
        ),
        "author_first_series_events": author_events,
        "legacy_last_only_false_events": false_events,
        "source_window_reached_target_prior_to_final_close": target_consumed,
        "source_profile": "TTRADES_NY_AM_2025",
        "conservative_immediate_confirmation_QORE_policy": True,
        "only_CISD_component_not_MSS_OB_entry": True,
        "m3_author_method_certified": False,
        "m4_full_ob_certified": False,
        "m5_swing_causation_certified": False,
        "cognition_integrated_certified": False,
        "ops_authorized": False,
        "orders_and_sizing_created": 0,
    }


def _work(rows: list[tuple[str, datetime]]) -> list[dict[str, object]]:
    if _GROUPS is None:
        raise ValueError("ULTRAFAST_SHARED_SOURCE_NOT_PRELOADED")
    return [
        audit_real_day(
            day=day,
            nine=_GROUPS[day][9], ten=_GROUPS[day][10],
            first_return_at=stamp,
        )
        for day,stamp in rows
    ]


def canonical_hash(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return sha256(raw.encode("utf-8")).hexdigest()


def analyze(market: Path, *, parity: bool = True) -> dict[str, object]:
    global _GROUPS  # noqa: PLW0603
    if hash_file(market) != MARKET_SHA:
        raise ValueError("MARKET_SHA256_OR_LICENSED_SOURCE_MISMATCH")
    start = time.monotonic()
    groups,n = collect_hours(market_rows(market))
    if n != M1_TOTAL:
        raise AssertionError("SOURCE_M1_COUNT_DRIFT")
    census=run_census(groups)
    if census["observed_days_total"] != 775 or census["state_counts"] != EXPECTED:
        raise AssertionError("FROZEN_775_DAY_SOURCE_CENSUS_DRIFT")
    rows = [
        (x["ny_day"],datetime.fromisoformat(x["as_of"]).astimezone(UTC))
        for x in census["source_classifications"]
        if x["classification"] == "FIRST_RETURN_NO_QORE_MSS"
    ]
    if len(rows) != 483 or len({x[0] for x in rows}) != 483:
        raise AssertionError("FROZEN_483_UNIQUE_FIRST_RETURNS_DRIFT")
    _GROUPS=groups
    preload_s=time.monotonic()-start
    baseline_records: list[dict[str, object]] | None=None
    scalar_s: float | None=None
    if parity:
        start=time.monotonic()
        baseline_records=_work(rows)
        scalar_s=time.monotonic()-start
    start=time.monotonic()
    with mp.get_context("fork").Pool(processes=2) as pool:
        partitions=pool.map(_work,[rows[::2],rows[1::2]])
    fast_records=sorted(
        (x for part in partitions for x in part),
        key=lambda x: x["ny_day"],
    )
    fast_s=time.monotonic()-start
    if len(fast_records) != 483:
        raise AssertionError("ULTRAFAST_PARTITIONS_LOST_CASES")
    digest=canonical_hash(fast_records)
    if parity:
        if baseline_records is None or canonical_hash(
            sorted(baseline_records,key=lambda x:x["ny_day"])
        ) != digest:
            raise AssertionError("SCALAR_VS_FAST_FULL_CASEBOOK_PARITY_FAILURE")
    counts=Counter(x["first_series_cisd_component_state"] for x in fast_records)
    if sum(counts.values()) != 483:
        raise AssertionError("CISD_PARTITION_DOES_NOT_COVER_SOURCE")
    first_examples: dict[str, dict[str,object]]={}
    for record in fast_records:
        first_examples.setdefault(record["first_series_cisd_component_state"],record)
    return {
        "schema": "VT31_M3_TTRADES_CISD_FIRST_OPEN_SERIES_SOURCE_ULTRAFAST_V1",
        "prereg_commit":PREREG,
        "original_m1_sha256":MARKET_SHA,
        "original_m1_count":n,
        "frozen_source_days":775,
        "frozen_first_returns":len(rows),
        "scalar_ultrafast_full_casebook_identical":parity,
        "casebook_sha256":digest,
        "author_first_open_vs_legacy_last_open_counts":dict(sorted(counts.items())),
        "first_example_by_class":first_examples,
        "days_with_any_legacy_last_only_false_event":sum(
            bool(x["legacy_last_only_false_events"]) for x in fast_records
        ),
        "all_483_cognitive_m1_records":fast_records,
        "source_author": (
            "https://ttrades.com/understanding-the-change-in-state-of-delivery-cisd/"
        ),
        "source_data_development_not_OOS":True,
        "timings_wall_seconds_not_PnL": {
            "source_load_once_and_census":round(preload_s,6),
            "scalar":round(scalar_s,6) if scalar_s is not None else None,
            "ultrafast_two_worker":round(fast_s,6),
        },
        "author_first_series_component_witness":True,
        "author_full_MSS_displacement_certified":False,
        "author_full_OB_entry_certified":False,
        "causative_stop_swing_certified":False,
        "method_cognition_certified":False,
        "M6_dual_signers_verified":False,
        "trader_certified":False,
        "orders_sizing_economics":False,
        "live_authorized":False,
    }


def main() -> None:
    p=argparse.ArgumentParser()
    p.add_argument("--market",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--parity",action="store_true")
    args=p.parse_args()
    report=analyze(args.market,parity=args.parity)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(report,sort_keys=True,indent=2)+"\n")
    print(json.dumps({
        "cases":report["frozen_first_returns"],
        "states":report["author_first_open_vs_legacy_last_open_counts"],
        "days_with_legacy_last_only_false_events":report[
            "days_with_any_legacy_last_only_false_event"
        ],
        "full_casebook_sha256":report["casebook_sha256"],
        "full_parity":report["scalar_ultrafast_full_casebook_identical"],
        "times":report["timings_wall_seconds_not_PnL"],
        "trader_certified":False,
    },sort_keys=True))


if __name__=="__main__":
    main()
