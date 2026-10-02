"""Seal CIBO Core provider economics through the stress-bound lane."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from qore.infrastructure.cibo_ce2i_provider_economics_component_freeze import (
    freeze_current_ctrader_demo_provider_economics,
)
from qore.infrastructure.cibo_ce2i_provider_stress_bound_freeze import (
    build_provider_stress_bound_freeze,
)


def _jsonable(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
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
    parser.add_argument("--empirical-inventory", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    empirical = json.loads(
        args.empirical_inventory.read_text(encoding="utf-8")
    )
    frozen_at = datetime.now(UTC)
    stress = build_provider_stress_bound_freeze(
        empirical_inventory=empirical,
        frozen_at=frozen_at,
    )
    component = freeze_current_ctrader_demo_provider_economics(
        frozen_at=frozen_at,
        stress_bound=stress,
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    stress_payload = {
        "schema": "qore.cibo.provider-stress-bound-freeze.v1",
        "status": "CORE_PRE_HOLDOUT_READY",
        **_jsonable(asdict(stress)),
        "fingerprint": stress.fingerprint(),
    }
    component_payload = {
        "schema": "qore.cibo.provider-economics-component-freeze.v2",
        "status": (
            "CORE_PRE_HOLDOUT_READY"
            if component.pre_holdout_provider_economics_ready
            else "NOT_READY"
        ),
        **_jsonable(asdict(component)),
        "fingerprint": component.fingerprint(),
    }
    (args.output_dir / "provider-stress-bound-freeze.json").write_text(
        json.dumps(stress_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (args.output_dir / "provider-economics-component-freeze.json").write_text(
        json.dumps(component_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(component_payload, sort_keys=True))


if __name__ == "__main__":
    main()
