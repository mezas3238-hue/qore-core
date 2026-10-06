"""Emit fail-closed CIBO calibration-freeze readiness from explicit evidence."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from qore.infrastructure.cibo_ce2i_calibration_freeze_manifest import (
    FrozenToolCalibration,
    FrozenToolCalibrationDisposition,
)
from qore.infrastructure.cibo_ce2i_calibration_freeze_readiness import (
    evaluate_calibration_freeze_readiness,
)


def _jsonable(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, tuple):
        return [_jsonable(item) for item in value]
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {
            str(key): _jsonable(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    return value


def _load_tools(path: Path) -> tuple[FrozenToolCalibration, ...]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("tools"), list):
        raise TypeError("calibration tool evidence must contain tools list")
    rows: list[FrozenToolCalibration] = []
    for raw in payload["tools"]:
        if not isinstance(raw, dict):
            raise TypeError("calibration tool evidence row must be object")
        refs = raw.get("evidence_refs")
        if not isinstance(refs, list):
            raise TypeError("calibration tool evidence refs must be list")
        rows.append(
            FrozenToolCalibration(
                tool_code=str(raw["tool_code"]),
                disposition=FrozenToolCalibrationDisposition(
                    str(raw["disposition"])
                ),
                evidence_refs=tuple(str(item) for item in refs),
                oos_ready=bool(raw["oos_ready"]),
                certification_ready=bool(raw["certification_ready"]),
                structurally_disabled=bool(raw["structurally_disabled"]),
                provider_economics_bound=bool(
                    raw["provider_economics_bound"]
                ),
                holdout_outcomes_used=bool(
                    raw.get("holdout_outcomes_used", False)
                ),
                target_aware=bool(raw.get("target_aware", False)),
            )
        )
    return tuple(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--forward-manifest", type=Path, required=True)
    parser.add_argument("--tool-evidence", type=Path, required=True)
    parser.add_argument("--frozen-at", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--require-ready", action="store_true")
    args = parser.parse_args()

    forward = json.loads(args.forward_manifest.read_text(encoding="utf-8"))
    if not isinstance(forward, dict):
        raise TypeError("forward manifest must be JSON object")
    frozen_at = datetime.fromisoformat(args.frozen_at)
    report = evaluate_calibration_freeze_readiness(
        forward_manifest=forward,
        tools=_load_tools(args.tool_evidence),
        frozen_at=frozen_at,
    )
    payload = _jsonable(report.as_dict())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, sort_keys=True))
    if args.require_ready and not report.ready_to_seal:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
