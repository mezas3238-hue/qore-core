"""CLI for Architect-B observed COMEX GC contract lifecycle."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, cast

from qore.infrastructure.core_stack_v2.shared_b_gc_contract_lifecycle import (
    build_gc_observed_contract_lifecycle,
)


def _load(path: Path) -> dict[str, object]:
    value: Any = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain an object")
    return cast(dict[str, object], value)


def _aware(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("assessed-at must be timezone-aware")
    return parsed


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--commodity-pack", type=Path, required=True)
    parser.add_argument("--authority-evidence", type=Path, required=True)
    parser.add_argument("--assessed-at", type=_aware, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    payload = build_gc_observed_contract_lifecycle(
        commodity_pack=_load(args.commodity_pack),
        authority_evidence=_load(args.authority_evidence),
        assessed_at=args.assessed_at,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "status": payload["status"],
        "dated_gc_contract_count": payload["dated_gc_contract_count"],
        "expired_before_assessment_month_count": payload[
            "expired_before_assessment_month_count"
        ],
        "current_front_contract_absent_from_observed_set": payload[
            "current_front_contract_absent_from_observed_set"
        ],
        "b15_complete": payload["b15_complete"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
