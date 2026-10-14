#!/usr/bin/env python3
"""VT31 L3 PREPARATION ONLY: 1x vs 32x M1 source-prefix decision parity.

This does NOT create TraderLabCandidateBinding, replay/order/fill evidence
or TraderLabFastForwardQualification; no official L1/L2/L3 is passed.
The accelerated path sees each new market event only at M1 CLOSED time.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from scripts.vt31_m4_m5_ttrades_census_20261014 import census
from scripts.vt31_m4_m5_ttrades_fvg_path_20261014 import (
    first_fvg_and_source_path,
)
from scripts.vt31_ttrades_am_method_m1_census_20261014 import (
    MARKET_SHA,
    collect_hours,
    complete_hour,
    hash_file,
    market_rows,
)
from scripts.vt31_ttrades_am_native_cog_v1_20261014 import (
    propose_ttrades_am_cognition,
)

SPEED_FACTOR = 32
PREREG = "51eb61d6982c67026bdca39dd301b380347d54bd"
MODEL = "VT31_TTRADES_RESEARCH_M1_PREFIX_PARITY_NOT_L3_QUALIFIED"


def canonical_hash(data: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            data, sort_keys=True, ensure_ascii=True, separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def classify_first_source(last: Any) -> str:
    """Independent streaming event classification, not a replayed helper call."""
    if last.state == "CONTEXT_ATTESTED_NOT_CERTIFIED":
        return "MSS_ATTESTED_CONTEXT_ONLY"
    if "QORE_MSS_PROXY_NOT_CONFIRMED_ON_FIRST_RETURN" in last.reasons:
        return "FIRST_RETURN_NO_QORE_MSS"
    if "BOTH_H1_SIDES_SWEPT_UNKNOWN_INTRABAR_ORDER" in last.reasons:
        return "AMBIGUOUS_DOUBLE_SWEEP"
    if last.state == "REJECTED":
        return "REJECTED_SOURCE"
    if last.native_state == "AWAIT_SWEEP":
        return "NO_SWEEP"
    if last.native_state == "AWAIT_RETURN":
        return "SWEEP_NO_RETURN"
    return "UNKNOWN_SOURCE"


def _is_terminal(source: Any) -> bool:
    return bool(
        source.state in ("REJECTED", "CONTEXT_ATTESTED_NOT_CERTIFIED")
        or source.native_state == "RETURN_INSIDE_OBSERVED"
        or "BOTH_H1_SIDES_SWEPT_UNKNOWN_INTRABAR_ORDER" in source.reasons
    )


def streaming_census(
    groups: dict[str, dict[int, tuple[Any, ...]]],
    *, factor: int,
) -> dict[str, Any]:
    """Publish data only on each CLOSED M1; wall-clock simulation is explicit.

    The effective virtual schedule uses the same simulated market-time ticks
    at 1x and at 32x, only the manually advanced wall clock differs.
    """
    if factor not in (1, SPEED_FACTOR):
        raise ValueError("PREREGISTERED_FACTOR_ONLY_1_OR_32")
    base: Counter[str] = Counter()
    m4: Counter[str] = Counter()
    m5: Counter[str] = Counter()
    cases: list[dict[str, Any]] = []
    source_instants: list[str] = []
    observed_events = 0
    elapsed_wall = timedelta()
    previous_source_at: datetime | None = None

    def observe(bar: Any) -> None:
        nonlocal observed_events, previous_source_at, elapsed_wall
        now = bar.closed_at
        if now.tzinfo is None or now.utcoffset() is None:
            raise ValueError("SOURCE_EVENT_NO_UTC_CLOCK")
        if previous_source_at is not None and now <= previous_source_at:
            raise ValueError("SOURCE_EVENTS_OUT_OF_ORDER_OR_DUPLICATED")
        if bar.closed_at - bar.opened_at != timedelta(minutes=1):
            raise ValueError("SOURCE_EVENT_NOT_60_SECONDS")
        # Market fact is published when the M1 CLOSE becomes available;
        # this cannot read its future successor.
        available_at = bar.closed_at
        if available_at > now:
            raise ValueError("FUTURE_AVAILABILITY_FORBIDDEN")
        source_instants.append(now.isoformat())
        previous_source_at = now
        observed_events += 1
        elapsed_wall += timedelta(microseconds=60_000_000 // factor)

    for day, hours in sorted(groups.items()):
        nine, ten = hours.get(9, ()), hours.get(10, ())
        if not complete_hour(day, 9, nine) or not complete_hour(day, 10, ten):
            base["INCOMPLETE_M1_HOURS"] += 1
            continue
        for b in nine:
            observe(b)
        latest: Any = None
        terminal: Any = None
        cognition: Any = None
        final_path: Any = None
        for i, bar in enumerate(ten):
            observe(bar)
            # CLOSED-only prefix: the 10AM market suffix is never passed in.
            prefix = ten[:i + 1]
            if terminal is None:
                latest = propose_ttrades_am_cognition(
                    as_of=bar.closed_at, history=nine + prefix,
                )
                if _is_terminal(latest):
                    terminal = latest
                    if terminal.state == "CONTEXT_ATTESTED_NOT_CERTIFIED":
                        cognition = terminal.decision
                        if cognition is None:
                            raise ValueError("SOURCE_COGNITION_DTO_NOT_PRESENT")
            if cognition is not None:
                final_path = first_fvg_and_source_path(
                    nine=nine, ten=prefix, cognition=cognition,
                )
                if final_path.execution_authorized or final_path.filled:
                    raise ValueError("RESEARCH_SOURCE_MUST_NEVER_EXECUTE")
        if terminal is None:
            terminal = latest
        if terminal is None:
            raise ValueError("EMPTY_10AM_SOURCE")
        category = classify_first_source(terminal)
        base[category] += 1
        if cognition is not None:
            if final_path is None:
                raise ValueError("NO_SOURCE_FVG_FINAL")
            m4[final_path.state] += 1
            if final_path.first_fvg_confirmed_at is not None:
                m5[final_path.source_path_state] += 1
            cases.append({
                "ny_day": day,
                "first_return_mss_at": terminal.as_of.isoformat(),
                "m4_m5_source_only": final_path.record(),
            })
    return {
        "baseline_M2_M3_state_counts": dict(sorted(base.items())),
        "baseline_days_total": sum(base.values()),
        "M2_M3_cognitive_contexts": base["MSS_ATTESTED_CONTEXT_ONLY"],
        "M4_source_state_counts": dict(sorted(m4.items())),
        "M5_hypothetical_source_path_counts": dict(sorted(m5.items())),
        "cognitive_case_evidence": cases,
        "observation_events": observed_events,
        "event_instants_sha256": canonical_hash(source_instants),
        "explicit_wall_advance_microseconds": int(
            elapsed_wall // timedelta(microseconds=1)
        ),
        "factor": factor,
    }


def parity_report(groups: dict[str, dict[int, tuple[Any, ...]]]) -> dict[str, Any]:
    baseline = census(groups)
    one = streaming_census(groups, factor=1)
    accelerated = streaming_census(groups, factor=SPEED_FACTOR)
    names = (
        "baseline_M2_M3_state_counts", "baseline_days_total",
        "M2_M3_cognitive_contexts", "M4_source_state_counts",
        "M5_hypothetical_source_path_counts", "cognitive_case_evidence",
    )
    for key in names:
        if one[key] != baseline[key]:
            raise ValueError(f"STREAM_1X_DIVERGED_FROM_FROZEN_BATCH:{key}")
        if accelerated[key] != one[key]:
            raise ValueError(f"STREAM_32X_DIVERGED_FROM_STREAM_1X:{key}")
    if one["observation_events"] != accelerated["observation_events"]:
        raise ValueError("ACCELERATION_DROPPED_M1_EVENTS")
    if one["event_instants_sha256"] != accelerated["event_instants_sha256"]:
        raise ValueError("ACCELERATION_CHANGED_SIMULATED_CHRONOLOGY")
    if (
        one["explicit_wall_advance_microseconds"]
        != SPEED_FACTOR * accelerated["explicit_wall_advance_microseconds"]
    ):
        raise ValueError("WALL_ADVANCE_RATIO_NOT_PREDECLARED_32")
    eligible = baseline["M2_M3_cognitive_contexts"]
    if baseline["baseline_days_total"] != 775 or eligible != 128:
        raise ValueError("FROZEN_3Y_BASELINE_POPULATION_CHANGED")
    if baseline["M4_source_state_counts"] != {
        "FVG_GEOMETRY_ATTESTED_NOT_EXECUTABLE": 119,
        "NO_ELIGIBLE_FVG": 8,
        "WINDOW_CLOSED_FOR_NEW_LIMIT": 1,
    }:
        raise ValueError("FROZEN_3Y_FVG_SOURCE_RESULT_CHANGED")
    if baseline["M5_hypothetical_source_path_counts"] != {
        "AMBIGUOUS_M1_SEQUENCE_NO_FILL": 31,
        "EXPIRED_NO_ORDER_OR_ACK": 27,
        "TOUCH_NOT_FILL": 61,
    }:
        raise ValueError("FROZEN_3Y_SOURCE_PATH_RESULT_CHANGED")
    return {
        "model": MODEL,
        "market_sha256": MARKET_SHA,
        "prereg_commit": PREREG,
        "reference_batch_cases_sha256":
            canonical_hash(baseline["cognitive_case_evidence"]),
        "one_x_cases_sha256": canonical_hash(one["cognitive_case_evidence"]),
        "thirty_two_x_cases_sha256":
            canonical_hash(accelerated["cognitive_case_evidence"]),
        "simulated_market_event_instants_sha256":
            one["event_instants_sha256"],
        "source_events_per_schedule": one["observation_events"],
        "wall_advance_1x_us": one["explicit_wall_advance_microseconds"],
        "wall_advance_32x_us":
            accelerated["explicit_wall_advance_microseconds"],
        "simulated_clock_parity": True,
        "reference_case_parity": True,
        "declared_virtual_speed_factor": SPEED_FACTOR,
        "first_return_only_cognitive_contexts": eligible,
        "M4_source_state_counts": baseline["M4_source_state_counts"],
        "M5_source_path_state_counts":
            baseline["M5_hypothetical_source_path_counts"],
        "trader_lab_candidate_binding_present": False,
        "trader_lab_L1_qualified": False,
        "trader_lab_L2_qualified": False,
        "trader_lab_L3_qualified": False,
        "economic_evaluation": None,
        "execution_ACK_fills": 0,
        "sizing_produced": False,
        "fresh_holdout_used": False,
        "trader_certified": False,
        "demo_eligible": False,
        "live_authorized": False,
    }


def main() -> None:
    args = argparse.ArgumentParser()
    args.add_argument("--market", type=Path, required=True)
    args.add_argument("--out", type=Path, required=True)
    options = args.parse_args()
    if hash_file(options.market) != MARKET_SHA:
        raise ValueError("SOURCE_FROZEN_HASH_MISMATCH")
    groups, count = collect_hours(market_rows(options.market))
    report = parity_report(groups)
    report["original_m1_count"] = count
    options.out.parent.mkdir(parents=True, exist_ok=True)
    options.out.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        key: report[key] for key in (
            "original_m1_count", "source_events_per_schedule",
            "declared_virtual_speed_factor", "reference_case_parity",
            "first_return_only_cognitive_contexts", "M4_source_state_counts",
            "M5_source_path_state_counts", "trader_lab_L3_qualified",
        )
    }, sort_keys=True))


if __name__ == "__main__":
    main()
