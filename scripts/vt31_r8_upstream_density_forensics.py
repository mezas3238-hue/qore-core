"""Consumed-only VT-31 R8 upstream setup-density forensics.

Classifies why a complete 09:00-11:00 NY day never produces a base R2.6
executable setup. This does not change R8 semantics and opens no new evidence.
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import cast

import vt31_r5_candidate as r5
from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_6_composite_entry_research import (
    _evaluate,
)
from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_5_multi_index_research import (
    _day,
    _wall,
    load_market_evidence,
)
from qore.infrastructure.traders.vt31_silver_bullet_r2_2 import (
    _detect_raid,
    _entry_evidence,
    _session_bars,
    _structure,
    build_reference_range,
)

MARKETS = ("NAS100", "SP500", "US30")


def classify(path: Path) -> dict[str, object]:
    series, *_ = load_market_evidence(path)
    by_day: dict[object, list[object]] = defaultdict(list)
    for bar in series:
        by_day[_day(bar.opened_at)].append(bar)

    stages: Counter[str] = Counter()
    first_candidate = 0
    raid_sides: Counter[str] = Counter()
    complete = 0
    examples: dict[str, list[str]] = defaultdict(list)

    for local_day in sorted(by_day):
        day_bars = tuple(by_day[local_day])
        reference = tuple(
            bar for bar in day_bars if (9, 0, 0) <= _wall(bar.opened_at) < (10, 0, 0)
        )
        session_indexed = tuple(
            (i, bar)
            for i, bar in enumerate(day_bars)
            if (10, 0, 0) <= _wall(bar.opened_at) < (11, 0, 0)
        )
        if len(reference) != 60 or len(session_indexed) != 60:
            continue
        complete += 1

        prefix = list(reference)
        found = False
        for _, bar in session_indexed:
            prefix.append(bar)
            candidate, _ = _evaluate(
                instrument=bar.instrument,
                as_of=bar.closed_at,
                bars=cast(object, tuple(prefix)),
                variant=r5.BASE_VARIANT,
            )
            if candidate is not None:
                found = True
                first_candidate += 1
                stages["FIRST_BASE_CANDIDATE"] += 1
                break
        if found:
            continue

        full_prefix = tuple(reference) + tuple(bar for _, bar in session_indexed)
        as_of = session_indexed[-1][1].closed_at
        instrument = session_indexed[-1][1].instrument
        ref = build_reference_range(instrument=instrument, as_of=as_of, bars=cast(object, full_prefix))
        if ref is None:
            stage = "REFERENCE_UNRESOLVED"
        else:
            session = _session_bars(as_of, cast(object, full_prefix))
            raid = _detect_raid(session, ref)
            if raid is None:
                stage = "NO_RAID"
            elif raid.high_taken and raid.low_taken:
                stage = "BOTH_SIDES_SWEPT"
            else:
                raid_sides[str(raid.side.value)] += 1
                structure = _structure(session, raid)
                if structure is None:
                    stage = "NO_STRUCTURE_CONFIRMATION"
                else:
                    confirmation_index, extreme_index, _, _ = structure
                    evidence = _entry_evidence(session, raid, confirmation_index, extreme_index)
                    if not evidence:
                        stage = "NO_DEMONSTRATED_ENTRY_FAMILY"
                    else:
                        # If entry evidence exists but _evaluate never emitted a setup, the
                        # remaining failure is causal entry geometry/selection containment.
                        stage = "NO_VALID_RETRACEMENT_GEOMETRY"
        stages[stage] += 1
        if len(examples[stage]) < 5:
            examples[stage].append(str(local_day))

    return {
        "complete_days": complete,
        "first_base_candidate_days": first_candidate,
        "first_base_candidate_rate": (first_candidate / complete if complete else 0.0),
        "terminal_stage_counts": dict(sorted(stages.items())),
        "raid_sides_on_no_candidate_days": dict(sorted(raid_sides.items())),
        "examples": dict(sorted(examples.items())),
    }


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 9:
        print("usage: script R5_NAS R5_SP R5_US R6_NAS R6_SP R6_US R8_NAS R8_SP R8_US")
        return 2
    names = ("r5", "r6", "r8_fresh")
    out: dict[str, object] = {
        "schema": "qore.trader_lab.vt31_r8_upstream_density_forensics.v1",
        "research_only": True,
        "opens_new_evidence": False,
        "candidate_status": "R8_REJECTED_FRESH_CONSUMED",
        "partitions": {},
    }
    for pi, name in enumerate(names):
        block: dict[str, object] = {}
        for mi, market in enumerate(MARKETS):
            block[market] = classify(Path(args[pi * 3 + mi]))
        cast(dict[str, object], out["partitions"])[name] = block
    print(json.dumps(out, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
