#!/usr/bin/env python3
"""Emit MC25 formal governance-stress evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from qore.infrastructure.core_stack_v2.mc25_formal_governance_stress import (
    run_formal_governance_stress,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = run_formal_governance_stress()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, sort_keys=True))
    raise SystemExit(
        0 if payload["formal_stress_stage_completed"] else 2
    )


if __name__ == "__main__":
    main()
