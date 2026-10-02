"""Assemble a reused Phase22 V4 holdout batch for infrastructure validation.

This is deliberately NON-CERTIFYING. It may replay an already consumed/burned
holdout to validate CIBO infrastructure. It never claims scientific freshness,
never grants broker/LIVE/real-capital authority, and never writes the canonical
Phase22 consumption ledger.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from qore.infrastructure.cibo_phase22_trader_parity_manifest import (
    CANONICAL_PHASE22_TRADER_IDS,
)
from qore.infrastructure.cibo_phase22_v4_fresh_batch import (
    build_phase22_v4_fresh_batch,
)
from qore.infrastructure.cibo_phase22_v4_fresh_evidence import (
    TURTLE_SURFACE,
    native_trader_evidence,
    turtle_trader_evidence,
)
from qore.infrastructure.cibo_phase22_v4_governance import V4_CANDIDATE_ID


def _sha(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _json(path: Path) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"expected JSON object: {path}")
    return raw


def _jsonl(path: Path) -> tuple[dict[str, object], ...]:
    rows: list[dict[str, object]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        raw = json.loads(line)
        if not isinstance(raw, dict):
            raise ValueError(f"expected JSONL object: {path}")
        rows.append(raw)
    return tuple(rows)


def assemble(
    *,
    vt08: Path,
    vt31: Path,
    turtle_paths: dict[str, Path],
) -> dict[str, object]:
    expected_turtle = {item[0] for item in TURTLE_SURFACE}
    if set(turtle_paths) != expected_turtle:
        raise ValueError("reused holdout requires exact five Turtle lanes")

    lane_sha256s = {
        "VT08_FOREX": _sha(vt08),
        "VT31_NAS100": _sha(vt31),
        **{trader_id: _sha(path) for trader_id, path in turtle_paths.items()},
    }
    by_id = {
        "VT08_FOREX": native_trader_evidence(
            trader_id="VT08_FOREX",
            payload=_json(vt08),
            lane_artifact_sha256=lane_sha256s["VT08_FOREX"],
        ),
        "VT31_NAS100": native_trader_evidence(
            trader_id="VT31_NAS100",
            payload=_json(vt31),
            lane_artifact_sha256=lane_sha256s["VT31_NAS100"],
        ),
    }
    for trader_id, _symbol in TURTLE_SURFACE:
        by_id[trader_id] = turtle_trader_evidence(
            trader_id=trader_id,
            rows=_jsonl(turtle_paths[trader_id]),
            lane_artifact_sha256=lane_sha256s[trader_id],
        )

    traders = tuple(by_id[item] for item in CANONICAL_PHASE22_TRADER_IDS)
    batch = build_phase22_v4_fresh_batch(traders)
    return {
        "schema": "qore.cibo.phase22.v4-fresh-batch-assembly.v1",
        "candidate_id": V4_CANDIDATE_ID,
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
        "validation_mode": "NON_CERTIFYING_REUSED_HOLDOUT",
        "reused_holdout": True,
        "scientific_freshness_claimed": False,
        "fresh_oos_generalization_claimed": False,
        "canonical_consumption_ledger_written": False,
        "broker_mutation_performed": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "production_authorized": False,
        "merge_authorized": False,
    }


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

    turtle = {
        "R34_XAUUSD": args.r34_xauusd,
        "R38_EURUSD": args.r38_eurusd,
        "R43_GBPUSD": args.r43_gbpusd,
        "R38_GBPJPY": args.r38_gbpjpy,
        "R42_AUDJPY": args.r42_audjpy,
    }
    payload = assemble(vt08=args.vt08, vt31=args.vt31, turtle_paths=turtle)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "candidate_id": payload["candidate_id"],
                "batch_sha256": payload["batch_sha256"],
                "opportunities": len(payload["opportunities"]),
                "scientific_freshness_claimed": False,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
