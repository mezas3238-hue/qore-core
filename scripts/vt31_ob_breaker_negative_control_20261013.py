#!/usr/bin/env python3
"""Post-hoc generic pivot null, four-way overlap, and common displacement anchor.

All sources are M1 research signals. No broker execution, no stop/TP PnL,
no strategy parameter adjustment, no holdout opening.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from statistics import mean, median
from typing import Any

from scripts.vt31_ttrades_am_all_entry_sources_20261013 import (
    FAMILIES, SOURCE_SHA, analyze as original_analyze, context, forward_15,
)
from scripts.vt31_ttrades_am_source_20261013 import (
    Bar, collect_days, diagnostic, file_hash, market_source,
)

PREREG = "2748d59daf1d32d42b6dd41d37c6def1ab314e41"
SOURCE_MODEL_HEAD = "9f85b83e1bfd23c02e5f642bd33defa65208f015"
FROZEN_EXPECTED = dict(zip(FAMILIES, (212, 205, 116, 84), strict=True))


def _confirmed_three_bar_pivot(
    candles: list[Bar], i: int, side: str,
) -> bool:
    """M1 pivot only confirmed at RIGHT candle close; never on center."""
    if i < 2:
        return False
    left, middle, right = candles[i-2:i+1]
    if not (
        left.time + timedelta(minutes=1) == middle.time
        and middle.time + timedelta(minutes=1) == right.time
    ):
        return False
    if side == "LONG":
        return middle.low < left.low and middle.low < right.low
    if side == "SHORT":
        return middle.high > left.high and middle.high > right.high
    raise ValueError("invalid control direction")


def generic_extreme(
    day: str, hours: dict[int, list[Bar]],
) -> dict[str, Any] | None:
    """One FIRST causal generic local pivot after displacement per context day."""
    status, ctx = context(hours[9], hours[10])
    if status != "CONTEXT_CONFIRMED" or ctx is None:
        return None
    di = ctx["disp_i"]
    side = ctx["side"]
    for i in range(di + 2, len(hours[10])):
        if _confirmed_three_bar_pivot(hours[10], i, side):
            candle = hours[10][i]
            return {
                "day_ny": day,
                "side": side,
                "confirmed_at": (
                    candle.time + timedelta(minutes=1)
                ).isoformat(),
                "pivot_center_time_NOT_SIGNAL": hours[10][i-1].time.isoformat(),
                "control": "FIRST_CONFIRMED_3M1_LOCAL_EXTREME",
            }
    return None


def time_gap(left: str, right: str) -> float:
    return (datetime.fromisoformat(left) - datetime.fromisoformat(right)).total_seconds() / 60


def describe_minutes(values: list[float]) -> dict[str, float | int | None]:
    if not values:
        return {"n": 0, "mean": None, "median": None, "min": None, "max": None}
    return {
        "n": len(values),
        "mean": round(mean(values), 4),
        "median": round(median(values), 4),
        "min": round(min(values), 4),
        "max": round(max(values), 4),
    }


def overlap_census(
    source: dict[str, dict[str, dict[str, Any]]],
    days: set[str],
) -> dict[str, Any]:
    members = {name: set(rows) for name, rows in source.items()}
    if set(members) != set(FAMILIES):
        raise ValueError("unknown source family")
    masks = Counter()
    for day in sorted(days):
        mask = "".join("1" if day in members[name] else "0" for name in FAMILIES)
        masks[mask] += 1
    pairs = {
        first: {
            second: len(members[first] & members[second])
            for second in FAMILIES
        }
        for first in FAMILIES
    }
    unique = {
        name: len(
            members[name] - set().union(
                *(members[x] for x in FAMILIES if x != name)
            )
        )
        for name in FAMILIES
    }
    union = set().union(*members.values())
    if sum(masks.values()) != len(days) or union != set().union(*members.values()):
        raise ValueError("invalid 16-pattern day overlap")
    if any(not m.issubset(days) for m in members.values()):
        raise ValueError("source event outside day universe")
    return {
        "family_order_mask": list(FAMILIES),
        "patterns_all_16": {
            f"{mask:04b}": masks.get(f"{mask:04b}", 0)
            for mask in range(16)
        },
        "pairwise_shared_days": pairs,
        "unique_family_days": unique,
        "union_days": len(union),
        "ob_without_fvg_or_direct": len(
            members["ORDER_BLOCK_RETEST"] - (
                members["FVG_3M1"] | members["DISPLACEMENT_DIRECT"]
            )
        ),
        "breaker_without_any_other_family": unique["BREAKER_RETEST"],
        "breaker_without_fvg_or_direct": len(
            members["BREAKER_RETEST"] - (
                members["FVG_3M1"] | members["DISPLACEMENT_DIRECT"]
            )
        ),
    }


def audit(days: dict[str, dict[int, list[Bar]]]) -> dict[str, Any]:
    """Audit already frozen emitter. No changes to predictor, filters or fills."""
    base = original_analyze(days)
    source = {
        fam: {str(e["day_ny"]): e for e in base["family_source_witnesses"][fam]}
        for fam in FAMILIES
    }
    for fam, expected in FROZEN_EXPECTED.items():
        if len(source[fam]) != expected:
            raise ValueError("original frozen four-family count drift")
    if base["source_days_ny"] != 775 or base["days_with_at_least_one_family"] != 212:
        raise ValueError("source-universe or union changed")

    overlap = overlap_census(source, set(days))
    if overlap["union_days"] != 212:
        raise ValueError("unexpected overlap union")
    direct = source["DISPLACEMENT_DIRECT"]
    placebo = {
        day: witness
        for day, d in days.items()
        if (witness := generic_extreme(day, d)) is not None
    }
    placebo_all = []
    control_returns: dict[str, float] = {}
    for day, event in placebo.items():
        ret = forward_15(event, days[day])
        if ret is not None:
            control_returns[day] = ret
            placebo_all.append((day, ret))

    tables: dict[str, dict[str, Any]] = {}
    for fam in FAMILIES:
        own = source[fam]
        common = []
        own15 = []
        common_lags = []
        control_pair_returns = []
        family_pair_returns = []
        diffs = []
        pivot_lags = []
        matched_at_same_minute = 0
        for day, ev in sorted(own.items()):
            if day not in direct:
                raise ValueError("source family outside displacement day")
            same_anchor = direct[day]
            displacement_open_result = forward_15(same_anchor, days[day])
            own_result = forward_15(ev, days[day])
            common_lags.append(time_gap(ev["confirmed_at"], same_anchor["confirmed_at"]))
            if displacement_open_result is not None:
                common.append((day, displacement_open_result))
            if own_result is not None:
                own15.append((day, own_result))
            if own_result is None or day not in control_returns:
                continue
            pivot = placebo[day]
            pivot_lag = time_gap(ev["confirmed_at"], pivot["confirmed_at"])
            pivot_lags.append(pivot_lag)
            matched_at_same_minute += int(pivot_lag == 0)
            family_pair_returns.append((day, own_result))
            control_pair_returns.append((day, control_returns[day]))
            diffs.append((day, own_result - control_returns[day]))

        tables[fam] = {
            "source_days": len(own),
            "own_clock_15m": diagnostic(own15),
            "common_displacement_clock_15m_posthoc_family_membership": diagnostic(common),
            "family_delay_minutes_after_displacement": describe_minutes(common_lags),
            "paired_first_generic_pivot": {
                "candidate_days": len(own),
                "with_a_valid_first_generic_pivot_and_both_M1_outcomes": len(diffs),
                "missing_control_or_M1": len(own)-len(diffs),
                "family_own_clock_on_matched_days": diagnostic(family_pair_returns),
                "control_pivot_own_clock_on_matched_days": diagnostic(control_pair_returns),
                "paired_difference_family_minus_generic_pivot": diagnostic(diffs),
                "time_family_minus_pivot_minutes": describe_minutes(pivot_lags),
                "same_confirmation_minute_count": matched_at_same_minute,
                "NOT_a_time_aligned_causal_effect": True,
            },
        }

    return {
        "schema": "qore.vt31.ob_breaker_null_overlap_common_clock.audit_v1",
        "controls_preregistered_commit": PREREG,
        "frozen_source_model_commit": SOURCE_MODEL_HEAD,
        "original_source_model_unchanged": True,
        "m1_frozen_sha256": SOURCE_SHA,
        "source_days": len(days),
        "source_union_days": overlap["union_days"],
        "overlap": overlap,
        "first_generic_pivot_all_context_days": {
            "with_causal_pivot": len(placebo),
            "with_full_forward_M1": len(placebo_all),
            "directional_15m": diagnostic(placebo_all),
            "no_OB_or_breaker_filter_in_control": True,
        },
        "each_family_common_anchor_and_matched_pivot_control": tables,
        "common_anchor_groups_use_future_family_membership": True,
        "generic_pivot_right_neighbor_closed_before_confirmation": True,
        "no_trades_fills_quotes_orders": True,
        "economic_edge": "NOT_IDENTIFIED",
        "pf_dd_sharpe": None,
        "selecting_ob_or_breaker_from_these_development_results_forbidden": True,
        "G3_original_signoff": "PENDING_DUAL_SIGNATURE",
        "Fresh_Holdout_opened": False,
        "main_VPS_live_modified": False,
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--market", type=Path)
    p.add_argument("--out", type=Path)
    args = p.parse_args()
    if not args.market or not args.out:
        p.error("--market and --out required")
    if file_hash(args.market) != SOURCE_SHA:
        raise ValueError("original M1 SHA256 drift")
    days = collect_days(market_source(args.market))
    report = audit(days)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, sort_keys=True)+"\n")
    print(json.dumps({
        "overlap": report["overlap"],
        "generic": report["first_generic_pivot_all_context_days"],
        "families": {
            k: {
                "own": v["own_clock_15m"],
                "common": v["common_displacement_clock_15m_posthoc_family_membership"],
                "paired": v["paired_first_generic_pivot"],
            }
            for k, v in report["each_family_common_anchor_and_matched_pivot_control"].items()
        },
        "economic_edge": report["economic_edge"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
