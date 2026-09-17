"""Gap05-comparable runner for the complete CIBO VT-31 behavior explainer.

Uses the already-consumed VT-31 `gap05` reference admission (09:00-10:00 may
contain up to five consecutive missing M1 bars) while keeping 10:00-11:00
strict60. This is only for trader-comparable research; strict60 Atlas remains
the independent data-quality control.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

import cibo_atlas_vt31_complete_behavior_explainer as base
import cibo_atlas_vt31_historical_market_scanner as strict
import vt31_r8_sparse_reference_forensics as sparse
from qore.infrastructure.market_data import OhlcSnapshot


def analyze_day_gap05(
    partition: str,
    market: str,
    provider: str,
    local_day: date,
    day_bars: tuple[OhlcSnapshot, ...],
) -> dict[str, Any] | None:
    reference = cast(
        tuple[OhlcSnapshot, ...],
        sparse._reference_bars(cast(tuple[object, ...], day_bars)),
    )
    session = base.bars_between(day_bars, (10, 0, 0), (11, 0, 0))
    lifecycle = base.bars_between(day_bars, (10, 0, 0), (16, 0, 0))
    if len(session) != 60 or not strict.contiguous(session):
        return None
    if not sparse._policy_accepts(cast(tuple[object, ...], reference), "gap05"):
        return None
    if not lifecycle:
        return None

    ref_high = max(base.d(bar.high) for bar in reference)
    ref_low = min(base.d(bar.low) for bar in reference)
    width = ref_high - ref_low
    if width <= 0:
        return None

    side, breach_index = base.first_breach(session, ref_high, ref_low)
    life_high = max(base.d(bar.high) for bar in lifecycle)
    life_low = min(base.d(bar.low) for bar in lifecycle)
    high_extension = max(Decimal(0), life_high - ref_high) / width
    low_extension = max(Decimal(0), ref_low - life_low) / width
    breached_high = high_extension > 0
    breached_low = low_extension > 0
    if not breached_high and not breached_low:
        regime = "inside-reference"
    elif breached_high and breached_low:
        regime = "two-sided-expansion"
    elif breached_high:
        regime = "one-sided-high-expansion"
    else:
        regime = "one-sided-low-expansion"

    life_range_ref = (life_high - life_low) / width
    objective_at: str | None = None
    post_boundary_extension_ref: Decimal | None = None
    breach_at: str | None = None
    breach_to_objective: int | None = None
    objective_to_farthest: int | None = None

    if side in {"high", "low"} and breach_index is not None:
        breach_bar = session[breach_index]
        breach_at = breach_bar.opened_at.isoformat()
        path = tuple(bar for bar in lifecycle if bar.opened_at >= breach_bar.opened_at)
        objective_index: int | None = None
        for index, bar in enumerate(path):
            hit = base.d(bar.low) <= ref_low if side == "high" else base.d(bar.high) >= ref_high
            if hit:
                objective_index = index
                break
        if objective_index is not None:
            objective = path[objective_index]
            objective_at = objective.opened_at.isoformat()
            breach_to_objective = int(
                (objective.opened_at - breach_bar.opened_at).total_seconds() // 60
            )
            tail = path[objective_index:]
            if side == "high":
                farthest_index = min(range(len(tail)), key=lambda i: base.d(tail[i].low))
                post_boundary_extension_ref = (
                    max(Decimal(0), ref_low - base.d(tail[farthest_index].low)) / width
                )
            else:
                farthest_index = max(range(len(tail)), key=lambda i: base.d(tail[i].high))
                post_boundary_extension_ref = (
                    max(Decimal(0), base.d(tail[farthest_index].high) - ref_high) / width
                )
            objective_to_farthest = int(
                (tail[farthest_index].opened_at - objective.opened_at).total_seconds() // 60
            )

    return {
        "partition": partition,
        "market": market,
        "provider": provider,
        "ny_date": str(local_day),
        "weekday": local_day.strftime("%A"),
        "reference_admission": "gap05",
        "reference_bar_count": len(reference),
        "reference_width": base.fmt(width),
        "reference_high": base.fmt(ref_high),
        "reference_low": base.fmt(ref_low),
        "first_breach": side,
        "first_breach_at": breach_at,
        "day_regime": regime,
        "lifecycle_range_ref": base.fmt(life_range_ref),
        "expansion_strength": base.expansion_strength(life_range_ref),
        "high_extension_ref": base.fmt(high_extension),
        "low_extension_ref": base.fmt(low_extension),
        "opposite_boundary_hit_by_16": objective_at is not None,
        "opposite_boundary_at": objective_at,
        "breach_to_opposite_minutes": breach_to_objective,
        "post_boundary_extension_ref": base.fmt(post_boundary_extension_ref),
        "opposite_to_farthest_extension_minutes": objective_to_farthest,
        "post_boundary_ladder": {
            base.fmt(level): bool(
                post_boundary_extension_ref is not None and post_boundary_extension_ref >= level
            )
            for level in base.TARGET_LADDER_REF
        },
    }


def load_market_days_gap05(
    paths: dict[tuple[str, str], Path],
) -> tuple[dict[tuple[str, str], tuple[OhlcSnapshot, ...]], list[dict[str, Any]]]:
    bars_by_key: dict[tuple[str, str], tuple[OhlcSnapshot, ...]] = {}
    rows_by_key: dict[tuple[str, str], dict[str, Any]] = {}

    for partition in base.PARTITIONS:
        for market in base.MARKETS:
            series, _, _, _, _, provider = base.load_market_evidence(paths[(partition, market)])
            grouped: dict[date, list[OhlcSnapshot]] = defaultdict(list)
            for bar in series:
                grouped[base._day(bar.opened_at)].append(bar)
            for local_day, bars in sorted(grouped.items()):
                frozen = tuple(bars)
                row = analyze_day_gap05(partition, market, provider, local_day, frozen)
                if row is None:
                    continue
                key = (market, str(local_day))
                if key in rows_by_key:
                    raise ValueError(f"overlapping accepted gap05 market day {key}")
                rows_by_key[key] = row
                bars_by_key[key] = frozen

    rows = [rows_by_key[key] for key in sorted(rows_by_key)]
    print(f"CIBO gap05 complete explainer coverage: accepted_market_days={len(rows)}")
    return bars_by_key, rows


def self_test() -> None:
    assert sparse.POLICIES["gap05"] == 5
    base.self_test()
    print("CIBO Atlas gap05 complete behavior explainer self-test PASS")


def main() -> None:
    base.load_market_days = load_market_days_gap05
    base.main()


if __name__ == "__main__":
    main()
