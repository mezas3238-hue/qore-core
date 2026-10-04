"""Build Architect-B current commodity observation identity pack."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import cast

from qore.infrastructure.core_stack_v2.shared_b_commodity_observation_identity import (
    build_commodity_observation_identity_pack,
)


def _load(path: Path) -> dict[str, object]:
    value=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return cast(dict[str,object],value)


def _aware(value: str) -> datetime:
    parsed=datetime.fromisoformat(value.replace("Z","+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise argparse.ArgumentTypeError("known-at must be timezone-aware")
    return parsed


def main() -> None:
    parser=argparse.ArgumentParser()
    parser.add_argument("--provider-schedule",type=Path,required=True)
    parser.add_argument("--metals-evidence",type=Path,required=True)
    parser.add_argument("--energy-evidence",type=Path,required=True)
    parser.add_argument("--gc-contract-evidence",type=Path,required=True)
    parser.add_argument("--known-at",type=_aware,required=True)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()

    payload=build_commodity_observation_identity_pack(
        provider_schedule=_load(args.provider_schedule),
        metals_evidence=_load(args.metals_evidence),
        energy_evidence=_load(args.energy_evidence),
        gc_contract_evidence=_load(args.gc_contract_evidence),
        known_at=args.known_at,
    )
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(
        json.dumps(payload,sort_keys=True,indent=2)+"\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "identity":payload["identity"],
        "status":payload["status"],
        "record_count":payload["record_count"],
        "metal_reference_count":payload["metal_reference_count"],
        "energy_reference_count":payload["energy_reference_count"],
        "dated_gc_contract_count":payload["dated_gc_contract_count"],
    },sort_keys=True))


if __name__=="__main__":
    main()
