"""CLI for Architect-B official index reference mapping."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, cast

from qore.infrastructure.core_stack_v2.shared_b_index_reference_mapping import (
    build_index_reference_mapping,
)


def _load(path: Path) -> dict[str, object]:
    value: Any = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain an object")
    return cast(dict[str, object], value)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider-attested", type=Path, required=True)
    parser.add_argument("--authority-evidence", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    payload = build_index_reference_mapping(
        provider_attested=_load(args.provider_attested),
        authority_evidence=_load(args.authority_evidence),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "status": payload["status"],
        "provider_index_sensor_count": payload["provider_index_sensor_count"],
        "current_official_reference_mapped_count": payload[
            "current_official_reference_mapped_count"
        ],
        "legacy_reference_lineage_only_count": payload[
            "legacy_reference_lineage_only_count"
        ],
        "provider_binding_unresolved_count": payload[
            "provider_binding_unresolved_count"
        ],
        "b06_complete": payload["b06_complete"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
