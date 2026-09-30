"""CLI for the Architect A internal-readiness contract."""

from __future__ import annotations

import json
from pathlib import Path

from qore.infrastructure.cibo_arch_a_internal_readiness import (
    evaluate_architect_a_internal_readiness,
)

OUTPUT_PATH = Path("artifacts/cibo_arch_a_internal_readiness_v1.json")


def main() -> int:
    report = evaluate_architect_a_internal_readiness()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(report.as_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report.as_dict(), sort_keys=True))
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
