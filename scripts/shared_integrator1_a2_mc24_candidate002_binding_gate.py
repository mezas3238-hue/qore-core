#!/usr/bin/env python3
"""Fail-closed MC24 binding gate for A2 MC23 candidate 002.

This Integrator-1 gate creates no scientific evidence and does not implement
MC24. It only prevents MC25 from advancing unless a sealed MC24 result is
explicitly bound to the validated candidate-002 identity and fingerprint.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

IDENTITY = "QORE_SHARED_INTEGRATOR_1_A2_MC24_CANDIDATE_002_BINDING_GATE_001"
MC23_ID = "QORE_SHARED_MC23_CANDIDATE_002_ROUTED_SECOND_ORDER_001"
MC23_PASS = "MC23_CANDIDATE_002_VALIDATED_AND_INDEPENDENTLY_REPLICATED_PASS"


def _load_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _safe(row: dict[str, Any]) -> bool:
    return not any(
        row.get(key) is True
        for key in (
            "productive_authority",
            "protected_certification_holdout_opened",
            "broker_mutation",
            "live",
            "real_capital_used",
        )
    )


def _rows(roots: list[Path]) -> list[tuple[Path, dict[str, Any]]]:
    out: list[tuple[Path, dict[str, Any]]] = []
    for root in roots:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*.json")):
            try:
                out.append((path, _load_object(path)))
            except (json.JSONDecodeError, OSError, ValueError):
                continue
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mc23-result",
        type=Path,
        default=Path("result/mc23-candidate-002.json"),
    )
    parser.add_argument(
        "--evidence-dir",
        type=Path,
        default=Path("docs/shared/evidence"),
    )
    parser.add_argument(
        "--runtime-evidence-dir",
        type=Path,
        action="append",
        default=[],
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    mc23 = _load_object(args.mc23_result)
    if (
        mc23.get("identity") != MC23_ID
        or mc23.get("status") != MC23_PASS
        or mc23.get("mc23_completed_and_proven") is not True
        or mc23.get("candidate_001_reused") is not False
        or not _safe(mc23)
    ):
        raise SystemExit("candidate-002 is not a sealed scientific PASS")

    fingerprint = mc23.get("candidate_fingerprint")
    if not isinstance(fingerprint, str) or not fingerprint:
        raise SystemExit("candidate-002 fingerprint missing")

    roots = [args.evidence_dir, *args.runtime_evidence_dir]
    matched_path: str | None = None
    for path, row in _rows(roots):
        bound_identity = (
            row.get("mc23_candidate_identity")
            or row.get("bound_mc23_identity")
            or row.get("source_mc23_identity")
        )
        bound_fingerprint = (
            row.get("mc23_candidate_fingerprint")
            or row.get("bound_mc23_fingerprint")
            or row.get("source_mc23_fingerprint")
        )
        if (
            bound_identity == MC23_ID
            and bound_fingerprint == fingerprint
            and row.get("mc24_completed_and_proven") is True
            and row.get("empirical_half_life_validated") is True
            and row.get("retained_knowledge_non_degradation_pass") is True
            and _safe(row)
        ):
            matched_path = str(path)
            break

    passed = matched_path is not None
    payload = {
        "identity": IDENTITY,
        "status": (
            "I1_A2_MC24_CANDIDATE_002_BINDING_PASS"
            if passed
            else "I1_A2_MC24_CANDIDATE_002_BINDING_BLOCKED"
        ),
        "mc23_candidate_identity": MC23_ID,
        "mc23_candidate_fingerprint": fingerprint,
        "mc24_explicit_binding_found": passed,
        "matched_mc24_evidence": matched_path,
        "blockers": (
            []
            if passed
            else ["MC24_CANDIDATE_002_EXPLICIT_BINDING_REQUIRED"]
        ),
        "scientific_evidence_created_by_gate": False,
        "producer_thresholds_modified": False,
        "productive_authority": False,
        "protected_certification_holdout_opened": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, sort_keys=True))
    raise SystemExit(0 if passed else 2)


if __name__ == "__main__":
    main()
