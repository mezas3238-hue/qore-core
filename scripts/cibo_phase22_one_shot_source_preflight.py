"""Validate immutable Phase22 V2 source archives without running Traders."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from qore.infrastructure.cibo_phase22_one_shot_source_preflight import (
    expected_source_archive_rows,
    validate_frozen_replay_source_manifest,
    validate_m5_source_root,
    validate_vt31_m1_source_root,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sources-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    validate_frozen_replay_source_manifest()
    reports = []
    for symbol, timeframe, *_rest in expected_source_archive_rows():
        root = args.sources_root / f"{symbol}-{timeframe}"
        if timeframe == "M1":
            reports.append(validate_vt31_m1_source_root(root=root))
        else:
            reports.append(validate_m5_source_root(root=root, symbol=symbol))

    payload = {
        "schema": "qore.cibo.phase22.one-shot-source-preflight.v1",
        "status": "READY",
        "source_archives": reports,
        "archive_count": len(reports),
        "trader_logic_executed": False,
        "outcomes_inspected": False,
        "productive_authority": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
