#!/usr/bin/env python3
"""Fast causal source-capacity count on the canonical VT31 owner 3Y base.

Counts distinct executable source episodes only. It does not inspect outcomes.
This gives a causal upper-bound map for density before fill, admission and
position-management attrition.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import UTC, date
from pathlib import Path
from typing import Any, cast

import vt31_nas100_specialist_r1_candidate as specialist

from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_5_multi_index_research import (
    _day,
    load_market_evidence,
)
from qore.infrastructure.traders.vt31_silver_bullet_r2_2 import (
    Vt31R22ExecutableSetup,
    Vt31R22ExecutionPolicy,
    evaluate_vt31_r2_2_source,
    make_executable_setup,
)

SCHEMA = "qore.vt31.nas100.owner_3y_capacity_count.v1"
BASE_ID = "VT31_NAS100_OWNER_3Y_BASE_001"
TARGET_TRADES = 450


def _signature(setup: Vt31R22ExecutableSetup) -> tuple[str, ...]:
    source = setup.source_setup
    selected = [
        item
        for item in source.candidates
        if item.family == setup.selected_family
    ]
    formed_at = min(
        (item.formed_at for item in selected),
        default=setup.decision_at,
    )
    return (
        setup.side.value,
        source.structure.raid_at.astimezone(UTC).isoformat(),
        source.structure.confirmation_at.astimezone(UTC).isoformat(),
        setup.selected_family.value,
        formed_at.astimezone(UTC).isoformat(),
        format(setup.entry_price, "f"),
        format(setup.stop_price, "f"),
        format(setup.target_price, "f"),
    )


def replay(evidence_path: Path) -> dict[str, object]:
    evidence_payload = json.loads(evidence_path.read_text(encoding="utf-8"))
    if evidence_payload.get("base_id") != BASE_ID:
        raise ValueError("capacity count requires canonical owner 3Y base")

    series, _, evidence, _, _, _ = load_market_evidence(evidence_path)
    raw: dict[date, list[object]] = defaultdict(list)
    for bar in series:
        raw[_day(getattr(bar, "opened_at"))].append(bar)
    by_day = {
        local_day: tuple(
            sorted(items, key=lambda item: getattr(item, "opened_at"))
        )
        for local_day, items in raw.items()
    }
    policy = Vt31R22ExecutionPolicy()

    day_counts: Counter[str] = Counter()
    distribution: Counter[int] = Counter()
    family_counts: Counter[str] = Counter()
    side_counts: Counter[str] = Counter()
    observations: list[dict[str, object]] = []

    for local_day in sorted(by_day):
        day_bars = by_day[local_day]
        reference = specialist._slice(day_bars, (9, 0, 0), (10, 0, 0))
        session = specialist._slice(day_bars, (10, 0, 0), (11, 0, 0))
        if len(reference) != 60 or len(session) != 60:
            day_counts["incomplete_day"] += 1
            continue

        day_counts["complete_day"] += 1
        prefix = list(reference)
        seen: set[tuple[str, ...]] = set()
        saw_source = False

        for bar in session:
            prefix.append(bar)
            evaluation = evaluate_vt31_r2_2_source(
                instrument=getattr(bar, "instrument"),
                as_of=getattr(bar, "closed_at"),
                m1_candles=cast(Any, tuple(prefix)),
                evidence_fingerprint=evidence,
            )
            if evaluation.setup is None:
                continue
            saw_source = True
            executable, _ = make_executable_setup(evaluation.setup, policy)
            if executable is None:
                day_counts["source_not_executable_observation"] += 1
                continue
            signature = _signature(executable)
            if signature in seen:
                continue
            seen.add(signature)
            family_counts[executable.selected_family.value] += 1
            side_counts[executable.side.value] += 1
            observations.append(
                {
                    "local_date": local_day.isoformat(),
                    "signature": list(signature),
                    "decision_at": executable.decision_at.astimezone(
                        UTC
                    ).isoformat(),
                    "side": executable.side.value,
                    "entry_family": executable.selected_family.value,
                }
            )

        if saw_source:
            day_counts["day_with_source"] += 1
        if seen:
            day_counts["day_with_executable_episode"] += 1
        if len(seen) >= 2:
            day_counts["day_with_2plus_executable_episodes"] += 1
        if len(seen) >= 3:
            day_counts["day_with_3plus_executable_episodes"] += 1
        distribution[len(seen)] += 1

    one_per_day_ceiling = int(day_counts["day_with_executable_episode"])
    unique_count = len(observations)
    return {
        "schema": SCHEMA,
        "base_id": BASE_ID,
        "target_trades_3y": TARGET_TRADES,
        "market_days": len(by_day),
        "day_counts": dict(sorted(day_counts.items())),
        "distinct_executable_episode_distribution": {
            str(key): value
            for key, value in sorted(distribution.items())
        },
        "unique_executable_episode_count": unique_count,
        "one_trade_per_day_opportunity_ceiling": one_per_day_ceiling,
        "one_trade_per_day_ceiling_gap_to_450": (
            TARGET_TRADES - one_per_day_ceiling
        ),
        "target_fraction_of_one_per_day_ceiling": (
            None
            if one_per_day_ceiling == 0
            else format(TARGET_TRADES / one_per_day_ceiling, ".6f")
        ),
        "entry_family_counts": dict(sorted(family_counts.items())),
        "side_counts": dict(sorted(side_counts.items())),
        "observations": observations,
        "governance": {
            "single_contiguous_3y_base": True,
            "outcomes_inspected": False,
            "future_information_used": False,
            "duplicate_signatures_counted_twice": False,
            "sizing_or_leverage_used": False,
            "policy_promoted": False,
            "candidate_certified": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    payload = replay(args.evidence)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "base_id": BASE_ID,
                "target_trades_3y": TARGET_TRADES,
                "day_counts": payload["day_counts"],
                "unique_executable_episode_count": payload[
                    "unique_executable_episode_count"
                ],
                "one_trade_per_day_opportunity_ceiling": payload[
                    "one_trade_per_day_opportunity_ceiling"
                ],
                "one_trade_per_day_ceiling_gap_to_450": payload[
                    "one_trade_per_day_ceiling_gap_to_450"
                ],
                "entry_family_counts": payload["entry_family_counts"],
                "side_counts": payload["side_counts"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
