#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from qore.infrastructure.cibo_arch2_t13_t15_functional_redundancy import (
    analyze_t13_t15_redundancy,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--decision-trace", type=Path, required=True)
    parser.add_argument("--group-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    trace = json.loads(args.decision_trace.read_text(encoding="utf-8"))
    payload = analyze_t13_t15_redundancy(trace)
    payload["group_id"] = args.group_id
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "group_id": payload["group_id"],
                "functional_seam_closed": payload["functional_seam_closed"],
                "T13": payload["T13"]["classification"],
                "T15": payload["T15"]["classification"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
