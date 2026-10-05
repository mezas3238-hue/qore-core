#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from qore.infrastructure.cibo_ceiling_discovery_assembly import (
    assemble_ceiling_discovery,
)


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--native-preflight", type=Path, required=True)
    parser.add_argument("--sovereign-run", type=Path, required=True)
    parser.add_argument("--diagnostic-frontier", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    result = assemble_ceiling_discovery(
        native_preflight=_load(args.native_preflight),
        sovereign_run=_load(args.sovereign_run),
        diagnostic_frontier=(
            None
            if args.diagnostic_frontier is None
            else _load(args.diagnostic_frontier)
        ),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "classification": result["classification"],
                "ceiling_discovery_ready_to_close": result[
                    "ceiling_discovery_ready_to_close"
                ],
                "capital_multiple": result["capital_multiple"],
                "maximum_drawdown_fraction_of_peak": result[
                    "maximum_drawdown_fraction_of_peak"
                ],
            },
            sort_keys=True,
        )
    )
    return 0 if result["ceiling_discovery_ready_to_close"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
