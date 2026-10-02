"""Assemble sealed Phase22 fresh lane files after the durable claim exists."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from qore.infrastructure.cibo_phase22_fresh_batch_assembly import (
    assemble_phase22_fresh_batch,
)


_TURTLE_ARGS = {
    "R34_XAUUSD": "r34_xauusd",
    "R38_EURUSD": "r38_eurusd",
    "R43_GBPUSD": "r43_gbpusd",
    "R38_GBPJPY": "r38_gbpjpy",
    "R42_AUDJPY": "r42_audjpy",
}


def _sha(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _json(path: Path) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"expected JSON object: {path}")
    return raw


def _jsonl(path: Path) -> tuple[dict[str, object], ...]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        raw = json.loads(line)
        if not isinstance(raw, dict):
            raise ValueError(f"expected JSONL objects: {path}")
        rows.append(raw)
    return tuple(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--vt08", type=Path, required=True)
    parser.add_argument("--vt31", type=Path, required=True)
    parser.add_argument("--r34-xauusd", dest="r34_xauusd", type=Path, required=True)
    parser.add_argument("--r38-eurusd", dest="r38_eurusd", type=Path, required=True)
    parser.add_argument("--r43-gbpusd", dest="r43_gbpusd", type=Path, required=True)
    parser.add_argument("--r38-gbpjpy", dest="r38_gbpjpy", type=Path, required=True)
    parser.add_argument("--r42-audjpy", dest="r42_audjpy", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    turtle_paths = {
        trader_id: getattr(args, name)
        for trader_id, name in _TURTLE_ARGS.items()
    }
    lane_digests = {
        "VT08_FOREX": _sha(args.vt08),
        "VT31_NAS100": _sha(args.vt31),
        **{trader_id: _sha(path) for trader_id, path in turtle_paths.items()},
    }
    batch = assemble_phase22_fresh_batch(
        vt08_payload=_json(args.vt08),
        turtle_rows={
            trader_id: _jsonl(path)
            for trader_id, path in turtle_paths.items()
        },
        vt31_payload=_json(args.vt31),
        lane_artifact_sha256s=lane_digests,
    )
    payload = {
        "schema": "qore.cibo.phase22.fresh-batch-assembly.v1",
        "candidate_id": batch.candidate_id,
        "batch_sha256": batch.fingerprint(),
        "traders": [
            {
                "trader_id": item.trader_id,
                "lane_artifact_sha256": item.source_artifact_sha256,
                "opportunity_count": len(item.opportunities),
                "evidence_sha256": item.fingerprint(),
            }
            for item in batch.traders
        ],
        "opportunities": [item.payload() for item in batch.opportunities],
        "legacy_trader_sizing_used_for_cibo": False,
        "productive_authority": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "candidate_id": batch.candidate_id,
        "batch_sha256": batch.fingerprint(),
        "opportunity_count": len(batch.opportunities),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
