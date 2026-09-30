"""CLI for Architect-B global identity frontier V3."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, cast

from qore.infrastructure.core_stack_v2.shared_b_global_identity_frontier_v3 import (
    build_identity_frontier_v3,
)


def _load(path: Path) -> dict[str, object]:
    value: Any = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain an object")
    return cast(dict[str, object], value)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--frontier-v2", type=Path, required=True)
    parser.add_argument("--index-mapping", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    payload = build_identity_frontier_v3(
        frontier_v2=_load(args.frontier_v2),
        index_mapping=_load(args.index_mapping),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "status": payload["status"],
        "sensor_count": payload["sensor_count"],
        "current_reference_mapped_count": payload[
            "current_reference_mapped_count"
        ],
        "dated_contract_descriptor_verified_count": payload[
            "dated_contract_descriptor_verified_count"
        ],
        "legacy_index_reference_lineage_only_count": payload[
            "legacy_index_reference_lineage_only_count"
        ],
        "index_provider_binding_unresolved_count": payload[
            "index_provider_binding_unresolved_count"
        ],
        "cryptocurrency_provider_attested_only_count": payload[
            "cryptocurrency_provider_attested_only_count"
        ],
        "b06_complete": payload["b06_complete"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
