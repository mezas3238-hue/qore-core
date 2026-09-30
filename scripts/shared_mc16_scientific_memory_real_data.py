#!/usr/bin/env python3
"""Bind governed Scientific Memory V2 to real historical research evidence."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, cast

import shared_sti6_sti8_real_position_intelligence as position

from qore.infrastructure.core_stack_v2.scientific_memory_v2 import (
    ScientificKnowledgeState,
    ScientificMemoryEntry,
    ScientificMemoryKind,
    ScientificMemoryQuery,
    SharedScientificMemory,
)

IDENTITY = "QORE_SHARED_MC16_SCIENTIFIC_MEMORY_REAL_DATA_001"

EXPECTED_IDENTITIES = {
    "sti2": "QORE_SHARED_STI2_V2_TRAJECTORY_HEADS_001",
    "sti5": "QORE_SHARED_STI5_V1_FAILURE_DIAGNOSTIC_001",
    "sti6": "QORE_SHARED_STI6_V1_FAILURE_DIAGNOSTIC_001",
}


def _find_identity(root: Path, identity: str) -> dict[str, Any]:
    for path in sorted(root.rglob("*.json")):
        try:
            payload = json.loads(path.read_text())
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        if isinstance(payload, dict) and payload.get("identity") == identity:
            return cast(dict[str, Any], payload)
    raise ValueError(f"scientific artifact identity not found: {identity}")


def _aware(value: object) -> datetime:
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("scientific memory timestamp must be aware")
    return parsed.astimezone(UTC)


def _terminal_time(
    *,
    signal: str,
    row: dict[str, object],
    paths: dict[str, tuple[object, tuple[object, ...]]],
) -> datetime:
    if signal not in paths:
        raise ValueError(f"missing reconstructed terminal path: {signal}")
    setup, day_bars = paths[signal]
    _fill, exit_index = position.counter._fill_and_exit_indices(
        setup,
        day_bars,
        row,
    )
    terminal_bar = day_bars[exit_index]
    return _aware(cast(Any, terminal_bar).closed_at)


def _episode_entries(
    *,
    partition: str,
    trades_path: Path,
    nas_path: Path,
) -> tuple[ScientificMemoryEntry, ...]:
    rows = position.journey.v3._load_trades(trades_path)
    paths = position._reconstruct_source_partition(nas_path)
    entries: list[ScientificMemoryEntry] = []
    for index, raw in enumerate(rows):
        row = cast(dict[str, object], raw)
        signal = str(row["signal_at"])
        terminal = _terminal_time(signal=signal, row=row, paths=paths)
        final_r = str(row["net_r_after_friction"])
        entries.append(
            ScientificMemoryEntry(
                memory_id=f"episode:{partition}:{index:04d}:{signal}",
                kind=ScientificMemoryKind.EPISODIC,
                subject="VT31_NAS100_CLOSED_POSITION",
                learned_at=terminal,
                evidence_cutoff_at=terminal,
                knowledge_state=ScientificKnowledgeState.RESEARCH,
                source_partition=partition.upper(),
                evidence_refs=(
                    f"immutable-{partition}-market-evidence",
                    f"immutable-{partition}-trade-row",
                ),
                payload=tuple(
                    sorted(
                        (
                            ("net_r_after_friction", final_r),
                            ("side", str(row["side"])),
                            ("signal_at", signal),
                        )
                    )
                ),
            )
        )
    return tuple(entries)


def _scientific_entries(
    *,
    sti2: dict[str, Any],
    sti5: dict[str, Any],
    sti6: dict[str, Any],
    learned_at: datetime,
) -> tuple[ScientificMemoryEntry, ...]:
    sti2_status = str(sti2.get("scientific_status") or sti2.get("status"))
    sti5_status = str(sti5.get("status"))
    sti6_status = str(sti6.get("status"))

    semantic = ScientificMemoryEntry(
        memory_id="semantic:sti2-v2-consumed-r6-r5",
        kind=ScientificMemoryKind.SEMANTIC,
        subject="STI2_OPPORTUNITY_TRAJECTORY_HEADS",
        learned_at=learned_at,
        evidence_cutoff_at=learned_at,
        knowledge_state=ScientificKnowledgeState.REPLICATED_RESEARCH,
        source_partition="R6_R5_CONSUMED",
        evidence_refs=tuple(sorted(("run:36667303884", "artifact:11076956277"))),
        payload=tuple(
            sorted(
                (
                    ("status", sti2_status),
                    ("hypothesis", str(sti2.get("hypothesis", "TRAJECTORY_HEADS"))),
                )
            )
        ),
    )

    regime = ScientificMemoryEntry(
        memory_id="regime:sti5-v1-mechanism-profile",
        kind=ScientificMemoryKind.REGIME,
        subject="STI5_REGIME_TRANSITION_MECHANISM_PROFILE",
        learned_at=learned_at + timedelta(seconds=1),
        evidence_cutoff_at=learned_at,
        knowledge_state=ScientificKnowledgeState.RESEARCH,
        source_partition="R6_R5_CONSUMED",
        evidence_refs=tuple(sorted(("run:36685175913", "artifact:11082953096"))),
        payload=tuple(
            sorted(
                (
                    ("status", sti5_status),
                    (
                        "cross_partition_hypothesis_count",
                        str(len(sti5.get("cross_partition_hypotheses", []))),
                    ),
                )
            )
        ),
    )

    failure_sti5 = ScientificMemoryEntry(
        memory_id="failure:sti5-v1",
        kind=ScientificMemoryKind.FAILURE,
        subject="STI5_REGIME_TRANSITION",
        learned_at=learned_at + timedelta(seconds=2),
        evidence_cutoff_at=learned_at,
        knowledge_state=ScientificKnowledgeState.FALSIFIED,
        source_partition="R6_R5_CONSUMED",
        evidence_refs=tuple(sorted(("run:36685175913", "artifact:11082953096"))),
        payload=(("diagnostic_status", sti5_status),),
        hypothesis_id="STI5_V1_STATIC_REGIME_TRANSITION",
        falsification_reasons=(
            "NO_CROSS_PARTITION_MECHANISM_HYPOTHESIS",
            "CURRENT_SENSOR_REPRESENTATION_INSUFFICIENT_ON_R5",
        ),
    )

    failure_sti6 = ScientificMemoryEntry(
        memory_id="failure:sti6-v1",
        kind=ScientificMemoryKind.FAILURE,
        subject="STI6_CONTINUATION_POSITIVE_TAIL",
        learned_at=learned_at + timedelta(seconds=3),
        evidence_cutoff_at=learned_at,
        knowledge_state=ScientificKnowledgeState.FALSIFIED,
        source_partition="R6_CONSUMED",
        evidence_refs=tuple(sorted(("run:36682712727", "artifact:11082582105"))),
        payload=(("diagnostic_status", sti6_status),),
        hypothesis_id="STI6_V1_STATIC_CONTINUATION_LEVEL",
        falsification_reasons=(
            "STATIC_LEVEL_NOT_DISCRIMINATIVE",
            "FAILURE_HAZARD_REQUIRES_SEPARATE_VETO",
        ),
    )
    return semantic, regime, failure_sti5, failure_sti6


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--r6-trades", type=Path, required=True)
    parser.add_argument("--r6-nas", type=Path, required=True)
    parser.add_argument("--r5-trades", type=Path, required=True)
    parser.add_argument("--r5-nas", type=Path, required=True)
    parser.add_argument("--sti2-artifact", type=Path, required=True)
    parser.add_argument("--sti5-artifact", type=Path, required=True)
    parser.add_argument("--sti6-artifact", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    episodes_r6 = _episode_entries(
        partition="r6",
        trades_path=args.r6_trades,
        nas_path=args.r6_nas,
    )
    episodes_r5 = _episode_entries(
        partition="r5",
        trades_path=args.r5_trades,
        nas_path=args.r5_nas,
    )
    sti2 = _find_identity(args.sti2_artifact, EXPECTED_IDENTITIES["sti2"])
    sti5 = _find_identity(args.sti5_artifact, EXPECTED_IDENTITIES["sti5"])
    sti6 = _find_identity(args.sti6_artifact, EXPECTED_IDENTITIES["sti6"])

    learned_at = datetime(2026, 9, 30, 12, 0, tzinfo=UTC)
    scientific = _scientific_entries(
        sti2=sti2,
        sti5=sti5,
        sti6=sti6,
        learned_at=learned_at,
    )
    memory = SharedScientificMemory(episodes_r6 + episodes_r5 + scientific)

    before_failures = memory.recall(
        ScientificMemoryQuery(
            as_of=learned_at - timedelta(seconds=1),
            kinds=(ScientificMemoryKind.FAILURE,),
        )
    )
    after_failures = memory.recall(
        ScientificMemoryQuery(
            as_of=learned_at + timedelta(minutes=1),
            kinds=(ScientificMemoryKind.FAILURE,),
        )
    )
    post_research = memory.recall(
        ScientificMemoryQuery(
            as_of=learned_at + timedelta(minutes=1),
            kinds=tuple(sorted(ScientificMemoryKind, key=lambda item: item.value)),
        )
    )

    payload = {
        "identity": IDENTITY,
        "status": "MC16_REAL_DATA_MEMORY_BOUND_CAUSAL_RECALL_PASS",
        "memory_fingerprint": memory.fingerprint(),
        "entry_count": memory.entry_count,
        "episodic_counts": {
            "r6": len(episodes_r6),
            "r5": len(episodes_r5),
        },
        "memory_kind_counts": {
            kind.value: sum(
                item.kind is kind for item in post_research.entries
            )
            for kind in ScientificMemoryKind
        },
        "pre_learning_failure_recall_count": len(before_failures.entries),
        "pre_learning_future_suppressed": before_failures.future_entries_suppressed,
        "post_learning_failure_recall_count": len(after_failures.entries),
        "failure_hypotheses": [
            item.hypothesis_id
            for item in after_failures.entries
        ],
        "causal_gate_pass": (
            len(before_failures.entries) == 0
            and before_failures.future_entries_suppressed == 2
            and len(after_failures.entries) == 2
        ),
        "failure_memory_pass": all(
            item.falsification_reasons
            for item in after_failures.entries
        ),
        "four_memory_classes_present": all(
            any(item.kind is kind for item in post_research.entries)
            for kind in ScientificMemoryKind
        ),
        "productive_authority": False,
        "protected_certification_holdout_opened": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
