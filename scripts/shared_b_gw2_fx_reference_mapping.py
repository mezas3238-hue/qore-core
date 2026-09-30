"""Build Architect-B current FX provider-to-reference mappings."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, cast

from qore.infrastructure.core_stack_v2.shared_b_fx_reference_mapping import (
    resolve_current_fx_reference_mappings,
)


def _load(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return cast(dict[str, object], payload)


def _aware(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise argparse.ArgumentTypeError("mapping-known-at must be timezone-aware")
    return parsed


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider-schedule", type=Path, required=True)
    parser.add_argument("--component-resolution", type=Path, required=True)
    parser.add_argument("--mapping-known-at", type=_aware, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    payload = resolve_current_fx_reference_mappings(
        provider_schedule=_load(args.provider_schedule),
        component_resolution=_load(args.component_resolution),
        mapping_known_at=args.mapping_known_at,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "identity": payload["identity"],
                "status": payload["status"],
                "mapped_provider_fx_symbol_count": payload[
                    "mapped_provider_fx_symbol_count"
                ],
                "provider_neutral_reference_count": payload[
                    "provider_neutral_reference_count"
                ],
                "mapping_scope": payload["mapping_authority_scope"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
