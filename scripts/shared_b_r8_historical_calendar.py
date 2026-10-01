"""CLI for Architect-B R8 historical calendar frontier."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, cast

from qore.infrastructure.core_stack_v2.shared_b_r8_historical_calendar import (
    build_r8_historical_calendar_frontier,
)


def _load(path: Path) -> dict[str, object]:
    value: Any = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain an object")
    return cast(dict[str, object], value)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--calendar-worklist", type=Path, required=True)
    parser.add_argument("--r8-manifest", type=Path, required=True)
    parser.add_argument("--authority-evidence", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    payload = build_r8_historical_calendar_frontier(
        calendar_worklist=_load(args.calendar_worklist),
        r8_manifest=_load(args.r8_manifest),
        authority_evidence=_load(args.authority_evidence),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": payload["status"],
                "verified_r8_session_schedules": payload[
                    "r8_historical_session_schedule_verified_count"
                ],
                "verified_r8_holiday_calendars": payload[
                    "r8_historical_holiday_calendar_verified_count"
                ],
                "canonical_calendar_verified_count": payload[
                    "canonical_calendar_verified_count"
                ],
                "b07_complete": payload["b07_complete"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
