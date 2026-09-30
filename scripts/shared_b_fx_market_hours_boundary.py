"""Build the Architect-B distributed OTC FX market-hours boundary."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import cast

from qore.infrastructure.core_stack_v2.shared_b_fx_market_hours_boundary import (
    build_fx_market_hours_boundary,
)


def _load(path: Path) -> dict[str, object]:
    payload=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload,dict):
        raise ValueError(f"{path} must contain a JSON object")
    return cast(dict[str,object],payload)


def main() -> None:
    parser=argparse.ArgumentParser()
    parser.add_argument("--provider-schedule",type=Path,required=True)
    parser.add_argument("--authority-evidence",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()

    payload=build_fx_market_hours_boundary(
        provider_schedule=_load(args.provider_schedule),
        authority_evidence=_load(args.authority_evidence),
    )
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(
        json.dumps(payload,sort_keys=True,indent=2)+"\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "identity":payload["identity"],
        "status":payload["status"],
        "fx_sensor_count":payload["fx_sensor_count"],
        "canonical_calendar_verified_count":payload[
            "canonical_calendar_verified_count"
        ],
        "daily_24_hour_operation_supported":payload[
            "daily_24_hour_operation_supported"
        ],
        "exact_universal_weekly_boundary_verified":payload[
            "exact_universal_weekly_boundary_verified"
        ],
    },sort_keys=True))


if __name__=="__main__":
    main()
