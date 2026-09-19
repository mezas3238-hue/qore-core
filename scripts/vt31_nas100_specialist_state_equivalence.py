"""Diagnose causal-state equivalence between research snapshot and raw-M1 specialist."""
# ruff: noqa: B009
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from typing import Any, cast

import vt31_nas100_specialist_r1_candidate as candidate

from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_5_multi_index_research import (
    _day,
    _wall,
    load_market_evidence,
)
from qore.infrastructure.traders.vt31_silver_bullet_r2_2 import (
    Vt31R22ExecutionPolicy,
    evaluate_vt31_r2_2_source,
    make_executable_setup,
)

SNAPSHOT_SCHEMA = "qore.vt31.nas100.market_understanding_snapshot.v1"


def run(snapshot_path: Path, evidence_path: Path) -> dict[str, object]:
    snapshot_payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
    if snapshot_payload.get("schema") != SNAPSHOT_SCHEMA:
        raise ValueError("unexpected snapshot schema")
    snapshots = {
        (str(row["local_date"]), str(row["decision_at"])): row
        for row in cast(list[dict[str, Any]], snapshot_payload["snapshots"])
    }

    series, _, evidence, _, _, _ = load_market_evidence(evidence_path)
    raw_by_day: dict[date, list[object]] = defaultdict(list)
    for bar in series:
        raw_by_day[_day(getattr(bar, "opened_at"))].append(bar)
    by_day: dict[date, tuple[object, ...]] = {
        day: tuple(sorted(bars, key=lambda bar: getattr(bar, "opened_at")))
        for day, bars in raw_by_day.items()
    }
    context_by_day = candidate._context_map(by_day)
    policy = Vt31R22ExecutionPolicy()

    counts: Counter[str] = Counter()
    mismatches: list[dict[str, object]] = []
    for local_day in sorted(by_day):
        day_bars = by_day[local_day]
        reference = candidate._slice(day_bars, (9, 0, 0), (10, 0, 0))
        session = candidate._slice(day_bars, (10, 0, 0), (11, 0, 0))
        if len(reference) != 60 or len(session) != 60:
            continue

        prefix = list(reference)
        selected_source = None
        selected = None
        selected_session_prefix: tuple[object, ...] = ()
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
            executable, _ = make_executable_setup(evaluation.setup, policy)
            if executable is None:
                break
            selected_source = evaluation.setup
            selected = executable
            selected_session_prefix = tuple(
                item
                for item in prefix
                if (10, 0, 0)
                <= _wall(getattr(item, "opened_at"))
                < (11, 0, 0)
            )
            break
        if selected is None or selected_source is None:
            continue

        key = (
            local_day.isoformat(),
            selected.decision_at.isoformat(),
        )
        snapshot = snapshots.get(key)
        if snapshot is None:
            counts["missing-snapshot"] += 1
            continue
        previous_path_range, prior_ref_median = context_by_day[local_day]
        direct = candidate._state_snapshot(
            day_bars,
            previous_path_range,
            prior_ref_median,
            selected_session_prefix,
            selected_source,
            selected,
        )
        primitives = cast(dict[str, object], snapshot["reasoning_primitives"])
        market_context = cast(dict[str, object], snapshot["market_context"])
        expected = {
            "last_is_reference": bool(
                primitives["reference_liquidity_support"]
            ),
            "path_compressed": (
                market_context["current_path_volatility_state"]
                == "compressed"
            ),
            "stale": bool(primitives["sequence_stale_8_14"]),
            "reference_volatility_state": market_context[
                "reference_volatility_state"
            ],
        }
        actual = {
            "last_is_reference": (
                direct["last_structure_event_family"]
                == "reference-liquidity-sweep"
            ),
            "path_compressed": direct["current_path_compressed"],
            "stale": direct["sequence_stale_8_14"],
            "reference_volatility_state": direct[
                "reference_volatility_state"
            ],
        }
        counts["compared"] += 1
        differences = [
            field
            for field in expected
            if expected[field] != actual[field]
        ]
        if not differences:
            counts["exact-match"] += 1
            continue
        for field in differences:
            counts[f"mismatch:{field}"] += 1
        mismatches.append(
            {
                "local_date": local_day.isoformat(),
                "decision_at": selected.decision_at.isoformat(),
                "differences": differences,
                "expected": expected,
                "actual": actual,
                "direct_last_family": direct[
                    "last_structure_event_family"
                ],
                "direct_last_age": direct[
                    "last_structure_event_age_minutes"
                ],
                "snapshot_cibo_structure": snapshot[
                    "cibo_structure_state"
                ],
            }
        )

    return {
        "schema": "qore.vt31.nas100.specialist_state_equivalence.v1",
        "partition": snapshot_payload["partition"],
        "research_only": True,
        "opens_new_holdout": False,
        "counts": dict(sorted(counts.items())),
        "mismatch_rows": mismatches,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = run(args.snapshot, args.evidence)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload["counts"], sort_keys=True))


if __name__ == "__main__":
    main()
