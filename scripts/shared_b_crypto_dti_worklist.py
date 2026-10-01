"""CLI for Architect-B crypto DTI authority worklist."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, cast

from qore.infrastructure.core_stack_v2.shared_b_crypto_dti_worklist import (
    build_crypto_dti_resolution_worklist,
)


def _load(path: Path) -> dict[str, object]:
    value: Any = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain an object")
    return cast(dict[str, object], value)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--unit-semantics", type=Path, required=True)
    parser.add_argument("--authority-policy", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    payload = build_crypto_dti_resolution_worklist(
        unit_semantics=_load(args.unit_semantics),
        authority_policy=_load(args.authority_policy),
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
                "crypto_sensor_count": payload["crypto_sensor_count"],
                "dti_asset_identity_verified_count": payload[
                    "dti_asset_identity_verified_count"
                ],
                "b06_complete": payload["b06_complete"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
