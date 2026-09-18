"""Acquisition/binding-only repair for the frozen GBPJPY R3 CIBO journey replay.

The immutable Target Destination V2 ledger contains a tiny number of source-opposite
keys that collide across different episode ids. The original R3 loader failed the
entire replay on the first collision. This wrapper preserves all economic mechanics
and fails closed only on those ambiguous bindings: colliding keys are omitted from
the source index and therefore become NO_CAUSAL_CIBO_EPISODE_MATCH abstentions.
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import turtle_soup_gbpjpy_r3_cibo_journey as r3

_LAST_AMBIGUOUS_KEYS = 0


def _load_targets_fail_closed(
    root: Path,
) -> tuple[
    dict[str, list[r3.TargetCandidate]],
    dict[tuple[datetime, str, str, Decimal], str],
]:
    global _LAST_AMBIGUOUS_KEYS
    manifest_paths = list(root.rglob("target-destination-v2-manifest.json"))
    ledger_paths = list(root.rglob("TARGET_DESTINATION_LEDGER_V2.jsonl"))
    if len(manifest_paths) != 1 or len(ledger_paths) != 1:
        raise ValueError("expected one GBPJPY Target Destination V2 artifact")
    manifest = json.loads(manifest_paths[0].read_text())
    if manifest.get("identity") != r3.TARGET_IDENTITY or manifest.get("symbol") != r3.SYMBOL:
        raise ValueError("unexpected Target Destination V2 identity")

    episodes: dict[str, list[r3.TargetCandidate]] = defaultdict(list)
    source_index: dict[tuple[datetime, str, str, Decimal], str] = {}
    ambiguous: set[tuple[datetime, str, str, Decimal]] = set()

    with ledger_paths[0].open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            raw = json.loads(line)
            candidate = r3.TargetCandidate(
                episode_id=str(raw["episode_id"]),
                kind=str(raw["candidate_type"]),
                timeframe=str(raw["source_timeframe"]),
                level=Decimal(str(raw["candidate_price"])),
                known_at=r3._dt(str(raw["candidate_known_at"])),
                touch_at=(
                    None
                    if raw.get("touch_m5_opened_at") is None
                    else r3._dt(str(raw["touch_m5_opened_at"]))
                ),
            )
            episodes[candidate.episode_id].append(candidate)
            if candidate.kind != "SOURCE_OPPOSITE_BOUNDARY":
                continue
            key = (
                r3._dt(str(raw["departure_at"])),
                str(raw["side"]),
                candidate.timeframe,
                candidate.level,
            )
            if key in ambiguous:
                continue
            previous = source_index.get(key)
            if previous is not None and previous != candidate.episode_id:
                source_index.pop(key, None)
                ambiguous.add(key)
                continue
            source_index[key] = candidate.episode_id

    _LAST_AMBIGUOUS_KEYS = len(ambiguous)
    return dict(episodes), source_index


def run(source_root: Path, target_root: Path, output: Path) -> dict[str, Any]:
    original_loader = r3._load_targets
    try:
        r3._load_targets = _load_targets_fail_closed
        payload = r3.run(source_root, target_root, output)
    finally:
        r3._load_targets = original_loader

    payload["binding_repair"] = {
        "type": "FAIL_CLOSED_AMBIGUOUS_SOURCE_OPPOSITE_BINDING_ONLY",
        "ambiguous_source_opposite_keys": _LAST_AMBIGUOUS_KEYS,
        "economic_mechanics_changed": False,
        "ambiguous_keys_are_abstentions": True,
    }
    (output / "report.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n"
    )
    return payload


def main() -> None:
    if len(sys.argv) != 4:
        raise SystemExit("usage: module SOURCE_ROOT TARGET_ROOT OUTPUT_DIR")
    payload = run(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]))
    print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
