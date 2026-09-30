"""Emit the CIBO pre-holdout readiness checkpoint without 2017H1 access."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from qore.infrastructure.cibo_ce2i_pre_holdout_checkpoint import (
    build_pre_holdout_checkpoint,
)


def _jsonable(value: Any) -> Any:
    if isinstance(value, tuple):
        return [_jsonable(item) for item in value]
    if hasattr(value, "value"):
        return value.value
    return value


def build_report() -> dict[str, object]:
    checkpoint = build_pre_holdout_checkpoint()
    payload = {
        key: _jsonable(value)
        for key, value in asdict(checkpoint).items()
    }
    payload.update(
        {
            "schema": "qore.cibo.pre_holdout_checkpoint.v1",
            "status": (
                "CIBO_PRE_HOLDOUT_FREEZE_READY"
                if checkpoint.ready_to_freeze
                else "CIBO_PRE_HOLDOUT_FREEZE_NOT_READY"
            ),
            "2017h1_unsealed": False,
            "2017h1_outcomes_inspected": False,
        }
    )
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = build_report()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
