"""CLI for Architect-B cryptocurrency provider-unit semantics."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, cast

from qore.infrastructure.core_stack_v2.shared_b_crypto_provider_unit_semantics import (
    build_crypto_provider_unit_semantics,
)


def _load(path: Path) -> dict[str, object]:
    value: Any = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain an object")
    return cast(dict[str, object], value)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider-attested", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = build_crypto_provider_unit_semantics(
        provider_attested=_load(args.provider_attested),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "status": payload["status"],
        "crypto_sensor_count": payload["crypto_sensor_count"],
        "direct_provider_base_unit_count": payload[
            "direct_provider_base_unit_count"
        ],
        "scaled_provider_base_unit_count": payload[
            "scaled_provider_base_unit_count"
        ],
        "b06_complete": payload["b06_complete"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
