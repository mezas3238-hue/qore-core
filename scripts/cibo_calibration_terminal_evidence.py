"""Export terminal Shadow-successor calibration evidence."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from qore.infrastructure.cibo_ce2i_calibration_terminal_evidence import (
    ACTIVE_CERTIFICATION_TOOLS,
    QUALIFICATION_FAILED_TOOLS,
    STRUCTURALLY_DISABLED_TOOLS,
    build_terminal_calibration_readiness,
    shadow_successor_manifest,
    terminal_tool_evidence,
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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    forward = shadow_successor_manifest()
    tools = terminal_tool_evidence()
    readiness = build_terminal_calibration_readiness()
    assert readiness.calibration_manifest is not None

    (args.output_dir / "shadow-successor-manifest.json").write_text(
        json.dumps(forward, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (args.output_dir / "terminal-tool-evidence.json").write_text(
        json.dumps(
            {"tools": _jsonable([asdict(item) for item in tools])},
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    payload = {
        "schema": "qore.cibo.calibration-freeze-terminal.v1",
        "status": "SEALED_TERMINAL",
        "ready_to_seal": readiness.ready_to_seal,
        "blockers": list(readiness.blockers),
        "manifest_fingerprint": readiness.calibration_manifest.fingerprint(),
        "active_certification_tools": list(ACTIVE_CERTIFICATION_TOOLS),
        "qualification_failed_tools": list(QUALIFICATION_FAILED_TOOLS),
        "structurally_disabled_tools": list(STRUCTURALLY_DISABLED_TOOLS),
        "calibration_manifest": _jsonable(
            asdict(readiness.calibration_manifest)
        ),
        "governance": {
            "historical_registry_rewritten": False,
            "holdout_2017h1_read": False,
            "productive_authority": False,
        },
    }
    (args.output_dir / "terminal-calibration-freeze.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
