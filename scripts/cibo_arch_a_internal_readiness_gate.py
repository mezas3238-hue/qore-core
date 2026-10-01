"""CLI for the Architect A internal-readiness contract."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from qore.infrastructure.cibo_arch_a_internal_readiness import (
    build_architect_a_scientific_batch_plan,
    evaluate_architect_a_internal_readiness,
    evaluate_architect_a_scientific_intake,
)

OUTPUT_PATH = Path("artifacts/cibo_arch_a_internal_readiness_v1.json")
INTAKE_OUTPUT_PATH = Path("artifacts/cibo_arch_a_scientific_intake_v1.json")
BATCH_OUTPUT_PATH = Path("artifacts/cibo_arch_a_scientific_batch_plan_v1.json")


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--forward-manifest",
        type=Path,
        help="Architect-B exported forward-economic manifest JSON.",
    )
    parser.add_argument(
        "--require-scientific-intake",
        action="store_true",
        help="Exit non-zero unless the B manifest unlocks A batch science.",
    )
    args = parser.parse_args()

    report = evaluate_architect_a_internal_readiness()
    _write_json(OUTPUT_PATH, report.as_dict())
    print(json.dumps(report.as_dict(), sort_keys=True))
    if not report.passed:
        return 1

    if args.forward_manifest is None:
        if args.require_scientific_intake:
            parser.error(
                "--require-scientific-intake requires --forward-manifest"
            )
        return 0

    payload = json.loads(args.forward_manifest.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError("Architect-B forward manifest must be JSON object")
    intake = evaluate_architect_a_scientific_intake(payload)
    batch = build_architect_a_scientific_batch_plan(report, intake)
    _write_json(INTAKE_OUTPUT_PATH, intake.as_dict())
    _write_json(BATCH_OUTPUT_PATH, batch.as_dict())
    print(json.dumps(intake.as_dict(), sort_keys=True))
    print(json.dumps(batch.as_dict(), sort_keys=True))

    if args.require_scientific_intake and not batch.population_batch_ready:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
