"""CLI for the Architect A internal-readiness contract."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from qore.infrastructure.cibo_arch_a_internal_readiness import (
    build_architect_a_phase22_v2_scientific_batch_plan,
    build_architect_a_scientific_batch_plan,
    evaluate_architect_a_internal_readiness,
    evaluate_architect_a_mechanism_evidence,
    evaluate_architect_a_phase22_v2_mechanism_evidence,
    evaluate_architect_a_phase22_v2_scientific_intake,
    evaluate_architect_a_phase22_v2_scientific_outcome,
    evaluate_architect_a_phase22_v2_workstream_evidence,
    evaluate_architect_a_scientific_intake,
)

OUTPUT_PATH = Path("artifacts/cibo_arch_a_internal_readiness_v1.json")
INTAKE_OUTPUT_PATH = Path("artifacts/cibo_arch_a_scientific_intake_v1.json")
BATCH_OUTPUT_PATH = Path("artifacts/cibo_arch_a_scientific_batch_plan_v1.json")
MECHANISM_OUTPUT_PATH = Path(
    "artifacts/cibo_arch_a_mechanism_evidence_receipt_v1.json"
)
PHASE22_INTAKE_OUTPUT_PATH = Path(
    "artifacts/cibo_arch_a_phase22_v2_scientific_intake_v1.json"
)
PHASE22_BATCH_OUTPUT_PATH = Path(
    "artifacts/cibo_arch_a_phase22_v2_scientific_batch_plan_v1.json"
)
PHASE22_MECHANISM_OUTPUT_PATH = Path(
    "artifacts/cibo_arch_a_phase22_v2_mechanism_evidence_v1.json"
)
PHASE22_WORKSTREAM_MATRIX_OUTPUT_PATH = Path(
    "artifacts/cibo_arch_a_phase22_v2_workstream_evidence_matrix_v1.json"
)
PHASE22_DISPOSITION_OUTPUT_PATH = Path(
    "artifacts/cibo_arch_a_phase22_v2_scientific_disposition_v1.json"
)


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
        "--phase22-v2-manifest",
        type=Path,
        help="Architect-B exported Phase22 V2 scientific handoff manifest JSON.",
    )
    parser.add_argument(
        "--require-scientific-intake",
        action="store_true",
        help="Exit non-zero unless the B manifest unlocks A population intake.",
    )
    parser.add_argument(
        "--mechanism-evidence",
        type=Path,
        help="Integrator JSON containing Architect-A mechanism evidence SHAs.",
    )
    parser.add_argument(
        "--scientific-outcome",
        type=Path,
        help="One completed frozen Architect-A workstream gate outcome JSON.",
    )
    parser.add_argument(
        "--require-full-mechanism-science",
        action="store_true",
        help="Exit non-zero unless all mechanism evidence packages are present.",
    )
    args = parser.parse_args()

    report = evaluate_architect_a_internal_readiness()
    _write_json(OUTPUT_PATH, report.as_dict())
    print(json.dumps(report.as_dict(), sort_keys=True))
    if not report.passed:
        return 1

    if (
        args.forward_manifest is not None
        and args.phase22_v2_manifest is not None
    ):
        parser.error(
            "--forward-manifest and --phase22-v2-manifest are mutually exclusive"
        )

    if args.forward_manifest is None and args.phase22_v2_manifest is None:
        if args.require_scientific_intake:
            parser.error(
                "--require-scientific-intake requires --forward-manifest"
            )
        if args.mechanism_evidence is not None:
            parser.error(
                "--mechanism-evidence requires a scientific manifest"
            )
        if args.scientific_outcome is not None:
            parser.error(
                "--scientific-outcome requires --phase22-v2-manifest"
            )
        if args.require_full_mechanism_science:
            parser.error(
                "--require-full-mechanism-science requires --forward-manifest"
            )
        return 0


    if args.phase22_v2_manifest is not None:
        payload = json.loads(
            args.phase22_v2_manifest.read_text(encoding="utf-8")
        )
        if not isinstance(payload, dict):
            raise TypeError("Architect-B Phase22 V2 manifest must be JSON object")
        intake_v2 = evaluate_architect_a_phase22_v2_scientific_intake(payload)
        batch_v2 = build_architect_a_phase22_v2_scientific_batch_plan(
            report,
            intake_v2,
        )
        _write_json(PHASE22_INTAKE_OUTPUT_PATH, intake_v2.as_dict())
        _write_json(PHASE22_BATCH_OUTPUT_PATH, batch_v2.as_dict())
        print(json.dumps(intake_v2.as_dict(), sort_keys=True))
        print(json.dumps(batch_v2.as_dict(), sort_keys=True))

        if (
            args.require_scientific_intake
            and not batch_v2.population_batch_ready
        ):
            return 2

        mechanism_v2 = None
        matrix_v2 = None
        if args.mechanism_evidence is not None:
            mechanism_payload = json.loads(
                args.mechanism_evidence.read_text(encoding="utf-8")
            )
            if not isinstance(mechanism_payload, dict):
                raise TypeError(
                    "Architect-A Phase22 mechanism evidence must be JSON object"
                )
            mechanism_v2 = evaluate_architect_a_phase22_v2_mechanism_evidence(
                mechanism_payload,
                intake_v2,
            )
            _write_json(
                PHASE22_MECHANISM_OUTPUT_PATH,
                mechanism_v2.as_dict(),
            )
            print(json.dumps(mechanism_v2.as_dict(), sort_keys=True))
            matrix_v2 = evaluate_architect_a_phase22_v2_workstream_evidence(
                intake_v2,
                mechanism_v2,
            )
            _write_json(
                PHASE22_WORKSTREAM_MATRIX_OUTPUT_PATH,
                matrix_v2.as_dict(),
            )
            print(json.dumps(matrix_v2.as_dict(), sort_keys=True))

        if args.scientific_outcome is not None:
            if matrix_v2 is None:
                parser.error(
                    "--scientific-outcome requires --mechanism-evidence"
                )
            outcome_payload = json.loads(
                args.scientific_outcome.read_text(encoding="utf-8")
            )
            if not isinstance(outcome_payload, dict):
                raise TypeError(
                    "Architect-A scientific outcome must be JSON object"
                )
            disposition = evaluate_architect_a_phase22_v2_scientific_outcome(
                outcome_payload,
                matrix_v2,
            )
            _write_json(
                PHASE22_DISPOSITION_OUTPUT_PATH,
                disposition.as_dict(),
            )
            print(json.dumps(disposition.as_dict(), sort_keys=True))

        if args.require_full_mechanism_science:
            if mechanism_v2 is None:
                parser.error(
                    "--require-full-mechanism-science requires "
                    "--mechanism-evidence"
                )
            if not mechanism_v2.ready_for_full_mechanism_science:
                return 3
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

    mechanism = None
    if args.mechanism_evidence is not None:
        mechanism_payload = json.loads(
            args.mechanism_evidence.read_text(encoding="utf-8")
        )
        if not isinstance(mechanism_payload, dict):
            raise TypeError("Architect-A mechanism evidence must be JSON object")
        mechanism = evaluate_architect_a_mechanism_evidence(
            mechanism_payload,
            intake,
        )
        _write_json(MECHANISM_OUTPUT_PATH, mechanism.as_dict())
        print(json.dumps(mechanism.as_dict(), sort_keys=True))

    if args.require_full_mechanism_science:
        if mechanism is None:
            parser.error(
                "--require-full-mechanism-science requires --mechanism-evidence"
            )
        if not mechanism.ready_for_full_mechanism_science:
            return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
