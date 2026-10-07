#!/usr/bin/env python3
"""Prepare the shared CIBO three-mode suite without rebuilding market history."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence", required=True, type=Path)
    parser.add_argument("--evidence-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    assets = args.evidence_dir / "assets"
    required = (
        "walk-forward",
        "historical-control",
        "atlas-AUDJPY",
        "atlas-EURUSD",
        "atlas-GBPJPY",
        "atlas-GBPUSD",
        "atlas-NAS100",
        "atlas-XAUUSD",
    )
    missing = [name for name in required if not (assets / name).is_dir()]
    if missing:
        raise SystemExit(f"missing shared CIBO suite assets: {missing}")

    payload = {
        "schema": "qore.github-trader-lab.cibo-three-mode-prepared.v1",
        "primary_evidence_sha256": sha256(args.evidence),
        "primary_evidence": str(args.evidence.resolve()),
        "assets_root": str(assets.resolve()),
        "required_assets": list(required),
        "prepared_from_raw_m1": False,
        "prepared_from_cached_causal_artifacts": True,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
